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
│  │  ₹10,000.00                 │  │  Score: 72.3  [🟡 POSITION OPEN]        │  │
│  │                             │  │                                         │  │
│  │  ─────────────────────────  │  └─────────────────────────────────────────┘  │
│  │                             │                                               │
│  │  Today's P&L                │  ┌─────────────────────────────────────────┐  │
│  │  +₹380.00 (+0.76%)          │  │         📈 OPEN POSITIONS                │  │
│  │  ███████████░░░░ 76%        │  │  ─────────────────────────────────────  │  │
│  │                             │  │                                         │  │
│  │  Daily Loss Limit           │  │  ┌─────────────────────────────────────┐│  │
│  │  ₹1,000 remaining           │  │  │ TATAMOTORS-EQ                       ││  │
│  │  ░░░░░░░░░░░░░░░░ 0% used   │  │  │ ───────────────────────────────────  ││  │
│  │                             │  │  │ BUY @ ₹650. 00  |  Qty: 30            ││  │
│  └─────────────────────────────┘  │  │ Current:  ₹653.50                     ││  │
│                                   │  │ P&L: +₹105.00 (+0.54%)               ││  │
│  ┌─────────────────────────────┐  │  │                                      ││  │
│  │      ⚙️ QUICK CONFIG        │  │  │ Target: ₹656.50  SL: ₹646.75        ││  │
│  │  ─────────────────���───────  │  │  │ [━━━━━━━━━░░░░░░] 54% to target     ││  │
│  │                             │  │  │                                      ││  │
│  │  Stop Loss %                │  │  │ [🔴 EXIT NOW]                        ││  │
│  │  [  0.5  ] [▼]              │  │  └─────────────────────────────────────┘│  │
│  │                             │  │                                         │  │
│  │  Target %                   │  └─────────────────────────────────────────┘  │
│  │  [  1.0  ] [▼]              │                                               │
│  │                             │  ┌─────────────────────────────────────────┐  │
│  │  Max Trades                 │  │         📊 TODAY'S TRADES                │  │
│  │  [  3  ] [▼]                │  │  ─────────────────────────────────────  │  │
│  │                             │  │                                         │  │
│  │  Trading Mode               │  │  # STOCK      BUY      SELL    P&L  ST │  │
│  │  [◉ Paper] [○ Live]         │  │  ─────────────────────────────────────  │  │
│  │                             │  │  1 RELIANCE  ₹2,448  ₹2,473  +₹485 ✅  │  │
│  │  [💾 Save Changes]          │  │  2 TATAMTR   ₹650    ---     +₹105 🟡  │  │
│  │                             │  │                                         │  │
│  └─────────────────────────────┘  │  Total P&L: +₹590.00                    │  │
│                                   │  Win Rate: 100% (1/1)                   │  │
│                                   └─────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                           📜 ACTIVITY LOG                                 │  │
│  │  ────────────────────────────────────────────���───────────────────────────│  │
│  │                                                                          │  │
│  │  09:45:32 │ TRADE    │ BUY 30 TATAMOTORS @ ₹650.00 | SL:  ₹646.75        │  │
│  │  09:45:30 │ SIGNAL   │ Entry signal detected for TATAMOTORS              │  │
│  │  09:35:00 │ SYSTEM   │ Monitoring started for RELIANCE, TATAMOTORS       │  │
│  │  09:15:00 │ SYSTEM   │ Market opened - WebSocket connected               │  │
│  │  09:00:00 │ ANALYSIS │ Stocks selected: RELIANCE (78.5), TATAMTR (72.3)  │  │
│  │  08:30:00 │ SYSTEM   │ Pre-market analysis started                       │  │
│  │  08:30:00 │ SYSTEM   │ Trading bot started in PAPER mode                 │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────��─────────────────────────────────────────────────────────────────────┐│
│  │ [▶️ START]   [⏸️ PAUSE]   [⏹️ STOP]   [🔄 REFRESH]   [⚙️ FULL SETTINGS]  ││
│  └────────────────────────────────────────────────────────────────────────────┘│
│                                                                                 │
└───────────────��─────────────────────────────────────────────────────────────────┘
```

### Dashboard Components Breakdown

#### 1. Header Section
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 INTRADAY TRADING BOT              [🟢 RUNNING]  [PAPER]     09:45:32 AM     │
├─────────────────────────────────────────────────────────────────────────────────┤

Components:
├── Logo/Title:  "INTRADAY TRADING BOT"
├── Status Badge: [🟢 RUNNING] / [🟡 PAUSED] / [🔴 STOPPED] / [⚪ READY]
├── Mode Badge: [PAPER] / [LIVE]
└── Current Time: Real-time clock (updates every second)
```

