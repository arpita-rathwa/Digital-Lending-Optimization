from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import numpy as np
import sqlite3
import pandas as pd
from typing import Optional
import gdown
import os

# ── Download DB if not present ───────────────────────────
DB_PATH = 'digital_lending.db'
if not os.path.exists(DB_PATH):
    print("Downloading database...")
    gdown.download(
        'https://drive.google.com/uc?id=1kCqmBCDvVwVY8RQ5NDLiVQzfTDZFa5MS',
        DB_PATH,
        quiet=False
    )
    print("Database downloaded!")
app = FastAPI(title="Digital Lending Optimization API")

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Load Models ──────────────────────────────────────────
with open('models/xgb_default.pkl', 'rb') as f:
    xgb_default = pickle.load(f)

with open('models/xgb_risk.pkl', 'rb') as f:
    xgb_risk = pickle.load(f)

with open('models/xgb_loss.pkl', 'rb') as f:
    xgb_loss = pickle.load(f)

with open('models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

with open('models/kmeans.pkl', 'rb') as f:
    kmeans = pickle.load(f)

with open('models/cluster_scaler.pkl', 'rb') as f:
    cluster_scaler = pickle.load(f)

# ── Segment Names ─────────────────────────────────────────
segment_names = {
    0: 'First-Time Micro Borrowers',
    1: 'High-Value Stressed',
    2: 'Rural Micro Borrowers',
    3: 'Urban Established',
    4: 'High-Income Large Borrowers'
}

# ── Feature Names ─────────────────────────────────────────
features = [
    'loan_amount', 'interest_rate', 'term_months', 'income',
    'dti', 'credit_score', 'employment_length',
    'loan_to_income', 'monthly_burden', 'high_dti_flag',
    'long_term_flag', 'cost_of_credit', 'risk_interaction',
    'digital_onboarding', 'upi_transaction_count',
    'mobile_credit_score', 'first_time_borrower', 'urban_flag',
    'home_ownership_enc', 'lending_medium_enc',
    'loan_size_enc', 'credit_tier_enc', 'income_segment_enc'
]

cluster_features = [
    'loan_amount', 'interest_rate', 'term_months',
    'income', 'dti', 'loan_to_income', 'monthly_burden',
    'mobile_credit_score', 'upi_transaction_count',
    'digital_onboarding', 'first_time_borrower', 'urban_flag'
]

# ── Request Schema ────────────────────────────────────────
class BorrowerInput(BaseModel):
    loan_amount: float
    term_months: float
    income: float
    dti: float
    credit_score: float
    employment_length: float
    home_ownership: str  # RENT, OWN, MORTGAGE, BUSINESS, UNKNOWN
    lending_medium: str  # P2P, Bank, Microfinance, SME
    digital_onboarding: int  # 0 or 1
    upi_transaction_count: int
    mobile_credit_score: float
    first_time_borrower: int  # 0 or 1
    urban_flag: int  # 0 or 1
    interest_rate: Optional[float] = None

# ── Helper: Engineer Features ─────────────────────────────
def engineer_features(data: BorrowerInput) -> np.ndarray:
    # Derived features
    loan_to_income = data.loan_amount / (data.income + 1)
    monthly_burden = data.loan_amount / (data.term_months + 1)
    high_dti_flag = int(data.dti > 35)
    long_term_flag = int(data.term_months > 36)

    # Interest rate default by medium
    rate_defaults = {'P2P': 13.5, 'Bank': 11.0, 'Microfinance': 8.0, 'SME': 14.0}
    interest_rate = data.interest_rate or rate_defaults.get(data.lending_medium, 10.0)

    cost_of_credit = (interest_rate / 100) * data.term_months
    risk_interaction = (data.loan_amount * data.dti) / (data.income + 1)

    # Loan size encoding
    if data.loan_amount <= 5000:
        loan_size_enc = 0
    elif data.loan_amount <= 15000:
        loan_size_enc = 1
    elif data.loan_amount <= 35000:
        loan_size_enc = 2
    else:
        loan_size_enc = 3

    # Credit tier encoding
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

    # Income segment encoding
    if data.income < 25000:
        income_segment_enc = 0
    elif data.income < 50000:
        income_segment_enc = 1
    elif data.income < 100000:
        income_segment_enc = 2
    else:
        income_segment_enc = 3

    # Categorical encodings
    home_map = {'RENT': 3, 'OWN': 2, 'MORTGAGE': 1, 'BUSINESS': 0, 'UNKNOWN': 4}
    medium_map = {'Bank': 0, 'Microfinance': 1, 'P2P': 2, 'SME': 3}

    home_ownership_enc = home_map.get(data.home_ownership.upper(), 4)
    lending_medium_enc = medium_map.get(data.lending_medium, 0)

    feature_vector = np.array([[
        data.loan_amount, interest_rate, data.term_months, data.income,
        data.dti, data.credit_score, data.employment_length,
        loan_to_income, monthly_burden, high_dti_flag,
        long_term_flag, cost_of_credit, risk_interaction,
        data.digital_onboarding, data.upi_transaction_count,
        data.mobile_credit_score, data.first_time_borrower, data.urban_flag,
        home_ownership_enc, lending_medium_enc,
        loan_size_enc, credit_tier_enc, income_segment_enc
    ]])

    return feature_vector, interest_rate, loan_to_income, monthly_burden

# ── Helper: Pricing ───────────────────────────────────────
def recommend_rate(default_prob, risk_tier, mobile_score, upi_count, first_timer):
    base_rate = 8.0
    risk_premium = {'High': 8.0, 'Medium': 4.0, 'Low': 1.0}.get(risk_tier, 2.0)
    prob_premium = default_prob * 20
    mobile_discount = max(0, (mobile_score - 650) / 100)
    upi_discount = min(1.5, upi_count / 100)
    first_timer_premium = 2.0 if first_timer == 1 else 0
    rate = base_rate + risk_premium + prob_premium + first_timer_premium - mobile_discount - upi_discount
    return round(float(np.clip(rate, 6.0, 36.0)), 2)

# ── Helper: Early Warning ─────────────────────────────────
def get_early_warning(default_prob, dti, loan_to_income, mobile_score, upi_count, monthly_burden):
    flags = []
    if default_prob > 0.6:
        flags.append('HIGH_DEFAULT_RISK')
    if dti > 40:
        flags.append('HIGH_DTI')
    if loan_to_income > 5:
        flags.append('LOAN_INCOME_STRESS')
    if mobile_score < 550:
        flags.append('LOW_MOBILE_SCORE')
    if upi_count < 10:
        flags.append('LOW_DIGITAL_ACTIVITY')
    if monthly_burden > 1000:
        flags.append('HIGH_MONTHLY_BURDEN')

    if not flags:
        return 'HEALTHY', []
    elif len(flags) == 1:
        return 'WATCH', flags
    elif len(flags) == 2:
        return 'WARNING', flags
    else:
        return 'CRITICAL', flags

# ══════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "Digital Lending Optimization API", "status": "running"}

@app.post("/predict")
def predict(borrower: BorrowerInput):
    # Engineer features
    X, interest_rate, loan_to_income, monthly_burden = engineer_features(borrower)
    X_scaled = scaler.transform(X)

    # Predictions
    default_prob = float(xgb_default.predict_proba(X)[0][1])
    predicted_default = int(default_prob >= 0.78)  # optimal threshold
    risk_tier_enc = int(xgb_risk.predict(X)[0])
    risk_tier = {0: 'Low', 1: 'Medium', 2: 'High'}.get(risk_tier_enc, 'Medium')
    expected_loss = float(xgb_loss.predict(X)[0])

    # Pricing
    rec_rate = recommend_rate(
        default_prob, risk_tier,
        borrower.mobile_credit_score,
        borrower.upi_transaction_count,
        borrower.first_time_borrower
    )

    # Early warning
    warning_status, warning_flags = get_early_warning(
        default_prob, borrower.dti, loan_to_income,
        borrower.mobile_credit_score, borrower.upi_transaction_count,
        monthly_burden
    )

    # Segment
    cluster_input = np.array([[
        borrower.loan_amount, interest_rate, borrower.term_months,
        borrower.income, borrower.dti, loan_to_income, monthly_burden,
        borrower.mobile_credit_score, borrower.upi_transaction_count,
        borrower.digital_onboarding, borrower.first_time_borrower, borrower.urban_flag
    ]])
    cluster_scaled = cluster_scaler.transform(cluster_input)
    cluster = int(kmeans.predict(cluster_scaled)[0])
    segment = segment_names.get(cluster, 'Unknown')

    # Approval decision
    approved = predicted_default == 0

    return {
        "approval": {
            "approved": approved,
            "decision": "APPROVED" if approved else "DECLINED",
            "confidence": round(1 - default_prob, 3)
        },
        "risk": {
            "default_probability": round(default_prob, 4),
            "risk_tier": risk_tier,
            "expected_loss": round(expected_loss, 2),
            "early_warning": warning_status,
            "warning_flags": warning_flags
        },
        "pricing": {
            "recommended_rate": rec_rate,
            "current_rate": interest_rate,
            "rate_adjustment": round(rec_rate - interest_rate, 2)
        },
        "segment": {
            "cluster": cluster,
            "name": segment
        }
    }

@app.get("/portfolio")
def portfolio():
    conn = sqlite3.connect('digital_lending.db')
    health = pd.read_sql_query("SELECT * FROM portfolio_health ORDER BY health_score DESC", conn)
    medium = pd.read_sql_query("SELECT * FROM medium_summary ORDER BY default_rate DESC", conn)
    segments = pd.read_sql_query("SELECT * FROM segment_summary ORDER BY default_rate DESC", conn)
    conn.close()

    return {
        "health_scores": health.to_dict(orient='records'),
        "medium_summary": medium.to_dict(orient='records'),
        "segments": segments.to_dict(orient='records')
    }

@app.get("/early-warning")
def early_warning_queue():
    conn = sqlite3.connect('digital_lending.db')
    queue = pd.read_sql_query("""
        SELECT lending_medium, loan_amount, default_probability,
               predicted_risk_tier, recommended_rate, early_warning
        FROM master_view
        WHERE early_warning != 'HEALTHY'
        ORDER BY default_probability DESC
        LIMIT 100
    """, conn)
    conn.close()

    distribution = queue['early_warning'].value_counts().to_dict()

    return {
        "distribution": distribution,
        "queue": queue.to_dict(orient='records')
    }

@app.get("/shap")
def shap_importance():
    conn = sqlite3.connect('digital_lending.db')
    shap_df = pd.read_sql_query("SELECT * FROM shap_importance ORDER BY importance DESC", conn)
    conn.close()
    return shap_df.to_dict(orient='records')