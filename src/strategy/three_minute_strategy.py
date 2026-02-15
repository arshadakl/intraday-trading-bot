"""3-Minute Strategy - Mean Reversion Gap Trading Strategy

MEAN REVERSION STRATEGY - Fade the Gap
======================================

This strategy uses pre-open market data to identify mean-reversion opportunities
by trading AGAINST the gap direction (fading the gap).

Core Concept (MEAN REVERSION):
- Fetch NSE pre-open data after 9:10 AM (when IEP is finalized)
- Gap Up → SHORT the strongest stocks (price likely to revert down)
- Gap Down → LONG the weakest stocks (price likely to revert up)
- Wait for confirmation after market opens (candle breakout)
- Execute trades OPPOSITE to gap direction

NSE Pre-Open Timeline:
- 9:00-9:08 AM: Order entry period (data changes frequently)
- 9:08-9:10 AM: Order matching period (final price being determined)
- 9:10-9:15 AM: Final IEP available, data is STABLE (fetch data here)

Workflow:
1. PRE-MARKET (9:10 AM): Fetch final pre-open data after IEP is confirmed
2. 9:10-9:15 AM: Analyze data, classify Nifty gap, select stocks
3. 9:15 AM: Determine trade direction based on Nifty gap
   - Nifty GAP UP → SHORT top stocks (fade the gap)
   - Nifty GAP DOWN → LONG bottom stocks (fade the gap)
   - Nifty FLAT → Trade both directions
4. POST-OPEN (9:15-9:18 AM): Capture first 3-minute candle reference
5. ENTRY WINDOW (9:20-10:30 AM): Enter on candle CLOSE beyond reference level
6. TRADING (Till 14:30): Monitor positions, no new entries after 2:30 PM
7. SQUARE-OFF (15:15 PM): Close all positions

Entry Rules:
- Wait for first 3-minute candle to close at 9:18 AM
- LONG: Candle must CLOSE above first candle high (breakout confirmation)
- SHORT: Candle must CLOSE below first candle low (breakdown confirmation)
- Volume must be 1.2x first candle volume
- Entry only on candle close (not intrabar)

Stop Loss Rules:
- If first candle range ≤ 1%: SL at first candle high/low
- If first candle range > 1%: SL at entry ± 1% (fallback)

Target Rules:
- Fixed target at entry ± 1%

Risk Management:
- Max 2 trades per day
- Max 2 daily losses allowed (drawdown guard)
- No new entries after 2:30 PM
- Square off all positions at 3:15 PM

Author: Trading Bot System
Version: 2.0 (Mean Reversion)
"""

from datetime import datetime, time, timedelta
from typing import Dict, Optional, List, Tuple
from enum import Enum
from loguru import logger

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry
from src.core.config_manager import get_config
from src.analysis.nifty_tracker import get_nifty_tracker
from src.utils.timezone import now_ist, now_ist_time


