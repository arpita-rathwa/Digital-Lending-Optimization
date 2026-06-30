"""Additional unit tests for new modules — conformal, calibrate, drift, fairness, auth."""

import numpy as np
import pytest

from lendiql.calibrate import calibrate_proba, compute_reliability_curve
from lendiql.conformal import predict_set
from lendiql.drift import detect_drift
from lendiql.fairness import compute_fairness_metrics
from lendiql.early_warning import adverse_action_reasons, segment_approval_threshold
from lendiql.features import validate_features
from lendiql.schemas import BorrowerInput


# ── Conformal Prediction ─────────────────────────────────────────

class TestConformal:
    def test_high_confidence_singleton(self):
        result = predict_set(0.95, alpha=0.1)
        assert result["predicted_class"] == 1
        assert result["prediction_set"] == [1]
        assert result["credible"] is True

    def test_low_confidence_both_classes(self):
        # Force non-conformity > q_hat by using probability near 0.5
        result = predict_set(0.55, alpha=0.1)
        assert result["predicted_class"] == 1
        assert result["credible"] is False

    def test_non_default_prediction(self):
        result = predict_set(0.05, alpha=0.1)
        assert result["predicted_class"] == 0
        assert result["predicted_label"] == "NON_DEFAULT"

    def test_shape_matches_schema(self):
        result = predict_set(0.3, alpha=0.1)
        for key in ("predicted_class", "predicted_label", "probability",
                     "non_conformity_score", "q_hat", "credible",
                     "prediction_set", "significance_level"):
            assert key in result


# ── Calibration ──────────────────────────────────────────────────

class TestCalibration:
    def test_calibrate_proba_monotonic(self):
        """Calibrated probabilities should preserve order."""
        probs = [0.1, 0.3, 0.5, 0.7, 0.9]
        calibrated = [calibrate_proba(p) for p in probs]
        for i in range(len(calibrated) - 1):
            assert calibrated[i] <= calibrated[i + 1]

    def test_calibrate_proba_bounds(self):
        for p in [0.0, 0.01, 0.5, 0.99, 1.0]:
            cp = calibrate_proba(p)
            assert 0.0 <= cp <= 1.0

    def test_reliability_curve_empty(self):
        curve = compute_reliability_curve(
            np.array([]), np.array([]), n_bins=5,
        )
        assert curve == []

    def test_reliability_curve_perfect(self):
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.1, 0.2, 0.8, 0.9])
        curve = compute_reliability_curve(y_true, y_prob, n_bins=10)
        assert len(curve) > 0
        for b in curve:
            assert "bin_center" in b
            assert "fraction_of_positives" in b
            assert "count" in b


# ── Drift Detection ──────────────────────────────────────────────

class TestDrift:
    def test_detect_no_drift(self):
        stats = {
            "loan_amount": {"mean": 12500, "std": 15000, "p1": 500, "p99": 75000},
            "income": {"mean": 48000, "std": 35000, "p1": 5000, "p99": 180000},
        }
        # Same values = no drift
        result = detect_drift(stats, stats)
        assert result["status"] == "stable"
        assert result["drift_score"] == 0.0

    def test_detect_drift_high(self):
        train_stats = {
            "loan_amount": {"mean": 12500, "std": 1000, "p1": 500, "p99": 75000},
        }
        live_stats = {
            "loan_amount": {"mean": 50000, "std": 1000, "p1": 500, "p99": 75000},
        }
        result = detect_drift(live_stats, train_stats)
        assert result["features"][0]["drifted"] is True

    def test_result_shape(self):
        result = detect_drift(
            {"loan_amount": {"mean": 13000, "std": 16000, "p1": 600, "p99": 80000}},
            {"loan_amount": {"mean": 12500, "std": 15000, "p1": 500, "p99": 75000}},
        )
        for key in ("drift_score", "status", "features_drifted", "features_total", "features"):
            assert key in result


# ── Fairness ─────────────────────────────────────────────────────

class TestFairness:
    def test_basic_fairness(self):
        segments = [
            {"segment": "A", "total": 100, "approved": 80, "defaulted": 5},
            {"segment": "B", "total": 100, "approved": 60, "defaulted": 15},
            {"segment": "C", "total": 100, "approved": 40, "defaulted": 25},
        ]
        result = compute_fairness_metrics(segments)
        assert result["overall_approval_rate"] == pytest.approx(0.6)
        assert result["reference_group_approval_rate"] == pytest.approx(0.8)
        assert len(result["segments"]) == 3
        assert result["segments"][0]["four_fifths_violation"] is False

    def test_four_fifths_violation(self):
        segments = [
            {"segment": "A", "total": 100, "approved": 80, "defaulted": 5},
            {"segment": "B", "total": 100, "approved": 30, "defaulted": 25},
        ]
        result = compute_fairness_metrics(segments)
        seg_b = [s for s in result["segments"] if s["segment"] == "B"][0]
        assert seg_b["four_fifths_violation"] is True
        assert seg_b["adverse_impact_ratio"] < 0.80

    def test_empty_segments(self):
        result = compute_fairness_metrics([])
        assert "error" in result


# ── Adverse Action Reasons ───────────────────────────────────────

class TestAdverseAction:
    def test_known_flags(self):
        reasons = adverse_action_reasons(["HIGH_DTI", "LOW_MOBILE_SCORE"])
        assert len(reasons) == 2
        assert reasons[0]["code"] == "HIGH_DTI"
        assert "exceeds" in reasons[0]["reason"].lower()

    def test_unknown_flag(self):
        reasons = adverse_action_reasons(["UNKNOWN_FLAG"])
        assert reasons[0]["reason"] == "Other"

    def test_empty_flags(self):
        assert adverse_action_reasons([]) == []


# ── Segment Thresholds ───────────────────────────────────────────

class TestSegmentThresholds:
    def test_known_cluster(self):
        assert segment_approval_threshold(0) == 0.35
        assert segment_approval_threshold(3) == 0.65

    def test_unknown_cluster_fallback(self):
        assert segment_approval_threshold(99) == 0.50


# ── Feature Validation ───────────────────────────────────────────

class TestFeatureValidation:
    def test_valid_features_no_warnings(self):
        b = BorrowerInput(
            loan_amount=10000, term_months=24, income=50000,
            dti=20, credit_score=700, employment_length=5,
            home_ownership="RENT", lending_medium="Bank",
            digital_onboarding=0, upi_transaction_count=30,
            mobile_credit_score=650, first_time_borrower=0, urban_flag=1,
        )
        warnings = validate_features(b)
        assert len(warnings) == 0

    def test_out_of_range_triggers_warning(self):
        b = BorrowerInput(
            loan_amount=1_000_000, term_months=24, income=50000,
            dti=20, credit_score=700, employment_length=5,
            home_ownership="RENT", lending_medium="Bank",
            digital_onboarding=0, upi_transaction_count=30,
            mobile_credit_score=650, first_time_borrower=0, urban_flag=1,
        )
        warnings = validate_features(b)
        assert len(warnings) > 0  # loan_amount exceeds p99
