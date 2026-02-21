"""
Backtest Engine for Three-Minute Breakout Strategy

Standalone module — no imports from bot.py or live strategy.
Replays historical 3-minute candle data through the strategy rules
defined in STRATEGY_RULES.md.

Usage:
    engine = BacktestEngine(config)
    result = engine.run(nifty_candles, all_stock_candles)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


# --- Constants (mirrored from strategy, not imported) ---
MARKET_OPEN = time(9, 15)
REFERENCE_CANDLE_END = time(9, 18)
NO_NEW_ENTRY_AFTER = time(15, 0)
SQUARE_OFF_TIME = time(15, 15)


@dataclass
class BacktestTrade:
    """A single simulated trade."""
    symbol: str
    direction: str          # "LONG" or "SHORT"
    entry_price: float
    entry_time: str
    exit_price: float = 0.0
    exit_time: str = ""
    exit_reason: str = ""   # "TARGET", "STOP_LOSS", "SQUARE_OFF"
    stop_loss: float = 0.0
    target: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    # Reference candle data
    ref_high: float = 0.0
    ref_low: float = 0.0
    ref_open: float = 0.0
    ref_close: float = 0.0
    ref_range_percent: float = 0.0
    is_large_candle: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": round(self.entry_price, 2),
            "entry_time": self.entry_time,
            "exit_price": round(self.exit_price, 2),
            "exit_time": self.exit_time,
            "exit_reason": self.exit_reason,
            "stop_loss": round(self.stop_loss, 2),
            "target": round(self.target, 2),
            "pnl": round(self.pnl, 2),
            "pnl_percent": round(self.pnl_percent, 2),
            "reference_candle": {
                "high": round(self.ref_high, 2),
                "low": round(self.ref_low, 2),
                "open": round(self.ref_open, 2),
                "close": round(self.ref_close, 2),
                "range_percent": round(self.ref_range_percent, 2),
                "is_large_candle": self.is_large_candle,
            },
        }


@dataclass
class BacktestResult:
    """Complete results of a single-day backtest."""
    date: str
    nifty_gap: Dict = field(default_factory=dict)
    selected_stocks: List[Dict] = field(default_factory=list)
    all_ranked_stocks: List[Dict] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    candle_data: Dict = field(default_factory=dict)
    # Stocks that were in watchlist but didn't trigger entry
    no_entry_stocks: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "nifty_gap": self.nifty_gap,
            "selected_stocks": self.selected_stocks,
            "all_ranked_stocks": self.all_ranked_stocks,
            "trades": [t.to_dict() for t in self.trades],
            "no_entry_stocks": self.no_entry_stocks,
            "summary": self.summary,
            "candle_data": self.candle_data,
        }

    def to_full_report(self) -> dict:
        """Generate full report dict for JSON file export (manual verification)."""
        report = {
            "backtest_date": self.date,
            "generated_at": datetime.now().isoformat(),
            "strategy": "3-Minute Breakout",
            "nifty_gap_analysis": self.nifty_gap,
            "stock_ranking": {
                "total_stocks_ranked": len(self.all_ranked_stocks),
                "all_stocks": self.all_ranked_stocks,
            },
            "watchlist": {
                "selected_count": len(self.selected_stocks),
                "stocks": self.selected_stocks,
            },
            "trade_results": {
                "summary": self.summary,
                "trades": [t.to_dict() for t in self.trades],
                "no_entry_stocks": self.no_entry_stocks,
            },
            "raw_candle_data": self.candle_data,
        }
        return report


class BacktestEngine:
    """
    Replays the 3-minute breakout strategy against historical candle data.

    This engine is self-contained and does NOT import any live trading code.
    It reimplements the strategy rules purely from candle data.
    """

    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        params = config.get("strategies", {}).get("three_minute", {}).get("params", {})

        self.gap_threshold_percent = float(params.get("gap_threshold_percent", 0.2))
        self.large_candle_percent = float(params.get("large_candle_percent", 1.0))
        self.stop_loss_percent = float(params.get("stop_loss_percent", 1.0))
        self.target_percent = float(params.get("target_percent", 1.0))
        self.max_trades_per_day = int(params.get("max_trades_per_day", 2))

    def run(
        self,
        date_str: str,
        nifty_candles: List[Dict],
        all_stock_candles: Dict[str, List[Dict]],
        stock_list: List[Dict],
    ) -> BacktestResult:
        """
        Run backtest for a single day.

        Args:
            date_str: Date being backtested (YYYY-MM-DD)
            nifty_candles: 3-min candles for Nifty 50 index on that date
            all_stock_candles: {symbol: [candles]} for all Nifty 50 stocks
            stock_list: List of stock dicts with 'symbol', 'token', etc.

        Returns:
            BacktestResult with trades, P&L, and summary
        """
        result = BacktestResult(date=date_str)

        # === Step 1: Classify Nifty gap ===
        nifty_gap = self._classify_nifty_gap(nifty_candles)
        result.nifty_gap = nifty_gap

        if not nifty_gap.get("valid"):
            result.summary = self._build_summary([], "No valid Nifty data")
            return result

        # === Step 2: Rank stocks by gap and select candidates ===
        ranked_stocks = self._rank_stocks_by_gap(all_stock_candles, stock_list)
        result.all_ranked_stocks = ranked_stocks
        selected = self._select_stocks(ranked_stocks, nifty_gap)
        result.selected_stocks = selected

        if not selected:
            result.summary = self._build_summary([], "No stocks selected")
            return result

        # === Step 3: Simulate trades for each selected stock ===
        trades = []
        no_entry_stocks = []

        for stock_info in selected:
            symbol = stock_info["symbol"]
            direction = stock_info["direction"]
            candles = all_stock_candles.get(symbol, [])

            if not candles:
                no_entry_stocks.append({
                    "symbol": symbol,
                    "direction": direction,
                    "reason": "No candle data available",
                })
                continue

            trade, ref_info = self._simulate_stock(symbol, direction, candles)
            if trade:
                trades.append(trade)
            else:
                no_entry_stocks.append({
                    "symbol": symbol,
                    "direction": direction,
                    "reason": "No breakout signal",
                    "reference_candle": ref_info or {},
                })

        result.trades = trades
        result.no_entry_stocks = no_entry_stocks
        result.summary = self._build_summary(trades)

        # === Step 4: Attach candle data for charts ===
        result.candle_data = {
            "nifty": self._format_candles_for_chart(nifty_candles),
        }
        for stock_info in selected:
            sym = stock_info["symbol"]
            if sym in all_stock_candles:
                result.candle_data[sym] = self._format_candles_for_chart(
                    all_stock_candles[sym]
                )

        # === Step 5: Save full report to JSON ===
        self._save_report(result)

        return result

    # ================================================================
    # GAP CLASSIFICATION
    # ================================================================

    def _classify_nifty_gap(self, nifty_candles: List[Dict]) -> Dict:
        """
        Classify Nifty gap from candle data.

        Uses previous day's last candle close as prev_close,
        and current day's first candle open as open_price.
        """
        if not nifty_candles or len(nifty_candles) < 2:
            return {"valid": False, "reason": "Insufficient Nifty candle data"}

        # Parse and separate by date
        test_candles = self._parse_candles_for_test_date(nifty_candles)
        prev_close = self._find_prev_close(nifty_candles)

        if not test_candles:
            return {"valid": False, "reason": "No candles found for test date"}

        if prev_close <= 0:
            return {"valid": False, "reason": "Could not determine previous close"}

        open_price = test_candles[0]["open"]
        gap_percent = ((open_price - prev_close) / prev_close) * 100

        if gap_percent > self.gap_threshold_percent:
            gap_status = "GAP_UP"
        elif gap_percent < -self.gap_threshold_percent:
            gap_status = "GAP_DOWN"
        else:
            gap_status = "FLAT"

        # Also include first candle data for reference
        first_candle = test_candles[0]

        return {
            "valid": True,
            "gap_status": gap_status,
            "gap_percent": round(gap_percent, 2),
            "prev_close": round(prev_close, 2),
            "open_price": round(open_price, 2),
            "first_candle": {
                "open": round(first_candle["open"], 2),
                "high": round(first_candle["high"], 2),
                "low": round(first_candle["low"], 2),
                "close": round(first_candle["close"], 2),
                "timestamp": first_candle.get("timestamp", ""),
            },
        }

    def _find_prev_close(self, candles: List[Dict]) -> float:
        """Find the previous day's closing price from candle data."""
        if not candles:
            return 0.0

        parsed_candles = []
        for c in candles:
            dt = self._parse_timestamp(c.get("timestamp", ""))
            if dt:
                parsed_candles.append((dt, c))

        if not parsed_candles:
            return 0.0

        parsed_candles.sort(key=lambda x: x[0])
        test_date = parsed_candles[-1][0].date()

        # Find last candle from the previous day
        prev_day_candles = [
            (dt, c) for dt, c in parsed_candles if dt.date() < test_date
        ]

        if prev_day_candles:
            return prev_day_candles[-1][1]["close"]

        return 0.0

    # ================================================================
    # STOCK RANKING & SELECTION
    # ================================================================

    def _rank_stocks_by_gap(
        self, all_stock_candles: Dict[str, List[Dict]], stock_list: List[Dict]
    ) -> List[Dict]:
        """Rank all stocks by their opening gap percentage."""
        ranked = []

        for stock in stock_list:
            symbol = stock.get("symbol", "")
            candles = all_stock_candles.get(symbol, [])
            if not candles:
                continue

            prev_close = self._find_prev_close(candles)
            if prev_close <= 0:
                continue

            test_candles = self._parse_candles_for_test_date(candles)
            if not test_candles:
                continue

            open_price = test_candles[0]["open"]
            gap_pct = ((open_price - prev_close) / prev_close) * 100

            ranked.append({
                "symbol": symbol,
                "token": stock.get("token", ""),
                "gap_percent": round(gap_pct, 2),
                "open_price": round(open_price, 2),
                "prev_close": round(prev_close, 2),
            })

        ranked.sort(key=lambda x: x["gap_percent"], reverse=True)
        return ranked

    def _select_stocks(
        self, ranked_stocks: List[Dict], nifty_gap: Dict
    ) -> List[Dict]:
        """Select stocks based on Nifty gap direction."""
        gap_status = nifty_gap.get("gap_status", "FLAT")
        max_trades = self.max_trades_per_day

        if gap_status == "GAP_UP":
            selected = [s.copy() for s in ranked_stocks[:max_trades]]
            for s in selected:
                s["direction"] = "SHORT"

        elif gap_status == "GAP_DOWN":
            selected = [s.copy() for s in ranked_stocks[-max_trades:]]
            for s in selected:
                s["direction"] = "LONG"

        else:
            trades_per_side = max(1, max_trades // 2)
            short_picks = [s.copy() for s in ranked_stocks[:trades_per_side]]
            for s in short_picks:
                s["direction"] = "SHORT"
            long_picks = [s.copy() for s in ranked_stocks[-trades_per_side:]]
            for s in long_picks:
                s["direction"] = "LONG"
            selected = short_picks + long_picks

        return selected

    # ================================================================
    # TRADE SIMULATION
    # ================================================================

    def _simulate_stock(
        self, symbol: str, direction: str, candles: List[Dict]
    ) -> tuple:
        """
        Simulate the 3-minute breakout strategy for a single stock.
        Returns: (BacktestTrade or None, ref_info dict)
        """
        test_candles = self._parse_candles_for_test_date(candles)
        if not test_candles or len(test_candles) < 2:
            return None, None

        # --- Reference candle = first 3-minute bar (9:15-9:18) ---
        ref_candle = test_candles[0]
        ref_high = ref_candle["high"]
        ref_low = ref_candle["low"]
        ref_open = ref_candle["open"]
        ref_close = ref_candle["close"]

        if ref_high <= 0 or ref_low <= 0 or ref_close <= 0:
            return None, None

        # [FIX] Use close as denominator per strategy spec
        ref_range_pct = ((ref_high - ref_low) / ref_close) * 100
        is_large_candle = ref_range_pct > self.large_candle_percent

        ref_info = {
            "high": round(ref_high, 2),
            "low": round(ref_low, 2),
            "open": round(ref_open, 2),
            "close": round(ref_close, 2),
            "range_percent": round(ref_range_pct, 2),
            "is_large_candle": is_large_candle,
            "timestamp": ref_candle.get("timestamp", ""),
        }

        # --- Scan subsequent candles for breakout ---
        trade: Optional[BacktestTrade] = None

        for i, candle in enumerate(test_candles[1:], start=1):
            candle_time_str = candle.get("timestamp", "")
            candle_t = self._get_time_from_timestamp(candle_time_str)

            if trade is None:
                # Looking for breakout entry
                if candle_t >= NO_NEW_ENTRY_AFTER:
                    break  # Past entry cutoff (3:00 PM)

                entry_signal = self._check_candle_breakout(
                    candle, direction, ref_high, ref_low
                )

                if entry_signal:
                    entry_price = candle["close"]
                    sl, target = self._compute_sl_target(
                        entry_price, direction, ref_high, ref_low, is_large_candle
                    )
                    trade = BacktestTrade(
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry_price,
                        entry_time=candle_time_str,
                        stop_loss=sl,
                        target=target,
                        ref_high=ref_high,
                        ref_low=ref_low,
                        ref_open=ref_open,
                        ref_close=ref_close,
                        ref_range_percent=ref_range_pct,
                        is_large_candle=is_large_candle,
                    )
            else:
                # [FIX] 3:15 PM mandatory square-off
                if candle_t >= SQUARE_OFF_TIME:
                    # Use the OPEN of this candle as square-off price
                    # (closest to 3:15 market price)
                    trade.exit_price = candle["open"]
                    trade.exit_time = candle_time_str
                    trade.exit_reason = "SQUARE_OFF_315"
                    trade.pnl = self._calc_pnl(trade)
                    trade.pnl_percent = self._calc_pnl_percent(trade)
                    return trade, ref_info

                # In trade — check SL/target on this candle's OHLC
                exit_result = self._check_exit_on_candle(trade, candle)
                if exit_result:
                    trade.exit_price = exit_result["price"]
                    trade.exit_time = candle_time_str
                    trade.exit_reason = exit_result["reason"]
                    trade.pnl = self._calc_pnl(trade)
                    trade.pnl_percent = self._calc_pnl_percent(trade)
                    return trade, ref_info

        # If still in trade at end of data → forced square off
        if trade and trade.exit_price == 0:
            last_candle = test_candles[-1]
            trade.exit_price = last_candle["close"]
            trade.exit_time = last_candle.get("timestamp", "")
            trade.exit_reason = "SQUARE_OFF_315"
            trade.pnl = self._calc_pnl(trade)
            trade.pnl_percent = self._calc_pnl_percent(trade)
            return trade, ref_info

        return trade, ref_info

    def _check_candle_breakout(
        self, candle: Dict, direction: str, ref_high: float, ref_low: float
    ) -> bool:
        """Check if candle CLOSE breaks reference level."""
        close = candle["close"]

        if direction == "LONG":
            return close > ref_high
        elif direction == "SHORT":
            return close < ref_low

        return False

    def _check_exit_on_candle(
        self, trade: BacktestTrade, candle: Dict
    ) -> Optional[Dict]:
        """
        Check if SL or target is hit within a candle.
        SL checked first (conservative — assume worst case happens first).
        """
        high = candle["high"]
        low = candle["low"]

        if trade.direction == "LONG":
            if low <= trade.stop_loss:
                return {"price": trade.stop_loss, "reason": "STOP_LOSS"}
            if high >= trade.target:
                return {"price": trade.target, "reason": "TARGET"}

        elif trade.direction == "SHORT":
            if high >= trade.stop_loss:
                return {"price": trade.stop_loss, "reason": "STOP_LOSS"}
            if low <= trade.target:
                return {"price": trade.target, "reason": "TARGET"}

        return None

    def _compute_sl_target(
        self,
        entry: float,
        direction: str,
        ref_high: float,
        ref_low: float,
        is_large_candle: bool,
    ) -> tuple:
        """Compute stop-loss and target. Same logic as live strategy."""
        if direction == "LONG":
            if is_large_candle:
                sl = entry * (1 - self.stop_loss_percent / 100)
            else:
                sl = ref_low
            target = entry * (1 + self.target_percent / 100)
        else:  # SHORT
            if is_large_candle:
                sl = entry * (1 + self.stop_loss_percent / 100)
            else:
                sl = ref_high
            target = entry * (1 - self.target_percent / 100)

        return round(sl, 2), round(target, 2)

    def _calc_pnl(self, trade: BacktestTrade) -> float:
        if trade.direction == "LONG":
            return trade.exit_price - trade.entry_price
        else:
            return trade.entry_price - trade.exit_price

    def _calc_pnl_percent(self, trade: BacktestTrade) -> float:
        if trade.entry_price <= 0:
            return 0.0
        pnl = self._calc_pnl(trade)
        return round((pnl / trade.entry_price) * 100, 2)

    # ================================================================
    # HELPERS
    # ================================================================

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse a timestamp string to datetime."""
        if not ts:
            return None
        try:
            if "T" in ts:
                return datetime.fromisoformat(ts.replace("+05:30", "").replace("Z", ""))
            else:
                return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None

    def _get_time_from_timestamp(self, ts: str) -> time:
        """Extract time from timestamp string."""
        dt = self._parse_timestamp(ts)
        if dt:
            return dt.time()
        return time(9, 18)  # Safe default

    def _parse_candles_for_test_date(self, candles: List[Dict]) -> List[Dict]:
        """Filter candles to only include the test date (latest date in data)."""
        if not candles:
            return []

        parsed = []
        for c in candles:
            dt = self._parse_timestamp(c.get("timestamp", ""))
            if dt:
                parsed.append((dt, c))

        if not parsed:
            return []

        parsed.sort(key=lambda x: x[0])
        test_date = parsed[-1][0].date()

        return [c for dt, c in parsed if dt.date() == test_date]

    def _format_candles_for_chart(self, candles: List[Dict]) -> List[Dict]:
        """Format candles for Lightweight Charts."""
        chart_data = []
        for c in candles:
            dt = self._parse_timestamp(c.get("timestamp", ""))
            if not dt:
                continue

            chart_data.append({
                "time": int(dt.timestamp()),
                "timestamp": c.get("timestamp", ""),
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c.get("volume", 0),
            })

        return chart_data

    def _build_summary(
        self, trades: List[BacktestTrade], error: str = ""
    ) -> Dict:
        """Build summary statistics from trades."""
        if error:
            return {"error": error, "total_trades": 0}

        total = len(trades)
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl < 0]
        breakeven = [t for t in trades if t.pnl == 0]

        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = sum(t.pnl_percent for t in trades)

        win_rate = (len(winners) / total * 100) if total > 0 else 0
        max_win = max((t.pnl for t in trades), default=0)
        max_loss = min((t.pnl for t in trades), default=0)
        avg_pnl = (total_pnl / total) if total > 0 else 0

        return {
            "total_trades": total,
            "winners": len(winners),
            "losers": len(losers),
            "breakeven": len(breakeven),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "avg_pnl": round(avg_pnl, 2),
        }

    # ================================================================
    # REPORT SAVING
    # ================================================================

    def _save_report(self, result: BacktestResult) -> None:
        """Save full backtest report to JSON file for manual verification."""
        try:
            report_dir = Path("data/backtest_reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            filename = f"backtest_{result.date}.json"
            filepath = report_dir / filename

            report = result.to_full_report()

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📄 Backtest report saved: {filepath}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save backtest report: {e}")
