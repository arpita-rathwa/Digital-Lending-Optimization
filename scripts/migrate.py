"""Alembic-style migration runner for LendIQ.

Since Alembic requires a proper env setup and the database is SQLite,
this provides a simplified migration system that tracks applied migrations.

Usage:
    py -m scripts.migrate list      # list all migrations
    py -m scripts.migrate up        # apply pending migrations
    py -m scripts.migrate down [id] # revert one migration
"""

from __future__ import annotations

import os
import sqlite3
import sys

DB_PATH = "digital_lending.db"

MIGRATIONS = []


def _get_db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT UNIQUE NOT NULL,"
        "applied_at TEXT DEFAULT (datetime('now'))"
        ")"
    )
    conn.commit()


def _applied(conn: sqlite3.Connection) -> set[str]:
    try:
        cursor = conn.execute("SELECT name FROM _migrations ORDER BY id")
        return {row[0] for row in cursor.fetchall()}
    except Exception:
        return set()


def register(name: str, up: str, down: str | None = None) -> None:
    MIGRATIONS.append({"name": name, "up": up, "down": down})


# ── Migration definitions ────────────────────────────────────────

register(
    "001_initial_schema",
    up="""
    CREATE TABLE IF NOT EXISTS prediction_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, loan_amount REAL, term_months REAL, income REAL,
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
    down="DROP TABLE IF EXISTS prediction_logs",
)

register(
    "002_ingested_loans",
    up="""
    CREATE TABLE IF NOT EXISTS ingested_loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id TEXT, lending_medium TEXT, loan_amount REAL,
        interest_rate REAL, term_months REAL, income REAL,
        dti REAL, credit_score REAL, default_probability REAL,
        recommended_rate REAL, segment_name TEXT, cluster INTEGER,
        decision TEXT, actual_default INTEGER, ingested_at TEXT
    )
    """,
    down="DROP TABLE IF EXISTS ingested_loans",
)

register(
    "003_loan_outcomes",
    up="""
    CREATE TABLE IF NOT EXISTS loan_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id TEXT, actual_default INTEGER,
        actual_loss REAL, recorded_at TEXT
    )
    """,
    down="DROP TABLE IF EXISTS loan_outcomes",
)

register(
    "004_api_keys",
    up="""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT UNIQUE NOT NULL,
        label TEXT DEFAULT '',
        role TEXT DEFAULT 'viewer',
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        last_used_at TEXT
    )
    """,
    down="DROP TABLE IF EXISTS api_keys",
)

register(
    "005_users",
    up="""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'viewer',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    down="DROP TABLE IF EXISTS users",
)

register(
    "006_drift_results",
    up="""
    CREATE TABLE IF NOT EXISTS drift_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        computed_at TEXT, result TEXT
    )
    """,
    down="DROP TABLE IF EXISTS drift_results",
)


# ── CLI ──────────────────────────────────────────────────────────

def list_migrations() -> None:
    if not os.path.exists(DB_PATH):
        print("No database found.")
        return
    conn = _get_db()
    try:
        _ensure_migrations_table(conn)
        applied = _applied(conn)
    finally:
        conn.close()

    print(f"{'Name':50s} {'Status':12s}")
    print("-" * 62)
    for m in MIGRATIONS:
        status = "APPLIED" if m["name"] in applied else "PENDING"
        print(f"{m['name']:50s} {status:12s}")


def apply_pending() -> None:
    conn = _get_db()
    try:
        _ensure_migrations_table(conn)
        applied = _applied(conn)
        for m in MIGRATIONS:
            if m["name"] in applied:
                continue
            print(f"Applying {m['name']}...")
            conn.executescript(m["up"])
            conn.execute("INSERT INTO _migrations (name) VALUES (?)", (m["name"],))
            conn.commit()
            print(f"  Done.")
    finally:
        conn.close()


def revert(name: str) -> None:
    conn = _get_db()
    try:
        _ensure_migrations_table(conn)
        for m in MIGRATIONS:
            if m["name"] == name and m["down"]:
                print(f"Reverting {name}...")
                conn.executescript(m["down"])
                conn.execute("DELETE FROM _migrations WHERE name=?", (name,))
                conn.commit()
                print(f"  Done.")
                return
        print(f"Migration '{name}' not found or has no down migration.")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py -m scripts.migrate [list|up|down <name>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        list_migrations()
    elif cmd == "up":
        apply_pending()
    elif cmd == "down" and len(sys.argv) > 2:
        revert(sys.argv[2])
    else:
        print("Unknown command.")
