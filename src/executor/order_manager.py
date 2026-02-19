"""Order Manager - Handles order execution and tracking."""

from typing import Dict, List, Optional

from loguru import logger

from src.broker.angel_client import AngelOneClient
from src.broker.paper_trader import PaperTrader
from src.core.config_manager import get_config
from src.utils.timezone import now_ist


class OrderManager:
    """Routes orders to paper/live backends."""

    def __init__(self, broker: AngelOneClient, paper_trader: PaperTrader):
        self.config = get_config()
        self.broker = broker
        self.paper_trader = paper_trader
        self.pending_orders: List[Dict] = []
        self.completed_orders: List[Dict] = []

    @property
    def is_paper_mode(self) -> bool:
        return self.config.is_paper_mode

    def _record_order(self, order: Dict) -> Dict:
        if order["status"] in ["FILLED", "PLACED"]:
            self.completed_orders.append(order)
        return order

    def place_buy_order(self, symbol: str, token: str, price: float, quantity: int, stop_loss: float, target: float) -> Dict:
        """Place a BUY entry order for a long position."""
        order = {
            "symbol": symbol,
            "token": token,
            "type": "BUY",
            "price": price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
            "timestamp": now_ist().isoformat(),
            "status": "PENDING",
        }
        try:
            if self.is_paper_mode:
                success = self.paper_trader.place_buy_order(symbol, token, price, quantity, stop_loss, target)
                order["status"] = "FILLED" if success else "REJECTED"
                order["order_id"] = f"PAPER_{now_ist().strftime('%H%M%S')}"
                order["mode"] = "paper"
            else:
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type="BUY",
                    quantity=quantity,
                    price=0,
                    order_type="MARKET",
                    product_type="INTRADAY",
                )
                if order_id:
                    order["status"] = "PLACED"
                    order["order_id"] = order_id
                    order["mode"] = "live"
                else:
                    order["status"] = "REJECTED"
                    order["error"] = "Order placement failed"
            return self._record_order(order)
        except Exception as e:
            order["status"] = "ERROR"
            order["error"] = str(e)
            return order

    def place_short_order(
        self, symbol: str, token: str, price: float, quantity: int, stop_loss: float, target: float
    ) -> Dict:
        """Place a SELL entry order for a short position."""
        order = {
            "symbol": symbol,
            "token": token,
            "type": "SELL",
            "price": price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
            "timestamp": now_ist().isoformat(),
            "status": "PENDING",
            "direction": "SHORT",
        }
        try:
            if self.is_paper_mode:
                success = self.paper_trader.place_short_order(symbol, token, price, quantity, stop_loss, target)
                order["status"] = "FILLED" if success else "REJECTED"
                order["order_id"] = f"PAPER_{now_ist().strftime('%H%M%S')}"
                order["mode"] = "paper"
            else:
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type="SELL",
                    quantity=quantity,
                    price=0,
                    order_type="MARKET",
                    product_type="INTRADAY",
                )
                if order_id:
                    order["status"] = "PLACED"
                    order["order_id"] = order_id
                    order["mode"] = "live"
                else:
                    order["status"] = "REJECTED"
                    order["error"] = "Order placement failed"
            return self._record_order(order)
        except Exception as e:
            order["status"] = "ERROR"
            order["error"] = str(e)
            return order

    def place_sell_order(self, symbol: str, token: str, price: float, quantity: int, reason: str = "MANUAL") -> Dict:
        """Place a SELL exit order for long positions."""
        order = {
            "symbol": symbol,
            "token": token,
            "type": "SELL",
            "price": price,
            "quantity": quantity,
            "reason": reason,
            "timestamp": now_ist().isoformat(),
            "status": "PENDING",
        }
        try:
            if self.is_paper_mode:
                success = self.paper_trader.place_sell_order(symbol=symbol, price=price, reason=reason)
                order["status"] = "FILLED" if success else "REJECTED"
                order["order_id"] = f"PAPER_{now_ist().strftime('%H%M%S')}"
                order["mode"] = "paper"
            else:
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type="SELL",
                    quantity=quantity,
                    price=0,
                    order_type="MARKET",
                    product_type="INTRADAY",
                )
                if order_id:
                    order["status"] = "PLACED"
                    order["order_id"] = order_id
                    order["mode"] = "live"
                else:
                    order["status"] = "REJECTED"
                    order["error"] = "Order placement failed"
            return self._record_order(order)
        except Exception as e:
            order["status"] = "ERROR"
            order["error"] = str(e)
            return order

    def place_cover_order(self, symbol: str, token: str, price: float, quantity: int, reason: str = "MANUAL") -> Dict:
        """Place a BUY exit order for short positions."""
        order = {
            "symbol": symbol,
            "token": token,
            "type": "BUY",
            "price": price,
            "quantity": quantity,
            "reason": reason,
            "timestamp": now_ist().isoformat(),
            "status": "PENDING",
            "direction": "SHORT",
        }
        try:
            if self.is_paper_mode:
                success = self.paper_trader.place_cover_order(symbol=symbol, price=price, reason=reason)
                order["status"] = "FILLED" if success else "REJECTED"
                order["order_id"] = f"PAPER_{now_ist().strftime('%H%M%S')}"
                order["mode"] = "paper"
            else:
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type="BUY",
                    quantity=quantity,
                    price=0,
                    order_type="MARKET",
                    product_type="INTRADAY",
                )
                if order_id:
                    order["status"] = "PLACED"
                    order["order_id"] = order_id
                    order["mode"] = "live"
                else:
                    order["status"] = "REJECTED"
                    order["error"] = "Order placement failed"
            return self._record_order(order)
        except Exception as e:
            order["status"] = "ERROR"
            order["error"] = str(e)
            return order

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        if self.is_paper_mode:
            for order in self.completed_orders:
                if order.get("order_id") == order_id:
                    return order
            return None
        order_book = self.broker.get_order_book()
        if order_book:
            for order in order_book:
                if order.get("orderid") == order_id:
                    return order
        return None

    def cancel_order(self, order_id: str) -> bool:
        if self.is_paper_mode:
            self.pending_orders = [o for o in self.pending_orders if o.get("order_id") != order_id]
            return True
        result = self.broker.cancel_order(order_id)
        return result is not None

    def get_trades_today(self) -> List[Dict]:
        if self.is_paper_mode:
            return self.paper_trader.get_trades_today()
        positions = self.broker.get_positions()
        if positions and "day" in positions:
            return positions["day"]
        return []

    def get_completed_orders(self) -> List[Dict]:
        return self.completed_orders.copy()

    def get_pending_orders(self) -> List[Dict]:
        return self.pending_orders.copy()

    def clear_order_history(self) -> None:
        self.pending_orders = []
        self.completed_orders = []
        logger.info("Order history cleared")
