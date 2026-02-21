import requests

from app.services.llm_exceptions import LLMAuthFailed, LLMInvalidJSONError, LLMRateLimited, LLMUpstreamUnavailable
from app.services.nemotron_client import nemotron_chat


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _set_env(monkeypatch):
    monkeypatch.setenv("USE_LLM_STUB", "false")
    monkeypatch.setenv("NIM_API_KEY", "test-key")
    monkeypatch.setenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("NIM_MODEL", "nvidia/nvidia-nemotron-nano-9b-v2")


def test_timeout_retries_then_raises_upstream_unavailable(monkeypatch):
    _set_env(monkeypatch)
    calls = {"count": 0}

    def _timeout(*args, **kwargs):
        calls["count"] += 1
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr("app.services.nemotron_client.requests.post", _timeout)
    monkeypatch.setattr("app.services.nemotron_client.time.sleep", lambda _: None)

    try:
        nemotron_chat([{"role": "user", "content": "{}"}])
        assert False, "Expected LLMUpstreamUnavailable"
    except LLMUpstreamUnavailable as exc:
        assert exc.error_code == "LLM_UPSTREAM_UNAVAILABLE"
        assert calls["count"] == 3


def test_401_maps_to_llm_auth_failed(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setattr(
        "app.services.nemotron_client.requests.post",
        lambda *args, **kwargs: _FakeResponse(status_code=401, text="unauthorized"),
    )
    try:
        nemotron_chat([{"role": "user", "content": "{}"}])
        assert False, "Expected LLMAuthFailed"
    except LLMAuthFailed as exc:
        assert exc.error_code == "LLM_AUTH_FAILED"
        assert exc.upstream_status == 401


def test_429_maps_to_llm_rate_limited(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setattr(
        "app.services.nemotron_client.requests.post",
        lambda *args, **kwargs: _FakeResponse(status_code=429, text="rate limited"),
    )
    try:
        nemotron_chat([{"role": "user", "content": "{}"}])
        assert False, "Expected LLMRateLimited"
    except LLMRateLimited as exc:
        assert exc.error_code == "LLM_RATE_LIMITED"
        assert exc.upstream_status == 429


def test_malformed_content_raises_invalid_json(monkeypatch):
    _set_env(monkeypatch)
    payload = {
        "choices": [
            {
                "message": {
                    "content": "Not JSON output. score is 7.5 but no object.",
                }
            }
        ]
    }
    monkeypatch.setattr(
        "app.services.nemotron_client.requests.post",
        lambda *args, **kwargs: _FakeResponse(status_code=200, payload=payload, text="ok"),
    )
    try:
        nemotron_chat([{"role": "user", "content": "{}"}])
        assert False, "Expected LLMInvalidJSONError"
    except LLMInvalidJSONError as exc:
        assert exc.error_code == "LLM_INVALID_JSON"