#### 2. Account Info Panel
```
┌─────────────────────────────────┐
│      💰 ACCOUNT INFO            │
│  ─────────────────────────────  │
│                                 │
│  Total Balance                  │
│  ₹50,380.00                     │  ← Fetched from broker/paper trader
│                                 │
│  Available                      │
│  ₹40,380.00                     │  ← Total - Used Margin
│                                 │
│  Used Margin                    │
│  ₹10,000.00                     │  ← Currently in positions
│                                 │
│  ─────────────────────────────  │
│                                 │
│  Today's P&L                    │
│  +₹380.00 (+0.76%)              │  ← Green if positive, Red if negative
│  ███████████░░░░░ 76%           │  ← Progress bar (% of target)
│                                 │
│  Daily Loss Limit               │
│  ₹1,000 remaining               │  ← How much loss is still allowed
│  ░░░░░░░░░░░░░░░░░ 0% used      │  ← Progress bar (% of loss limit used)
│                                 │
└─────────────────────────────────┘

Features:
├── Real-time balance updates
├── P&L with color coding (green/red)
├── Progress bars for visual feedback
└── Daily loss limit tracking
```

#### 3. Selected Stocks Panel
```
┌─────────────────────────────────────────────────────────────────┐
│         📋 TODAY'S SELECTED STOCKS                              │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  STOCK      LTP        ENTRY      TARGET     STOP-LOSS         │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  RELIANCE   ₹2,450. 00  ₹2,448.00  ₹2,472.48  ₹2,435.76         │
│  Score: 78.5  [🟢 WATCHING]                                     │
│                                                                 │
│  TATAMTR    ₹653.50    ₹650.00    ₹656.50    ₹646.75           │
│  Score: 72.3  [🟡 POSITION OPEN]                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Status Icons:
├── 🟢 WATCHING     = Monitoring for entry signal
├── 🟡 POSITION OPEN = Currently holding position
├── ✅ COMPLETED    = Trade completed (target/SL hit)
└── ⚪ WAITING      = Not yet analyzed

Features:
├── Real-time LTP updates
├── Pre-calculated entry, target, stop-loss
├── Score from pre-market analysis
└── Current status of each stock
```

#### 4. Open Positions Panel
```
┌─────────────────────────────────────────────────────────────────┐
│         📈 OPEN POSITIONS                                       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  ┌──────────────────────────────────────────────���──────────┐   │
│  │ TATAMOTORS-EQ                                            │   │
│  │ ─────────────────────────────────────────────────────── │   │
│  │ BUY @ ₹650.00  |  Qty: 30  |  Value: ₹19,500            │   │
│  │                                                          │   │
│  │ Current Price: ₹653.50                                   │   │
│  │ Unrealized P&L: +₹105.00 (+0.54%)                        │   │
│  │                                                          │   │
│  │ Target: ₹656.50          Stop-Loss: ₹646.75             │   │
│  │ [━━━━━━━━━░░░░░░░░░░░░] 54% to target                   │   │
│  │                                                          │   │
│  │ Entry Time: 09:45:32                                     │   │
│  │                                                          │   │
│  │        [🔴 EXIT NOW]        [✏️ MODIFY SL/TGT]           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  No more open positions                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Features:
├── Real-time price and P&L updates
├── Progress bar showing distance to target
├── Manual exit button for emergency
├── Modify SL/Target option
└── Entry time tracking
```

