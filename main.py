"""Backward-compatible re-export for ``uvicorn main:app``."""

from lendiql.app import app
from lendiql.early_warning import get_early_warning, risk_tier_from_probability
from lendiql.features import engineer_features
from lendiql.pricing import recommend_rate
from lendiql.schemas import BorrowerInput
