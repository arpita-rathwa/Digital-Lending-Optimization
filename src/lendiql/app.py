"""FastAPI application — endpoints and app setup."""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from lendiql import __version__
from lendiql.adapters import get_adapter, list_partners
from lendiql.auth import init_auth_db, register_auth_routes, require_viewer, require_operator, require_admin
from lendiql.calibrate import calibrate_proba, compute_reliability_curve
from lendiql.conformal import predict_set
from lendiql.config import (
    DB_PATH,
    SEGMENT_NAMES,
    TRAINING_FEATURE_STATS,
)
from lendiql.drift import detect_drift
from lendiql.early_warning import (
    adverse_action_reasons,
    get_early_warning,
    risk_tier_from_probability,
    segment_approval_threshold,
)
from lendiql.fairness import compute_fairness_metrics
from lendiql.features import engineer_features, validate_features
from lendiql.models import (
    get_calibrator,
    get_startup_error,
    init_on_startup,
    require_ready,
)
from lendiql.explainer import explain_portfolio
from lendiql.ops import (
    logger,
    rate_limit_middleware,
    register_metrics_routes,
    security_headers_middleware,
    setup_logging,
    timing_middleware,
)
from lendiql.optimizer import knapsack_optimize
from lendiql.pricing import recommend_rate
from lendiql.schemas import BorrowerInput, OptimizationRequest, PartnerRequest
from lendiql.shap_explain import compute_waterfall
from lendiql.worker import enqueue, get_task, list_tasks, start_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_on_startup()
    init_auth_db()
    worker_task = start_worker(interval=30.0)
    logger.info("LendIQ started — auth DB initialized, worker running")
    yield
    worker_task.cancel()
    logger.info("LendIQ shutting down")


app = FastAPI(
    title="Digital Lending Optimization API",
    description="LendIQ — multi-medium lending intelligence & decision optimization",
    version=__version__,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check & status"},
        {"name": "Prediction", "description": "Risk prediction & scoring"},
        {"name": "Portfolio", "description": "Portfolio intelligence & optimization"},
        {"name": "Fairness", "description": "Fairness & compliance monitoring"},
        {"name": "Observability", "description": "Model observability & drift"},
        {"name": "Authentication", "description": "API key management & auth"},
        {"name": "Partners", "description": "External partner integrations"},
        {"name": "Tasks", "description": "Background task management"},
    ],
)

# Middleware order: outermost first
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(timing_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(security_headers_middleware)

# Static file serving for frontend
try:
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
    if os.path.isdir(frontend_path):
        app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")
except Exception:
    pass

# Register sub-systems
register_metrics_routes(app)
register_auth_routes(app)


# ── Error handler ────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ── Helper ──────────────────────────────────────────────────────


def _get_db() -> sqlite3.Connection:
    err = get_startup_error()
    if err or not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {err or 'missing'}",
        )
    return sqlite3.connect(DB_PATH)


def _compute_portfolio_aggregates(conn: sqlite3.Connection) -> dict | None:
    """Try to compute live portfolio stats from ingested_loans table."""
    try:
        cursor = conn.execute("SELECT count(*) FROM ingested_loans")
        count = cursor.fetchone()[0]
        if count == 0:
            return None
    except Exception:
        return None

    try:
        health = pd.read_sql_query(
            """
            SELECT lending_medium,
                   100 - AVG(default_probability)*100 AS health_score,
                   AVG(default_probability) AS default_rate
            FROM ingested_loans
            GROUP BY lending_medium
            """, conn,
        )
        medium = pd.read_sql_query(
            """
            SELECT lending_medium,
                   COUNT(*) AS total_loans,
                   AVG(loan_amount) AS avg_loan_amount,
                   AVG(default_probability) AS default_rate,
                   AVG(interest_rate) AS avg_interest_rate
            FROM ingested_loans
            GROUP BY lending_medium
            """, conn,
        )
        segments = pd.read_sql_query(
            """
            SELECT segment_name AS segment,
                   COUNT(*) AS total_loans,
                   AVG(default_probability) AS default_rate,
                   AVG(loan_amount) AS avg_loan,
                   AVG(recommended_rate) AS avg_recommended_rate
            FROM ingested_loans
            GROUP BY segment_name
            """, conn,
        )
        return {
            "health_scores": health.to_dict(orient="records"),
            "medium_summary": medium.to_dict(orient="records"),
            "segments": segments.to_dict(orient="records"),
        }
    except Exception:
        return None


