/**
 * Professional Trading Dashboard - JavaScript Controller
 * Institutional-grade interface logic
 */

const API_BASE_URL = 'http://localhost:5000/api';
let autoRefresh = true;
let refreshInterval = null;

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    initializeControls();
    initializeAutoRefresh();
    updateStatus();
});

// ==================== Control Button Handlers ====================
function initializeControls() {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');

    startBtn.addEventListener('click', () => sendCommand('start'));
    pauseBtn.addEventListener('click', () => sendCommand('pause'));
    stopBtn.addEventListener('click', () => sendCommand('stop'));
    
    autoRefreshToggle.addEventListener('click', toggleAutoRefresh);
}

async function sendCommand(action) {
    try {
        const response = await fetch(`${API_BASE_URL}/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            addLogEntry('SYSTEM', `Bot ${action}ed successfully`);
            updateStatus();
        } else {
            addLogEntry('ERROR', `Failed to ${action} bot: ${data.message}`);
        }
    } catch (error) {
        addLogEntry('ERROR', `Network error: ${error.message}`);
    }
}

// ==================== Status Update ====================
async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/status`);
        const data = await response.json();
        
        updateTopBar(data);
        updateRiskPanel(data);
        updateMarketStatus(data);
        updateCandidates(data);
        updatePositions(data);
        updateControlButtons(data);
        
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

function updateTopBar(data) {
    // Update time
    const now = new Date();
    document.getElementById('header-time').textContent = 
        now.toLocaleTimeString('en-IN', { hour12: false, timeZone: 'Asia/Kolkata' }) + ' IST';
    
    // Update market status chip
    const marketChip = document.getElementById('market-status-chip');
    if (data.market_state === 'OPEN') {
        marketChip.textContent = 'OPEN';
        marketChip.className = 'status-chip market-open';
    } else {
        marketChip.textContent = 'CLOSED';
        marketChip.className = 'status-chip market-closed';
    }
    
    // Update mode chip
    const modeChip = document.getElementById('mode-chip');
    if (data.mode === 'LIVE') {
        modeChip.textContent = 'LIVE';
        modeChip.className = 'status-chip mode-live';
    } else {
        modeChip.textContent = 'PAPER';
        modeChip.className = 'status-chip mode-paper';
    }
}

function updateRiskPanel(data) {
    // Total Capital
    document.getElementById('total-capital').textContent = 
        `₹${formatNumber(data.total_capital || 0)}`;
    
    // Used Margin
    document.getElementById('used-margin').textContent = 
        `₹${formatNumber(data.used_margin || 0)}`;
    
    // Today's P&L
    const pnl = data.today_pnl || 0;
    const pnlElement = document.getElementById('today-pnl');
    pnlElement.textContent = `₹${formatNumber(pnl, 2)}`;
    
    if (pnl > 0) {
        pnlElement.className = 'risk-value positive';
    } else if (pnl < 0) {
        pnlElement.className = 'risk-value negative';
    } else {
        pnlElement.className = 'risk-value neutral';
    }
    
    // P&L Bar
    const maxLoss = Math.abs(data.max_loss || 1000);
    const pnlPercentage = Math.min(100, Math.abs(pnl) / maxLoss * 100);
    const pnlBar = document.getElementById('pnl-bar-fill');
    pnlBar.style.width = `${pnlPercentage}%`;
    pnlBar.className = pnl < 0 ? 'pnl-bar-fill negative' : 'pnl-bar-fill';
    
    // Max Loss
    document.getElementById('max-loss-limit').textContent = 
        `₹${formatNumber(Math.abs(data.max_loss || 0))}`;
    
    // Mode Indicator
    const modeIndicator = document.getElementById('mode-indicator');
    if (data.mode === 'LIVE') {
        modeIndicator.textContent = 'LIVE TRADING';
        modeIndicator.className = 'mode-indicator live';
    } else {
        modeIndicator.textContent = 'PAPER TRADING';
        modeIndicator.className = 'mode-indicator paper';
    }
}

function updateMarketStatus(data) {
    // Market State
    const marketState = document.getElementById('market-state');
    marketState.textContent = data.market_state || 'CLOSED';
    marketState.className = data.market_state === 'OPEN' ? 
        'metric-value status-open' : 'metric-value status-closed';
    
    // Analysis Mode
    const analysisMode = document.getElementById('analysis-mode');
    if (data.market_state === 'OPEN') {
        analysisMode.textContent = 'Live Trading';
    } else {
        analysisMode.textContent = 'Reference Only';
    }
    
    // Universe Size
    const universeSize = data.market_analysis?.total_stocks || '--';
    document.getElementById('universe-size').textContent = `${universeSize} Stocks`;
    
    // Last Scan
    const lastScan = data.market_analysis?.last_analysis;
    if (lastScan) {
        document.getElementById('last-scan').textContent = 
            new Date(lastScan).toLocaleTimeString('en-IN', { hour12: false });
    } else {
        document.getElementById('last-scan').textContent = '--:--:--';
    }
    
    // Server Time
    if (data.server_time) {
        const serverTimeStr = data.server_time.server || '--:--:--';
        const timezone = data.server_time.timezone || '';
        document.getElementById('server-time').textContent = 
            `${serverTimeStr} ${timezone}`;
    } else {
        document.getElementById('server-time').textContent = '--:--:--';
    }
}

function updateCandidates(data) {
    const tbody = document.getElementById('candidates-body');
    const candidates = data.selected_stocks || [];
    
    if (candidates.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">No trade candidates selected</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = candidates.map(stock => {
        const bias = stock.bias === 'bullish' ? 'LONG' : 'SHORT';
        const biasClass = stock.bias === 'bullish' ? 'long' : 'short';
        const arrow = stock.bias === 'bullish' ? '↑' : '↓';
        const rr = stock.risk_reward ? stock.risk_reward.toFixed(1) : '--';
        
        return `
            <tr>
                <td data-label="STOCK"><span class="stock-symbol">${stock.symbol}</span></td>
                <td data-label="BIAS">
                    <span class="bias-indicator ${biasClass}">
                        ${arrow} ${bias}
                    </span>
                </td>
                <td data-label="ENTRY"><span class="price-value">₹${stock.entry || '--'}</span></td>
                <td data-label="TARGET"><span class="price-value">₹${stock.target || '--'}</span></td>
                <td data-label="STOP LOSS"><span class="price-value">₹${stock.stop_loss || '--'}</span></td>
                <td data-label="R:R"><span class="rr-ratio">${rr}</span></td>
                <td data-label="SCORE"><span class="score-badge">${stock.score || '--'}</span></td>
            </tr>
        `;
    }).join('');
}

function updatePositions(data) {
    const container = document.getElementById('positions-container');
    const positions = data.open_positions || [];
    
    if (positions.length === 0) {
        container.innerHTML = '<div class="empty-state">No active trades</div>';
        return;
    }
    
    container.innerHTML = positions.map(pos => `
        <div style="padding: 12px; background: var(--bg-elevated-2); border-radius: 8px; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span class="stock-symbol">${pos.symbol}</span>
                <span class="price-value ${pos.pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ₹${formatNumber(pos.pnl || 0, 2)}
                </span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary);">
                <span>Qty: ${pos.quantity}</span>
                <span>Entry: ₹${pos.entry_price}</span>
                <span>LTP: ₹${pos.ltp}</span>
            </div>
        </div>
    `).join('');
}

function updateControlButtons(data) {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    const status = data.status || 'stopped';
    
    if (status === 'running') {
        startBtn.disabled = true;
        pauseBtn.disabled = false;
        stopBtn.disabled = false;
    } else if (status === 'paused') {
        startBtn.disabled = false;
        pauseBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        startBtn.disabled = false;
        pauseBtn.disabled = true;
        stopBtn.disabled = true;
    }
}

// ==================== Activity Log ====================
function addLogEntry(tag, message) {
    const log = document.getElementById('activity-log');
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    const tagClass = tag.toLowerCase();
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <div class="log-time">${timeStr}</div>
        <div class="log-content">
            <span class="log-tag ${tagClass}">${tag}</span>
            <span class="log-message">${message}</span>
        </div>
    `;
    
    // Prepend new entries
    if (log.firstChild) {
        log.insertBefore(entry, log.firstChild);
    } else {
        log.appendChild(entry);
    }
    
    // Keep only last 50 entries
    while (log.children.length > 50) {
        log.removeChild(log.lastChild);
    }
}

// ==================== Auto Refresh ====================
function initializeAutoRefresh() {
    if (autoRefresh) {
        startAutoRefresh();
    }
}

function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    const toggle = document.getElementById('auto-refresh-toggle');
    
    if (autoRefresh) {
        toggle.classList.add('active');
        startAutoRefresh();
    } else {
        toggle.classList.remove('active');
        stopAutoRefresh();
    }
}

function startAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(updateStatus, 2000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// ==================== Utility Functions ====================
function formatNumber(num, decimals = 0) {
    if (typeof num !== 'number') return '0';
    return num.toLocaleString('en-IN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}
