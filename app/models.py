from datetime import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    role_title: Mapped[str | None] = mapped_column(String(255))
    level: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    base_salary: Mapped[float | None] = mapped_column(Float)
    bonus_target: Mapped[float | None] = mapped_column(Float)
    equity_type: Mapped[str | None] = mapped_column(String(100))
    equity_amount: Mapped[float | None] = mapped_column(Float)
    vesting_schedule: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[datetime | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1")
    answers_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    missing_fields_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    key_drivers_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    negotiation_targets_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risks_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    summary_text: Mapped[str] = mapped_column(String(600), nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    followup_questions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
