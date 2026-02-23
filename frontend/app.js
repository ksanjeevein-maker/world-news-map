/**
 * World News Map â€” Dashboard App v2
 * Full-page tab navigation + Interactive Leaflet map
 */

const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 30_000;

// â”€â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
let state = {
    news: [],
    signals: [],
    conflicts: [],
    conflictsEnabled: false,
    cryptoTickers: [],
    forexTickers: [],
    fearGreed: null,
    stats: null,
    newsFilter: null,
    signalFilter: null,
    mapSeverityFilter: 'all',
    mapShowAcled: true,
    mapShowNews: true,
    connected: false,
    lastUpdate: null,
    activeTab: 'news',
};

let map = null;
let mapMarkers = null;

// â”€â”€â”€ GEO DATABASE â€” Maps keywords in titles to coordinates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const GEO_DB = {
    // Countries â†’ [lat, lng]
    'ukraine': [48.38, 31.17], 'russia': [55.75, 37.62], 'china': [39.90, 116.40],
    'taiwan': [25.03, 121.57], 'iran': [35.69, 51.39], 'israel': [31.77, 35.23],
    'palestine': [31.95, 35.20], 'gaza': [31.50, 34.47], 'lebanon': [33.89, 35.50],
    'syria': [33.51, 36.29], 'iraq': [33.31, 44.37], 'yemen': [15.37, 44.19],
    'afghanistan': [34.53, 69.17], 'pakistan': [33.69, 73.04], 'india': [28.61, 77.21],
    'north korea': [39.02, 125.75], 'south korea': [37.57, 126.98],
    'japan': [35.68, 139.69], 'myanmar': [16.87, 96.20], 'thailand': [13.76, 100.50],
    'philippines': [14.60, 120.98], 'vietnam': [21.03, 105.85],
    'united states': [38.91, -77.04], 'u.s.': [38.91, -77.04], ' us ': [38.91, -77.04],
    'washington': [38.91, -77.04], 'pentagon': [38.87, -77.06],
    'canada': [45.42, -75.70], 'mexico': [19.43, -99.13], 'brazil': [-15.79, -47.88],
    'colombia': [4.71, -74.07], 'venezuela': [10.49, -66.88], 'argentina': [-34.60, -58.38],
    'united kingdom': [51.51, -0.13], 'uk': [51.51, -0.13], 'london': [51.51, -0.13],
    'france': [48.86, 2.35], 'paris': [48.86, 2.35],
    'germany': [52.52, 13.41], 'berlin': [52.52, 13.41],
    'italy': [41.90, 12.50], 'spain': [40.42, -3.70],
    'poland': [52.23, 21.01], 'turkey': [39.93, 32.86], 'ankara': [39.93, 32.86],
    'egypt': [30.04, 31.24], 'cairo': [30.04, 31.24],
    'saudi arabia': [24.71, 46.68], 'riyadh': [24.71, 46.68],
    'uae': [24.45, 54.65], 'dubai': [25.20, 55.27],
    'nigeria': [9.08, 7.49], 'south africa': [-33.93, 18.42],
    'ethiopia': [9.02, 38.75], 'sudan': [15.59, 32.53], 'somalia': [2.05, 45.32],
    'libya': [32.90, 13.18], 'tunisia': [36.81, 10.17], 'morocco': [33.97, -6.85],
    'kenya': [-1.29, 36.82], 'congo': [-4.32, 15.31],
    'australia': [-33.87, 151.21], 'new zealand': [-41.29, 174.78],
    'nato': [50.88, 4.42], 'brussels': [50.85, 4.35],
    'beijing': [39.90, 116.40], 'moscow': [55.75, 37.62], 'kyiv': [50.45, 30.52],
    'taipei': [25.03, 121.57], 'tehran': [35.69, 51.39], 'jerusalem': [31.77, 35.23],
    'kabul': [34.53, 69.17], 'islamabad': [33.69, 73.04], 'new delhi': [28.61, 77.21],
    'tokyo': [35.68, 139.69], 'seoul': [37.57, 126.98], 'pyongyang': [39.02, 125.75],
    'crimea': [45.30, 34.10], 'donbas': [48.00, 37.80], 'kherson': [46.64, 32.62],
    'houthi': [15.37, 44.19], 'hezbollah': [33.89, 35.50], 'hamas': [31.50, 34.47],
    'red sea': [20.0, 38.0], 'persian gulf': [26.0, 52.0], 'south china sea': [12.0, 114.0],
    'strait of hormuz': [26.60, 56.25], 'black sea': [43.0, 34.0],
    'arctic': [71.0, 25.0], 'baltic': [57.0, 20.0],
    'opec': [26.0, 50.0], 'suez': [30.0, 32.58],
};

