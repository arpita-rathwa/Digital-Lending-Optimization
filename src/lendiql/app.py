"""FastAPI application — endpoints and app setup."""

from __future__ import annotations

import os
import sqlite3

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from lendiql import __version__
from lendiql.config import (
    DB_PATH,
    INDIVIDUAL_APPROVAL_THRESHOLD,
)
from lendiql.early_warning import get_early_warning, risk_tier_from_probability
from lendiql.features import engineer_features
from lendiql.models import (
    get_startup_error,
    init_on_startup,
    predict_borrower,
    require_ready,
)
from lendiql.pricing import recommend_rate
from lendiql.schemas import BorrowerInput

app = FastAPI(
    title="Digital Lending Optimization API",
    description="LendIQ — multi-medium lending intelligence & decision optimization",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    init_on_startup()


# ── Endpoints ─────────────────────────────────────────────────────


@app.get("/")
def root():
    err = get_startup_error()
    if err:
        return {
            "message": "Digital Lending Optimization API",
            "status": "degraded",
            "error": err,
        }
    return {
        "message": "Digital Lending Optimization API",
        "status": "running",
        "version": app.version,
    }


@app.post("/predict")
def predict(borrower: BorrowerInput):
    models = require_ready()

    X, interest_rate, loan_to_income, monthly_burden = engineer_features(borrower)
    X_scaled = models["scaler"].transform(X)

    default_prob = float(models["xgb_default"].predict_proba(X_scaled)[0][1])
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

    cluster_input = np.array([[
        borrower.loan_amount, interest_rate, borrower.term_months,
        borrower.income, borrower.dti, loan_to_income, monthly_burden,
        borrower.mobile_credit_score, borrower.upi_transaction_count,
        borrower.digital_onboarding, borrower.first_time_borrower, borrower.urban_flag,
    ]])
    cluster_scaled = models["cluster_scaler"].transform(cluster_input)
    cluster = int(models["kmeans"].predict(cluster_scaled)[0])
    segment = {
        0: "First-Time Micro Borrowers",
        1: "High-Value Stressed",
        2: "Rural Micro Borrowers",
        3: "Urban Established",
        4: "High-Income Large Borrowers",
    }.get(cluster, "Unknown")

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
    err = get_startup_error()
    if err or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {err or 'missing'}",
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
    err = get_startup_error()
    if err or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {err or 'missing'}",
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
    err = get_startup_error()
    if err or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {err or 'missing'}",
        )
    conn = sqlite3.connect(DB_PATH)
    try:
        shap_df = pd.read_sql_query(
            "SELECT * FROM shap_importance ORDER BY importance DESC", conn
        )
    finally:
        conn.close()
    return shap_df.to_dict(orient="records")
