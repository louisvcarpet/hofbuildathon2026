import asyncio
import logging
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import Base, engine, get_db
from app.models import Offer, SurveyResponse
from app.node1_extract.databricks_node import DatabricksNode
from app.offer_workflow.state import OfferWorkflowState
from app.schemas import (
    EvaluationOutput,
    MarketSnapshotResponse,
    OfferChatRequest,
    OfferChatResponse,
    OfferPdfIngestResponse,
    ParsedOfferData,
)
from app.services.evaluation_engine import _evaluation_from_row
from app.services.evaluation_engine import (
    evaluate_offer,
    get_latest_evaluation,
    is_recent,
)
from app.services.pdf_reader import extract_pdf_text, parse_offer_text
from app.services.nemotron_client import nemotron_chat
from app.services.llm_exceptions import (
    LLMBadRequest,
    LLMAuthFailed,
    LLMError,
    LLMInvalidJSONError,
    LLMModelUnavailable,
    LLMRateLimited,
    LLMUpstreamUnavailable,
)

try:
    from app.offer_workflow.run import run_offer_workflow
except Exception:  # pragma: no cover - optional workflow dependency path
    run_offer_workflow = None

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Offer Evaluation MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.post("/offers/ingest-pdf", response_model=OfferPdfIngestResponse)
def ingest_offer_pdf(
    file: UploadFile = File(...),
    create_records: bool = Query(default=True),
    include_text: bool = Query(default=False),
    priority_financial: int | None = Form(default=None),
    priority_career: int | None = Form(default=None),
    priority_lifestyle: int | None = Form(default=None),
    priority_alignment: int | None = Form(default=None),
    remote_preference: str | None = Form(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OfferPdfIngestResponse:
    if (file.content_type or "").lower() not in {"application/pdf"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported")

    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        extracted_text = extract_pdf_text(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to read PDF: {exc}") from exc
    if not extracted_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF text extraction returned empty content")

    parsed = parse_offer_text(extracted_text)
    parsed_payload = ParsedOfferData(
        role_title=parsed.role_title,
        level=parsed.level,
        location=parsed.location,
        base_salary=parsed.base_salary,
        bonus_target=parsed.bonus_target,
        equity_type=parsed.equity_type,
        equity_amount=parsed.equity_amount,
        vesting_schedule=parsed.vesting_schedule,
        start_date=parsed.start_date.date().isoformat() if parsed.start_date else None,
        confidence_note=parsed.confidence_note,
    )

    if not create_records:
        return OfferPdfIngestResponse(
            extracted_text_chars=len(extracted_text),
            extracted_text=extracted_text if include_text else None,
            parsed=parsed_payload,
        )

    offer = Offer(
        user_id=user_id,
        role_title=parsed.role_title,
        level=parsed.level,
        location=parsed.location,
        base_salary=parsed.base_salary,
        bonus_target=parsed.bonus_target,
        equity_type=parsed.equity_type,
        equity_amount=parsed.equity_amount,
        vesting_schedule=parsed.vesting_schedule,
        start_date=parsed.start_date.date() if parsed.start_date else None,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    normalized_remote_preference = remote_preference.strip() if isinstance(remote_preference, str) else None
    if normalized_remote_preference == "":
        normalized_remote_preference = None

    survey_answers = {
        "ingest_source": "pdf",
        "ingest_filename": file.filename,
        "priority_financial": priority_financial,
        "priority_career": priority_career,
        "priority_lifestyle": priority_lifestyle,
        "priority_alignment": priority_alignment,
        "remote_preference": normalized_remote_preference,
        # Keep compatibility with existing workflow payload mapping.
        "role_fit": priority_alignment,
        "risk_flags": [],
    }
    survey = SurveyResponse(
        offer_id=offer.id,
        user_id=user_id,
        schema_version="1",
        answers_json=survey_answers,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    return OfferPdfIngestResponse(
        offer_id=offer.id,
        survey_response_id=survey.id,
        extracted_text_chars=len(extracted_text),
        extracted_text=extracted_text if include_text else None,
        parsed=parsed_payload,
    )


def _workflow_payload_from_offer(offer: Offer, survey: SurveyResponse | None) -> dict:
    answers = survey.answers_json if survey and isinstance(survey.answers_json, dict) else {}
    years_exp = answers.get("years_exp", answers.get("years_experience", 0))
    try:
        years_exp = int(years_exp)
    except (TypeError, ValueError):
        years_exp = 0

    remote_status = answers.get("remote_status") or answers.get("remote_preference") or "Hybrid"

    user_priorities = {
        "role_fit": answers.get("role_fit"),
        "risk_flags": answers.get("risk_flags", []),
        "relocation_flexibility": answers.get("relocation_flexibility"),
        "remote_preference": remote_status,
        "priority_financial": answers.get("priority_financial"),
        "priority_career": answers.get("priority_career"),
        "priority_lifestyle": answers.get("priority_lifestyle"),
        "priority_alignment": answers.get("priority_alignment"),
    }
    return {
        "job_title": offer.role_title or "Unknown",
        "industry": answers.get("industry", "Unknown"),
        "company_tier": answers.get("company_tier", offer.level or "Unknown"),
        "location": offer.location or "Unknown",
        "base_salary": float(offer.base_salary or 0),
        "bonus_pct": float(offer.bonus_target or 0),
        "equity_val": float(offer.equity_amount or 0),
        "signing_bonus": float(answers.get("signing_bonus", 0) or 0),
        "years_exp": years_exp,
        "remote_status": remote_status,
        "user_priorities": user_priorities,
    }


def _extract_workflow_result(workflow_output) -> dict:
    if hasattr(workflow_output, "result"):
        return workflow_output.result if isinstance(workflow_output.result, dict) else {}
    if isinstance(workflow_output, dict):
        result = workflow_output.get("result")
        return result if isinstance(result, dict) else {}
    return {}


def _chat_context_from_offer(offer: Offer, survey: SurveyResponse | None) -> dict:
    answers = survey.answers_json if survey and isinstance(survey.answers_json, dict) else {}
    return {
        "offer": {
            "role_title": offer.role_title,
            "level": offer.level,
            "location": offer.location,
            "base_salary": offer.base_salary,
            "bonus_target": offer.bonus_target,
            "equity_type": offer.equity_type,
            "equity_amount": offer.equity_amount,
            "vesting_schedule": offer.vesting_schedule,
        },
        "user_priorities": {
            "priority_financial": answers.get("priority_financial"),
            "priority_career": answers.get("priority_career"),
            "priority_lifestyle": answers.get("priority_lifestyle"),
            "priority_alignment": answers.get("priority_alignment"),
            "remote_preference": answers.get("remote_preference"),
            "risk_flags": answers.get("risk_flags", []),
        },
    }


@app.get("/offers/{offer_id}/market-snapshot", response_model=MarketSnapshotResponse)
def offer_market_snapshot(
    offer_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MarketSnapshotResponse:
    offer = db.execute(select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    survey = db.execute(
        select(SurveyResponse)
        .where(SurveyResponse.offer_id == offer_id, SurveyResponse.user_id == user_id)
        .order_by(SurveyResponse.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    payload = _workflow_payload_from_offer(offer, survey)

    try:
        state = OfferWorkflowState(**payload)
        state = asyncio.run(DatabricksNode()(state))
        market_data = state.market_data or {}
        return MarketSnapshotResponse.model_validate(market_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "MARKET_SNAPSHOT_INVALID", "message": str(exc)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "MARKET_SNAPSHOT_FAILURE", "message": str(exc)},
        ) from exc


@app.post("/offers/{offer_id}/evaluate", response_model=EvaluationOutput)
def evaluate_offer_endpoint(
    offer_id: int,
    request: Request,
    force: bool = Query(default=False),
    mode: str = Query(default=os.getenv("EVALUATION_MODE_DEFAULT", "engine")),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> EvaluationOutput:
    if mode not in {"engine", "workflow"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be 'engine' or 'workflow'")

    offer = db.execute(select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    if mode == "engine":
        latest = get_latest_evaluation(db, offer_id, user_id)
        if latest and is_recent(latest) and not force:
            return _evaluation_from_row(latest)

    if mode == "workflow":
        if run_offer_workflow is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow mode unavailable: missing workflow dependencies",
            )

        survey = db.execute(
            select(SurveyResponse)
            .where(SurveyResponse.offer_id == offer_id, SurveyResponse.user_id == user_id)
            .order_by(SurveyResponse.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        payload = _workflow_payload_from_offer(offer, survey)
        try:
            workflow_state = asyncio.run(run_offer_workflow(payload))
            workflow_result = _extract_workflow_result(workflow_state)
            if workflow_result.get("error"):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"error_code": "WORKFLOW_ERROR", "message": workflow_result["error"]},
                )
            return EvaluationOutput.model_validate(workflow_result)
        except HTTPException:
            raise
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error_code": "WORKFLOW_INVALID_OUTPUT", "message": str(exc)},
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error_code": "WORKFLOW_FAILURE", "message": str(exc)},
            ) from exc

    req_id = request.headers.get("X-Request-Id") or str(uuid4())
    try:
        return evaluate_offer(db=db, offer_id=offer_id, user_id=user_id, request_id=req_id)
    except LLMInvalidJSONError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_INVALID_JSON", "request_id": req_id, "message": str(exc)},
        ) from exc
    except LLMAuthFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_AUTH_FAILED", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMModelUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_MODEL_UNAVAILABLE", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMBadRequest as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_UPSTREAM_BAD_REQUEST", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "LLM_RATE_LIMITED", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMUpstreamUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "LLM_UPSTREAM_UNAVAILABLE", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": exc.error_code, "request_id": req_id, "message": exc.message},
        ) from exc


@app.post("/offers/{offer_id}/chat", response_model=OfferChatResponse)
def chat_about_offer(
    offer_id: int,
    payload: OfferChatRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OfferChatResponse:
    offer = db.execute(select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    survey = db.execute(
        select(SurveyResponse)
        .where(SurveyResponse.offer_id == offer_id, SurveyResponse.user_id == user_id)
        .order_by(SurveyResponse.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    context = _chat_context_from_offer(offer, survey)

    messages = [
        {
            "role": "system",
            "content": (
                "You are OfferGo's negotiation copilot. Answer with practical, specific guidance "
                "grounded only in the provided offer context and user priorities. "
                "Return JSON only in this shape: {\"answer\": \"...\"}. "
                "Keep the answer concise and actionable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Offer context: {context}\n"
                f"User question: {payload.message}"
            ),
        },
    ]

    req_id = request.headers.get("X-Request-Id") or str(uuid4())
    try:
        llm_json = nemotron_chat(messages)
        answer = llm_json.get("answer") if isinstance(llm_json, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise LLMInvalidJSONError(error_code="LLM_INVALID_JSON", message="Chat response missing 'answer'")
        return OfferChatResponse(answer=answer.strip())
    except LLMInvalidJSONError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_INVALID_JSON", "request_id": req_id, "message": str(exc)},
        ) from exc
    except LLMAuthFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_AUTH_FAILED", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMModelUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_MODEL_UNAVAILABLE", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMBadRequest as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "LLM_UPSTREAM_BAD_REQUEST", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "LLM_RATE_LIMITED", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMUpstreamUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "LLM_UPSTREAM_UNAVAILABLE", "request_id": req_id, "message": exc.message},
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": exc.error_code, "request_id": req_id, "message": exc.message},
        ) from exc


@app.get("/offers/{offer_id}/evaluation", response_model=EvaluationOutput)
def get_offer_evaluation(
    offer_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> EvaluationOutput:
    offer = db.execute(select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    latest = get_latest_evaluation(db, offer_id, user_id)
    if not latest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    return EvaluationOutput(
        score=latest.score,
        recommendation=latest.recommendation,
        confidence=latest.confidence,
        key_drivers=latest.key_drivers_json,
        negotiation_targets=latest.negotiation_targets_json,
        risks=latest.risks_json,
        followup_questions=latest.followup_questions_json,
        one_paragraph_summary=latest.summary_text,
    )
