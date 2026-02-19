"""Position Tracker - Tracks and manages open positions."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.utils.timezone import now_ist


@dataclass
class Position:
    """Represents an open position."""

    symbol: str
    token: str
    entry_price: float
    quantity: int
    stop_loss: float
    target: float
    entry_time: datetime
    direction: str = "LONG"  # LONG or SHORT
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "OPEN"

    def update_price(self, price: float) -> None:
        """Update current price and calculate P&L."""
        self.current_price = price
        if self.direction == "SHORT":
            self.pnl = (self.entry_price - price) * self.quantity
            self.pnl_percent = ((self.entry_price - price) / self.entry_price) * 100
        else:
            self.pnl = (price - self.entry_price) * self.quantity
            self.pnl_percent = ((price - self.entry_price) / self.entry_price) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["entry_time"] = self.entry_time.isoformat()
        return data


class PositionTracker:
    """Tracks all open positions in real-time."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict] = []

    def add_position(
        self,
        symbol: str,
        token: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        target: float,
        direction: str = "LONG",
    ) -> Position:
        """Add a new open position."""
        position = Position(
            symbol=symbol,
            token=token,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            entry_time=now_ist(),
            direction=direction,
            current_price=entry_price,
        )
        self.positions[symbol] = position

        logger.info(
            f"Position opened: {symbol} | {direction} | Qty={quantity} @ {entry_price:.2f} | "
            f"Target={target:.2f} | SL={stop_loss:.2f}"
        )
        return position

    def remove_position(self, symbol: str, exit_price: float, reason: str = "MANUAL") -> Optional[Dict]:
        """Close and remove a position."""
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return None

        position = self.positions[symbol]
        position.update_price(exit_price)
        position.status = "CLOSED"

        closed = position.to_dict()
        closed["exit_price"] = exit_price
        closed["exit_time"] = now_ist().isoformat()
        closed["exit_reason"] = reason

        self.closed_positions.append(closed)
        del self.positions[symbol]

        logger.info(
            f"Position closed: {symbol} | {position.direction} | Entry={position.entry_price:.2f} -> "
            f"Exit={exit_price:.2f} | P&L={position.pnl:.2f} ({position.pnl_percent:.2f}%) | Reason: {reason}"
        )
        return closed

    def update_price(self, symbol: str, price: float) -> Optional[str]:
        """Update position price and check stop-loss/target."""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        position.update_price(price)

        if position.direction == "SHORT":
            if price >= position.stop_loss:
                return "STOP_LOSS"
            if price <= position.target:
                return "TARGET"
            return None

        if price <= position.stop_loss:
            return "STOP_LOSS"
        if price >= position.target:
            return "TARGET"
        return None

    def get_position(self, symbol: str) -> Optional[Dict]:
        if symbol in self.positions:
            return self.positions[symbol].to_dict()
        return None

    def get_all_positions(self) -> List[Dict]:
        return [pos.to_dict() for pos in self.positions.values()]

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def get_position_count(self) -> int:
        return len(self.positions)

    def get_total_unrealized_pnl(self) -> float:
        return sum(pos.pnl for pos in self.positions.values())

    def get_total_position_value(self) -> float:
        return sum(pos.current_price * pos.quantity for pos in self.positions.values())

    def get_closed_positions(self) -> List[Dict]:
        return self.closed_positions.copy()

    def get_position_summary(self) -> Dict:
        positions = self.get_all_positions()
        return {
            "open_count": len(positions),
            "total_value": self.get_total_position_value(),
            "unrealized_pnl": self.get_total_unrealized_pnl(),
            "positions": positions,
            "closed_count": len(self.closed_positions),
            "realized_pnl": sum(p.get("pnl", 0) for p in self.closed_positions),
        }

    def update_stop_loss(self, symbol: str, new_stop_loss: float) -> bool:
        if symbol not in self.positions:
            return False
        old_sl = self.positions[symbol].stop_loss
        self.positions[symbol].stop_loss = new_stop_loss
        logger.info(f"Stop-loss updated: {symbol} | {old_sl:.2f} -> {new_stop_loss:.2f}")
        return True

    def update_target(self, symbol: str, new_target: float) -> bool:
        if symbol not in self.positions:
            return False
        old_target = self.positions[symbol].target
        self.positions[symbol].target = new_target
        logger.info(f"Target updated: {symbol} | {old_target:.2f} -> {new_target:.2f}")
        return True

    def close_all_positions(self, prices: Dict[str, float], reason: str = "SQUARE_OFF") -> List[Dict]:
        closed = []
        symbols = list(self.positions.keys())
        for symbol in symbols:
            price = prices.get(symbol, self.positions[symbol].current_price)
            result = self.remove_position(symbol, price, reason)
            if result:
                closed.append(result)
        logger.info(f"Closed all positions: {len(closed)} positions")
        return closed

    def clear_closed_positions(self) -> None:
        self.closed_positions = []
        logger.info("Closed positions history cleared")
