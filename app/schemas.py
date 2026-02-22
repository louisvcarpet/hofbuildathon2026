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
