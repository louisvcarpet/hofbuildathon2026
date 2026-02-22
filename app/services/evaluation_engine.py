import json
import logging
import os
import time
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Evaluation, Offer, SurveyResponse
from app.schemas import EvaluationOutput, RecommendationEnum
from app.services.databricks_service import get_market_comps
from app.services.llm_exceptions import LLMInvalidJSONError
from app.services.nemotron_client import nemotron_chat
from app.services.scoring import SCORING_VERSION, score_offer
from app.utils.redaction import redact_money_values, redact_pii_strings

logger = logging.getLogger(__name__)
MODEL_VERSION_FALLBACK = "nemotron-unknown"
LLM_SURVEY_ALLOWLIST = {"role_fit", "risk_flags", "relocation_flexibility", "remote_preference"}


def _evaluation_from_row(row: Evaluation) -> EvaluationOutput:
    return EvaluationOutput(
        score=round(float(row.score), 1),
        recommendation=row.recommendation,
        confidence=float(row.confidence),
        key_drivers=row.key_drivers_json,
        negotiation_targets=row.negotiation_targets_json,
        risks=row.risks_json,
        followup_questions=row.followup_questions_json,
        one_paragraph_summary=row.summary_text,
    )


def get_latest_evaluation(db: Session, offer_id: int, user_id: int) -> Evaluation | None:
    return db.execute(
        select(Evaluation)
        .where(Evaluation.offer_id == offer_id, Evaluation.user_id == user_id)
        .order_by(desc(Evaluation.created_at))
        .limit(1)
    ).scalar_one_or_none()


def is_recent(evaluation: Evaluation, max_age_minutes: int = 60) -> bool:
    return evaluation.created_at >= datetime.utcnow() - timedelta(minutes=max_age_minutes)


def _get_offer_and_survey(db: Session, offer_id: int, user_id: int) -> tuple[Offer, SurveyResponse]:
    offer = db.execute(
        select(Offer).where(Offer.id == offer_id, Offer.user_id == user_id).limit(1)
    ).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    survey = db.execute(
        select(SurveyResponse)
        .where(SurveyResponse.offer_id == offer_id, SurveyResponse.user_id == user_id)
        .order_by(desc(SurveyResponse.created_at))
        .limit(1)
    ).scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey response not found")
    return offer, survey


def _build_messages(packet: dict) -> list[dict]:
    schema_hint = {
        "score": "float",
        "recommendation": "accept|renegotiate|needs_more_info",
        "confidence": "float",
        "key_drivers": [{"label": "str", "impact": "positive|negative|neutral"}],
        "negotiation_targets": [{"item": "str", "ask": "str", "reason": "str"}],
        "risks": ["str"],
        "followup_questions": ["str"],
        "one_paragraph_summary": "str <= 600 chars",
    }
    return [
        {
            "role": "system",
            "content": (
                "You are an offer evaluation assistant. Output JSON ONLY with no markdown and no extra text. "
                "Do not invent numbers that are not provided. Do not change score/confidence; use provided values. "
                "If missing critical fields OR comps sample_size is too small, set recommendation to "
                "\"needs_more_info\". Ground advice in comps and score breakdown. If info is missing, include followup questions. "
                f"Return exactly this shape: {json.dumps(schema_hint)}"
            ),
        },
        {"role": "user", "content": json.dumps(packet)},
    ]


def _bucket_comp_median(median: float | None) -> str:
    if not median:
        return "unknown"
    if median < 100_000:
        return "<100k"
    if median < 200_000:
        return "100k-200k"
    if median < 300_000:
        return "200k-300k"
    return "300k+"


def filter_survey_for_llm(answers_json: dict | None) -> dict:
    if not isinstance(answers_json, dict):
        return {}
    filtered: dict = {}
    for key in LLM_SURVEY_ALLOWLIST:
        if key not in answers_json:
            continue
        value = answers_json[key]
        if isinstance(value, str):
            filtered[key] = redact_pii_strings(value)
        elif isinstance(value, list):
            scrubbed_list = [redact_pii_strings(item) if isinstance(item, str) else item for item in value]
            filtered[key] = scrubbed_list
        elif isinstance(value, dict):
            # Nested survey maps are allowed only after redaction.
            filtered[key] = redact_money_values(value)
        else:
            filtered[key] = value
    return filtered


def _coerce_and_validate(model_json: dict, locked_score: float, locked_confidence: float) -> EvaluationOutput:
    model_json["score"] = locked_score
    model_json["confidence"] = locked_confidence
    return EvaluationOutput.model_validate(model_json)


