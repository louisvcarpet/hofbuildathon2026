from datetime import datetime

from app.models import Offer, SurveyResponse
from app.services.scoring import score_offer


def _offer(**kwargs) -> Offer:
    return Offer(
        id=1,
        user_id=1,
        role_title=kwargs.get("role_title", "Backend Engineer"),
        level=kwargs.get("level", "senior"),
        location=kwargs.get("location", "SF"),
        base_salary=kwargs.get("base_salary", 220000),
        bonus_target=kwargs.get("bonus_target", 15),
        equity_type=kwargs.get("equity_type", "RSU"),
        equity_amount=kwargs.get("equity_amount", 120000),
        vesting_schedule=kwargs.get("vesting_schedule", "4y/1y cliff"),
        start_date=kwargs.get("start_date"),
        created_at=datetime.utcnow(),
    )


def _survey(answers: dict | None = None) -> SurveyResponse:
    return SurveyResponse(
        id=1,
        offer_id=1,
        user_id=1,
        schema_version="1",
        answers_json=answers or {"role_fit": 4, "risk_flags": []},
        created_at=datetime.utcnow(),
    )


def test_score_offer_high_comp_offer_scores_well():
    payload = score_offer(
        _offer(),
        _survey(),
        {"p25": 150000, "median": 200000, "p75": 240000, "sample_size": 60},
    )
    assert payload.score >= 7.5
    assert payload.confidence >= 0.8
    assert payload.breakdown.salary >= 3.0
    assert payload.missing_fields == []


def test_score_offer_missing_data_reduces_confidence():
    payload = score_offer(
        _offer(base_salary=None, bonus_target=0, equity_amount=0, role_title=None),
        _survey(answers={"risk_flags": ["commute"], "role_fit": 3}),
        {"sample_size": 0},
    )
    assert payload.score <= 6.0
    assert payload.confidence <= 0.6
    assert "role_title" in payload.missing_fields
    assert "market_comps" in payload.missing_fields


def test_score_offer_same_input_same_score():
    offer = _offer()
    survey = _survey()
    comps = {"p25": 150000, "median": 200000, "p75": 240000, "sample_size": 60}

    payload_1 = score_offer(offer, survey, comps)
    payload_2 = score_offer(offer, survey, comps)

    assert payload_1.score == payload_2.score
    assert payload_1.confidence == payload_2.confidence
    assert payload_1.breakdown.model_dump() == payload_2.breakdown.model_dump()


def test_missing_vesting_lowers_confidence():
    complete_offer = _offer(vesting_schedule="4y/1y cliff")
    missing_vesting_offer = _offer(vesting_schedule=None)
    survey = _survey(answers={"risk_flags": [], "role_fit": 4})
    comps = {"p25": 150000, "median": 200000, "p75": 240000, "sample_size": 60}

    complete = score_offer(complete_offer, survey, comps)
    missing = score_offer(missing_vesting_offer, survey, comps)

    assert "vesting_schedule" in missing.missing_fields
    assert missing.confidence < complete.confidence
