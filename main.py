"""
LendIQ — Digital Lending Optimization API
==========================================

End-to-end risk + pricing + portfolio API for a digital lending platform
spanning 4 mediums (P2P, Bank, Microfinance, SME).

Notable design decisions (see README for full context):
  - ``risk_tier`` is DERIVED from ``default_probability`` to guarantee the
    two values can never disagree.
  - Two approval thresholds are used: 0.50 for individual live decisions
    (``/predict``), 0.78 for portfolio-level batch optimization only.
  - All magic numbers (pricing, early warning) are centralised in CONFIG.
  - The SQLite DB is downloaded lazily; if the download fails, ``/`` still
    returns a clear error instead of crashing the whole process.
"""

from __future__ import annotations

import os
import pickle
import sqlite3
from typing import Optional

import gdown
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ══════════════════════════════════════════════════════════
# CONFIG — single source of truth for every threshold/tunable
# ══════════════════════════════════════════════════════════
DB_PATH = "digital_lending.db"
DB_DRIVE_URL = "https://drive.google.com/uc?id=1kCqmBCDvVwVY8RQ5NDLiVQzfTDZFa5MS"

# Approval thresholds
INDIVIDUAL_APPROVAL_THRESHOLD = 0.50  # used by /predict for live decisions
PORTFOLIO_APPROVAL_THRESHOLD = 0.78   # used for batch portfolio optimization

# Risk tier cut-offs (applied to default_probability)
RISK_TIER_THRESHOLDS = {"Low": 0.25, "Medium": 0.50, "High": 1.01}

# Pricing engine parameters
PRICING_CONFIG = {
    "base_rate": 8.0,
    "risk_premium": {"Low": 1.0, "Medium": 4.0, "High": 8.0},
    "default_prob_weight": 20.0,       # each unit of P(default) adds this much %
    "first_timer_premium": 2.0,
    "mobile_discount_reference": 650,   # score above this earns a discount
    "mobile_discount_per_100": 1.0,     # discount per 100 points above reference
    "upi_discount_per_100": 1.0,       # discount per 100 UPI txns (capped)
    "upi_discount_cap": 1.5,
    "min_rate": 6.0,
    "max_rate": 36.0,
}

# Early warning rule thresholds (configurable for future tuning)
EARLY_WARNING_CONFIG = {
    "high_default_prob": 0.6,
    "high_dti": 40,
    "loan_income_stress": 5,
    "low_mobile_score": 550,
    "low_digital_activity_upi": 10,
    "high_monthly_burden": 1000,
}

# Per-medium default interest rate when the caller doesn't supply one
MEDIUM_DEFAULT_RATES = {"P2P": 13.5, "Bank": 11.0, "Microfinance": 8.0, "SME": 14.0}

SEGMENT_NAMES = {
    0: "First-Time Micro Borrowers",
    1: "High-Value Stressed",
    2: "Rural Micro Borrowers",
    3: "Urban Established",
    4: "High-Income Large Borrowers",
}

FEATURE_NAMES = [
    "loan_amount", "interest_rate", "term_months", "income",
    "dti", "credit_score", "employment_length",
    "loan_to_income", "monthly_burden", "high_dti_flag",
    "long_term_flag", "cost_of_credit", "risk_interaction",
    "digital_onboarding", "upi_transaction_count",
    "mobile_credit_score", "first_time_borrower", "urban_flag",
    "home_ownership_enc", "lending_medium_enc",
    "loan_size_enc", "credit_tier_enc", "income_segment_enc",
]

CLUSTER_FEATURES = [
    "loan_amount", "interest_rate", "term_months",
    "income", "dti", "loan_to_income", "monthly_burden",
    "mobile_credit_score", "upi_transaction_count",
    "digital_onboarding", "first_time_borrower", "urban_flag",
]

HOME_OWNERSHIP_MAP = {"RENT": 3, "OWN": 2, "MORTGAGE": 1, "BUSINESS": 0, "UNKNOWN": 4}
MEDIUM_MAP = {"Bank": 0, "Microfinance": 1, "P2P": 2, "SME": 3}

