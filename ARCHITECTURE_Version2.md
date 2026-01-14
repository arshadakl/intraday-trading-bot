# 🏗️ Project Architecture & Structure

This document details the complete project structure, component design, and UI plan for the Intraday Trading Bot.

---

## 📋 Table of Contents

- [Project Structure](#-project-structure)
- [Component Architecture](#-component-architecture)
- [Module Details](#-module-details)
- [Data Flow](#-data-flow)
- [Database Schema](#-database-schema)
- [API Design](#-api-design)
- [UI/Dashboard Plan](#-uidashboard-plan)
- [File Descriptions](#-file-descriptions)
- [Technology Stack](#-technology-stack)
- [Development Phases](#-development-phases)

---

## 📁 Project Structure

### Complete Directory Tree

```
intraday-trading-bot/
│
├── 📄 . env                           # API credentials (NEVER commit!)
├── 📄 . env.example                   # Example environment file
├── 📄 . gitignore                     # Git ignore rules
├── 📄 README.md                      # Main documentation
├── 📄 ARCHITECTURE.md                # This file
├── 📄 requirements.txt               # Python dependencies
├── 📄 run.py                         # Main entry point
│
├── 📁 config/                        # Configuration files
│   ├── 📄 settings.json              # User settings (editable)
│   ├── 📄 nifty50.json               # Nifty 50 stock tokens
│   └── 📄 defaults.py                # Default configuration values
│
├── 📁 src/                           # Source code
│   ├── 📄 __init__.py
│   │
│   ├── 📁 core/                      # Core bot logic
│   │   ├── 📄 __init__.py
│   │   ├── 📄 config_manager.py      # Configuration handling
│   │   ├── 📄 bot. py                 # Main bot orchestrator
│   │   └── 📄 scheduler.py           # Task scheduling
│   │
│   ├── 📁 broker/                    # Broker integration
│   │   ├── 📄 __init__.py
│   │   ├── 📄 angel_client.py        # Angel One REST API
│   │   ├── 📄 websocket_client.py    # Real-time WebSocket
│   │   └── 📄 paper_trader.py        # Paper trading simulator
│   │
│   ├── 📁 analysis/                  # Market analysis
│   │   ├── 📄 __init__. py
│   │   ├── 📄 indicators.py          # Technical indicators (RSI, VWAP)
│   │   ├── 📄 stock_scorer.py        # Stock scoring algorithm
│   │   └── 📄 pre_market. py          # Pre-market analysis
│   │
│   ├── 📁 strategy/                  # Trading strategies
│   │   ├── 📄 __init__.py
│   │   ├── 📄 base_strategy.py       # Strategy interface
│   │   ├── 📄 vwap_rsi_strategy.py   # VWAP + RSI strategy
│   │   └── 📄 risk_manager.py        # Risk management
│   │
│   ├── 📁 executor/                  # Trade execution
│   │   ├── 📄 __init__. py
│   │   ├── 📄 order_manager.py       # Order placement
│   │   └── 📄 position_tracker.py    # Position tracking
│   │
│   └── 📁 api/                       # REST API server
│       ├── 📄 __init__.py
│       └── 📄 server.py              # Flask API endpoints
│
├── 📁 dashboard/                     # Web UI (HTML/CSS/JS)
│   ├── 📄 index.html                 # Main dashboard page
│   ├── 📄 styles.css                 # Dashboard styling
│   └── 📄 app.js                     # Frontend JavaScript
│
├── 📁 data/                          # Data storage
│   ├── 📁 daily/                     # Daily price logs
│   │   └── 📄 2024-01-15.json
│   ├── 📁 trades/                    # Trade history
│   │   └── 📄 2024-01-15.json
│   └── 📁 reports/                   # Daily reports
│       └── 📄 2024-01-15.json
│
└── 📁 logs/                          # Application logs
    └── 📄 bot.log
```

---

## 🏛️ Component Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRADING BOT SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         PRESENTATION LAYER                           │   │
│  │  ┌──────────────────┐        ┌────────────────────────────────┐     │   │
│  │  │   Web Dashboard  │◄──────►│      REST API (Flask)          │     │   │
│  │  │  (HTML/CSS/JS)   │        │   localhost:5000/api/*         │     │   │
│  │  └──────────────────┘        └────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                       ▲                                     │
│                                       │                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          APPLICATION LAYER                           │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  TradingBot  │  │  Scheduler   │  │ ConfigManager│               │   │
│  │  │ (Orchestrator│  │ (Time-based) │  │  (Settings)  │               │   │
│  │  └──────┬───────┘  └──────────────┘  └──────────────┘               │   │
│  │         │                                                             │   │
│  │         ▼                                                             │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │                     BUSINESS LOGIC                            │   │   │
│  │  │                                                               │   │   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │   │
│  │  │  │  Analysis  │  │  Strategy  │  │  Executor  │              │   │   │
│  │  │  │  Module    │  │  Module    │  │  Module    │              │   │   │
│  │  │  ├────────────┤  ├────────────┤  ├────────────┤              │   │   │
│  │  │  │ PreMarket  │  │ VWAP+RSI   │  │ OrderMgr   │              │   │   │
│  │  │  │ StockScorer│  │ RiskMgr    │  │ PositionTrk│              │   │   │
│  │  │  │ Indicators │  │            │  │            │              │   │   │
│  │  │  └────────────┘  └────────────┘  └────────────┘              │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                     │
│                                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          INTEGRATION LAYER                           │   │
│  │                                                                       │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │   │
│  │  │  AngelOneClient  │  │  WebSocketClient │  │   PaperTrader    │   │   │
│  │  │   (REST API)     │  │  (Real-time)     │  │   (Simulator)    │   │   │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────────────┘   │   │
│  │           │                     │                                    │   │
│  └───────────┼─────────────────────┼────────────────────────────────────┘   │
│              │                     │                                        │
│              ▼                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          EXTERNAL SERVICES                           │   │
│  │                                                                       │   │
│  │         ┌─────────────────────────────────────────┐                  │   │
│  │         │        ANGEL ONE SMARTAPI               │                  │   │
│  │         │  ┌─────────────┐  ┌─────────────┐       │                  │   │
│  │         │  │  REST API   │  │  WebSocket  │       │                  │   │
│  │         │  │  (Orders)   │  │  (Prices)   │       │                  │   │
│  │         │  └─────────────┘  └─────────────┘       │                  │   │
│  │         └─────────────────────────────────────────┘                  │   │
│  └───────────────────────────────────────────────────���─────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           DATA LAYER                                 │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │ config/      │  │ data/        │  │ logs/        │               │   │
│  │  │ settings. json│  │ daily/*. json │  │ bot.log      │               │   │
│  │  │ nifty50.json │  │ trades/*.json│  │              │               │   │
│  │  └──────────────┘  │ reports/*.json│ └──────────────┘               │   │
│  │                    └──────────────┘                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Module Details

### 1. Core Module (`src/core/`)

```
┌─────────────────────────────────────────────────────────────┐
│                      CORE MODULE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ config_manager.py                                    │   │
│  │ ─────────────────                                    │   │
│  │ • Load/save JSON configuration                       │   │
│  │ • Get/set config values (dot notation)               │   │
│  │ • Merge with defaults                                │   │
│  │ • Singleton pattern for global access                │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── get(key, default) → Get config value             │   │
│  │ ├── set(key, value) → Set and save config            │   │
│  │ ├── save() → Save current config to file             │   │
│  │ └── reload() → Reload config from file               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ bot.py                                               │   │
│  │ ──────                                               │   │
│  │ • Main orchestrator - controls everything            │   │
│  │ • Initialize all components on startup               │   │
│  │ • Coordinate:  analysis → strategy → execution        │   │
│  │ • Handle start/stop/pause commands                   │   │
│  │ • Manage activity log for dashboard                  │   │
│  │                                                       │   │
│  │ Key Methods:                                           │   │
│  │ ├── initialize() → Setup all components              │   │
│  │ ├── start() → Start trading bot                      │   │
│  │ ├── stop() → Stop and cleanup                        │   │
│  │ ├── pause() / resume() → Pause/resume trading        │   │
│  │ ├── run_pre_market_analysis() → Analyze stocks       │   │
│  │ ├── square_off_all() → Close all positions           │   │
│  │ └── get_status() → Get current bot status            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ scheduler.py                                         │   │
│  │ ────────────                                         │   │
│  │ • Time-based task scheduling                         │   │
│  │ • Run tasks at specific times daily                  │   │
│  │ • Check market hours                                 │   │
│  │                                                       │   │
│  │ Schedule:                                              │   │
│  │ ├── 08:30 AM → Pre-market analysis                   │   │
│  │ ├── 09:15 AM → Start monitoring (WebSocket)          │   │
│  │ ├── 15:15 PM → Square off all positions              │   │
│  │ └── 15:30 PM → Generate daily report                 │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── schedule_task(name, time, callback)              │   │
│  │ ├── is_market_hours() → Check if market open         │   │
│  │ ├── is_trading_hours() → Check if can trade          │   │
│  │ └── start() / stop() → Control scheduler             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Broker Module (`src/broker/`)

```
┌─────────────────────────────────────────────────────────────┐
│                      BROKER MODULE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ angel_client.py                                      │   │
│  │ ────────────────                                     │   │
│  │ • Angel One SmartAPI wrapper                         │   │
│  │ • All broker communication goes through here         │   │
│  │                                                       │   │
│  │ Authentication:                                       │   │
│  │ ├── login() → Authenticate with TOTP                 │   │
│  │ └── logout() → End session                           │   │
│  │                                                       │   │
│  │ Account Data:                                         │   │
│  │ ├── get_profile() → User profile info                │   │
│  │ ├── get_funds() → Account balance                    │   │
│  │ └── get_positions() → Open positions                 │   │
│  │                                                       │   │
│  │ Market Data:                                          │   │
│  │ ├── get_ltp(symbol, token) → Last traded price       │   │
│  │ ├── get_quote(symbol, token) → Full quote            │   │
│  │ └── get_historical_data() → OHLCV candles            │   │
│  │                                                       │   │
│  │ Orders:                                               │   │
│  │ ├── place_order() → Place buy/sell order             │   │
│  │ ├── cancel_order() → Cancel pending order            │   │
│  │ └── get_order_book() → All orders today              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ websocket_client. py                                  │   │
│  │ ───────────────────                                  │   │
│  │ • Real-time price streaming via WebSocket            │   │
│  │ • Receives price updates every tick                  │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── connect() → Connect to WebSocket server          │   │
│  │ ├── subscribe(tokens) → Subscribe to stocks          │   │
│  │ ├── disconnect() → Close connection                  │   │
│  │ └── on_price_update → Callback for price updates     │   │
│  │                                                       │   │
│  │ Data Received:                                        │   │
│  │ ├── LTP (Last Traded Price)                          │   │
│  │ ├── Open, High, Low, Close                           │   │
│  │ ├── Volume                                            │   │
│  │ └── Timestamp                                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ paper_trader.py                                      │   │
│  │ ───────────────                                      │   │
│  │ • Simulates trading without real money               │   │
│  │ • Same interface as real trading                     │   │
│  │ • Tracks virtual positions and P&L                   │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── set_balance(amount) → Set virtual balance        │   │
│  │ ├── place_buy_order() → Simulate buy                 │   │
│  │ ├── place_sell_order() → Simulate sell               │   │
│  │ ├── update_price() → Update position price           │   │
│  │ ├── get_positions() → Get virtual positions          │   │
│  │ ├── get_trades_today() → Get today's trades          │   │
│  │ └── get_daily_summary() → P&L summary                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Analysis Module (`src/analysis/`)

```
┌─────────────────────────────────────────────────────────────┐
│                     ANALYSIS MODULE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ indicators.py                                        │   │
│  │ ─────────────                                        │   │
│  │ • Technical indicator calculations                   │   │
│  │ • Uses pandas/numpy for efficiency                   │   │
│  │                                                       │   │
│  │ Indicators:                                           │   │
│  │ ├── calculate_rsi(prices, period=14)                 │   │
│  │ │   └── Relative Strength Index (0-100)              │   │
│  │ │                                                     │   │
│  │ ├── calculate_vwap(high, low, close, volume)         │   │
│  │ │   └── Volume Weighted Average Price                │   │
│  │ │                                                     │   │
���  │ ├── calculate_sma(prices, period)                    │   │
│  │ │   └── Simple Moving Average                        │   │
│  │ │                                                     │   │
│  │ ├── calculate_ema(prices, period)                    │   │
│  │ │   └── Exponential Moving Average                   │   │
│  │ │                                                     │   │
│  │ ├── calculate_atr(high, low, close, period=14)       │   │
│  │ │   └── Average True Range (volatility)              │   │
│  │ │                                                     │   │
│  │ └── calculate_volume_ratio(volume, period=20)        │   │
│  │     └── Current volume vs average                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ stock_scorer.py                                      │   │
│  │ ───────────────                                      │   │
│  │ • Scores stocks for intraday trading potential       │   │
│  │ • Composite score from multiple factors              │   │
│  │                                                       │   │
│  │ Scoring Factors (each 0-100):                         │   │
│  │ ├── Volatility Score (25%)                           │   │
│  │ │   └── Higher ATR = higher score                    │   │
│  │ │                                                     │   │
│  │ ├── Volume Score (25%)                               │   │
│  │ │   └── Above average volume = higher score          │   │
│  │ │                                                     │   │
│  │ ├── Trend Score (25%)                                │   │
│  │ │   └── Clear trend direction = higher score         │   │
│  │ │                                                     │   │
│  │ └── Momentum Score (25%)                             │   │
│  │     └── RSI in favorable zone = higher score         │   │
│  │                                                       │   │
│  │ Final Score = Weighted average (0-100)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ pre_market. py                                        │   │
│  │ ─────────────                                        │   │
│  │ • Runs before market opens (8:30 AM)                 │   │
│  │ • Analyzes all 50 Nifty stocks                       │   │
│  │ • Selects top 2 stocks for trading                   │   │
│  │                                                       │   │
│  │ Process:                                              │   │
│  │ ├── 1. Load Nifty 50 stock list                      │   │
│  │ ├── 2. Fetch historical data for each stock         │   │
│  │ ├── 3. Calculate indicators for each stock          │   │
│  │ ├── 4. Score each stock                              │   │
│  │ ├── 5. Sort by score (descending)                    │   │
│  │ ├── 6. Select top N stocks (default:  2)              │   │
│  │ └── 7. Calculate entry/target/SL for selected        │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── analyze_all_stocks() → Score all Nifty 50        │   │
│  │ ├── analyze_stock(symbol) → Analyze single stock     │   │
│  │ └── get_selected_stocks() → Return top stocks        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Strategy Module (`src/strategy/`)

```
┌─────────────────────────────────────────────────────────────┐
│                     STRATEGY MODULE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ base_strategy.py                                     │   │
│  │ ────────────────                                     │   │
│  │ • Abstract base class for all strategies             │   │
│  │ • Defines interface that strategies must implement   │   │
│  │                                                       │   │
│  │ Abstract Methods:                                     │   │
│  │ ├── check_entry_signal(stock, price) → Dict/None     │   │
│  │ ├── check_exit_signal(position, price) → Dict/None   │   │
│  │ └── calculate_entry_points(stock) → Dict             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ vwap_rsi_strategy.py                                 │   │
│  │ ────────────────────                                 │   │
│  │ • Main trading strategy:  VWAP + RSI Crossover        │   │
│  │                                                       │   │
│  │ Configuration:                                        │   │
│  │ ├── stop_loss_percent:  0.5%                          │   │
│  │ ├── target_percent: 1.0%                             │   │
│  │ ├── rsi_oversold:  40                                 │   │
│  │ └── rsi_overbought:  70                               │   │
│  │                                                       │   │
│  │ Entry Signal (BUY):                                   │   │
│  │ ├── Price crosses ABOVE VWAP                         │   │
│  │ ├── RSI between 40-60 (not extreme)                  │   │
│  │ ├── Volume > Average volume                          │   │
│  │ └── Time between 9:30 AM - 3:00 PM                   │   │
│  │                                                       │   │
│  │ Exit Signal (SELL):                                   │   │
│  │ ├── Price hits TARGET (entry + 1%)                   │   │
│  │ ├── Price hits STOP-LOSS (entry - 0.5%)              │   │
│  │ ├── RSI > 70 (overbought)                            │   │
│  │ ├── Price crosses BELOW VWAP                         │   │
│  │ └── Time is 3:15 PM (forced exit)                    │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── check_entry_signal(stock, current_price)         │   │
│  │ │   └── Returns:  {entry_price, stop_loss, target}    │   │
│  │ ├── check_exit_signal(position, current_price)       │   │
│  │ │   └── Returns: {action:  'EXIT', reason: '... '}     │   │
│  │ └── calculate_entry_points(stock)                    │   │
│  │     └── Returns: {entry, target, stop_loss}          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ risk_manager.py                                      │   │
│  │ ───────────────                                      │   │
│  │ • Controls risk at trade and daily level             │   │
│  │ • Position sizing based on risk                      │   │
│  │                                                       │   │
│  │ Configuration:                                        │   │
│  │ ├── total_capital: Trading capital available         │   │
│  │ ├── max_daily_loss_percent: 2%                       │   │
│  │ ├── max_trades_per_day: 3                            │   │
│  │ └── max_position_size_percent: 25%                   │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── can_trade() → bool                               │   │
│  │ │   └── Check if trading is allowed                  │   │
│  │ │                                                     │   │
│  │ ├── calculate_position_size(entry, stop_loss)        │   │
│  │ │   └── Returns quantity to buy                      │   │
│  │ │                                                     │   │
│  │ ├── record_trade() → Increment trade count           │   │
│  │ ├── record_loss(amount) → Track daily loss           │   │
│  │ ├── get_daily_pnl() → Current day P&L                │   │
│  │ └── reset_daily() → Reset for new day                │   │
│  │                                                       │   │
│  │ Position Sizing Formula:                              │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ risk_amount = capital × (stop_loss_% / 100)     │ │   │
│  │ │ price_diff = entry_price - stop_loss_price      │ │   │
│  │ │ quantity = risk_amount / price_diff             │ │   │
│  │ │                                                  │ │   │
│  │ │ Example:                                         │ │   │
│  │ │ Capital: ₹50,000, Stop Loss: 0.5%               │ │   │
│  │ │ Risk Amount: ₹250                               │ │   │
│  │ │ Entry:  ₹2450, SL: ₹2438 (diff: ₹12)            │ │   │
│  │ │ Quantity: 250/12 = 20 shares                    │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5. Executor Module (`src/executor/`)

```
┌─────────────────────────────────────────────────────────────┐
│                     EXECUTOR MODULE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ order_manager.py                                     │   │
│  │ ────────────────                                     │   │
│  │ • Handles all order placement                        │   │
│  │ • Routes to paper or live trader                     │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── place_buy_order(symbol, token, price, qty,       │   │
│  │ │                   stop_loss, target)               │   │
│  │ │   └── Returns: bool (success/failure)              │   │
│  │ │                                                     │   │
│  │ ├── place_sell_order(symbol, token, price,           │   │
│  │ │                    qty, reason)                    │   │
│  │ │   └── Returns: bool (success/failure)              │   │
│  │ │                                                     │   │
│  │ ├── get_trades_today() → List[Dict]                  │   │
│  │ │   └── All completed trades today                   │   │
│  │ │                                                     │   │
│  │ └── get_pending_orders() → List[Dict]                │   │
│  │     └── Orders not yet executed                      │   │
│  │                                                       │   │
│  │ Routing Logic:                                        │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ if is_paper_mode:                                │ │   │
│  │ │     paper_trader.place_order(...)               │ │   │
│  │ │ else:                                           │ │   │
│  │ │     angel_client.place_order(...)               │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ position_tracker.py                                  │   │
│  │ ──────────────────                                   │   │
│  │ • Tracks all open positions                          │   │
│  │ • Updates prices in real-time                        │   │
│  │ • Calculates unrealized P&L                          │   │
│  │                                                       │   │
│  │ Position Data Structure:                              │   │
│  │ ├── symbol: "RELIANCE-EQ"                            │   │
│  │ ├── token: "2885"                                    │   │
│  │ ├── entry_price: 2450.00                             │   │
│  │ ├── quantity: 20                                     │   │
│  │ ├── current_price: 2455.00                           │   │
│  │ ├── stop_loss:  2438.00                               │   │
│  │ ├── target: 2475.00                                  │   │
│  │ ├── pnl: 100.00                                      │   │
│  │ └── entry_time: "2024-01-15T09:45:30"                │   │
│  │                                                       │   │
│  │ Key Methods:                                          │   │
│  │ ├── add_position(symbol, token, entry, qty, sl, tgt) │   │
│  │ ├── remove_position(symbol)                          │   │
│  │ ├── update_price(symbol, price)                      │   │
│  │ ├── get_position(symbol) → Dict                      │   │
│  │ ├── get_all_positions() → List[Dict]                 │   │
│  │ └── has_position(symbol) → bool                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└──────────────────────────────���──────────────────────────────┘
```

### 6. API Module (`src/api/`)

```
┌─────────────────────────────────────────────────────────────┐
│                       API MODULE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ server.py                                            │   │
│  │ ─────────                                            │   │
│  │ • Flask REST API server                              │   │
│  │ • Serves dashboard and API endpoints                 │   │
│  │ • CORS enabled for browser access                    │   │
│  │                                                       │   │
│  │ Server Config:                                        │   │
│  │ ├── Host: 127.0.0.1 (localhost only)                 │   │
│  │ ├── Port:  5000                                       │   │
│  │ └── Debug:  False (production)                        │   │
│  │                                                       │   │
│  │ Static Files:                                         │   │
│  │ ├── GET / → Serve index.html                         │   │
│  │ └── GET /static/* → Serve CSS/JS files               │   │
│  │                                                       │   │
│  │ API Endpoints:                                        │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ Status & Info                                    │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ GET  /api/status      → Bot status overview      │ │   │
│  │ │ GET  /api/account     → Account balance info     │ │   │
│  │ │ GET  /api/logs        → Activity log (last 50)   │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  │                                                       │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ Configuration                                    │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ GET  /api/config      → Get current config       │ │   │
│  │ │ POST /api/config      → Update config values     │ │   │
│  │ │ POST /api/mode        → Switch paper/live mode   │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  │                                                       │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ Trading Data                                     │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ GET  /api/stocks/selected → Selected stocks      │ │   │
│  │ │ GET  /api/positions       → Open positions       │ │   │
│  │ │ GET  /api/trades/today    → Today's trades       │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  │                                                       │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ Bot Control                                      │ │   │
│  │ ├─────────────────────────────────────────────────┤ │   │
│  │ │ POST /api/bot/start   → Start the bot            │ │   │
│  │ │ POST /api/bot/pause   → Pause trading            │ │   │
│  │ │ POST /api/bot/resume  → Resume trading           │ │   │
│  │ │ POST /api/bot/stop    → Stop bot completely      │ │   │
│  │ │ POST /api/position/exit → Exit specific position │ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                           ANGEL ONE SERVERS
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
   ┌───────────┐           ┌───────────┐           ┌───────────┐
   │ Historical│           │ Real-time │           │  Account  │
   │   Data    │           │  Prices   │           │   Data    │
   │ (REST API)│           │(WebSocket)│           │ (REST API)│
   └─────┬─────┘           └─────┬─────┘           └─────┬─────┘
         │                       │                       │
         ▼                       ▼                       ▼
   ┌───────────────────────────────────────────────────────────┐
   │                    ANGEL ONE CLIENT                        │
   │                    (src/broker/angel_client.py)            │
   └─────────────────────────────┬─────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   PRE-MARKET    │ │    REAL-TIME    │ │    ACCOUNT      │
    │    ANALYZER     │ │    MONITOR      │ │    MANAGER      │
    │                 │ │                 │ │                 │
    │ • Fetch OHLCV   │ │ • Price ticks   │ │ • Balance       │
    │ • Calculate     │ │ • Update UI     │ │ • Positions     │
    │   indicators    │ │ • Check signals │ │ • P&L           │
    │ • Score stocks  │ │                 │ │                 │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             └─────────┬─────────┴─────────┬─────────┘
                       │                   │
                       ▼                   ▼
             ┌─────────────────┐ ┌─────────────────┐
             │    STRATEGY     │ │      RISK       │
             │     ENGINE      │ │    MANAGER      │
             │                 │ │                 │
             │ • Entry signals │ │ • Position size │
             │ • Exit signals  │ │ • Daily limits  │
             │ • VWAP + RSI    │ │ • Can trade?     │
             └────────┬────────┘ └────────┬────────┘
                      │                   │
                      └─────────┬─────────┘
                                │
                                ▼
                      ┌─────────────────┐
                      │  ORDER MANAGER  │
                      │                 │
                      │ • Place orders  │
                      │ • Track status  │
                      └────────┬────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  PAPER TRADER   │ │   LIVE ORDERS   │ │ POSITION TRACKER│
    │  (Simulation)   │ │ (Angel One API) │ │                 │
    │                 │ │                 │ │ • Track open    │
    │ • Virtual P&L   │ │ • Real orders   │ │ • Update prices │
    │ • No real money │ │ • Real money    │ │ • Calculate P&L │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             └─────────┬─────────┴─────────┬─────────┘
                       │                   │
                       ▼                   ▼
             ┌─────────────────┐ ┌─────────────────┐
             │   DATA STORE    │ │   REST API      │
             │   (JSON Files)  │ │   (Flask)       │
             │                 │ │                 │
             │ • daily/*. json  │ │ • /api/status   │
             │ • trades/*.json │ │ • /api/positions│
             │ • reports/*.json│ │ • /api/trades   │
             └─────────────────┘ └────────┬────────┘
                                          │
                                          ▼
                                ┌─────────────────┐
                                │    DASHBOARD    │
                                │   (HTML/JS/CSS) │
                                │                 │
                                │ • Display data  │
                                │ • User controls │
                                │ • Configuration │
                                └─────────────────┘
```

---

## 💾 Database Schema

### We use JSON files for simplicity (no database server needed)

### 1. Daily Price Log (`data/daily/YYYY-MM-DD.json`)

```json
{
  "date": "2024-01-15",
  "stocks": {
    "RELIANCE-EQ": {
      "token": "2885",
      "ticks": [
        {
          "time": "09:15:01",
          "ltp": 2445.50,
          "open": 2440.00,
          "high":  2446.00,
          "low":  2438.00,
          "volume": 125000
        },
        {
          "time": "09:15:02",
          "ltp": 2446.00,
          "open":  2440.00,
          "high": 2446.00,
          "low": 2438.00,
          "volume": 126500
        }
      ]
    },
    "TATAMOTORS-EQ": {
      "token": "3456",
      "ticks": [...]
    }
  }
}
```

### 2. Trade History (`data/trades/YYYY-MM-DD.json`)

```json
{
  "date": "2024-01-15",
  "mode": "paper",
  "trades": [
    {
      "id": "T001",
      "symbol": "RELIANCE-EQ",
      "token": "2885",
      "type": "BUY",
      "entry_price": 2448.50,
      "exit_price": 2472.75,
      "quantity": 20,
      "entry_time": "2024-01-15T10:30:45",
      "exit_time":  "2024-01-15T12:15:30",
      "pnl": 485.00,
      "pnl_percent": 0.99,
      "exit_reason": "TARGET",
      "stop_loss": 2436.25,
      "target": 2472.90
    },
    {
      "id": "T002",
      "symbol": "TATAMOTORS-EQ",
      "token": "3456",
      "type": "BUY",
      "entry_price": 652.00,
      "exit_price": 648.50,
      "quantity": 30,
      "entry_time":  "2024-01-15T11:00:15",
      "exit_time":  "2024-01-15T11:45:00",
      "pnl":  -105.00,
      "pnl_percent": -0.54,
      "exit_reason":  "STOP_LOSS",
      "stop_loss": 648.75,
      "target": 658.50
    }
  ]
}
```

### 3. Daily Report (`data/reports/YYYY-MM-DD.json`)

```json
{
  "date":  "2024-01-15",
  "mode": "paper",
  "summary": {
    "initial_balance": 50000.00,
    "final_balance": 50380.00,
    "daily_pnl": 380.00,
    "daily_pnl_percent": 0.76,
    "total_trades": 2,
    "winning_trades": 1,
    "losing_trades": 1,
    "win_rate": 50.0,
    "max_drawdown": -105.00,
    "largest_win": 485.00,
    "largest_loss": -105.00
  },
  "selected_stocks": [
    {
      "symbol": "RELIANCE-EQ",
      "score": 78.5,
      "traded":  true
    },
    {
      "symbol": "TATAMOTORS-EQ",
      "score": 72.3,
      "traded": true
    }
  ],
  "trades":  [... ],
  "config_used": {
    "stop_loss_percent": 0.5,
    "target_percent": 1.0,
    "max_trades":  3
  }
}
```

### 4. Configuration (`config/settings.json`)

```json
{
  "trading_mode": "paper",
  
  "capital": {
    "use_percentage": true,
    "trading_percentage": 50,
    "fixed_amount": null,
    "per_trade_percentage": 25,
    "per_trade_fixed": null
  },
  
  "stock_selection": {
    "max_stocks": 2,
    "universe": "nifty50",
    "min_volume": 1000000,
    "min_price": 100,
    "max_price": 5000
  },
  
  "strategy": {
    "name": "vwap_rsi",
    "stop_loss_percent": 0.5,
    "stop_loss_max": 0.75,
    "target_percent":  1.0,
    "target_max": 1.5,
    "trailing_stop_loss": false,
    "max_trades_per_day": 3,
    "rsi_oversold":  40,
    "rsi_overbought": 70
  },
  
  "risk":  {
    "max_daily_loss_percent": 2.0,
    "max_daily_loss_max": 3.0,
    "max_position_size_percent": 25
  },
  
  "timing": {
    "analysis_start": "08:30",
    "trading_start": "09:15",
    "no_new_trade_after": "15:00",
    "square_off_time": "15:15",
    "market_close": "15:30"
  },
  
  "alerts": {
    "sound_enabled": true,
    "desktop_notifications": true
  }
}
```

---

## 🔌 API Design

### REST API Specification

#### Base URL
```
http://localhost:5000/api
```

#### Response Format
All responses follow this structure:
```json
{
  "success": true,
  "data": { ...  },
  "message": "Optional message",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Endpoints Detail

#### 1. GET /api/status
Get complete bot status. 

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "RUNNING",
    "mode": "paper",
    "is_paper_mode": true,
    "start_time": "2024-01-15T08:30:00",
    "market_status": "OPEN",
    "selected_stocks_count": 2,
    "open_positions_count": 1,
    "daily_stats": {
      "trades": 2,
      "wins": 1,
      "losses": 1,
      "pnl": 380.00
    }
  }
}
```

#### 2. GET /api/account
Get account information.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_balance": 50380.00,
    "available_balance": 40380.00,
    "used_margin": 10000.00,
    "daily_pnl": 380.00,
    "daily_pnl_percent": 0.76
  }
}
```

#### 3. GET /api/config
Get current configuration.

**Response:**
```json
{
  "success": true,
  "data": {
    "trading_mode": "paper",
    "capital": { ... },
    "stock_selection": { ... },
    "strategy": { ... },
    "risk": { ... },
    "timing": { ... }
  }
}
```

#### 4. POST /api/config
Update configuration. 

**Request:**
```json
{
  "strategy. stop_loss_percent": 0.75,
  "strategy.target_percent": 1.5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated",
  "data": {
    "updated_keys": ["strategy.stop_loss_percent", "strategy.target_percent"]
  }
}
```

#### 5. GET /api/stocks/selected
Get today's selected stocks.

**Response:**
```json
{
  "success": true,
  "data": {
    "date": "2024-01-15",
    "stocks": [
      {
        "symbol":  "RELIANCE-EQ",
        "token": "2885",
        "name": "Reliance Industries",
        "score": 78.5,
        "ltp": 2450.00,
        "entry_price": 2448.00,
        "target": 2472.48,
        "stop_loss": 2435.76,
        "status": "WATCHING"
      },
      {
        "symbol": "TATAMOTORS-EQ",
        "token": "3456",
        "name": "Tata Motors",
        "score":  72.3,
        "ltp": 652.00,
        "entry_price": 650.00,
        "target":  656.50,
        "stop_loss": 646.75,
        "status":  "POSITION_OPEN"
      }
    ]
  }
}
```

#### 6. GET /api/positions
Get open positions.

**Response:**
```json
{
  "success": true,
  "data": {
    "positions": [
      {
        "symbol": "TATAMOTORS-EQ",
        "token": "3456",
        "entry_price": 650.00,
        "current_price": 653.50,
        "quantity": 30,
        "pnl": 105.00,
        "pnl_percent": 0.54,
        "stop_loss": 646.75,
        "target":  656.50,
        "entry_time": "2024-01-15T10:30:00",
        "progress_to_target": 54
      }
    ],
    "total_unrealized_pnl": 105.00
  }
}
```

#### 7. GET /api/trades/today
Get today's completed trades.

**Response:**
```json
{
  "success":  true,
  "data": {
    "date": "2024-01-15",
    "trades": [
      {
        "id": "T001",
        "symbol":  "RELIANCE-EQ",
        "entry_price": 2448.50,
        "exit_price":  2472.75,
        "quantity": 20,
        "pnl": 485.00,
        "pnl_percent": 0.99,
        "exit_reason": "TARGET",
        "entry_time": "2024-01-15T10:30:45",
        "exit_time":  "2024-01-15T12:15:30"
      }
    ],
    "summary": {
      "total_trades": 1,
      "total_pnl": 485.00,
      "win_rate": 100
    }
  }
}
```

#### 8. GET /api/logs
Get activity logs.

**Query Params:** `?limit=50`

**Response:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2024-01-15T10:30:45",
        "time": "10:30:45",
        "category": "TRADE",
        "message": "BUY 20 RELIANCE-EQ @ ₹2,448.50",
        "data": {
          "stop_loss": 2435.76,
          "target":  2472.48
        }
      },
      {
        "timestamp": "2024-01-15T09:15:00",
        "time": "09:15:00",
        "category": "SYSTEM",
        "message": "Market opened - WebSocket connected",
        "data": {}
      }
    ]
  }
}
```

#### 9. POST /api/bot/start
Start the trading bot.

**Response:**
```json
{
  "success": true,
  "message": "Trading bot started",
  "data": {
    "status": "RUNNING",
    "start_time": "2024-01-15T08:30:00"
  }
}
```

#### 10. POST /api/bot/stop
Stop the trading bot.

**Response:**
```json
{
  "success": true,
  "message": "Trading bot stopped",
  "data": {
    "status": "STOPPED",
    "positions_closed": 1,
    "final_pnl": 380.00
  }
}
```

#### 11. POST /api/mode
Switch trading mode.

**Request:**
```json
{
  "mode":  "live"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to LIVE trading mode",
  "data": {
    "mode": "live",
    "warning": "Real money will be used for trading"
  }
}
```

---

## 🖥️ UI/Dashboard Plan

### Dashboard Layout Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 INTRADAY TRADING BOT              [🟢 RUNNING]  [PAPER]     09:45:32 AM     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │      💰 ACCOUNT INFO        │  │         📋 TODAY'S SELECTED STOCKS       │  │
│  │  ─────────────────────────  │  │  ─────────────────────────────────────  │  │
│  │                             │  │                                         │  │
│  │  Total Balance              │  │  STOCK      LTP      ENTRY    TGT    SL │  │
│  │  ₹50,380.00                 │  │  ─────────────────────────────────────  │  │
│  │                             │  │                                         │  │
│  │  Available                  │  │  RELIANCE   ₹2,450   ₹2,448  ₹2,472  ₹2,436│
│  │  ₹40,380.00                 │  │  Score:  78.5  [🟢 WATCHING]             │  │
│  │                             │  │                                         │  │
│  │  Used Margin                │  │  TATAMTR    ₹653     ₹650    ₹657   ₹647│  │
│  │  ₹10,000.00                 │  │  Score: 72.3  [🟡 POSITION