function geoLocateItem(item) {
    const text = (item.title + ' ' + (item.summary || '')).toLowerCase();
    for (const [keyword, coords] of Object.entries(GEO_DB)) {
        if (text.includes(keyword)) {
            // Add small random offset to prevent exact overlap
            return [
                coords[0] + (Math.random() - 0.5) * 1.5,
                coords[1] + (Math.random() - 0.5) * 1.5,
            ];
        }
    }
    return null;
}

// â”€â”€â”€ API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function apiFetch(endpoint) {
    try {
        const resp = await fetch(`${API_BASE}${endpoint}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        state.connected = true;
        return await resp.json();
    } catch (err) {
        console.error(`API error [${endpoint}]:`, err);
        state.connected = false;
        return null;
    }
}

async function fetchAllData() {
    const [news, signals, crypto, forex, conflicts, stats] = await Promise.all([
        apiFetch('/api/news/latest?limit=300'),
        apiFetch('/api/signals?limit=200'),
        apiFetch('/api/market/crypto'),
        apiFetch('/api/market/forex'),
        apiFetch('/api/conflicts?limit=500'),
        apiFetch('/api/stats'),
    ]);

    if (news) state.news = news;
    if (signals) state.signals = signals;
    if (crypto) {
        state.cryptoTickers = crypto.tickers || [];
        state.fearGreed = crypto.fear_greed;
    }
    if (forex) state.forexTickers = forex;
    if (conflicts) {
        state.conflicts = conflicts.events || [];
        state.conflictsEnabled = conflicts.enabled || false;
    }
    if (stats) state.stats = stats;
    state.lastUpdate = new Date();

    renderAll();
}

// â”€â”€â”€ Time Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function timeAgo(dateStr) {
    if (!dateStr) return '';
    const now = Date.now();
    const ts = typeof dateStr === 'number' ? dateStr * 1000 : new Date(dateStr).getTime();
    const diff = Math.max(0, now - ts);
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

function formatPrice(price) {
    if (price == null) return 'â€”';
    if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(2);
    if (price >= 0.01) return price.toFixed(4);
    return price.toFixed(6);
}

function formatChange(pct) {
    if (pct == null) return '';
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + 'â€¦' : str;
}

function openLink(url) {
    if (url) window.open(url, '_blank', 'noopener');
}

// â”€â”€â”€ Tab Switching â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function switchTab(tabId) {
    state.activeTab = tabId;

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    document.querySelectorAll('.tab-page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${tabId}`);
    });

    // Initialize map on first switch to map tab
    if (tabId === 'map' && !map) {
        initMap();
    }
    if (tabId === 'map' && map) {
        setTimeout(() => map.invalidateSize(), 100);
        updateMapMarkers();
    }
}

// â”€â”€â”€ Filters â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function setNewsFilter(category) {
    state.newsFilter = category || null;
    document.querySelectorAll('#page-news .filter-tab').forEach(tab => {
        tab.classList.toggle('active', (tab.dataset.category || null) === state.newsFilter);
    });
    renderNews();
}

function setSignalFilter(impact) {
    state.signalFilter = impact || null;
    document.querySelectorAll('#page-signals .filter-tab').forEach(tab => {
        tab.classList.toggle('active', (tab.dataset.impact || null) === state.signalFilter);
    });
    renderSignals();
}

function setMapFilter(severity) {
    state.mapSeverityFilter = severity;
    document.querySelectorAll('#map-filters [data-mapfilter]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mapfilter === severity);
    });
    updateMapMarkers();
}

function toggleMapSource(source) {
    if (source === 'acled') state.mapShowAcled = !state.mapShowAcled;
    if (source === 'news') state.mapShowNews = !state.mapShowNews;
    document.querySelectorAll('#map-filters [data-mapsource]').forEach(btn => {
        if (btn.dataset.mapsource === 'acled') btn.classList.toggle('active', state.mapShowAcled);
        if (btn.dataset.mapsource === 'news') btn.classList.toggle('active', state.mapShowNews);
    });
    updateMapMarkers();
}

