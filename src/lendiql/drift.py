"""Drift detection — PSI / distribution comparison between training and live data."""

from __future__ import annotations

from typing import Optional

import numpy as np

from lendiql.config import FEATURE_NAMES, TRAINING_FEATURE_STATS


def _psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """Population Stability Index between two distributions."""
    bins = np.linspace(0, 1, n_bins + 1)
    expected_pct = np.histogram(expected, bins=bins, density=True)[0]
    actual_pct = np.histogram(actual, bins=bins, density=True)[0]
    expected_pct = np.clip(expected_pct, 1e-12, None)
    actual_pct = np.clip(actual_pct, 1e-12, None)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def _zscore(val: float, mean: float, std: float) -> float:
    return (val - mean) / max(std, 1e-12)


def detect_drift(
    live_stats: dict[str, dict],
    training_stats: Optional[dict] = None,
) -> dict:
    """Compare live feature statistics against training baselines.

    ``live_stats`` should have the same shape as ``TRAINING_FEATURE_STATS``:
    ``{feature_name: {"mean": x, "std": y, "p1": a, "p99": b}}``.

    Returns a dict with overall ``drift_score``, ``status``, and a
    per-feature breakdown.
    """
    train = training_stats or TRAINING_FEATURE_STATS
    features = []
    feature_count = 0
    drifted_count = 0

    for fname in FEATURE_NAMES:
        if fname not in train or fname not in live_stats:
            continue
        feature_count += 1
        t = train[fname]
        l = live_stats[fname]

        mean_z = abs(_zscore(l["mean"], t["mean"], t["std"]))
        # Simple drift flag: mean shifted more than 1.5 std or std ratio > 2x
        std_ratio = max(l["std"], 1e-12) / max(t["std"], 1e-12)
        drifted = mean_z > 1.5 or std_ratio > 2.0 or std_ratio < 0.5

        severity = "high" if mean_z > 2.5 else "medium" if mean_z > 1.5 else "low"
        if drifted:
            drifted_count += 1

        features.append({
            "feature": fname,
            "training_mean": round(t["mean"], 2),
            "live_mean": round(l["mean"], 2),
            "z_score": round(mean_z, 3),
            "std_ratio": round(std_ratio, 3),
            "drifted": drifted,
            "severity": severity,
        })

    features.sort(key=lambda f: f["z_score"], reverse=True)
    drift_pct = drifted_count / max(feature_count, 1)

    if drift_pct > 0.3:
        status = "critical"
    elif drift_pct > 0.15:
        status = "warning"
    else:
        status = "stable"

    return {
        "drift_score": round(drift_pct, 4),
        "status": status,
        "features_drifted": drifted_count,
        "features_total": feature_count,
        "features": features,
    }
