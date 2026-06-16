"""Deterministic portfolio explainer — turns raw metrics into plain-English insights."""

from __future__ import annotations


def explain_portfolio(portfolio: dict) -> str:
    mediums = portfolio.get("medium_summary", [])
    segments = portfolio.get("segments", [])
    health_scores = portfolio.get("health_scores", [])

    if not mediums and not segments:
        return "No portfolio data available to analyze."

    health_map = {h["lending_medium"]: h["health_score"] for h in health_scores}

    best_medium = worst_medium = None
    if mediums:
        sorted_media = sorted(mediums, key=lambda m: m["default_rate"])
        best_medium = sorted_media[0]
        worst_medium = sorted_media[-1]

    worst_segment = None
    if segments:
        worst_segment = max(segments, key=lambda s: s["default_rate"])

    total_loans = sum(m["total_loans"] for m in mediums)
    avg_default_rate = (
        sum(m["default_rate"] * m["total_loans"] for m in mediums) / total_loans
        if total_loans
        else 0
    )

    lines = []

    # ── Medium analysis ──
    if best_medium and worst_medium:
        best_name = best_medium["lending_medium"]
        worst_name = worst_medium["lending_medium"]
        best_def = best_medium["default_rate"] * 100
        worst_def = worst_medium["default_rate"] * 100
        best_health = health_map.get(best_name, "N/A")
        worst_health = health_map.get(worst_name, "N/A")

        lines.append(
            f"{best_name} is the strongest medium ({best_def:.1f}% default rate, "
            f"health score {best_health}), while {worst_name} is the weakest "
            f"({worst_def:.1f}% default rate, health score {worst_health})."
        )

        # Compare to portfolio average
        avg_def_pct = avg_default_rate * 100
        for m in [worst_medium]:
            m_def = m["default_rate"] * 100
            if m_def > avg_def_pct * 1.5:
                lines.append(
                    f"{m['lending_medium']}'s default rate ({m_def:.1f}%) is "
                    f"{m_def/avg_def_pct:.1f}x the portfolio average ({avg_def_pct:.1f}%) "
                    f"— this medium is driving most of the portfolio risk."
                )

    # ── Segment spotlight ──
    if worst_segment:
        seg_def = worst_segment["default_rate"] * 100
        seg_loans = worst_segment["total_loans"]
        lines.append(
            f"The {worst_segment['segment']} segment requires attention: "
            f"{seg_loans:,} loans with a {seg_def:.1f}% default rate."
        )

    # ── Recommendation ──
    if worst_medium:
        recs = []
        w_name = worst_medium["lending_medium"]
        w_def = worst_medium["default_rate"]

        if w_def > 0.25:
            recs.append(
                f"Tighten approval criteria for {w_name} — raise the minimum credit "
                f"score or reduce max loan-to-income ratios."
            )
        if best_medium:
            recs.append(
                f"Consider reallocating marketing spend toward {best_medium['lending_medium']} "
                f"which shows the strongest risk-adjusted performance."
            )
        if worst_segment and worst_segment["default_rate"] > 0.2:
            recs.append(
                f"Review underwriting rules for the {worst_segment['segment']} segment "
                f"to add stricter income or collateral requirements."
            )

        if recs:
            lines.append("Recommendation: " + " ".join(recs[:2]))

    return "\n\n".join(lines)
