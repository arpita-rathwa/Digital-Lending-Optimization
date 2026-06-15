// ── LendIQ API Integration ────────────────────────────────
// To point at a local backend during development, set window.API_BASE
// in your browser console or in a local script tag before api.js loads:
//     window.API_BASE = 'http://localhost:8000';
const API_BASE = (typeof window !== 'undefined' && window.API_BASE)
    ? window.API_BASE
    : 'https://digital-lending-optimization-1.onrender.com';

// ── Fetch Portfolio Data ──────────────────────────────────
async function fetchPortfolio() {
    try {
        const res = await fetch(`${API_BASE}/portfolio`);
        return await res.json();
    } catch (e) {
        console.error('Portfolio fetch failed:', e);
        return null;
    }
}

// ── Fetch Early Warning Queue ─────────────────────────────
async function fetchWarnings() {
    try {
        const res = await fetch(`${API_BASE}/early-warning`);
        return await res.json();
    } catch (e) {
        console.error('Warning fetch failed:', e);
        return null;
    }
}

// ── Fetch SHAP Importance ─────────────────────────────────
async function fetchShap() {
    try {
        const res = await fetch(`${API_BASE}/shap`);
        return await res.json();
    } catch (e) {
        console.error('SHAP fetch failed:', e);
        return null;
    }
}

// ── Predict Borrower Risk ─────────────────────────────────
async function predictRisk(borrowerData) {
    try {
        const res = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(borrowerData)
        });
        return await res.json();
    } catch (e) {
        console.error('Predict failed:', e);
        return null;
    }
}

// ── Helpers ───────────────────────────────────────────────
function formatCurrency(val) {
    if (!val) return '$0';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + (val / 1e3).toFixed(1) + 'K';
    return '$' + val.toFixed(0);
}

function getRiskColor(tier) {
    return { High: '#ef4444', Medium: '#f59e0b', Low: '#22c55e' }[tier] || '#6b7280';
}

function getWarningColor(status) {
    return { CRITICAL: '#ef4444', WARNING: '#f59e0b', WATCH: '#3b82f6', HEALTHY: '#22c55e' }[status] || '#6b7280';
}

function getWarningBg(status) {
    return {
        CRITICAL: 'bg-red-50 text-red-700 border-red-200',
        WARNING: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        WATCH: 'bg-blue-50 text-blue-700 border-blue-200',
        HEALTHY: 'bg-green-50 text-green-700 border-green-200'
    }[status] || 'bg-gray-50 text-gray-700';
}

function getHealthColor(score) {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
}

function showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.innerHTML = '<div class="animate-pulse bg-gray-200 rounded h-6 w-24"></div>';
}

function showError(elementId, msg = 'Error loading') {
    const el = document.getElementById(elementId);
    if (el) el.textContent = msg;
}