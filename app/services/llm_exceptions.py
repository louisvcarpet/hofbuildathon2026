from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMError(Exception):
    error_code: str
    message: str
    upstream_status: int | None = None
    upstream_body: str | None = None
    retry_count: int = 0

    def __str__(self) -> str:
        return self.message


class LLMUpstreamUnavailable(LLMError):
    pass


class LLMAuthFailed(LLMError):
    pass


class LLMRateLimited(LLMError):
    pass


class LLMModelUnavailable(LLMError):
    pass


class LLMBadRequest(LLMError):
    pass


class LLMInvalidJSONError(LLMError):
    pass
