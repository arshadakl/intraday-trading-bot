"""3-Minute Breakout Strategy

Breakout system driven by Nifty 50 gap behavior at market open.
Uses a 3-minute reference candle (9:15-9:18) and waits for candle-close
breakout confirmation before entering trades.

See STRATEGY_RULES.md for the complete specification.
"""

import threading
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from loguru import logger

from src.analysis.nifty_tracker import get_nifty_tracker
from src.core.config_manager import get_config
from src.utils.timezone import now_ist, now_ist_time

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry


# --- Constants ---
MARKET_OPEN = time(9, 15)
REFERENCE_CANDLE_END = time(9, 18)
CANDLE_INTERVAL_MINUTES = 3
NO_NEW_ENTRY_DEFAULT = time(15, 0)


class StockState(Enum):
    """Per-stock state machine for the trading day."""
    WAITING_FOR_REFERENCE = "waiting_for_reference"
    WAITING_FOR_BREAKOUT = "waiting_for_breakout"
    IN_TRADE = "in_trade"
    DONE = "done"  # SL/target hit or trade completed — no re-entry


class ThreeMinuteStrategy(BaseStrategy):
    """
    3-Minute Breakout Strategy implementation.

    Workflow per day:
    1. Receive gap candidates (top/bottom ranked stocks with direction)
    2. Build reference candle from ticks during 9:15-9:18
    3. After 9:18, monitor 3-min candle closes for breakout
    4. Enter on breakout close, set SL/target
    5. Exit on SL, target, or market close
    """

    def __init__(self):
        super().__init__("three_minute")
        self.config = get_config()
        self._load_params()

        # --- Per-stock state ---
        self._stock_states: Dict[str, StockState] = {}
        self._stock_directions: Dict[str, str] = {}  # symbol -> "LONG" or "SHORT"

        # --- Reference candle data (9:15-9:18) ---
        self._ref_candle: Dict[str, Dict] = {}
        # Keys per symbol: {"high": float, "low": float, "open": float, "close": float, "ready": bool}

        # --- 3-minute candle builder ---
        self._current_candle: Dict[str, Dict] = {}
        # Keys per symbol: {"open": float, "high": float, "low": float, "close": float,
        #                    "start_time": datetime, "tick_count": int}
        self._last_candle_boundary: Optional[datetime] = None

        # --- Tracking ---
        self._completed_stocks: Set[str] = set()  # Stocks that have finished trading
        self._traded_today: Set[str] = set()  # Stocks that entered a trade today

        self._lock = threading.Lock()

        logger.info(
            f"📊 3-Minute Breakout Strategy initialized | "
            f"target={self.target_percent}% | SL={self.stop_loss_percent}% | "
            f"large_candle_threshold={self.large_candle_percent}% | "
            f"gap_threshold={self.gap_threshold_percent}%"
        )

    def _load_params(self):
        """Load strategy parameters from config."""
        params = self.config.get("strategies.three_minute.params", {})
        self.gap_threshold_percent = float(params.get("gap_threshold_percent", 0.2))
        self.large_candle_percent = float(params.get("large_candle_percent", 1.0))
        self.stop_loss_percent = float(params.get("stop_loss_percent", 1.0))
        self.target_percent = float(params.get("target_percent", 1.0))
        self.max_trades_per_day = int(params.get("max_trades_per_day", 2))
        self.stocks_per_side = int(params.get("stocks_per_side", 4))

        no_new_trade_str = params.get("no_new_trade_after", "15:00")
        h, m = map(int, no_new_trade_str.split(":"))
        self.no_new_entry_after = time(h, m)

    # ================================================================
    # PUBLIC API — Called by bot.py
    # ================================================================

    def set_gap_candidates(self, stocks: List[Dict]) -> None:
        """
        Receive the list of stocks selected after gap classification.
        Each stock dict must include 'symbol' and 'direction' keys.
        Called once at ~9:15 AM by bot._apply_three_minute_market_open_filter().
        """
        with self._lock:
            for stock in stocks:
                symbol = stock.get("symbol")
                direction = stock.get("direction", "LONG").upper()
                if not symbol:
                    continue

                self._stock_states[symbol] = StockState.WAITING_FOR_REFERENCE
                self._stock_directions[symbol] = direction
                self._ref_candle[symbol] = {
                    "high": 0.0, "low": float("inf"),
                    "open": 0.0, "close": 0.0, "ready": False
                }

            symbols = [s.get("symbol") for s in stocks if s.get("symbol")]
            directions = {s.get("symbol"): s.get("direction", "LONG") for s in stocks}
            logger.info(
                f"🎯 Gap candidates set: {len(symbols)} stocks | "
                f"Directions: {directions}"
            )

    def reset_daily(self) -> None:
        """Reset all state for a new trading day."""
        with self._lock:
            self._stock_states.clear()
            self._stock_directions.clear()
            self._ref_candle.clear()
            self._current_candle.clear()
            self._completed_stocks.clear()
            self._traded_today.clear()
            self._last_candle_boundary = None

        self._load_params()
        logger.info("🔄 3-Minute Strategy daily state reset")

    def on_entry_filled(self, symbol: str) -> None:
        """Called by bot when an entry order is filled."""
        with self._lock:
            self._stock_states[symbol] = StockState.IN_TRADE
            self._traded_today.add(symbol)
        logger.info(f"✅ {symbol}: Entry filled — state → IN_TRADE")

    # ================================================================
    # ENTRY SIGNAL — Called on every price tick
    # ================================================================

    def check_entry_signal(
        self, stock: Dict, current_price: float, indicators: Dict
    ) -> Optional[Dict]:
        """
        Check if a breakout entry signal is triggered.

        This method is called on every WebSocket tick. Internally, it:
        1. Feeds ticks into the reference candle builder (before 9:18)
        2. Feeds ticks into the 3-minute candle builder (after 9:18)
        3. Only generates entry signals when a 3-minute candle closes
        4. Checks if the candle close breaks the reference level
        """
        symbol = stock.get("symbol")
        if not symbol:
            return None

        now = now_ist()
        now_t = now.time()

        with self._lock:
            state = self._stock_states.get(symbol)
            if state is None or state in (StockState.IN_TRADE, StockState.DONE):
                return None

            # Rule: no new entries after cutoff
            if now_t >= self.no_new_entry_after:
                return None

            # Rule: already completed (SL/target hit)
            if symbol in self._completed_stocks:
                return None

            # Rule: already traded today
            if symbol in self._traded_today:
                return None

            direction = self._stock_directions.get(symbol)
            if not direction:
                return None

            # --- Phase 1: Building reference candle (9:15 - 9:18) ---
            if state == StockState.WAITING_FOR_REFERENCE:
                self._feed_reference_candle(symbol, current_price, now)

                # Check if reference candle is complete
                if now_t >= REFERENCE_CANDLE_END:
                    ref = self._ref_candle.get(symbol, {})
                    if ref.get("high", 0) > 0 and ref.get("low", float("inf")) < float("inf"):
                        ref["ready"] = True
                        ref["close"] = current_price
                        self._stock_states[symbol] = StockState.WAITING_FOR_BREAKOUT

                        # Initialize the first 3-min candle starting at 9:18
                        self._init_candle(symbol, current_price, now)

                        logger.info(
                            f"📊 {symbol}: Reference candle complete | "
                            f"High={ref['high']:.2f} Low={ref['low']:.2f} | "
                            f"Range={((ref['high'] - ref['low']) / ref['low'] * 100):.2f}% | "
                            f"Direction={direction}"
                        )
                    else:
                        logger.warning(f"⚠️ {symbol}: Reference candle has no valid data at 9:18")
                return None

            # --- Phase 2: Monitoring for breakout (after 9:18) ---
            if state == StockState.WAITING_FOR_BREAKOUT:
                return self._check_breakout(symbol, current_price, now, direction, stock)

        return None

    # ================================================================
    # EXIT SIGNAL — Called on every price tick when in position
    # ================================================================

    def check_exit_signal(
        self, position: Dict, current_price: float, indicators: Dict
    ) -> Optional[Dict]:
        """
        Check if SL or target is hit. Checked on every tick for fast execution.
        """
        symbol = position.get("symbol")
        direction = position.get("direction", "LONG").upper()
        stop_loss = position.get("stop_loss", 0)
        target = position.get("target", 0)

        if not symbol or not stop_loss or not target:
            return None

        if direction == "LONG":
            # Target hit
            if current_price >= target:
                self._mark_completed(symbol)
                return {
                    "action": "SELL",
                    "exit_price": current_price,
                    "reason": "TARGET",
                    "direction": direction,
                }
            # Stop-loss hit
            if current_price <= stop_loss:
                self._mark_completed(symbol)
                return {
                    "action": "SELL",
                    "exit_price": current_price,
                    "reason": "STOP_LOSS",
                    "direction": direction,
                }

        elif direction == "SHORT":
            # Target hit (price drops to target)
            if current_price <= target:
                self._mark_completed(symbol)
                return {
                    "action": "BUY",
                    "exit_price": current_price,
                    "reason": "TARGET",
                    "direction": direction,
                }
            # Stop-loss hit (price rises to SL)
            if current_price >= stop_loss:
                self._mark_completed(symbol)
                return {
                    "action": "BUY",
                    "exit_price": current_price,
                    "reason": "STOP_LOSS",
                    "direction": direction,
                }

        return None

    def calculate_entry_points(self, stock: Dict) -> Dict:
        """Calculate entry, target, and stop-loss for a stock (used by dashboard)."""
        symbol = stock.get("symbol", "")
        direction = self._stock_directions.get(symbol, "LONG")
        ref = self._ref_candle.get(symbol, {})
        price = stock.get("ltp", stock.get("last_price", 0))

        if not price or not ref.get("ready"):
            return {"entry_price": 0, "target_price": 0, "stop_loss": 0}

        if direction == "LONG":
            entry = ref.get("high", price)
            sl, target = self._compute_sl_target(entry, direction, ref)
        else:
            entry = ref.get("low", price)
            sl, target = self._compute_sl_target(entry, direction, ref)

        return {
            "entry_price": round(entry, 2),
            "target_price": round(target, 2),
            "stop_loss": round(sl, 2),
            "direction": direction,
        }

    # ================================================================
    # INTERNAL — Reference candle builder
    # ================================================================

    def _feed_reference_candle(self, symbol: str, price: float, now: datetime) -> None:
        """Accumulate tick data into the reference candle (9:15-9:18)."""
        ref = self._ref_candle.get(symbol)
        if ref is None:
            return

        if ref["open"] == 0.0:
            ref["open"] = price

        ref["high"] = max(ref["high"], price)
        ref["low"] = min(ref["low"], price)
        ref["close"] = price

    # ================================================================
    # INTERNAL — 3-minute candle builder & breakout checker
    # ================================================================

    def _get_candle_boundary(self, now: datetime) -> datetime:
        """
        Get the start time of the current 3-minute candle.
        Candle boundaries: 9:18, 9:21, 9:24, 9:27, ...
        """
        base = now.replace(hour=9, minute=18, second=0, microsecond=0)
        if now < base:
            return base

        elapsed = (now - base).total_seconds()
        interval_seconds = CANDLE_INTERVAL_MINUTES * 60
        candles_elapsed = int(elapsed // interval_seconds)
        return base + timedelta(seconds=candles_elapsed * interval_seconds)

    def _init_candle(self, symbol: str, price: float, now: datetime) -> None:
        """Initialize a new 3-minute candle."""
        boundary = self._get_candle_boundary(now)
        self._current_candle[symbol] = {
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "start_time": boundary,
            "tick_count": 1,
        }

    def _check_breakout(
        self, symbol: str, current_price: float, now: datetime,
        direction: str, stock: Dict
    ) -> Optional[Dict]:
        """
        Feed tick into 3-min candle builder. On candle close, check breakout.
        Returns entry signal dict if breakout confirmed, None otherwise.
        """
        candle = self._current_candle.get(symbol)
        if candle is None:
            self._init_candle(symbol, current_price, now)
            return None

        current_boundary = self._get_candle_boundary(now)

        # Check if the current candle has closed (we've moved to a new boundary)
        if current_boundary > candle["start_time"]:
            # The previous candle is complete — check for breakout
            closed_candle = {
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
            }

            # Start new candle immediately
            self._current_candle[symbol] = {
                "open": current_price,
                "high": current_price,
                "low": current_price,
                "close": current_price,
                "start_time": current_boundary,
                "tick_count": 1,
            }

            # Check breakout on the CLOSED candle
            signal = self._evaluate_breakout(symbol, closed_candle, direction, stock)
            if signal:
                return signal
        else:
            # Update current candle with this tick
            candle["high"] = max(candle["high"], current_price)
            candle["low"] = min(candle["low"], current_price)
            candle["close"] = current_price
            candle["tick_count"] += 1

        return None

    def _evaluate_breakout(
        self, symbol: str, candle: Dict, direction: str, stock: Dict
    ) -> Optional[Dict]:
        """
        Evaluate whether a closed 3-minute candle constitutes a breakout.
        Breakout = candle CLOSE beyond the reference level.
        """
        ref = self._ref_candle.get(symbol, {})
        if not ref.get("ready"):
            return None

        ref_high = ref["high"]
        ref_low = ref["low"]
        candle_close = candle["close"]

        if direction == "LONG":
            # Breakout above reference high
            if candle_close > ref_high:
                entry_price = candle_close
                sl, target = self._compute_sl_target(entry_price, direction, ref)

                logger.info(
                    f"🚀 {symbol}: LONG BREAKOUT confirmed | "
                    f"Candle close {candle_close:.2f} > Ref high {ref_high:.2f} | "
                    f"Entry={entry_price:.2f} SL={sl:.2f} Target={target:.2f}"
                )

                return {
                    "action": "BUY",
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "stop_loss": sl,
                    "target": target,
                    "reason": f"3-min breakout above ref high {ref_high:.2f}",
                }

        elif direction == "SHORT":
            # Breakout below reference low
            if candle_close < ref_low:
                entry_price = candle_close
                sl, target = self._compute_sl_target(entry_price, direction, ref)

                logger.info(
                    f"🚀 {symbol}: SHORT BREAKOUT confirmed | "
                    f"Candle close {candle_close:.2f} < Ref low {ref_low:.2f} | "
                    f"Entry={entry_price:.2f} SL={sl:.2f} Target={target:.2f}"
                )

                return {
                    "action": "SELL",
                    "direction": "SHORT",
                    "entry_price": entry_price,
                    "stop_loss": sl,
                    "target": target,
                    "reason": f"3-min breakout below ref low {ref_low:.2f}",
                }

        return None

    # ================================================================
    # INTERNAL — SL / Target computation
    # ================================================================

    def _compute_sl_target(
        self, entry_price: float, direction: str, ref: Dict
    ) -> tuple:
        """
        Compute stop-loss and target based on reference candle size.

        Normal case: SL = reference candle opposite extreme
        Large candle case (>large_candle_percent range): SL = fixed % from entry

        Returns: (stop_loss, target)
        """
        ref_high = ref.get("high", entry_price)
        ref_low = ref.get("low", entry_price)

        # Check if reference candle is "large"
        if ref_low > 0:
            candle_range_percent = ((ref_high - ref_low) / ref_low) * 100
        else:
            candle_range_percent = 0

        is_large_candle = candle_range_percent > self.large_candle_percent

        if direction == "LONG":
            if is_large_candle:
                # Large candle: fixed % SL from entry
                sl = entry_price * (1 - self.stop_loss_percent / 100)
                logger.info(
                    f"📏 Large candle detected ({candle_range_percent:.2f}% > "
                    f"{self.large_candle_percent}%). Using fixed SL: {sl:.2f}"
                )
            else:
                # Normal: SL at reference candle low
                sl = ref_low

            target = entry_price * (1 + self.target_percent / 100)

        else:  # SHORT
            if is_large_candle:
                sl = entry_price * (1 + self.stop_loss_percent / 100)
                logger.info(
                    f"📏 Large candle detected ({candle_range_percent:.2f}% > "
                    f"{self.large_candle_percent}%). Using fixed SL: {sl:.2f}"
                )
            else:
                # Normal: SL at reference candle high
                sl = ref_high

            target = entry_price * (1 - self.target_percent / 100)

        return round(sl, 2), round(target, 2)

    def _mark_completed(self, symbol: str) -> None:
        """Mark a stock as done for the day (no re-entry allowed)."""
        with self._lock:
            self._completed_stocks.add(symbol)
            self._stock_states[symbol] = StockState.DONE
        logger.info(f"🏁 {symbol}: Marked DONE for today — no re-entry allowed")

    # ================================================================
    # STATUS — For dashboard display
    # ================================================================

    def get_strategy_status(self) -> Dict:
        """Return current strategy state for the dashboard."""
        with self._lock:
            ref_data = {}
            for sym, ref in self._ref_candle.items():
                ref_data[sym] = {
                    "high": ref.get("high", 0),
                    "low": ref.get("low", 0),
                    "ready": ref.get("ready", False),
                    "state": self._stock_states.get(sym, StockState.DONE).value,
                    "direction": self._stock_directions.get(sym, ""),
                }

            return {
                "name": self.name,
                "states": {s: st.value for s, st in self._stock_states.items()},
                "ref_candles": ref_data,
                "completed_stocks": list(self._completed_stocks),
                "traded_today": list(self._traded_today),
            }


# --- Register the strategy ---
StrategyRegistry.register_strategy(
    "three_minute",
    ThreeMinuteStrategy,
    display_name="3-Minute Breakout Strategy",
    description="Breakout strategy using 3-minute reference candle. "
                "SHORT top stocks on gap-up, LONG bottom stocks on gap-down.",
    stock_picker="preopen_gap",
    default_params={
        "gap_threshold_percent": 0.2,
        "large_candle_percent": 1.0,
        "stop_loss_percent": 1.0,
        "target_percent": 1.0,
        "max_trades_per_day": 2,
        "stocks_per_side": 4,
        "no_new_trade_after": "15:00",
    },
)
