"""Background task worker — runs heavy computations (SHAP, drift, retraining) asynchronously.

Usage:
    python -m lendiql.worker
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from lendiql.config import DB_PATH, FEATURE_NAMES, TRAINING_FEATURE_STATS
from lendiql.drift import detect_drift


# ── In-memory task queue ─────────────────────────────────────────

_tasks: dict[str, dict[str, Any]] = {}


def enqueue(task_type: str, payload: dict | None = None) -> str:
    task_id = f"{task_type}_{int(time.time() * 1000)}_{len(_tasks)}"
    _tasks[task_id] = {
        "id": task_id,
        "type": task_type,
        "status": "pending",
        "payload": payload or {},
        "result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    return task_id


def get_task(task_id: str) -> dict | None:
    return _tasks.get(task_id)


def list_tasks(limit: int = 20) -> list[dict]:
    return sorted(_tasks.values(), key=lambda t: t["created_at"], reverse=True)[:limit]


# ── Worker Loop ──────────────────────────────────────────────────


async def _process_shap() -> None:
    """Placeholder: SHAP waterfall computation runs inline in the API."""
    pass


async def _process_drift() -> None:
    """Recompute drift from ingested_loans and store result."""
    conn = sqlite3.connect(DB_PATH)
    try:
        live_df = pd.read_sql_query(
            "SELECT loan_amount, interest_rate, term_months, income, "
            "dti, credit_score, employment_length, "
            "mobile_credit_score, upi_transaction_count "
            "FROM ingested_loans", conn,
        )
    except Exception:
        live_df = pd.DataFrame()
    finally:
        conn.close()

    if len(live_df) == 0:
        return

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

    result = detect_drift(live_stats, TRAINING_FEATURE_STATS)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS drift_results ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "computed_at TEXT, result TEXT)"
        )
        conn.execute(
            "INSERT INTO drift_results (computed_at, result) VALUES (?, ?)",
            (datetime.now(timezone.utc).isoformat(), json.dumps(result)),
        )
        conn.commit()
    finally:
        conn.close()


_task_handlers = {
    "shap": _process_shap,
    "drift": _process_drift,
}


async def _worker_loop(interval: float = 30.0) -> None:
    """Poll for pending tasks every N seconds."""
    while True:
        for task_id, task in list(_tasks.items()):
            if task["status"] != "pending":
                continue
            task["status"] = "running"
            handler = _task_handlers.get(task["type"])
            if handler:
                try:
                    await handler()
                    task["status"] = "completed"
                except Exception as e:
                    task["status"] = "failed"
                    task["result"] = str(e)
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
        await asyncio.sleep(interval)


def start_worker(interval: float = 30.0) -> asyncio.Task:
    """Launch the background worker as an asyncio task."""
    loop = asyncio.get_event_loop()
    return loop.create_task(_worker_loop(interval))
