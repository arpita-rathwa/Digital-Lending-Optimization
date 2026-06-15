"""Find which feature causes high default prob."""
import pickle, numpy as np
from lendiql.features import engineer_features
from lendiql.schemas import BorrowerInput

models = {}
for name in ['xgb_default', 'xgb_risk', 'xgb_loss', 'scaler']:
    with open(f'models/{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

# Start from the good profile, change one feature at a time
good = BorrowerInput(loan_amount=15000, term_months=36, income=85000, dti=12, credit_score=760,
    employment_length=8, home_ownership='MORTGAGE', lending_medium='Bank', digital_onboarding=1,
    upi_transaction_count=80, mobile_credit_score=750, first_time_borrower=0, urban_flag=1, interest_rate=10)

X, _, _, _ = engineer_features(good)
X_scaled = models['scaler'].transform(X)
dp_good = float(models['xgb_default'].predict_proba(X_scaled)[0][1])
print(f'GOOD (baseline): {dp_good:.4f}')

changes = {
    'income=50K': {'income': 50000},
    'loan=10K': {'loan_amount': 10000},
    'credit=720': {'credit_score': 720},
    'dti=15.5': {'dti': 15.5},
    'emp=5': {'employment_length': 5},
    'RENT': {'home_ownership': 'RENT'},
    'upi=45': {'upi_transaction_count': 45},
    'mobile=680': {'mobile_credit_score': 680},
    'first_time=1': {'first_time_borrower': 1},
    'urban=0': {'urban_flag': 0},
    'rate=11': {'interest_rate': 11},
}

for label, kwargs in changes.items():
    b = BorrowerInput(**{**{k: getattr(good, k) for k in good.model_fields.keys()}, **kwargs})
    X, _, _, _ = engineer_features(b)
    X_scaled = models['scaler'].transform(X)
    dp = float(models['xgb_default'].predict_proba(X_scaled)[0][1])
    print(f'  change {label}: {dp:.4f}  (delta: {dp - dp_good:+.4f})')
