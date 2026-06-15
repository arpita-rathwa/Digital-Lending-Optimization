"""Pydantic schemas for request / response validation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BorrowerInput(BaseModel):
    loan_amount: float = Field(..., gt=0)
    term_months: float = Field(..., gt=0)
    income: float = Field(..., ge=0)
    dti: float = Field(..., ge=0)
    credit_score: float = Field(..., ge=0, le=850)
    employment_length: float = Field(..., ge=0)
    home_ownership: str
    lending_medium: str
    digital_onboarding: int = Field(..., ge=0, le=1)
    upi_transaction_count: int = Field(..., ge=0)
    mobile_credit_score: float = Field(..., ge=0, le=850)
    first_time_borrower: int = Field(..., ge=0, le=1)
    urban_flag: int = Field(..., ge=0, le=1)
    interest_rate: Optional[float] = Field(default=None, ge=0)
