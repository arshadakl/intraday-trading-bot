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

        // Handle 401 Unauthorized
        if (response.status === 401) {
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
            return { success: false, error: 'Session expired' };
        }
        
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            return {
                success: response.ok,
                error: response.ok ? null : `HTTP ${response.status}`
            };
        }
        
        const text = await response.text();
        if (!text) {
            return {
                success: response.ok,
                error: response.ok ? null : `HTTP ${response.status} (empty response)`
            };
        }
        
        return JSON.parse(text);
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

async function getStockHistory(symbol) {
    return fetchAPI(`/stocks/${symbol}/history`);
}

// ==================== Stock Chart Management ====================

// Store chart instances and their data
const stockCharts = {};
const stockPriceHistory = {};

async function initializeStockCharts(stocks) {
    if (!stocks || stocks.length === 0) return;
    
    const container = document.getElementById('stock-charts-container');
    if (!container) return;
    
    // Clear container if no stocks
    if (stocks.length === 0) {
        container.innerHTML = '<div class="text-center py-8 text-text-muted">Select stocks to view charts</div>';
        return;
    }
    
    // Initialize charts for each stock
    for (const stock of stocks) {
        const symbol = stock.symbol;
        
        // Skip if chart already exists
        if (stockCharts[symbol]) continue;
        
        // Create chart container
        const chartWrapper = document.createElement('div');
        chartWrapper.className = 'stock-chart-wrapper';
        chartWrapper.id = `chart-wrapper-${symbol}`;
        
        const cleanSymbol = symbol.replace('-EQ', '');
        chartWrapper.innerHTML = `
            <div class="stock-chart-header">
                <span class="stock-chart-symbol">${cleanSymbol}</span>
                <div class="stock-chart-legend">
                    <span><span style="display:inline-block;width:10px;height:3px;background:#22c55e;margin-right:4px;"></span>Entry: ₹${stock.entry_price || 0}</span>
                    <span><span style="display:inline-block;width:10px;height:3px;background:#3b82f6;margin-right:4px;"></span>Target: ₹${stock.target_price || stock.target || 0}</span>
                    <span><span style="display:inline-block;width:10px;height:3px;background:#ef4444;margin-right:4px;"></span>SL: ₹${stock.stop_loss || 0}</span>
                </div>
            </div>
            <div id="chart-${symbol}" class="stock-chart-container"></div>
        `;
        
        container.appendChild(chartWrapper);
        
        // Initialize lightweight chart
        const chart = LightweightCharts.createChart(
            document.getElementById(`chart-${symbol}`),
            {
                layout: {
                    background: { color: 'transparent' },
                    textColor: '#a1a1a6',
                },
                grid: {
                    vertLines: { color: 'rgba(56, 56, 58, 0.3)' },
                    horzLines: { color: 'rgba(56, 56, 58, 0.3)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                    vertLine: {
                        color: '#0a84ff',
                        width: 1,
                        style: LightweightCharts.LineStyle.Dashed,
                    },
                    horzLine: {
                        color: '#0a84ff',
                        width: 1,
                        style: LightweightCharts.LineStyle.Dashed,
                    },
                },
                rightPriceScale: {
                    borderColor: '#38383a',
                },
                timeScale: {
                    borderColor: '#38383a',
                    timeVisible: true,
                    secondsVisible: false,
                },
                handleScroll: {
                    vertTouchDrag: false,
                },
            }
        );
        
        // Add candlestick series for price
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderUpColor: '#22c55e',
            borderDownColor: '#ef4444',
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });
        
        // Add horizontal lines for Entry, Target, SL
        const entryLine = chart.addLineSeries({
            color: '#22c55e',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Solid,
            lastValueVisible: true,
            title: 'Entry',
        });
        
        const targetLine = chart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
            title: 'Target',
        });
        
        const slLine = chart.addLineSeries({
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
            title: 'SL',
        });
        
        // Store chart instance
        stockCharts[symbol] = {
            chart,
            candleSeries,
            entryLine,
            targetLine,
            slLine,
            wrapper: chartWrapper,
            entryPrice: stock.entry_price,
            targetPrice: stock.target_price || stock.target,
            stopLoss: stock.stop_loss,
        };
        
        // Fetch historical data
        await fetchAndDisplayHistoricalData(symbol);
    }
    
    // Remove charts for stocks that are no longer selected
    Object.keys(stockCharts).forEach(symbol => {
        if (!stocks.find(s => s.symbol === symbol)) {
            removeStockChart(symbol);
        }
    });
}

async function fetchAndDisplayHistoricalData(symbol) {
    try {
        const response = await getStockHistory(symbol);
        if (!response.success || !response.data) return;
        
        const data = response.data;
        const chartData = stockCharts[symbol];
        if (!chartData) return;
        
        // Set candles
        if (data.candles && data.candles.length > 0) {
            chartData.candleSeries.setData(data.candles);
            stockPriceHistory[symbol] = data.candles;
        }
        
        // Set horizontal lines
        const timeRange = data.candles && data.candles.length > 0 
            ? { start: data.candles[0].time, end: data.candles[data.candles.length - 1].time }
            : { start: Math.floor(Date.now() / 1000) - 3600, end: Math.floor(Date.now() / 1000) };
        
        if (data.entry_price) {
            chartData.entryLine.setData([
                { time: timeRange.start, value: data.entry_price },
                { time: timeRange.end + 3600, value: data.entry_price }
            ]);
        }
        
        if (data.target_price) {
            chartData.targetLine.setData([
                { time: timeRange.start, value: data.target_price },
                { time: timeRange.end + 3600, value: data.target_price }
            ]);
        }
        
        if (data.stop_loss) {
            chartData.slLine.setData([
                { time: timeRange.start, value: data.stop_loss },
                { time: timeRange.end + 3600, value: data.stop_loss }
            ]);
        }
        
        // Fit content
        chartData.chart.timeScale().fitContent();
        
    } catch (error) {
        console.error(`Error fetching historical data for ${symbol}:`, error);
    }
}

