"""SHAP waterfall explanations for individual predictions."""

from __future__ import annotations

from typing import Optional

import numpy as np

from lendiql.config import FEATURE_NAMES


def compute_waterfall(
    model,
    X_scaled: np.ndarray,
    feature_names: Optional[list[str]] = None,
) -> dict:
    """Compute SHAP waterfall values for a single prediction row.

    Uses ``shap.TreeExplainer`` for the XGBoost model — no background
    dataset required for tree-based models.

    Returns a dict with ``base_value``, ``prediction``, and a list of
    ``contributions`` sorted by absolute magnitude (descending).
    """
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_scaled)

    fnames = feature_names or FEATURE_NAMES
    contributions = []
    for i in range(X_scaled.shape[1]):
        contributions.append({
            "feature": fnames[i] if i < len(fnames) else f"f_{i}",
            "value": float(X_scaled[0, i]),
            "contribution": float(shap_values[0, i]),
        })

    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)

    return {
        "base_value": float(explainer.expected_value),
        "prediction": float(float(model.predict_proba(X_scaled)[0][1])),
        "contributions": contributions,
    }
