/**
 * Trading Bot Dashboard - Frontend JavaScript
 */

// ==================== API Configuration ====================
const API_BASE = '/api';  // Same origin, relative path
let refreshInterval = null;

// ==================== Auth Helpers ====================

function getAuthToken() {
    return localStorage.getItem('auth_token');
}

function logout() {
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
}

// ==================== Utility Functions ====================

function formatCurrency(amount) {
    const sign = amount >= 0 ? '+' : '';
    return `${sign}₹${Math.abs(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPrice(price) {
    return `₹${parseFloat(price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(date) {
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function getCurrentTime() {
    return formatTime(new Date());
}

// ==================== API Calls ====================

async function fetchAPI(endpoint, options = {}) {
    const token = getAuthToken();
    
    // Build headers - include auth token if available (but don't require it)
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: headers
        });
        
        // Handle 401 Unauthorized - only redirect if we had a token (auth was expected)
        if (response.status === 401 && token) {
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
            return { success: false, error: 'Session expired' };
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        return { success: false, error: error.message };
    }
}

async function getStatus() {
    return fetchAPI('/status');
}

async function getAccount() {
    return fetchAPI('/account');
}

async function getSelectedStocks() {
    return fetchAPI('/stocks/selected');
}

async function getPositions() {
    return fetchAPI('/positions');
}

async function getTrades() {
    return fetchAPI('/trades/today');
}

async function getLogs() {
    return fetchAPI('/logs?limit=30');
}

async function getLogFile(lines = 200) {
    return fetchAPI(`/logs/file?lines=${lines}`);
}

async function getReports() {
    return fetchAPI('/reports');
}

async function getReportDetail(date) {
    return fetchAPI(`/reports/${date}`);
}

async function getConfig() {
    return fetchAPI('/config');
}

async function updateConfig(updates) {
    return fetchAPI('/config', {
        method: 'POST',
        body: JSON.stringify(updates)
    });
}

async function startBot() {
    return fetchAPI('/bot/start', { method: 'POST' });
}

async function pauseBot() {
    return fetchAPI('/bot/pause', { method: 'POST' });
}

async function resumeBot() {
    return fetchAPI('/bot/resume', { method: 'POST' });
}

async function stopBot() {
    return fetchAPI('/bot/stop', { method: 'POST' });
}

async function switchMode(mode) {
    return fetchAPI('/mode', {
        method: 'POST',
        body: JSON.stringify({ mode })
    });
}

// ==================== UI Update Functions ====================

function updateTime() {
    document.getElementById('current-time').textContent = getCurrentTime();
}

function updateStatusBadge(status) {
    const badge = document.getElementById('status-badge');
    badge.className = 'badge';
    
    switch (status.toUpperCase()) {
        case 'RUNNING':
            badge.className += ' status-running';
            badge.textContent = '🟢 RUNNING';
            break;
        case 'PAUSED':
            badge.className += ' status-paused';
            badge.textContent = '🟡 PAUSED';
            break;
        default:
            badge.className += ' status-stopped';
            badge.textContent = '⚪ STOPPED';
    }
}

function updateModeBadge(mode) {
    const badge = document.getElementById('mode-badge');
    badge.className = 'badge';
    
    if (mode === 'live') {
        badge.className += ' mode-live';
        badge.textContent = 'LIVE';
    } else {
        badge.className += ' mode-paper';
        badge.textContent = 'PAPER';
    }
}

function updateStartupMode(startupMode, currentMode) {
    const badge = document.getElementById('startup-mode-badge');
    if (!badge) return;
    
    badge.className = 'badge';
    
    // Prefer currentMode for real-time accuracy
    const mode = currentMode || startupMode;
    
    switch (mode) {
        case 'TRADING':
            badge.className += ' startup-mode-market';
            badge.textContent = '📈 TRADING';
            break;
        case 'READY_TO_TRADE':
            badge.className += ' startup-mode-market';
            badge.textContent = '🟢 READY';
            break;
        case 'WAITING_FOR_ANALYSIS':
            badge.className += ' startup-mode-pre';
            badge.textContent = '⏳ WAITING';
            break;
        case 'PRE_MARKET':
            badge.className += ' startup-mode-pre';
            badge.textContent = '🌅 PRE-MARKET';
            break;
        case 'MARKET_HOURS':
            badge.className += ' startup-mode-market';
            badge.textContent = '📈 MARKET HOURS';
            break;
        case 'MONITORING_ONLY':
            badge.className += ' startup-mode-market';
            badge.textContent = '👁️ MONITORING';
            break;
        case 'MARKET_CLOSING':
            badge.className += ' startup-mode-non';
            badge.textContent = '🔸 CLOSING';
            break;
        case 'ANALYSIS_COMPLETE':
            badge.className += ' startup-mode-non';
            badge.textContent = '📋 ANALYSIS DONE';
            break;
        case 'NON_MARKET':
            badge.className += ' startup-mode-non';
            badge.textContent = '🌙 NON-MARKET';
            break;
        default:
            badge.className += ' startup-mode-pre';
            badge.textContent = '⏳ WAITING';
    }
}

function updateMarketAnalysis(data) {
    const startupMode = data.startup_mode;
    const currentMode = data.current_mode;  // Dynamic real-time mode from backend
    const isActivelyTrading = data.is_actively_trading;
    const analysis = data.market_analysis || {};
    
    // Update startup mode in analysis section - now uses current_mode for accuracy
    const modeEl = document.getElementById('analysis-startup-mode');
    if (modeEl) {
        let modeText = 'Waiting...';
        // Prefer current_mode for real-time accuracy
        switch (currentMode) {
            case 'TRADING':
                modeText = '📈 Trading Active';
                break;
            case 'READY_TO_TRADE':
                modeText = '🟢 Ready to Trade (Market Hours)';
                break;
            case 'WAITING_FOR_ANALYSIS':
                modeText = '⏳ Waiting for Analysis';
                break;
            case 'MONITORING_ONLY':
                modeText = '👁️ Monitoring Only (No New Trades)';
                break;
            case 'MARKET_CLOSING':
                modeText = '🔸 Market Closing Soon';
                break;
            case 'ANALYSIS_COMPLETE':
                modeText = '📋 Analysis Complete (Non-Market)';
                break;
            case 'NON_MARKET':
                modeText = '🌙 Non-Market (Analysis Only)';
                break;
            default:
                // Fallback to startup_mode
                if (startupMode === 'PRE_MARKET') modeText = '🌅 Pre-Market (Normal Schedule)';
                else if (startupMode === 'MARKET_HOURS') modeText = '📈 Market Hours (Active Trading)';
                else if (startupMode === 'NON_MARKET') modeText = '🌙 Non-Market (Analysis Only)';
        }
        modeEl.textContent = modeText;
    }
    
    // Update analysis time
    const timeEl = document.getElementById('analysis-time');
    if (timeEl && analysis.analyzed_at) {
        const date = new Date(analysis.analyzed_at);
        timeEl.textContent = date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    
    // Update stocks analyzed
    const stocksEl = document.getElementById('stocks-analyzed');
    if (stocksEl) {
        stocksEl.textContent = analysis.total_stocks_analyzed || 0;
    }
    
    // Update server time display
    const serverTimeEl = document.getElementById('server-time');
    if (serverTimeEl && data.server_time) {
        const istTime = data.server_time.ist || '--';
        const serverTime = data.server_time.server || '--';
        const timezone = data.server_time.timezone || 'Local';
        const offset = data.server_time.offset || '';
        
        // Show actual server time (not IST)
        serverTimeEl.textContent = `🖥️ ${serverTime} ${timezone}`;
        serverTimeEl.title = `IST (Bot uses): ${istTime} | Server (${offset}): ${serverTime}`;
    }
    
    // Update trading status - use current_mode for real-time accuracy
    const statusEl = document.getElementById('trading-status');
    if (statusEl) {
        if (currentMode === 'TRADING' || isActivelyTrading) {
            statusEl.textContent = '✅ Trading Active';
            statusEl.style.color = 'var(--color-success)';
        } else if (currentMode === 'READY_TO_TRADE') {
            statusEl.textContent = '🟢 Ready to Trade';
            statusEl.style.color = 'var(--color-success)';
        } else if (currentMode === 'WAITING_FOR_ANALYSIS') {
            statusEl.textContent = '⏳ Waiting for Analysis';
            statusEl.style.color = 'var(--text-secondary)';
        } else if (currentMode === 'MONITORING_ONLY') {
            statusEl.textContent = '👁️ Monitoring Positions';
            statusEl.style.color = 'var(--color-info)';
        } else if (currentMode === 'MARKET_CLOSING' || currentMode === 'ANALYSIS_COMPLETE' || currentMode === 'NON_MARKET') {
            statusEl.textContent = '🔍 Analysis Only';
            statusEl.style.color = 'var(--color-warning)';
        } else {
            statusEl.textContent = '⏳ Initializing...';
            statusEl.style.color = 'var(--text-secondary)';
        }
    }
    
    // Update trading decision box
    const decisionEl = document.getElementById('trading-decision');
    const reasonEl = document.getElementById('trading-reason');
    if (decisionEl && reasonEl) {
        decisionEl.className = 'trading-decision';
        
        if (currentMode === 'TRADING' || isActivelyTrading) {
            decisionEl.className += ' suitable';
            reasonEl.textContent = '✅ ' + (analysis.reason || 'Trading in progress - WebSocket connected');
        } else if (currentMode === 'READY_TO_TRADE') {
            decisionEl.className += ' suitable';
            reasonEl.textContent = '✅ Ready to trade - Waiting for entry signals';
        } else if (analysis.trading_suitable) {
            decisionEl.className += ' suitable';
            reasonEl.textContent = '✅ ' + (analysis.reason || 'Trading conditions favorable');
        } else if (analysis.reason) {
            decisionEl.className += ' not-suitable';
            reasonEl.textContent = '⚠️ ' + analysis.reason;
        } else {
            reasonEl.textContent = 'Waiting for market analysis...';
        }
    }
}

function updateAccountInfo(data) {
    if (!data) return;
    
    document.getElementById('total-balance').textContent = formatPrice(data.total_balance || 0);
    document.getElementById('available-balance').textContent = formatPrice(data.available_balance || 0);
    document.getElementById('used-margin').textContent = formatPrice(data.used_margin || 0);
    
    const pnl = data.daily_pnl || 0;
    const pnlElement = document.getElementById('daily-pnl');
    pnlElement.textContent = formatCurrency(pnl);
    pnlElement.className = `value ${pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`;
    
    // Update progress bars
    const pnlPercent = Math.min(100, Math.abs((data.daily_pnl_percent || 0)));
    document.getElementById('pnl-progress').style.width = `${pnlPercent * 10}%`;
}

function updateStocksTable(stocks) {
    const tbody = document.getElementById('stocks-body');
    
    if (!stocks || stocks.length === 0) {
        tbody.innerHTML = '<tr class="no-data"><td colspan="6">No stocks selected yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = stocks.map(stock => {
        const statusClass = stock.status === 'WATCHING' ? 'status-watching' : 
                           stock.status === 'POSITION_OPEN' ? 'status-open' : 'status-completed';
        const statusIcon = stock.status === 'WATCHING' ? '🟢' : 
                          stock.status === 'POSITION_OPEN' ? '🟡' : '✅';
        
        return `
            <tr>
                <td><strong>${stock.symbol?.replace('-EQ', '') || 'N/A'}</strong></td>
                <td>${formatPrice(stock.ltp || stock.close || 0)}</td>
                <td>${formatPrice(stock.entry_price || 0)}</td>
                <td>${formatPrice(stock.target_price || stock.target || 0)}</td>
                <td>${formatPrice(stock.stop_loss || 0)}</td>
                <td class="${statusClass}">${statusIcon} ${stock.status || 'N/A'}</td>
            </tr>
        `;
    }).join('');
}

function updatePositions(data) {
    const container = document.getElementById('positions-container');
    const positions = data?.positions || [];
    
    if (positions.length === 0) {
        container.innerHTML = '<div class="no-data">No open positions</div>';
        return;
    }
    
    container.innerHTML = positions.map(pos => {
        const pnlClass = pos.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const progressPercent = Math.min(100, Math.max(0, 
            ((pos.current_price - pos.entry_price) / (pos.target - pos.entry_price)) * 100
        ));
        
        return `
            <div class="position-card">
                <div class="position-header">
                    <span class="position-symbol">${pos.symbol?.replace('-EQ', '')}</span>
                    <span class="position-pnl ${pnlClass}">${formatCurrency(pos.pnl)} (${pos.pnl_percent?.toFixed(2)}%)</span>
                </div>
                <div class="position-details">
                    <span>Entry: ${formatPrice(pos.entry_price)}</span>
                    <span>Current: ${formatPrice(pos.current_price)}</span>
                    <span>Target: ${formatPrice(pos.target)}</span>
                    <span>SL: ${formatPrice(pos.stop_loss)}</span>
                </div>
                <div class="position-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <div class="position-progress-text">${progressPercent.toFixed(0)}% to target</div>
                </div>
                <button class="btn btn-exit" onclick="exitPosition('${pos.symbol}')">🔴 EXIT NOW</button>
            </div>
        `;
    }).join('');
}

function updateTrades(data) {
    const tbody = document.getElementById('trades-body');
    const trades = data?.trades || [];
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr class="no-data"><td colspan="6">No trades yet</td></tr>';
    } else {
        tbody.innerHTML = trades.map((trade, index) => {
            const pnlClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
            const statusIcon = trade.exit_reason === 'TARGET' ? '✅' : 
                               trade.exit_reason === 'STOP_LOSS' ? '🛑' : 
                               trade.status === 'OPEN' ? '🟡' : '🔵';
            
            return `
                <tr>
                    <td>${index + 1}</td>
                    <td>${trade.symbol?.replace('-EQ', '') || 'N/A'}</td>
                    <td>${formatPrice(trade.entry_price || 0)}</td>
                    <td>${trade.exit_price ? formatPrice(trade.exit_price) : '---'}</td>
                    <td class="${pnlClass}">${formatCurrency(trade.pnl || 0)}</td>
                    <td>${statusIcon} ${trade.exit_reason || trade.status || 'OPEN'}</td>
                </tr>
            `;
        }).join('');
    }
    
    // Update summary
    const summary = data?.summary || {};
    document.getElementById('total-pnl').textContent = formatCurrency(summary.total_pnl || 0);
    document.getElementById('win-rate').textContent = `${(summary.win_rate || 0).toFixed(0)}%`;
}

function updateActivityLog(logs) {
    const container = document.getElementById('activity-log');
    
    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="log-entry system">
                <span class="log-time">${getCurrentTime()}</span>
                <span class="log-message">Waiting for activity...</span>
            </div>
        `;
        return;
    }
    
    container.innerHTML = logs.map(log => {
        const category = (log.category || 'SYSTEM').toLowerCase();
        return `
            <div class="log-entry ${category}">
                <span class="log-time">${log.time || '--:--:--'}</span>
                <span class="log-category">${log.category || 'SYSTEM'}</span>
                <span class="log-message">${log.message || ''}</span>
            </div>
        `;
    }).join('');
}

function updateButtonStates(status) {
    const btnStart = document.getElementById('btn-start');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    
    switch (status.toUpperCase()) {
        case 'RUNNING':
            btnStart.disabled = true;
            btnPause.disabled = false;
            btnStop.disabled = false;
            btnPause.textContent = '⏸️ PAUSE';
            break;
        case 'PAUSED':
            btnStart.disabled = true;
            btnPause.disabled = false;
            btnStop.disabled = false;
            btnPause.textContent = '▶️ RESUME';
            break;
        default:
            btnStart.disabled = false;
            btnPause.disabled = true;
            btnStop.disabled = true;
            btnPause.textContent = '⏸️ PAUSE';
    }
}

// ==================== Refresh Data ====================

let logRefreshInterval = null;

async function refreshAllData() {
    try {
        // Only refresh main dashboard data if that tab is active
        const activeTabEl = document.querySelector('.tab-btn.active');
        const activeTab = activeTabEl ? activeTabEl.dataset.tab : 'dashboard';
        
        if (activeTab === 'dashboard') {
            // Get status
            const statusResp = await getStatus();
            if (statusResp.success && statusResp.data) {
                updateStatusBadge(statusResp.data.status || 'STOPPED');
                updateModeBadge(statusResp.data.mode || 'paper');
                updateButtonStates(statusResp.data.status || 'STOPPED');
                updateStartupMode(statusResp.data.startup_mode, statusResp.data.current_mode);
                updateMarketAnalysis(statusResp.data);
            }
            
            // Get account info
            const accountResp = await getAccount();
            if (accountResp.success && accountResp.data) {
                updateAccountInfo(accountResp.data);
            }
            
            // Get selected stocks
            const stocksResp = await getSelectedStocks();
            if (stocksResp.success && stocksResp.data) {
                updateStocksTable(stocksResp.data.stocks || []);
            }
            
            // Get positions
            const positionsResp = await getPositions();
            if (positionsResp.success && positionsResp.data) {
                updatePositions(positionsResp.data);
            }
            
            // Get trades
            const tradesResp = await getTrades();
            if (tradesResp.success && tradesResp.data) {
                updateTrades(tradesResp.data);
            }
            
            // Get activity logs (mini log in dashboard)
            const logsResp = await getLogs();
            if (logsResp.success && logsResp.data) {
                updateActivityLog(logsResp.data.logs || []);
            }
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

async function refreshLogFile() {
    const select = document.getElementById('log-lines-select');
    const lines = select ? select.value : 200;
    const result = await getLogFile(lines);
    if (result.success && result.data) {
        const pre = document.getElementById('log-file-content');
        if (!pre) return;
        const logLines = result.data.lines || [];
        pre.textContent = logLines.join('\n');
        // Scroll to bottom
        pre.scrollTop = pre.scrollHeight;
    }
}

async function refreshReportsList() {
    const result = await getReports();
    if (result.success && result.data) {
        const container = document.getElementById('reports-list');
        if (!container) return;
        const reports = result.data.reports || [];
        
        if (reports.length === 0) {
            container.innerHTML = '<p class="no-data">No reports found.</p>';
            return;
        }
        
        container.innerHTML = reports.map(report => `
            <div class="report-item" onclick="loadReportDetail('${report.date}')" data-date="${report.date}">
                <div class="report-item-header">
                    <span class="report-item-date">${report.date}</span>
                    <span class="report-item-pnl ${report.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${formatCurrency(report.pnl)}</span>
                </div>
                <div class="report-item-stats">Trades: ${report.trades}</div>
            </div>
        `).join('');
    }
}

async function loadReportDetail(date) {
    // UI selection
    document.querySelectorAll('.report-item').forEach(item => {
        item.classList.toggle('active', item.dataset.date === date);
    });
    
    const detailContainer = document.getElementById('report-detail');
    if (!detailContainer) return;
    
    detailContainer.innerHTML = '<p class="loading">Loading report details...</p>';
    
    const result = await getReportDetail(date);
    if (result.success && result.data) {
        const report = result.data;
        const stats = report.stats || {};
        const pnl = stats.pnl || 0;
        
        detailContainer.innerHTML = `
            <div class="report-summary-grid">
                <div class="report-stat-box">
                    <span class="report-stat-label">Total P&L</span>
                    <span class="report-stat-value ${pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${formatCurrency(pnl)}</span>
                </div>
                <div class="report-stat-box">
                    <span class="report-stat-label">Trades</span>
                    <span class="report-stat-value">${stats.trades || 0}</span>
                </div>
                <div class="report-stat-box">
                    <span class="report-stat-label">Wins/Losses</span>
                    <span class="report-stat-value">${stats.wins || 0}W / ${stats.losses || 0}L</span>
                </div>
            </div>
            
            <h3>Trades</h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>P&L</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(report.trades || []).map(trade => `
                            <tr>
                                <td>${trade.symbol?.replace('-EQ', '')}</td>
                                <td>${formatPrice(trade.entry_price)}</td>
                                <td>${formatPrice(trade.exit_price)}</td>
                                <td class="${trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${formatCurrency(trade.pnl)}</td>
                                <td style="font-size: 0.7rem">${trade.exit_reason || 'N/A'}</td>
                            </tr>
                        `).join('') || '<tr><td colspan="5" class="no-data">No trades recorded</td></tr>'}
                    </tbody>
                </table>
            </div>
            <div style="margin-top: var(--spacing-lg); color: var(--text-muted); font-size: 0.8rem;">
                Final Balance: ${formatPrice(report.final_balance || 0)}
            </div>
        `;
    }
}

// ==================== Tab Switching ====================

function switchTab(tabId) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    
    // Update content visibility
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('hidden', content.id !== `tab-${tabId}`);
    });
    
    // Special handling for tabs
    if (tabId === 'logs') {
        refreshLogFile();
        startLogAutoRefresh();
    } else {
        stopLogAutoRefresh();
    }
    
    if (tabId === 'reports') {
        refreshReportsList();
    }
}

function startLogAutoRefresh() {
    stopLogAutoRefresh(); // Clear existing
    const autoRefresh = document.getElementById('log-auto-refresh');
    if (autoRefresh && autoRefresh.checked) {
        logRefreshInterval = setInterval(refreshLogFile, 5000);
    }
}

function stopLogAutoRefresh() {
    if (logRefreshInterval) {
        clearInterval(logRefreshInterval);
        logRefreshInterval = null;
    }
}

// ==================== Event Handlers ====================

async function handleStart() {
    const result = await startBot();
    if (result.success) {
        addLogEntry('SYSTEM', 'Bot started');
        refreshAllData();
    } else {
        alert(`Failed to start: ${result.error}`);
    }
}

async function handlePause() {
    const btn = document.getElementById('btn-pause');
    
    if (btn.textContent.includes('RESUME')) {
        const result = await resumeBot();
        if (result.success) {
            addLogEntry('SYSTEM', 'Trading resumed');
            refreshAllData();
        }
    } else {
        const result = await pauseBot();
        if (result.success) {
            addLogEntry('SYSTEM', 'Trading paused');
            refreshAllData();
        }
    }
}

async function handleStop() {
    if (!confirm('Are you sure you want to stop the bot? All positions will be squared off.')) {
        return;
    }
    
    const result = await stopBot();
    if (result.success) {
        addLogEntry('SYSTEM', `Bot stopped. Final P&L: ${formatCurrency(result.data?.final_pnl || 0)}`);
        refreshAllData();
    } else {
        alert(`Failed to stop: ${result.error}`);
    }
}

async function handleSaveConfig() {
    const updates = {
        'strategy.stop_loss_percent': parseFloat(document.getElementById('stop-loss').value),
        'strategy.target_percent': parseFloat(document.getElementById('target').value),
        'strategy.max_trades_per_day': parseInt(document.getElementById('max-trades').value)
    };
    
    const result = await updateConfig(updates);
    if (result.success) {
        addLogEntry('CONFIG', 'Configuration saved');
        alert('Configuration saved successfully!');
    } else {
        alert(`Failed to save: ${result.error}`);
    }
}

async function handleModeToggle(mode) {
    if (mode === 'live') {
        if (!confirm('⚠️ WARNING: Switching to LIVE mode will use REAL MONEY. Are you sure?')) {
            return;
        }
    }
    
    const result = await switchMode(mode);
    if (result.success) {
        updateModeBadge(mode);
        document.getElementById('mode-paper').classList.toggle('active', mode === 'paper');
        document.getElementById('mode-live').classList.toggle('active', mode === 'live');
        addLogEntry('SYSTEM', `Switched to ${mode.toUpperCase()} mode`);
    }
}

async function exitPosition(symbol) {
    if (!confirm(`Exit position for ${symbol}?`)) {
        return;
    }
    
    const result = await fetchAPI('/position/exit', {
        method: 'POST',
        body: JSON.stringify({ symbol })
    });
    
    if (result.success) {
        addLogEntry('TRADE', `Exit requested for ${symbol}`);
        refreshAllData();
    }
}

function addLogEntry(category, message) {
    const container = document.getElementById('activity-log');
    if (!container) return;
    const entry = document.createElement('div');
    entry.className = `log-entry ${category.toLowerCase()}`;
    entry.innerHTML = `
        <span class="log-time">${getCurrentTime()}</span>
        <span class="log-category">${category}</span>
        <span class="log-message">${message}</span>
    `;
    container.insertBefore(entry, container.firstChild);
}

function openSettingsModal() {
    document.getElementById('settings-modal').classList.remove('hidden');
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

// ==================== Initialization ====================

function initEventListeners() {
    // Control buttons
    document.getElementById('btn-start').addEventListener('click', handleStart);
    document.getElementById('btn-pause').addEventListener('click', handlePause);
    document.getElementById('btn-stop').addEventListener('click', handleStop);
    document.getElementById('btn-refresh').addEventListener('click', refreshAllData);

    
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Log controls
    document.getElementById('btn-refresh-logs')?.addEventListener('click', refreshLogFile);
    document.getElementById('log-auto-refresh')?.addEventListener('change', (e) => {
        if (e.target.checked) startLogAutoRefresh();
        else stopLogAutoRefresh();
    });
    
    // Config
    document.getElementById('save-config')?.addEventListener('click', handleSaveConfig);
    document.getElementById('mode-paper')?.addEventListener('click', () => handleModeToggle('paper'));
    document.getElementById('mode-live')?.addEventListener('click', () => handleModeToggle('live'));
    
    // Modal
    document.querySelector('.modal-close')?.addEventListener('click', closeSettingsModal);
    document.getElementById('settings-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'settings-modal') closeSettingsModal();
    });
}

async function loadInitialConfig() {
    const result = await getConfig();
    if (result.success && result.data) {
        const sl = document.getElementById('stop-loss');
        if (sl) sl.value = result.data.strategy?.stop_loss_percent || 0.5;
        
        const tgt = document.getElementById('target');
        if (tgt) tgt.value = result.data.strategy?.target_percent || 1.0;
        
        const maxT = document.getElementById('max-trades');
        if (maxT) maxT.value = result.data.strategy?.max_trades_per_day || 3;
        
        const mode = result.data.trading_mode || 'paper';
        const paperBtn = document.getElementById('mode-paper');
        const liveBtn = document.getElementById('mode-live');
        if (paperBtn) paperBtn.classList.toggle('active', mode === 'paper');
        if (liveBtn) liveBtn.classList.toggle('active', mode === 'live');
    }
}

function init() {
    // Update time every second
    updateTime();
    setInterval(updateTime, 1000);
    
    // Initialize event listeners
    initEventListeners();
    
    // Load initial config
    loadInitialConfig();
    
    // Initial data load
    refreshAllData();
    
    // Auto-refresh every 5 seconds
    refreshInterval = setInterval(refreshAllData, 5000);
    
    console.log('📊 Trading Bot Dashboard initialized');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
