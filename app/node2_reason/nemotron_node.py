import json
import os

from pydantic import ValidationError

from app.schemas import EvaluationOutput, RecommendationEnum
from app.services.llm_exceptions import LLMError, LLMInvalidJSONError
from app.services.nemotron_client import nemotron_chat


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _missing_fields(state) -> list[str]:
    missing: list[str] = []
    if not state.job_title or state.job_title == "Unknown":
        missing.append("job_title")
    if not state.industry or state.industry == "Unknown":
        missing.append("industry")
    if _safe_float(state.base_salary) <= 0:
        missing.append("base_salary")
    if _safe_float(state.equity_val) <= 0:
        missing.append("equity_val")
    return missing


def _deterministic_score_payload(state, market: dict) -> dict:
    ratio = _safe_float(market.get("offer_vs_market_ratio", 1.0), 1.0)
    sample = int(_safe_float(market.get("sample_size", 0), 0))
    missing = _missing_fields(state)

    salary_score = max(0.0, min(4.5, 3.0 + (ratio - 1.0) * 5.0))
    bonus_score = max(0.0, min(1.5, (_safe_float(state.bonus_pct) / 20.0) * 1.5))
    equity_score = max(0.0, min(2.0, (_safe_float(state.equity_val) / 120000.0) * 2.0))
    fit_score = max(0.0, min(1.5, 1.0 if state.years_exp >= 3 else 0.6))
    risk_penalty = min(2.0, 0.25 * len(missing) + (0.7 if sample < 3 else 0.0))

    score = max(0.0, min(10.0, salary_score + bonus_score + equity_score + fit_score - risk_penalty))
    confidence = max(0.3, min(0.9, 0.45 + min(sample, 30) / 100.0 - 0.05 * len(missing)))

    return {
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "missing_fields": missing,
        "breakdown": {
            "salary": round(salary_score, 2),
            "bonus": round(bonus_score, 2),
            "equity": round(equity_score, 2),
            "fit": round(fit_score, 2),
            "risk_penalty": round(risk_penalty, 2),
        },
    }


def _build_messages(packet: dict) -> list[dict]:
    schema_hint = {
        "score": "float (0..10)",
        "recommendation": "accept|renegotiate|needs_more_info",
        "confidence": "float (0..1)",
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
                "You are an offer evaluation assistant. Output JSON only, no markdown. "
                "Use the packet fields exactly. Do not invent market stats. "
                "Keep score/confidence equal to score_payload.score/confidence. "
                "If market sample is low or critical fields are missing, set recommendation to needs_more_info. "
                "Always provide clear, actionable negotiation guidance in negotiation_targets. "
                "If recommendation is renegotiate or needs_more_info, include at least 2 concrete asks "
                "with rationale tied to market stats or missing-risk items. "
                f"Return this exact shape: {json.dumps(schema_hint)}"
            ),
        },
        {"role": "user", "content": json.dumps(packet)},
    ]


def _deterministic_fallback(state, market: dict, score_payload: dict, error_msg: str) -> dict:
    ratio = _safe_float(market.get("offer_vs_market_ratio", 1.0), 1.0)
    sample = int(_safe_float(market.get("sample_size", 0), 0))
    offer_total = _safe_float(market.get("offer_total_est", 0.0))
    market_total = _safe_float(market.get("market_total_est", 0.0))
    delta = round(offer_total - market_total, 2)

    if score_payload["missing_fields"] or sample < 3:
        recommendation = RecommendationEnum.needs_more_info.value
    elif ratio >= 1.05:
        recommendation = RecommendationEnum.accept.value
    else:
        recommendation = RecommendationEnum.renegotiate.value

    return {
        "score": score_payload["score"],
        "recommendation": recommendation,
        "confidence": score_payload["confidence"],
        "key_drivers": [
            {"label": f"Total compensation delta vs market estimate: {delta}", "impact": "positive" if delta >= 0 else "negative"},
            {"label": f"Matched market sample size: {sample}", "impact": "neutral" if sample >= 3 else "negative"},
            {"label": f"Fallback reason: {error_msg[:120]}", "impact": "neutral"},
        ],
        "negotiation_targets": [
            {
                "item": "Base salary",
                "ask": "Increase base salary toward benchmark median.",
                "reason": "Cash compensation usually has strongest immediate upside.",
            }
        ],
        "risks": ["LLM unavailable or invalid output; using deterministic fallback response."],
        "followup_questions": [
            "Can you confirm vesting schedule details and any acceleration clauses?",
            "What exact bonus formula and payout timeline applies for year one?",
        ],
        "one_paragraph_summary": (
            f"Generated with deterministic fallback because Nemotron reasoning was unavailable. "
            f"Offer total estimate is {offer_total:,.0f} versus market estimate {market_total:,.0f}; "
            f"ratio={ratio:.2f}, sample_size={sample}."
        )[:600],
    }


