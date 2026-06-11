// ── Early Warning Page Logic ──────────────────────────────

let allWarnings = [];
let activeFilter = 'ALL';

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
    if (healthyEl) healthyEl.textContent =(dist.HEALTHY || 0).toLocaleString();
}

function renderTable(warnings) {
    const tbody = document.getElementById('warning-table-body');
    if (!tbody) return;

    if (warnings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-12 text-center text-on-surface-variant text-body-md">
                    No warnings match the current filter
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = warnings.map((loan, i) => {
        const prob = (loan.default_probability * 100).toFixed(1);
        const probColor = loan.default_probability >= 0.65 ? '#ef4444' : loan.default_probability >= 0.5 ? '#f59e0b' : '#3b82f6';
        const warnBg = getWarningBg(loan.early_warning);

        return `
        <tr class="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
            <td class="px-6 py-4 text-label-md font-bold text-on-surface-variant">#${String(i+1).padStart(2,'0')}</td>
            <td class="px-6 py-4">
                <span class="px-3 py-1 rounded-full text-label-md font-bold border ${warnBg}">${loan.early_warning}</span>
            </td>
            <td class="px-6 py-4 font-semibold text-on-surface">${loan.lending_medium}</td>
            <td class="px-6 py-4 font-bold text-on-surface">${formatCurrency(loan.loan_amount)}</td>
            <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden max-w-[60px]">
                        <div class="h-full rounded-full" style="width:${prob}%;background:${probColor}"></div>
                    </div>
                    <span class="font-bold text-label-md" style="color:${probColor}">${prob}%</span>
                </div>
            </td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-label-sm font-bold" 
                    style="background:${getRiskColor(loan.predicted_risk_tier)}20;color:${getRiskColor(loan.predicted_risk_tier)}">
                    ${loan.predicted_risk_tier || 'N/A'}
                </span>
            </td>
            <td class="px-6 py-4 text-body-md font-semibold text-primary">${loan.recommended_rate ? loan.recommended_rate.toFixed(1) + '%' : 'N/A'}</td>
        </tr>`;
    }).join('');
}

function filterWarnings(level) {
    activeFilter = level;

    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('bg-primary', 'text-on-primary');
        btn.classList.add('bg-white', 'text-on-surface');
    });
    const activeBtn = document.getElementById(`filter-${level.toLowerCase()}`);
    if (activeBtn) {
        activeBtn.classList.add('bg-primary', 'text-on-primary');
        activeBtn.classList.remove('bg-white', 'text-on-surface');
    }

    if (level === 'ALL') {
        renderTable(allWarnings);
    } else {
        renderTable(allWarnings.filter(w => w.early_warning === level));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadWarningsPage();

    // Wire filter buttons
    ['ALL', 'CRITICAL', 'WARNING', 'WATCH'].forEach(level => {
        const btn = document.getElementById(`filter-${level.toLowerCase()}`);
        if (btn) btn.addEventListener('click', () => filterWarnings(level));
    });
});


