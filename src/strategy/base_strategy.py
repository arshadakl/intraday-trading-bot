"""Base Strategy - Abstract base class for all trading strategies"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    All strategies must implement these methods.
    """
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name for identification
        """
        self.name = name
        self.is_active = True
    
    @abstractmethod
    def check_entry_signal(self, stock: Dict, current_price: float, 
                          indicators: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met.
        
        Args:
            stock: Stock data dictionary
            current_price: Current market price
            indicators: Current indicator values (RSI, VWAP, etc.)
            
        Returns:
            Dict with entry signal details if triggered, None otherwise
            Expected format:
            {
                'action': 'BUY',
                'entry_price': float,
                'stop_loss': float,
                'target': float,
                'reason': str
            }
        """
        pass
    
    @abstractmethod
    def check_exit_signal(self, position: Dict, current_price: float, 
                         indicators: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.
        
        Args:
            position: Current position data
            current_price: Current market price
            indicators: Current indicator values
            
        Returns:
            Dict with exit signal details if triggered, None otherwise
            Expected format:
            {
                'action': 'SELL',
                'exit_price': float,
                'reason': str  # 'TARGET', 'STOP_LOSS', 'SIGNAL', 'TIME', 'MANUAL'
            }
        """
        pass
    
    @abstractmethod
    def calculate_entry_points(self, stock: Dict) -> Dict:
        """
        Calculate entry, target, and stop-loss prices for a stock.
        
        Args:
            stock: Stock data with current price and indicators
            
        Returns:
            Dict with entry_price, target_price, stop_loss
        """
        pass
    
    def is_trading_time(self, start_time: str = "09:30", 
                       end_time: str = "15:00") -> bool:
        """
        Check if current time is within trading hours.
        
        Args:
            start_time: Trading start time (HH:MM)
            end_time: Trading end time (HH:MM)
            
        Returns:
            True if within trading hours
        """
        now = datetime.now().time()
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
        return start <= now <= end
    
    def is_initial_volatility_period(self, start_buffer: int = 15) -> bool:
        """
        Check if we're in the initial high volatility period after market opens.
        
        Args:
            start_buffer: Minutes to wait after market opens
            
        Returns:
            True if still in volatility period
        """
        from datetime import timedelta
        now = datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        buffer_end = market_open + timedelta(minutes=start_buffer)
        return now < buffer_end
    
    def activate(self) -> None:
        """Activate the strategy"""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate the strategy"""
        self.is_active = False