class NemotronNode:
    """Reasoning node that calls Nemotron with schema validation + fallback."""

    async def __call__(self, state):
        state.tryout += 1
        market = state.market_data or {}
        score_payload = _deterministic_score_payload(state, market)

        packet = {
            "offer": {
                "job_title": state.job_title,
                "industry": state.industry,
                "company_tier": state.company_tier,
                "location": state.location,
                "base_salary": state.base_salary,
                "bonus_pct": state.bonus_pct,
                "equity_val": state.equity_val,
                "signing_bonus": state.signing_bonus,
                "years_exp": state.years_exp,
                "remote_status": state.remote_status,
            },
            "market_comps_stats": market,
            "score_payload": score_payload,
            "user_priorities": state.user_priorities or {},
        }

        use_nemotron = os.getenv("WORKFLOW_USE_NEMOTRON", "true").lower() == "true"
        if not use_nemotron:
            state.llm_response = _deterministic_fallback(state, market, score_payload, "WORKFLOW_USE_NEMOTRON=false")
            return state

        messages = _build_messages(packet)
        try:
            first = nemotron_chat(messages)
            first["score"] = score_payload["score"]
            first["confidence"] = score_payload["confidence"]
            output = EvaluationOutput.model_validate(first)
        except (LLMInvalidJSONError, ValidationError, KeyError, TypeError) as first_err:
            fix_prompt = messages + [
                {
                    "role": "user",
                    "content": "Your output was invalid. Re-emit valid JSON only with the required schema.",
                }
            ]
            try:
                second = nemotron_chat(fix_prompt)
                second["score"] = score_payload["score"]
                second["confidence"] = score_payload["confidence"]
                output = EvaluationOutput.model_validate(second)
            except (LLMInvalidJSONError, ValidationError, KeyError, TypeError, LLMError) as second_err:
                state.llm_response = _deterministic_fallback(state, market, score_payload, str(second_err))
                return state
        except LLMError as llm_err:
            state.llm_response = _deterministic_fallback(state, market, score_payload, str(llm_err))
            return state

        if score_payload["missing_fields"] or int(_safe_float(market.get("sample_size", 0), 0)) < 3:
            output.recommendation = RecommendationEnum.needs_more_info

        # Enforce practical guidance quality regardless of model variance.
        if output.recommendation in {
            RecommendationEnum.renegotiate,
            RecommendationEnum.needs_more_info,
        } and len(output.negotiation_targets) < 2:
            output.negotiation_targets = [
                {
                    "item": "Base salary",
                    "ask": "Request adjustment toward or above market median.",
                    "reason": "Cash compensation is the most reliable way to close market delta.",
                },
                {
                    "item": "Signing bonus",
                    "ask": "Request a one-time signing bonus to offset immediate compensation gap.",
                    "reason": "Helps bridge near-term difference while longer-term comp is reviewed.",
                },
            ]

        if output.recommendation == RecommendationEnum.accept and not output.negotiation_targets:
            output.negotiation_targets = [
                {
                    "item": "Offer terms confirmation",
                    "ask": "Confirm vesting schedule, bonus conditions, and remote policy in writing.",
                    "reason": "Reduces ambiguity and protects expected value after acceptance.",
                }
            ]

        state.llm_response = output.model_dump(mode="json")
        return state
