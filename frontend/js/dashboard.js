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

    // ── Segment Donut Chart ────────────────────────────────
    if (data.segments) {
        const colors = ['#b52330', '#ff5a5f', '#22c55e', '#3b82f6', '#f59e0b'];

        const ctx = document.getElementById('segmentDonut');
        if (ctx) {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.segments.map(s => s.segment),
                    datasets: [{
                        data: data.segments.map(s => s.total_loans),
                        backgroundColor: colors,
                        borderWidth: 0
                    }]
                },
                options: {
                    cutout: '70%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(ctx) {
                                    return `${ctx.label}: ${ctx.parsed.toLocaleString()} loans`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // Custom legend
        const legend = document.getElementById('segment-legend');
        if (legend) {
            const total = data.segments.reduce((a, b) => a + b.total_loans, 0);
            legend.innerHTML = data.segments.map((s, i) => `
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <div class="w-3 h-3 rounded-full flex-shrink-0" style="background:${colors[i]}"></div>
                        <span class="text-label-md text-on-surface-variant">${s.segment}</span>
                    </div>
                    <span class="text-label-md font-bold">${((s.total_loans / total) * 100).toFixed(0)}%</span>
                </div>
            `).join('');
        }
    }

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