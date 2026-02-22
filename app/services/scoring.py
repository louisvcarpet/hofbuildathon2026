from app.models import Offer, SurveyResponse
from app.schemas import ScoreBreakdown, ScorePayload

SCORING_VERSION = "v1"


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score_offer(offer: Offer, survey: SurveyResponse, comps: dict) -> ScorePayload:
    missing_fields: list[str] = []
    answers = survey.answers_json or {}

    for key in ("role_title", "level", "location", "base_salary", "vesting_schedule"):
        if getattr(offer, key, None) in (None, "", 0):
            missing_fields.append(key)

    p25 = float(comps.get("p25", 0) or 0)
    median = float(comps.get("median", 0) or 0)
    p75 = float(comps.get("p75", 0) or 0)
    sample_size = int(comps.get("sample_size", 0) or 0)

    base_salary = float(offer.base_salary or 0)
    bonus_target = float(offer.bonus_target or 0)
    equity_amount = float(offer.equity_amount or 0)

    salary_score = 2.0
    if median > 0 and base_salary > 0:
        if base_salary < p25:
            salary_score = 1.0
        elif base_salary <= median:
            salary_score = 2.5
        elif base_salary <= p75:
            salary_score = 3.4
        else:
            salary_score = 4.0
    elif median == 0:
        missing_fields.append("market_comps")
    else:
        missing_fields.append("base_salary")

    # Bonus assumes percent target (e.g. 15 for 15%).
    bonus_score = _clamp(bonus_target / 15.0, 0.0, 1.5)
    if bonus_target <= 0:
        missing_fields.append("bonus_target")

    equity_score = _clamp(equity_amount / 80_000.0, 0.0, 2.0)
    if equity_amount <= 0:
        missing_fields.append("equity_amount")

    fit_raw = float(answers.get("role_fit", 3) or 3)
    fit_score = _clamp((fit_raw / 5.0) * 2.5, 0.5, 2.5)
    if "role_fit" not in answers:
        missing_fields.append("survey.role_fit")

    risk_flags = answers.get("risk_flags", [])
    risk_count = len(risk_flags) if isinstance(risk_flags, list) else 0
    risk_penalty = _clamp(risk_count * 0.4, 0.0, 2.0)

    raw_score = salary_score + bonus_score + equity_score + fit_score - risk_penalty
    score = round(_clamp(raw_score, 0.0, 10.0), 1)

    confidence = 0.9
    confidence -= min(0.4, 0.05 * len(set(missing_fields)))
    if sample_size < 30:
        confidence -= 0.2
    if sample_size == 0:
        confidence -= 0.1
    confidence = round(_clamp(confidence, 0.1, 0.99), 2)

    breakdown = ScoreBreakdown(
        salary=round(salary_score, 2),
        bonus=round(bonus_score, 2),
        equity=round(equity_score, 2),
        fit=round(fit_score, 2),
        risk_penalty=round(risk_penalty, 2),
    )
    return ScorePayload(
        score=score,
        breakdown=breakdown,
        confidence=confidence,
        missing_fields=sorted(set(missing_fields)),
    )