function toggleFullscreenMap() {
    const page = document.getElementById('page-map');
    const btn = document.getElementById('btn-fullscreen');
    const isFullscreen = page.classList.toggle('is-fullscreen');

    if (isFullscreen) {
        btn.textContent = '✖ Exit Fullscreen';
        btn.classList.add('active');
    } else {
        btn.textContent = '⛶ Fullscreen';
        btn.classList.remove('active');
    }

    if (map) {
        // Give the DOM a tiny slice of time to reflow before telling Leaflet
        setTimeout(() => map.invalidateSize(), 50);
    }
}
// â”€â”€â”€ Render Functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function renderAll() {
    renderStatus();
    renderSignalTicker();
    renderNews();
    renderSignals();
    renderCrypto();
    renderForex();
    updateClock();
    updateBadges();
    if (state.activeTab === 'map' && map) {
        updateMapMarkers();
    }
}

function updateBadges() {
    document.getElementById('news-count').textContent = state.news.length;
    document.getElementById('signals-count').textContent = state.signals.length;
    document.getElementById('crypto-count').textContent = state.cryptoTickers.length;
    document.getElementById('forex-count').textContent = state.forexTickers.length;
    // ACLED status
    const acledEl = document.getElementById('acled-status');
    if (acledEl) {
        if (state.conflictsEnabled) {
            acledEl.textContent = `ACLED: ${state.conflicts.length} events`;
            acledEl.style.color = 'var(--accent-green)';
        } else {
            acledEl.textContent = 'ACLED: set API key to enable';
            acledEl.style.color = 'var(--text-muted)';
        }
    }
}

function renderStatus() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (state.connected) {
        dot.className = 'status-dot';
        text.textContent = `${state.stats?.feeds?.total_items || 0} items Â· ${state.stats?.signals?.total_signals || 0} signals`;
    } else {
        dot.className = 'status-dot error';
        text.textContent = 'Disconnected';
    }
}

function renderSignalTicker() {
    const track = document.getElementById('ticker-track');
    if (!state.signals.length) {
        track.innerHTML = '<span class="ticker-item" style="color: var(--text-muted)">Waiting for signals...</span>';
        return;
    }
    const items = state.signals.slice(0, 25);
    track.innerHTML = [...items, ...items].map(s => {
        const type = s.type.replace(/_/g, ' ');
        return `<span class="ticker-item" onclick="openLink('${s.link}')" title="${escapeHtml(s.title)}">
            <span class="severity-dot severity-${s.impact}"></span>
            <strong>${type}</strong> ${escapeHtml(truncate(s.title, 70))}
        </span>`;
    }).join('');
}

function renderNews() {
    const container = document.getElementById('news-list');
    let items = state.news;
    if (state.newsFilter) items = items.filter(n => n.category === state.newsFilter);

    if (!items.length) {
        container.innerHTML = `<div class="empty-state"><span class="icon">ðŸ“¡</span>${state.newsFilter ? 'No ' + state.newsFilter + ' news right now' : 'Loading news feeds...'}</div>`;
        return;
    }

    container.innerHTML = items.slice(0, 150).map(item => {
        const severityClass = item.severity !== 'normal' ? `severity-${item.severity}` : '';
        const biasTag = item.bias_tag !== 'neutral'
            ? `<span class="bias-tag ${item.bias_tag}">${item.bias_tag}</span>` : '';
        const summary = item.summary ? `<div class="news-item-summary">${escapeHtml(truncate(item.summary, 200))}</div>` : '';

        return `<div class="news-item ${severityClass}" onclick="openLink('${item.link}')">
            <div class="news-item-title">${escapeHtml(item.title)}</div>
            ${summary}
            <div class="news-item-meta">
                <span class="news-source">${item.source}</span>
                <span class="news-time">${timeAgo(item.published)}</span>
                <span style="color:var(--text-muted)">${item.category}</span>
                ${biasTag}
            </div>
        </div>`;
    }).join('');
}

