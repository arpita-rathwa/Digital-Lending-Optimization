"""Pricing engine — personalized interest rate recommendation."""

from __future__ import annotations

import numpy as np

from lendiql.config import PRICING_CONFIG


def recommend_rate(
    default_prob: float,
    risk_tier: str,
    mobile_score: float,
    upi_count: int,
    first_timer: int,
) -> float:
    """Apply the pricing formula defined in the README."""
    cfg = PRICING_CONFIG
    risk_premium = cfg["risk_premium"].get(risk_tier, 2.0)
    prob_premium = default_prob * cfg["default_prob_weight"]
    mobile_discount = max(
        0.0,
        (mobile_score - cfg["mobile_discount_reference"]) / 100 * cfg["mobile_discount_per_100"],
    )
    upi_discount = min(cfg["upi_discount_cap"], upi_count / 100 * cfg["upi_discount_per_100"])
    first_timer_premium = cfg["first_timer_premium"] if first_timer == 1 else 0.0

    rate = (
        cfg["base_rate"]
        + risk_premium
        + prob_premium
        + first_timer_premium
        - mobile_discount
        - upi_discount
    )
    return round(float(np.clip(rate, cfg["min_rate"], cfg["max_rate"])), 2)