#### 5. Quick Config Panel
```
┌─────────────────────────────────┐
│      ⚙️ QUICK CONFIG            │
│  ─────────────────────────────  │
│                                 │
│  Stop Loss %                    │
│  ┌─────────────────────────┐   │
│  │  0.5               [▼]  │   │  ← Dropdown:  0.5, 0.75
│  └─────────────────────────┘   │
│                                 │
│  Target %                       │
│  ┌─────────────────────────┐   │
│  │  1.0               [▼]  │   │  ← Dropdown: 1.0, 1.25, 1.5
│  └─────────────────────────┘   │
│                                 │
│  Max Trades/Day                 │
│  ┌─────────────────────────┐   │
│  │  3                 [▼]  │   │  ← Dropdown: 1-5
│  └─────────────────────────┘   │
│                                 │
│  Trading Mode                   │
│  ┌─────────────────────────┐   │
│  │ (◉) Paper   (○) Live    │   │  ← Radio buttons
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │   💾 Save Changes       │   │  ← Save button
│  └─────────────────────────┘   │
│                                 │
└───────��─────────────────────────┘

Features:
├── Quick access to common settings
├── Instant updates (no page reload)
├── Mode switch with confirmation
└── Changes take effect immediately
```

#### 6. Today's Trades Panel
```
┌─────────────────────────────────────────────────────────────────┐
│         📊 TODAY'S TRADES                                       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  #   STOCK       BUY        SELL       P&L         STATUS      │
│  ─────���───────────────────────────────────────────────────────  │
│  1   RELIANCE    ₹2,448.50  ₹2,472.75  +₹485.00    ✅ TARGET   │
│  2   TATAMTR     ₹650.00    ---        +₹105.00    🟡 OPEN     │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Summary:                                                       │
│  ├── Total Trades: 2 (1 closed, 1 open)                         │
│  ├── Total P&L: +₹590.00                                        │
│  ├── Win Rate: 100% (1 wins / 1 closed)                         │
│  └── Largest Win: +₹485.00 | Largest Loss: ₹0.00                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Status Icons:
├── ✅ TARGET     = Exited at target price
├── 🛑 STOP_LOSS = Exited at stop-loss
├── 🟡 OPEN      = Still holding
├── ⏰ SQUARE_OFF = Forced exit at 3: 15 PM
└── 🔵 MANUAL    = Manually exited

Features:
├── Complete trade history for today
├── Real-time P&L tracking
├── Win rate calculation
└── Summary statistics
```

#### 7. Activity Log Panel
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           📜 ACTIVITY LOG                                     │
│  ──────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  TIME      │ CATEGORY │ MESSAGE                                              │
│  ──────────────────────────────────────────────────────────────────────────  │
│  09:45:32  │ TRADE    │ BUY 30 TATAMOTORS @ ₹650.00 | SL: ₹646.75           │
│  09:45:30  │ SIGNAL   │ Entry signal detected for TATAMOTORS                 │
│  09:35:00  │ SYSTEM   │ Monitoring started for RELIANCE, TATAMOTORS          │
│  09:15:00  │ SYSTEM   │ Market opened - WebSocket connected                  │
│  09:00:00  │ ANALYSIS │ Stocks selected: RELIANCE (78.5), TATAMTR (72.3)     │
│  08:30:00  │ SYSTEM   │ Pre-market analysis started                          │
│  08:30:00  │ SYSTEM   │ Trading bot started in PAPER mode                    │
│                                                                              │
│                            [Load More ▼]                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Category Colors:
├── SYSTEM   = Blue      (Bot operations)
├── TRADE    = Green     (Buy/Sell orders)
├── SIGNAL   = Yellow    (Entry/Exit signals)
├── ANALYSIS = Purple    (Stock analysis)
├── ERROR    = Red       (Errors/Warnings)
└── CONFIG   = Gray      (Configuration changes)

Features:
├── Real-time log updates
├── Color-coded categories
├── Scrollable with load more
└── Newest entries at top
```

#### 8. Control Buttons Panel
```
┌────────────────────────────────────────────────────────────────────────────────┐
│ [▶️ START]   [⏸️ PAUSE]   [⏹️ STOP]   [🔄 REFRESH]   [⚙️ FULL SETTINGS]      │
└───────────────���────────────────────────────────────────────────────────────────┘

