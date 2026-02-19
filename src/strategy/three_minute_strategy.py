"""3-Minute Strategy - Mean reversion pre-open gap strategy."""

import threading
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Tuple

from loguru import logger

from src.analysis.nifty_tracker import get_nifty_tracker
from src.core.config_manager import get_config
from src.utils.timezone import now_ist, now_ist_time

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry


FIRST_CANDLE_END = time(9, 18)
CANDLE_INTERVAL_MINUTES = 3


class TradeState(Enum):
    WAITING_REFERENCE = "waiting_reference"
    WAITING_BREAKOUT = "waiting_breakout"
    ENTERED = "entered"
    EXITED = "exited"


@StrategyRegistry.register(
    name="three_minute",
    display_name="3-Minute Mean Reversion Strategy",
    description="Fade the gap - Short on gap-up, Long on gap-down with 3-min candle confirmation",
    stock_picker="preopen_gap",
    default_params={
        "min_gap_percent": 1.0,
        "max_gap_percent": 8.0,
        "entry_window_start": "09:20",
        "entry_window_end": "10:30",
        "stop_loss_percent": 1.0,
        "target_percent": 1.0,
        "risk_reward_ratio": 1.0,
        "require_nifty_alignment": False,
        "max_trades_per_day": 2,
        "no_new_trade_after": "14:30",
        "max_daily_losses": 2,
        "first_candle_sl_threshold": 1.0,
    },
)
class ThreeMinuteStrategy(BaseStrategy):
    """3-minute mean reversion strategy."""

    display_name = "3-Minute Strategy (Pre-Open Gap)"
    description = "Trade gap-up/gap-down stocks from pre-open session with candle breakout"

    def __init__(self):
        super().__init__("three_minute")
        self.config = get_config()
        self.nifty_tracker = get_nifty_tracker()
        self._lock = threading.Lock()

        params = self.config.get("strategies.three_minute.params", {})
        self.min_gap_percent = params.get("min_gap_percent", 1.0)
        self.max_gap_percent = params.get("max_gap_percent", 8.0)
        self.entry_window_start = params.get("entry_window_start", "09:20")
        self.entry_window_end = params.get("entry_window_end", "10:30")
        self.stop_loss_percent = params.get("stop_loss_percent", 1.0)
        self.target_percent = params.get("target_percent", 1.0)
        self.max_sl_percent = params.get("max_sl_percent", 2.0)
        self.require_nifty_alignment = params.get("require_nifty_alignment", False)
        self.max_trades_per_day = params.get("max_trades_per_day", 2)
        self.no_new_trade_after = params.get("no_new_trade_after", "14:30")
        self.max_daily_losses = params.get("max_daily_losses", 2)
        self.first_candle_sl_threshold = params.get("first_candle_sl_threshold", 1.0)

        self.gap_signals: Dict[str, str] = {}
        self.gap_percent: Dict[str, float] = {}
        self.first_candle: Dict[str, Dict] = {}
        self.trade_states: Dict[str, TradeState] = {}
        self.trade_pnl: Dict[str, float] = {}
        self.daily_losses = 0
        self.trades_today = 0
        self._processed_candles: Dict[str, str] = {}
        self._first_candle_captured: Dict[str, bool] = {}
        self._minute_candles: Dict[str, List[Dict]] = {}

    def reset_daily(self) -> None:
        with self._lock:
            self.gap_signals.clear()
            self.gap_percent.clear()
            self.first_candle.clear()
            self.trade_states.clear()
            self.trade_pnl.clear()
            self._processed_candles.clear()
            self._first_candle_captured.clear()
            self._minute_candles.clear()
            self.daily_losses = 0
            self.trades_today = 0
            logger.info("3-Minute Strategy daily state reset")

    def set_gap_candidates(self, candidates: List[Dict]) -> None:
        with self._lock:
            for stock in candidates:
                symbol = stock.get("symbol", "UNKNOWN")
                signal_type = stock.get("signal_type", stock.get("gap_type", "NEUTRAL"))
                gap = stock.get("gap_percent", 0)
                if signal_type in ("BULLISH", "BEARISH"):
                    self.gap_signals[symbol] = signal_type
                    self.gap_percent[symbol] = gap
                    if symbol not in self.trade_states:
                        self.trade_states[symbol] = TradeState.WAITING_REFERENCE

    def _is_valid_entry_window(self) -> bool:
        now = now_ist_time()
        start = datetime.strptime(self.entry_window_start, "%H:%M").time()
        end = datetime.strptime(self.entry_window_end, "%H:%M").time()
        return start <= now <= end

    def _capture_first_candle(
        self, symbol: str, open_price: float, high_price: float, low_price: float, close_price: float, volume: float, candle_end_time: str
    ) -> bool:
        with self._lock:
            if self._first_candle_captured.get(symbol, False):
                return False
            if min(open_price, high_price, low_price, close_price) <= 0:
                return False

            self.first_candle[symbol] = {
                "high": high_price,
                "low": low_price,
                "open": open_price,
                "close": close_price,
                "volume": volume,
                "candle_end_time": candle_end_time,
                "captured_at": now_ist().isoformat(),
            }
            self._first_candle_captured[symbol] = True
            self.trade_states[symbol] = TradeState.WAITING_BREAKOUT
            return True

    def _check_nifty_alignment(self, signal: str) -> bool:
        if not self.require_nifty_alignment:
            return True
        if signal == "BULLISH":
            return self.nifty_tracker.is_bullish() or self.nifty_tracker.is_neutral()
        if signal == "BEARISH":
            return self.nifty_tracker.is_bearish() or self.nifty_tracker.is_neutral()
        return True

    def _get_completed_three_minute_candle(
        self, symbol: str, indicators: Dict, candle_timestamp: Optional[datetime] = None
    ) -> Optional[Dict]:
        candle_data = indicators.get("candle_data") if isinstance(indicators, dict) else None
        if not isinstance(candle_data, dict) or not candle_data.get("is_closed"):
            return None

        ts = candle_data.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = None
        if not isinstance(ts, datetime):
            ts = candle_timestamp or now_ist()

        end_minutes = ts.hour * 60 + ts.minute
        market_open_minutes = 9 * 60 + 15
        if end_minutes <= market_open_minutes:
            return None

        with self._lock:
            buffer = self._minute_candles.setdefault(symbol, [])
            if buffer and buffer[-1].get("end_minutes") == end_minutes:
                return None
            buffer.append(
                {
                    "end_minutes": end_minutes,
                    "open": float(candle_data.get("open", 0)),
                    "high": float(candle_data.get("high", 0)),
                    "low": float(candle_data.get("low", 0)),
                    "close": float(candle_data.get("close", 0)),
                    "volume": float(candle_data.get("volume", 0)),
                }
            )
            self._minute_candles[symbol] = buffer[-20:]

            if (end_minutes - market_open_minutes) % CANDLE_INTERVAL_MINUTES != 0:
                return None

            window = [c for c in self._minute_candles[symbol] if end_minutes - 2 <= c["end_minutes"] <= end_minutes]
            if len(window) < 3:
                return None
            window.sort(key=lambda x: x["end_minutes"])
            if [w["end_minutes"] for w in window[-3:]] != [end_minutes - 2, end_minutes - 1, end_minutes]:
                return None
            window = window[-3:]

            open_price = window[0]["open"]
            high_price = max(w["high"] for w in window)
            low_price = min(w["low"] for w in window)
            close_price = window[-1]["close"]
            volume = sum(w["volume"] for w in window)
            if min(open_price, high_price, low_price, close_price) <= 0:
                return None

            candle_id = time(end_minutes // 60, end_minutes % 60).strftime("%H:%M")
            return {
                "candle_id": candle_id,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "is_first_period": candle_id == "09:18",
            }

    def check_entry_signal(
        self, stock: Dict, current_price: float, indicators: Dict, candle_timestamp: Optional[datetime] = None
    ) -> Optional[Dict]:
        symbol = stock.get("symbol", "UNKNOWN")

        with self._lock:
            if not self.is_active:
                return None
            if self.daily_losses >= self.max_daily_losses:
                return None
            if self.trades_today >= self.max_trades_per_day:
                return None

            current_state = self.trade_states.get(symbol)
            if current_state in [TradeState.ENTERED, TradeState.EXITED]:
                return None

            signal = self.gap_signals.get(symbol)
            if not signal:
                signal = stock.get("signal_type", stock.get("gap_type"))
                if signal in ("BULLISH", "BEARISH"):
                    self.gap_signals[symbol] = signal
                    self.gap_percent[symbol] = stock.get("gap_percent", 0)
                    if symbol not in self.trade_states:
                        self.trade_states[symbol] = TradeState.WAITING_REFERENCE
                else:
                    return None

        completed_candle = self._get_completed_three_minute_candle(symbol, indicators, candle_timestamp)
        if not completed_candle:
            return None

        candle_id = completed_candle["candle_id"]
        open_price = completed_candle["open"]
        high_price = completed_candle["high"]
        low_price = completed_candle["low"]
        close_price = completed_candle["close"]
        volume = completed_candle["volume"]
        is_first_period = completed_candle["is_first_period"]

        if current_state == TradeState.WAITING_REFERENCE or symbol not in self.first_candle:
            if is_first_period and candle_id == "09:18":
                self._capture_first_candle(symbol, open_price, high_price, low_price, close_price, volume, candle_id)
            return None

        with self._lock:
            first_candle = self.first_candle.get(symbol)
            if not first_candle:
                return None
            if self._processed_candles.get(symbol) == candle_id:
                return None

        if not self._is_valid_entry_window():
            return None
        if not self.is_trading_time("09:20", self.no_new_trade_after):
            return None
        if close_price <= 0:
            return None
        if not self._check_nifty_alignment(signal):
            return None

        reference_high = first_candle["high"]
        reference_low = first_candle["low"]
        reference_open = first_candle["open"]
        first_candle_range_pct = ((reference_high - reference_low) / reference_open) * 100 if reference_open > 0 else 0

        is_breakout = False
        breakout_reason = ""
        if signal == "BULLISH" and close_price > reference_high:
            is_breakout = True
            breakout_reason = f"Close {close_price:.2f} > Reference High {reference_high:.2f}"
        elif signal == "BEARISH" and close_price < reference_low:
            is_breakout = True
            breakout_reason = f"Close {close_price:.2f} < Reference Low {reference_low:.2f}"
        if not is_breakout:
            return None

        with self._lock:
            self._processed_candles[symbol] = candle_id

        entry_price = close_price
        stop_loss, target = self._calculate_sl_target(symbol, signal, entry_price, first_candle_range_pct)
        if signal == "BULLISH" and stop_loss >= entry_price:
            return None
        if signal == "BEARISH" and stop_loss <= entry_price:
            return None

        direction = "LONG" if signal == "BULLISH" else "SHORT"
        action = "BUY" if direction == "LONG" else "SELL"
        gap = self.gap_percent.get(symbol, 0)
        nifty_change = self.nifty_tracker.get_change_percent()

        return {
            "action": action,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "reason": f"3-Min Breakout - {breakout_reason}",
            "signal_type": signal,
            "gap_percent": gap,
            "nifty_trend": self.nifty_tracker.trend,
            "nifty_change": nifty_change,
            "first_candle": first_candle,
            "candle_range_pct": first_candle_range_pct,
            "candle_id": candle_id,
        }

    def on_entry_filled(self, symbol: str) -> None:
        """Mark successful entry after broker confirms order."""
        with self._lock:
            self.trade_states[symbol] = TradeState.ENTERED
            self.trades_today += 1

    def _calculate_sl_target(self, symbol: str, signal: str, entry_price: float, first_candle_range_pct: float) -> Tuple[float, float]:
        first_candle = self.first_candle.get(symbol, {})
        if signal == "BULLISH":
            if first_candle_range_pct <= self.first_candle_sl_threshold and first_candle.get("low"):
                stop_loss = first_candle["low"]
                max_sl = entry_price * (1 - self.stop_loss_percent / 100)
                if stop_loss < max_sl:
                    stop_loss = max_sl
            else:
                stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            target = entry_price * (1 + self.target_percent / 100)
        else:
            if first_candle_range_pct <= self.first_candle_sl_threshold and first_candle.get("high"):
                stop_loss = first_candle["high"]
                max_sl = entry_price * (1 + self.stop_loss_percent / 100)
                if stop_loss > max_sl:
                    stop_loss = max_sl
            else:
                stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            target = entry_price * (1 - self.target_percent / 100)
        return round(stop_loss, 2), round(target, 2)

    def check_exit_signal(self, position: Dict, current_price: float, indicators: Dict) -> Optional[Dict]:
        symbol = position.get("symbol", "UNKNOWN")
        entry_price = position.get("entry_price", current_price)
        stop_loss = position.get("stop_loss", 0)
        target = position.get("target", 0)
        direction = position.get("direction", "LONG")

        if direction == "LONG":
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - current_price) / entry_price) * 100

        exit_signal = None
        if direction == "LONG" and current_price >= target:
            exit_signal = {"action": "SELL", "exit_price": current_price, "reason": "TARGET", "pnl_percent": pnl_percent}
        elif direction == "SHORT" and current_price <= target:
            exit_signal = {"action": "BUY", "exit_price": current_price, "reason": "TARGET", "pnl_percent": pnl_percent}
        elif direction == "LONG" and current_price <= stop_loss:
            exit_signal = {"action": "SELL", "exit_price": current_price, "reason": "STOP_LOSS", "pnl_percent": pnl_percent}
        elif direction == "SHORT" and current_price >= stop_loss:
            exit_signal = {"action": "BUY", "exit_price": current_price, "reason": "STOP_LOSS", "pnl_percent": pnl_percent}
        else:
            if now_ist_time() >= time(15, 15):
                action = "SELL" if direction == "LONG" else "BUY"
                exit_signal = {"action": action, "exit_price": current_price, "reason": "TIME", "pnl_percent": pnl_percent}

        if exit_signal:
            with self._lock:
                self.trade_states[symbol] = TradeState.EXITED
                self.trade_pnl[symbol] = pnl_percent
                if pnl_percent < 0:
                    self.daily_losses += 1
            return exit_signal
        return None

    def calculate_entry_points(self, stock: Dict) -> Dict:
        signal = stock.get("signal_type", stock.get("gap_type", "BULLISH"))
        price = stock.get("price", stock.get("ltp", stock.get("iep", 0)))
        if price <= 0:
            price = stock.get("prev_close", 1000)
        gap = stock.get("gap_percent", 0)

        if signal == "BULLISH":
            entry_price = price * 1.005
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            target_price = entry_price * (1 + self.target_percent / 100)
        else:
            entry_price = price * 0.995
            stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            target_price = entry_price * (1 - self.target_percent / 100)

        return {
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "gap_percent": gap,
            "signal_type": signal,
            "stop_loss_percent": self.stop_loss_percent,
            "target_percent": self.target_percent,
        }

    def get_strategy_status(self) -> Dict:
        with self._lock:
            return {
                "name": self.name,
                "display_name": self.display_name,
                "gap_candidates": {
                    "bullish": [s for s, sig in self.gap_signals.items() if sig == "BULLISH"],
                    "bearish": [s for s, sig in self.gap_signals.items() if sig == "BEARISH"],
                },
                "gap_percentages": self.gap_percent.copy(),
                "first_candles": {
                    s: {
                        "high": c.get("high"),
                        "low": c.get("low"),
                        "range_pct": ((c.get("high", 0) - c.get("low", 0)) / c.get("open", 1)) * 100,
                    }
                    for s, c in self.first_candle.items()
                },
                "trade_states": {s: state.value for s, state in self.trade_states.items()},
                "trades_today": self.trades_today,
                "max_trades": self.max_trades_per_day,
                "daily_losses": self.daily_losses,
                "max_daily_losses": self.max_daily_losses,
                "is_entry_window": self._is_valid_entry_window(),
                "is_first_candle_complete": now_ist_time() >= FIRST_CANDLE_END,
                "nifty": self.nifty_tracker.get_status(),
            }