def _log_prediction(conn: sqlite3.Connection, borrower: BorrowerInput,
                    result: dict) -> None:
    """Non-blocking prediction logging."""
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                loan_amount REAL, term_months REAL, income REAL,
                dti REAL, credit_score REAL, employment_length REAL,
                lending_medium TEXT, home_ownership TEXT,
                mobile_credit_score REAL, upi_transaction_count INTEGER,
                digital_onboarding INTEGER, first_time_borrower INTEGER,
                urban_flag INTEGER, interest_rate REAL,
                default_probability REAL, risk_tier TEXT,
                expected_loss REAL, early_warning TEXT,
                decision TEXT, recommended_rate REAL, cluster INTEGER,
                segment TEXT
            )
            """,
        )
        conn.execute(
            """
            INSERT INTO prediction_logs (
                timestamp, loan_amount, term_months, income,
                dti, credit_score, employment_length,
                lending_medium, home_ownership,
                mobile_credit_score, upi_transaction_count,
                digital_onboarding, first_time_borrower, urban_flag,
                interest_rate,
                default_probability, risk_tier, expected_loss,
                early_warning, decision, recommended_rate,
                cluster, segment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                borrower.loan_amount, borrower.term_months, borrower.income,
                borrower.dti, borrower.credit_score, borrower.employment_length,
                borrower.lending_medium, borrower.home_ownership,
                borrower.mobile_credit_score, borrower.upi_transaction_count,
                borrower.digital_onboarding, borrower.first_time_borrower,
                borrower.urban_flag, borrower.interest_rate,
                result["risk"]["default_probability"], result["risk"]["risk_tier"],
                result["risk"]["expected_loss"], result["risk"]["early_warning"],
                result["approval"]["decision"], result["pricing"]["recommended_rate"],
                result["segment"]["cluster"], result["segment"]["name"],
            ),
        )
        conn.commit()
    except Exception:
        pass  # non-blocking


# ── Health ──────────────────────────────────────────────────────


@app.get("/")
def root():
    err = get_startup_error()
    return {
        "message": "Digital Lending Optimization API",
        "status": "degraded" if err else "running",
        "version": app.version,
        "uptime": "N/A",
        "endpoints": {
            "predict": "POST /predict",
            "portfolio": "GET /portfolio, POST /portfolio/explain, POST /portfolio/optimize, POST /portfolio/ingest, POST /portfolio/outcome",
            "early_warning": "GET /early-warning",
            "shap": "GET /shap, POST /shap/waterfall",
            "fairness": "POST /fairness",
            "drift": "GET /drift",
            "calibration": "GET /calibration",
            "conformal": "POST /conformal/predict",
            "partners": "GET /partners, POST /partner/assess",
            "auth": "POST /auth/keys, GET /auth/keys, DELETE /auth/keys/{id}",
            "observability": "GET /metrics, GET /prediction-logs",
            "tasks": "POST /tasks/{type}, GET /tasks, GET /tasks/{id}",
        },
    }


# ── Predict ─────────────────────────────────────────────────────


