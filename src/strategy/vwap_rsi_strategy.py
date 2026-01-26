"""VWAP + RSI Strategy - Main trading strategy implementation"""

from datetime import datetime
from typing import Dict, Optional, List
from loguru import logger

from .base_strategy import BaseStrategy
from src.core.config_manager import get_config


class VWAPRSIStrategy(BaseStrategy):
    """
    VWAP + RSI Crossover Strategy for intraday trading.
    
    Entry Rules (BUY):
    - Price crosses ABOVE VWAP
    - RSI is between 40-60 (not overbought/oversold)
    - Volume > Average Volume
    - Time is between 9:30 AM - 3:00 PM
    
    Exit Rules (SELL):
    - Price hits TARGET (Entry + target_percent)
    - Price hits STOP-LOSS (Entry - stop_loss_percent)
    - RSI > 70 (overbought)
    - Price crosses BELOW VWAP
    - Time is 3:15 PM (forced square-off)
    """
    
    def __init__(self):
        super().__init__("vwap_rsi")
        self.config = get_config()
        
        # Strategy parameters from config
        self.stop_loss_percent = self.config.stop_loss_percent
        self.target_percent = self.config.target_percent
        self.rsi_oversold = self.config.get('strategy.rsi_oversold', 40)
        self.rsi_overbought = self.config.get('strategy.rsi_overbought', 70)
        
        # Track recent prices for crossover detection
        self.previous_prices: Dict[str, float] = {}
        self.previous_vwap: Dict[str, float] = {}
        
        # Professional enhancements
        self.price_history: Dict[str, List[float]] = {}  # For consolidation detection
        self.price_history_size = 5  # Track last 5 candles
        self.consolidation_threshold = self.config.get('strategy.consolidation_threshold', 0.005)  # 0.5%
        self.volume_breakout_threshold = self.config.get('strategy.volume_breakout_threshold', 1.5)  # 1.5x
        self.use_pivot_confluence = self.config.get('strategy.use_pivot_confluence', True)
        self.require_pivot_confluence = self.config.get('strategy.require_pivot_confluence', False)
    
    def is_hugging_vwap(self, symbol: str, current_price: float, vwap: float) -> bool:
        """
        Detect if price is consolidating ("hugging") around VWAP.
        
        Professional trick: Avoid trading during low-volatility consolidation
        phases which lead to whipsaws and false breakouts.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            vwap: Current VWAP value
        
        Returns:
            True if price is consolidating (should skip trade)
        """
        # Initialize history if needed
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        # Add current price
        self.price_history[symbol].append(current_price)
        
        # Keep only last N candles
        if len(self.price_history[symbol]) > self.price_history_size:
            self.price_history[symbol] = self.price_history[symbol][-self.price_history_size:]
        
        # Need at least 5 data points to  detect pattern
        if len(self.price_history[symbol]) < self.price_history_size:
            return False  # Not enough data, allow trade
        
        # Count how many prices are "hugging" VWAP (within threshold)
        threshold = vwap * self.consolidation_threshold
        hugging_count = sum(
            1 for price in self.price_history[symbol]
            if abs(price - vwap) <= threshold
        )
        
        # If 4+ out of 5 are hugging, it's consolidation
        is_consolidating = hugging_count >= 4
        
        if is_consolidating:
            logger.debug(
                f"{symbol}: Consolidating around VWAP - "
                f"{hugging_count}/{self.price_history_size} candles within "
                f"{self.consolidation_threshold*100:.1f}%"
            )
        
        return is_consolidating
    
    def check_entry_signal(self, stock: Dict, current_price: float, 
                          indicators: Dict) -> Optional[Dict]:
        """
        PROFESSIONAL-GRADE entry signal with multi-layer confirmation.
        
        Entry requires ALL of these filters:
        1. ✅ Candle close above VWAP (not just tick)
        2. ✅ NOT in consolidation phase ("hugging")
        3. ✅ Strong volume surge (1.5x+ average)
        4. ✅ RSI in neutral zone (40-70)
        5. ✅ (Optional) Pivot point confluence
        
        This dramatically reduces false signals and whipsaws.
        
        Args:
            stock: Stock data (symbol, token, pivots, etc.)
            current_price: Current LTP (but we use candle close)
            indicators: Dict with rsi, vwap, volume_ratio, candle_data
            
        Returns:
            Entry signal dict or None
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        
        # Check if strategy is active
        if not self.is_active:
            return None
        
        # Check trading time (no trades in first 15 min or after 3 PM)
        if self.is_initial_volatility_period():
            logger.debug(f"{symbol}: Initial volatility period")
            return None
        
        if not self.is_trading_time("09:30", "15:00"):
            logger.debug(f"{symbol}: Outside trading hours")
            return None
        
        # Get indicator values
        rsi = indicators.get('rsi', 50)
        vwap = indicators.get('vwap', current_price)
        volume_ratio = indicators.get('volume_ratio', 1)
        candle_data = indicators.get('candle_data')  # Professional: wait for candle
        pivots = stock.get('pivots')  # Pivot points from pre-market
        
        # ========== FILTER 1: Candle Close Confirmation ==========
        # CRITICAL: Don't trade on tick noise, wait for candle close
        if not candle_data or not candle_data.get('is_closed'):
            return None  # Candle still forming, wait
        
        candle_close = candle_data['close']
        
        # Initialize previous tracking
        is_first_tick = symbol not in self.previous_prices
        if is_first_tick:
            self.previous_prices[symbol] = vwap  # Use VWAP as baseline
            self.previous_vwap[symbol] = vwap
        
        prev_price = self.previous_prices.get(symbol, vwap)
        prev_vwap = self.previous_vwap.get(symbol, vwap)
        
        # Update tracking (use candle close, not LTP)
        self.previous_prices[symbol] = candle_close
        self.previous_vwap[symbol] = vwap
        
        # ========== FILTER 2: VWAP Crossover ==========
        price_crossed_above = prev_price <= prev_vwap and candle_close > vwap
        first_tick_above_vwap = is_first_tick and candle_close > vwap
        
        if not (price_crossed_above or first_tick_above_vwap):
            return None  # No VWAP cross, no entry
        
        # ========== FILTER 3: Consolidation Detection ==========
        # Professional trick: Skip "hugging" phase (whipsaw zone)
        if self.is_hugging_vwap(symbol, candle_close, vwap):
            logger.info(
                f"{symbol}: ⏸️  SKIPPED - Price consolidating around VWAP "
                f"(whipsaw zone)"
            )
            return None
        
        # ========== FILTER 4: Volume Surge ==========
        # Professional standard: 1.5x minimum for breakout confirmation
        if volume_ratio < self.volume_breakout_threshold:
            logger.debug(
                f"{symbol}: Weak volume {volume_ratio:.2f}x "
                f"(need {self.volume_breakout_threshold}x+ for breakout)"
            )
            return None
        
        # ========== FILTER 5: RSI Zone ==========
        if not (self.rsi_oversold <= rsi <= self.rsi_overbought):
            logger.debug(
                f"{symbol}: RSI {rsi:.1f} outside neutral zone "
                f"({self.rsi_oversold}-{self.rsi_overbought})"
            )
            return None
        
        # ========== FILTER 6: Pivot Confluence (Optional) ==========
        entry_reason = "VWAP Crossover" if price_crossed_above else "Above VWAP Entry"
        has_pivot_confluence = False
        
        if pivots and self.use_pivot_confluence:
            from src.analysis.pivot_calculator import PivotPointCalculator
            calc = PivotPointCalculator()
            
            has_confluence, pivot_reason = calc.check_pivot_confluence(
                current_price=candle_close,
                vwap=vwap,
                pivots=pivots
            )
            
            if has_confluence:
                entry_reason = pivot_reason  # Upgrade to double confirmation
                has_pivot_confluence = True
                logger.info(
                    f"🎯 {symbol}: DOUBLE CONFIRMATION - {pivot_reason}"
                )
            else:
                # STRICT MODE: Require pivot confluence if enabled
                if self.require_pivot_confluence:
                    logger.debug(f"{symbol}: No pivot confluence (strict mode)")
                    return None
        
        # ========== ALL FILTERS PASSED - GENERATE SIGNAL ==========
        atr = indicators.get('atr', 0)
        entry_points = self.calculate_entry_points({
            'close': candle_close,
            'vwap': vwap,
            'atr': atr
        })
        
        logger.info(
            f"📈 ENTRY SIGNAL: {symbol} | {entry_reason} | "
            f"Price=₹{candle_close:.2f} VWAP=₹{vwap:.2f} | "
            f"RSI={rsi:.1f} Vol={volume_ratio:.2f}x ATR={atr:.2f} | "
            f"{'✅ Pivot' if has_pivot_confluence else '⚪ No Pivot'}"
        )
        
        return {
            'action': 'BUY',
            'entry_price': candle_close,  # Use candle close, not tick
            'stop_loss': entry_points['stop_loss'],
            'target': entry_points['target_price'],
            'reason': entry_reason,
            'indicators': {
                'rsi': rsi,
                'vwap': vwap,
                'volume_ratio': volume_ratio,
                'atr': atr,
                'candle': candle_data,
                'pivots': pivots,
                'has_pivot_confluence': has_pivot_confluence
            }
        }
    
    def check_exit_signal(self, position: Dict, current_price: float, 
                         indicators: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.
        
        Args:
            position: Current position data (entry_price, stop_loss, target, etc.)
            current_price: Current LTP
            indicators: Dict with rsi, vwap
            
        Returns:
            Exit signal dict or None
        """
        symbol = position.get('symbol', 'UNKNOWN')
        entry_price = position.get('entry_price', current_price)
        stop_loss = position.get('stop_loss', entry_price * 0.995)
        target = position.get('target', entry_price * 1.01)
        
        rsi = indicators.get('rsi', 50)
        vwap = indicators.get('vwap', current_price)
        
        # ============ EXIT CONDITIONS ============
        
        # 1. TARGET HIT - Price reached profit target
        if current_price >= target:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            logger.info(
                f"🎯 TARGET HIT: {symbol} | "
                f"Entry=${entry_price:.2f} → Exit=${current_price:.2f} | "
                f"P&L={pnl_percent:.2f}%"
            )
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'TARGET',
                'pnl_percent': pnl_percent
            }
        
        # 2. STOP-LOSS HIT - Price dropped below stop-loss
        if current_price <= stop_loss:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            logger.info(
                f"🛑 STOP-LOSS HIT: {symbol} | "
                f"Entry=${entry_price:.2f} → Exit=${current_price:.2f} | "
                f"P&L={pnl_percent:.2f}%"
            )
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'STOP_LOSS',
                'pnl_percent': pnl_percent
            }
        
        # 3. RSI OVERBOUGHT - Take profit when RSI goes above 70
        if rsi > self.rsi_overbought:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            logger.info(
                f"⚠️ RSI OVERBOUGHT: {symbol} | RSI={rsi:.1f} | "
                f"Entry=${entry_price:.2f} → Exit=${current_price:.2f}"
            )
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'RSI_OVERBOUGHT',
                'pnl_percent': pnl_percent
            }
        
        # 4. VWAP BREAKDOWN - Price crossed below VWAP (trend reversal)
        prev_price = self.previous_prices.get(symbol, current_price)
        prev_vwap = self.previous_vwap.get(symbol, vwap)
        
        price_crossed_below_vwap = prev_price >= prev_vwap and current_price < vwap
        
        if price_crossed_below_vwap:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            logger.info(
                f"📉 VWAP BREAKDOWN: {symbol} | "
                f"Entry=${entry_price:.2f} → Exit=${current_price:.2f}"
            )
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'VWAP_BREAKDOWN',
                'pnl_percent': pnl_percent
            }
        
        # 5. TIME-BASED EXIT - Forced square-off at 3:15 PM IST
        from src.utils.timezone import now_ist_time
        now = now_ist_time()
        square_off_time = datetime.strptime("15:15", "%H:%M").time()
        
        if now >= square_off_time:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            logger.info(
                f"⏰ SQUARE-OFF TIME: {symbol} | "
                f"Entry=${entry_price:.2f} → Exit=${current_price:.2f}"
            )
            return {
                'action': 'SELL',
                'exit_price': current_price,
                'reason': 'SQUARE_OFF',
                'pnl_percent': pnl_percent
            }
        
        # Update tracking
        self.previous_prices[symbol] = current_price
        self.previous_vwap[symbol] = vwap
        
        return None
    
    def calculate_entry_points(self, stock: Dict) -> Dict:
        """
        Calculate entry, target, and stop-loss prices.
        
        Uses ATR for dynamic risk management if available, otherwise falls back to fixed percentage.
        - Stop Loss = Entry - 2.0 * ATR
        - Target = Entry + 4.0 * ATR
        
        Args:
            stock: Stock data with 'close' and optionally 'vwap', 'atr'
            
        Returns:
            Dict with entry_price, target_price, stop_loss
        """
        current_price = stock.get('close', 0)
        vwap = stock.get('vwap', current_price)
        atr = stock.get('atr', 0)
        
        # Entry at current price (or slightly above VWAP for confirmation)
        entry_price = current_price
        
        if atr > 0:
            # Dynamic ATR-based risk management
            # SL = 2 * ATR (Outside normal volatility)
            # Target = 4 * ATR (1:2 Risk:Reward)
            stop_loss = entry_price - (2.0 * atr)
            target_price = entry_price + (4.0 * atr)
            method = "ATR"
        else:
            # Fallback to fixed percentage
            target_price = entry_price * (1 + self.target_percent / 100)
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
            method = "Percent"
        
        return {
            'entry_price': round(entry_price, 2),
            'target_price': round(target_price, 2),
            'stop_loss': round(stop_loss, 2),
            'calculation_method': method
        }
    
    def update_config(self) -> None:
        """Reload strategy parameters from config"""
        self.config = get_config()
        self.stop_loss_percent = self.config.stop_loss_percent
        self.target_percent = self.config.target_percent
        self.rsi_oversold = self.config.get('strategy.rsi_oversold', 40)
        self.rsi_overbought = self.config.get('strategy.rsi_overbought', 70)
        
        logger.info(
            f"📊 Strategy config updated: "
            f"SL={self.stop_loss_percent}%, Target={self.target_percent}%, "
            f"RSI Range={self.rsi_oversold}-{self.rsi_overbought}"
        )
