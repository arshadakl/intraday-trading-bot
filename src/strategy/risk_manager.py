"""Risk Manager - Position sizing and daily risk controls"""

from datetime import datetime, date
from typing import Dict, Optional
from loguru import logger

from src.core.config_manager import get_config


class RiskManager:
    """
    Controls risk at trade and daily level.
    - Position sizing based on stop-loss
    - Daily loss limits
    - Trade count limits
    - Maximum position size constraints
    """
    
    def __init__(self, trading_capital: float):
        """
        Initialize Risk Manager.
        
        Args:
            trading_capital: Capital allocated for trading
        """
        self.config = get_config()
        self.trading_capital = trading_capital
        
        # Daily tracking
        self.today = date.today()
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        
        # Risk parameters from config
        self.max_daily_loss_percent = self.config.max_daily_loss_percent
        self.max_trades_per_day = self.config.max_trades_per_day
        self.max_position_size_percent = self.config.get(
            'risk.max_position_size_percent', 25
        )
        self.stop_loss_percent = self.config.stop_loss_percent
        
        # Calculate limits
        self.max_daily_loss = self.trading_capital * (self.max_daily_loss_percent / 100)
        self.max_position_size = self.trading_capital * (self.max_position_size_percent / 100)
        # Spam guards
        self._max_trades_alerted = False
        
        logger.info(
            f"💰 Risk Manager initialized: "
            f"Capital=₹{trading_capital:,.2f}, "
            f"Max Daily Loss=₹{self.max_daily_loss:,.2f} ({self.max_daily_loss_percent}%), "
            f"Max Position=₹{self.max_position_size:,.2f}"
        )
    
    def _check_new_day(self) -> None:
        """Reset daily counters if it's a new day"""
        if date.today() != self.today:
            self.reset_daily()
    
    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed based on risk limits.
        Uses IST timezone for market hours check.
        
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        from src.utils.timezone import now_ist_time
        
        self._check_new_day()
        
        # Check 1: Daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            reason = f"Daily loss limit reached (₹{abs(self.daily_pnl):,.2f} >= ₹{self.max_daily_loss:,.2f})"
            logger.warning(f"🚫 {reason}")
            return False, reason
        
        # Check 2: Maximum trades per day
        if self.daily_trades >= self.max_trades_per_day:
            reason = f"Max trades per day reached ({self.daily_trades}/{self.max_trades_per_day})"
            if not self._max_trades_alerted:
                logger.warning(f"🚫 {reason}")
                self._max_trades_alerted = True
            return False, reason
        
        # Check 3: Market hours (IST)
        now = now_ist_time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        no_new_trades = datetime.strptime("15:00", "%H:%M").time()
        
        if now < market_open:
            return False, "Market not yet open"
        
        if now > no_new_trades:
            return False, "No new trades after 3:00 PM"
        
        return True, "Trading allowed"
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, direction: str = 'LONG') -> int:
        """
        Calculate position size based on risk per trade.
        
        Uses the actual price difference (entry - stop_loss) which may come from
        ATR-based dynamic risk management.
        
        Formula:
        Risk Amount = Capital × (configured risk % / 100)
        Price Difference = |Entry Price - Stop Loss Price| (from ATR or %)
        Quantity = Risk Amount / Price Difference
        
        Args:
            entry_price: Planned entry price
            stop_loss: Stop-loss price (may be ATR-based)
            direction: 'LONG' or 'SHORT' - affects SL validation
            
        Returns:
            Number of shares to buy (rounded down)
        """
        self._check_new_day()
        
        direction = direction.upper()
        
        # Validate stop-loss based on direction
        if direction == 'LONG':
            # For LONG: stop-loss must be BELOW entry price
            if stop_loss >= entry_price:
                logger.warning(f"⚠️ Invalid stop-loss for LONG: must be below entry price (SL={stop_loss}, Entry={entry_price})")
                return 0
            price_difference = entry_price - stop_loss
        elif direction == 'SHORT':
            # For SHORT: stop-loss must be ABOVE entry price
            if stop_loss <= entry_price:
                logger.warning(f"⚠️ Invalid stop-loss for SHORT: must be above entry price (SL={stop_loss}, Entry={entry_price})")
                return 0
            price_difference = stop_loss - entry_price
        else:
            logger.warning(f"⚠️ Invalid direction '{direction}': must be LONG or SHORT")
            return 0
        
        # Calculate actual SL% being used
        actual_sl_percent = (price_difference / entry_price) * 100
        
        # Risk amount = how much you're willing to lose on this trade
        # Uses configured risk tolerance (stop_loss_percent of capital)
        risk_amount = self.trading_capital * (self.stop_loss_percent / 100)
        
        # Calculate quantity based on risk
        quantity = int(risk_amount / price_difference)
        
        # Check against max position size
        position_value = quantity * entry_price
        if position_value > self.max_position_size:
            quantity = int(self.max_position_size / entry_price)
            logger.info(f"📊 Position size limited to ₹{self.max_position_size:,.2f}")
        
        # Ensure at least 1 share (if affordable)
        if quantity < 1 and entry_price <= self.max_position_size:
            quantity = 1
        
        logger.info(
            f"📊 Position sizing: Entry=₹{entry_price:.2f}, SL=₹{stop_loss:.2f} ({actual_sl_percent:.2f}%), "
            f"Risk=₹{risk_amount:.2f}, Qty={quantity}"
        )
        
        return quantity
    
    def calculate_position_size_by_value(self, entry_price: float, 
                                          max_value: float = None) -> int:
        """
        Calculate position size based on maximum position value.
        
        Args:
            entry_price: Entry price per share
            max_value: Maximum position value (uses config if not provided)
            
        Returns:
            Number of shares to buy
        """
        if max_value is None:
            max_value = self.max_position_size
        
        quantity = int(max_value / entry_price)
        return max(0, quantity)
    
    def record_trade(self, pnl: float) -> None:
        """
        Record a completed trade.
        
        Args:
            pnl: Profit/Loss from the trade
        """
        self._check_new_day()
        
        self.daily_trades += 1
        self.daily_pnl += pnl
        
        if pnl >= 0:
            self.daily_wins += 1
        else:
            self.daily_losses += 1
        
        logger.info(
            f"📝 Trade recorded: P&L=₹{pnl:,.2f}, "
            f"Daily Total=₹{self.daily_pnl:,.2f}, "
            f"Trades={self.daily_trades}/{self.max_trades_per_day}"
        )
    
    def record_loss(self, amount: float) -> None:
        """
        Record a loss (for tracking daily loss limit).
        
        Args:
            amount: Loss amount (positive number)
        """
        self._check_new_day()
        self.daily_pnl -= abs(amount)
        self.daily_losses += 1
        self.daily_trades += 1
    
    def record_win(self, amount: float) -> None:
        """
        Record a win.
        
        Args:
            amount: Win amount (positive number)
        """
        self._check_new_day()
        self.daily_pnl += abs(amount)
        self.daily_wins += 1
        self.daily_trades += 1
    
    def get_daily_pnl(self) -> float:
        """Get current daily P&L"""
        self._check_new_day()
        return self.daily_pnl
    
    def get_remaining_loss_budget(self) -> float:
        """Get remaining loss budget for today"""
        self._check_new_day()
        return self.max_daily_loss + self.daily_pnl
    
    def get_remaining_trades(self) -> int:
        """Get remaining trades allowed for today"""
        self._check_new_day()
        return max(0, self.max_trades_per_day - self.daily_trades)
    
    def get_win_rate(self) -> float:
        """Get win rate for today"""
        self._check_new_day()
        total = self.daily_wins + self.daily_losses
        if total == 0:
            return 0.0
        return (self.daily_wins / total) * 100
    
    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics"""
        self._check_new_day()
        return {
            'date': self.today.isoformat(),
            'trades': self.daily_trades,
            'wins': self.daily_wins,
            'losses': self.daily_losses,
            'win_rate': self.get_win_rate(),
            'pnl': self.daily_pnl,
            'pnl_percent': (self.daily_pnl / self.trading_capital) * 100,
            'remaining_trades': self.get_remaining_trades(),
            'remaining_loss_budget': self.get_remaining_loss_budget(),
            'max_daily_loss': self.max_daily_loss,
            'trading_capital': self.trading_capital
        }
    
    def reset_daily(self) -> None:
        """Reset daily counters (called at start of each day)"""
        self.today = date.today()
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self._max_trades_alerted = False
        logger.info("🔄 Daily risk counters reset")
    
    def update_capital(self, new_capital: float) -> None:
        """
        Update trading capital (e.g., after deposits/withdrawals).
        
        Args:
            new_capital: New trading capital amount
        """
        self.trading_capital = new_capital
        self.max_daily_loss = new_capital * (self.max_daily_loss_percent / 100)
        self.max_position_size = new_capital * (self.max_position_size_percent / 100)
        
        logger.info(
            f"💰 Capital updated: ₹{new_capital:,.2f}, "
            f"Max Loss=₹{self.max_daily_loss:,.2f}"
        )
    
    def update_config(self) -> None:
        """Reload risk parameters from config"""
        self.config = get_config()
        self.max_daily_loss_percent = self.config.max_daily_loss_percent
        self.max_trades_per_day = self.config.max_trades_per_day
        self.max_position_size_percent = self.config.get(
            'risk.max_position_size_percent', 25
        )
        self.stop_loss_percent = self.config.stop_loss_percent
        
        # Recalculate limits
        self.max_daily_loss = self.trading_capital * (self.max_daily_loss_percent / 100)
        self.max_position_size = self.trading_capital * (self.max_position_size_percent / 100)
        
        logger.info("📊 Risk parameters updated from config")
