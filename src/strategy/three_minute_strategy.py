"""3-Minute Strategy - Pre-Open Market Gap Trading Strategy

Analysis of the Pre-Open Market Intraday Trading Strategy
=========================================================

This strategy leverages pre-open market data to identify high-momentum intraday trades
based on gap-up and gap-down patterns.

Core Concept:
- Scan NSE pre-open session (9:00-9:08 AM) for stocks with significant gaps
- Gap Up = Bullish (price opens higher than previous close)
- Gap Down = Bearish (price opens lower than previous close)
- Wait for confirmation after market opens (candle breakout)
- Execute trades in the direction of the gap momentum

Workflow:
1. PRE-MARKET (9:00-9:08 AM): Fetch pre-open data, identify top gap stocks
2. PRICE MATCHING (9:08-9:15 AM): Confirm opening prices, finalize watchlist
3. POST-OPEN (9:15-9:20 AM): Wait for initial volatility to settle
4. ENTRY WINDOW (9:20-10:30 AM): Look for candle breakout confirmation
5. TRADING (Till 15:00): Monitor positions, trail stops
6. SQUARE-OFF (15:15 PM): Close all positions

Entry Rules:
- Gap Up (LONG): Wait for price to break above first 3-5 minute high
- Gap Down (SHORT): Wait for price to break below first 3-5 minute low
- Volume should be higher than average
- Confirm with Nifty trend alignment

Exit Rules:
- Stop Loss: Below/above the opening range high/low
- Target: 1:2 or 1:3 Risk-Reward ratio
- Time Exit: 15:15 PM square-off

Author: Trading Bot System
Version: 1.0
"""

from datetime import datetime, time, timedelta
from typing import Dict, Optional, List, Tuple
from loguru import logger

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry
from src.core.config_manager import get_config
from src.analysis.nifty_tracker import get_nifty_tracker
from src.utils.timezone import now_ist, now_ist_time


