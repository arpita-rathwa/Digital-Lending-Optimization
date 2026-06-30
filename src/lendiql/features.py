"""Feature engineering helpers."""

from __future__ import annotations

import numpy as np

from lendiql.config import (
    HOME_OWNERSHIP_MAP,
    MEDIUM_MAP,
    TRAINING_FEATURE_STATS,
    TRAINING_MEDIAN_RATES,
)
from lendiql.schemas import BorrowerInput


def engineer_features(data: BorrowerInput):
    """Build the 23-feature vector used by XGBoost classifiers.

    Returns ``(feature_vector, interest_rate, loan_to_income, monthly_burden)``.
    """
    loan_to_income = data.loan_amount / (data.income + 1)
    monthly_burden = data.loan_amount / (data.term_months + 1)
    high_dti_flag = int(data.dti > 35)
    long_term_flag = int(data.term_months > 36)

    interest_rate = data.interest_rate or TRAINING_MEDIAN_RATES.get(data.lending_medium, 10.0)
    cost_of_credit = (interest_rate / 100) * data.term_months
    risk_interaction = (data.loan_amount * data.dti) / (data.income + 1)

    if data.loan_amount <= 5_000:
        loan_size_enc = 0
    elif data.loan_amount <= 15_000:
        loan_size_enc = 1
    elif data.loan_amount <= 35_000:
        loan_size_enc = 2
    else:
        loan_size_enc = 3

    if data.credit_score <= 580:
        credit_tier_enc = 0
    elif data.credit_score <= 670:
        credit_tier_enc = 1
    elif data.credit_score <= 740:
        credit_tier_enc = 2
    elif data.credit_score <= 800:
        credit_tier_enc = 3
    else:
        credit_tier_enc = 4

    if data.income <= 25_000:
        income_segment_enc = 0
    elif data.income <= 50_000:
        income_segment_enc = 1
    elif data.income <= 100_000:
        income_segment_enc = 2
    else:
        income_segment_enc = 3

    home_ownership_enc = HOME_OWNERSHIP_MAP.get(data.home_ownership.upper(), 4)
    lending_medium_enc = MEDIUM_MAP.get(data.lending_medium, 0)

    feature_vector = np.array([[
        data.loan_amount, interest_rate, data.term_months, data.income,
        data.dti, data.credit_score, data.employment_length,
        loan_to_income, monthly_burden, high_dti_flag,
        long_term_flag, cost_of_credit, risk_interaction,
        data.digital_onboarding, data.upi_transaction_count,
        data.mobile_credit_score, data.first_time_borrower, data.urban_flag,
        home_ownership_enc, lending_medium_enc,
        loan_size_enc, credit_tier_enc, income_segment_enc,
    ]])

    return feature_vector, interest_rate, loan_to_income, monthly_burden


def validate_features(data: BorrowerInput) -> list[str]:
    """Check incoming feature values against training-time p1–p99 ranges.

    Returns a list of warning messages for out-of-range features.
    """
    warnings = []
    checks = {
        "loan_amount": data.loan_amount,
        "interest_rate": data.interest_rate or 10.0,
        "term_months": data.term_months,
        "income": data.income,
        "dti": data.dti,
        "credit_score": data.credit_score,
        "employment_length": data.employment_length,
        "mobile_credit_score": data.mobile_credit_score,
        "upi_transaction_count": float(data.upi_transaction_count),
    }
    for name, val in checks.items():
        stats = TRAINING_FEATURE_STATS.get(name)
        if stats is None:
            continue
        if val < stats["p1"] or val > stats["p99"]:
            warnings.append(
                f"{name} ({val:.1f}) outside training range "
                f"[{stats['p1']:.1f}, {stats['p99']:.1f}]"
            )
    return warnings
