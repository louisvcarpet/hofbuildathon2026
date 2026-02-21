import os
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Offer, SurveyResponse


def _seed_offer_and_survey():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.execute(delete(SurveyResponse))
        db.execute(delete(Offer))
        db.commit()

        offer = Offer(
            user_id=42,
            role_title="Backend Engineer",
            level="senior",
            location="SF",
            base_salary=210000,
            bonus_target=15,
            equity_type="RSU",
            equity_amount=100000,
            vesting_schedule="4y/1y cliff",
            start_date=date(2026, 3, 1),
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)

        survey = SurveyResponse(
            offer_id=offer.id,
            user_id=42,
            schema_version="1",
            answers_json={"role_fit": 4, "risk_flags": []},
        )
        db.add(survey)
        db.commit()
        return offer.id


def test_evaluate_offer_with_stubs_returns_schema_exact():
    os.environ["USE_COMP_STUB"] = "true"
    os.environ["USE_LLM_STUB"] = "true"

    offer_id = _seed_offer_and_survey()
    client = TestClient(app)

    response = client.post(f"/offers/{offer_id}/evaluate", headers={"X-User-Id": "42"})
    assert response.status_code == 200, response.text

    body = response.json()
    assert set(body.keys()) == {
        "score",
        "recommendation",
        "confidence",
        "key_drivers",
        "negotiation_targets",
        "risks",
        "followup_questions",
        "one_paragraph_summary",
    }
    assert isinstance(body["score"], float)
    assert body["recommendation"] in {"accept", "renegotiate", "needs_more_info"}
    assert isinstance(body["key_drivers"], list)
    assert len(body["key_drivers"]) >= 3

    get_response = client.get(f"/offers/{offer_id}/evaluation", headers={"X-User-Id": "42"})
    assert get_response.status_code == 200
    assert get_response.json()["score"] == body["score"]
