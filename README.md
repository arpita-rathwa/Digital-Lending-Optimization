# 💳 Digital Lending Optimization
### LendIQ — Multi-Medium Lending Intelligence & Decision Optimization Platform

[![Live API](https://img.shields.io/badge/Live%20API-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://digital-lending-optimization-1.onrender.com)
[![Live App](https://img.shields.io/badge/Live%20App-LendIQ-FF5A5F?style=for-the-badge&logo=netlify)](https://zingy-sopapillas-e170dc.netlify.app/scorer)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/arpita-rathwa/Digital-Lending-Optimization)

> An end-to-end digital lending intelligence system spanning 4 lending mediums (P2P, Bank, Microfinance, SME) and 765,140 loans — combining risk prediction, borrower segmentation, and a full optimization layer (approval thresholds, dynamic pricing, portfolio health scoring, early warning) into a deployed full-stack platform with a FastAPI backend and an interactive LendIQ frontend.

---

## Real-World Business Framing

Most "credit risk" portfolio projects stop at predicting whether a borrower will default. But a real digital lender's question is broader:

> *"How do we grow our loan book without blowing up our default rate — and how do we price, monitor, and intervene on every loan we hold?"*

This project reframes the problem as **decision optimization**, not just prediction, across four levers:

- **Credit Risk Optimization** — find the approval threshold that maximizes profit while keeping defaults under control
- **Pricing Optimization** — recommend a personalized interest rate per borrower based on risk, behavior, and digital signals
- **Portfolio Optimization** — score and rank the health of each lending medium and borrower segment
- **Early Warning Optimization** — flag loans showing stress signals before they become defaults

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| Pandas + NumPy | Data unification and feature engineering |
| SQLite | Relational database layer (8 tables) |
| DB Browser for SQLite | SQL analysis |
| Scikit-learn | Logistic Regression, K-Means clustering, preprocessing |
| XGBoost | Default classification, risk tiering, expected loss regression |
| LightGBM / Optuna | (Planned) faster training & hyperparameter tuning |
| SHAP | Model explainability (TreeExplainer) |
| Matplotlib | Visualization (elbow plot, SHAP plots) |
| FastAPI + Uvicorn | Backend REST API |
| Render | Backend deployment |
| gdown | Runtime database download from Google Drive |
| HTML / Tailwind CSS / JS | LendIQ frontend (Stitch-generated design system) |
| Chart.js | Interactive charts (segment donut, default rate, health scores) |
| Netlify | Frontend deployment |
| pytest + httpx | API & unit tests |

---

## Dataset — Unifying 4 Lending Mediums

Rather than relying on a single dataset, this project combines **four real public datasets**, each representing a distinct lending medium, into one unified schema — a structure no single off-the-shelf dataset offers.

| Medium | Source | Rows | Default Rate |
|---|---|---|---|
| **P2P Lending** | LendingClub 2007 (GitHub mirror) | 39,252 | 14.4% |
| **Bank Loans** | Credit Risk Dataset (Kaggle) | 32,581 | 21.8% |
| **Microfinance** | Kiva Loans (Kaggle) | 671,205 | 1.5% |
| **SME Lending** | SBA Loans (2,102 real + 20,000 synthetic) | 22,102 | 33.4% |
| **Combined** | | **765,140** | **4.0%** |

### Data Cleaning Highlights
- **P2P `loan_status` was inverted** (1 = good loan) — corrected to standard convention (`1` = default)
- **Microfinance has no native default label** — engineered a proxy: `repayment_interval == 'bullet' AND funding_gap > 0`
- **SME dataset (2,102 rows) was too small** — expanded to 22,102 rows via synthetic generation matching the real distribution's loan amount, term, and default rate

---

## Feature Engineering — 26 Features

**Core features** — `loan_amount`, `interest_rate`, `term_months`, `income`, `dti`, `credit_score`, `employment_length`, `home_ownership`, `lending_medium`

**Risk-engineered features** — `loan_to_income`, `monthly_burden`, `high_dti_flag`, `long_term_flag`, `cost_of_credit`, `risk_interaction`

**Behavioral / categorical encodings** — `loan_size` (Micro/Small/Medium/Large), `credit_tier` (Poor → Exceptional), `income_segment` (Low → High)

**India / Emerging Market Context (synthetic, grounded)** — `digital_onboarding`, `upi_transaction_count`, `mobile_credit_score`, `first_time_borrower`, `urban_flag`

**Targets** — `default` (binary), `risk_tier` (Low/Medium/High), `expected_loss` (continuous)

### Two-Stage Null Handling
Microfinance (671k rows) has no income, credit score, or DTI — by design, since microfinance borrowers typically lack formal credit histories. Nulls were imputed first by **lending-medium median**, then by **global median** as fallback — preserving the realistic data-availability gap between formal and informal lending channels.

---

## Architecture

```
4 Raw Datasets (P2P, Bank, Microfinance, SME)
        ↓
Unification + Cleaning (765,140 loans, 26 features)
        ↓
SQLite Database (8 tables)
        ↓
SQL Analysis Layer (5 business queries)
        ↓
ML Pipeline (XGBoost / RF / Logistic Regression × 3 tasks)
        ↓
SHAP Explainability
        ↓
K-Means Borrower Segmentation (5 segments)
        ↓
Optimization Layer
 (Approval Threshold · Pricing Engine · Portfolio Health · Early Warning)
        ↓
FastAPI Backend (5 endpoints, live on Render)
        ↓
LendIQ Frontend (HTML/Tailwind/Chart.js, deployed on Netlify)
```

---

## Phase 1 — SQLite Database

| Table | Rows | Description |
|---|---|---|
| `loans` | 765,140 | Unified fact table across all 4 mediums |
| `medium_summary` | 4 | Aggregate stats per lending medium |
| `risk_segments` | 12 | Risk tier × medium breakdown |
| `ml_predictions` | 100,000 | Model predictions on sampled data |
| `threshold_analysis` | 99 | Approval threshold sweep (0.01–0.99) |
| `optimization_output` | 100,000 | Pricing + early warning per loan |
| `portfolio_health` | 4 | Health score per medium |
| `segment_summary` | 5 | K-Means segment profiles |
| `master_view` | 765,140 | Fully joined denormalized view |

---

## Phase 2 — ML Pipeline (100k sample, class-imbalance aware)

The dataset is heavily imbalanced — only **4% of loans default**. A naive model predicting "no default" for everything scores 96% accuracy while being completely useless. All models therefore use `class_weight='balanced'` (Random Forest, Logistic Regression) or `scale_pos_weight` (XGBoost), and **recall on the default class** — not overall accuracy — is the key metric.

### Task 1 — Default Classification (Binary)

| Model | Accuracy | Default Recall | Default F1 |
|---|---|---|---|
| Random Forest | 96.43% | 15% | 0.24 |
| **XGBoost** | **85.18%** | **80%** ✅ | **0.30** |
| Logistic Regression | 88.93% | — | — |

> Random Forest has higher accuracy but catches only 15% of actual defaulters — useless for a lender. XGBoost trades ~11 points of accuracy for **5.3× better default recall**.

### Task 2 — Risk Tier Classification (Multi-class)
XGBoost selected as the risk-tiering model.

> **Note:** In production (`/predict`), `risk_tier` is now derived deterministically from `default_probability` thresholds (Low < 0.25, Medium 0.25–0.5, High ≥ 0.5) to guarantee the two outputs can never disagree.

### Task 3 — Expected Loss Regression

| Model | MAE |
|---|---|
| **XGBoost** | **3,067** ✅ |
| Random Forest | 3,087 |

---

## Phase 3 — SHAP Explainability

SHAP TreeExplainer applied to the XGBoost default classifier on a 2,000-loan sample.

### Top 10 Feature Importances

| Rank | Feature | Importance |
|---|---|---|
| 1 | **Term Months** | 1.181 |
| 2 | **Monthly Burden** | 0.858 |
| 3 | **Loan Amount** | 0.851 |
| 4 | **Home Ownership** | 0.779 |
| 5 | **Mobile Credit Score** | 0.302 |
| 6 | **UPI Transaction Count** | 0.195 |
| 7 | Loan-to-Income | 0.168 |
| 8 | Risk Interaction | 0.151 |
| 9 | Interest Rate | 0.114 |
| 10 | DTI | 0.069 |

### Key Insights
- **Loan structuring (term, amount, monthly burden) matters more than borrower demographics**
- **Mobile Credit Score ranked 5th out of 23** — validating that India-context alternative-data features are genuinely predictive, not just decorative additions
- `lending_medium` itself has near-zero importance — default risk is driven by loan structure and borrower behavior, not which channel originated the loan

---

## Phase 4 — Borrower Segmentation (K-Means, K=5)

K selected via elbow method on a 50,000-loan scaled sample across 12 behavioral and financial features.

| Segment | Loans | Default Rate | Avg Loan | Recommended Rate |
|---|---|---|---|---|
| **Urban Established** | 313,883 | 3.1% | $1,827 | 11.8% |
| **First-Time Micro Borrowers** | 260,523 | 3.2% | $1,843 | 13.8% |
| **Rural Micro Borrowers** | 169,465 | 3.2% | $1,840 | 11.6% |
| **High-Income Large Borrowers** | 18,943 | 32.0% | $260,130 | 25.7% |
| **High-Value Stressed** | 2,326 | 35.2% | $972,369 | 26.1% |

### Key Insight
The two largest segments (Urban Established, First-Time Micro — together 75% of the portfolio) have default rates around **3%**, while the two smallest segments (High-Income Large, High-Value Stressed — under 3% of loans) carry **32–35% default rates** and require disproportionate pricing premiums and monitoring attention.

---

## Phase 5 — Optimization Layer

This is the core differentiator of the project — four optimization sub-systems built on top of the ML predictions.

### 5.1 — Dual Approval Thresholds
The system distinguishes between **individual live decisions** and **portfolio-level batch optimization**, which require different risk tolerances.

| Use Case | Threshold | Approval Rate | Resulting Default Rate |
|---|---|---|---|
| **`/predict` (individual decision)** | **0.50** | ~93% | ~3% (matches portfolio baseline) |
| **Batch portfolio optimization** | 0.78 | 94.9% | 1.3% |

A swept default-probability threshold from 0.01 to 0.99 is used to find the threshold that maximizes portfolio profit. At 0.78, profit is maximized at **$167,185,678** because high-probability defaulters are concentrated in a small fraction of loans. This loose threshold is only used for *batch* portfolio analysis — individual applicants are scored against a stricter 0.50 cutoff.

### 5.2 — Dynamic Pricing Engine
Recommends an interest rate per loan:

```
recommended_rate = base_rate (8%)
    + risk_tier_premium (1% / 4% / 8% for Low/Medium/High)
    + default_probability × 20
    + first_time_borrower_premium (2%)
    − mobile_credit_score_discount
    − upi_activity_discount
clipped to [6%, 36%]
```

| Risk Tier | Mean Rate | Range |
|---|---|---|
| Low | 12.32% | 6.40% – 29.96% |
| Medium | 19.19% | 9.65% – 32.63% |
| High | 34.57% | 16.95% – 36.00% |

| Lending Medium | Mean Recommended Rate |
|---|---|
| Microfinance | 11.64% |
| P2P | 19.67% |
| Bank | 20.33% |
| SME | 25.97% |

### 5.3 — Portfolio Health Scoring (0–100)
Composite score: `30% × (1−default_rate) + 25% × (1−avg_default_prob) + 20% × (1−high_risk_pct) + 15% × (mobile_score/850) + 10% × digital_onboarding_pct`

| Medium | Health Score |
|---|---| 
| **Microfinance** | **89.57** |
| P2P | 75.34 |
| Bank | 70.73 |
| SME | 59.42 |

### 5.4 — Early Warning System
Each loan is flagged based on the count of active stress signals (high default probability, high DTI, loan-to-income stress, low mobile credit score, low digital activity, high monthly burden):

| Flags Active | Status |
|---|---|
| 0 | HEALTHY |
| 1 | WATCH |
| 2 | WARNING |
| 3+ | CRITICAL |

---

## Phase 6 — FastAPI Backend

Deployed live on Render: **[digital-lending-optimization-1.onrender.com](https://digital-lending-optimization-1.onrender.com)**

The 255MB SQLite database is hosted on Google Drive and downloaded at runtime via `gdown` on server startup. If the download fails (e.g., on a cold start that times out), the `/` endpoint returns a clear error message instead of crashing.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/predict` | POST | Full risk assessment for a borrower: default probability, risk tier, expected loss, recommended rate, early warning status, segment assignment |
| `/portfolio` | GET | Portfolio health scores, medium summary, segment summary |
| `/early-warning` | GET | Top N flagged loans with risk details (query param `?limit=100`) |
| `/shap` | GET | SHAP feature importance rankings |

### Example `/predict` Response
```json
{
  "approval": { "approved": false, "decision": "DECLINED", "confidence": 0.2325, "threshold_used": 0.5, "threshold_type": "individual" },
  "risk": {
    "default_probability": 0.7675,
    "risk_tier": "High",
    "expected_loss": 281.68,
    "early_warning": "WATCH",
    "warning_flags": ["HIGH_DEFAULT_RISK"]
  },
  "pricing": { "recommended_rate": 30.6, "current_rate": 11.0, "rate_adjustment": 19.6 },
  "segment": { "cluster": 3, "name": "Urban Established" }
}
```

> `risk_tier` is now derived directly from `default_probability` thresholds, so the two values are guaranteed to be consistent.

### Local Development

```bash
# Install dependencies (editable install recommended for dev)
pip install -e ".[dev]"

# Or using requirements.txt directly
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start the API (uses models/*.pkl + digital_lending.db)
uvicorn main:app --reload
```

The frontend reads `window.API_BASE` first and falls back to the deployed URL — set it in your browser console or via a local script tag to point at `http://localhost:8000` during development:

```js
window.API_BASE = 'http://localhost:8000';
```

---

## Phase 7 — LendIQ Frontend

A 4-page lending intelligence dashboard built from a Stitch-generated design system (warm fintech red/cream palette, Inter typography) and wired to the live FastAPI backend.

**Pages:**
- **Dashboard** — portfolio KPIs, medium performance pills, portfolio health bars, segment distribution donut (Chart.js), early warning summary
- **Risk Scorer** — interactive borrower assessment form → real-time risk gauge, decision badge, pricing recommendation, segment assignment, warning flags
- **Portfolio Intelligence** — ranked medium performance table, default rate & health score bar charts (Chart.js), segment intelligence cards
- **Early Warning Queue** — filterable table of flagged loans by warning level

All data is fetched live from the Render API — no hardcoded values.

---

## ML Axes

| Axis | Detail |
|---|---|
| Learning Paradigm & Training Regime | Supervised (classification + regression) + Unsupervised (K-Means clustering) |
| Scope & Complexity | Multi-source data fusion · Multi-target ML · Full optimization layer · Full-stack deployment |
| Data Modality | Tabular (financial, behavioral, alternative/digital signals) |
| Explainability & Impact | High — SHAP-driven, four optimization sub-systems, live API + deployed frontend |

---

## Repository Structure

```
Digital-Lending-Optimization/
├── src/
│   └── lendiql/                 # Python package
│       ├── __init__.py          # Package marker & version
│       ├── config.py            # Central configuration (thresholds, maps)
│       ├── schemas.py           # Pydantic request models
│       ├── features.py          # Feature engineering
│       ├── pricing.py           # Pricing engine
│       ├── early_warning.py     # Early warning & risk tier derivation
│       ├── models.py            # Model loading / lazy init
│       ├── app.py               # FastAPI app & endpoints
│       └── main.py              # Entry point (uvicorn)
├── main.py                      # Backward-compat re-export (``main:app``)
├── pyproject.toml               # Project metadata & tool config
├── requirements.txt
├── README.md
├── Dockerfile
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions (lint + tests)
├── data/                        # Raw datasets (not tracked)
├── models/                      # Trained .pkl artifacts (not tracked)
├── notebooks/                   # Exploratory notebooks
├── outputs/                     # SHAP plots, elbow plot, query CSVs
├── research_paper/              # Credit invisibility research paper
├── frontend/                    # LendIQ dashboard
│   ├── index.html               # Dashboard
│   ├── scorer.html              # Risk Scorer
│   ├── portfolio.html           # Portfolio Intelligence
│   ├── warnings.html            # Early Warning Queue
│   ├── DESIGN.md                # Design system tokens
│   ├── assets/                  # Screenshots
│   └── js/                      # api.js, dashboard.js, scorer.js, etc.
└── tests/                       # pytest suite
    ├── test_helpers.py
    └── test_api.py
```

---

## Scope for Fine-Tuning & Future Improvements

**Model Level**
- ~~Fix risk_tier inconsistency~~ — **DONE**: `risk_tier` now derived from `default_probability` thresholds
- ~~Stricter individual approval threshold~~ — **DONE**: dual-threshold system (0.50 individual, 0.78 batch)
- ~~Fix training/inference encoding mismatch~~ — **DONE**: replaced `cat.codes` with fixed `HOME_OWNERSHIP_MAP` + regularized retraining
- Hyperparameter tuning via Optuna across all XGBoost models
- LightGBM as a faster alternative to XGBoost on the 671k-row Microfinance segment
- Probability calibration (Platt / isotonic) with reliability diagram

**Data Level**
- Replace synthetic SME expansion with real SBA loan data at scale
- Real transactional UPI/mobile data instead of synthetic India-context features
- Time-series loan performance data for true early-warning validation (current flags are cross-sectional)

**System Level**
- Authentication and per-loan-officer audit logging
- A/B testing framework to validate whether recommended pricing/interventions actually change outcomes
- Batch scoring endpoint for portfolio-wide threshold optimization re-runs
- Rate limiting on `/predict` (e.g., `slowapi`)

**Frontend Level**
- Persist Risk Scorer history per session
- Export early warning queue to CSV
- "What-if" sliders on the Risk Scorer (live recompute as inputs change)
- PWA support for offline portfolio health caching

**Engineering**
- Migrate DB hosting from Google Drive → S3/R2 (gdown is fragile on cold starts)
- ~~Add a `Dockerfile` for the backend~~ — **DONE**
- Add a `MODEL_CARD.md` documenting training data, intended use, and fairness considerations
- ~~CI via GitHub Actions (lint + tests on every PR)~~ — **DONE**
# trigger
#   t r i g g e r  
 #   t r i g g e r   C I R e c o n  
 