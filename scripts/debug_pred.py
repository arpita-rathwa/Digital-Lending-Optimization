"""Debug model predictions."""

import pickle
import numpy as np
from lendiql.features import engineer_features
from lendiql.schemas import BorrowerInput
from lendiql.config import FEATURE_NAMES

models = {}
for name in ['xgb_default', 'xgb_risk', 'xgb_loss', 'scaler', 'kmeans', 'cluster_scaler']:
    with open(f'models/{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

test_cases = [
    BorrowerInput(loan_amount=10000, term_months=36, income=50000, dti=15.5,
                  credit_score=720, employment_length=5, home_ownership='RENT',
                  lending_medium='Bank', digital_onboarding=1, upi_transaction_count=45,
                  mobile_credit_score=680, first_time_borrower=0, urban_flag=1,
                  interest_rate=11.0),
    BorrowerInput(loan_amount=200000, term_months=60, income=25000, dti=60.0,
                  credit_score=520, employment_length=0.5, home_ownership='RENT',
                  lending_medium='SME', digital_onboarding=0, upi_transaction_count=0,
                  mobile_credit_score=480, first_time_borrower=1, urban_flag=0,
                  interest_rate=14.0),
]

for i, b in enumerate(test_cases):
    X, ir, lti, burden = engineer_features(b)
    label = 'LOW' if i == 0 else 'HIGH'
    print(f'=== {label} RISK BORROWER ===')
    for j, name in enumerate(FEATURE_NAMES):
        val = X[0, j]
        print(f'  {name}: {val}')
    
    X_scaled = models['scaler'].transform(X)
    print(f'\n  --- Scaled ---')
    for j, name in enumerate(FEATURE_NAMES):
        print(f'  {name}: {X_scaled[0][j]:.4f}')
    
    dp_proba = models['xgb_default'].predict_proba(X_scaled)
    dp = float(dp_proba[0][1])
    print(f'\n  predict_proba: {dp_proba}')
    print(f'  default_prob: {dp:.4f}')
    print()
