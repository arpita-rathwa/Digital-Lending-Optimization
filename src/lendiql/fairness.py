"""Fairness metrics — per-segment analysis for regulatory compliance."""

from __future__ import annotations

import numpy as np


def compute_fairness_metrics(
    segments: list[dict],
) -> dict:
    """Compute fairness metrics across borrower segments.

    Each segment dict should contain:
      ``segment``, ``total``, ``approved``, ``defaulted``.

    Returns adverse impact ratios, approval rates, and statistical parity
    difference for each segment vs the highest-approved segment.
    """
    if not segments:
        return {"error": "No segment data provided"}

    for s in segments:
        s["approval_rate"] = s["approved"] / max(s["total"], 1)
        s["default_rate"] = s["defaulted"] / max(s["total"], 1)

    max_approval = max(s["approval_rate"] for s in segments)
    overall_approved = sum(s["approved"] for s in segments)
    overall_total = sum(s["total"] for s in segments)
    overall_approval_rate = overall_approved / max(overall_total, 1)

    results = []
    for s in segments:
        adverse_impact_ratio = s["approval_rate"] / max(max_approval, 1e-12)
        stat_parity_diff = s["approval_rate"] - overall_approval_rate

        results.append({
            "segment": s["segment"],
            "total_applicants": s["total"],
            "approved": s["approved"],
            "defaulted": s["defaulted"],
            "approval_rate": round(s["approval_rate"], 4),
            "default_rate": round(s["default_rate"], 4),
            "adverse_impact_ratio": round(adverse_impact_ratio, 4),
            "statistical_parity_difference": round(stat_parity_diff, 4),
            "four_fifths_violation": adverse_impact_ratio < 0.80,
        })

    return {
        "segments": results,
        "overall_approval_rate": round(overall_approval_rate, 4),
        "reference_group_approval_rate": round(max_approval, 4),
    }