function updateStockChartRealtime(symbol, priceData) {
    const chartData = stockCharts[symbol];
    if (!chartData) return;
    
    // Create a candle from the price data
    const time = Math.floor(Date.now() / 1000);
    const price = priceData.ltp || priceData.close || priceData;
    
    // If we have historical data, update the last candle or add new one
    if (stockPriceHistory[symbol] && stockPriceHistory[symbol].length > 0) {
        const lastCandle = stockPriceHistory[symbol][stockPriceHistory[symbol].length - 1];
        const lastCandleTime = lastCandle.time;
        
        // If same minute, update last candle
        if (Math.floor(time / 60) === Math.floor(lastCandleTime / 60)) {
            lastCandle.close = price;
            if (price > lastCandle.high) lastCandle.high = price;
            if (price < lastCandle.low) lastCandle.low = price;
            chartData.candleSeries.update(lastCandle);
        } else {
            // Add new candle
            const newCandle = {
                time: time,
                open: price,
                high: price,
                low: price,
                close: price
            };
            stockPriceHistory[symbol].push(newCandle);
            chartData.candleSeries.update(newCandle);
        }
    } else {
        // No history, create new candle
        const newCandle = {
            time: time,
            open: price,
            high: price,
            low: price,
            close: price
        };
        chartData.candleSeries.update(newCandle);
    }
}

function removeStockChart(symbol) {
    const chartData = stockCharts[symbol];
    if (!chartData) return;
    
    // Remove chart
    chartData.chart.remove();
    
    // Remove wrapper element
    if (chartData.wrapper && chartData.wrapper.parentNode) {
        chartData.wrapper.parentNode.removeChild(chartData.wrapper);
    }
    
    // Clean up
    delete stockCharts[symbol];
    delete stockPriceHistory[symbol];
}

// ==================== Chart Data Management ====================
// NOTE: We do NOT poll for historical data to avoid API rate limits (AB1004)
// Instead, we:
// 1. Fetch historical data ONCE when charts are created
// 2. Build real-time candles from price updates every 1 minute (not 5 seconds)

let lastChartUpdateTime = 0;
const CHART_UPDATE_INTERVAL = 60000; // 1 minute in milliseconds

function updateChartsFromRealtimeData(stocks) {
    // Only update charts every 1 minute to avoid rate limits
    const now = Date.now();
    if (now - lastChartUpdateTime < CHART_UPDATE_INTERVAL) {
        return; // Skip update, not enough time passed
    }
    
    lastChartUpdateTime = now;
    console.log('📈 Updating charts (1-minute interval)...');
    
    // Update charts with real-time price data from the main dashboard refresh
    // This avoids making additional API calls for historical data
    stocks.forEach(stock => {
        if (stock.ltp && stockCharts[stock.symbol]) {
            updateStockChartRealtime(stock.symbol, { ltp: stock.ltp });
        }
    });
}

// ==================== Strategy API Functions ====================

async function getStrategies() {
    return fetchAPI('/strategies');
}

async function getActiveStrategy() {
    return fetchAPI('/strategy/active');
}

async function switchStrategy(strategyName, force = false) {
    return fetchAPI('/strategy/switch', {
        method: 'POST',
        body: JSON.stringify({ strategy: strategyName, force })
    });
}

async function getStrategyParams(strategyName) {
    return fetchAPI(`/strategy/${strategyName}/params`);
}