function renderSignals() {
    const container = document.getElementById('signals-list');
    let items = state.signals;
    if (state.signalFilter) items = items.filter(s => s.impact === state.signalFilter);

    if (!items.length) {
        container.innerHTML = '<div class="empty-state"><span class="icon">âš¡</span>No active signals</div>';
        return;
    }

    container.innerHTML = items.slice(0, 100).map(s => {
        const type = s.type.replace(/_/g, ' ');
        const affects = s.affects.map(a => `<span class="affect-tag">${a}</span>`).join('');

        return `<div class="signal-item impact-${s.impact}" onclick="openLink('${s.link}')">
            <div class="signal-type-badge ${s.impact}">${type} Â· ${s.impact}</div>
            <div class="signal-title">${escapeHtml(s.title)}</div>
            <div class="news-item-meta">
                <span class="news-source">${s.source}</span>
                <span class="news-time">${timeAgo(s.timestamp)}</span>
            </div>
            <div class="signal-affects">${affects}</div>
        </div>`;
    }).join('');
}

function renderCrypto() {
    const fgContainer = document.getElementById('fear-greed');
    if (state.fearGreed) {
        const fg = state.fearGreed;
        let color = '#f59e0b';
        if (fg.value <= 25) color = '#ef4444';
        else if (fg.value <= 40) color = '#f97316';
        else if (fg.value >= 75) color = '#10b981';
        else if (fg.value >= 60) color = '#84cc16';

        fgContainer.innerHTML = `
            <span class="fear-greed-label">Fear & Greed Index</span>
            <div class="fear-greed-track">
                <div class="fear-greed-needle" style="left: calc(${fg.value}% - 9px)"></div>
            </div>
            <span class="fear-greed-value" style="color: ${color}">${fg.value} â€” ${fg.label}</span>
        `;
        fgContainer.style.display = 'flex';
    } else {
        fgContainer.style.display = 'none';
    }

    const container = document.getElementById('crypto-grid');
    if (!state.cryptoTickers.length) {
        container.innerHTML = '<div class="empty-state"><span class="icon">â‚¿</span>Loading crypto data...</div>';
        return;
    }

    container.innerHTML = state.cryptoTickers.map(t => {
        const changeClass = (t.change_pct_24h || 0) >= 0 ? 'positive' : 'negative';
        return `<div class="market-ticker">
            <div class="market-ticker-symbol">${t.symbol}</div>
            <div class="market-ticker-name">${t.name}</div>
            <div class="market-ticker-price">$${formatPrice(t.price)}</div>
            <div class="market-ticker-change ${changeClass}">${formatChange(t.change_pct_24h)}</div>
        </div>`;
    }).join('');
}

function renderForex() {
    const container = document.getElementById('forex-grid');
    if (!state.forexTickers.length) {
        container.innerHTML = '<div class="empty-state"><span class="icon">ðŸ’±</span>Loading forex data...</div>';
        return;
    }

    container.innerHTML = state.forexTickers.map(t => {
        return `<div class="market-ticker">
            <div class="market-ticker-symbol">${t.symbol}</div>
            <div class="market-ticker-name">${t.name}</div>
            <div class="market-ticker-price">${formatPrice(t.price)}</div>
        </div>`;
    }).join('');
}

// â”€â”€â”€ Interactive Map (Leaflet) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function initMap() {
    map = L.map('map-container', {
        center: [25, 30],
        zoom: 3,
        minZoom: 2,
        maxZoom: 10,
        zoomControl: true,
        attributionControl: false,
    });

    // Dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 19,
    }).addTo(map);

    // Attribution
    L.control.attribution({ position: 'bottomright' })
        .addAttribution('&copy; <a href="https://carto.com/">CARTO</a>')
        .addTo(map);

    mapMarkers = L.layerGroup().addTo(map);
    updateMapMarkers();
}

function getMarkerColor(item) {
    if (item.severity === 'breaking') return '#ef4444';
    if (item.severity === 'elevated') return '#f97316';
    if (item.category === 'military' || item.category === 'cyber') return '#f59e0b';
    return '#3b82f6';
}

function getMarkerRadius(item) {
    if (item.severity === 'breaking') return 10;
    if (item.severity === 'elevated') return 8;
    return 6;
}