Buttons:
├── ▶️ START       = Start the trading bot
│   └── Disabled when running
├── ⏸️ PAUSE       = Pause trading (keep monitoring)
│   └── Shows "RESUME" when paused
├── ⏹️ STOP        = Stop bot and square off positions
│   └── Confirmation required
├── 🔄 REFRESH     = Manually refresh all data
│   └── Useful if WebSocket disconnects
└── ⚙️ SETTINGS    = Open full settings modal
    └── Advanced configuration

Button States:
├── STOPPED  → START enabled, others disabled
├── RUNNING  → PAUSE, STOP enabled, START disabled
├── PAUSED   → RESUME, STOP enabled
```

### Full Settings Modal

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ⚙️ FULL SETTINGS                             [✕]     │
├────────��────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─── TABS ─────────────────────────────────────────────────────────────────┐  │
│  │ [Capital] [Stock Selection] [Strategy] [Risk] [Timing] [Alerts]          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                           💰 CAPITAL SETTINGS                                   │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  Capital Allocation                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ (◉) Use Percentage of Balance    (○) Use Fixed Amount                   │   │
│  └──────────────────���──────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Trading Capital Percentage                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ [━━━━━━━━━━━●━━━━━━━━━] 50%                                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│  Use 50% of total balance for trading.  Rest stays as buffer.                   │
│                                                                                 │
│  Per Trade Allocation                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ (◉) Percentage: [25] % of trading capital                                │   │
│  │ (○) Fixed Amount: ₹ [_____]                                              │   │
│  └────────────────────────────────────────────────────────────���────────────┘   │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│                    [Cancel]                    [💾 Save All Settings]          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Responsive Design (Mobile View)

```
┌──────────────────────────────────┐
│ 📊 TRADING BOT    [🟢] [PAPER]   │
├──────────────────────────────────┤
│                                  │
│  ┌────────────────────────────┐  │
│  │ 💰 Balance: ₹50,380        │  │
│  │ P&L: +₹380 (+0.76%)       │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │ 📋 SELECTED STOCKS         │  │
│  │ ────────────────────────── │  │
│  │ RELIANCE    ₹2,450  🟢     │  │
│  │ TATAMTR     ₹653    🟡     │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │ 📈 OPEN POSITION           │  │
│  │ ────────────────────────── │  │
│  │ TATAMTR                    │  │
│  │ BUY ₹650 → ₹653.50        │  │
│  │ P&L: +₹105 (+0.54%)       │  │
│  │ [━━━━━░░░░] 54%           │  │
│  │ [EXIT]                     │  │
│  └────────────────────────────┘  │
│                                  │
│  ┌────────────────────────────┐  │
│  │ 📜 ACTIVITY LOG            │  │
│  │ ────────────────────────── │  │
│  │ 09:45 BUY TATAMTR ₹650    │  │
│  │ 09:35 Monitoring started   │  │
│  │ 09:15 Market opened        │  │
│  └────────────────────────────┘  │
│                                  │
│  [▶️][⏸️][⏹️][🔄][⚙️]           │
│                                  │
└──────────────────────────────────┘
```

### Color Scheme

```
┌─────────────────────────────────────────────────────────────────┐
│                      COLOR PALETTE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Primary Colors:                                                 │
│  ├── Background:      #1a1a2e (Dark Navy)                        │
│  ├── Card Background: #16213e (Darker Navy)                     │
│  ├── Primary Accent:   #0f3460 (Navy Blue)                       │
│  └── Text Primary:    #ffffff (White)                           │
│                                                                 │
│  Status Colors:                                                  │
│  ├── Success/Profit:   #00ff88 (Bright Green)                    │
│  ├── Error/Loss:      #ff4757 (Red)                             │
│  ├── Warning:         #ffa502 (Orange)                          │
│  ├── Info:            #3498db (Blue)                            │
│  └── Neutral:         #a0a0a0 (Gray)                            │
│                                                                 │
│  Button Colors:                                                  │
│  ├── Start:            #00b894 (Green)                           │
│  ├── Pause:           #fdcb6e (Yellow)                          │
│  ├── Stop:            #d63031 (Red)                             │
│  └── Settings:        #6c5ce7 (Purple)                          │
│                                                                 │
│  Mode Badges:                                                    │
│  ├── Paper Mode:      #00cec9 (Cyan)                            │
│  └── Live Mode:       #e17055 (Coral/Orange)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### CSS Variables

