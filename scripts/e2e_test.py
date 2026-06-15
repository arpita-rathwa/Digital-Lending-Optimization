"""Quick end-to-end test."""
import pickle, numpy as np
from lendiql.features import engineer_features
from lendiql.schemas import BorrowerInput
from lendiql.early_warning import risk_tier_from_probability, get_early_warning
from lendiql.pricing import recommend_rate

models = {}
for name in ['xgb_default', 'xgb_risk', 'xgb_loss', 'scaler', 'kmeans', 'cluster_scaler']:
    with open(f'models/{name}.pkl', 'rb') as f:
        models[name] = pickle.load(f)

b = BorrowerInput(loan_amount=10000, term_months=36, income=50000, dti=15.5,
    credit_score=720, employment_length=5, home_ownership='RENT',
    lending_medium='Bank', digital_onboarding=1, upi_transaction_count=45,
    mobile_credit_score=680, first_time_borrower=0, urban_flag=1, interest_rate=11.0)

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
seg = {0:'First-Time Micro Borrowers',1:'High-Value Stressed',2:'Rural Micro Borrowers',3:'Urban Established',4:'High-Income Large Borrowers'}.get(cl)

print(f'Default prob: {dp:.4f}')
print(f'Risk tier: {rt}')
print(f'Expected loss: ${el:.2f}')
print(f'Recommended rate: {rr}%')
print(f'Early warning: {ws} flags={wf}')
print(f'Segment: {seg}')
print(f'Approved: {dp < 0.5}')
