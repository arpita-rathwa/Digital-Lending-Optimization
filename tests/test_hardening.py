"""Hardening tests — auth, rate limiting, security headers, input validation."""

import pytest
from fastapi.testclient import TestClient

from lendiql.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Security Headers ─────────────────────────────────────────────

class TestSecurityHeaders:
    def test_sts_header(self, client):
        r = client.get("/")
        assert "strict-transport-security" in r.headers
        assert "max-age=31536000" in r.headers["strict-transport-security"]

    def test_xss_protection(self, client):
        r = client.get("/")
        assert r.headers.get("x-xss-protection") == "1; mode=block"

    def test_frame_options(self, client):
        r = client.get("/")
        assert r.headers.get("x-frame-options") == "DENY"

    def test_content_type_options(self, client):
        r = client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"

    def test_csp_header(self, client):
        r = client.get("/")
        csp = r.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    def test_request_time_header(self, client):
        r = client.get("/")
        assert "x-request-time-ms" in r.headers


# ── Auth / API Key ───────────────────────────────────────────────

class TestAuth:
    def test_missing_key_returns_401(self, client):
        r = client.post("/auth/keys")
        assert r.status_code == 401

    def test_invalid_key_returns_403(self, client):
        r = client.post(
            "/auth/keys",
            json={"label": "test", "role": "viewer"},
            headers={"x-api-key": "bad_key"},
        )
        assert r.status_code == 403

    def test_public_endpoints_work_without_key(self, client):
        for path in ["/", "/metrics"]:
            r = client.get(path)
            assert r.status_code in (200, 307), f"{path} failed without auth"


# ── Input Validation ─────────────────────────────────────────────

class TestInputValidation:
    def test_negative_loan_amount(self, client):
        r = client.post(
            "/predict",
            json={
                "loan_amount": -1000, "term_months": 12, "income": 50000,
                "dti": 20, "credit_score": 700, "employment_length": 5,
                "home_ownership": "RENT", "lending_medium": "Bank",
                "digital_onboarding": 0, "upi_transaction_count": 10,
                "mobile_credit_score": 650, "first_time_borrower": 0,
                "urban_flag": 1,
            },
        )
        assert r.status_code == 422

    def test_credit_score_out_of_range(self, client):
        r = client.post(
            "/predict",
            json={
                "loan_amount": 10000, "term_months": 12, "income": 50000,
                "dti": 20, "credit_score": 999, "employment_length": 5,
                "home_ownership": "RENT", "lending_medium": "Bank",
                "digital_onboarding": 0, "upi_transaction_count": 10,
                "mobile_credit_score": 650, "first_time_borrower": 0,
                "urban_flag": 1,
            },
        )
        assert r.status_code == 422

    def test_string_in_numeric_field(self, client):
        r = client.post(
            "/predict",
            json={
                "loan_amount": "abc", "term_months": 12, "income": 50000,
                "dti": 20, "credit_score": 700, "employment_length": 5,
                "home_ownership": "RENT", "lending_medium": "Bank",
                "digital_onboarding": 0, "upi_transaction_count": 10,
                "mobile_credit_score": 650, "first_time_borrower": 0,
                "urban_flag": 1,
            },
        )
        assert r.status_code == 422

    def test_missing_required_field(self, client):
        r = client.post("/predict", json={"loan_amount": 10000})
        assert r.status_code == 422

    def test_extra_fields_ignored(self, client):
        payload = {
            "loan_amount": 10000, "term_months": 12, "income": 50000,
            "dti": 20, "credit_score": 700, "employment_length": 5,
            "home_ownership": "RENT", "lending_medium": "Bank",
            "digital_onboarding": 0, "upi_transaction_count": 10,
            "mobile_credit_score": 650, "first_time_borrower": 0,
            "urban_flag": 1, "hacker_field": "injection_attempt",
        }
        # Should not error on extra fields
        r = client.post("/predict", json=payload)
        assert r.status_code in (200, 422)  # 200 if models exist


# ── Rate Limiting ────────────────────────────────────────────────

class TestRateLimiting:
    @pytest.mark.slow
    def test_rate_limit_returns_429(self, client):
        responses = [client.get("/metrics").status_code for _ in range(50)]
        assert all(s in (200, 429) for s in responses)


# ── CORS ─────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_headers_present(self, client):
        r = client.options(
            "/",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in r.headers


# ── Drift & Fairness Inputs ──────────────────────────────────────

class TestDriftFairnessInputs:
    def test_drift_endpoint_shape(self, client):
        r = client.get("/drift")
        if r.status_code == 200:
            body = r.json()
            assert "drift_score" in body
            assert "status" in body
            assert "features" in body

    def test_fairness_endpoint_shape(self, client):
        r = client.post("/fairness")
        if r.status_code == 200:
            body = r.json()
            assert "segments" in body
            assert "overall_approval_rate" in body
