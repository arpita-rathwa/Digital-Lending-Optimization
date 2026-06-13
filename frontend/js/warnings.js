// ── Early Warning Page Logic ──────────────────────────────

let allWarnings = [];

async function loadWarningsPage() {
    const data = await fetchWarnings();
    if (!data) return;

    allWarnings = data.queue;

    // ── Summary Bar ───────────────────────────────────────
    const dist = data.distribution;
    const critEl = document.getElementById('summary-critical');
    const warnEl = document.getElementById('summary-warning');
    const watchEl = document.getElementById('summary-watch');
    const healthyEl = document.getElementById('summary-healthy');

    if (critEl) critEl.textContent = (dist.CRITICAL || 0).toLocaleString();
    if (warnEl) warnEl.textContent = (dist.WARNING || 0).toLocaleString();
    if (watchEl) watchEl.textContent = (dist.WATCH || 0).toLocaleString();
    if (healthyEl) healthyEl.textContent = (dist.HEALTHY || 0).toLocaleString();

    renderTable(allWarnings);
}

function getRiskTierLabel(tier) {
    const map = { Low: 'Tier 1 (A)', Medium: 'Tier 3 (C)', High: 'Tier 5 (E)' };
    return map[tier] || tier || 'N/A';
}

function getStatusBadge(status) {
    const styles = {
        CRITICAL: 'bg-error/10 text-error',
        WARNING: 'bg-primary/10 text-primary',
        WATCH: 'bg-secondary/10 text-secondary',
        HEALTHY: 'bg-tertiary/10 text-tertiary'
    };
    return styles[status] || 'bg-secondary/10 text-secondary';
}

function getProbBarColor(status) {
    const colors = {
        CRITICAL: 'bg-error',
        WARNING: 'bg-primary',
        WATCH: 'bg-secondary',
        HEALTHY: 'bg-tertiary'
    };
    return colors[status] || 'bg-secondary';
}

function getRiskTierColor(tier) {
    const colors = { Low: 'text-tertiary', Medium: 'text-secondary', High: 'text-error' };
    return colors[tier] || 'text-secondary';
}

function renderTable(warnings) {
    const tbody = document.getElementById('warning-table-body');
    if (!tbody) return;

    if (warnings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="px-6 py-12 text-center text-on-surface-variant">
                    No warnings match the current filter
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = warnings.slice(0, 50).map((loan, i) => {
        const prob = (loan.default_probability * 100).toFixed(1);
        const status = loan.early_warning;

        return `
        <tr class="hover:bg-surface-container-high transition-colors">
            <td class="px-6 py-5 font-body-md text-body-md font-bold text-on-surface">#${i+1}</td>
            <td class="px-6 py-5">
                <span class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full font-label-sm text-label-sm">${loan.lending_medium}</span>
            </td>
            <td class="px-6 py-5 font-body-md text-body-md text-on-surface">${formatCurrency(loan.loan_amount)}</td>
            <td class="px-6 py-5">
                <div class="flex flex-col gap-1 w-24">
                    <span class="font-label-sm text-label-sm text-on-surface-variant">${prob}%</span>
                    <div class="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden">
                        <div class="h-full ${getProbBarColor(status)} rounded-full" style="width:${prob}%;"></div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-5">
                <span class="${getRiskTierColor(loan.predicted_risk_tier)} font-bold font-body-md text-body-md">${getRiskTierLabel(loan.predicted_risk_tier)}</span>
            </td>
            <td class="px-6 py-5 font-body-md text-body-md text-on-surface">${loan.recommended_rate ? loan.recommended_rate.toFixed(1) + '%' : 'N/A'}</td>
            <td class="px-6 py-5">
                <span class="${getStatusBadge(status)} px-2 py-1 rounded-md font-label-md text-label-md font-bold">${status}</span>
            </td>
            <td class="px-6 py-5">
                <div class="flex gap-1 text-on-surface-variant">—</div>
            </td>
            <td class="px-6 py-5 text-right">
                <button class="text-primary font-label-md text-label-md hover:underline">Review</button>
            </td>
        </tr>`;
    }).join('');
}

function filterByLevel(level) {
    if (level === 'All Levels' || level === 'ALL') {
        renderTable(allWarnings);
    } else {
        renderTable(allWarnings.filter(w => w.early_warning === level));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadWarningsPage();

    const filterSelect = document.getElementById('filter-level');
    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => filterByLevel(e.target.value));
    }
});