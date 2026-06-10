// ── Dashboard Page Logic ──────────────────────────────────

async function loadDashboard() {
    const data = await fetchPortfolio();
    if (!data) return;

    // ── KPI Cards ─────────────────────────────────────────
    const totalVolume = data.medium_summary.reduce((a, b) => a + (b.avg_loan_amount * b.total_loans), 0);
    const avgDefault = data.medium_summary.reduce((a, b) => a + b.default_rate, 0) / data.medium_summary.length;
    const avgRate = data.medium_summary.reduce((a, b) => a + b.avg_interest_rate, 0) / data.medium_summary.length;

    const volEl = document.getElementById('kpi-volume');
    const defEl = document.getElementById('kpi-default');
    const rateEl = document.getElementById('kpi-rate');

    if (volEl) volEl.textContent = formatCurrency(totalVolume);
    if (defEl) defEl.textContent = (avgDefault * 100).toFixed(1) + '%';
    if (rateEl) rateEl.textContent = avgRate.toFixed(1) + '%';

    // ── Medium Pills ──────────────────────────────────────
    data.health_scores.forEach(h => {
        const medium = h.lending_medium.toLowerCase().replace('finance', '');
        const key = medium === 'micro' ? 'micro' : medium === 'p2p' ? 'p2p' : medium === 'bank' ? 'bank' : 'sme';

        const healthEl = document.getElementById(`health-${key}`);
        const defMedEl = document.getElementById(`def-${key}`);

        if (healthEl) healthEl.textContent = h.health_score;
        if (defMedEl) defMedEl.textContent = `Def: ${(h.default_rate * 100).toFixed(1)}%`;
    });

    // ── Early Warning Summary ─────────────────────────────
    const warnData = await fetchWarnings();
    if (warnData) {
        const critEl = document.getElementById('warn-critical');
        const warnEl = document.getElementById('warn-warning');
        const watchEl = document.getElementById('warn-watch');
        if (critEl) critEl.textContent = (warnData.distribution.CRITICAL || 0).toLocaleString();
        if (warnEl) warnEl.textContent = (warnData.distribution.WARNING || 0).toLocaleString();
        if (watchEl) watchEl.textContent = (warnData.distribution.WATCH || 0).toLocaleString();
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);