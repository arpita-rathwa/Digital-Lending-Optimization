// ── Portfolio Page Logic ──────────────────────────────────

async function loadPortfolioPage() {
    const data = await fetchWithFreshness(`${API_BASE}/portfolio`);
    if (!data) {
        const loading = document.getElementById('table-loading');
        if (loading) loading.innerHTML = '<td colspan="7" class="px-6 py-12 text-center text-on-surface-variant">Failed to load portfolio data</td>';
        return;
    }
    // Hide loading indicators
    const tableLoading = document.getElementById('table-loading');
    if (tableLoading) tableLoading.style.display = 'none';
    const segLoading = document.getElementById('segments-loading');
    if (segLoading) segLoading.style.display = 'none';

    // ── Medium Comparison Table ───────────────────────────
    const tableBody = document.getElementById('medium-table-body');
    if (tableBody) {
        const maxDefault = Math.max(...data.medium_summary.map(m => m.default_rate));

        tableBody.innerHTML = data.medium_summary
            .sort((a, b) => b.health_score - a.health_score)
            .map((m, i) => {
                const health = data.health_scores.find(h => h.lending_medium === m.lending_medium);
                const healthScore = health ? health.health_score : 0;
                const defPct = (m.default_rate * 100).toFixed(1);
                const barWidth = ((m.default_rate / maxDefault) * 100).toFixed(0);
                const healthColor = healthScore >= 80 ? 'text-tertiary' : healthScore >= 60 ? 'text-primary-container' : 'text-primary';
                const healthBarColor = healthScore >= 80 ? 'bg-tertiary' : healthScore >= 60 ? 'bg-primary-container' : 'bg-primary';
                const defBarColor = m.default_rate >= 0.3 ? 'bg-primary' : m.default_rate >= 0.15 ? 'bg-primary-container' : 'bg-tertiary';

                return `
                <tr class="hover:bg-surface-container-low transition-colors group" data-medium="${m.lending_medium.toLowerCase()}">
                    <td class="px-6 py-4 font-bold text-primary">${String(i+1).padStart(2,'0')}</td>
                    <td class="px-6 py-4 font-semibold">${m.lending_medium}</td>
                    <td class="px-6 py-4 text-right">${m.total_loans.toLocaleString()}</td>
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-3">
                            <span class="w-12">${defPct}%</span>
                            <div class="w-24 h-1.5 bg-surface-container rounded-full overflow-hidden">
                                <div class="h-full ${defBarColor}" style="width:${barWidth}%"></div>
                            </div>
                        </div>
                    </td>
                    <td class="px-6 py-4 text-right">${formatCurrency(m.avg_loan_amount)}</td>
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            <div class="flex-1 h-1.5 bg-surface-container rounded-full overflow-hidden">
                                <div class="h-full ${healthBarColor}" style="width:${healthScore}%"></div>
                            </div>
                            <span class="${healthColor} font-bold">${healthScore}</span>
                        </div>
                    </td>
                    <td class="px-6 py-4 text-right font-semibold">${m.avg_interest_rate.toFixed(1)}%</td>
                </tr>`;
            }).join('');
    }

    // ── Segment Grid ──────────────────────────────────────
    const segGrid = document.getElementById('segment-grid');
    if (segGrid && data.segments) {
        segGrid.innerHTML = data.segments.map(s => {
            const defPct = (s.default_rate * 100).toFixed(1);
            const defColor = s.default_rate >= 0.3
                ? 'bg-primary/10 text-primary'
                : s.default_rate >= 0.1
                ? 'bg-primary-container/10 text-primary-container'
                : 'bg-tertiary/10 text-tertiary';
            const trendIcon = s.default_rate >= 0.3 ? 'trending_down' : s.default_rate >= 0.1 ? 'trending_flat' : 'trending_up';
            const trendColor = s.default_rate >= 0.3 ? 'text-primary' : s.default_rate >= 0.1 ? 'text-primary-container' : 'text-tertiary';

            return `
            <div class="bg-surface-container-lowest rounded-xl border border-outline-variant card-shadow p-5 hover:border-primary transition-all group cursor-pointer" data-segment="${s.segment.toLowerCase()}">
                <div class="flex justify-between items-start mb-4">
                    <h4 class="font-label-md text-label-md font-bold text-on-surface uppercase tracking-tight">${s.segment}</h4>
                    <span class="material-symbols-outlined text-[18px] ${trendColor}">${trendIcon}</span>
                </div>
                <div class="space-y-4">
                    <div class="flex justify-between items-end">
                        <span class="font-label-sm text-label-sm opacity-60">Loan Count</span>
                        <span class="font-headline-md text-headline-md">${s.total_loans.toLocaleString()}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="font-label-sm text-label-sm opacity-60">Default Rate</span>
                        <span class="px-2 py-0.5 ${defColor} rounded text-label-sm font-bold">${defPct}%</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="font-label-sm text-label-sm opacity-60">Avg Loan</span>
                        <span class="font-body-md text-body-md font-bold">${formatCurrency(s.avg_loan)}</span>
                    </div>
                    <div class="pt-2 border-t border-outline-variant">
                        <p class="font-label-sm text-label-sm opacity-60 mb-1">Recommended Rate</p>
                        <p class="font-body-md text-body-md font-bold text-primary">${s.avg_recommended_rate.toFixed(1)}%</p>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    // ── Default Rate by Medium Chart ───────────────────────
    const defCtx = document.getElementById('defaultRateChart');
    if (defCtx) {
        const sorted = [...data.medium_summary].sort((a, b) => b.default_rate - a.default_rate);
        new Chart(defCtx, {
            type: 'bar',
            data: {
                labels: sorted.map(m => m.lending_medium),
                datasets: [{
                    label: 'Default Rate %',
                    data: sorted.map(m => (m.default_rate * 100).toFixed(1)),
                    backgroundColor: '#b52330',
                    borderRadius: 6,
                    maxBarThickness: 60
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: ctx => `Default Rate: ${ctx.parsed.y}%` }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: v => v + '%' },
                        grid: { color: '#f7dcdb' }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // ── Health Score / Risk Distribution Chart ─────────────
    const riskCtx = document.getElementById('riskTierChart');
    if (riskCtx) {
        const sorted = [...data.health_scores].sort((a, b) => b.health_score - a.health_score);
        new Chart(riskCtx, {
            type: 'bar',
            data: {
                labels: sorted.map(h => h.lending_medium),
                datasets: [{
                    label: 'Health Score',
                    data: sorted.map(h => h.health_score),
                    backgroundColor: sorted.map(h =>
                        h.health_score >= 80 ? '#006c4c' : h.health_score >= 60 ? '#ff5a5f' : '#b52330'
                    ),
                    borderRadius: 6,
                    maxBarThickness: 60
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: ctx => `Health Score: ${ctx.parsed.y}` }
                    }
                },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: '#f7dcdb' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // ── AI Portfolio Explanation ──────────────────────────
    const aiEl = document.getElementById('ai-explanation');
    if (aiEl) {
        const result = await fetchPortfolioExplanation();
        if (result && result.explanation) {
            aiEl.innerHTML = `<div class="text-body-md text-on-surface leading-relaxed whitespace-pre-line">${escapeHtml(result.explanation)}</div>`;
        } else {
            aiEl.innerHTML = `<div class="text-on-surface-variant font-body-md py-4">Portfolio analysis unavailable.</div>`;
        }
    }

    // ── SHAP Feature Importance (if container exists) ──────
    const shapContainer = document.getElementById('shap-features');
    if (shapContainer) {
        const shapData = await fetchShap();
        if (shapData && shapData.length) {
            const maxImp = shapData[0].importance;
            shapContainer.innerHTML = shapData.slice(0, 10).map((f, i) => `
                <div class="flex items-center gap-3 py-2">
                    <span class="text-label-sm text-on-surface-variant w-4">${i+1}</span>
                    <span class="text-body-md font-medium flex-1">${f.feature}</span>
                    <div class="w-32 h-2 bg-surface-container rounded-full overflow-hidden">
                        <div class="h-full rounded-full bg-primary" style="width:${(f.importance/maxImp*100).toFixed(0)}%"></div>
                    </div>
                    <span class="text-label-md font-bold text-primary w-16 text-right">${f.importance.toFixed(3)}</span>
                </div>
            `).join('');
        }
    }
}

// ── Search Bar ────────────────────────────────────────────
function filterPortfolio(query) {
    const q = query.toLowerCase();
    const tableRows = document.querySelectorAll('#medium-table-body tr');
    const segCards = document.querySelectorAll('#segment-grid > div');

    tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
    });

    segCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? '' : 'none';
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    loadPortfolioPage();

    const searchInput = document.querySelector('#portfolio-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => filterPortfolio(searchInput.value), 200);
        });
    }
});