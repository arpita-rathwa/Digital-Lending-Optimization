"""API-level tests using FastAPI's TestClient.

These tests run against the actual HTTP surface and verify response shape
and the critical risk_tier / default_probability consistency contract.

They DO require the trained models (``models/*.pkl``) to be present.
Skip this file in environments where models aren't available.
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.path.exists("models/xgb_default.pkl"),
    reason="Trained models not available in this environment",
)

from fastapi.testclient import TestClient

from lendiql.app import app

client = TestClient(app)


def test_root_returns_200():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert "status" in body


def test_predict_response_shape():
    payload = {
        "loan_amount": 15_000,
        "term_months": 36,
        "income": 60_000,
        "dti": 25.0,
        "credit_score": 720,
        "employment_length": 5.0,
        "home_ownership": "MORTGAGE",
        "lending_medium": "Bank",
        "digital_onboarding": 1,
        "upi_transaction_count": 45,
        "mobile_credit_score": 680,
        "first_time_borrower": 0,
        "urban_flag": 1,
        "interest_rate": 11.0,
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 200, r.text

    body = r.json()

    for key in ("approval", "risk", "pricing", "segment"):
        assert key in body, f"missing key: {key}"

    assert "approved" in body["approval"]
    assert "decision" in body["approval"]
    assert "threshold_used" in body["approval"]
    assert body["approval"]["threshold_used"] == 0.5
    assert body["approval"]["threshold_type"] == "individual"

    risk = body["risk"]
    assert 0.0 <= risk["default_probability"] <= 1.0
    assert risk["risk_tier"] in {"Low", "Medium", "High"}
    assert risk["early_warning"] in {"HEALTHY", "WATCH", "WARNING", "CRITICAL"}
    assert isinstance(risk["warning_flags"], list)

    pricing = body["pricing"]
    assert 6.0 <= pricing["recommended_rate"] <= 36.0
    assert pricing["rate_adjustment"] == pytest.approx(
        pricing["recommended_rate"] - pricing["current_rate"], abs=1e-6
    )

    assert "cluster" in body["segment"]
    assert "name" in body["segment"]


def test_risk_tier_matches_probability():
    payload = {
        "loan_amount": 15_000,
        "term_months": 36,
        "income": 60_000,
        "dti": 25.0,
        "credit_score": 720,
        "employment_length": 5.0,
        "home_ownership": "MORTGAGE",
        "lending_medium": "Bank",
        "digital_onboarding": 1,
        "upi_transaction_count": 45,
        "mobile_credit_score": 680,
        "first_time_borrower": 0,
        "urban_flag": 1,
        "interest_rate": 11.0,
    }
    body = client.post("/predict", json=payload).json()
    p = body["risk"]["default_probability"]
    tier = body["risk"]["risk_tier"]

    if p < 0.25:
        assert tier == "Low", f"p={p} should be Low, got {tier}"
    elif p < 0.5:
        assert tier == "Medium", f"p={p} should be Medium, got {tier}"
    else:
        assert tier == "High", f"p={p} should be High, got {tier}"


def test_approval_decision_matches_threshold():
    payload = {
        "loan_amount": 200_000,
        "term_months": 60,
        "income": 25_000,
        "dti": 60.0,
        "credit_score": 520,
        "employment_length": 0.5,
        "home_ownership": "RENT",
        "lending_medium": "SME",
        "digital_onboarding": 0,
        "upi_transaction_count": 0,
        "mobile_credit_score": 480,
        "first_time_borrower": 1,
        "urban_flag": 0,
        "interest_rate": 14.0,
    }
    body = client.post("/predict", json=payload).json()
    p = body["risk"]["default_probability"]
    approved = body["approval"]["approved"]

    if p >= 0.5:
        assert approved is False
        assert body["approval"]["decision"] == "DECLINED"


def test_invalid_payload_rejected():
    r = client.post("/predict", json={"loan_amount": "not a number"})
    assert r.status_code == 422


def test_early_warning_limit_param():
    r = client.get("/early-warning?limit=10")
    if r.status_code == 200:
        body = r.json()
        assert "queue" in body
        assert "distribution" in body
        assert len(body["queue"]) <= 10
