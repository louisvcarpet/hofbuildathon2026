import logging
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.database import Base, engine, get_db
from app.models import Offer
from app.schemas import EvaluationOutput
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

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Offer Evaluation MVP")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.post("/offers/{offer_id}/evaluate", response_model=EvaluationOutput)
def evaluate_offer_endpoint(
    offer_id: int,
    request: Request,
    force: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> EvaluationOutput:
    offer = db.execute(select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    latest = get_latest_evaluation(db, offer_id, user_id)
    if latest and is_recent(latest) and not force:
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
