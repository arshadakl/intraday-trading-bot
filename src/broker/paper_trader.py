"""Paper Trading Simulator"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger
import json
from pathlib import Path


@dataclass
class PaperPosition:
    """Represents a paper trading position"""
    symbol: str
    token: str
    entry_price: float
    quantity: int
    entry_time: datetime
    stop_loss:  float
    target:  float
    current_price: float = 0.0
    pnl: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""


@dataclass
class PaperTrade:
    """Represents a completed paper trade"""
    symbol: str
    token: str
    entry_price: float
    exit_price: float
    quantity:  int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    exit_reason: str


class PaperTrader: 
    """
    Simulates trading without real money. 
    Tracks positions, P&L, and trade history.
    """
    
    def __init__(self, initial_balance: float = 100000.0):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.trades: List[PaperTrade] = []
        self.daily_pnl = 0.0
        self. trade_count = 0
        
        # Create data directory
        self.data_dir = Path("data/paper_trades")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Paper Trader initialized with balance: ₹{initial_balance:,.2f}")
    
    def set_balance(self, balance: float) -> None:
        """Set the paper trading balance"""
        self.initial_balance = balance
        self. available_balance = balance
        logger.info(f"Paper balance set to ₹{balance:,.2f}")
    
    def get_available_balance(self) -> float:
        """Get available balance for trading"""
        return self.available_balance
    
    def get_total_balance(self) -> float:
        """Get total balance including open positions"""
        position_value = sum(
            pos.current_price * pos.quantity 
            for pos in self.positions.values()
        )
        return self.available_balance + position_value
    
    def place_buy_order(
        self,
        symbol: str,
        token: str,
        price: float,
        quantity: int,
        stop_loss: float,
        target: float
    ) -> bool:
        """Simulate a buy order with realistic slippage"""
        # Simulate slippage (0.05% - buy executes slightly higher)
        slippage_percent = 0.0005  # 0.05%
        executed_price = price * (1 + slippage_percent)
        
        order_value = executed_price * quantity
        
        if order_value > self.available_balance:
            logger.warning(f"Insufficient balance for {symbol}. Required: ₹{order_value:,.2f}")
            return False
        
        if symbol in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return False
        
        # Create position with slippage-adjusted price
        position = PaperPosition(
            symbol=symbol,
            token=token,
            entry_price=executed_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            target=target,
            current_price=executed_price
        )
        
        self.positions[symbol] = position
        self.available_balance -= order_value
        self.trade_count += 1
        
        logger.success(
            f"[PAPER] BUY {quantity} {symbol} @ ₹{executed_price:.2f} (slippage: {slippage_percent*100:.2f}%) | "
            f"SL: ₹{stop_loss:.2f} | Target: ₹{target:.2f}"
        )
        
        return True
    
    def place_sell_order(self, symbol: str, price: float, reason: str = "MANUAL") -> bool:
        """Simulate a sell order with realistic slippage"""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return False
        
        position = self.positions[symbol]
        
        # Simulate slippage (0.05% - sell executes slightly lower)
        slippage_percent = 0.0005  # 0.05%
        executed_price = price * (1 - slippage_percent)
        
        # Calculate P&L with slippage-adjusted exit price
        pnl = (executed_price - position.entry_price) * position.quantity
        pnl_percent = ((executed_price - position.entry_price) / position.entry_price) * 100
        
        # Record trade
        trade = PaperTrade(
            symbol=symbol,
            token=position.token,
            entry_price=position.entry_price,
            exit_price=executed_price,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            pnl_percent=pnl_percent,
            exit_reason=reason
        )
        self.trades.append(trade)
        
        # Update balance with slippage-adjusted price
        self.available_balance += executed_price * position.quantity
        self.daily_pnl += pnl
        
        # Remove position
        del self.positions[symbol]
        
        pnl_symbol = "+" if pnl >= 0 else ""
        logger.success(
            f"[PAPER] SELL {position.quantity} {symbol} @ ₹{executed_price:.2f} (slippage: {slippage_percent*100:.2f}%) | "
            f"P&L: {pnl_symbol}₹{pnl:.2f} ({pnl_percent:+.2f}%) | Reason: {reason}"
        )
        
        return True
    
    def update_price(self, symbol: str, price: float) -> Optional[str]:
        """
        Update current price and check stop loss/target. 
        Returns action if triggered:  'STOP_LOSS', 'TARGET', or None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.current_price = price
        position.pnl = (price - position. entry_price) * position.quantity
        
        # Check stop loss
        if price <= position.stop_loss:
            return "STOP_LOSS"
        
        # Check target
        if price >= position.target:
            return "TARGET"
        
        return None
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions as list of dicts"""
        return [
            {
                "symbol":  pos.symbol,
                "token": pos.token,
                "entry_price": pos.entry_price,
                "quantity": pos.quantity,
                "current_price": pos.current_price,
                "pnl":  pos.pnl,
                "stop_loss": pos.stop_loss,
                "target": pos. target,
                "entry_time": pos.entry_time. isoformat(),
                "status": pos.status
            }
            for pos in self.positions. values()
        ]
    
    def get_trades_today(self) -> List[Dict]:
        """Get today's trades"""
        today = datetime.now().date()
        return [
            {
                "symbol": trade.symbol,
                "entry_price": trade.entry_price,
                "exit_price":  trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "exit_reason": trade.exit_reason,
                "entry_time": trade. entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat()
            }
            for trade in self.trades
            if trade.exit_time. date() == today
        ]
    
    def get_daily_summary(self) -> Dict:
        """Get daily trading summary"""
        today_trades = self.get_trades_today()
        
        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.get_total_balance(),
            "available_balance": self.available_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percent": (self.daily_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0.0,
            "total_trades": len(today_trades),
            "winning_trades": len([t for t in today_trades if t["pnl"] > 0]),
            "losing_trades": len([t for t in today_trades if t["pnl"] < 0]),
            "open_positions": len(self.positions)
        }
    
    def save_daily_report(self) -> None:
        """Save daily trading report to file"""
        today = datetime.now().strftime("%Y-%m-%d")
        report = {
            "date": today,
            "summary": self.get_daily_summary(),
            "trades": self. get_trades_today(),
            "open_positions": self.get_positions()
        }
        
        filepath = self.data_dir / f"{today}. json"
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Daily report saved to {filepath}")
    
    def reset_daily(self) -> None:
        """Reset daily counters (call at start of each day)"""
        self.daily_pnl = 0.0
        self.trade_count = 0
        # Note: positions carry over if not squared off
        logger.info("Daily counters reset")