def _call_llm_with_retry(messages: list[dict], score: float, confidence: float) -> EvaluationOutput:
    try:
        first = nemotron_chat(messages)
        return _coerce_and_validate(first, score, confidence)
    except (LLMInvalidJSONError, json.JSONDecodeError, ValidationError, KeyError, TypeError) as first_err:
        fix_prompt = messages + [
            {
                "role": "user",
                "content": (
                    "Your prior output was invalid. Re-emit valid JSON only, matching the required schema exactly. "
                    "No prose, no markdown."
                ),
            }
        ]
        try:
            second = nemotron_chat(fix_prompt)
            return _coerce_and_validate(second, score, confidence)
        except (LLMInvalidJSONError, json.JSONDecodeError, ValidationError, KeyError, TypeError) as second_err:
            raise LLMInvalidJSONError(
                error_code="LLM_INVALID_JSON",
                message=f"Invalid JSON from LLM after retry: {second_err}",
            ) from first_err


def _apply_missing_info_followups(output: EvaluationOutput, missing_fields: list[str]) -> EvaluationOutput:
    followups = list(output.followup_questions)
    if "vesting_schedule" in missing_fields:
        followups.append("What is the exact vesting schedule, cliff, and acceleration policy for the equity grant?")

    # Keep deterministic and bounded by schema max.
    output.followup_questions = list(dict.fromkeys(followups))[:3]
    return output


def evaluate_offer(db: Session, offer_id: int, user_id: int, request_id: str | None = None) -> EvaluationOutput:
    req_id = request_id or str(uuid4())
    offer, survey = _get_offer_and_survey(db, offer_id, user_id)

    comps = get_market_comps(offer.role_title, offer.level, offer.location)
    score_payload = score_offer(offer, survey, comps)
    model_name = os.getenv("NIM_MODEL", MODEL_VERSION_FALLBACK)
    comps_summary = {
        "sample_size": int(comps.get("sample_size", 0) or 0),
        "median_bucket": _bucket_comp_median(comps.get("median")),
        "source": comps.get("source", "stub_or_unknown"),
    }
    logger.info(
        "evaluate_offer comps request_id=%s offer_id=%s model=%s comps_summary=%s",
        req_id,
        offer_id,
        model_name,
        comps_summary,
    )
    logger.info(
        "evaluate_offer score_summary request_id=%s offer_id=%s model=%s score=%.1f confidence=%.2f missing_fields_count=%s",
        req_id,
        offer_id,
        model_name,
        score_payload.score,
        score_payload.confidence,
        len(score_payload.missing_fields),
    )

    packet = {
        "offer": {
            "role_title": offer.role_title,
            "level": offer.level,
            "location": offer.location,
            "base_salary": offer.base_salary,
            "bonus_target": offer.bonus_target,
            "equity_type": offer.equity_type,
            "equity_amount": offer.equity_amount,
            "vesting_schedule": offer.vesting_schedule,
            "start_date": offer.start_date.isoformat() if offer.start_date else None,
        },
        "survey_answers": filter_survey_for_llm(survey.answers_json or {}),
        "comps_stats": comps,
        "score_payload": score_payload.model_dump(),
    }
    logger.info(
        "evaluate_offer llm_packet_summary request_id=%s offer_id=%s model=%s survey_keys=%s missing_fields_count=%s",
        req_id,
        offer_id,
        model_name,
        sorted(packet["survey_answers"].keys()),
        len(score_payload.missing_fields),
    )
    messages = _build_messages(packet)

    start = time.perf_counter()
    llm_output = _call_llm_with_retry(messages, score_payload.score, score_payload.confidence)
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "evaluate_offer llm_success request_id=%s offer_id=%s model=%s latency_ms=%s",
        req_id,
        offer_id,
        model_name,
        latency_ms,
    )

    if score_payload.missing_fields or int(comps.get("sample_size", 0)) < 30:
        llm_output.recommendation = RecommendationEnum.needs_more_info
    llm_output = _apply_missing_info_followups(llm_output, score_payload.missing_fields)

    model_version = model_name
    evaluation = Evaluation(
        offer_id=offer.id,
        user_id=user_id,
        score=round(score_payload.score, 1),
        confidence=score_payload.confidence,
        missing_fields_json=score_payload.missing_fields,
        score_breakdown_json=score_payload.breakdown.model_dump(),
        key_drivers_json=[d.model_dump() for d in llm_output.key_drivers],
        negotiation_targets_json=[t.model_dump() for t in llm_output.negotiation_targets],
        risks_json=llm_output.risks,
        summary_text=llm_output.one_paragraph_summary,
        model_version=model_version or MODEL_VERSION_FALLBACK,
        scoring_version=SCORING_VERSION,
        recommendation=llm_output.recommendation.value,
        followup_questions_json=llm_output.followup_questions,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_from_row(evaluation)
