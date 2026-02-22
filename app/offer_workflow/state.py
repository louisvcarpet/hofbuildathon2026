# app/offer_workflow/state.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class OfferWorkflowState(BaseModel):

    # ---- Input ----
    job_title: str
    industry: str
    company_tier: str
    location: str
    base_salary: float
    bonus_pct: float
    equity_val: float
    signing_bonus: float
    years_exp: int
    remote_status: str
    user_priorities: Optional[Dict[str, Any]] = None

    # ---- Enrichment ----
    market_data: Optional[Dict[str, Any]] = None

    # ---- LLM ----
    llm_response: Optional[Dict[str, Any]] = None
    output_checker: Optional[str] = None

    # ---- Control ----
    tryout: int = 0
    maxtry: int = Field(default=2)

    result: Optional[Any] = None