# ══════════════════════════════════════════════════════════
# App setup
# ══════════════════════════════════════════════════════════
app = FastAPI(
    title="Digital Lending Optimization API",
    description="LendIQ — multi-medium lending intelligence & decision optimization",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track startup state so we can return a useful error from / if the
# DB download or model load failed.
_startup_error: Optional[str] = None
_models: dict = {}


def _load_models() -> dict:
    """Load all pickle artifacts. Called lazily so import-time failures
    in dev don't block the whole app."""
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


def _ensure_db() -> None:
    """Download the SQLite DB from Google Drive if not present locally.
    Raises ``RuntimeError`` on failure so callers can surface a clean error."""
    if os.path.exists(DB_PATH):
        return
    print("Downloading database from Google Drive...")
    gdown.download(DB_DRIVE_URL, DB_PATH, quiet=False)
    if not os.path.exists(DB_PATH):
        raise RuntimeError("Database download completed but file is missing.")
    print("Database downloaded.")


def _init_on_startup() -> None:
    """Run once at app startup. Errors are captured into ``_startup_error``."""
    global _startup_error
    try:
        _ensure_db()
        _models.update(_load_models())
    except Exception as exc:  # noqa: BLE001 — we want to surface any failure
        _startup_error = f"{type(exc).__name__}: {exc}"
        print(f"[startup error] {_startup_error}")


@app.on_event("startup")
def _on_startup() -> None:
    _init_on_startup()


# ══════════════════════════════════════════════════════════
# Pydantic schemas
# ══════════════════════════════════════════════════════════
class BorrowerInput(BaseModel):
    loan_amount: float = Field(..., gt=0)
    term_months: float = Field(..., gt=0)
    income: float = Field(..., ge=0)
    dti: float = Field(..., ge=0)
    credit_score: float = Field(..., ge=0, le=850)
    employment_length: float = Field(..., ge=0)
    home_ownership: str  # RENT, OWN, MORTGAGE, BUSINESS, UNKNOWN
    lending_medium: str  # P2P, Bank, Microfinance, SME
    digital_onboarding: int = Field(..., ge=0, le=1)
    upi_transaction_count: int = Field(..., ge=0)
    mobile_credit_score: float = Field(..., ge=0, le=850)
    first_time_borrower: int = Field(..., ge=0, le=1)
    urban_flag: int = Field(..., ge=0, le=1)
    interest_rate: Optional[float] = Field(default=None, ge=0)


# ══════════════════════════════════════════════════════════
# Pure helpers (no I/O, easy to unit-test)
# ══════════════════════════════════════════════════════════
def risk_tier_from_probability(p: float) -> str:
    """Derive the risk tier label directly from default probability.

    Guarantees the label and the probability can never disagree.
    """
    if p < RISK_TIER_THRESHOLDS["Low"]:
        return "Low"
    if p < RISK_TIER_THRESHOLDS["Medium"]:
        return "Medium"
    return "High"


def engineer_features(data: BorrowerInput):
    """Build the 23-feature vector used by the XGBoost classifiers.

    Returns ``(feature_vector, interest_rate, loan_to_income, monthly_burden)``.
    """
    loan_to_income = data.loan_amount / (data.income + 1)
    monthly_burden = data.loan_amount / (data.term_months + 1)
    high_dti_flag = int(data.dti > 35)
    long_term_flag = int(data.term_months > 36)

    interest_rate = data.interest_rate or MEDIUM_DEFAULT_RATES.get(data.lending_medium, 10.0)
    cost_of_credit = (interest_rate / 100) * data.term_months
    risk_interaction = (data.loan_amount * data.dti) / (data.income + 1)

    # Binned categoricals — must match the training-time bin boundaries.
    if data.loan_amount <= 5_000:
        loan_size_enc = 0
    elif data.loan_amount <= 15_000:
        loan_size_enc = 1
    elif data.loan_amount <= 35_000:
        loan_size_enc = 2
    else:
        loan_size_enc = 3

    if data.credit_score < 580:
        credit_tier_enc = 0
    elif data.credit_score < 670:
        credit_tier_enc = 1
    elif data.credit_score < 740:
        credit_tier_enc = 2
    elif data.credit_score < 800:
        credit_tier_enc = 3
    else:
        credit_tier_enc = 4

    if data.income < 25_000:
        income_segment_enc = 0
    elif data.income < 50_000:
        income_segment_enc = 1
    elif data.income < 100_000:
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


def _require_ready() -> dict:
    """Return the loaded model dict or raise a 503 if startup failed."""
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


# ══════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════
@app.get("/")
def root():
    if _startup_error:
        return {
            "message": "Digital Lending Optimization API",
            "status": "degraded",
            "error": _startup_error,
        }
    return {
        "message": "Digital Lending Optimization API",
        "status": "running",
        "version": app.version,
    }


@app.post("/predict")
def predict(borrower: BorrowerInput):
    models = _require_ready()

    X, interest_rate, loan_to_income, monthly_burden = engineer_features(borrower)
    X_scaled = models["scaler"].transform(X)

    default_prob = float(models["xgb_default"].predict_proba(X_scaled)[0][1])

    # Risk tier derived deterministically from default_probability —
    # this is the only place risk_tier is computed in the API.
    risk_tier = risk_tier_from_probability(default_prob)

    expected_loss = float(models["xgb_loss"].predict(X_scaled)[0])

    rec_rate = recommend_rate(
        default_prob, risk_tier,
        borrower.mobile_credit_score,
        borrower.upi_transaction_count,
        borrower.first_time_borrower,
    )

    warning_status, warning_flags = get_early_warning(
        default_prob, borrower.dti, loan_to_income,
        borrower.mobile_credit_score, borrower.upi_transaction_count,
        monthly_burden,
    )

    # Segment assignment uses an UNSCALED view of the borrower's features
    # (matching the training-time cluster pipeline).
    cluster_input = np.array([[
        borrower.loan_amount, interest_rate, borrower.term_months,
        borrower.income, borrower.dti, loan_to_income, monthly_burden,
        borrower.mobile_credit_score, borrower.upi_transaction_count,
        borrower.digital_onboarding, borrower.first_time_borrower, borrower.urban_flag,
    ]])
    cluster_scaled = models["cluster_scaler"].transform(cluster_input)
    cluster = int(models["kmeans"].predict(cluster_scaled)[0])
    segment = SEGMENT_NAMES.get(cluster, "Unknown")

    # INDIVIDUAL threshold — strict, suitable for live applicant decisions.
    approved = default_prob < INDIVIDUAL_APPROVAL_THRESHOLD

    return {
        "approval": {
            "approved": approved,
            "decision": "APPROVED" if approved else "DECLINED",
            "confidence": round(1 - default_prob, 4),
            "threshold_used": INDIVIDUAL_APPROVAL_THRESHOLD,
            "threshold_type": "individual",
        },
        "risk": {
            "default_probability": round(default_prob, 4),
            "risk_tier": risk_tier,
            "expected_loss": round(expected_loss, 2),
            "early_warning": warning_status,
            "warning_flags": warning_flags,
        },
        "pricing": {
            "recommended_rate": rec_rate,
            "current_rate": interest_rate,
            "rate_adjustment": round(rec_rate - interest_rate, 2),
        },
        "segment": {
            "cluster": cluster,
            "name": segment,
        },
    }


@app.get("/portfolio")
def portfolio():
    if _startup_error or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {_startup_error or 'missing'}",
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        health = pd.read_sql_query(
            "SELECT * FROM portfolio_health ORDER BY health_score DESC", conn
        )
        medium = pd.read_sql_query(
            "SELECT * FROM medium_summary ORDER BY default_rate DESC", conn
        )
        segments = pd.read_sql_query(
            "SELECT * FROM segment_summary ORDER BY default_rate DESC", conn
        )
    finally:
        conn.close()

    return {
        "health_scores": health.to_dict(orient="records"),
        "medium_summary": medium.to_dict(orient="records"),
        "segments": segments.to_dict(orient="records"),
    }


@app.get("/early-warning")
def early_warning_queue(limit: int = Query(default=100, ge=1, le=1000)):
    if _startup_error or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {_startup_error or 'missing'}",
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        queue = pd.read_sql_query(
            """
            SELECT lending_medium, loan_amount, default_probability,
                   predicted_risk_tier, recommended_rate, early_warning
            FROM master_view
            WHERE early_warning != 'HEALTHY'
            ORDER BY default_probability DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )
    finally:
        conn.close()

    distribution = queue["early_warning"].value_counts().to_dict()
    return {
        "distribution": distribution,
        "queue": queue.to_dict(orient="records"),
    }


@app.get("/shap")
def shap_importance():
    if _startup_error or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {_startup_error or 'missing'}",
        )
    conn = sqlite3.connect(DB_PATH)
    try:
        shap_df = pd.read_sql_query(
            "SELECT * FROM shap_importance ORDER BY importance DESC", conn
        )
    finally:
        conn.close()
    return shap_df.to_dict(orient="records")
