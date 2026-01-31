"""OHL Strategy - Open=High or Open=Low trading strategy"""

from datetime import datetime, time, timedelta
from typing import Dict, Optional, List
from loguru import logger

from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry
from src.core.config_manager import get_config
from src.analysis.nifty_tracker import get_nifty_tracker
from src.utils.timezone import now_ist, now_ist_time


@StrategyRegistry.register(
    name="ohl",
    display_name="OHL (Open=High/Low)",
    description="Trade based on first candle Open=High (bearish) or Open=Low (bullish) pattern with Nifty correlation",
    stock_picker="ohl",
    default_params={
        "buffer_percent": 0.06,
        "entry_window_start": "09:30",
        "entry_window_end": "09:45",
        "require_nifty_alignment": True,
        "risk_reward_ratio": 1.5
    }
)
class OHLStrategy(BaseStrategy):
    """
    OHL (Open = High or Open = Low) Strategy for intraday trading.
    
    Core Logic:
    - Bullish Signal: When Open = Low (buyers in control from open)
    - Bearish Signal: When Open = High (sellers in control from open)
    - Uses 0.06% buffer tolerance for matching
    
    Entry Rules:
    1. Wait until 9:30-9:45 AM (confirm OHL pattern is holding)
    2. Check Nifty trend alignment (bullish market = only longs)
    3. Wait for range breakout (break above/below 15-min range)
    4. Confirm OHL condition still valid at entry
    
    Exit Rules:
    - Stop Loss: Day's High (for short) or Low (for long), or 10-min range
    - Target: 1:1.5 to 1:2 Risk-Reward ratio
    - OHL Invalidation: New high above open (for shorts)
    - Time Exit: 3:15 PM square off
    """
    
    # Class-level metadata
    display_name = "OHL (Open=High/Low)"
    description = "Trade based on first candle Open=High (bearish) or Open=Low (bullish) pattern"
    
    def __init__(self):
        super().__init__("ohl")
        self.config = get_config()
        self.nifty_tracker = get_nifty_tracker()
        
        # Get strategy params from config
        strategy_params = self.config.get('strategies.ohl.params', {})
        
        # OHL-specific parameters
        self.buffer_percent = strategy_params.get('buffer_percent', 0.06)
        self.entry_window_start = strategy_params.get('entry_window_start', '09:30')
        self.entry_window_end = strategy_params.get('entry_window_end', '09:45')
        self.require_nifty_alignment = strategy_params.get('require_nifty_alignment', True)
        self.use_range_breakout = strategy_params.get('use_range_breakout', True)
        self.range_period_minutes = strategy_params.get('range_period_minutes', 15)
        self.use_10min_sl = strategy_params.get('use_10min_sl', True)
        self.risk_reward_ratio = strategy_params.get('risk_reward_ratio', 1.5)
        self.max_sl_percent = strategy_params.get('max_sl_percent', 2.0)
        
        # General trading params
        self.stop_loss_percent = strategy_params.get('stop_loss_percent', 1.0)
        self.target_percent = strategy_params.get('target_percent', 1.5)
        self.max_trades_per_day = strategy_params.get('max_trades_per_day', 3)
        
        # State tracking per symbol
        self.ohl_signals: Dict[str, str] = {}  # symbol -> 'BULLISH' or 'BEARISH'
        self.opening_range: Dict[str, Dict] = {}  # symbol -> {high, low}
        self.first_10min_range: Dict[str, Dict] = {}  # symbol -> {high, low}
        self.ohl_detected_time: Dict[str, datetime] = {}
        self.trades_today = 0
    
    def reset_daily(self) -> None:
        """Reset all daily state.
        
        Note: NiftyIndexTracker is NOT reset here because it's a singleton
        shared across strategies. It should only be reset in bot.py's global
        daily reset to avoid wiping valid data when switching strategies mid-day.
        """
        self.ohl_signals.clear()
        self.opening_range.clear()
        self.first_10min_range.clear()
        self.ohl_detected_time.clear()
        self.trades_today = 0
        logger.info("🔄 OHL Strategy daily state reset")
    
    def _detect_ohl_signal(self, stock: Dict, _current_price: float) -> Optional[str]:
        """
        Detect if stock has O=H or O=L pattern.
        
        Args:
            stock: Stock data with OHLC
            _current_price: Current LTP (intentionally unused; kept for interface 
                          compatibility with other strategy signal detection methods)
            
        Returns:
            'BULLISH' (O=L), 'BEARISH' (O=H), or None
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        open_price = stock.get('open', 0)
        high_price = stock.get('high', 0)
        low_price = stock.get('low', 0)
        
        if open_price <= 0:
            return None
        
        buffer = open_price * (self.buffer_percent / 100)
        
        # Check O=H (bearish) - price hasn't gone above open
        if abs(open_price - high_price) <= buffer:
            if symbol not in self.ohl_signals or self.ohl_signals[symbol] != 'BEARISH':
                logger.info(f"📉 {symbol}: O=H detected (bearish signal)")
                self.ohl_detected_time[symbol] = now_ist()
            return 'BEARISH'
        
        # Check O=L (bullish) - price hasn't gone below open
        if abs(open_price - low_price) <= buffer:
            if symbol not in self.ohl_signals or self.ohl_signals[symbol] != 'BULLISH':
                logger.info(f"📈 {symbol}: O=L detected (bullish signal)")
                self.ohl_detected_time[symbol] = now_ist()
            return 'BULLISH'
        
        # Pattern broken if it was previously detected
        if symbol in self.ohl_signals:
            logger.info(f"❌ {symbol}: OHL pattern invalidated")
            del self.ohl_signals[symbol]
        
        return None
    
    def _is_valid_entry_window(self) -> bool:
        """Check if current time is within entry window (e.g. 9:30-9:45).
        
        Note:
            This uses only `time` objects (no date context). Windows that span
            midnight (e.g. "23:50"-"00:10") are not supported.
        
        Returns:
            True if current time is within entry window, False otherwise
        """
        now = now_ist_time()
        try:
            start = datetime.strptime(self.entry_window_start, "%H:%M").time()
            end = datetime.strptime(self.entry_window_end, "%H:%M").time()
        except (TypeError, ValueError) as e:
            logger.error(
                f"Invalid entry window configuration: "
                f"start={self.entry_window_start!r}, end={self.entry_window_end!r}: {e}"
            )
            return False
        
        # Reject windows where end is before start (midnight-spanning not supported)
        if end < start:
            logger.error(
                f"Invalid entry window (end before start, midnight-spanning "
                f"windows not supported): start={start}, end={end}"
            )
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
    
    def _update_opening_range(self, symbol: str, high: float, low: float) -> None:
        """Track the first 15-minute opening range"""
        now = now_ist_time()
        range_end = time(9, 15 + self.range_period_minutes)
        
        if now <= range_end:
            if symbol not in self.opening_range:
                self.opening_range[symbol] = {'high': high, 'low': low}
            else:
                self.opening_range[symbol]['high'] = max(self.opening_range[symbol]['high'], high)
                self.opening_range[symbol]['low'] = min(self.opening_range[symbol]['low'], low)
    
    def _update_10min_range(self, symbol: str, high: float, low: float) -> None:
        """Track the first 10-minute range (for tighter SL)"""
        now = now_ist_time()
        range_end = time(9, 25)  # 9:15 + 10 min
        
        if now <= range_end:
            if symbol not in self.first_10min_range:
                self.first_10min_range[symbol] = {'high': high, 'low': low}
            else:
                self.first_10min_range[symbol]['high'] = max(self.first_10min_range[symbol]['high'], high)
                self.first_10min_range[symbol]['low'] = min(self.first_10min_range[symbol]['low'], low)
    
    def _check_range_breakout(self, symbol: str, current_price: float, signal: str) -> bool:
        """
        Check if price has broken out of opening range.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            signal: 'BULLISH' or 'BEARISH'
            
        Returns:
            True if breakout confirmed
        """
        if not self.use_range_breakout:
            return True  # Skip breakout check if disabled
        
        if symbol not in self.opening_range:
            return False
        
        range_high = self.opening_range[symbol]['high']
        range_low = self.opening_range[symbol]['low']
        
        if signal == 'BULLISH':
            # For longs, need price above range high
            breakout = current_price > range_high
            if breakout:
                logger.info(f"📈 {symbol}: Breakout above range high {range_high:.2f}")
            return breakout
        elif signal == 'BEARISH':
            # For shorts, need price below range low
            breakout = current_price < range_low
            if breakout:
                logger.info(f"📉 {symbol}: Breakdown below range low {range_low:.2f}")
            return breakout
        
        return False
    
    def _is_ohl_still_valid(self, stock: Dict, signal: str) -> bool:
        """
        Check if OHL pattern is still valid at entry time.
        
        For shorts (O=H): High should not have exceeded open
        For longs (O=L): Low should not have gone below open
        """
        open_price = stock.get('open', 0)
        high_price = stock.get('high', 0)
        low_price = stock.get('low', 0)
        
        if open_price <= 0:
            return False
        
        buffer = open_price * (self.buffer_percent / 100)
        
        if signal == 'BEARISH':
            # O=H should still hold
            return abs(open_price - high_price) <= buffer
        elif signal == 'BULLISH':
            # O=L should still hold
            return abs(open_price - low_price) <= buffer
        
        return False
    
    def check_entry_signal(self, stock: Dict, current_price: float,
                          indicators: Dict) -> Optional[Dict]:
        """
        Check for OHL entry signals.
        
        Entry requires ALL conditions:
        1. ✅ Not in initial volatility period (after 9:16)
        2. ✅ O=H or O=L pattern detected
        3. ✅ Within entry window (9:30-9:45)
        4. ✅ Nifty trend alignment
        5. ✅ Range breakout confirmed
        6. ✅ OHL pattern still valid
        7. ✅ Not exceeded max trades per day
        
        Args:
            stock: Stock data
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
        
        # Check trading time (not in first 15 min)
        if self.is_initial_volatility_period():
            return None
        
        # Check not after 3 PM
        if not self.is_trading_time("09:30", "15:00"):
            return None
        
        # Get OHLC data
        open_price = stock.get('open', indicators.get('open', 0))
        high_price = stock.get('high', indicators.get('high', 0))
        low_price = stock.get('low', indicators.get('low', 0))
        
        if open_price <= 0:
            return None
        
        # Update ranges
        self._update_opening_range(symbol, high_price, low_price)
        self._update_10min_range(symbol, high_price, low_price)
        
        # Step 1: Detect OHL signal
        signal = self._detect_ohl_signal(stock, current_price)
        if signal:
            self.ohl_signals[symbol] = signal
        else:
            # Pattern not present or broken
            return None
        
        # Step 2: Check entry window
        if not self._is_valid_entry_window():
            logger.debug(f"{symbol}: Outside entry window")
            return None
        
        # Step 3: Check Nifty alignment
        if not self._check_nifty_alignment(signal):
            return None
        
        # Step 4: Check range breakout
        if not self._check_range_breakout(symbol, current_price, signal):
            return None
        
        # Step 5: Confirm OHL still valid
        if not self._is_ohl_still_valid(stock, signal):
            logger.info(f"❌ {symbol}: OHL pattern invalidated at entry")
            return None
        
        # All conditions met - generate entry signal
        entry_price = current_price
        
        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(stock, signal, entry_price)
        
        # Calculate target based on risk-reward
        risk = abs(entry_price - stop_loss)
        
        if signal == 'BULLISH':
            target = entry_price + (risk * self.risk_reward_ratio)
            action = 'BUY'
        else:  # BEARISH
            target = entry_price - (risk * self.risk_reward_ratio)
            action = 'SELL'  # Short sell
        
        # Safety check: SL not too wide
        sl_percent = (risk / entry_price) * 100
        if sl_percent > self.max_sl_percent:
            logger.warning(f"{symbol}: SL {sl_percent:.2f}% too wide, capping")
            risk = entry_price * (self.max_sl_percent / 100)
            if signal == 'BULLISH':
                stop_loss = entry_price - risk
                target = entry_price + (risk * self.risk_reward_ratio)
            else:
                stop_loss = entry_price + risk
                target = entry_price - (risk * self.risk_reward_ratio)
        
        nifty_change = self.nifty_tracker.get_change_percent()
        
        logger.info(
            f"🎯 {symbol}: OHL Entry Signal - {action}\n"
            f"   Signal: {signal}, Nifty: {nifty_change:+.2f}%\n"
            f"   Entry: ₹{entry_price:.2f}, SL: ₹{stop_loss:.2f}, "
            f"Target: ₹{target:.2f} (R:R = 1:{self.risk_reward_ratio})"
        )
        
        self.trades_today += 1
        
        return {
            'action': action,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'reason': f"OHL {signal} - Range Breakout",
            'signal_type': signal,
            'nifty_trend': self.nifty_tracker.trend,
            'nifty_change': nifty_change
        }
    
    def _calculate_stop_loss(self, stock: Dict, signal: str, entry_price: float) -> float:
        """
        Calculate stop loss based on strategy rules.
        
        Priority:
        1. Use 10-min range high/low if available and use_10min_sl=True
        2. Use day's high/low
        3. Fallback to percentage-based SL
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        high_price = stock.get('high', 0)
        low_price = stock.get('low', 0)
        
        if signal == 'BULLISH':
            # For longs, SL is below low
            if self.use_10min_sl and symbol in self.first_10min_range:
                sl = self.first_10min_range[symbol]['low'] - 0.5  # Small buffer
            else:
                sl = low_price - 0.5
        else:  # BEARISH
            # For shorts, SL is above high
            if self.use_10min_sl and symbol in self.first_10min_range:
                sl = self.first_10min_range[symbol]['high'] + 0.5
            else:
                sl = high_price + 0.5
        
        # Validate SL is reasonable
        max_sl_amount = entry_price * (self.max_sl_percent / 100)
        
        if signal == 'BULLISH' and (entry_price - sl) > max_sl_amount:
            sl = entry_price - max_sl_amount
        elif signal == 'BEARISH' and (sl - entry_price) > max_sl_amount:
            sl = entry_price + max_sl_amount
        
        return sl
    
    def check_exit_signal(self, position: Dict, current_price: float,
                         indicators: Dict) -> Optional[Dict]:
        """
        Check for exit conditions.
        
        Exit triggers:
        1. Target hit
        2. Stop loss hit
        3. OHL pattern invalidated
        4. Time-based exit (3:15 PM)
        
        Args:
            position: Current position data
            current_price: Current price
            indicators: Indicator values
            
        Returns:
            Exit signal dict or None
        """
        symbol = position.get('symbol', 'UNKNOWN')
        stop_loss = position.get('stop_loss', 0)
        target = position.get('target', 0)
        direction = position.get('direction', 'LONG')
        
        # 1. Check target hit
        if direction == 'LONG' and current_price >= target:
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'TARGET'
            }
        elif direction == 'SHORT' and current_price <= target:
            return {
                'action': 'BUY',  # Buy to cover short
                'exit_price': current_price,
                'reason': 'TARGET'
            }
        
        # 2. Check stop loss hit
        if direction == 'LONG' and current_price <= stop_loss:
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'STOP_LOSS'
            }
        elif direction == 'SHORT' and current_price >= stop_loss:
            return {
                'action': 'BUY',
                'exit_price': current_price,
                'reason': 'STOP_LOSS'
            }
        
        # 3. Check OHL invalidation
        open_price = indicators.get('open', 0)
        high_price = indicators.get('high', 0)
        low_price = indicators.get('low', 0)
        
        if open_price > 0:
            buffer = open_price * (self.buffer_percent / 100)
            
            if direction == 'SHORT':
                # For short, if high goes above open, pattern broken
                if high_price > open_price + buffer:
                    logger.warning(f"❌ {symbol}: O=H invalidated - new high above open")
                    return {
                        'action': 'BUY',
                        'exit_price': current_price,
                        'reason': 'SIGNAL'  # Pattern invalidation
                    }
            elif direction == 'LONG':
                # For long, if low goes below open, pattern broken
                if low_price < open_price - buffer:
                    logger.warning(f"❌ {symbol}: O=L invalidated - new low below open")
                    return {
                        'action': 'SELL',
                        'exit_price': current_price,
                        'reason': 'SIGNAL'
                    }
        
        # 4. Time-based exit (3:15 PM)
        now = now_ist_time()
        square_off_time = time(15, 15)
        
        if now >= square_off_time:
            action = 'SELL' if direction == 'LONG' else 'BUY'
            return {
                'action': action,
                'exit_price': current_price,
                'reason': 'TIME'
            }
        
        return None
    
    def calculate_entry_points(self, stock: Dict) -> Dict:
        """
        Calculate entry points for a stock (used during analysis).
        
        For OHL, this is more dynamic and depends on real-time data,
        but we can provide estimates based on ATR.
        """
        price = stock.get('price', stock.get('ltp', stock.get('close', 0)))
        atr = stock.get('atr', price * 0.015)  # Default 1.5% if no ATR
        
        # Estimate entry at current price
        entry_price = price
        
        # SL based on ATR or max_sl_percent
        sl_amount = min(atr, price * (self.max_sl_percent / 100))
        stop_loss = entry_price - sl_amount
        
        # Target based on R:R
        target_price = entry_price + (sl_amount * self.risk_reward_ratio)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'atr': atr,
            'sl_percent': (sl_amount / entry_price) * 100
        }
    
    def get_ohl_status(self) -> Dict:
        """Get current OHL detection status for all stocks"""
        return {
            'detected_signals': self.ohl_signals.copy(),
            'opening_ranges': self.opening_range.copy(),
            'trades_today': self.trades_today,
            'nifty': self.nifty_tracker.get_status()
        }
