"""Portfolio optimizer — knapsack-based loan selection under constraints."""

from __future__ import annotations

from typing import Any

from lendiql.schemas import OptimizationRequest


def knapsack_optimize(req: OptimizationRequest) -> dict[str, Any]:
    """0-1 knapsack DP to select optimal loan set under budget, loss, and
    medium-concentration constraints.

    Returns the selected loan IDs, total return, and utilisation stats.
    """
    candidates = req.candidates
    budget = req.budget
    max_loss = req.max_loss_rate
    max_conc = req.max_medium_concentration

    n = len(candidates)
    amounts = [c.loan_amount for c in candidates]
    returns = [c.expected_return for c in candidates]
    risks = [c.risk_score for c in candidates]

    # Map each candidate to its lending medium (extracted from id prefix)
    _medium_prefix = {
        c.id: c.id.split("_")[0] if "_" in c.id else "unknown"
        for c in candidates
    }

    # DP: dp[j] = (max_return, loss_sum, selected_mask)
    max_amount = int(min(budget, sum(amounts)))
    dp = [(0.0, 0.0, 0)] * (max_amount + 1)

    for i in range(n):
        amt = int(amounts[i])
        ret = returns[i]
        rsk = risks[i]
        for j in range(max_amount, amt - 1, -1):
            prev_ret, prev_loss, _ = dp[j - amt]
            new_ret = prev_ret + ret
            new_loss = prev_loss + rsk * amt
            new_loss_rate = new_loss / max(j, 1)
            if new_ret > dp[j][0] and new_loss_rate <= max_loss:
                dp[j] = (new_ret, new_loss, dp[j - amt][2] | (1 << i))

    # Find best allocation respecting medium concentration
    best_mask = 0
    best_return = 0.0
    best_utilization = 0.0
    for j in range(1, max_amount + 1):
        ret, loss_sum, mask = dp[j]
        if mask == 0:
            continue
        selected = [candidates[k] for k in range(n) if mask & (1 << k)]
        medium_counts: dict[str, int] = {}
        for c in selected:
            med = _medium_prefix.get(c.id, "unknown")
            medium_counts[med] = medium_counts.get(med, 0) + 1
        total_sel = len(selected)
        if any(cnt / max(total_sel, 1) > max_conc for cnt in medium_counts.values()):
            continue
        if ret > best_return:
            best_return = ret
            best_mask = mask
            best_utilization = j / budget

    selected_ids = [c.id for k, c in enumerate(candidates) if best_mask & (1 << k)]
    total_amount = sum(
        candidates[k].loan_amount for k in range(n) if best_mask & (1 << k)
    )
    total_loss = sum(
        candidates[k].risk_score * candidates[k].loan_amount
        for k in range(n) if best_mask & (1 << k)
    )

    return {
        "selected_loans": selected_ids,
        "total_return": round(best_return, 2),
        "total_amount": round(total_amount, 2),
        "budget_utilization": round(best_utilization, 4),
        "weighted_loss_rate": round(total_loss / max(total_amount, 1), 4),
        "constraints_applied": {
            "budget": budget,
            "max_loss_rate": max_loss,
            "max_medium_concentration": max_conc,
        },
    }
