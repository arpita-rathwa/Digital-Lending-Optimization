// ── Risk Scorer Page Logic ────────────────────────────────

function getFormData() {
    const termSelect = document.getElementById('f-term-months');
    const termValue = termSelect ? parseFloat(termSelect.value) : null;

    const empSelect = document.getElementById('f-emp-length');
    const empValue = empSelect ? parseFloat(empSelect.value) : null;

    const mobileRaw = parseFloat(document.getElementById('f-mobile-score')?.value);
    const mobileScore = mobileRaw ? 300 + (mobileRaw / 100) * 550 : null;

    return {
        loan_amount: parseFloat(document.getElementById('f-loan-amount')?.value) || null,
        term_months: termValue,
        lending_medium: document.getElementById('f-lending-medium')?.value || 'Bank',
        interest_rate: parseFloat(document.getElementById('f-interest-rate')?.value) || null,
        income: parseFloat(document.getElementById('f-income')?.value) || null,
        dti: parseFloat(document.getElementById('f-dti')?.value) || null,
        credit_score: parseFloat(document.getElementById('f-credit-score')?.value) || null,
        employment_length: empValue,
        mobile_credit_score: mobileScore,
        upi_transaction_count: parseInt(document.getElementById('f-upi-count')?.value) || null,
        digital_onboarding: document.getElementById('f-digital-onboarding')?.checked ? 1 : 0,
        first_time_borrower: document.getElementById('f-first-timer')?.checked ? 1 : 0,
        urban_flag: document.getElementById('f-urban')?.checked ? 1 : 0,
        home_ownership: document.getElementById('f-home-ownership')?.value || 'RENT'
    };
}

function showSkeletons() {
    const resultPanel = document.querySelector('.lg\\:col-span-5');
    if (!resultPanel) return;
    resultPanel.querySelectorAll('.skeleton-target').forEach(el => {
        el.innerHTML = skeletonBox('h-6', 'w-3/4');
    });
    document.getElementById('gauge-value').textContent = '—';
}

function updateGauge(probability) {
    const circumference = 552.92;
    const pct = probability * 100;
    const safetyScore = 100 - pct;
    const offset = circumference - (safetyScore / 100 * circumference);

    const circle = document.getElementById('gauge-circle');
    const valueEl = document.getElementById('gauge-value');

    if (circle) {
        circle.setAttribute('stroke-dashoffset', offset.toFixed(2));
        if (probability >= 0.65) {
            circle.classList.remove('text-tertiary-container', 'text-yellow-300');
            circle.classList.add('text-error');
        } else if (probability >= 0.40) {
            circle.classList.remove('text-tertiary-container', 'text-error');
            circle.classList.add('text-yellow-300');
        } else {
            circle.classList.remove('text-error', 'text-yellow-300');
            circle.classList.add('text-tertiary-container');
        }
    }

    if (valueEl) {
        valueEl.textContent = safetyScore.toFixed(0) + '%';
    }
}

function showResults(result) {
    const decisionEl = document.getElementById('result-decision');
    if (decisionEl) {
        const approved = result.approval.approved;
        decisionEl.textContent = result.approval.decision;
        decisionEl.className = `inline-flex items-center px-6 py-2 rounded-full font-bold text-headline-md border ${
            approved
                ? 'bg-tertiary/10 text-tertiary border-tertiary/20'
                : 'bg-error/10 text-error border-error/20'
        }`;
    }

    updateGauge(result.risk.default_probability);

    const probEl = document.getElementById('result-prob');
    if (probEl) probEl.textContent = `Default Probability: ${(result.risk.default_probability * 100).toFixed(1)}%`;

    const tierEl = document.getElementById('result-risk-tier');
    if (tierEl) {
        tierEl.textContent = result.risk.risk_tier + ' Risk';
        const colors = {
            High: 'bg-error/10 text-error border-error/20',
            Medium: 'bg-[#ff9800]/10 text-[#ff9800] border-[#ff9800]/20',
            Low: 'bg-tertiary/10 text-tertiary border-tertiary/20'
        };
        tierEl.className = `px-3 py-1 rounded-full font-bold text-body-md border ${colors[result.risk.risk_tier] || colors.Low}`;
    }

    const lossEl = document.getElementById('result-expected-loss');
    if (lossEl) lossEl.textContent = formatCurrency(result.risk.expected_loss);

    const warnEl = document.getElementById('result-warning');
    if (warnEl) {
        const status = result.risk.early_warning;
        const messages = {
            HEALTHY: 'Clear - No red flags detected in credit history.',
            WATCH: 'Watch - Minor risk signals detected. Monitor closely.',
            WARNING: 'Warning - Multiple risk factors identified.',
            CRITICAL: 'Critical - High risk profile. Review required.'
        };
        warnEl.textContent = messages[status] || status;
        const warnColor = status === 'HEALTHY' ? 'text-tertiary' : status === 'WATCH' ? 'text-[#ffd600]' : status === 'WARNING' ? 'text-[#ff9800]' : 'text-error';
        warnEl.className = `font-bold text-body-md ${warnColor}`;
    }

    const recRateEl = document.getElementById('result-rec-rate');
    const currRateEl = document.getElementById('result-curr-rate');
    if (recRateEl) recRateEl.textContent = result.pricing.recommended_rate + '%';
    if (currRateEl) currRateEl.textContent = result.pricing.current_rate + '%';

    const segEl = document.getElementById('result-segment');
    if (segEl) segEl.textContent = result.segment.name;

    const flagsEl = document.getElementById('result-flags');
    if (flagsEl) {
        if (!result.risk.warning_flags || result.risk.warning_flags.length === 0) {
            flagsEl.innerHTML = '<div class="bg-tertiary/10 text-tertiary px-3 py-1 rounded-full text-label-sm font-bold border border-tertiary/20">No Risk Flags</div>';
        } else {
            flagsEl.innerHTML = result.risk.warning_flags.map(flag =>
                `<div class="bg-error-container text-on-error-container px-3 py-1 rounded-full text-label-sm font-bold border border-error/10">${flag.replace(/_/g, ' ')}</div>`
            ).join('');
        }
    }

    // Persist to sessionStorage for navigation resilience
    try { sessionStorage.setItem('lendiq_last_result', JSON.stringify(result)); } catch (e) { /* noop */ }
}

