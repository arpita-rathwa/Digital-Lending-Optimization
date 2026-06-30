"""Authentication — JWT tokens + API key management."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from typing import Optional

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from lendiql.config import DB_PATH

TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
security = HTTPBearer(auto_error=False)


# ── API Key Hashing ──────────────────────────────────────────────

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate (raw_key, hashed_key). Return raw key to the user once."""
    raw = f"lq_{secrets.token_hex(24)}"
    return raw, hash_api_key(raw)


def _get_db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_auth_db() -> None:
    """Create the auth tables if they don't exist."""
    conn = _get_db()
    try:
        conn.execute(
            """
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
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,
        )
        conn.commit()
    finally:
        conn.close()


def validate_api_key(key: str) -> Optional[dict]:
    """Check an API key against the DB. Returns key info or None."""
    conn = _get_db()
    try:
        h = hash_api_key(key)
        cursor = conn.execute(
            "SELECT id, label, role FROM api_keys WHERE key_hash=? AND active=1",
            (h,),
        )
        row = cursor.fetchone()
        if row:
            conn.execute(
                "UPDATE api_keys SET last_used_at=datetime('now') WHERE id=?",
                (row[0],),
            )
            conn.commit()
            return {"id": row[0], "label": row[1], "role": row[2]}
        # Also check for a master key env var
        master = os.getenv("LENDIQ_MASTER_KEY")
        if master and hmac.compare_digest(key, master):
            return {"id": 0, "label": "master", "role": "admin"}
        return None
    finally:
        conn.close()


def require_role(required: str = "viewer"):
    """Dependency factory — requires a valid API key with a minimum role.

    Role hierarchy: viewer < operator < admin
    """
    roles = {"viewer": 0, "operator": 1, "admin": 2}

    def _dependency(
        authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
        x_api_key: Optional[str] = Header(default=None),
    ):
        key = None
        if authorization:
            key = authorization.credentials
        elif x_api_key:
            key = x_api_key

        if not key:
            raise HTTPException(status_code=401, detail="Missing API key")

        info = validate_api_key(key)
        if info is None:
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

        user_level = roles.get(info["role"], -1)
        required_level = roles.get(required, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{info['role']}' insufficient. Required: '{required}'",
            )
        return info

    return _dependency


require_viewer = require_role("viewer")
require_operator = require_role("operator")
require_admin = require_role("admin")


# ── API Key Management Endpoints (injected into app.py) ──────────

def register_auth_routes(app) -> None:
    from fastapi import APIRouter, Body

    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post("/keys", dependencies=[Depends(require_admin)])
    def create_api_key(label: str = Body(""), role: str = Body("viewer")):
        raw, hashed = generate_api_key()
        conn = _get_db()
        try:
            conn.execute(
                "INSERT INTO api_keys (key_hash, label, role) VALUES (?, ?, ?)",
                (hashed, label, role),
            )
            conn.commit()
        finally:
            conn.close()
        return {"api_key": raw, "label": label, "role": role}

    @router.get("/keys", dependencies=[Depends(require_admin)])
    def list_api_keys():
        conn = _get_db()
        try:
            cursor = conn.execute(
                "SELECT id, label, role, active, created_at, last_used_at FROM api_keys"
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [
            {
                "id": r[0], "label": r[1], "role": r[2],
                "active": bool(r[3]), "created_at": r[4], "last_used_at": r[5],
            }
            for r in rows
        ]

    @router.delete("/keys/{key_id}", dependencies=[Depends(require_admin)])
    def revoke_api_key(key_id: int):
        conn = _get_db()
        try:
            conn.execute("UPDATE api_keys SET active=0 WHERE id=?", (key_id,))
            conn.commit()
        finally:
            conn.close()
        return {"revoked": key_id}

    app.include_router(router)
