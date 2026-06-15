"""Central configuration — single source of truth for every threshold / tunable."""

import os

DB_PATH = os.getenv("LENDIQ_DB_PATH", "digital_lending.db")
DB_DRIVE_URL = os.getenv(
    "LENDIQ_DB_DRIVE_URL",
    "https://drive.google.com/uc?id=1kCqmBCDvVwVY8RQ5NDLiVQzfTDZFa5MS",
)

# Approval thresholds
INDIVIDUAL_APPROVAL_THRESHOLD = 0.50
PORTFOLIO_APPROVAL_THRESHOLD = 0.78

# Risk tier cut-offs (applied to default_probability)
RISK_TIER_THRESHOLDS = {"Low": 0.25, "Medium": 0.50, "High": 1.01}

# Pricing engine parameters
PRICING_CONFIG = {
    "base_rate": 8.0,
    "risk_premium": {"Low": 1.0, "Medium": 4.0, "High": 8.0},
    "default_prob_weight": 20.0,
    "first_timer_premium": 2.0,
    "mobile_discount_reference": 650,
    "mobile_discount_per_100": 1.0,
    "upi_discount_per_100": 1.0,
    "upi_discount_cap": 1.5,
    "min_rate": 6.0,
    "max_rate": 36.0,
}

# Early warning rule thresholds
EARLY_WARNING_CONFIG = {
    "high_default_prob": 0.6,
    "high_dti": 40,
    "loan_income_stress": 5,
    "low_mobile_score": 550,
    "low_digital_activity_upi": 10,
    "high_monthly_burden": 1000,
}

# Per-medium default interest rate when caller doesn't supply one
MEDIUM_DEFAULT_RATES = {"P2P": 13.5, "Bank": 11.0, "Microfinance": 8.0, "SME": 14.0}

SEGMENT_NAMES = {
    0: "First-Time Micro Borrowers",
    1: "High-Value Stressed",
    2: "Rural Micro Borrowers",
    3: "Urban Established",
    4: "High-Income Large Borrowers",
}

FEATURE_NAMES = [
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

HOME_OWNERSHIP_MAP = {"RENT": 3, "OWN": 2, "MORTGAGE": 1, "BUSINESS": 0, "UNKNOWN": 4}
MEDIUM_MAP = {"Bank": 0, "Microfinance": 1, "P2P": 2, "SME": 3}
