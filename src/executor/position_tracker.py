"""Position Tracker - Tracks and manages open positions"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    token: str
    entry_price: float
    quantity: int
    stop_loss: float
    target: float
    entry_time: datetime
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "OPEN"
    
    def update_price(self, price: float) -> None:
        """Update current price and calculate P&L"""
        self.current_price = price
        self.pnl = (price - self.entry_price) * self.quantity
        self.pnl_percent = ((price - self.entry_price) / self.entry_price) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        return data


class PositionTracker:
    """
    Tracks all open positions in real-time.
    Updates prices and calculates unrealized P&L.
    """
    
    def __init__(self):
        """Initialize Position Tracker"""
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict] = []
    
    def add_position(self, symbol: str, token: str, entry_price: float,
                     quantity: int, stop_loss: float, target: float) -> Position:
        """
        Add a new open position.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE-EQ")
            token: Stock token
            entry_price: Entry price
            quantity: Number of shares
            stop_loss: Stop-loss price
            target: Target price
            
        Returns:
            Created Position object
        """
        position = Position(
            symbol=symbol,
            token=token,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            entry_time=datetime.now(),
            current_price=entry_price
        )
        
        self.positions[symbol] = position
        
        logger.info(
            f"📈 Position opened: {symbol} | "
            f"Qty={quantity} @ ₹{entry_price:.2f} | "
            f"Target=₹{target:.2f} | SL=₹{stop_loss:.2f}"
        )
        
        return position
    
    def remove_position(self, symbol: str, exit_price: float, 
                        reason: str = "MANUAL") -> Optional[Dict]:
        """
        Close and remove a position.
        
        Args:
            symbol: Stock symbol to close
            exit_price: Exit price
            reason: Exit reason (TARGET, STOP_LOSS, MANUAL, SQUARE_OFF)
            
        Returns:
            Closed position data or None if not found
        """
        if symbol not in self.positions:
            logger.warning(f"⚠️ Position not found: {symbol}")
            return None
        
        position = self.positions[symbol]
        position.update_price(exit_price)
        position.status = "CLOSED"
        
        # Create closed position record
        closed = position.to_dict()
        closed['exit_price'] = exit_price
        closed['exit_time'] = datetime.now().isoformat()
        closed['exit_reason'] = reason
        
        self.closed_positions.append(closed)
        del self.positions[symbol]
        
        logger.info(
            f"📉 Position closed: {symbol} | "
            f"Entry=₹{position.entry_price:.2f} → Exit=₹{exit_price:.2f} | "
            f"P&L=₹{position.pnl:.2f} ({position.pnl_percent:.2f}%) | "
            f"Reason: {reason}"
        )
        
        return closed
    
    def update_price(self, symbol: str, price: float) -> Optional[str]:
        """
        Update position price and check stop-loss/target.
        
        Args:
            symbol: Stock symbol
            price: Current price
            
        Returns:
            'STOP_LOSS', 'TARGET', or None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.update_price(price)
        
        # Check stop-loss
        if price <= position.stop_loss:
            return 'STOP_LOSS'
        
        # Check target
        if price >= position.target:
            return 'TARGET'
        
        return None
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position data for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position dict or None
        """
        if symbol in self.positions:
            return self.positions[symbol].to_dict()
        return None
    
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions as list of dicts"""
        return [pos.to_dict() for pos in self.positions.values()]
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return symbol in self.positions
    
    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions"""
        return sum(pos.pnl for pos in self.positions.values())
    
    def get_total_position_value(self) -> float:
        """Get total value of all open positions"""
        return sum(
            pos.current_price * pos.quantity 
            for pos in self.positions.values()
        )
    
    def get_closed_positions(self) -> List[Dict]:
        """Get list of closed positions for today"""
        return self.closed_positions.copy()
    
    def get_position_summary(self) -> Dict:
        """
        Get summary of all positions.
        
        Returns:
            Dict with position summary
        """
        positions = self.get_all_positions()
        
        return {
            'open_count': len(positions),
            'total_value': self.get_total_position_value(),
            'unrealized_pnl': self.get_total_unrealized_pnl(),
            'positions': positions,
            'closed_count': len(self.closed_positions),
            'realized_pnl': sum(
                p.get('pnl', 0) for p in self.closed_positions
            )
        }
    
    def update_stop_loss(self, symbol: str, new_stop_loss: float) -> bool:
        """
        Update stop-loss for a position (for trailing stop-loss).
        
        Args:
            symbol: Stock symbol
            new_stop_loss: New stop-loss price
            
        Returns:
            True if updated successfully
        """
        if symbol not in self.positions:
            return False
        
        old_sl = self.positions[symbol].stop_loss
        self.positions[symbol].stop_loss = new_stop_loss
        
        logger.info(
            f"📊 Stop-loss updated: {symbol} | "
            f"₹{old_sl:.2f} → ₹{new_stop_loss:.2f}"
        )
        
        return True
    
    def update_target(self, symbol: str, new_target: float) -> bool:
        """
        Update target for a position.
        
        Args:
            symbol: Stock symbol
            new_target: New target price
            
        Returns:
            True if updated successfully
        """
        if symbol not in self.positions:
            return False
        
        old_target = self.positions[symbol].target
        self.positions[symbol].target = new_target
        
        logger.info(
            f"📊 Target updated: {symbol} | "
            f"₹{old_target:.2f} → ₹{new_target:.2f}"
        )
        
        return True
    
    def close_all_positions(self, prices: Dict[str, float], 
                           reason: str = "SQUARE_OFF") -> List[Dict]:
        """
        Close all open positions.
        
        Args:
            prices: Dict mapping symbol to current price
            reason: Exit reason
            
        Returns:
            List of closed positions
        """
        closed = []
        symbols = list(self.positions.keys())  # Copy keys to avoid modification during iteration
        
        for symbol in symbols:
            price = prices.get(symbol, self.positions[symbol].current_price)
            result = self.remove_position(symbol, price, reason)
            if result:
                closed.append(result)
        
        logger.info(f"📉 Closed all positions: {len(closed)} positions")
        return closed
    
    def clear_closed_positions(self) -> None:
        """Clear closed positions history (call at start of day)"""
        self.closed_positions = []
        logger.info("🔄 Closed positions history cleared")