class TradeState(Enum):
    """Trade state machine states"""
    WAITING_REFERENCE = "waiting_reference"      # Waiting for 9:18 first candle
    WAITING_BREAKOUT = "waiting_breakout"        # Have reference, waiting for breakout
    ENTERED = "entered"                          # Position entered
    EXITED = "exited"                            # Position exited, locked for day


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
        "use_opening_range_breakout": True,
        "opening_range_minutes": 3,
        "max_trades_per_day": 2,
        "no_new_trade_after": "14:30",
        "max_daily_losses": 2,
        "first_candle_sl_threshold": 1.0,
        "volume_breakout_multiplier": 1.2,
        "require_candle_close": True
    }
)
class ThreeMinuteStrategy(BaseStrategy):
    """
    3-Minute Mean Reversion Strategy - Fade the Gap Trading Strategy.
    
    MEAN REVERSION PRINCIPLE: When Nifty gaps up, short strongest stocks (likely to fall).
    When Nifty gaps down, long weakest stocks (likely to rise).
    
    Key Features:
    - Uses NSE pre-open data (fetch after 9:10 AM when IEP is final) to identify gap candidates
    - Captures first 3-minute candle (9:15-9:18) as reference
    - Enters on candle CLOSE beyond reference level (not intrabar)
    - Requires volume confirmation (1.2x reference volume)
    - Implements strict risk management with daily loss limits
    
    Gap Classification & Trade Direction:
    - Nifty GAP UP (>0.2%): SHORT top 4 strongest stocks (fade the gap)
    - Nifty GAP DOWN (<-0.2%): LONG bottom 4 weakest stocks (fade the gap)
    - Nifty FLAT (±0.2%): Trade both directions with split allocation
    
    State Machine:
    - WAITING_REFERENCE: Waiting for 9:18 first candle to form
    - WAITING_BREAKOUT: Have reference, waiting for candle close breakout
    - ENTERED: Position entered, monitoring for exit
    - EXITED: Position exited, locked for rest of day
    """
    
    # Class-level metadata
    display_name = "3-Minute Strategy (Pre-Open Gap)"
    description = "Trade gap-up/gap-down stocks from pre-open session with candle breakout"
    
    def __init__(self):
        super().__init__("three_minute")
        self.config = get_config()
        self.nifty_tracker = get_nifty_tracker()
        
        # Get strategy params from config
        strategy_params = self.config.get('strategies.three_minute.params', {})
        
        # Gap parameters
        self.min_gap_percent = strategy_params.get('min_gap_percent', 1.0)
        self.max_gap_percent = strategy_params.get('max_gap_percent', 8.0)
        
        # Entry window parameters
        self.entry_window_start = strategy_params.get('entry_window_start', '09:20')
        self.entry_window_end = strategy_params.get('entry_window_end', '10:30')
        
        # Risk management
        self.stop_loss_percent = strategy_params.get('stop_loss_percent', 1.0)
        self.target_percent = strategy_params.get('target_percent', 1.0)
        self.risk_reward_ratio = strategy_params.get('risk_reward_ratio', 1.0)
        self.max_sl_percent = strategy_params.get('max_sl_percent', 2.0)
        
        # Strategy options
        self.require_nifty_alignment = strategy_params.get('require_nifty_alignment', False)
        self.use_opening_range_breakout = strategy_params.get('use_opening_range_breakout', True)
        self.opening_range_minutes = strategy_params.get('opening_range_minutes', 3)
        self.max_trades_per_day = strategy_params.get('max_trades_per_day', 2)
        
        # NEW: Time and risk controls
        self.no_new_trade_after = strategy_params.get('no_new_trade_after', '14:30')
        self.max_daily_losses = strategy_params.get('max_daily_losses', 2)
        self.first_candle_sl_threshold = strategy_params.get('first_candle_sl_threshold', 1.0)
        self.volume_breakout_multiplier = strategy_params.get('volume_breakout_multiplier', 1.2)
        self.require_candle_close = strategy_params.get('require_candle_close', True)
        
        # State tracking per symbol
        self.gap_signals: Dict[str, str] = {}  # symbol -> 'BULLISH' or 'BEARISH'
        self.gap_percent: Dict[str, float] = {}  # symbol -> gap percentage
        self.opening_range: Dict[str, Dict] = {}  # symbol -> {high, low, open, close}
        self.first_candle: Dict[str, Dict] = {}  # symbol -> first 3-min candle data
        self.trade_states: Dict[str, TradeState] = {}  # symbol -> current state
        self.trade_pnl: Dict[str, float] = {}  # symbol -> P&L for completed trades
        self.daily_losses = 0
        self.trades_today = 0
        
        # Opening range tracking
        self._opening_range_end: Optional[time] = None
        self._first_candle_formed: Dict[str, bool] = {}  # symbol -> first candle ready
        
    def reset_daily(self) -> None:
        """
        Reset all daily state.
        
        Called at the start of each trading day.
        """
        self.gap_signals.clear()
        self.gap_percent.clear()
        self.opening_range.clear()
        self.first_candle.clear()
        self.trade_states.clear()
        self.trade_pnl.clear()
        self._first_candle_formed.clear()
        self.daily_losses = 0
        self.trades_today = 0
        self._opening_range_end = None
        logger.info("🔄 3-Minute Strategy daily state reset")
    
    def set_gap_candidates(self, candidates: List[Dict]) -> None:
        """
        Set the gap candidates from pre-open stock picker.
        
        Called after pre-open analysis to set up trading candidates.
        
        Args:
            candidates: List of stocks with gap data from PreOpenGapPicker
        """
        for stock in candidates:
            symbol = stock.get('symbol', 'UNKNOWN')
            signal_type = stock.get('signal_type', stock.get('gap_type', 'NEUTRAL'))
            gap = stock.get('gap_percent', 0)
            
            if signal_type in ('BULLISH', 'BEARISH'):
                self.gap_signals[symbol] = signal_type
                self.gap_percent[symbol] = gap
                logger.info(f"📋 {symbol}: Registered as {signal_type} candidate (Gap: {gap:+.2f}%)")
    
    def _calculate_opening_range_end(self) -> time:
        """Calculate the time when opening range period ends."""
        if self._opening_range_end is None:
            market_open = datetime.strptime("09:15", "%H:%M")
            range_end = market_open + timedelta(minutes=self.opening_range_minutes)
            self._opening_range_end = range_end.time()
        return self._opening_range_end
    
    def _is_opening_range_period(self) -> bool:
        """Check if we're still in the opening range formation period."""
        now = now_ist_time()
        market_open = time(9, 15)
        range_end = self._calculate_opening_range_end()
        
        return market_open <= now <= range_end
    
    def _update_opening_range(self, symbol: str, high: float, low: float, open_price: float) -> None:
        """
        Track the opening range for a stock.
        
        The opening range is the high/low of the first N minutes after market opens.
        This is used for breakout confirmation.
        """
        now = now_ist_time()
        range_end = self._calculate_opening_range_end()
        
        if now <= range_end:
            if symbol not in self.opening_range:
                self.opening_range[symbol] = {
                    'high': high,
                    'low': low,
                    'open': open_price,
                    'range': 0
                }
            else:
                self.opening_range[symbol]['high'] = max(self.opening_range[symbol]['high'], high)
                self.opening_range[symbol]['low'] = min(self.opening_range[symbol]['low'], low)
            
            # Calculate range
            self.opening_range[symbol]['range'] = (
                self.opening_range[symbol]['high'] - self.opening_range[symbol]['low']
            )
    
    def _is_valid_entry_window(self) -> bool:
        """Check if current time is within entry window."""
        now = now_ist_time()
        try:
            start = datetime.strptime(self.entry_window_start, "%H:%M").time()
            end = datetime.strptime(self.entry_window_end, "%H:%M").time()
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid entry window configuration: {e}")
            return False
        
        return start <= now <= end
    
    def _check_nifty_alignment(self, signal: str) -> bool:
        """
        Check if signal aligns with Nifty trend.
        
        Args:
            signal: 'BULLISH' or 'BEARISH'
            
        Returns:
            True if aligned (or alignment not required)
        """
        if not self.require_nifty_alignment:
            return True
        
        if signal == 'BULLISH':
            aligned = self.nifty_tracker.is_bullish() or self.nifty_tracker.is_neutral()
            if not aligned:
                logger.debug("Bullish signal skipped - Nifty is bearish")
            return aligned
        elif signal == 'BEARISH':
            aligned = self.nifty_tracker.is_bearish() or self.nifty_tracker.is_neutral()
            if not aligned:
                logger.debug("Bearish signal skipped - Nifty is bullish")
            return aligned
        
        return True
    
    def _check_opening_range_breakout(self, symbol: str, current_price: float, signal: str) -> Tuple[bool, str]:
        """
        Check if price has broken out of opening range.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            signal: 'BULLISH' or 'BEARISH'
            
        Returns:
            Tuple of (is_breakout, reason)
        """
        if not self.use_opening_range_breakout:
            return True, "Opening range breakout disabled"
        
        if symbol not in self.opening_range:
            return False, "Opening range not yet formed"
        
        range_data = self.opening_range[symbol]
        range_high = range_data['high']
        range_low = range_data['low']
        
        if signal == 'BULLISH':
            # For longs, need price above range high
            if current_price > range_high:
                return True, f"Breakout above {range_high:.2f}"
            return False, f"Waiting for breakout above {range_high:.2f}"
        
        elif signal == 'BEARISH':
            # For shorts, need price below range low
            if current_price < range_low:
                return True, f"Breakdown below {range_low:.2f}"
            return False, f"Waiting for breakdown below {range_low:.2f}"
        
        return False, "Invalid signal type"
    
    def check_entry_signal(self, stock: Dict, current_price: float,
                          indicators: Dict, candle_timestamp: Optional[datetime] = None) -> Optional[Dict]:
        """
        Check for 3-Minute Strategy entry signals with state machine and candle close logic.
        
        Entry requires ALL conditions:
        1. Stock is in gap candidates list
        2. Not exceeded max daily losses (drawdown guard)
        3. Within entry window (9:20-10:30)
        4. Not after 2:30 PM cut-off
        5. Not already entered/exited for this stock
        6. Not exceeded max trades per day
        7. First 3-min candle formed (9:15-9:18) and captured
        8. Candle CLOSES beyond reference level (not intrabar)
        9. Volume confirmation on breakout
        
        Args:
            stock: Stock data with gap info
            current_price: Current LTP (should be candle close price)
            indicators: Indicator values
            candle_timestamp: Optional timestamp of the candle to determine if it's first candle
            
        Returns:
            Entry signal dict or None
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        
        # Check if strategy is active
        if not self.is_active:
            return None
        
        # Check max daily losses (drawdown guard)
        if self.daily_losses >= self.max_daily_losses:
            logger.debug(f"{symbol}: Daily loss limit reached ({self.daily_losses}/{self.max_daily_losses})")
            return None
        
        # Check max trades
        if self.trades_today >= self.max_trades_per_day:
            return None
        
        # Check if already triggered for this stock
        current_state = self.trade_states.get(symbol, TradeState.WAITING_REFERENCE)
        if current_state in [TradeState.ENTERED, TradeState.EXITED]:
            return None
        
        # Check if this stock is in our gap candidates
        signal = self.gap_signals.get(symbol)
        if not signal:
            # Try to get from stock data
            signal = stock.get('signal_type', stock.get('gap_type'))
            if signal in ('BULLISH', 'BEARISH'):
                self.gap_signals[symbol] = signal
                self.gap_percent[symbol] = stock.get('gap_percent', 0)
            else:
                return None  # Not a gap candidate
        
        # Get complete OHLCV data
        open_price = stock.get('open', indicators.get('open', current_price))
        high_price = stock.get('high', indicators.get('high', current_price))
        low_price = stock.get('low', indicators.get('low', current_price))
        close_price = stock.get('close', indicators.get('close', current_price))
        volume = stock.get('volume', indicators.get('volume', 0))
        
        # Use close_price if available and require_candle_close is enabled
        if self.require_candle_close and close_price:
            check_price = close_price
        else:
            check_price = current_price
        
        # PHASE 1: Capture first 3-min candle (9:15-9:18)
        # Check if this is the first candle ending at 9:18
        now = candle_timestamp if candle_timestamp else now_ist_time()
        first_candle_end = time(9, 18)
        
        # If we're in WAITING_REFERENCE state and it's around 9:18, capture the first candle
        if current_state == TradeState.WAITING_REFERENCE:
            current_time = now.time() if isinstance(now, datetime) else now
            
            # Check if this is the first candle (9:15-9:18)
            if isinstance(current_time, time) and current_time <= time(9, 19):
                # Save first candle data
                self.first_candle[symbol] = {
                    'high': high_price,
                    'low': low_price,
                    'open': open_price,
                    'close': close_price,
                    'volume': volume,
                    'captured_at': now.isoformat() if isinstance(now, datetime) else str(now)
                }
                self._first_candle_formed[symbol] = True
                self.trade_states[symbol] = TradeState.WAITING_BREAKOUT
                logger.info(f"📊 {symbol}: First 3-min candle captured. High: {high_price}, Low: {low_price}, Vol: {volume}")
                return None  # Wait for next candle for breakout
            else:
                # First candle period missed
                logger.warning(f"⚠️ {symbol}: First candle period missed at {current_time}. Cannot trade today.")
                self.trade_states[symbol] = TradeState.EXITED
                return None
        
        # Check if first candle exists (should be in WAITING_BREAKOUT state)
        if symbol not in self.first_candle:
            logger.warning(f"⚠️ {symbol}: No first candle data. Cannot trade.")
            self.trade_states[symbol] = TradeState.EXITED
            return None
        
        # Check entry window
        if not self._is_valid_entry_window():
            return None
        
        # Check trading time (not after 2:30 PM)
        if not self.is_trading_time("09:20", self.no_new_trade_after):
            return None
        
        # PHASE 2: Check for breakout on candle CLOSE
        first_candle = self.first_candle[symbol]
        reference_high = first_candle['high']
        reference_low = first_candle['low']
        reference_volume = first_candle['volume']
        
        # Calculate first candle range %
        first_candle_range_pct = ((reference_high - reference_low) / first_candle['open']) * 100
        
        # Check breakout direction based on signal
        is_breakout = False
        breakout_reason = ""
        
        if signal == 'BULLISH':
            # LONG: Wait for candle to CLOSE above first candle high
            if check_price > reference_high:
                is_breakout = True
                breakout_reason = f"Close above first candle high {reference_high:.2f}"
            else:
                logger.debug(f"{symbol}: LONG waiting for close above {reference_high:.2f}, current close {check_price:.2f}")
                
        elif signal == 'BEARISH':
            # SHORT: Wait for candle to CLOSE below first candle low
            if check_price < reference_low:
                is_breakout = True
                breakout_reason = f"Close below first candle low {reference_low:.2f}"
            else:
                logger.debug(f"{symbol}: SHORT waiting for close below {reference_low:.2f}, current close {check_price:.2f}")
        
        if not is_breakout:
            return None
        
        # Volume confirmation required (only check on breakout)
        volume_confirmed = volume >= (reference_volume * self.volume_breakout_multiplier)
        if not volume_confirmed:
            logger.debug(f"{symbol}: Volume {volume} below threshold {reference_volume * self.volume_breakout_multiplier:.0f}")
            return None
        
        # All conditions met - generate entry signal
        entry_price = check_price
        
        # Calculate stop loss and target based on first candle
        stop_loss, target = self._calculate_sl_target_v2(symbol, signal, entry_price, first_candle_range_pct)
        
        # Validate SL is in correct direction
        if signal == 'BULLISH' and stop_loss >= entry_price:
            logger.error(f"❌ {symbol}: Invalid SL for LONG - SL {stop_loss} >= Entry {entry_price}")
            return None
        elif signal == 'BEARISH' and stop_loss <= entry_price:
            logger.error(f"❌ {symbol}: Invalid SL for SHORT - SL {stop_loss} <= Entry {entry_price}")
            return None
        
        # Determine trade action
        if signal == 'BULLISH':
            action = 'BUY'
            direction = 'LONG'
        else:  # BEARISH
            action = 'SELL'
            direction = 'SHORT'
        
        gap = self.gap_percent.get(symbol, 0)
        nifty_change = self.nifty_tracker.get_change_percent()
        
        # Mark as triggered and update state machine
        self.trade_states[symbol] = TradeState.ENTERED
        self.trades_today += 1
        
        logger.info(
            f"🎯 3-MIN ENTRY: {symbol} | {action} ({direction})\n"
            f"   Gap: {gap:+.2f}% | Nifty: {nifty_change:+.2f}%\n"
            f"   Entry: ₹{entry_price:.2f} | SL: ₹{stop_loss:.2f} | "
            f"Target: ₹{target:.2f}\n"
            f"   First Candle Range: {first_candle_range_pct:.2f}% | Volume: {volume}\n"
            f"   Reason: {breakout_reason}"
        )
        
        return {
            'action': action,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'reason': f"3-Min Breakout - {breakout_reason}",
            'signal_type': signal,
            'gap_percent': gap,
            'nifty_trend': self.nifty_tracker.trend,
            'nifty_change': nifty_change,
            'first_candle': first_candle
        }
    
    def _calculate_sl_target(self, symbol: str, signal: str, entry_price: float) -> Tuple[float, float]:
        """
        Calculate stop loss and target based on opening range and configured percentages.
        
        Priority:
        1. Use opening range high/low as SL (if available)
        2. Fall back to percentage-based SL
        
        Target is calculated based on the configured target_percent (fixed at entry).
        """
        range_data = self.opening_range.get(symbol, {})
        
        if signal == 'BULLISH':
            # For longs: SL below opening range low
            if range_data and 'low' in range_data:
                stop_loss = range_data['low'] - 0.5  # Small buffer
            else:
                stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            
            # Calculate target based on fixed target_percent (NOT risk-reward ratio)
            target = entry_price * (1 + self.target_percent / 100)
            
        else:  # BEARISH
            # For shorts: SL above opening range high
            if range_data and 'high' in range_data:
                stop_loss = range_data['high'] + 0.5  # Small buffer
            else:
                stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            
            # Calculate target based on fixed target_percent (NOT risk-reward ratio)
            target = entry_price * (1 - self.target_percent / 100)
        
        # Validate SL is not too wide
        max_sl_amount = entry_price * (self.max_sl_percent / 100)
        
        if signal == 'BULLISH' and (entry_price - stop_loss) > max_sl_amount:
            stop_loss = entry_price - max_sl_amount
            # Recalculate target based on target_percent after SL adjustment
            target = entry_price * (1 + self.target_percent / 100)
        elif signal == 'BEARISH' and (stop_loss - entry_price) > max_sl_amount:
            stop_loss = entry_price + max_sl_amount
            # Recalculate target based on target_percent after SL adjustment
            target = entry_price * (1 - self.target_percent / 100)
        
        return round(stop_loss, 2), round(target, 2)
    
    def _calculate_sl_target_v2(self, symbol: str, signal: str, entry_price: float, 
                                 first_candle_range_pct: float) -> Tuple[float, float]:
        """
        Calculate stop loss and target based on first candle logic.
        
        NEW LOGIC:
        - If first candle range < 1%: SL at first candle high/low
        - If first candle range > 1%: SL at entry ± 1% (fallback)
        - Target: Entry ± target_percent (default 1%)
        
        Args:
            symbol: Stock symbol
            signal: 'BULLISH' or 'BEARISH'
            entry_price: Entry price
            first_candle_range_pct: First candle range as percentage
            
        Returns:
            Tuple of (stop_loss, target)
        """
        first_candle = self.first_candle.get(symbol, {})
        
        if signal == 'BULLISH':
            # LONG trade
            if first_candle_range_pct <= self.first_candle_sl_threshold:
                # Normal first candle - use first candle low as SL
                stop_loss = first_candle.get('low', entry_price * 0.99)
            else:
                # First candle too large - use 1% fallback
                stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            
            # Target: entry + target_percent
            target = entry_price * (1 + self.target_percent / 100)
            
        else:  # BEARISH
            # SHORT trade
            if first_candle_range_pct <= self.first_candle_sl_threshold:
                # Normal first candle - use first candle high as SL
                stop_loss = first_candle.get('high', entry_price * 1.01)
            else:
                # First candle too large - use 1% fallback
                stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            
            # Target: entry - target_percent
            target = entry_price * (1 - self.target_percent / 100)
        
        return round(stop_loss, 2), round(target, 2)
    
    def check_exit_signal(self, position: Dict, current_price: float,
                          indicators: Dict) -> Optional[Dict]:
        """
        Check for exit conditions with state machine update and daily loss tracking.
        
        Exit triggers:
        1. Target hit - Take profit at target level
        2. Stop loss hit - Cut loss at SL level
        3. Time-based exit (3:15 PM) - Square off all positions
        
        Daily Drawdown Guard:
        - Counts completed losing trades (not unrealized P&L)
        - Stops new entries after max_daily_losses losing trades
        - Resets daily at market open
        
        State Machine Update:
        - On exit: Sets state to EXITED (prevents re-entry for this stock today)
        - Tracks P&L for completed trades
        
        Args:
            position: Current position data
            current_price: Current price
            indicators: Indicator values
            
        Returns:
            Exit signal dict or None
        """
        symbol = position.get('symbol', 'UNKNOWN')
        entry_price = position.get('entry_price', current_price)
        stop_loss = position.get('stop_loss', 0)
        target = position.get('target', 0)
        direction = position.get('direction', 'LONG')
        
        # Calculate P&L
        if direction == 'LONG':
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        exit_signal = None
        
        # 1. Check target hit
        if direction == 'LONG' and current_price >= target:
            logger.info(f"🎯 TARGET HIT: {symbol} | P&L: +{pnl_percent:.2f}%")
            exit_signal = {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'TARGET',
                'pnl_percent': pnl_percent
            }
        elif direction == 'SHORT' and current_price <= target:
            logger.info(f"🎯 TARGET HIT: {symbol} | P&L: +{pnl_percent:.2f}%")
            exit_signal = {
                'action': 'BUY',
                'exit_price': current_price,
                'reason': 'TARGET',
                'pnl_percent': pnl_percent
            }
        
        # 2. Check stop loss hit
        elif direction == 'LONG' and current_price <= stop_loss:
            logger.info(f"🛑 STOP LOSS: {symbol} | P&L: {pnl_percent:.2f}%")
            exit_signal = {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'STOP_LOSS',
                'pnl_percent': pnl_percent
            }
        elif direction == 'SHORT' and current_price >= stop_loss:
            logger.info(f"🛑 STOP LOSS: {symbol} | P&L: {pnl_percent:.2f}%")
            exit_signal = {
                'action': 'BUY',
                'exit_price': current_price,
                'reason': 'STOP_LOSS',
                'pnl_percent': pnl_percent
            }
        
        # 3. Time-based exit (3:15 PM)
        else:
            now = now_ist_time()
            square_off_time = time(15, 15)
            
            if now >= square_off_time:
                action = 'SELL' if direction == 'LONG' else 'BUY'
                logger.info(f"⏰ SQUARE-OFF: {symbol} | P&L: {pnl_percent:.2f}%")
                exit_signal = {
                    'action': action,
                    'exit_price': current_price,
                    'reason': 'TIME',
                    'pnl_percent': pnl_percent
                }
        
        # Process exit signal and update state machine
        if exit_signal:
            # Update state machine - mark as exited (locked for rest of day)
            self.trade_states[symbol] = TradeState.EXITED
            
            # Track P&L for this completed trade
            self.trade_pnl[symbol] = pnl_percent
            
            # Daily Drawdown Guard: Count completed losing trades
            # This stops trading after max_daily_losses losing trades
            # Note: We count completed trades only, not unrealized P&L
            if pnl_percent < 0:
                self.daily_losses += 1
                logger.warning(f"⚠️ Daily loss #{self.daily_losses}/{self.max_daily_losses}: {symbol} {pnl_percent:.2f}%")
                
                if self.daily_losses >= self.max_daily_losses:
                    logger.error(f"🚫 DAILY LOSS LIMIT REACHED: {self.daily_losses} losses. Stopping new trades for today.")
            else:
                logger.info(f"✅ Winning trade: {symbol} +{pnl_percent:.2f}%")
            
            return exit_signal
        
        return None
    
    def calculate_entry_points(self, stock: Dict) -> Dict:
        """
        Calculate entry points for a stock (used during analysis).
        
        For 3-minute strategy, entry is based on opening range breakout.
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        signal = stock.get('signal_type', stock.get('gap_type', 'BULLISH'))
        price = stock.get('price', stock.get('ltp', stock.get('iep', 0)))
        
        if price <= 0:
            price = stock.get('prev_close', 1000)
        
        # Use gap percentage or default
        gap = stock.get('gap_percent', 0)
        
        # Calculate entry based on signal using configured stop_loss_percent and target_percent
        if signal == 'BULLISH':
            entry_price = price * 1.001  # Slight buffer above
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            target_price = entry_price * (1 + self.target_percent / 100)
        else:  # BEARISH
            entry_price = price * 0.999  # Slight buffer below
            stop_loss = entry_price * (1 + self.stop_loss_percent / 100)
            target_price = entry_price * (1 - self.target_percent / 100)
        
        return {
            'entry_price': round(entry_price, 2),
            'stop_loss': round(stop_loss, 2),
            'target_price': round(target_price, 2),
            'gap_percent': gap,
            'signal_type': signal,
            'stop_loss_percent': self.stop_loss_percent,
            'target_percent': self.target_percent
        }
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status for monitoring."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'gap_candidates': {
                'bullish': [s for s, sig in self.gap_signals.items() if sig == 'BULLISH'],
                'bearish': [s for s, sig in self.gap_signals.items() if sig == 'BEARISH']
            },
            'gap_percentages': self.gap_percent.copy(),
            'opening_ranges': self.opening_range.copy(),
            'trades_today': self.trades_today,
            'max_trades': self.max_trades_per_day,
            'is_entry_window': self._is_valid_entry_window(),
            'is_opening_range_period': self._is_opening_range_period(),
            'nifty': self.nifty_tracker.get_status(),
            'config': {
                'min_gap': self.min_gap_percent,
                'entry_window': f"{self.entry_window_start} - {self.entry_window_end}",
                'r_r_ratio': self.risk_reward_ratio,
                'require_nifty_alignment': self.require_nifty_alignment
            }
        }
