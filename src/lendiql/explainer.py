"""Gemini-powered portfolio explainer — turns raw metrics into plain-English insights."""

from __future__ import annotations

import json
import time

from google import genai
from google.genai import types as genai_types

from lendiql.config import GEMINI_API_KEY, GEMINI_MODEL

_cache: dict = {"data": None, "expires_at": 0.0}

def _build_prompt(portfolio: dict) -> str:
    mediums = portfolio.get("medium_summary", [])
    segments = portfolio.get("segments", [])

    medium_lines = "\n".join(
        f"- {m['lending_medium']}: {m['total_loans']} loans, "
        f"{m['default_rate']*100:.1f}% default rate, "
        f"${m['avg_loan_amount']:,.0f} avg loan"
        for m in mediums
    )
    seg_lines = "\n".join(
        f"- {s['segment']}: {s['total_loans']} loans, "
        f"{s['default_rate']*100:.1f}% default rate, "
        f"${s['avg_loan']:,.0f} avg loan, {s['avg_recommended_rate']:.1f}% rate"
        for s in segments
    )
    health = portfolio.get("health_scores", [])
    health_line = ", ".join(
        f"{h['lending_medium']}={h['health_score']}" for h in health
    )

    return f"""You are a chief risk officer's AI analyst. Given this portfolio data, write a sharp analysis (<200 words). Cover: 1) strongest/weakest medium, 2) riskiest segment, 3) one recommendation.

Health scores: {health_line}

Mediums:
{medium_lines}

Segments:
{seg_lines}"""


def explain_portfolio(portfolio: dict) -> str | None:
    if not GEMINI_API_KEY:
        return None

    now = time.time()
    if _cache["data"] and now < _cache["expires_at"]:
        return _cache["data"]

    prompt = _build_prompt(portfolio)
    client = genai.Client(api_key=GEMINI_API_KEY)
    models = [GEMINI_MODEL, "gemini-2.0-flash-lite"]

    for model in models:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            result = resp.text.strip()
            _cache["data"] = result
            _cache["expires_at"] = now + 60
            return result
        except genai_types.HttpError as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                continue
            _cache["data"] = f"AI explanation unavailable: {e}"
            _cache["expires_at"] = now + 60
            return _cache["data"]
        except Exception as e:
            _cache["data"] = f"AI explanation unavailable: {e}"
            _cache["expires_at"] = now + 60
            return _cache["data"]

    _cache["data"] = "AI explanation unavailable: All models are rate-limited (free tier exhausted). Try again in a minute or upgrade at https://ai.google.dev/pricing"
    _cache["expires_at"] = now + 30
    return _cache["data"]