```css
:root {
  /* Background Colors */
  --bg-primary: #1a1a2e;
  --bg-secondary:  #16213e;
  --bg-card: #0f3460;
  
  /* Text Colors */
  --text-primary: #ffffff;
  --text-secondary: #a0a0a0;
  --text-muted: #6c7a89;
  
  /* Status Colors */
  --color-success: #00ff88;
  --color-error: #ff4757;
  --color-warning: #ffa502;
  --color-info: #3498db;
  
  /* Button Colors */
  --btn-start: #00b894;
  --btn-pause: #fdcb6e;
  --btn-stop: #d63031;
  --btn-settings: #6c5ce7;
  
  /* Mode Colors */
  --mode-paper:  #00cec9;
  --mode-live: #e17055;
  
  /* Borders & Shadows */
  --border-color: #2d3436;
  --shadow-color: rgba(0, 0, 0, 0.3);
  
  /* Fonts */
  --font-family:  'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  --font-mono: 'Consolas', 'Monaco', monospace;
  
  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

---

## 📄 File Descriptions

### Root Files

| File | Description |
|------|-------------|
| `.env` | API credentials and environment variables.  **Never commit this! ** |
| `.env.example` | Template for .env file with placeholder values |
| `.gitignore` | Specifies files to exclude from git tracking |
| `README.md` | Main project documentation |
| `ARCHITECTURE.md` | This file - technical architecture details |
| `requirements.txt` | Python dependencies list |
| `run.py` | Main entry point - starts bot and dashboard |

### Config Files

| File | Description |
|------|-------------|
| `config/settings.json` | User-editable settings (persisted) |
| `config/nifty50.json` | Nifty 50 stock symbols and tokens |
| `config/defaults.py` | Default configuration values |

### Source Files - Core

| File | Description |
|------|-------------|
| `src/core/config_manager.py` | Load/save/manage configuration |
| `src/core/bot. py` | Main bot orchestrator |
| `src/core/scheduler.py` | Time-based task scheduling |

### Source Files - Broker

| File | Description |
|------|-------------|
| `src/broker/angel_client.py` | Angel One REST API wrapper |
| `src/broker/websocket_client.py` | Real-time WebSocket client |
| `src/broker/paper_trader.py` | Paper trading simulator |

### Source Files - Analysis

| File | Description |
|------|-------------|
| `src/analysis/indicators.py` | Technical indicator calculations |
| `src/analysis/stock_scorer.py` | Stock scoring algorithm |
| `src/analysis/pre_market. py` | Pre-market analysis logic |

### Source Files - Strategy

| File | Description |
|------|-------------|
| `src/strategy/base_strategy.py` | Strategy interface (abstract) |
| `src/strategy/vwap_rsi_strategy.py` | VWAP + RSI strategy implementation |
| `src/strategy/risk_manager.py` | Risk management and position sizing |

### Source Files - Executor

| File | Description |
|------|-------------|
| `src/executor/order_manager.py` | Order placement and tracking |
| `src/executor/position_tracker.py` | Open position tracking |

### Source Files - API

| File | Description |
|------|-------------|
| `src/api/server.py` | Flask REST API server |

### Dashboard Files

| File | Description |
|------|-------------|
| `dashboard/index.html` | Main dashboard HTML structure |
| `dashboard/styles.css` | Dashboard styling (CSS) |
| `dashboard/app.js` | Frontend JavaScript logic |

### Data Files

| Directory | Description |
|-----------|-------------|
| `data/daily/` | Daily price tick logs (JSON) |
| `data/trades/` | Trade history by date (JSON) |
| `data/reports/` | Daily summary reports (JSON) |
| `logs/` | Application logs |

---

## 🛠️ Technology Stack

### Backend (Python)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9+ | Core programming language |
| Flask | 3.0+ | REST API server |
| Flask-CORS | 4.0+ | Cross-origin requests |
| SmartAPI-Python | 1.3+ | Angel One API client |
| PyOTP | 2.9+ | TOTP generation for auth |
| Pandas | 2.0+ | Data manipulation |
| NumPy | 1.24+ | Numerical computations |
| TA (Technical Analysis) | 0.11+ | Technical indicators |
| Schedule | 1.2+ | Task scheduling |
| Loguru | 0.7+ | Logging |
| Python-dotenv | 1.0+ | Environment variables |
| WebSocket-client | 1.6+ | WebSocket support |

### Frontend (Vanilla JS)

| Technology | Purpose |
|------------|---------|
| HTML5 | Page structure |
| CSS3 | Styling (custom, no framework) |
| Vanilla JavaScript | Interactivity |
| Fetch API | HTTP requests |
| WebSocket API | Real-time updates (optional) |

### Data Storage

| Technology | Purpose |
|------------|---------|
| JSON Files | Configuration and data storage |
| File System | Local storage for logs and reports |

### Development Tools

| Tool | Purpose |
|------|---------|
| VS Code | Recommended IDE |
| Git | Version control |
| Virtual Environment | Python dependency isolation |

---

## 📅 Development Phases

### Phase 1: Foundation (Week 1)
```
✅ Project structure setup
✅ Configuration system (JSON based)
✅ Angel One API connection
✅ Basic authentication
✅ Paper trading mode toggle
✅ Logging system
```

### Phase 2: Data & Analysis (Week 2)
```
✅ Fetch Nifty 50 stock list
✅ Get historical data (OHLCV)
✅ Calculate indicators (RSI, VWAP)
✅ Stock scoring algorithm
✅ Pre-market analysis
✅ Stock selection (top 2)
```

### Phase 3: Strategy & Execution (Week 3)
```
✅ VWAP + RSI strategy implementation
✅ Entry signal detection
✅ Exit signal detection
✅ Stop-loss management
✅ Target management
✅ Position sizing (risk-based)
✅ Order placement (paper mode)
```

### Phase 4: Real-time Monitoring (Week 4)
```
✅ WebSocket integration
✅ Real-time price updates
✅ Position tracking
✅ Automatic trade execution
✅ Daily scheduler
✅ Square-off at 3: 15 PM
✅ Daily report generation
```

### Phase 5: Dashboard UI (Week 5)
```
✅ HTML dashboard structure
✅ CSS styling (dark theme)
✅ JavaScript API integration
✅ Real-time data display
✅ Configuration panel
✅ Trade history
✅ Activity log
✅ Control buttons
```

### Phase 6: Testing & Polish (Week 6)
```
✅ Paper trading tests
✅ Error handling improvements
✅ Edge case handling
✅ Performance optimization
✅ Documentation updates
✅ Final testing
```

---

## 🔒 Security Considerations

### API Credentials
```
1.  NEVER commit . env file to git
2. Use environment variables for all secrets
3. Rotate API keys periodically
4. Keep TOTP secret secure
```

### Dashboard Security
```
1. Dashboard runs on localhost only (127.0.0.1)
2. No authentication needed (local access only)
3. Don't expose port 5000 to internet
4. Use HTTPS if deploying remotely (not recommended)
```

### Trading Security
```
1. Start with paper trading mode
2. Set conservative risk limits
3. Use daily loss limits
4. Never risk more than you can afford
5. Monitor bot regularly
```

---

## 📈 Future Enhancements

### Planned Features
```
├── Multiple strategy support
├── Backtesting module
├── Email/SMS alerts
├── Telegram bot integration
├── Multi-broker support
├── Options trading support
├── Advanced charting in dashboard
├── Historical performance analytics
├── Machine learning signal enhancement
└── Mobile app (React Native)
```

### Performance Improvements
```
├── Redis for caching
├── PostgreSQL for data storage
├── WebSocket for dashboard updates
├── Async/await for API calls
└── Multi-threading for analysis
```

---

## 📞 Support & Resources

### Documentation
- [Angel One SmartAPI Docs](https://smartapi.angelone.in/docs)
- [TA-Lib Documentation](https://technical-analysis-library-in-python.readthedocs. io/)
- [Flask Documentation](https://flask.palletsprojects.com/)

### Community
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Stack Overflow for technical help

---

**End of Architecture Document**

*Last Updated: January 2024*
*Version: 1.0.0*