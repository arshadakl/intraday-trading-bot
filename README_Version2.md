# 🤖 Intraday Trading Bot - Angel One SmartAPI

An automated intraday trading bot for the Indian stock market (Nifty 50) built with Python.  Uses Angel One's free SmartAPI for real-time data and order execution.  Features a simple web dashboard for monitoring and configuration.

![Trading Bot Banner](https://img.shields.io/badge/Trading-Bot-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)
![Angel One](https://img.shields.io/badge/Angel%20One-SmartAPI-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Trading Strategy](#-trading-strategy)
- [Daily Workflow](#-daily-workflow)
- [Risk Management](#-risk-management)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Dashboard](#-dashboard)
- [Paper Trading vs Live Trading](#-paper-trading-vs-live-trading)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)
- [Disclaimer](#-disclaimer)
- [License](#-license)

---

## 🎯 Overview

### What is this? 

This is an **automated intraday trading bot** designed specifically for the **Indian stock market**. It focuses on trading the top **Nifty 50 stocks** using a proven **VWAP + RSI strategy**. 

### Why did I build this?

- To automate repetitive trading tasks
- To remove emotions from trading decisions
- To execute trades at precise entry/exit points
- To learn algorithmic trading concepts

### Who is this for?

- Traders who want to automate their intraday strategies
- Developers interested in algorithmic trading
- Anyone wanting to learn about trading bots

---

## ✨ Features

### Core Features

| Feature | Description |
|---------|-------------|
| 🔍 **Pre-Market Analysis** | Analyzes all 50 Nifty stocks before market opens |
| 📊 **Smart Stock Selection** | Automatically picks 2 best stocks for the day |
| 📈 **VWAP + RSI Strategy** | Proven intraday strategy with clear rules |
| 🎯 **Auto Entry/Exit** | Executes trades at calculated points |
| 🛡️ **Risk Management** | Stop-loss, daily loss limits, position sizing |
| 📱 **Real-time Monitoring** | WebSocket-based live price tracking |
| 🖥️ **Web Dashboard** | Simple UI to monitor and control the bot |
| 📝 **Paper Trading** | Test strategies without real money |
| 💾 **Data Logging** | Saves all trades and price data |

### Technical Features

- ✅ Angel One SmartAPI integration (FREE API)
- ✅ Real-time WebSocket price streaming
- ✅ Configurable via JSON/Dashboard
- ✅ Easy switch between Paper/Live mode
- ✅ Automatic square-off at 3: 15 PM
- ✅ Daily P&L reports
- ✅ Activity logging

---

## 🔄 How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRADING BOT FLOW                              │
└─────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │  BOT STARTS  │
     │   (8:30 AM)  │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  PRE-MARKET  │◄──── Fetch data for all 50 Nifty stocks
     │   ANALYSIS   │◄──── Calculate RSI, VWAP, Volume
     └──────┬───────┘◄──── Score and rank stocks
            │
            ��
     ┌──────────────┐
     │    SELECT    │◄──── Pick top 2 stocks based on score
     │   2 STOCKS   │◄──── Calculate entry, target, stop-loss
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ WAIT FOR     │
     │ MARKET OPEN  │◄──── 9:15 AM
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   CONNECT    │◄──── Start WebSocket connection
     │  WEBSOCKET   │◄──── Subscribe to selected stocks
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   MONITOR    │◄──── Real-time price updates
     │   PRICES     │◄──── Check for entry signals
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ ENTRY SIGNAL │◄──── Price crosses VWAP + RSI conditions
     │   DETECTED   │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  PLACE BUY   │◄──── Calculate quantity based on risk
     │    ORDER     │◄──── Set stop-loss and target
     └──────┬───────��
            │
            ▼
     ┌──────────────┐
     │   MONITOR    │◄──── Track position P&L
     │   POSITION   │◄──── Check exit conditions
     └──────┬───────┘
            │
            ▼
     ┌──────────────────────────────────────────┐
     │              EXIT CONDITIONS              │
     ├───────────────┬──────────────���┬──────────┤
     │  ✅ TARGET    │  🛑 STOP-LOSS │  ⏰ TIME │
     │    HIT        │     HIT       │  3:15 PM │
     └───────────────┴───────────────┴──────────┘
            │
            ▼
     ┌──────────────┐
     │  PLACE SELL  │
     │    ORDER     │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │    UPDATE    │◄──── Record P&L
     │    STATS     │◄──── Update daily statistics
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   GENERATE   │◄──── Save trades to file
     │    REPORT    │◄──── Calculate win rate
     └──────────────┘
```

---

## 📊 Trading Strategy

### Strategy:  VWAP + RSI Crossover

We use a combination of **VWAP (Volume Weighted Average Price)** and **RSI (Relative Strength Index)** for entry and exit decisions.

### Why This Strategy?

| Reason | Explanation |
|--------|-------------|
| **Simple** | Easy to understand and implement |
| **Effective** | Works well for intraday trading |
| **Clear Signals** | No ambiguity in entry/exit points |
| **Risk-Defined** | Stop-loss is always known beforehand |

### Entry Rules (BUY Signal)

ALL conditions must be TRUE: 

```
┌─────────────────────────────────────────────────────────────┐
│                     BUY SIGNAL CONDITIONS                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Price crosses ABOVE VWAP                                │
│     └── Indicates bullish momentum                          │
│                                                             │
│  ✅ RSI is between 40-60                                    │
│     └── Not overbought or oversold                          │
│                                                             │
│  ✅ Volume > Average Volume                                 │
│     └── Confirms momentum with volume                       │
│                                                             │
│  ✅ Time is between 9:30 AM - 2:30 PM                       │
│     └── Avoid first 15 min volatility & last hour          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Exit Rules (SELL Signal)

ANY condition triggers exit:

```
┌─────────────────────────────────────────────────────────────┐
│                    SELL SIGNAL CONDITIONS                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Price hits TARGET (Entry + 1%)                          │
│     └── Book profit at target                               │
│                                                             │
│  🛑 Price hits STOP-LOSS (Entry - 0.5%)                     │
│     └── Cut losses quickly                                  │
│                                                             │
│  ⚠️ RSI goes above 70                                       │
│     └── Overbought - take profit                            │
│                                                             │
│  ⚠️ Price crosses BELOW VWAP                                │
│     └── Trend reversal signal                               │
│                                                             │
│  ⏰ Time is 3:15 PM                                         │
│     └── Forced square-off (intraday rule)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Visual Example

```
Price (₹)
    ▲
    │
2470├─────────────────────────────────────── Target (+1%)
    │                              ╱
    │                           ╱
2450├─────────────────────────●───────────── Entry Point
    │                       ╱ │
    │            ─────────╱───┼─────────── VWAP Line
    │                   ╱     │
2438├─────────────────────────────────────── Stop Loss (-0.5%)
    │
    └──────────────────────────────────────────────────────▶ Time
              9:30      10:00     11:00     12:00

    Legend:
    ● = Entry Point (when price crosses above VWAP with RSI 40-60)
    ─ = VWAP Line (dynamic support/resistance)
```

### Default Settings

| Parameter | Value | Range |
|-----------|-------|-------|
| Stop Loss | 0.5% | 0.5% - 0.75% |
| Target | 1. 0% | 1.0% - 1.5% |
| Max Daily Loss | 2.0% | 2.0% - 3.0% |
| Max Stocks | 2 | 1 - 5 |
| Max Trades/Day | 3 | 1 - 10 |

---

## ⏰ Daily Workflow

### Complete Timeline

```
TIME          EVENT                    DESCRIPTION
──────────────────────────────────────────────────────────────────────
08:30 AM      🟢 Bot Starts            Auto-start (or manual)
              │
08:30-09:00   📊 Pre-Market Analysis   
              ├── Fetch Nifty 50 data
              ├── Calculate indicators
              ├── Score all stocks
              └── Select top 2 stocks
              │
09:00 AM      📌 Stocks Selected       
              ├── Display on dashboard
              ├── Calculate entry points
              └── Set targets & stop-loss
              │
09:15 AM      🔔 Market Opens          
              ├── Connect WebSocket
              ├── Start real-time monitoring
              └── Begin looking for entries
              │
09:15-09:30   ⏳ Initial Volatility    
              └── Wait period (no trades)
              │
09:30 AM      ▶️ Trading Starts         
              ├── Check entry conditions
              └── Execute trades when signals trigger
              │
09:30-15:00   📈 Active Trading        
              ├── Monitor open positions
              ├── Check stop-loss/target
              ├── Execute new trades (if allowed)
              └── Log all price data
              │
15:00 PM      🚫 No New Trades         
              └── Only manage existing positions
              │
15:15 PM      🔴 Square Off            
              ├── Close ALL open positions
              ├── Book profit/loss
              └── Final P&L calculation
              │
15:30 PM      📋 Daily Report          
              ├── Generate trade summary
              ├── Calculate win rate
              ├── Save to reports folder
              └── Update dashboard
              │
15:30 PM      🛑 Bot Stops             
              └── Wait for next trading day
──────────────────────────────────────────────────────────────────────
```

### Weekend/Holiday Handling

- Bot automatically skips weekends (Saturday, Sunday)
- Add market holidays to config (manual)
- No trades on non-trading days

---

## 🛡️ Risk Management

### Multi-Layer Protection

```
┌─────────────────────────────────────────────────────────────────────┐
│                      RISK MANAGEMENT LAYERS                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LAYER 1: Per-Trade Risk                                            │
│  ──────────────────────                                             │
│  ├── Stop-loss:  0.5% per trade                                      │
│  ├── Maximum loss per trade is capped                               │
│  └── Position size calculated based on stop-loss                    │
│                                                                     │
│  LAYER 2: Daily Risk                                                │
│  ─────────────────                                                  │
│  ├── Max daily loss:  2% of capital                                  │
│  ├── Trading stops if limit reached                                 │
│  └── Prevents revenge trading                                       │
│                                                                     │
│  LAYER 3: Capital Allocation                                        │
│  ─────────────────────────                                          │
│  ├── Only use 50% of total capital                                  │
│  ├── Max 25% per single trade                                       │
│  └── Rest stays as buffer                                           │
│                                                                     │
│  LAYER 4: Trade Limits                                              │
│  ────────────────────                                               │
│  ├── Max 3 trades per day                                           │
│  ├── Max 2 stocks to trade                                          │
│  └── Prevents overtrading                                           │
│                                                                     │
│  LAYER 5: Time-Based                                                │
│  ──────────────────                                                 │
│  ├── No trades in first 15 minutes                                  │
│  ├── No new trades after 3:00 PM                                    │
│  └── Forced square-off at 3:15 PM                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Position Sizing Formula

```python
# How we calculate quantity to buy

Risk Amount = Trading Capital × (Stop Loss % / 100)
# Example: ₹50,000 × 0.5% = ₹250 max risk per trade

Price Difference = Entry Price - Stop Loss Price
# Example: ₹2450 - ₹2438 = ₹12

Quantity = Risk Amount / Price Difference
# Example: ₹250 / ₹12 = 20 shares (rounded down)
```

### Daily Loss Limit Example

```
Total Capital:  ₹1,00,000
Trading Capital (50%): ₹50,000
Max Daily Loss (2%): ₹1,000

If losses reach ₹1,000 → Bot stops trading for the day
```

---

## 📋 Prerequisites

### 1. Angel One Account

- Open a **Demat account** with Angel One (Free)
- Complete KYC verification
- Get SmartAPI access from:  https://smartapi.angelone.in/

### 2. API Credentials

You'll need these from Angel One SmartAPI portal: 

| Credential | Where to Get |
|------------|--------------|
| API Key | SmartAPI Dashboard → Create App |
| Client ID | Your Angel One client code |
| Password | Your trading password |
| TOTP Secret | SmartAPI Dashboard → Enable TOTP |

### 3. System Requirements

- **Python 3.9+** installed
- **pip** package manager
- **Windows/Mac/Linux** (any OS)
- **Internet connection** (stable)

### 4. Recommended

- Basic understanding of stock trading
- Familiarity with command line
- Text editor (VS Code recommended)

---

## 🚀 Installation

### Step 1: Clone/Download the Project

```bash
# Create project folder
mkdir intraday-trading-bot
cd intraday-trading-bot

# If you have the files, copy them here
# Or create each file as shown in the project structure
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables

```bash
# Copy example env file
cp .env.example . env

# Edit . env with your credentials
# Use any text editor
```

### Step 5: Configure Your Settings

Edit `config/settings.json` with your preferences. 

### Step 6: Run the Bot

```bash
# Start the bot with dashboard
python run. py
```

### Step 7: Access Dashboard

Open browser and go to: `http://localhost:5000`

---

## ⚙️ Configuration

### Configuration File: `config/settings.json`

```json
{
  "trading_mode": "paper",     // "paper" or "live"
  
  "capital":  {
    "use_percentage": true,    // Use % of balance or fixed amount
    "trading_percentage": 50,  // Use 50% of total balance
    "fixed_amount": null,      // Or set fixed amount like 25000
    "per_trade_percentage": 25 // Max 25% per trade
  },
  
  "stock_selection": {
    "max_stocks": 2,           // Trade max 2 stocks per day
    "universe": "nifty50",     // Stock universe
    "min_volume": 1000000,     // Minimum volume filter
    "min_price": 100,          // Min stock price
    "max_price":  5000          // Max stock price
  },
  
  "strategy": {
    "name": "vwap_rsi",
    "stop_loss_percent": 0.5,  // 0.5% stop loss
    "target_percent": 1.0,     // 1% target
    "max_trades_per_day": 3,   // Max 3 trades
    "rsi_oversold":  40,
    "rsi_overbought": 70
  },
  
  "risk":  {
    "max_daily_loss_percent": 2.0  // Stop if 2% loss
  },
  
  "timing": {
    "analysis_start": "08:30",
    "trading_start": "09:15",
    "no_new_trade_after": "15:00",
    "square_off_time": "15:15"
  }
}
```

### Environment Variables:  `.env`

```env
# Angel One Credentials
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_totp_secret

# Mode
TRADING_MODE=paper

# Server
API_HOST=127.0.0.1
API_PORT=5000
```

---

## 💻 Usage

### Starting the Bot

```bash
# Method 1: Full bot with dashboard
python run.py

# Method 2: Bot only (no dashboard)
python run.py --no-dashboard

# Method 3: Dashboard only (for monitoring)
python run.py --dashboard-only
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--no-dashboard` | Run bot without web UI |
| `--dashboard-only` | Run only dashboard (connect to running bot) |
| `--paper` | Force paper trading mode |
| `--live` | Force live trading mode (⚠️ careful!) |
| `--config FILE` | Use custom config file |

### Dashboard Controls

| Button | Action |
|--------|--------|
| ▶️ START | Start the trading bot |
| ⏸️ PAUSE | Pause trading (keep monitoring) |
| ⏹️ STOP | Stop bot and square off |
| 🔄 REFRESH | Refresh dashboard data |

---

## 🖥️ Dashboard

### Dashboard URL

```
http://localhost:5000
```

### Dashboard Sections

```
┌───────────────���─────────────────────────────────────────────────────────┐
│  📊 INTRADAY TRADING BOT                          [🟢 RUNNING] 09:45 AM │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── ACCOUNT ───┐  ┌─── TODAY'S STOCKS ────────────────────────────┐  │
│  │               │  │                                               │  │
│  │ Balance:       │  │  SYMBOL    LTP      ENTRY   TARGET    SL     │  │
│  │ ₹50,000       │  │  RELIANCE  ₹2,450   ₹2,445  ₹2,469   ₹2,433  │  │
│  │               │  │  TATAMTR   ₹650     ₹648    ₹655     ₹645    │  │
│  │ Today's P&L:  │  │                                               │  │
│  │ +₹350         │  └───────────────────────────────────────────────┘  │
│  │               │                                                      │
│  └───────────────┘  ┌─── OPEN POSITIONS ────────────────────────────┐  │
│                     │                                               │  │
│  ┌─── CONFIG ────┐  │  TATAMTR | BUY @ ₹648 | Qty: 15              │  │
│  │               │  │  Current: ₹652 | P&L: +₹60                   │  │
│  │ Stop Loss:    │  │  [━━━━━━━░░░] 57% to target                  │  │
│  │ [0.5] %       │  │                                               │  │
│  │               │  └───────────────────────────────────────────────┘  │
│  │ Target:       │                                                      │
│  │ [1.0] %       │  ┌─── ACTIVITY LOG ��─────────────────────────────┐  │
│  │               │  │ 09:45 | BUY TATAMTR @ ₹648                   │  │
│  │ [💾 SAVE]     │  │ 09:35 | Monitoring started                   │  │
│  └───────────────┘  │ 09:15 | Market opened                        │  │
│                     │ 09:00 | Stocks selected:  RELIANCE, TATAMTR   │  │
│                     └───────────────────────────────────────────────┘  │
│                                                                         │
│  [▶️ START]  [⏸️ PAUSE]  [⏹️ STOP]  [⚙️ SETTINGS]                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Real-time Updates

- Prices update every second via WebSocket
- P&L updates automatically
- Activity log shows latest events
- No page refresh needed

---

## 🧪 Paper Trading vs Live Trading

### Paper Trading Mode (Default)

```
✅ No real money used
✅ All trades are simulated
✅ Perfect for testing strategies
✅ Learn without financial risk
✅ Same logic as live trading
```

### Live Trading Mode

```
⚠️ Uses REAL MONEY
⚠️ Real orders placed on exchange
⚠️ Profits and losses are real
⚠️ Only use after thorough testing
⚠️ Start with small capital
```

### Switching Modes

**Method 1: Config File**
```json
{
  "trading_mode": "paper"  // Change to "live" for real trading
}
```

**Method 2: Dashboard**
- Click Settings → Trading Mode → Select Paper/Live

**Method 3: Environment**
```bash
TRADING_MODE=paper  # or "live"
```

### Recommendation

```
1. Start with PAPER mode (at least 2 weeks)
2. Analyze your paper trading results
3. If consistently profitable, switch to LIVE
4. Start with small capital (₹10,000 - ₹25,000)
5. Gradually increase based on performance
```

---

## 🔌 API Reference

### REST API Endpoints

The bot runs a local API server for the dashboard. 

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Bot status and overview |
| `/api/account` | GET | Account balance info |
| `/api/config` | GET | Current configuration |
| `/api/config` | POST | Update configuration |
| `/api/stocks/selected` | GET | Today's selected stocks |
| `/api/positions` | GET | Open positions |
| `/api/trades/today` | GET | Today's completed trades |
| `/api/logs` | GET | Recent activity logs |
| `/api/bot/start` | POST | Start the bot |
| `/api/bot/pause` | POST | Pause trading |
| `/api/bot/stop` | POST | Stop the bot |

### Example API Calls

```bash
# Get bot status
curl http://localhost:5000/api/status

# Get account info
curl http://localhost:5000/api/account

# Start the bot
curl -X POST http://localhost:5000/api/bot/start

# Update config
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"strategy. stop_loss_percent": 0.75}'
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Login Failed

```
Error: Login failed - Invalid TOTP
```

**Solution:**
- Regenerate TOTP secret from SmartAPI portal
- Ensure system time is correct (TOTP is time-based)
- Check if API key is active

#### 2. WebSocket Connection Failed

```
Error: WebSocket connection error
```

**Solution:**
- Check internet connection
- Verify feed token is valid
- Restart the bot

#### 3. No Stocks Selected

```
Warning: No stocks selected for today
```

**Solution:**
- Check if market is open
- Verify Nifty 50 tokens in config
- Check API rate limits

#### 4. Order Placement Failed

```
Error: Order failed - Insufficient margin
```

**Solution:**
- Check available balance
- Reduce position size
- Verify trading capital settings

### Debug Mode

```bash
# Run with debug logging
python run.py --debug
```

### Log Files

```
logs/bot.log        # Main bot log
data/daily/         # Daily price data
data/trades/        # Trade history
data/reports/       # Daily reports
```

---

## ⚠️ Disclaimer

### Important Warnings

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ⚠️ DISCLAIMER ⚠️                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1.  FINANCIAL RISK                                                  │
│     Trading in stock markets involves substantial risk of loss.      │
│     Only trade with money you can afford to lose.                    │
│                                                                     │
│  2. NO GUARANTEE                                                    │
│     Past performance does not guarantee future results.             │
│     This bot does not guarantee any profits.                        │
│                                                                     │
│  3. YOUR RESPONSIBILITY                                             │
│     You are solely responsible for your trading decisions.          │
│     The creator is not liable for any losses.                       │
│                                                                     │
│  4. TESTING REQUIRED                                                │
│     Always test thoroughly in paper mode before live trading.       │
│     Understand the code and strategy before using.                   │
│                                                                     │
│  5. REGULATORY COMPLIANCE                                           │
│     Ensure your algo trading complies with SEBI regulations.        │
│     Consult a financial advisor if needed.                          │
│                                                                     │
│  BY USING THIS SOFTWARE, YOU AGREE TO THESE TERMS.                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Best Practices

1. **Start Small** - Begin with minimum capital
2. **Paper Trade First** - Test for at least 2 weeks
3. **Monitor Regularly** - Don't leave bot unattended initially
4. **Keep Learning** - Understand why trades succeed or fail
5. **Have a Backup** - Be ready to intervene manually if needed

---

## 📄 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- [Angel One SmartAPI](https://smartapi.angelone.in/) - Free broker API
- [TA-Lib](https://github.com/mrjbq7/ta-lib) - Technical analysis library
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

## 📞 Support

- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Updates**: Watch the repo for updates

---

**Happy Trading!  📈**

*Remember: The goal is not to get rich quick, but to build a sustainable trading system.*