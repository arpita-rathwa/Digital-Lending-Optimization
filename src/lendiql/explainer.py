"""Gemini-powered portfolio explainer — turns raw metrics into plain-English insights."""

from __future__ import annotations

import json

from google import genai

from lendiql.config import GEMINI_API_KEY, GEMINI_MODEL


def _build_prompt(portfolio: dict) -> str:
    health = portfolio.get("health_scores", [])
    mediums = portfolio.get("medium_summary", [])
    segments = portfolio.get("segments", [])

    return f"""You are a chief risk officer's AI analyst. Given the following portfolio data, write a sharp, concise analysis (< 250 words) in plain English. Cover:

1. Which lending medium is strongest/weakest and why
2. Which borrower segment needs attention
3. One actionable recommendation

Data:
Health Scores: {json.dumps(health, indent=2)}
Medium Summary: {json.dumps(mediums, indent=2)}
Segments: {json.dumps(segments, indent=2)}"""


def explain_portfolio(portfolio: dict) -> str | None:
    if not GEMINI_API_KEY:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = _build_prompt(portfolio)

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e:
        return f"AI explanation unavailable: {e}"