@app.post("/predict")
def predict(borrower: BorrowerInput):
    models = require_ready()

    # Feature validation
    val_warnings = validate_features(borrower)

    X, interest_rate, loan_to_income, monthly_burden = engineer_features(borrower)
    X_scaled = models["scaler"].transform(X)

    default_prob = float(models["xgb_default"].predict_proba(X_scaled)[0][1])

    # Calibrate probability
    calibrator = get_calibrator()
    if calibrator is not None:
        default_prob = calibrate_proba(default_prob, calibrator)
    else:
        default_prob = calibrate_proba(default_prob)  # fallback sigmoid

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
    segment = SEGMENT_NAMES.get(cluster, "Unknown")

    thresh = segment_approval_threshold(cluster)
    approved = default_prob < thresh

    result = {
        "approval": {
            "approved": approved,
            "decision": "APPROVED" if approved else "DECLINED",
            "confidence": round(1 - default_prob, 4),
            "threshold_used": thresh,
            "threshold_type": "segment_adaptive",
            "segment": segment,
        },
        "risk": {
            "default_probability": round(default_prob, 4),
            "risk_tier": risk_tier,
            "expected_loss": round(expected_loss, 2),
            "early_warning": warning_status,
            "warning_flags": warning_flags,
            "adverse_action_reasons": adverse_action_reasons(warning_flags),
            "calibrated": calibrator is not None,
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
        "validation_warnings": val_warnings,
    }

    # Log prediction (non-blocking)
    conn = _get_db()
    try:
        _log_prediction(conn, borrower, result)
    finally:
        conn.close()

    return result


# ── SHAP Waterfall ──────────────────────────────────────────────


@app.post("/shap/waterfall")
def shap_waterfall(borrower: BorrowerInput):
    models = require_ready()
    X, _, _, _ = engineer_features(borrower)
    X_scaled = models["scaler"].transform(X)
    waterfall = compute_waterfall(models["xgb_default"], X_scaled)
    return waterfall


# ── Portfolio ───────────────────────────────────────────────────


@app.get("/portfolio")
def portfolio():
    conn = _get_db()
    try:
        # Try live aggregation first
        live = _compute_portfolio_aggregates(conn)
        if live is not None:
            return live

        # Fallback to static DB tables
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


@app.post("/portfolio/explain")
def portfolio_explain():
    conn = _get_db()
    try:
        live = _compute_portfolio_aggregates(conn)
        if live is not None:
            portfolio_data = live
        else:
            health = pd.read_sql_query(
                "SELECT * FROM portfolio_health ORDER BY health_score DESC", conn
            )
            medium = pd.read_sql_query(
                "SELECT * FROM medium_summary ORDER BY default_rate DESC", conn
            )
            segments_df = pd.read_sql_query(
                "SELECT * FROM segment_summary ORDER BY default_rate DESC", conn
            )
            portfolio_data = {
                "health_scores": health.to_dict(orient="records"),
                "medium_summary": medium.to_dict(orient="records"),
                "segments": segments_df.to_dict(orient="records"),
            }
    finally:
        conn.close()

    return {"explanation": explain_portfolio(portfolio_data)}


@app.post("/portfolio/optimize")
def portfolio_optimize(req: OptimizationRequest):
    return knapsack_optimize(req)


@app.post("/portfolio/ingest")
def portfolio_ingest(records: list[dict]):
    conn = _get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id TEXT, lending_medium TEXT, loan_amount REAL,
                interest_rate REAL, term_months REAL, income REAL,
                dti REAL, credit_score REAL, default_probability REAL,
                recommended_rate REAL, segment_name TEXT, cluster INTEGER,
                decision TEXT, ingested_at TEXT
            )
            """,
        )
        now = datetime.now(timezone.utc).isoformat()
        for rec in records:
            conn.execute(
                """
                INSERT INTO ingested_loans (
                    loan_id, lending_medium, loan_amount,
                    interest_rate, term_months, income,
                    dti, credit_score, default_probability,
                    recommended_rate, segment_name, cluster,
                    decision, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.get("loan_id", ""),
                    rec.get("lending_medium", ""),
                    rec.get("loan_amount", 0),
                    rec.get("interest_rate", 0),
                    rec.get("term_months", 0),
                    rec.get("income", 0),
                    rec.get("dti", 0),
                    rec.get("credit_score", 0),
                    rec.get("default_probability", 0),
                    rec.get("recommended_rate", 0),
                    rec.get("segment_name", ""),
                    rec.get("cluster", -1),
                    rec.get("decision", ""),
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return {"ingested": len(records)}


@app.post("/portfolio/outcome")
def portfolio_outcome(outcomes: list[dict]):
    conn = _get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS loan_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id TEXT, actual_default INTEGER,
                actual_loss REAL, recorded_at TEXT
            )
            """,
        )
        now = datetime.now(timezone.utc).isoformat()
        for o in outcomes:
            conn.execute(
                """
                INSERT INTO loan_outcomes (loan_id, actual_default, actual_loss, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (o.get("loan_id", ""), int(o.get("actual_default", 0)),
                 o.get("actual_loss", 0), now),
            )
        conn.commit()
    finally:
        conn.close()
    return {"recorded": len(outcomes)}


# ── Early Warning ───────────────────────────────────────────────


@app.get("/early-warning")
def early_warning_queue(limit: int = Query(default=100, ge=1, le=1000)):
    conn = _get_db()
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


# ── SHAP (global) ───────────────────────────────────────────────


@app.get("/shap")
def shap_importance():
    conn = _get_db()
    try:
        shap_df = pd.read_sql_query(
            "SELECT * FROM shap_importance ORDER BY importance DESC", conn
        )
    finally:
        conn.close()
    return shap_df.to_dict(orient="records")


# ── Calibration Curve ───────────────────────────────────────────


@app.get("/calibration")
def calibration_curve(n_bins: int = Query(default=10, ge=5, le=50)):
    conn = _get_db()
    try:
        # Try live data first
        try:
            live = pd.read_sql_query(
                "SELECT default_probability, actual_default FROM ingested_loans "
                "WHERE actual_default IS NOT NULL", conn,
            )
            if len(live) > 0:
                curve = compute_reliability_curve(
                    live["actual_default"].values,
                    live["default_probability"].values,
                    n_bins,
                )
                return {"source": "live", "bins": curve}
        except Exception:
            pass

        df = pd.read_sql_query(
            "SELECT default_probability, default FROM master_view", conn
        )
    finally:
        conn.close()

    curve = compute_reliability_curve(
        df["default"].values, df["default_probability"].values, n_bins,
    )
    return {"source": "master_view", "bins": curve}


