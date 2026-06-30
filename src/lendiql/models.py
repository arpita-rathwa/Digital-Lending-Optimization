"""Model loading and inference."""

from __future__ import annotations

import os
import pickle
import sqlite3
from typing import Optional

import gdown
import numpy as np
import pandas as pd

from lendiql.config import (
    DB_DRIVE_URL,
    DB_PATH,
    INDIVIDUAL_APPROVAL_THRESHOLD,
    SEGMENT_NAMES,
)
from lendiql.early_warning import segment_approval_threshold

# Module-level state
_startup_error: Optional[str] = None
_models: dict = {}
_calibrator: Optional[object] = None


def load_artifacts() -> dict:
    """Load all pickle artifacts from disk."""
    artifacts = {
        "xgb_default": "models/xgb_default.pkl",
        "xgb_risk": "models/xgb_risk.pkl",
        "xgb_loss": "models/xgb_loss.pkl",
        "scaler": "models/scaler.pkl",
        "kmeans": "models/kmeans.pkl",
        "cluster_scaler": "models/cluster_scaler.pkl",
    }
    loaded = {}
    for name, path in artifacts.items():
        with open(path, "rb") as f:
            loaded[name] = pickle.load(f)
    return loaded


def load_calibrator() -> Optional[object]:
    """Load Platt calibrator from disk if present."""
    path = "models/calibrator.pkl"
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def ensure_db() -> None:
    """Download the SQLite DB from Google Drive if not present locally."""
    if os.path.exists(DB_PATH):
        return
    print("Downloading database from Google Drive...")
    gdown.download(DB_DRIVE_URL, DB_PATH, quiet=False)
    if not os.path.exists(DB_PATH):
        raise RuntimeError("Database download completed but file is missing.")
    print("Database downloaded.")


def init_on_startup() -> None:
    """Run once at app startup. Captures errors into ``_startup_error``."""
    global _startup_error, _models, _calibrator
    try:
        ensure_db()
        _models.update(load_artifacts())
        _calibrator = load_calibrator()
    except Exception as exc:
        _startup_error = f"{type(exc).__name__}: {exc}"
        print(f"[startup error] {_startup_error}")


def require_ready():
    """Return the loaded model dict or raise a 503 if startup failed."""
    from fastapi import HTTPException

    if _startup_error:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {_startup_error}",
        )
    if not _models:
        raise HTTPException(
            status_code=503,
            detail="Models not loaded. Visit / to retry initialization.",
        )
    return _models


def get_calibrator() -> Optional[object]:
    return _calibrator


def get_startup_error() -> Optional[str]:
    return _startup_error


def predict_borrower(X_scaled: np.ndarray, cluster_input_scaled: np.ndarray, models: dict):
    """Run all predictions for a single borrower."""
    default_prob = float(models["xgb_default"].predict_proba(X_scaled)[0][1])
    expected_loss = float(models["xgb_loss"].predict(X_scaled)[0])
    cluster = int(models["kmeans"].predict(cluster_input_scaled)[0])
    segment = SEGMENT_NAMES.get(cluster, "Unknown")
    thresh = segment_approval_threshold(cluster)
    approved = default_prob < thresh
    return default_prob, expected_loss, cluster, segment, approved, thresh
