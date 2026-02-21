import json
import logging
import os
import random
import time
from typing import Any

import requests

from app.schemas import RecommendationEnum
from app.services.llm_exceptions import (
    LLMBadRequest,
    LLMAuthFailed,
    LLMInvalidJSONError,
    LLMModelUnavailable,
    LLMRateLimited,
    LLMUpstreamUnavailable,
)

logger = logging.getLogger(__name__)


def _stub_output() -> dict[str, Any]:
    return {
        "score": 7.2,
        "recommendation": RecommendationEnum.renegotiate.value,
        "confidence": 0.78,
        "key_drivers": [
            {"label": "Base salary vs market median", "impact": "positive"},
            {"label": "Equity package size", "impact": "neutral"},
            {"label": "Risk flags in priorities", "impact": "negative"},
        ],
        "negotiation_targets": [
            {
                "item": "Base salary",
                "ask": "Request 8-12% increase",
                "reason": "Package is below upper market band.",
            }
        ],
        "risks": ["Limited data on career growth path."],
        "followup_questions": ["Can you share level expectations for promotion in year one?"],
        "one_paragraph_summary": "The offer is competitive in some areas but leaves room to improve guaranteed cash and clarify growth expectations. Prioritize negotiating base salary and requesting concrete promotion criteria to reduce downside risk while preserving upside from variable compensation and equity.",
    }


def extract_first_json_object(text: str) -> str:
    stack: list[str] = []
    start = -1
    in_string = False
    escaped = False

    for idx, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char in "{[":
            if not stack:
                start = idx
            stack.append(char)
            continue

        if char in "}]":
            if not stack:
                continue
            opener = stack.pop()
            if (opener == "{" and char != "}") or (opener == "[" and char != "]"):
                raise ValueError("Mismatched JSON braces")
            if not stack and start >= 0:
                return text[start : idx + 1]

    raise ValueError("No JSON object/array found")


def _truncate_body(text: str, max_chars: int = 500) -> str:
    return text[:max_chars]


def _log_upstream_error(error_code: str, model: str, status: int | None, retry_count: int, upstream_body: str | None) -> None:
    logger.warning(
        "nemotron_error error_code=%s model=%s upstream_status=%s retry_count=%s upstream_body=%s",
        error_code,
        model,
        status,
        retry_count,
        upstream_body,
    )


def _extract_message_content(data: dict[str, Any]) -> Any:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMInvalidJSONError(
            error_code="LLM_INVALID_JSON",
            message="NIM response missing choices array",
        )
    message = choices[0].get("message", {})
    content = message.get("content")
    if content is None and "reasoning_content" in message:
        content = message.get("reasoning_content")
    return content


def _parse_llm_json(data: dict[str, Any]) -> dict[str, Any]:
    content = _extract_message_content(data)
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        content = "\n".join(text_parts)
    if not isinstance(content, str):
        raise LLMInvalidJSONError(
            error_code="LLM_INVALID_JSON",
            message="NIM content field was not parseable text",
        )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            extracted = extract_first_json_object(content)
            return json.loads(extracted)
        except (ValueError, json.JSONDecodeError) as exc:
            raise LLMInvalidJSONError(
                error_code="LLM_INVALID_JSON",
                message=f"NIM returned non-JSON content: {str(exc)}",
            ) from exc


def _build_payload(model: str, messages: list[dict], tools: list[dict] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0}
    if tools:
        payload["tools"] = tools
    if os.getenv("NIM_JSON_MODE", "false").lower() == "true":
        payload["response_format"] = {"type": "json_object"}
    return payload


