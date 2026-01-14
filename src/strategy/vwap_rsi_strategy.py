"""VWAP + RSI Strategy - Main trading strategy implementation"""

from datetime import datetime
from typing import Dict, Optional
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
    
    def check_entry_signal(self, stock: Dict, current_price: float, 
                          indicators: Dict) -> Optional[Dict]:
        """
        Check if VWAP + RSI entry conditions are met.
        
        Args:
            stock: Stock data (symbol, token, entry_price, etc.)
            current_price: Current LTP
            indicators: Dict with rsi, vwap, volume_ratio
            
        Returns:
            Entry signal dict or None
        """
        symbol = stock.get('symbol', 'UNKNOWN')
        
        # Check if strategy is active
        if not self.is_active:
            return None
        
        # Check trading time (no trades in first 15 min or after 3 PM)
        if self.is_initial_volatility_period():
            logger.debug(f"{symbol}: Skipping - Initial volatility period")
            return None
        
        if not self.is_trading_time("09:30", "15:00"):
            logger.debug(f"{symbol}: Skipping - Outside trading hours")
            return None
        
        # Get indicator values
        rsi = indicators.get('rsi', 50)
        vwap = indicators.get('vwap', current_price)
        volume_ratio = indicators.get('volume_ratio', 1)
        
        # Get previous price for crossover detection
        prev_price = self.previous_prices.get(symbol, current_price)
        prev_vwap = self.previous_vwap.get(symbol, vwap)
        
        # Update tracking
        self.previous_prices[symbol] = current_price
        self.previous_vwap[symbol] = vwap
        
        # ============ ENTRY CONDITIONS ============
        
        # 1. Price crosses ABOVE VWAP (bullish crossover) - MANDATORY
        price_crossed_above_vwap = prev_price <= prev_vwap and current_price > vwap
        
        # 2. RSI in neutral zone (40-60)
        rsi_in_range = self.rsi_oversold <= rsi <= self.rsi_overbought
        
        # 3. Volume is above average
        volume_confirmed = volume_ratio > 1.0
        
        # Log conditions for debugging
        logger.debug(
            f"{symbol}: Price=${current_price:.2f}, VWAP=${vwap:.2f}, "
            f"RSI={rsi:.1f}, VolRatio={volume_ratio:.2f}, Crossover={price_crossed_above_vwap}"
        )
        
        # CROSSOVER IS NOW MANDATORY - prevents false entries when price hovers above VWAP
        if price_crossed_above_vwap and rsi_in_range and volume_confirmed:
            # Calculate entry points with ATR for dynamic risk management
            atr = indicators.get('atr', 0)
            entry_points = self.calculate_entry_points({
                'close': current_price,
                'vwap': vwap,
                'atr': atr  # Pass ATR for dynamic SL/Target
            })
            
            logger.info(
                f"📈 ENTRY SIGNAL: {symbol} | "
                f"VWAP Crossover | RSI={rsi:.1f} | VolRatio={volume_ratio:.2f} | ATR={atr:.2f}"
            )
            
            return {
                'action': 'BUY',
                'entry_price': current_price,
                'stop_loss': entry_points['stop_loss'],
                'target': entry_points['target_price'],
                'reason': 'VWAP Crossover',
                'indicators': {
                    'rsi': rsi,
                    'vwap': vwap,
                    'volume_ratio': volume_ratio,
                    'atr': atr
                }
            }
        
        return None
    
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
        
        # 5. TIME-BASED EXIT - Forced square-off at 3:15 PM
        now = datetime.now().time()
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
