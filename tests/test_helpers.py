"""Tests for the pure (no I/O) helpers.

These tests do not require the trained models or the SQLite database,
so they can run in any environment with just ``numpy`` installed.
"""

import numpy as np
import pytest

from lendiql.early_warning import get_early_warning, risk_tier_from_probability
from lendiql.features import engineer_features
from lendiql.pricing import recommend_rate
from lendiql.schemas import BorrowerInput


# ── A canonical borrower used across multiple tests ──────────────
@pytest.fixture
def sample_borrower() -> BorrowerInput:
    return BorrowerInput(
        loan_amount=15_000,
        term_months=36,
        income=60_000,
        dti=25.0,
        credit_score=720,
        employment_length=5.0,
        home_ownership="MORTGAGE",
        lending_medium="Bank",
        digital_onboarding=1,
        upi_transaction_count=45,
        mobile_credit_score=680,
        first_time_borrower=0,
        urban_flag=1,
        interest_rate=11.0,
    )


# ── risk_tier_from_probability ───────────────────────────────────
class TestRiskTier:
    @pytest.mark.parametrize(
        "p,expected",
        [
            (0.0, "Low"),
            (0.10, "Low"),
            (0.2499, "Low"),
            (0.25, "Medium"),
            (0.40, "Medium"),
            (0.4999, "Medium"),
            (0.5, "High"),
            (0.75, "High"),
            (1.0, "High"),
        ],
    )
    def test_boundaries(self, p, expected):
        assert risk_tier_from_probability(p) == expected

    def test_consistency_with_threshold(self):
        for p in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            tier = risk_tier_from_probability(p)
            if p < 0.25:
                assert tier == "Low"
            elif p < 0.5:
                assert tier == "Medium"
            else:
                assert tier == "High"


# ── engineer_features ────────────────────────────────────────────
class TestEngineerFeatures:
    def test_output_shape(self, sample_borrower):
        X, _, _, _ = engineer_features(sample_borrower)
        assert X.shape == (1, 23)

    def test_derived_features_match_formula(self, sample_borrower):
        _, interest_rate, lti, burden = engineer_features(sample_borrower)
        assert lti == pytest.approx(sample_borrower.loan_amount / (sample_borrower.income + 1))
        assert burden == pytest.approx(sample_borrower.loan_amount / (sample_borrower.term_months + 1))
        assert interest_rate == sample_borrower.interest_rate

    def test_default_interest_rate_by_medium(self):
        b = BorrowerInput(
            loan_amount=10_000, term_months=24, income=40_000, dti=20.0,
            credit_score=700, employment_length=3.0, home_ownership="RENT",
            lending_medium="Microfinance", digital_onboarding=0,
            upi_transaction_count=20, mobile_credit_score=600,
            first_time_borrower=1, urban_flag=0,
        )
        _, ir, _, _ = engineer_features(b)
        assert ir == 8.0

    def test_high_dti_flag(self):
        b = BorrowerInput(
            loan_amount=10_000, term_months=24, income=40_000, dti=45.0,
            credit_score=700, employment_length=3.0, home_ownership="RENT",
            lending_medium="Bank", digital_onboarding=0,
            upi_transaction_count=20, mobile_credit_score=600,
            first_time_borrower=0, urban_flag=0,
        )
        X, _, _, _ = engineer_features(b)
        assert X[0, 9] == 1.0

    def test_long_term_flag(self):
        b = BorrowerInput(
            loan_amount=10_000, term_months=60, income=40_000, dti=20.0,
            credit_score=700, employment_length=3.0, home_ownership="RENT",
            lending_medium="Bank", digital_onboarding=0,
            upi_transaction_count=20, mobile_credit_score=600,
            first_time_borrower=0, urban_flag=0,
        )
        X, _, _, _ = engineer_features(b)
        assert X[0, 10] == 1.0


# ── recommend_rate ───────────────────────────────────────────────
class TestRecommendRate:
    def test_low_risk_low_rate(self):
        rate = recommend_rate(
            default_prob=0.05, risk_tier="Low",
            mobile_score=750, upi_count=80, first_timer=0,
        )
        assert 6.0 <= rate <= 15.0

    def test_high_risk_high_rate(self):
        rate = recommend_rate(
            default_prob=0.9, risk_tier="High",
            mobile_score=500, upi_count=5, first_timer=1,
        )
        assert rate >= 30.0

    def test_clipped_to_min(self):
        rate = recommend_rate(
            default_prob=0.0, risk_tier="Low",
            mobile_score=850, upi_count=0, first_timer=0,
        )
        assert rate >= 6.0

    def test_clipped_to_max(self):
        rate = recommend_rate(
            default_prob=1.0, risk_tier="High",
            mobile_score=300, upi_count=0, first_timer=1,
        )
        assert rate <= 36.0

    def test_first_timer_premium(self):
        without = recommend_rate(0.3, "Medium", 650, 30, 0)
        with_first = recommend_rate(0.3, "Medium", 650, 30, 1)
        assert with_first - without == pytest.approx(2.0)


# ── get_early_warning ────────────────────────────────────────────
class TestEarlyWarning:
    def test_healthy_when_no_flags(self):
        status, flags = get_early_warning(
            default_prob=0.1, dti=20, loan_to_income=2,
            mobile_score=700, upi_count=50, monthly_burden=300,
        )
        assert status == "HEALTHY"
        assert flags == []

    def test_watch_for_single_flag(self):
        status, flags = get_early_warning(
            default_prob=0.7, dti=20, loan_to_income=2,
            mobile_score=700, upi_count=50, monthly_burden=300,
        )
        assert status == "WATCH"
        assert flags == ["HIGH_DEFAULT_RISK"]

    def test_warning_for_two_flags(self):
        status, flags = get_early_warning(
            default_prob=0.7, dti=45, loan_to_income=2,
            mobile_score=700, upi_count=50, monthly_burden=300,
        )
        assert status == "WARNING"
        assert set(flags) == {"HIGH_DEFAULT_RISK", "HIGH_DTI"}

    def test_critical_for_three_or_more(self):
        status, flags = get_early_warning(
            default_prob=0.7, dti=45, loan_to_income=6,
            mobile_score=500, upi_count=5, monthly_burden=1200,
        )
        assert status == "CRITICAL"
        assert len(flags) >= 3
