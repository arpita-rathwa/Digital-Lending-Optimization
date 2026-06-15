"""Early warning system — flag stressed loans before they default, and risk tier derivation."""

from __future__ import annotations

from lendiql.config import EARLY_WARNING_CONFIG, RISK_TIER_THRESHOLDS


def risk_tier_from_probability(p: float) -> str:
    """Derive the risk tier label directly from default probability."""
    if p < RISK_TIER_THRESHOLDS["Low"]:
        return "Low"
    if p < RISK_TIER_THRESHOLDS["Medium"]:
        return "Medium"
    return "High"


def get_early_warning(
    default_prob: float,
    dti: float,
    loan_to_income: float,
    mobile_score: float,
    upi_count: int,
    monthly_burden: float,
):
    """Return ``(status, [flag_names])`` based on configurable thresholds."""
    cfg = EARLY_WARNING_CONFIG
    flags = []
    if default_prob > cfg["high_default_prob"]:
        flags.append("HIGH_DEFAULT_RISK")
    if dti > cfg["high_dti"]:
        flags.append("HIGH_DTI")
    if loan_to_income > cfg["loan_income_stress"]:
        flags.append("LOAN_INCOME_STRESS")
    if mobile_score < cfg["low_mobile_score"]:
        flags.append("LOW_MOBILE_SCORE")
    if upi_count < cfg["low_digital_activity_upi"]:
        flags.append("LOW_DIGITAL_ACTIVITY")
    if monthly_burden > cfg["high_monthly_burden"]:
        flags.append("HIGH_MONTHLY_BURDEN")

    if not flags:
        return "HEALTHY", []
    if len(flags) == 1:
        return "WATCH", flags
    if len(flags) == 2:
        return "WARNING", flags
    return "CRITICAL", flags
