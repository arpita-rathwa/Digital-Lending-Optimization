"""Debug individual feature effects."""
import pickle, numpy as np
from lendiql.features import engineer_features
from lendiql.schemas import BorrowerInput
from lendiql.config import FEATURE_NAMES

models = {}
for name in ['xgb_default', 'xgb_risk', 'xgb_loss', 'scaler']:
    with open(f'models/{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

profiles = [
    ("Prime Bank Mortgage", BorrowerInput(loan_amount=15000, term_months=36, income=85000, dti=12, credit_score=760,
        employment_length=8, home_ownership='MORTGAGE', lending_medium='Bank', digital_onboarding=1,
        upi_transaction_count=80, mobile_credit_score=750, first_time_borrower=0, urban_flag=1, interest_rate=10)),
    ("Bank RENT", BorrowerInput(loan_amount=10000, term_months=36, income=50000, dti=15.5, credit_score=720,
        employment_length=5, home_ownership='RENT', lending_medium='Bank', digital_onboarding=1,
        upi_transaction_count=45, mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=11)),
    ("Bank MORTGAGE same", BorrowerInput(loan_amount=10000, term_months=36, income=50000, dti=15.5, credit_score=720,
        employment_length=5, home_ownership='MORTGAGE', lending_medium='Bank', digital_onboarding=1,
        upi_transaction_count=45, mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=11)),
    ("P2P RENT same", BorrowerInput(loan_amount=10000, term_months=36, income=50000, dti=15.5, credit_score=720,
        employment_length=5, home_ownership='RENT', lending_medium='P2P', digital_onboarding=1,
        upi_transaction_count=45, mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=11)),
]

for label, b in profiles:
    X, _, _, _ = engineer_features(b)
    X_scaled = models['scaler'].transform(X)
    dp = float(models['xgb_default'].predict_proba(X_scaled)[0][1])
    print(f'{label}: default_prob = {dp:.4f}')
