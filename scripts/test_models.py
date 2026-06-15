"""Test regularized models."""
import pickle, numpy as np
from lendiql.features import engineer_features
from lendiql.schemas import BorrowerInput
from lendiql.early_warning import risk_tier_from_probability, get_early_warning
from lendiql.pricing import recommend_rate
from lendiql.config import INDIVIDUAL_APPROVAL_THRESHOLD

models = {}
for name in ['xgb_default', 'xgb_risk', 'xgb_loss', 'scaler', 'kmeans', 'cluster_scaler']:
    with open(f'models/{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

segs = {0:'First-Time Micro Borrowers',1:'High-Value Stressed',
        2:'Rural Micro Borrowers',3:'Urban Established',4:'High-Income Large Borrowers'}

profiles = [
    ("Prime Bank", dict(loan_amount=15000, term_months=36, income=85000, dti=12, credit_score=760,
        employment_length=8, home_ownership='MORTGAGE', lending_medium='Bank', digital_onboarding=1,
        upi_transaction_count=80, mobile_credit_score=750, first_time_borrower=0, urban_flag=1, interest_rate=10)),
    ("Subprime SME", dict(loan_amount=50000, term_months=60, income=35000, dti=45, credit_score=580,
        employment_length=1, home_ownership='RENT', lending_medium='SME', digital_onboarding=0,
        upi_transaction_count=5, mobile_credit_score=480, first_time_borrower=1, urban_flag=0, interest_rate=16)),
    ("Micro Rural", dict(loan_amount=2000, term_months=12, income=12000, dti=8, credit_score=620,
        employment_length=2, home_ownership='UNKNOWN', lending_medium='Microfinance', digital_onboarding=0,
        upi_transaction_count=15, mobile_credit_score=520, first_time_borrower=1, urban_flag=0, interest_rate=8)),
    ("P2P Good", dict(loan_amount=20000, term_months=36, income=70000, dti=18, credit_score=720,
        employment_length=5, home_ownership='RENT', lending_medium='P2P', digital_onboarding=1,
        upi_transaction_count=60, mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=12)),
    ("Bank RENT user", dict(loan_amount=10000, term_months=36, income=50000, dti=15.5, credit_score=720,
        employment_length=5, home_ownership='RENT', lending_medium='Bank', digital_onboarding=1,
        upi_transaction_count=45, mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=11)),
]

for label, kw in profiles:
    b = BorrowerInput(**kw)
    X, ir, lti, burden = engineer_features(b)
    X_scaled = models['scaler'].transform(X)

    dp = float(models['xgb_default'].predict_proba(X_scaled)[0][1])
    rt = risk_tier_from_probability(dp)
    el = float(models['xgb_loss'].predict(X_scaled)[0])
    rr = recommend_rate(dp, rt, b.mobile_credit_score, b.upi_transaction_count, b.first_time_borrower)
    ws, wf = get_early_warning(dp, b.dti, lti, b.mobile_credit_score, b.upi_transaction_count, burden)

    ci = np.array([[b.loan_amount, ir, b.term_months, b.income, b.dti, lti, burden,
                    b.mobile_credit_score, b.upi_transaction_count,
                    b.digital_onboarding, b.first_time_borrower, b.urban_flag]])
    cs = models['cluster_scaler'].transform(ci)
    cl = int(models['kmeans'].predict(cs)[0])

    approved = dp < INDIVIDUAL_APPROVAL_THRESHOLD
    print(f'--- {label} ---')
    print(f'  prob: {dp:.4f} | tier: {rt} | approved: {approved}')
    print(f'  loss: ${el:.2f} | rate: {rr}% | ew: {ws} | seg: {segs.get(cl, "?")}')
    print()
