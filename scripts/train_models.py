"""Retrain all ML models for LendIQ with regularization, calibration, and explainability."""

import os, sqlite3, pickle, warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore")
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODELS_DIR = "models"
DB_PATH = "digital_lending.db"
SAMPLE_SIZE = 100_000
RANDOM_STATE = 42
TEST_SIZE = 0.2

FEATURES = [
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

print("Loading data from SQLite...")
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM loans", conn)
conn.close()
print(f"Loaded: {df.shape}")

HOME_OWNERSHIP_MAP = {"RENT": 3, "OWN": 2, "MORTGAGE": 1, "BUSINESS": 0, "UNKNOWN": 4}
MEDIUM_MAP = {"Bank": 0, "Microfinance": 1, "P2P": 2, "SME": 3}
df["home_ownership_enc"] = df["home_ownership"].map(HOME_OWNERSHIP_MAP).fillna(4)
df["lending_medium_enc"] = df["lending_medium"].map(MEDIUM_MAP).fillna(0)
df["loan_size_enc"] = df["loan_size"].map({"Micro": 0, "Small": 1, "Medium": 2, "Large": 3}).fillna(0).astype(int)
df["credit_tier_enc"] = df["credit_tier"].map({"Poor": 0, "Fair": 1, "Good": 2, "Very Good": 3, "Exceptional": 4, "Unknown": -1}).fillna(-1).astype(int)
df["income_segment_enc"] = df["income_segment"].map({"Low": 0, "Middle": 1, "Upper Middle": 2, "High": 3, "Unknown": -1}).fillna(-1).astype(int)

X = df[FEATURES].copy()
y_default = df["default"]
y_risk = df["risk_tier"].map({"Low": 0, "Medium": 1, "High": 2})
y_loss = df["expected_loss"]

sample_idx = df.sample(SAMPLE_SIZE, random_state=RANDOM_STATE).index
X_sample = X.loc[sample_idx]
y_default_sample = y_default.loc[sample_idx]
y_risk_sample = y_risk.loc[sample_idx]
y_loss_sample = y_loss.loc[sample_idx]

default_rate = y_default_sample.mean()
print(f"Default rate in sample: {default_rate:.3f}")

print("Fitting scaler...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_sample)

X_train_s, X_test_s, y_train_d, y_test_d = train_test_split(
    X_scaled, y_default_sample, test_size=TEST_SIZE, random_state=RANDOM_STATE
)
_, _, y_train_r, y_test_r = train_test_split(
    X_sample, y_risk_sample, test_size=TEST_SIZE, random_state=RANDOM_STATE
)
_, _, y_train_l, y_test_l = train_test_split(
    X_sample, y_loss_sample, test_size=TEST_SIZE, random_state=RANDOM_STATE
)

print("Training XGBoost default classifier...")
scale_pos_weight = (1 - default_rate) / max(default_rate, 0.001)
xgb_default = XGBClassifier(
    n_estimators=500, max_depth=4, learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    reg_lambda=3.0, reg_alpha=1.0,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric="logloss", early_stopping_rounds=20,
    random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
)
xgb_default.fit(X_train_s, y_train_d, eval_set=[(X_test_s, y_test_d)], verbose=False)
preds = xgb_default.predict(X_test_s)
acc = (preds == y_test_d).mean()
recall = ((preds == 1) & (y_test_d == 1)).sum() / max((y_test_d == 1).sum(), 1)
print(f"  Accuracy: {acc:.4f}, Default Recall: {recall:.4f}")

print("Training XGBoost risk tier classifier...")
xgb_risk = XGBClassifier(
    n_estimators=500, max_depth=4, learning_rate=0.05,
    objective="multi:softprob", num_class=3,
    reg_lambda=3.0, reg_alpha=1.0,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric="mlogloss", early_stopping_rounds=20,
    random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
)
xgb_risk.fit(X_train_s, y_train_r, eval_set=[(X_test_s, y_test_r)], verbose=False)

print("Training XGBoost expected loss regressor...")
xgb_loss = XGBRegressor(
    n_estimators=500, max_depth=4, learning_rate=0.05,
    reg_lambda=3.0, reg_alpha=1.0,
    subsample=0.8, colsample_bytree=0.8,
    eval_metric="mae", early_stopping_rounds=20,
    random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
)
xgb_loss.fit(X_train_s, y_train_l, eval_set=[(X_test_s, y_test_l)], verbose=False)

cluster_idx = df.sample(50_000, random_state=RANDOM_STATE).index
X_cluster = df.loc[cluster_idx, CLUSTER_FEATURES].copy()
print("Fitting cluster scaler...")
cluster_scaler = StandardScaler()
X_cluster_scaled = cluster_scaler.fit_transform(X_cluster)

print("Training K-Means (K=5)...")
kmeans = KMeans(n_clusters=5, random_state=RANDOM_STATE, n_init=10)
kmeans.fit(X_cluster_scaled)

os.makedirs(MODELS_DIR, exist_ok=True)
artifacts = {
    "xgb_default": xgb_default, "xgb_risk": xgb_risk, "xgb_loss": xgb_loss,
    "scaler": scaler, "kmeans": kmeans, "cluster_scaler": cluster_scaler,
}
for name, obj in artifacts.items():
    path = os.path.join(MODELS_DIR, f"{name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"  {name}.pkl — {os.path.getsize(path):,} bytes")

# ── Platt Scaling (Calibration) ─────────────────────────────────
print("\nTraining Platt calibrator...")
cal_proba = xgb_default.predict_proba(X_test_s)[:, 1]
calibrator = LogisticRegression()
calibrator.fit(cal_proba.reshape(-1, 1), y_test_d)
with open(os.path.join(MODELS_DIR, "calibrator.pkl"), "wb") as f:
    pickle.dump(calibrator, f)
print(f"  calibrator.pkl saved")

# ── Conformal Prediction — Non-conformity Scores ────────────────
print("\nComputing conformal non-conformity scores...")
val_idx = df.sample(10_000, random_state=RANDOM_STATE).index
X_val = scaler.transform(X.loc[val_idx])
y_val = y_default.loc[val_idx]
val_proba = xgb_default.predict_proba(X_val)[:, 1]
ncf_scores = 1.0 - np.maximum(val_proba, 1.0 - val_proba)
alpha = 0.1
q_hat = float(np.quantile(ncf_scores, 1 - alpha))
conformal_data = {"q_hat": q_hat, "n_scores": len(ncf_scores), "alpha": alpha}
with open(os.path.join(MODELS_DIR, "conformal_scores.pkl"), "wb") as f:
    pickle.dump(conformal_data, f)
print(f"  conformal_scores.pkl — q_hat={q_hat:.4f} at alpha={alpha}")

# ── Feature Statistics for Drift Detection ──────────────────────
print("\nComputing training feature statistics...")
stats = {}
for col in FEATURES:
    if col not in X.columns:
        continue
    series = X[col]
    stats[col] = {
        "mean": round(float(series.mean()), 2),
        "std": round(float(series.std()), 2),
        "p1": round(float(series.quantile(0.01)), 2),
        "p99": round(float(series.quantile(0.99)), 2),
    }

# Write to config import (human-readable summary)
import json
stats_path = os.path.join(MODELS_DIR, "feature_stats.json")
with open(stats_path, "w") as f:
    json.dump(stats, f, indent=2)
print(f"  feature_stats.json — {len(stats)} features")

# ── Training Median Rates ──────────────────────────────────────
print("\nComputing training median rates by medium...")
median_rates = df.groupby("lending_medium")["interest_rate"].median().to_dict()
print(f"  median rates: {median_rates}")

# ── SHAP Importance (global) ───────────────────────────────────
print("\nComputing global SHAP importance...")
try:
    import shap
    explainer = shap.TreeExplainer(xgb_default)
    shap_vals = explainer.shap_values(X_test_s[:1000])
    mean_abs_shap = np.abs(shap_vals).mean(axis=0)
    shap_importance = pd.DataFrame({
        "feature": FEATURES[:len(mean_abs_shap)],
        "importance": mean_abs_shap,
    }).sort_values("importance", ascending=False)

    conn = sqlite3.connect(DB_PATH)
    shap_importance.to_sql("shap_importance", conn, if_exists="replace", index=False)
    conn.close()
    print(f"  SHAP importance written to DB ({len(shap_importance)} features)")
except Exception as e:
    print(f"  SHAP computation skipped: {e}")

print("\nTraining complete. All artifacts saved.")