def nemotron_chat(messages: list[dict], tools: list[dict] | None = None) -> dict[str, Any]:
    if os.getenv("USE_LLM_STUB", "false").lower() == "true":
        return _stub_output()

    # Default to NVIDIA's OpenAI-compatible endpoint for real Nemotron usage.
    base_url = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    # Support either NIM_API_KEY or NVIDIA_API_KEY for convenience.
    api_key = os.getenv("NIM_API_KEY") or os.getenv("NVIDIA_API_KEY")
    model = os.getenv("NIM_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
    if not api_key:
        raise LLMAuthFailed(
            error_code="LLM_AUTH_FAILED",
            message="Missing API key for real Nemotron.",
        )
    payload = _build_payload(model, messages, tools=tools)

    max_retries = 2
    attempt = 0
    last_error: Exception | None = None
    while attempt <= max_retries:
        retry_count = attempt
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries:
                sleep_s = (2**attempt) + random.uniform(0, 0.25)
                logger.warning(
                    "nemotron_retry request retry_count=%s model=%s reason=%s",
                    retry_count + 1,
                    model,
                    type(exc).__name__,
                )
                time.sleep(sleep_s)
                attempt += 1
                continue
            _log_upstream_error(
                "LLM_UPSTREAM_UNAVAILABLE",
                model,
                None,
                retry_count,
                _truncate_body(str(exc)),
            )
            raise LLMUpstreamUnavailable(
                error_code="LLM_UPSTREAM_UNAVAILABLE",
                message="NIM upstream unavailable after retries",
                retry_count=retry_count,
            ) from exc
        except requests.exceptions.RequestException as exc:
            _log_upstream_error(
                "LLM_UPSTREAM_UNAVAILABLE",
                model,
                None,
                retry_count,
                _truncate_body(str(exc)),
            )
            raise LLMUpstreamUnavailable(
                error_code="LLM_UPSTREAM_UNAVAILABLE",
                message=f"NIM transport error: {type(exc).__name__}",
                retry_count=retry_count,
            ) from exc

        status = response.status_code
        body = _truncate_body(response.text or "")
        if status in (401, 403):
            _log_upstream_error("LLM_AUTH_FAILED", model, status, retry_count, body)
            raise LLMAuthFailed(
                error_code="LLM_AUTH_FAILED",
                message="NIM authentication/authorization failed",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            )
        if status in (404, 410):
            _log_upstream_error("LLM_MODEL_UNAVAILABLE", model, status, retry_count, body)
            raise LLMModelUnavailable(
                error_code="LLM_MODEL_UNAVAILABLE",
                message="Configured NIM model/endpoint is unavailable",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            )
        if status == 429:
            _log_upstream_error("LLM_RATE_LIMITED", model, status, retry_count, body)
            raise LLMRateLimited(
                error_code="LLM_RATE_LIMITED",
                message="NIM rate limit exceeded",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            )
        if status == 400:
            _log_upstream_error("LLM_UPSTREAM_BAD_REQUEST", model, status, retry_count, body)
            raise LLMBadRequest(
                error_code="LLM_UPSTREAM_BAD_REQUEST",
                message="NIM rejected request payload",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            )
        if status >= 500:
            if attempt < max_retries:
                sleep_s = (2**attempt) + random.uniform(0, 0.25)
                logger.warning(
                    "nemotron_retry status retry_count=%s model=%s upstream_status=%s",
                    retry_count + 1,
                    model,
                    status,
                )
                time.sleep(sleep_s)
                attempt += 1
                continue
            _log_upstream_error("LLM_UPSTREAM_UNAVAILABLE", model, status, retry_count, body)
            raise LLMUpstreamUnavailable(
                error_code="LLM_UPSTREAM_UNAVAILABLE",
                message="NIM returned upstream server error",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMInvalidJSONError(
                error_code="LLM_INVALID_JSON",
                message="NIM returned non-JSON HTTP payload",
                upstream_status=status,
                upstream_body=body,
                retry_count=retry_count,
            ) from exc
        return _parse_llm_json(data)

    # Unreachable in normal flow.
    raise LLMUpstreamUnavailable(
        error_code="LLM_UPSTREAM_UNAVAILABLE",
        message=f"NIM request failed after retries: {type(last_error).__name__ if last_error else 'unknown'}",
        retry_count=max_retries,
    )