async function updateStrategyParams(strategyName, params) {
    return fetchAPI(`/strategy/${strategyName}/params`, {
        method: 'POST',
        body: JSON.stringify(params)
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
        case 'STOPPED':
            badge.className += ' startup-mode-non';
            badge.textContent = '⏹️ STOPPED';
            break;
        case 'INITIALIZING':
            badge.className += ' startup-mode-pre';
            badge.textContent = '⏳ INITIALIZING';
            break;
        case 'PAUSED':
            badge.className += ' startup-mode-pre';
            badge.textContent = '⏸️ PAUSED';
            break;
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
            badge.textContent = '⏳ ANALYZING';
            break;
        case 'PRE_MARKET':
            badge.className += ' startup-mode-pre';
            badge.textContent = '🌅 PRE-MARKET';
            break;
        case 'PRE_MARKET_READY':
            badge.className += ' startup-mode-pre';
            badge.textContent = '🌅 PRE-MARKET READY';
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
            case 'STOPPED':
                modeText = '⏹️ Bot Stopped';
                break;
            case 'INITIALIZING':
                modeText = '⏳ Initializing...';
                break;
            case 'PAUSED':
                modeText = '⏸️ Paused';
                break;
            case 'TRADING':
                modeText = '📈 Trading Active';
                break;
            case 'READY_TO_TRADE':
                modeText = '🟢 Ready to Trade (Market Hours)';
                break;
            case 'WAITING_FOR_ANALYSIS':
                modeText = '⏳ Waiting for Analysis';
                break;
            case 'PRE_MARKET':
                modeText = '🌅 Pre-Market (Analyzing...)';
                break;
            case 'PRE_MARKET_READY':
                modeText = '🌅 Pre-Market (Stocks Ready)';
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
        // Also clear charts
        const chartContainer = document.getElementById('stock-charts-container');
        if (chartContainer) {
            chartContainer.innerHTML = '<div class="text-center py-8 text-text-muted">Select stocks to view charts</div>';
        }
        // Clean up chart instances
        Object.keys(stockCharts).forEach(symbol => removeStockChart(symbol));
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
    
    // Initialize or update charts for selected stocks
    initializeStockCharts(stocks);
    
    // Update real-time data for existing charts (from main data refresh, no extra API calls)
    updateChartsFromRealtimeData(stocks);
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

                // Update strategy info from status
                if (statusResp.data.strategy) {
                    updateStrategyFromStatus(statusResp.data.strategy);
                }
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

        // Nifty50 data is now handled by separate polling mechanism in startNifty50Polling()
        // to avoid conflicts with the 5-second dashboard refresh
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

async function refreshLogFile() {
    const select = document.getElementById('log-lines-select');
    const lines = select ? select.value : 200;
    const pre = document.getElementById('log-file-content');
    if (!pre) return;

    const result = await getLogFile(lines);
    if (result.success && result.data) {
        const logLines = result.data.lines || [];
        if (logLines.length === 0) {
            pre.textContent = 'No log entries found.';
        } else {
            pre.textContent = logLines.join('\n');
            // Scroll to bottom
            pre.scrollTop = pre.scrollHeight;
        }
    } else {
        // Show error message
        pre.textContent = `Error loading logs: ${result.error || 'Bot may not be running. Start the bot to view logs.'}`;
    }
}

async function refreshReportsList() {
    const container = document.getElementById('reports-list');
    if (!container) return;

    const result = await getReports();
    if (result.success && result.data) {
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
    } else {
        // Show error message
        container.innerHTML = `<p class="no-data error">Error loading reports: ${result.error || 'Bot may not be running.'}</p>`;
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

    if (tabId === 'nifty50') {
        // Start Nifty50 polling when tab is active
        startNifty50Polling();
    } else {
        // Stop Nifty50 polling when switching away from the tab
        stopNifty50Polling();
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
    const usePercentage = document.getElementById('capital-percent-fields')?.classList.contains('hidden') === false;

    const updates = {
        'strategy.stop_loss_percent': parseFloat(document.getElementById('stop-loss').value),
        'strategy.target_percent': parseFloat(document.getElementById('target').value),
        'strategy.max_trades_per_day': parseInt(document.getElementById('max-trades').value),
        'capital.use_percentage': usePercentage,
        'capital.trading_percentage': parseInt(document.getElementById('trading-capital-percent').value),
        'capital.per_trade_percentage': parseInt(document.getElementById('per-trade-percent').value)
    };

    // Only include fixed amount if not using percentage
    if (!usePercentage) {
        const fixedAmount = document.getElementById('trading-capital-fixed').value;
        if (fixedAmount) {
            updates['capital.fixed_amount'] = parseFloat(fixedAmount);
        }
    } else {
        updates['capital.fixed_amount'] = null;
    }

    const result = await updateConfig(updates);
    if (result.success) {
        addLogEntry('CONFIG', 'Configuration saved including capital settings');
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

function handleCapitalModeToggle(mode) {
    const percentBtn = document.getElementById('capital-mode-percent');
    const fixedBtn = document.getElementById('capital-mode-fixed');
    const percentFields = document.getElementById('capital-percent-fields');
    const fixedFields = document.getElementById('capital-fixed-fields');

    if (mode === 'percent') {
        percentBtn.classList.remove('btn-secondary');
        percentBtn.classList.add('btn-primary');
        fixedBtn.classList.remove('btn-primary');
        fixedBtn.classList.add('btn-secondary');
        percentFields.classList.remove('hidden');
        fixedFields.classList.add('hidden');
    } else {
        fixedBtn.classList.remove('btn-secondary');
        fixedBtn.classList.add('btn-primary');
        percentBtn.classList.remove('btn-primary');
        percentBtn.classList.add('btn-secondary');
        fixedFields.classList.remove('hidden');
        percentFields.classList.add('hidden');
    }
}

// ==================== Strategy Handlers ====================

async function loadStrategies() {
    const result = await getStrategies();
    if (result.success && result.data) {
        const select = document.getElementById('strategy-select');
        const strategies = result.data.strategies || [];
        const active = result.data.active;
        const canSwitch = result.data.can_switch;

        // Clear and rebuild options
        select.innerHTML = '';
        strategies.forEach(s => {
            const option = document.createElement('option');
            option.value = s.name;
            option.textContent = s.display_name || s.name;
            if (s.name === active || s.is_active) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        // Update active strategy display
        const activeStrategy = strategies.find(s => s.name === active || s.is_active);
        if (activeStrategy) {
            document.getElementById('active-strategy-name').textContent = activeStrategy.display_name || activeStrategy.name;
            document.getElementById('strategy-description').textContent = activeStrategy.description || '';
        }

        // Update switch button state
        updateStrategySwitchButton(canSwitch, select.value, active);
    }
}

function handleStrategySelectChange(e) {
    const selectedValue = e.target.value;
    const activeStrategyName = document.getElementById('active-strategy-name').textContent;

    // Get current active strategy name from data attribute or infer
    const strategies = Array.from(document.getElementById('strategy-select').options);
    const currentActive = strategies.find(opt => opt.textContent === activeStrategyName)?.value;

    // Enable switch button if selection is different from active
    const switchBtn = document.getElementById('btn-switch-strategy');
    const isActive = selectedValue === currentActive;

    // Get can_switch state from last status update (stored globally)
    const canSwitch = window._canSwitchStrategy !== false;

    switchBtn.disabled = isActive || !canSwitch;
}

function updateStrategySwitchButton(canSwitch, selected, active) {
    const switchBtn = document.getElementById('btn-switch-strategy');
    const warning = document.getElementById('strategy-warning');

    // Note: canSwitch state is checked fresh from API before switching
    // to avoid stale state issues between status polls

    if (!canSwitch) {
        switchBtn.disabled = true;
        warning.classList.remove('hidden');
    } else {
        warning.classList.add('hidden');
        switchBtn.disabled = selected === active;
    }
}

// Flag to prevent concurrent strategy switch requests
let _switchingStrategy = false;

async function handleSwitchStrategy() {
    // Prevent concurrent switch requests (race condition protection)
    if (_switchingStrategy) {
        return;
    }
    _switchingStrategy = true;

    const select = document.getElementById('strategy-select');
    const strategyName = select.value;
    const strategyDisplayName = select.options[select.selectedIndex]?.textContent || strategyName;

    const switchBtn = document.getElementById('btn-switch-strategy');
    switchBtn.disabled = true;
    switchBtn.textContent = '⏳ Checking...';

    try {
        // Fetch fresh status to check if switching is allowed (avoid stale state)
        const freshStatus = await getStrategies();
        if (freshStatus.success && freshStatus.data && !freshStatus.data.can_switch) {
            alert('Cannot switch strategy while positions are open. Please close all positions first.');
            switchBtn.textContent = '🔄 Switch';
            switchBtn.disabled = false;
            return;
        }

        if (!confirm(`Switch to "${strategyDisplayName}" strategy?`)) {
            switchBtn.textContent = '🔄 Switch';
            switchBtn.disabled = false;
            return;
        }

        switchBtn.textContent = '⏳ Switching...';

        const result = await switchStrategy(strategyName);

        if (result.success) {
            addLogEntry('STRATEGY', `Switched to ${strategyDisplayName}`);

            // Update UI
            document.getElementById('active-strategy-name').textContent = strategyDisplayName;

            // Get description from option or fetch
            const strategies = await getStrategies();
            if (strategies.success && strategies.data) {
                const newActive = strategies.data.strategies.find(s => s.name === strategyName);
                if (newActive) {
                    document.getElementById('strategy-description').textContent = newActive.description || '';
                }
            }

            switchBtn.textContent = '✅ Switched!';
            setTimeout(() => {
                switchBtn.textContent = '🔄 Switch';
                switchBtn.disabled = true; // Already on selected strategy
            }, 2000);
        } else {
            alert(`Failed to switch strategy: ${result.error || result.message}`);
            switchBtn.textContent = '🔄 Switch';
            switchBtn.disabled = false;
        }
    } catch (error) {
        alert(`Error switching strategy: ${error.message}`);
        switchBtn.textContent = '🔄 Switch';
        switchBtn.disabled = false;
    } finally {
        // Always reset the flag to allow future switch attempts
        _switchingStrategy = false;
    }
}

function updateStrategyFromStatus(strategyInfo) {
    if (!strategyInfo) return;

    const nameEl = document.getElementById('active-strategy-name');
    const select = document.getElementById('strategy-select');

    if (nameEl && strategyInfo.display_name) {
        nameEl.textContent = strategyInfo.display_name;
    }

    if (select && strategyInfo.active) {
        select.value = strategyInfo.active;
    }

    // Update switch button based on can_switch
    updateStrategySwitchButton(
        strategyInfo.can_switch !== false,
        select?.value,
        strategyInfo.active
    );
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

    // Capital Config
    document.getElementById('capital-mode-percent')?.addEventListener('click', () => handleCapitalModeToggle('percent'));
    document.getElementById('capital-mode-fixed')?.addEventListener('click', () => handleCapitalModeToggle('fixed'));

    // Strategy
    document.getElementById('btn-switch-strategy')?.addEventListener('click', handleSwitchStrategy);
    document.getElementById('strategy-select')?.addEventListener('change', handleStrategySelectChange);

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

        // Load capital configuration
        const capitalConfig = result.data.capital || {};
        const usePercentage = capitalConfig.use_percentage !== false; // default true

        // Set capital mode toggle
        handleCapitalModeToggle(usePercentage ? 'percent' : 'fixed');

        // Set capital values
        const tradingPercent = document.getElementById('trading-capital-percent');
        if (tradingPercent) tradingPercent.value = capitalConfig.trading_percentage || 50;

        const tradingFixed = document.getElementById('trading-capital-fixed');
        if (tradingFixed) tradingFixed.value = capitalConfig.fixed_amount || '';

        const perTradePercent = document.getElementById('per-trade-percent');
        if (perTradePercent) perTradePercent.value = capitalConfig.per_trade_percentage || 25;
    }

    // Load available strategies
    await loadStrategies();
}

// ==================== Nifty 50 Data ====================

async function getNifty50Data() {
    return fetchAPI('/nifty50/preopen');
}

async function getWatchlistData() {
    return fetchAPI('/nifty50/watchlist');
}

async function getNifty50GapStatus() {
    return fetchAPI('/nifty50/gap-status');
}

let niftyGapChart = null;

async function refreshNiftyGapStatus() {
    try {
        const result = await getNifty50GapStatus();
        
        if (!result.success || !result.data) {
            console.log('Nifty gap status not available yet');
            return;
        }
        
        const data = result.data;
        const gapStatus = data.gap_status;
        const gapPercent = data.gap_percent;
        const gapPoints = data.gap_points;
        
        // Update gap badge
        const badge = document.getElementById('nifty-gap-badge');
        if (badge) {
            let badgeClass = 'bg-bg-elevated text-text-secondary';
            let badgeText = 'FLAT';
            let badgeIcon = '➡️';
            
            if (gapStatus === 'GAP_UP') {
                badgeClass = 'bg-success/20 text-success border border-success/30';
                badgeText = `GAP UP +${gapPercent}%`;
                badgeIcon = '🟢';
            } else if (gapStatus === 'GAP_DOWN') {
                badgeClass = 'bg-danger/20 text-danger border border-danger/30';
                badgeText = `GAP DOWN ${gapPercent}%`;
                badgeIcon = '🔴';
            } else {
                badgeClass = 'bg-warning/20 text-warning border border-warning/30';
                badgeText = 'FLAT OPEN';
                badgeIcon = '⚪';
            }
            
            badge.className = `px-4 py-2 rounded-lg font-bold text-lg ${badgeClass}`;
            badge.innerHTML = `${badgeIcon} ${badgeText}`;
        }
        
        // Update price values
        const prevCloseEl = document.getElementById('nifty-prev-close');
        if (prevCloseEl) prevCloseEl.textContent = data.prev_close ? `₹${data.prev_close.toLocaleString('en-IN')}` : '-';
        
        const openPriceEl = document.getElementById('nifty-open-price');
        if (openPriceEl) openPriceEl.textContent = data.open_price ? `₹${data.open_price.toLocaleString('en-IN')}` : '-';
        
        const gapPercentEl = document.getElementById('nifty-gap-percent');
        if (gapPercentEl) {
            const sign = gapPercent >= 0 ? '+' : '';
            const colorClass = gapPercent > 0 ? 'text-success' : gapPercent < 0 ? 'text-danger' : 'text-text-secondary';
            gapPercentEl.innerHTML = `<span class="${colorClass}">${sign}${gapPercent}%</span>`;
        }
        
        const currentPriceEl = document.getElementById('nifty-current-price');
        if (currentPriceEl) {
            const currentChange = data.current_change_percent;
            const sign = currentChange >= 0 ? '+' : '';
            const colorClass = currentChange > 0 ? 'text-success' : currentChange < 0 ? 'text-danger' : 'text-text-secondary';
            currentPriceEl.innerHTML = `<span class="${colorClass}">₹${data.current_price?.toLocaleString('en-IN') || '-'} (${sign}${currentChange}%)</span>`;
        }
        
        // Update trading direction indicator
        const directionSection = document.getElementById('nifty-trading-direction');
        const directionIcon = document.getElementById('nifty-direction-icon');
        const directionTitle = document.getElementById('nifty-direction-title');
        const directionDesc = document.getElementById('nifty-direction-desc');
        
        if (directionSection && directionTitle && directionDesc) {
            directionSection.classList.remove('hidden');
            
            if (gapStatus === 'GAP_UP') {
                directionIcon.textContent = '🔴';
                directionTitle.textContent = 'Strategy: SHORT (Mean Reversion)';
                directionDesc.textContent = `Nifty gapped up ${gapPercent}%. Strategy will SHORT strongest stocks expecting gap fade.`;
                directionSection.className = 'mt-4 p-3 rounded-lg bg-danger/10 border border-danger/20';
            } else if (gapStatus === 'GAP_DOWN') {
                directionIcon.textContent = '🟢';
                directionTitle.textContent = 'Strategy: LONG (Mean Reversion)';
                directionDesc.textContent = `Nifty gapped down ${gapPercent}%. Strategy will LONG weakest stocks expecting gap fill.`;
                directionSection.className = 'mt-4 p-3 rounded-lg bg-success/10 border border-success/20';
            } else {
                directionIcon.textContent = '⚪';
                directionTitle.textContent = 'Strategy: BOTH DIRECTIONS';
                directionDesc.textContent = 'Nifty opened flat. Strategy will trade both gap-up and gap-down stocks.';
                directionSection.className = 'mt-4 p-3 rounded-lg bg-warning/10 border border-warning/20';
            }
        }
        
        // Update chart (now async)
        await updateNiftyGapChart(data);
        
    } catch (error) {
        console.error('Error refreshing Nifty gap status:', error);
    }
}

async function fetchNiftyChartData(interval = 'FIVE_MINUTE') {
    // Fetch Nifty 50 historical chart data from API
    try {
        const response = await fetchAPI(`/nifty50/chart?interval=${interval}&days=1`);
        return response;
    } catch (error) {
        console.error('Error fetching Nifty chart data:', error);
        return null;
    }
}

async function updateNiftyGapChart(gapStatusData) {
    const chartContainer = document.getElementById('nifty-gap-chart');
    const loadingEl = document.getElementById('nifty-chart-loading');
    
    if (!chartContainer) return;
    
    // Fetch actual historical chart data
    const chartData = await fetchNiftyChartData('FIVE_MINUTE');
    
    // Hide loading
    if (loadingEl) loadingEl.style.display = 'none';
    
    // Destroy existing chart if any
    if (niftyGapChart) {
        niftyGapChart.remove();
        niftyGapChart = null;
    }
    
    // Create new chart with better configuration
    niftyGapChart = LightweightCharts.createChart(chartContainer, {
        layout: {
            background: { color: 'transparent' },
            textColor: '#a1a1a6',
        },
        grid: {
            vertLines: { color: 'rgba(56, 56, 58, 0.3)' },
            horzLines: { color: 'rgba(56, 56, 58, 0.3)' },
        },
        rightPriceScale: {
            borderColor: '#38383a',
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        timeScale: {
            visible: true,
            borderColor: '#38383a',
            timeVisible: true,
            secondsVisible: false,
        },
        handleScroll: true,
        handleScale: true,
    });
    
    // Add candlestick series for actual price data
    const candleSeries = niftyGapChart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
    });
    
    // Set candle data if available
    if (chartData && chartData.success && chartData.data && chartData.data.candles && chartData.data.candles.length > 0) {
        candleSeries.setData(chartData.data.candles);
    }
    
    // Add reference lines for gap analysis
    if (gapStatusData && gapStatusData.prev_close) {
        const prevCloseLine = niftyGapChart.addLineSeries({
            color: '#22c55e',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
            title: 'Prev Close',
        });
        
        // Create horizontal line for previous close
        const prevCloseData = [];
        const candles = chartData?.data?.candles || [];
        if (candles.length > 0) {
            const firstTime = candles[0].time;
            const lastTime = candles[candles.length - 1].time;
            prevCloseData.push(
                { time: firstTime, value: gapStatusData.prev_close },
                { time: lastTime, value: gapStatusData.prev_close }
            );
        } else {
            // Fallback: create a simple line if no candle data
            const baseTime = Math.floor(Date.now() / 1000);
            prevCloseData.push(
                { time: baseTime - 3600, value: gapStatusData.prev_close },
                { time: baseTime, value: gapStatusData.prev_close }
            );
        }
        prevCloseLine.setData(prevCloseData);
    }
    
    if (gapStatusData && gapStatusData.open_price) {
        const openLine = niftyGapChart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: true,
            title: 'Open',
        });
        
        // Create horizontal line for open price
        const openData = [];
        const candles = chartData?.data?.candles || [];
        if (candles.length > 0) {
            const firstTime = candles[0].time;
            const lastTime = candles[candles.length - 1].time;
            openData.push(
                { time: firstTime, value: gapStatusData.open_price },
                { time: lastTime, value: gapStatusData.open_price }
            );
        } else {
            const baseTime = Math.floor(Date.now() / 1000);
            openData.push(
                { time: baseTime - 3600, value: gapStatusData.open_price },
                { time: baseTime, value: gapStatusData.open_price }
            );
        }
        openLine.setData(openData);
    }
    
    // Fit content to show all data
    niftyGapChart.timeScale().fitContent();
}

let currentNiftyInterval = 'FIVE_MINUTE';

async function changeNiftyInterval(interval) {
    // Change Nifty chart interval and reload data
    currentNiftyInterval = interval;
    
    // Update button styles
    document.querySelectorAll('.nifty-interval-btn').forEach(btn => {
        btn.classList.remove('bg-accent', 'text-white');
        btn.classList.add('text-text-secondary');
    });
    const activeBtn = document.querySelector(`.nifty-interval-btn[data-interval="${interval}"]`);
    if (activeBtn) {
        activeBtn.classList.add('bg-accent', 'text-white');
        activeBtn.classList.remove('text-text-secondary');
    }
    
    // Show loading
    const loadingEl = document.getElementById('nifty-chart-loading');
    if (loadingEl) loadingEl.style.display = 'flex';
    
    // Fetch new chart data
    const chartData = await fetchNiftyChartData(interval);
    const gapStatusData = await getNifty50GapStatus();
    
    // Update chart with new data
    if (gapStatusData && gapStatusData.success && gapStatusData.data) {
        await updateNiftyGapChart(gapStatusData.data);
    }
}

async function refreshWatchlistData() {
    const bullishBody = document.getElementById('watchlist-bullish-body');
    const bearishBody = document.getElementById('watchlist-bearish-body');
    const statusDiv = document.getElementById('watchlist-status');

    if (!bullishBody || !bearishBody) return;

    // Set loading state
    const loadingRow = '<tr><td colspan="3" class="px-3 py-4 text-center text-text-muted">Loading...</td></tr>';
    bullishBody.innerHTML = loadingRow;
    bearishBody.innerHTML = loadingRow;

    try {
        const result = await getWatchlistData();

        if (result.success && result.data) {
            const data = result.data.data || result.data; // Handle wrapped or direct data

            // Only update if we have stocks data
            const stocks = data.stocks || {};
            const bullishStocks = stocks.bullish || [];
            const bearishStocks = stocks.bearish || [];

            // Update Status
            if (statusDiv) {
                const trend = data.nifty_trend || 'WAITING';
                const activeSet = data.active_set || 'BOTH';
                // Clean up reason text if it's too long or has newlines
                const reason = (data.filter_reason || 'Waiting for market open...').split('\n')[0];

                let statusColor = 'text-text-secondary';
                if (trend === 'BULLISH') statusColor = 'text-success';
                if (trend === 'BEARISH') statusColor = 'text-danger';

                statusDiv.innerHTML = `
                    <span class="font-bold ${statusColor}">TREND: ${trend}</span> | 
                    Active: <span class="font-medium">${activeSet}</span> | 
                    <span class="text-text-muted text-xs">${reason}</span>
                `;
            }

            // Render Bullish Stocks
            if (bullishStocks.length > 0) {
                bullishBody.innerHTML = bullishStocks.map(stock => {
                    const price = stock.last_price || stock.iep || stock.ltp || 0;
                    const changeClass = (stock.gap_percent || 0) > 0 ? 'text-success' : 'text-danger';
                    return `
                        <tr class="border-b border-border-subtle hover:bg-bg-elevated/50">
                            <td class="px-3 py-2 font-medium">${(stock.symbol || 'N/A').replace('-EQ', '')}</td>
                            <td class="px-3 py-2 text-right ${changeClass} font-mono">${(stock.gap_percent || 0).toFixed(2)}%</td>
                            <td class="px-3 py-2 text-right font-mono">₹${parseFloat(price).toLocaleString('en-IN')}</td>
                        </tr>
                    `;
                }).join('');
            } else {
                bullishBody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-text-muted">No bullish candidates</td></tr>';
            }

            // Render Bearish Stocks
            if (bearishStocks.length > 0) {
                bearishBody.innerHTML = bearishStocks.map(stock => {
                    const price = stock.last_price || stock.iep || stock.ltp || 0;
                    const changeClass = (stock.gap_percent || 0) > 0 ? 'text-success' : 'text-danger';
                    return `
                        <tr class="border-b border-border-subtle hover:bg-bg-elevated/50">
                            <td class="px-3 py-2 font-medium">${(stock.symbol || 'N/A').replace('-EQ', '')}</td>
                            <td class="px-3 py-2 text-right ${changeClass} font-mono">${(stock.gap_percent || 0).toFixed(2)}%</td>
                            <td class="px-3 py-2 text-right font-mono">₹${parseFloat(price).toLocaleString('en-IN')}</td>
                        </tr>
                    `;
                }).join('');
            } else {
                bearishBody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-text-muted">No bearish candidates</td></tr>';
            }

        } else {
            // Check if it's just that the file doesn't exist yet (first run)
            if (statusDiv) statusDiv.innerHTML = '<span class="text-warning">Watchlist not yet generated (waiting for 9:10 AM update)</span>';
            bullishBody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-text-muted">No data available yet</td></tr>';
            bearishBody.innerHTML = '<tr><td colspan="3" class="px-3 py-4 text-center text-text-muted">No data available yet</td></tr>';
        }
    } catch (error) {
        console.error('Error fetching watchlist:', error);
        if (bullishBody) bullishBody.innerHTML = '<tr><td colspan="3" class="text-center py-2 text-danger">Error loading data</td></tr>';
        if (bearishBody) bearishBody.innerHTML = '<tr><td colspan="3" class="text-center py-2 text-danger">Error loading data</td></tr>';
    }
}

async function refreshNifty50Data(isInitialLoad = false) {
    try {
        // Refresh Watchlist (parallel)
        refreshWatchlistData();

        const cardGrid = document.getElementById('nifty50-card-grid');

        if (!cardGrid) return;

        // Only show loading state on initial load, not on refresh
        if (isInitialLoad) {
            cardGrid.innerHTML = '<div class="text-center py-8 text-text-muted col-span-full">Loading Nifty 50 data...</div>';
        }

        const result = await getNifty50Data();

        if (result.success && result.data) {
            const stocks = result.data.stocks || [];
            const metadata = result.data.metadata || {};

            // Update metadata
            const totalEl = document.getElementById('nifty50-total');
            if (totalEl) totalEl.textContent = metadata.total_stocks || stocks.length;

            const updatedEl = document.getElementById('nifty50-updated');
            if (updatedEl) updatedEl.textContent = metadata.last_updated || 'Unknown';

            const sourceEl = document.getElementById('nifty50-source');
            if (sourceEl) sourceEl.textContent = metadata.source || 'NSE API';

            const timeEl = document.getElementById('nifty50-update-time');
            if (timeEl) timeEl.textContent = metadata.update_time || '09:10 AM IST';

            // Update card grid
            if (stocks.length === 0) {
                cardGrid.innerHTML = '<div class="text-center py-8 text-text-muted col-span-full">No Nifty 50 data available yet. Data will be fetched at 9:10 AM.</div>';
                return;
            }

            // Render Card Grid
            cardGrid.innerHTML = stocks.map((stock, index) => {
                const hasToken = stock.token && stock.token !== '';
                const statusIcon = hasToken ? '✅' : '⚠️';
                const statusClass = hasToken ? 'text-success' : 'text-warning';

                // Format numbers
                const iep = stock.iep ? `₹${parseFloat(stock.iep).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--';
                const changePercent = stock.change_percent ? parseFloat(stock.change_percent).toFixed(2) : '0.00';
                const gapPercent = stock.gap_percent ? parseFloat(stock.gap_percent).toFixed(2) : '0.00';
                const volume = stock.volume ? parseInt(stock.volume).toLocaleString('en-IN') : '--';

                // Color classes
                const changeClass = parseFloat(changePercent) > 0 ? 'text-success' : parseFloat(changePercent) < 0 ? 'text-danger' : 'text-text-secondary';
                const gapType = stock.gap_type || 'NEUTRAL';
                const gapBadgeClass = gapType === 'BULLISH' ? 'bg-success/20 text-success' : gapType === 'BEARISH' ? 'bg-danger/20 text-danger' : 'bg-bg-elevated text-text-muted';

                return `
                    <div class="card p-3 bg-bg-surface border border-border-subtle shadow-sm hover:shadow-md transition-all duration-200 hover:bg-bg-elevated/50">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center gap-2">
                                <span class="text-text-secondary font-mono text-xs opacity-50">${stock.rank || index + 1}</span>
                                <h4 class="font-semibold text-text-primary text-base">${(stock.symbol || 'N/A').replace('-EQ', '')}</h4>
                                <span class="${statusClass} text-xs" title="${stock.token || 'No Token'}">${statusIcon}</span>
                            </div>
                            <div class="text-right">
                                <span class="font-mono text-lg font-medium text-text-primary">${iep}</span>
                            </div>
                        </div>
                        <div class="flex justify-between items-center text-sm border-t border-border-subtle pt-2 mt-1">
                            <div class="flex flex-col">
                                <span class="text-xs text-text-muted">Change</span>
                                <span class="font-mono ${changeClass} font-medium">
                                    ${parseFloat(changePercent) > 0 ? '+' : ''}${changePercent}%
                                </span>
                            </div>
                            <div class="flex flex-col">
                                <span class="text-xs text-text-muted">Gap</span>
                                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${gapBadgeClass}">
                                    ${parseFloat(gapPercent) > 0 ? '+' : ''}${gapPercent}%
                                </span>
                            </div>
                            <div class="flex flex-col text-right">
                                <span class="text-xs text-text-muted">Volume</span>
                                <span class="font-mono text-xs text-text-secondary">${volume}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

        } else {
            if (isInitialLoad) {
                cardGrid.innerHTML = `<div class="p-4 text-center text-danger col-span-full">Error loading data: ${result.error || 'Unknown error'}</div>`;
            }
        }
    } catch (error) {
        console.error('Error in refreshNifty50Data:', error);
        const cardGrid = document.getElementById('nifty50-card-grid');
        if (cardGrid && isInitialLoad) {
            cardGrid.innerHTML = `<div class="p-4 text-center text-danger col-span-full">Application Error: ${error.message}</div>`;
        }
    }
}

// ==================== Market Hours Check ====================

function isMarketHours() {
    // Get current time in IST (Indian Standard Time)
    const now = new Date();
    const istTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const hours = istTime.getHours();
    const minutes = istTime.getMinutes();
    const currentTime = hours * 60 + minutes; // Convert to minutes since midnight

    // Market hours: 9:00 AM to 3:30 PM IST
    const marketOpen = 9 * 60;      // 9:00 AM = 540 minutes
    const marketClose = 15 * 60 + 30; // 3:30 PM = 930 minutes

    return currentTime >= marketOpen && currentTime <= marketClose;
}

function getNextMarketOpenTime() {
    const now = new Date();
    const istTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const marketOpen = new Date(istTime);
    marketOpen.setHours(9, 0, 0, 0);

    // If it's already past 9:00 AM, next open is tomorrow
    if (istTime > marketOpen) {
        marketOpen.setDate(marketOpen.getDate() + 1);
    }

    return marketOpen;
}

// ==================== Nifty50 Polling ====================

let nifty50PollingInterval = null;

function startNifty50Polling() {
    // Stop any existing polling
    stopNifty50Polling();

    // Only start polling if in market hours
    if (isMarketHours()) {
        console.log('📊 Starting Nifty50 polling (market hours)');

        // Initial load with loading state
        refreshNifty50Data(true);
        refreshNiftyGapStatus();

        // Poll every 20 seconds during market hours
        nifty50PollingInterval = setInterval(() => {
            if (isMarketHours()) {
                // Smooth update without loading state
                refreshNifty50Data(false);
                refreshNiftyGapStatus();
            } else {
                // Stop polling when market closes
                stopNifty50Polling();
                console.log('📊 Stopped Nifty50 polling (market closed)');
            }
        }, 20000); // 20 seconds
    } else {
        console.log('📊 Market closed - Nifty50 polling not started');
        // Just load data once without polling
        refreshNifty50Data(true);
        refreshNiftyGapStatus();
    }
}

function stopNifty50Polling() {
    if (nifty50PollingInterval) {
        clearInterval(nifty50PollingInterval);
        nifty50PollingInterval = null;
    }
}

function scheduleNextMarketPolling() {
    const nextOpen = getNextMarketOpenTime();
    const now = new Date();
    const delay = nextOpen - now;

    console.log(`📊 Scheduled Nifty50 polling to resume at ${nextOpen.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}`);

    setTimeout(() => {
        startNifty50Polling();
    }, delay);
}

// Handle window resize for charts
window.addEventListener('resize', () => {
    Object.values(stockCharts).forEach(chartData => {
        if (chartData && chartData.chart) {
            chartData.chart.applyOptions({
                width: chartData.wrapper.clientWidth - 32 // Account for padding
            });
        }
    });
    
    // Resize Nifty chart if it exists
    if (niftyGapChart) {
        const chartContainer = document.getElementById('nifty-gap-chart');
        if (chartContainer) {
            niftyGapChart.applyOptions({
                width: chartContainer.clientWidth,
                height: chartContainer.clientHeight
            });
        }
    }
});

function init() {
    // Update time every second
    updateTime();
    setInterval(updateTime, 1000);

    // Initialize event listeners
    initEventListeners();

    // Load initial config
    loadInitialConfig();

    // Initial data load for dashboard
    refreshAllData();

    // Start Nifty50 polling based on market hours
    startNifty50Polling();

    // Check every minute if we need to start/stop polling (for market open/close transitions)
    setInterval(() => {
        const activeTabEl = document.querySelector('.tab-btn.active');
        const activeTab = activeTabEl ? activeTabEl.dataset.tab : 'dashboard';

        if (activeTab === 'nifty50') {
            if (isMarketHours() && !nifty50PollingInterval) {
                // Market just opened, start polling
                startNifty50Polling();
            } else if (!isMarketHours() && nifty50PollingInterval) {
                // Market just closed, stop polling and schedule next
                stopNifty50Polling();
                scheduleNextMarketPolling();
            }
        }
    }, 60000); // Check every minute

    console.log('📊 Trading Bot Dashboard initialized');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
