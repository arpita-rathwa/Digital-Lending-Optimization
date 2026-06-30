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

// ── Fetch Portfolio AI Explanation ────────────────────────
async function fetchPortfolioExplanation() {
    try {
        const res = await fetch(`${API_BASE}/portfolio/explain`, { method: 'POST' });
        return await res.json();
    } catch (e) {
        console.error('Explanation fetch failed:', e);
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

function showError(elementId, msg = 'Error loading') {
    const el = document.getElementById(elementId);
    if (el) el.textContent = msg;
}

// ── Data Freshness ──────────────────────────────────────────
async function fetchWithFreshness(url, options = {}) {
    const start = Date.now();
    try {
        const res = await fetch(url, options);
        const data = await res.json();
        updateFreshnessBanner(start);
        return data;
    } catch (e) {
        updateFreshnessBanner(null);
        console.error('Fetch failed:', e);
        return null;
    }
}

function updateFreshnessBanner(startTime) {
    const banners = document.querySelectorAll('.freshness-banner');
    if (!banners.length) return;
    if (startTime === null) {
        banners.forEach(b => { b.textContent = '⚠ Connection error'; b.className = 'freshness-banner text-xs text-error font-medium'; });
        return;
    }
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const label = elapsed < 60 ? `${elapsed}s ago` : `${Math.floor(elapsed / 60)}m ago`;
    banners.forEach(b => { b.textContent = `Last updated: ${label}`; b.className = 'freshness-banner text-xs text-on-surface-variant font-medium'; });
}

// ── Skeleton Helpers ────────────────────────────────────────
function skeletonBox(height = 'h-6', width = 'w-full', count = 1) {
    return Array(count).fill(0).map(() =>
        `<div class="animate-pulse bg-surface-container-highest rounded ${height} ${width} mb-2"></div>`
    ).join('');
}

function skeletonCard() {
    return `
    <div class="animate-pulse bg-surface-container-lowest rounded-xl border border-outline-variant p-container-padding space-y-4">
        ${skeletonBox('h-4', 'w-1/3')}
        ${skeletonBox('h-8', 'w-2/3')}
        ${skeletonBox('h-4', 'w-1/2')}
    </div>`;
}

// ── Retry Helper ────────────────────────────────────────────
async function fetchWithRetry(url, options = {}, retries = 2) {
    for (let i = 0; i <= retries; i++) {
        const result = await fetchWithFreshness(url, options);
        if (result !== null) return result;
        if (i < retries) await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
    return null;
}