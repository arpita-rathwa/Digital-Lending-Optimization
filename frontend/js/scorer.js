// ── Risk Scorer Page Logic ────────────────────────────────

function getFormData() {
    const termSelect = document.getElementById('f-term-months');
    const termValue = termSelect ? parseFloat(termSelect.value) : 24;

    const empSelect = document.getElementById('f-emp-length');
    const empValue = empSelect ? parseFloat(empSelect.value) : 4;

    // Mobile score slider is 1-100, map to 300-850
    const mobileRaw = parseFloat(document.getElementById('f-mobile-score')?.value || 65);
    const mobileScore = 300 + (mobileRaw / 100) * 550;

    return {
        loan_amount: parseFloat(document.getElementById('f-loan-amount')?.value || 25000),
        term_months: termValue,
        lending_medium: document.getElementById('f-lending-medium')?.value || 'Bank',
        interest_rate: parseFloat(document.getElementById('f-interest-rate')?.value || 12.5) || null,
        income: parseFloat(document.getElementById('f-income')?.value || 85000),
        dti: parseFloat(document.getElementById('f-dti')?.value || 28.4),
        credit_score: parseFloat(document.getElementById('f-credit-score')?.value || 720),
        employment_length: empValue,
        mobile_credit_score: mobileScore,
        upi_transaction_count: parseInt(document.getElementById('f-upi-count')?.value || 45),
        digital_onboarding: document.getElementById('f-digital-onboarding')?.checked ? 1 : 0,
        first_time_borrower: document.getElementById('f-first-timer')?.checked ? 1 : 0,
        urban_flag: document.getElementById('f-urban')?.checked ? 1 : 0,
        home_ownership: document.getElementById('f-home-ownership')?.value || 'RENT'
    };
}

function updateGauge(probability) {
    // Circumference = 2 * pi * 88 = 552.92
    const circumference = 552.92;
    const pct = probability * 100;
    // Higher prob = more of gauge filled = less offset
    const offset = circumference - (pct / 100 * circumference);

    const circle = document.getElementById('gauge-circle');
    const valueEl = document.getElementById('gauge-value');

    if (circle) {
        circle.setAttribute('stroke-dashoffset', offset.toFixed(2));
        // Change color based on risk
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
        valueEl.textContent = (100 - pct).toFixed(0) + '%';
    }
}

function showResults(result) {
    // Decision badge
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

    // Gauge
    updateGauge(result.risk.default_probability);

    // Default probability text
    const probEl = document.getElementById('result-prob');
    if (probEl) probEl.textContent = `Default Probability: ${(result.risk.default_probability * 100).toFixed(1)}%`;

    // Risk tier
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

    // Expected loss
    const lossEl = document.getElementById('result-expected-loss');
    if (lossEl) lossEl.textContent = formatCurrency(result.risk.expected_loss);

    // Early warning
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

    // Rates
    const recRateEl = document.getElementById('result-rec-rate');
    const currRateEl = document.getElementById('result-curr-rate');
    if (recRateEl) recRateEl.textContent = result.pricing.recommended_rate + '%';
    if (currRateEl) currRateEl.textContent = result.pricing.current_rate + '%';

    // Segment
    const segEl = document.getElementById('result-segment');
    if (segEl) segEl.textContent = result.segment.name;

    // Warning flags
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
}

async function assessRiskHandler() {
    const btn = document.getElementById('assess-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined animate-spin">autorenew</span> Analysing...';
    }

    const formData = getFormData();
    const result = await predictRisk(formData);

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined">bolt</span> ASSESS RISK';
    }

    if (!result) {
        const warnEl = document.getElementById('result-warning');
        if (warnEl) {
            warnEl.textContent = 'Error: Could not reach the API. Is the backend running?';
            warnEl.className = 'font-bold text-body-md text-error';
        }
        return;
    }

    if (result.detail) {
        const warnEl = document.getElementById('result-warning');
        if (warnEl) {
            warnEl.textContent = 'API Error: ' + result.detail;
            warnEl.className = 'font-bold text-body-md text-error';
        }
        return;
    }

    showResults(result);
}

document.addEventListener('DOMContentLoaded', () => {
    const assessBtn = document.getElementById('assess-btn');
    if (assessBtn) assessBtn.addEventListener('click', assessRiskHandler);
});