from app.schemas import EvaluationOutput
from app.services.evaluation_engine import _apply_missing_info_followups, _call_llm_with_retry, filter_survey_for_llm
from app.services.llm_exceptions import LLMInvalidJSONError


def test_missing_vesting_adds_followup_question():
    output = EvaluationOutput(
        score=7.5,
        recommendation="needs_more_info",
        confidence=0.8,
        key_drivers=[
            {"label": "salary", "impact": "positive"},
            {"label": "bonus", "impact": "neutral"},
            {"label": "equity", "impact": "neutral"},
        ],
        negotiation_targets=[],
        risks=[],
        followup_questions=[],
        one_paragraph_summary="Test summary.",
    )

    updated = _apply_missing_info_followups(output, missing_fields=["vesting_schedule"])
    assert any("vesting schedule" in question.lower() for question in updated.followup_questions)


def test_filter_survey_for_llm_drops_unexpected_and_scrubs_pii():
    filtered = filter_survey_for_llm(
        {
            "role_fit": 4,
            "risk_flags": ["email me at test@example.com", "call me at (212) 555-1111"],
            "free_text_notes": "my email is hi@company.com",
            "user_id": "123",
        }
    )
    assert "free_text_notes" not in filtered
    assert "user_id" not in filtered
    assert filtered["role_fit"] == 4
    assert "[REDACTED_EMAIL]" in filtered["risk_flags"][0]
    assert "[REDACTED_PHONE]" in filtered["risk_flags"][1]


def test_call_llm_with_retry_raises_invalid_json_after_second_failure(monkeypatch):
    calls = {"count": 0}

    def _bad_chat(_messages):
        calls["count"] += 1
        return {"choices": []}

    monkeypatch.setattr("app.services.evaluation_engine.nemotron_chat", _bad_chat)
    try:
        _call_llm_with_retry([{"role": "user", "content": "{}"}], score=7.5, confidence=0.9)
        assert False, "Expected LLMInvalidJSONError"
    except LLMInvalidJSONError as exc:
        assert exc.error_code == "LLM_INVALID_JSON"
        assert calls["count"] == 2
