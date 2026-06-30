"""Conformal prediction — uncertainty quantification via inductive conformal inference."""

from __future__ import annotations

import os
import pickle
from typing import Optional

import numpy as np

from lendiql.config import CONFORMAL_Q_HAT


CONFORMAL_PATH = "models/conformal_scores.pkl"


def _load_q_hat() -> float:
    """Load the pre-computed conformity threshold, or fall back to config."""
    if not os.path.exists(CONFORMAL_PATH):
        return CONFORMAL_Q_HAT
    with open(CONFORMAL_PATH, "rb") as f:
        data = pickle.load(f)
    return data.get("q_hat", CONFORMAL_Q_HAT)


def predict_set(prob_default: float, alpha: float = 0.1) -> dict:
    """Return a conformal prediction set at significance level ``alpha``.

    For binary classification, this produces either a singleton or the
    full set {0, 1} when the non-conformity score exceeds ``q_hat``.
    """
    q_hat = _load_q_hat()
    # Non-conformity score: 1 - predicted probability of the predicted class
    non_conformity = 1.0 - max(prob_default, 1.0 - prob_default)

    if non_conformity <= q_hat:
        # Confident — predict the class with highest probability
        pred_class = 1 if prob_default >= 0.5 else 0
        credible = True
    else:
        # Uncertain — both classes are possible
        pred_class = 1 if prob_default >= 0.5 else 0
        credible = False

    return {
        "predicted_class": pred_class,
        "predicted_label": "DEFAULT" if pred_class == 1 else "NON_DEFAULT",
        "probability": round(prob_default, 4),
        "non_conformity_score": round(non_conformity, 4),
        "q_hat": round(q_hat, 4),
        "credible": credible,
        "prediction_set": [pred_class] if credible else [0, 1],
        "significance_level": alpha,
    }