@StrategyRegistry.register(
    name="three_minute",
    display_name="3-Minute Strategy (Pre-Open Gap)",
    description="Trade gap-up/gap-down stocks identified from pre-open session with candle breakout confirmation",
    stock_picker="preopen_gap",
    default_params={
        "min_gap_percent": 1.0,
        "max_gap_percent": 8.0,
        "entry_window_start": "09:20",
        "entry_window_end": "10:30",
        "stop_loss_percent": 1.0,
        "target_percent": 2.0,
        "risk_reward_ratio": 2.0,
        "require_nifty_alignment": True,
        "use_opening_range_breakout": True,
        "opening_range_minutes": 5,
        "max_trades_per_day": 5
    }
)
class ThreeMinuteStrategy(BaseStrategy):
    """
    3-Minute Strategy - Pre-Open Market Gap Trading Strategy.
    
    This strategy is based on analyzing gaps from the pre-open market session
    and trading in the direction of the gap with confirmation.
    
    Key Features:
    - Uses NSE pre-open data (9:00-9:08 AM) to identify gap candidates
    - Waits for candle breakout confirmation after market opens
    - Supports both LONG (gap up) and SHORT (gap down) trades
    - Uses opening range breakout for entry confirmation
    - Implements strict risk management with R:R ratio
    
    Signal Types:
    - BULLISH (Gap Up): Price opens significantly above previous close
    - BEARISH (Gap Down): Price opens significantly below previous close
    
    Trade Direction:
    - LONG: Buy gap-up stocks after breakout above opening range
    - SHORT: Sell gap-down stocks after breakdown below opening range
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
        self.target_percent = strategy_params.get('target_percent', 2.0)
        self.risk_reward_ratio = strategy_params.get('risk_reward_ratio', 2.0)
        self.max_sl_percent = strategy_params.get('max_sl_percent', 2.0)
        
        # Strategy options
        self.require_nifty_alignment = strategy_params.get('require_nifty_alignment', True)
        self.use_opening_range_breakout = strategy_params.get('use_opening_range_breakout', True)
        self.opening_range_minutes = strategy_params.get('opening_range_minutes', 5)
        self.max_trades_per_day = strategy_params.get('max_trades_per_day', 5)
        
        # State tracking per symbol
        self.gap_signals: Dict[str, str] = {}  # symbol -> 'BULLISH' or 'BEARISH'
        self.gap_percent: Dict[str, float] = {}  # symbol -> gap percentage
        self.opening_range: Dict[str, Dict] = {}  # symbol -> {high, low, open}
        self.entry_triggered: Dict[str, bool] = {}  # symbol -> already entered
        self.trades_today = 0
        
        # Opening range tracking
        self._opening_range_end: Optional[time] = None
        
    def reset_daily(self) -> None:
        """
        Reset all daily state.
        
        Called at the start of each trading day.
        """
        self.gap_signals.clear()
        self.gap_percent.clear()
        self.opening_range.clear()
        self.entry_triggered.clear()
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
                          indicators: Dict) -> Optional[Dict]:
        """
        Check for 3-Minute Strategy entry signals.
        
        Entry requires ALL conditions:
        1. ✅ Stock is in gap candidates list
        2. ✅ Not in initial volatility period (first 5 min after open)
        3. ✅ Within entry window (9:20-10:30)
        4. ✅ Nifty trend alignment (optional)
        5. ✅ Opening range breakout confirmed
        6. ✅ Not already triggered for this stock
        7. ✅ Not exceeded max trades per day
        
        Args:
            stock: Stock data with gap info
            current_price: Current LTP
            indicators: Indicator values
            
        Returns:
            Entry signal dict or None
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        
        # Check if strategy is active
        if not self.is_active:
            return None
        
        # Check max trades
        if self.trades_today >= self.max_trades_per_day:
            return None
        
        # Check if already triggered for this stock
        if self.entry_triggered.get(symbol, False):
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
        
        # Get OHLC data
        open_price = stock.get('open', indicators.get('open', current_price))
        high_price = stock.get('high', indicators.get('high', current_price))
        low_price = stock.get('low', indicators.get('low', current_price))
        
        # Update opening range if still forming
        if self._is_opening_range_period():
            self._update_opening_range(symbol, high_price, low_price, open_price)
            return None  # Wait for range to form
        
        # Check entry window
        if not self._is_valid_entry_window():
            return None
        
        # Check trading time (not after 3 PM)
        if not self.is_trading_time("09:20", "15:00"):
            return None
        
        # Check Nifty alignment
        if not self._check_nifty_alignment(signal):
            return None
        
        # Check opening range breakout
        is_breakout, breakout_reason = self._check_opening_range_breakout(symbol, current_price, signal)
        if not is_breakout:
            logger.debug(f"{symbol}: {breakout_reason}")
            return None
        
        # All conditions met - generate entry signal
        entry_price = current_price
        
        # Calculate stop loss and target
        stop_loss, target = self._calculate_sl_target(symbol, signal, entry_price)
        
        # Determine trade action
        if signal == 'BULLISH':
            action = 'BUY'
            direction = 'LONG'
        else:  # BEARISH
            action = 'SELL'
            direction = 'SHORT'
        
        gap = self.gap_percent.get(symbol, 0)
        nifty_change = self.nifty_tracker.get_change_percent()
        
        # Mark as triggered
        self.entry_triggered[symbol] = True
        self.trades_today += 1
        
        logger.info(
            f"🎯 3-MIN ENTRY: {symbol} | {action} ({direction})\n"
            f"   Gap: {gap:+.2f}% | Nifty: {nifty_change:+.2f}%\n"
            f"   Entry: ₹{entry_price:.2f} | SL: ₹{stop_loss:.2f} | "
            f"Target: ₹{target:.2f}\n"
            f"   Reason: {breakout_reason}"
        )
        
        return {
            'action': action,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'reason': f"3-Min Gap {signal} - {breakout_reason}",
            'signal_type': signal,
            'gap_percent': gap,
            'nifty_trend': self.nifty_tracker.trend,
            'nifty_change': nifty_change,
            'opening_range': self.opening_range.get(symbol, {})
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
    
    def check_exit_signal(self, position: Dict, current_price: float,
                         indicators: Dict) -> Optional[Dict]:
        """
        Check for exit conditions.
        
        Exit triggers:
        1. Target hit
        2. Stop loss hit
        3. Gap direction violated (price goes opposite to gap)
        4. Time-based exit (3:15 PM)
        
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
        
        # 1. Check target hit
        if direction == 'LONG' and current_price >= target:
            logger.info(f"🎯 TARGET HIT: {symbol} | P&L: +{pnl_percent:.2f}%")
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'TARGET',
                'pnl_percent': pnl_percent
            }
        elif direction == 'SHORT' and current_price <= target:
            logger.info(f"🎯 TARGET HIT: {symbol} | P&L: +{pnl_percent:.2f}%")
            return {
                'action': 'BUY',
                'exit_price': current_price,
                'reason': 'TARGET',
                'pnl_percent': pnl_percent
            }
        
        # 2. Check stop loss hit
        if direction == 'LONG' and current_price <= stop_loss:
            logger.info(f"🛑 STOP LOSS: {symbol} | P&L: {pnl_percent:.2f}%")
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'STOP_LOSS',
                'pnl_percent': pnl_percent
            }
        elif direction == 'SHORT' and current_price >= stop_loss:
            logger.info(f"🛑 STOP LOSS: {symbol} | P&L: {pnl_percent:.2f}%")
            return {
                'action': 'BUY',
                'exit_price': current_price,
                'reason': 'STOP_LOSS',
                'pnl_percent': pnl_percent
            }
        
        # 3. Check gap invalidation
        signal = self.gap_signals.get(symbol)
        range_data = self.opening_range.get(symbol, {})
        
        if signal == 'BULLISH' and direction == 'LONG':
            # If gap-up stock closes below opening range low, gap is invalidated
            if range_data and current_price < range_data.get('low', 0) * 0.995:
                logger.warning(f"❌ {symbol}: Gap UP invalidated - price below opening low")
                return {
                    'action': 'SELL',
                    'exit_price': current_price,
                    'reason': 'SIGNAL',
                    'pnl_percent': pnl_percent
                }
        
        elif signal == 'BEARISH' and direction == 'SHORT':
            # If gap-down stock closes above opening range high, gap is invalidated
            if range_data and current_price > range_data.get('high', 0) * 1.005:
                logger.warning(f"❌ {symbol}: Gap DOWN invalidated - price above opening high")
                return {
                    'action': 'BUY',
                    'exit_price': current_price,
                    'reason': 'SIGNAL',
                    'pnl_percent': pnl_percent
                }
        
        # 4. Time-based exit (3:15 PM)
        now = now_ist_time()
        square_off_time = time(15, 15)
        
        if now >= square_off_time:
            action = 'SELL' if direction == 'LONG' else 'BUY'
            logger.info(f"⏰ SQUARE-OFF: {symbol} | P&L: {pnl_percent:.2f}%")
            return {
                'action': action,
                'exit_price': current_price,
                'reason': 'TIME',
                'pnl_percent': pnl_percent
            }
        
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