function updateMapMarkers() {
    if (!mapMarkers) return;
    mapMarkers.clearLayers();

    const sevFilter = state.mapSeverityFilter;

    function newsToSeverity(item) {
        if (item.severity === 'breaking') return 'critical';
        if (item.severity === 'elevated') return 'high';
        if (item.category === 'military' || item.category === 'cyber') return 'high';
        return 'medium';
    }

    function passesSeverityFilter(sev) {
        if (sevFilter === 'all') return true;
        return sev === sevFilter;
    }

    // â”€â”€ 1. ACLED conflict events (EXACT coordinates) â”€â”€
    if (state.mapShowAcled) {
        for (const evt of state.conflicts) {
            if (!evt.latitude || !evt.longitude) continue;
            if (!passesSeverityFilter(evt.severity)) continue;

            let color = '#ef4444';
            let radius = 8;
            if (evt.severity === 'high') { color = '#f97316'; radius = 7; }
            if (evt.severity === 'medium') { color = '#f59e0b'; radius = 5; }

            if (evt.fatalities >= 10) radius = 12;
            else if (evt.fatalities >= 5) radius = 10;

            const marker = L.circleMarker([evt.latitude, evt.longitude], {
                radius,
                fillColor: color,
                color: '#fff',
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.65,
            });

            const fatText = evt.fatalities > 0 ? `<br><strong style="color:#ef4444">\u2620 ${evt.fatalities} fatalities</strong>` : '';
            const popup = `
                <div class="popup-title">${escapeHtml(evt.event_type)}: ${escapeHtml(evt.location)}</div>
                <div class="popup-source">${evt.country} \u00b7 ${evt.event_date} \u00b7 ACLED</div>
                <div class="popup-summary">
                    <strong>${escapeHtml(evt.actor1)}</strong>${evt.actor2 ? ' vs ' + escapeHtml(evt.actor2) : ''}
                    ${fatText}
                </div>
                ${evt.notes ? `<div class="popup-summary" style="margin-top:4px">${escapeHtml(truncate(evt.notes, 200))}</div>` : ''}
            `;

            marker.bindPopup(popup, { maxWidth: 380 });
            mapMarkers.addLayer(marker);
        }
    }

    // â”€â”€ 2. News signals + elevated news (keyword-guessed coordinates) â”€â”€
    if (state.mapShowNews) {
        const mapItems = [];

        for (const sig of state.signals.slice(0, 50)) {
            const coords = geoLocateItem(sig);
            if (coords) {
                const sev = sig.impact === 'critical' ? 'critical' : sig.impact;
                if (!passesSeverityFilter(sev)) continue;
                mapItems.push({
                    coords,
                    title: sig.title,
                    source: sig.source,
                    summary: '',
                    link: sig.link,
                    severity: sig.impact === 'critical' ? 'breaking' : sig.impact,
                    category: sig.type,
                });
            }
        }

        for (const item of state.news) {
            if (item.severity === 'normal' && item.category !== 'military' && item.category !== 'geopolitical') continue;
            const sev = newsToSeverity(item);
            if (!passesSeverityFilter(sev)) continue;
            const coords = geoLocateItem(item);
            if (coords) {
                mapItems.push({
                    coords,
                    title: item.title,
                    source: item.source,
                    summary: item.summary || '',
                    link: item.link,
                    severity: item.severity,
                    category: item.category,
                });
            }
        }

        const seen = new Set();
        for (const item of mapItems) {
            const key = item.title.slice(0, 50).toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);

            const color = getMarkerColor(item);
            const radius = getMarkerRadius(item);

            const marker = L.circleMarker(item.coords, {
                radius,
                fillColor: color,
                color: color,
                weight: 2,
                opacity: 0.9,
                fillOpacity: 0.4,
            });

            const popup = `
                <div class="popup-title">${escapeHtml(item.title)}</div>
                <div class="popup-source">${item.source} \u00b7 ${item.category}</div>
                ${item.summary ? `<div class="popup-summary">${escapeHtml(truncate(item.summary, 150))}</div>` : ''}
                ${item.link ? `<a href="${item.link}" target="_blank" class="popup-link">Read full article \u2192</a>` : ''}
            `;

            marker.bindPopup(popup, { maxWidth: 350 });
            mapMarkers.addLayer(marker);
        }
    }
}

// â”€â”€â”€ Clock â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function updateClock() {
    const el = document.getElementById('header-time');
    const now = new Date();
    const offset = -now.getTimezoneOffset() / 60;
    const sign = offset >= 0 ? '+' : '';
    el.textContent = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        + ` UTC${sign}${offset}`;
}

// â”€â”€â”€ Init â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
document.addEventListener('DOMContentLoaded', () => {
    fetchAllData();
    setInterval(fetchAllData, REFRESH_INTERVAL);
    setInterval(updateClock, 1000);
});
