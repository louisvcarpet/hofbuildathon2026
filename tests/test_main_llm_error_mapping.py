from datetime import date

from fastapi.testclient import TestClient
import requests
from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Evaluation, Offer, SurveyResponse
from app.services.llm_exceptions import (
    LLMAuthFailed,
    LLMInvalidJSONError,
    LLMRateLimited,
    LLMUpstreamUnavailable,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = "ok"):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def _seed_offer():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.execute(delete(Evaluation))
        db.execute(delete(SurveyResponse))
        db.execute(delete(Offer))
        db.commit()
        offer = Offer(
            user_id=42,
            role_title="Backend Engineer",
            level="senior",
            location="SF",
            base_salary=200000,
            bonus_target=10,
            equity_type="RSU",
            equity_amount=100000,
            vesting_schedule="4y/1y cliff",
            start_date=date(2026, 3, 1),
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)
        return offer.id


def _seed_offer_with_survey():
    offer_id = _seed_offer()
    with SessionLocal() as db:
        survey = SurveyResponse(
            offer_id=offer_id,
            user_id=42,
            schema_version="1",
            answers_json={"role_fit": 4, "risk_flags": []},
        )
        db.add(survey)
        db.commit()
    return offer_id


def test_llm_invalid_json_maps_to_502(monkeypatch):
    offer_id = _seed_offer()
    client = TestClient(app)

    def _raise(**kwargs):
        raise LLMInvalidJSONError(error_code="LLM_INVALID_JSON", message="bad json")

    monkeypatch.setattr("app.main.evaluate_offer", _raise)
    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert res.status_code == 502
    assert res.json()["detail"]["error_code"] == "LLM_INVALID_JSON"
    assert "request_id" in res.json()["detail"]


def test_llm_auth_failed_maps_to_502(monkeypatch):
    offer_id = _seed_offer()
    client = TestClient(app)

    def _raise(**kwargs):
        raise LLMAuthFailed(error_code="LLM_AUTH_FAILED", message="auth failed", upstream_status=401)

    monkeypatch.setattr("app.main.evaluate_offer", _raise)
    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert res.status_code == 502
    assert res.json()["detail"]["error_code"] == "LLM_AUTH_FAILED"


def test_llm_rate_limited_maps_to_503(monkeypatch):
    offer_id = _seed_offer()
    client = TestClient(app)

    def _raise(**kwargs):
        raise LLMRateLimited(error_code="LLM_RATE_LIMITED", message="rate limited", upstream_status=429)

    monkeypatch.setattr("app.main.evaluate_offer", _raise)
    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert res.status_code == 503
    assert res.json()["detail"]["error_code"] == "LLM_RATE_LIMITED"


def test_llm_upstream_unavailable_maps_to_503(monkeypatch):
    offer_id = _seed_offer()
    client = TestClient(app)

    def _raise(**kwargs):
        raise LLMUpstreamUnavailable(error_code="LLM_UPSTREAM_UNAVAILABLE", message="timeout")

    monkeypatch.setattr("app.main.evaluate_offer", _raise)
    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert res.status_code == 503
    assert res.json()["detail"]["error_code"] == "LLM_UPSTREAM_UNAVAILABLE"


def test_timeout_from_nemotron_client_maps_to_503(monkeypatch):
    offer_id = _seed_offer_with_survey()
    client = TestClient(app)
    monkeypatch.setenv("USE_LLM_STUB", "false")
    monkeypatch.setenv("NIM_API_KEY", "test-key")
    monkeypatch.setenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("NIM_MODEL", "nvidia/nvidia-nemotron-nano-9b-v2")

    def _timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr("app.services.nemotron_client.requests.post", _timeout)
    monkeypatch.setattr("app.services.nemotron_client.time.sleep", lambda _: None)

    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert res.status_code == 503
    assert res.json()["detail"]["error_code"] == "LLM_UPSTREAM_UNAVAILABLE"


def test_malformed_json_retries_once_then_maps_to_502(monkeypatch):
    offer_id = _seed_offer_with_survey()
    client = TestClient(app)
    monkeypatch.setenv("USE_LLM_STUB", "false")
    monkeypatch.setenv("NIM_API_KEY", "test-key")
    monkeypatch.setenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("NIM_MODEL", "nvidia/nvidia-nemotron-nano-9b-v2")

    calls = {"count": 0}

    def _bad_json(*args, **kwargs):
        calls["count"] += 1
        payload = {"choices": [{"message": {"content": "not valid json response"}}]}
        return _FakeResponse(status_code=200, payload=payload)

    monkeypatch.setattr("app.services.nemotron_client.requests.post", _bad_json)

    res = client.post(f"/offers/{offer_id}/evaluate?force=true", headers={"X-User-Id": "42"})
    assert calls["count"] == 2
    assert res.status_code == 502
    assert res.json()["detail"]["error_code"] == "LLM_INVALID_JSON"
