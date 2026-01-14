# 📈 Intraday Trading Bot

An automated trading bot for Indian stock market (NSE) using **VWAP + RSI strategy**.

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      DAILY WORKFLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   8:30 AM   →  Analyze 50 Nifty stocks                         │
│                Score by: Volatility + Volume + Trend + RSI      │
│                Select top 2 stocks                              │
│                                                                 │
│   9:15 AM   →  Start live monitoring via WebSocket              │
│                                                                 │
│   9:30 AM   →  Trading begins                                   │
│      ↓         Wait for VWAP crossover signal                   │
│      ↓         Entry: Price crosses ABOVE VWAP                  │
│      ↓         + RSI in 40-60 range                             │
│      ↓         + Volume > Average                               │
│                                                                 │
│   During     → Monitor positions                                │
│   Market       Exit on: Target hit (ATR-based)                  │
│                        Stop Loss hit (ATR-based)                │
│                        RSI > 70 (overbought)                    │
│                                                                 │
│   3:15 PM   →  Square off all positions                         │
│                                                                 │
│   3:30 PM   →  Generate daily report                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env with your Angel One credentials

# 3. Run
python run.py
```

## 📊 Dashboard

Open `http://localhost:5000` to view:
- Selected stocks
- Live positions
- Today's P&L
- Activity logs

## ⚙️ Configuration

Edit `config/settings.json`:
- `max_stocks`: Number of stocks to trade (default: 2)
- `paper_trading`: true/false
- `max_daily_loss_percent`: Daily loss limit

## 🎯 Strategy Summary

| Component | Logic |
|-----------|-------|
| **Stock Selection** | Top scorer by ATR + Volume + Trend + RSI |
| **Entry** | VWAP Crossover + RSI 40-60 + Volume confirmation |
| **Stop Loss** | Entry - 2×ATR (dynamic) |
| **Target** | Entry + 4×ATR (dynamic) |
| **Exit** | Target/SL hit OR RSI > 70 OR 3:15 PM |

## ⚠️ Disclaimer

This bot is for educational purposes. Use at your own risk. Always test with paper trading first.