# ── Drift Detection ─────────────────────────────────────────────


@app.get("/drift")
def drift_detection():
    conn = _get_db()
    try:
        try:
            live_df = pd.read_sql_query(
                "SELECT loan_amount, interest_rate, term_months, income, "
                "dti, credit_score, employment_length, "
                "mobile_credit_score, upi_transaction_count "
                "FROM ingested_loans", conn,
            )
            if len(live_df) == 0:
                live_df = pd.read_sql_query(
                    "SELECT loan_amount, interest_rate, term_months, income, "
                    "dti, credit_score, employment_length, "
                    "mobile_credit_score, upi_transaction_count "
                    "FROM master_view LIMIT 1000", conn,
                )
        except Exception:
            live_df = pd.read_sql_query(
                "SELECT loan_amount, interest_rate, term_months, income, "
                "dti, credit_score, employment_length, "
                "mobile_credit_score, upi_transaction_count "
                "FROM master_view LIMIT 1000", conn,
            )
    finally:
        conn.close()

    live_stats = {}
    for col in live_df.columns:
        series = live_df[col].dropna()
        if len(series) == 0:
            continue
        live_stats[col] = {
            "mean": float(series.mean()),
            "std": float(series.std()),
            "p1": float(series.quantile(0.01)),
            "p99": float(series.quantile(0.99)),
        }

    return detect_drift(live_stats, TRAINING_FEATURE_STATS)


# ── Fairness ────────────────────────────────────────────────────


@app.post("/fairness")
def fairness():
    conn = _get_db()
    try:
        try:
            df = pd.read_sql_query(
                "SELECT segment_name AS segment, COUNT(*) AS total, "
                "SUM(CASE WHEN decision='APPROVED' THEN 1 ELSE 0 END) AS approved, "
                "SUM(CASE WHEN actual_default=1 THEN 1 ELSE 0 END) AS defaulted "
                "FROM ingested_loans GROUP BY segment_name", conn,
            )
            if len(df) == 0:
                raise ValueError("empty")
        except Exception:
            df = pd.read_sql_query(
                "SELECT segment AS segment, total_loans AS total, "
                "approved_loans AS approved, defaulted_loans AS defaulted "
                "FROM segment_summary", conn,
            )
    finally:
        conn.close()

    segments = df.to_dict(orient="records")
    return compute_fairness_metrics(segments)


# ── Conformal Prediction ────────────────────────────────────────


@app.post("/conformal/predict")
def conformal_predict(borrower: BorrowerInput):
    models = require_ready()
    X, _, _, _ = engineer_features(borrower)
    X_scaled = models["scaler"].transform(X)
    prob = float(models["xgb_default"].predict_proba(X_scaled)[0][1])
    return predict_set(prob)


# ── Partner Adapters ────────────────────────────────────────────


@app.post("/partner/assess")
def partner_assess(req: PartnerRequest):
    models = require_ready()

    # Authenticate (simple API key check)
    if len(req.api_key) < 8:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Run LendIQ prediction
    pred_result = predict(req.borrower)

    # Translate via partner adapter
    adapter = get_adapter(req.partner)
    partner_body = adapter.build_request(req.borrower, pred_result)

    return {
        "partner": req.partner,
        "lendiq_assessment": {
            "decision": pred_result["approval"]["decision"],
            "default_probability": pred_result["risk"]["default_probability"],
            "recommended_rate": pred_result["pricing"]["recommended_rate"],
        },
        "partner_payload": partner_body,
        "callback_url": req.callback_url,
    }


@app.get("/partners")
def list_available_partners():
    return {"partners": list_partners()}


# ── Prediction Logs ─────────────────────────────────────────────


@app.get("/prediction-logs")
def prediction_logs(limit: int = Query(default=50, ge=1, le=1000)):
    conn = _get_db()
    try:
        logs = pd.read_sql_query(
            "SELECT * FROM prediction_logs ORDER BY id DESC LIMIT ?",
            conn, params=(limit,),
        )
    finally:
        conn.close()
    return logs.to_dict(orient="records")


# ── Background Tasks ─────────────────────────────────────────────


@app.post("/tasks/{task_type}", dependencies=[Depends(require_operator)])
def create_task(task_type: str):
    valid_types = ["shap", "drift"]
    if task_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Task type must be one of {valid_types}")
    task_id = enqueue(task_type)
    return {"task_id": task_id, "type": task_type, "status": "pending"}


@app.get("/tasks", dependencies=[Depends(require_viewer)])
def list_all_tasks(limit: int = Query(default=20, ge=1, le=100)):
    return {"tasks": list_tasks(limit)}


@app.get("/tasks/{task_id}", dependencies=[Depends(require_viewer)])
def get_task_status(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