function showErrorState(msg) {
    const warnEl = document.getElementById('result-warning');
    if (warnEl) {
        warnEl.textContent = msg;
        warnEl.className = 'font-bold text-body-md text-error';
    }
    const btn = document.getElementById('assess-btn');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined">bolt</span> ASSESS RISK';
    }
}

async function assessRiskHandler() {
    const btn = document.getElementById('assess-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined animate-spin">autorenew</span> Analysing...';
    }
    showSkeletons();

    const formData = getFormData();
    const result = await fetchWithRetry(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    }, 2);

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined">bolt</span> ASSESS RISK';
    }

    if (!result) {
        showErrorState('⚠ Error: Could not reach the API. <button class="underline ml-2" onclick="assessRiskHandler()">Retry</button>');
        return;
    }

    if (result.detail) {
        showErrorState('API Error: ' + result.detail);
        return;
    }

    showResults(result);
}

document.addEventListener('DOMContentLoaded', () => {
    const assessBtn = document.getElementById('assess-btn');
    if (assessBtn) assessBtn.addEventListener('click', assessRiskHandler);

    // Restore last result from sessionStorage
    try {
        const saved = sessionStorage.getItem('lendiq_last_result');
        if (saved) {
            const parsed = JSON.parse(saved);
            if (parsed.risk && parsed.approval) showResults(parsed);
        }
    } catch (e) { /* noop */ }

    // Debounced auto-assessment on input change
    let debounceTimer;
    document.querySelectorAll('#f-loan-amount, #f-term-months, #f-lending-medium, #f-interest-rate, #f-income, #f-dti, #f-credit-score, #f-emp-length, #f-mobile-score, #f-upi-count, #f-digital-onboarding, #f-first-timer, #f-urban, #f-home-ownership').forEach(el => {
        el.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(assessRiskHandler, 600);
        });
        el.addEventListener('change', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(assessRiskHandler, 600);
        });
    });

    // Clear result placeholders on page load
    document.getElementById('gauge-value').textContent = '—';
    document.getElementById('result-decision').innerHTML = '<span class="material-symbols-outlined mr-2">hourglass_empty</span> PENDING';
    document.getElementById('result-prob').textContent = 'Default Probability: awaiting input';
    document.getElementById('result-risk-tier').textContent = '—';
    document.getElementById('result-expected-loss').textContent = '—';
    document.getElementById('result-rec-rate').textContent = '—';
    document.getElementById('result-curr-rate').textContent = '—';
    document.getElementById('result-segment').textContent = '—';
    document.getElementById('result-flags').innerHTML = '<div class="bg-surface-container text-on-surface-variant px-3 py-1 rounded-full text-label-sm font-bold">Enter borrower details to assess</div>';
    document.getElementById('result-warning').textContent = 'Awaiting assessment';

    // Scorer search bar (filter result panel)
    const scorerSearch = document.getElementById('scorer-search');
    if (scorerSearch) {
        let searchTimer;
        scorerSearch.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                const q = scorerSearch.value.toLowerCase();
                document.querySelectorAll('.lg\\:col-span-5 .skeleton-target, .lg\\:col-span-5 p, .lg\\:col-span-5 .flex-wrap').forEach(el => {
                    if (!q) { el.style.opacity = '1'; return; }
                    const text = el.textContent.toLowerCase();
                    el.style.opacity = text.includes(q) ? '1' : '0.3';
                });
            }, 200);
        });
    }
});