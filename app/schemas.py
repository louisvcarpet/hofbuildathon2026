from enum import Enum

from pydantic import BaseModel, Field


class RecommendationEnum(str, Enum):
    accept = "accept"
    renegotiate = "renegotiate"
    needs_more_info = "needs_more_info"


class ImpactEnum(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class KeyDriver(BaseModel):
    label: str
    impact: ImpactEnum


class NegotiationTarget(BaseModel):
    item: str
    ask: str
    reason: str


class ScoreBreakdown(BaseModel):
    salary: float
    bonus: float
    equity: float
    fit: float
    risk_penalty: float


class ScorePayload(BaseModel):
    score: float = Field(ge=0, le=10)
    breakdown: ScoreBreakdown
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)


class EvaluationOutput(BaseModel):
    score: float = Field(ge=0, le=10)
    recommendation: RecommendationEnum
    confidence: float = Field(ge=0, le=1)
    key_drivers: list[KeyDriver] = Field(default_factory=list, min_length=3, max_length=6)
    negotiation_targets: list[NegotiationTarget] = Field(default_factory=list, max_length=5)
    risks: list[str] = Field(default_factory=list, max_length=6)
    followup_questions: list[str] = Field(default_factory=list, max_length=3)
    one_paragraph_summary: str = Field(max_length=600)


class MarketComps(BaseModel):
    p25: float = 0
    median: float = 0
    p75: float = 0
    sample_size: int = 0


class ParsedOfferData(BaseModel):
    role_title: str | None = None
    level: str | None = None
    location: str | None = None
    base_salary: float | None = None
    bonus_target: float | None = None
    equity_type: str | None = None
    equity_amount: float | None = None
    vesting_schedule: str | None = None
    start_date: str | None = None
    confidence_note: str


class OfferPdfIngestResponse(BaseModel):
    offer_id: int | None = None
    survey_response_id: int | None = None
    extracted_text_chars: int
    extracted_text: str | None = None
    parsed: ParsedOfferData


class OfferChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class OfferChatResponse(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
