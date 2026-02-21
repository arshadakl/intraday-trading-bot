# Three-Minute Breakout Strategy — Rules Document

> This document defines the exact trading rules implemented in the bot.
> Any code behavior that deviates from this document is a bug.

---

## 1. Pre-Market Preparation (Before 9:15 AM)

- Maintain two ranked lists from Nifty 50 pre-open data:
  - **Top 4 stocks**: Sorted by gap_percent descending (highest positive gap first)
  - **Bottom 4 stocks**: Sorted by gap_percent ascending (most negative gap first)
- Stock ranking is sourced from NSE pre-open API at ~9:10 AM.
- **Do NOT** move stocks to the active watchlist until gap classification is complete.

---

## 2. Gap Classification (Exactly at 9:15 AM)

At market open, compare **Nifty 50 index open price** with its **previous day close**:

```
gap_percent = ((open_price - prev_close) / prev_close) * 100
```

| Condition | Classification |
|---|---|
| `gap_percent > +0.2%` | **GAP_UP** |
| `gap_percent < -0.2%` | **GAP_DOWN** |
| `-0.2% ≤ gap_percent ≤ +0.2%` | **FLAT** |

- The threshold `0.2%` is configurable via `gap_threshold_percent`.
- Classification runs **once per day** and **never changes** after being set.

---

## 3. Stock Selection Based on Gap

After gap classification, select stocks from the ranked lists:

| Gap Type | Stocks Selected | Direction | Count |
|---|---|---|---|
| GAP_UP | Top ranked stocks | **SHORT** | `maxTrades` (default 2) |
| GAP_DOWN | Bottom ranked stocks | **LONG** | `maxTrades` (default 2) |
| FLAT | Top stocks → SHORT, Bottom stocks → LONG | **MIXED** | `maxTrades` split evenly |

- `maxTrades` is configurable (default = 2).
- Selected stocks are moved to the active watchlist with their assigned direction.
- Direction is **locked** — once set, a stock's direction cannot change for the day.

---

## 4. Reference Candle (9:15 – 9:18)

The bot operates on a **3-minute timeframe**.

- The first 3-minute candle spans **9:15:00 to 9:17:59** (closes at 9:18:00).
- This is the **reference candle**.
- After 9:18, record:
  - `reference_high` = highest price during 9:15–9:18
  - `reference_low` = lowest price during 9:15–9:18

**No trades are allowed before the reference candle completes (before 9:18).**

---

## 5. Entry Conditions (Break & Close Rule)

Entry is based on **3-minute candle close**, not tick price or wick:

### For LONG trades (gap-down case):
- Wait until a **full 3-minute candle closes above** `reference_high`.
- Enter at the close price of that breakout candle.

### For SHORT trades (gap-up case):
- Wait until a **full 3-minute candle closes below** `reference_low`.
- Enter at the close price of that breakout candle.

### Rules:
- ❌ Wick breaks do NOT count — only the candle **close** matters.
- ❌ No blind entries — breakout confirmation is mandatory.
- ✅ Monitoring happens strictly at 3-minute candle close events (9:18, 9:21, 9:24, 9:27, ...).

---

## 6. Stop-Loss Rules

There are two stop-loss modes:

### Normal Case
If the reference candle range is ≤ `large_candle_percent` (default 1%):

| Direction | Stop-Loss |
|---|---|
| LONG | `reference_low` |
| SHORT | `reference_high` |

### Large Candle Case
If the reference candle range > `large_candle_percent`:

```
candle_range_percent = ((reference_high - reference_low) / reference_low) * 100
```

| Direction | Stop-Loss |
|---|---|
| LONG | `entry_price × (1 - 0.01)` → 1% below entry |
| SHORT | `entry_price × (1 + 0.01)` → 1% above entry |

This prevents excessive risk on volatile openings.

---

## 7. Target Rules

- Target is **percentage-based** (configurable, default = 1%).
- Calculated from entry price:

| Direction | Target |
|---|---|
| LONG | `entry_price × (1 + target_percent / 100)` |
| SHORT | `entry_price × (1 - target_percent / 100)` |

- No dynamic trailing — simple fixed target.
- Target is checked on every tick (not just candle close) for faster execution.

---

## 8. Exit Conditions

A position is exited when **any** of these conditions is met:

1. **Target hit**: Current price reaches or exceeds the target.
2. **Stop-loss hit**: Current price reaches or breaches the stop-loss.
3. **Market close**: All positions are squared off at 3:15 PM IST.

Exit is checked on every price tick for responsive execution.

---

## 9. Execution Restrictions

| Rule | Enforcement |
|---|---|
| No blind entry | Entry only on 3-min candle close breakout confirmation |
| One trade per stock per day | `_completed_stocks` set tracks traded symbols |
| No re-entry after SL/target | Stock added to `_completed_stocks` on exit |
| No direction change | Direction is locked at stock selection time |
| Trade only watchlist stocks | Only selected stocks receive price updates |
| 3-minute timeframe only | Entry signals generated only on 3-min candle close |
| `maxTrades` limit | Risk manager enforces daily trade count |

---

## 10. Daily Workflow Summary

```
┌─────────────────────────────────────────────────┐
│  ~9:10 AM  │  Fetch Nifty 50 pre-open data      │
│            │  Rank stocks: Top 4 + Bottom 4      │
├────────────┼─────────────────────────────────────┤
│  9:15 AM   │  Market opens                       │
│            │  Classify Nifty gap (UP/DOWN/FLAT)   │
│            │  Select stocks + assign direction    │
│            │  Start building reference candle     │
├────────────┼─────────────────────────────────────┤
│  9:18 AM   │  Reference candle complete           │
│            │  Record reference high & low         │
│            │  Begin monitoring for breakout       │
├────────────┼─────────────────────────────────────┤
│ 9:18–3:00  │  On each 3-min candle close:         │
│            │    Check breakout condition           │
│            │    Enter if confirmed                 │
│            │  On each tick (if in position):       │
│            │    Check SL / Target                  │
├────────────┼─────────────────────────────────────┤
│  3:00 PM   │  No new entries allowed              │
├────────────┼─────────────────────────────────────┤
│  3:15 PM   │  Square off all open positions       │
├────────────┼─────────────────────────────────────┤
│  3:30 PM   │  Market closes                       │
│            │  Generate daily report               │
└─────────────────────────────────────────────────┘
```

---

## 11. Configuration Parameters

| Parameter | Default | Description |
|---|---|---|
| `max_trades_per_day` | `2` | Maximum trades per day across all stocks |
| `gap_threshold_percent` | `0.2` | Min gap % to classify as GAP_UP or GAP_DOWN |
| `large_candle_percent` | `1.0` | Reference candle range threshold for SL mode |
| `target_percent` | `1.0` | Target as % from entry price |
| `stop_loss_percent` | `1.0` | Fixed SL % (used only for large candle case) |
| `stocks_per_side` | `4` | Number of stocks to rank per side (top/bottom) |

---

## 12. What This Strategy Does NOT Do

- ❌ No trailing stop-loss
- ❌ No indicator-based entry (no RSI, VWAP, EMA signals)
- ❌ No scaling in/out of positions
- ❌ No reversal trades (direction is fixed per stock)
- ❌ No overnight positions (strictly intraday)
