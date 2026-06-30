// ── Early Warning Page Logic ──────────────────────────────

let allWarnings = [];

async function loadWarningsPage() {
    const data = await fetchWithFreshness(`${API_BASE}/early-warning`);
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

    // Hide loading indicator
    const tableLoading = document.getElementById('table-loading');
    if (tableLoading) tableLoading.style.display = 'none';

    renderTable(allWarnings);

    // ── Intelligence Advisory ─────────────────────────────
    renderIntelligenceAdvisory(data);

    // ── Portfolio Health Index ────────────────────────────
    const portfolio = await fetchWithFreshness(`${API_BASE}/portfolio`);
    if (portfolio && portfolio.health_scores) {
        const avgHealth = portfolio.health_scores.reduce((a, b) => a + b.health_score, 0) / portfolio.health_scores.length;
        const healthEl = document.getElementById('portfolio-health-index');
        const statusEl = document.getElementById('portfolio-health-status');
        if (healthEl) healthEl.textContent = avgHealth.toFixed(1);
        if (statusEl) {
            if (avgHealth >= 80) statusEl.textContent = 'Stable Condition';
            else if (avgHealth >= 60) statusEl.textContent = 'Moderate — Monitor Closely';
            else statusEl.textContent = 'At Risk — Action Required';
        }
    }
}

function renderIntelligenceAdvisory(data) {
    const container = document.getElementById('intelligence-advisory-content');
    if (!container) return;

    const dist = data.distribution;
    const total = (dist.CRITICAL || 0) + (dist.WARNING || 0) + (dist.WATCH || 0);
    const criticalPct = total > 0 ? ((dist.CRITICAL || 0) / total * 100) : 0;

    const advisories = [];

    if (criticalPct > 20) {
        advisories.push({
            level: 'error',
            title: 'High Critical Exposure',
            text: `${(dist.CRITICAL || 0).toLocaleString()} accounts (${criticalPct.toFixed(0)}% of flagged loans) are CRITICAL. Immediate portfolio review recommended — consider tightening approval thresholds.`
        });
    } else if (criticalPct > 10) {
        advisories.push({
            level: 'warning',
            title: 'Elevated Critical Count',
            text: `${(dist.CRITICAL || 0).toLocaleString()} critical accounts detected. Close monitoring of delinquency patterns advised.`
        });
    }

    if ((dist.WARNING || 0) > (dist.WATCH || 0) * 1.5 && (dist.WARNING || 0) > 20) {
        advisories.push({
            level: 'warning',
            title: 'Warning Cluster Detected',
            text: `Warning-level accounts (${dist.WARNING}) significantly outpace Watch-level (${dist.WATCH || 0}). Potential systemic risk brewing in one or more segments.`
        });
    }

    if ((dist.HEALTHY || 0) > (dist.CRITICAL || 0) * 10) {
        advisories.push({
            level: 'success',
            title: 'Strong Portfolio Base',
            text: `Healthy accounts outnumber critical ones 10-to-1. Current risk monitoring framework appears effective.`
        });
    }

    if (advisories.length === 0) {
        advisories.push({
            level: 'info',
            title: 'Portfolio Status Nominal',
            text: `No unusual patterns detected. ${total.toLocaleString()} flagged accounts across all warning levels within expected ranges.`
        });
    }

    const colorMap = {
        error: { bg: 'bg-error/10', border: 'border-error/20', text: 'text-on-surface', label: 'text-error' },
        warning: { bg: 'bg-primary-container/5', border: 'border-primary-container/20', text: 'text-on-surface', label: 'text-primary' },
        success: { bg: 'bg-tertiary-container/5', border: 'border-tertiary-container/20', text: 'text-on-surface', label: 'text-tertiary' },
        info: { bg: 'bg-secondary/5', border: 'border-secondary/20', text: 'text-on-surface', label: 'text-secondary' }
    };

    container.innerHTML = advisories.map(a => {
        const c = colorMap[a.level];
        return `
            <div class="p-4 ${c.bg} rounded-lg border ${c.border}">
                <p class="font-body-md text-body-md ${c.text}">
                    <strong class="${c.label}">${a.title}:</strong> ${a.text}
                </p>
            </div>
        `;
    }).join('');
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
        <tr class="hover:bg-surface-container-high transition-colors" data-status="${status}">
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

// ── Search Bar ────────────────────────────────────────────
function filterWarnings(query) {
    const q = query.toLowerCase();
    const rows = document.querySelectorAll('#warning-table-body tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadWarningsPage();

    const filterSelect = document.getElementById('filter-level');
    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => filterByLevel(e.target.value));
    }

    const searchInput = document.querySelector('#warnings-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => filterWarnings(searchInput.value), 200);
        });
    }
});