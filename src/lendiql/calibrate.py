"""Probability calibration — Platt scaling + reliability curve."""

from __future__ import annotations

import os
import pickle
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from lendiql.config import PLATT_A, PLATT_B


CALIBRATOR_PATH = "models/calibrator.pkl"


def _load_calibrator() -> Optional[LogisticRegression]:
    """Load the saved Platt calibrator, or return None."""
    if not os.path.exists(CALIBRATOR_PATH):
        return None
    with open(CALIBRATOR_PATH, "rb") as f:
        return pickle.load(f)


def calibrate_proba(raw_proba: float, model: Optional[LogisticRegression] = None) -> float:
    """Apply Platt scaling to a raw probability.

    If no calibrator model is available, falls back to the sigmoid defined
    by ``PLATT_A`` and ``PLATT_B`` from config.
    """
    if model is not None:
        X = np.array([[raw_proba]])
        return float(model.predict_proba(X)[0][1])

    # Fallback: logistic sigmoid with config parameters
    prob = np.clip(raw_proba, 1e-12, 1 - 1e-12)
    logit = PLATT_A + PLATT_B * np.log(prob / (1.0 - prob))
    return float(1.0 / (1.0 + np.exp(-logit)))


def compute_reliability_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> list[dict]:
    """Compute reliability (calibration) curve data.

    Returns a list of bins, each with:
      ``bin_center``, ``mean_predicted``, ``fraction_of_positives``, ``count``.
    """
    bins = np.linspace(0, 1, n_bins + 1)
    results = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        count = int(mask.sum())
        if count == 0:
            continue
        mean_pred = float(np.mean(y_prob[mask]))
        frac_pos = float(np.mean(y_true[mask]))
        results.append({
            "bin_center": float((lo + hi) / 2),
            "bin_lower": float(lo),
            "bin_upper": float(hi),
            "mean_predicted": round(mean_pred, 4),
            "fraction_of_positives": round(frac_pos, 4),
            "count": count,
        })
    return results
