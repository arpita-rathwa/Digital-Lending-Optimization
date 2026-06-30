"""External API adapters — partner integration layer for multi-medium lending.

Each adapter translates LendIQ signals into the format expected by a
specific lending partner.  New partners implement ``BaseAdapter``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lendiql.schemas import BorrowerInput


class BaseAdapter(ABC):
    """Abstract partner adapter — all partners implement this interface."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def build_request(self, borrower: BorrowerInput, prediction: dict) -> dict:
        """Translate LendIQ prediction into partner-specific request body."""
        ...

    @abstractmethod
    def parse_response(self, raw: dict) -> dict:
        """Parse partner response into standardised LendIQ result."""
        ...


class BankAdapter(BaseAdapter):
    def name(self) -> str:
        return "Bank"

    def build_request(self, borrower: BorrowerInput, prediction: dict) -> dict:
        return {
            "customer": {
                "annual_income": borrower.income,
                "credit_score": borrower.credit_score,
                "employment_months": int(borrower.employment_length * 12),
            },
            "loan": {
                "amount": borrower.loan_amount,
                "term_months": int(borrower.term_months),
                "purpose": "PERSONAL",
            },
            "risk_assessment": {
                "default_probability": prediction["risk"]["default_probability"],
                "risk_tier": prediction["risk"]["risk_tier"],
                "recommended_rate": prediction["pricing"]["recommended_rate"],
            },
        }

    def parse_response(self, raw: dict) -> dict:
        return {
            "partner_decision": raw.get("decision", "PENDING"),
            "partner_rate": raw.get("offered_rate"),
            "partner_loan_id": raw.get("loan_id"),
            "partner_fees": raw.get("fees", 0),
        }


class P2PAdapter(BaseAdapter):
    def name(self) -> str:
        return "P2P"

    def build_request(self, borrower: BorrowerInput, prediction: dict) -> dict:
        return {
            "borrower_profile": {
                "income": borrower.income,
                "dti_ratio": borrower.dti,
                "credit_tier": borrower.credit_score,
                "employment_years": borrower.employment_length,
                "first_time": bool(borrower.first_time_borrower),
            },
            "listing": {
                "amount": borrower.loan_amount,
                "term": int(borrower.term_months),
                "max_rate": prediction["pricing"]["recommended_rate"],
            },
            "lendiq_score": {
                "default_prob": prediction["risk"]["default_probability"],
                "segment": prediction["segment"]["name"],
            },
        }

    def parse_response(self, raw: dict) -> dict:
        return {
            "partner_decision": raw.get("status", "PENDING"),
            "partner_rate": raw.get("funding_rate"),
            "partner_loan_id": raw.get("listing_id"),
            "funded_amount": raw.get("funded_amount", 0),
        }


class MicrofinanceAdapter(BaseAdapter):
    def name(self) -> str:
        return "Microfinance"

    def build_request(self, borrower: BorrowerInput, prediction: dict) -> dict:
        return {
            "applicant": {
                "monthly_income": borrower.income / 12,
                "mobile_money_score": borrower.mobile_credit_score,
                "upi_volume": borrower.upi_transaction_count,
                "rural_flag": not bool(borrower.urban_flag),
            },
            "microloan": {
                "amount": borrower.loan_amount,
                "repayment_months": int(borrower.term_months),
                "digital_onboarding": bool(borrower.digital_onboarding),
            },
            "recommendation": {
                "approved": prediction["approval"]["approved"],
                "confidence": prediction["approval"]["confidence"],
                "suggested_rate": prediction["pricing"]["recommended_rate"],
            },
        }

    def parse_response(self, raw: dict) -> dict:
        return {
            "partner_decision": raw.get("outcome", "PENDING"),
            "partner_rate": raw.get("interest_rate"),
            "partner_loan_id": raw.get("microloan_id"),
            "disbursement_date": raw.get("disbursement_date"),
        }


class SMEAdapter(BaseAdapter):
    def name(self) -> str:
        return "SME"

    def build_request(self, borrower: BorrowerInput, prediction: dict) -> dict:
        return {
            "business": {
                "annual_revenue": borrower.income,
                "years_operating": borrower.employment_length,
                "urban_location": bool(borrower.urban_flag),
            },
            "credit_facility": {
                "requested_amount": borrower.loan_amount,
                "term_months": int(borrower.term_months),
                "collateral_score": borrower.credit_score,
            },
            "risk_rating": {
                "probability_of_default": prediction["risk"]["default_probability"],
                "expected_loss": prediction["risk"]["expected_loss"],
                "early_warning": prediction["risk"]["early_warning"],
                "tier": prediction["risk"]["risk_tier"],
            },
        }

    def parse_response(self, raw: dict) -> dict:
        return {
            "partner_decision": raw.get("approval_status", "PENDING"),
            "partner_rate": raw.get("annualized_rate"),
            "partner_loan_id": raw.get("facility_id"),
            "collateral_required": raw.get("collateral_amount", 0),
        }


_ADAPTER_REGISTRY: dict[str, BaseAdapter] = {
    "Bank": BankAdapter(),
    "P2P": P2PAdapter(),
    "Microfinance": MicrofinanceAdapter(),
    "SME": SMEAdapter(),
}


def get_adapter(partner: str) -> BaseAdapter:
    adapter = _ADAPTER_REGISTRY.get(partner)
    if adapter is None:
        raise ValueError(f"Unknown partner '{partner}'. Available: {list(_ADAPTER_REGISTRY)}")
    return adapter


def list_partners() -> list[str]:
    return list(_ADAPTER_REGISTRY)
