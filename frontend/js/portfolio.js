// ── Portfolio Page Logic ──────────────────────────────────

async function loadPortfolioPage() {
    const data = await fetchPortfolio();
    if (!data) return;

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
                <tr class="hover:bg-surface-container-low transition-colors group">
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
            <div class="bg-surface-container-lowest rounded-xl border border-outline-variant card-shadow p-5 hover:border-primary transition-all group cursor-pointer">
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
}

document.addEventListener('DOMContentLoaded', loadPortfolioPage);