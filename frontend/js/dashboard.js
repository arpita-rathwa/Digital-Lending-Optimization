// ── Dashboard Page Logic ──────────────────────────────────

async function loadDashboard() {
    const data = await fetchWithFreshness(`${API_BASE}/portfolio`);
    if (!data) return;

    // ── KPI Cards ─────────────────────────────────────────
    const totalVolume = data.medium_summary.reduce((a, b) => a + (b.avg_loan_amount * b.total_loans), 0);
    const avgDefault = data.medium_summary.reduce((a, b) => a + b.default_rate, 0) / data.medium_summary.length;
    const avgRate = data.medium_summary.reduce((a, b) => a + b.avg_interest_rate, 0) / data.medium_summary.length;
    const avgHealth = data.health_scores.reduce((a, b) => a + b.health_score, 0) / data.health_scores.length;

    const volEl = document.getElementById('kpi-volume');
    const defEl = document.getElementById('kpi-default');
    const rateEl = document.getElementById('kpi-rate');
    const approvalEl = document.getElementById('kpi-approval');

    if (volEl) volEl.textContent = formatCurrency(totalVolume);
    if (defEl) defEl.textContent = (avgDefault * 100).toFixed(1) + '%';
    if (rateEl) rateEl.textContent = avgRate.toFixed(1) + '%';
    if (approvalEl) approvalEl.textContent = (100 - avgDefault * 100).toFixed(1) + '%';

    // ── Medium Pills ──────────────────────────────────────
    data.health_scores.forEach(h => {
        const medium = h.lending_medium.toLowerCase().replace('finance', '');
        const key = medium === 'micro' ? 'micro' : medium === 'p2p' ? 'p2p' : medium === 'bank' ? 'bank' : 'sme';

        const healthEl = document.getElementById(`health-${key}`);
        const defMedEl = document.getElementById(`def-${key}`);

        if (healthEl) healthEl.textContent = h.health_score;
        if (defMedEl) defMedEl.textContent = `Def: ${(h.default_rate * 100).toFixed(1)}%`;
    });

    // ── Health Bars ───────────────────────────────────────
    const healthContainer = document.getElementById('health-bars-container');
    if (healthContainer && data.health_scores) {
        const sorted = [...data.health_scores].sort((a, b) => b.health_score - a.health_score);
        healthContainer.innerHTML = sorted.map(h => {
            const score = h.health_score;
            const color = score >= 80 ? 'bg-tertiary' : score >= 60 ? 'bg-primary-container' : 'bg-error';
            const textColor = score >= 80 ? 'text-tertiary' : score >= 60 ? 'text-primary-container' : 'text-error';
            const width = Math.min(score, 100);
            const name = h.lending_medium;
            return `
                <div>
                    <div class="flex justify-between text-label-md mb-1">
                        <span class="text-on-surface font-semibold">${name}</span>
                        <span class="${textColor} font-bold">${score.toFixed(2)}</span>
                    </div>
                    <div class="w-full bg-surface-container h-3 rounded-full overflow-hidden">
                        <div class="${color} h-full rounded-full" style="width: ${width}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

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
    const warnData = await fetchWithFreshness(`${API_BASE}/early-warning`);
    if (warnData) {
        const critEl = document.getElementById('warn-critical');
        const warnEl = document.getElementById('warn-warning');
        const watchEl = document.getElementById('warn-watch');
        if (critEl) critEl.textContent = (warnData.distribution.CRITICAL || 0).toLocaleString();
        if (warnEl) warnEl.textContent = (warnData.distribution.WARNING || 0).toLocaleString();
        if (watchEl) watchEl.textContent = (warnData.distribution.WATCH || 0).toLocaleString();
    }
}

// ── Search Bar ────────────────────────────────────────────
function filterDashboardTable(query) {
    const containers = document.querySelectorAll('#health-bars-container > div');
    const q = query.toLowerCase();
    const pills = document.querySelectorAll('.medium-pill');
    const segments = document.querySelectorAll('#segment-legend > div');
    const warnCards = document.querySelectorAll('.warn-summary-card');

    containers.forEach((el, i) => {
        const text = el.textContent.toLowerCase();
        el.style.display = text.includes(q) ? '' : 'none';
    });

    pills.forEach((el, i) => {
        const text = el.textContent.toLowerCase();
        el.style.display = text.includes(q) ? '' : 'none';
    });

    segments.forEach((el, i) => {
        const text = el.textContent.toLowerCase();
        el.style.display = text.includes(q) ? '' : 'none';
    });

    warnCards.forEach((el, i) => {
        const text = el.textContent.toLowerCase();
        el.style.display = text.includes(q) ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();

    const searchInput = document.querySelector('#dashboard-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => filterDashboardTable(searchInput.value), 200);
        });
    }
});