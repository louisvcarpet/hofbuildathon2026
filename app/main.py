import asyncio
import logging
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import Base, engine, get_db
from app.models import Offer, SurveyResponse
from app.schemas import EvaluationOutput
from app.services.evaluation_engine import _evaluation_from_row
from app.services.evaluation_engine import (
    evaluate_offer,
    get_latest_evaluation,
    is_recent,
)
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


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def _workflow_payload_from_offer(offer: Offer, survey: SurveyResponse | None) -> dict:
    answers = survey.answers_json if survey and isinstance(survey.answers_json, dict) else {}
    years_exp = answers.get("years_exp", answers.get("years_experience", 0))
    try:
        years_exp = int(years_exp)
    except (TypeError, ValueError):
        years_exp = 0

    user_priorities = {
        "role_fit": answers.get("role_fit"),
        "risk_flags": answers.get("risk_flags", []),
        "relocation_flexibility": answers.get("relocation_flexibility"),
        "remote_preference": answers.get("remote_preference", answers.get("remote_status")),
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
        "remote_status": answers.get("remote_status", answers.get("remote_preference", "Hybrid")),
        "user_priorities": user_priorities,
    }


def _extract_workflow_result(workflow_output) -> dict:
    if hasattr(workflow_output, "result"):
        return workflow_output.result if isinstance(workflow_output.result, dict) else {}
    if isinstance(workflow_output, dict):
        result = workflow_output.get("result")
        return result if isinstance(result, dict) else {}
    return {}


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
