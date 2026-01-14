"""Order Manager - Handles all order placement and routing"""

from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from src.core.config_manager import get_config
from src.broker.angel_client import AngelOneClient
from src.broker.paper_trader import PaperTrader


class OrderManager:
    """
    Manages order placement for both paper and live trading.
    Routes orders to appropriate broker based on trading mode.
    """
    
    def __init__(self, broker: AngelOneClient, paper_trader: PaperTrader):
        """
        Initialize Order Manager.
        
        Args:
            broker: AngelOneClient instance for live trading
            paper_trader: PaperTrader instance for paper trading
        """
        self.config = get_config()
        self.broker = broker
        self.paper_trader = paper_trader
        
        # Order tracking
        self.pending_orders: List[Dict] = []
        self.completed_orders: List[Dict] = []
    
    @property
    def is_paper_mode(self) -> bool:
        """Check if trading in paper mode"""
        return self.config.is_paper_mode
    
    def place_buy_order(self, symbol: str, token: str, price: float, 
                        quantity: int, stop_loss: float, target: float) -> Dict:
        """
        Place a buy order.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE-EQ")
            token: Stock token
            price: Entry price (0 for market order)
            quantity: Number of shares
            stop_loss: Stop-loss price
            target: Target price
            
        Returns:
            Dict with order details and status
        """
        order = {
            'symbol': symbol,
            'token': token,
            'type': 'BUY',
            'price': price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'target': target,
            'timestamp': datetime.now().isoformat(),
            'status': 'PENDING'
        }
        
        try:
            if self.is_paper_mode:
                # Paper trading - simulate order
                success = self.paper_trader.place_buy_order(
                    symbol=symbol,
                    token=token,
                    price=price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    target=target
                )
                order['status'] = 'FILLED' if success else 'REJECTED'
                order['order_id'] = f"PAPER_{datetime.now().strftime('%H%M%S')}"
                order['mode'] = 'paper'
                
            else:
                # Live trading - place real order
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type='BUY',
                    quantity=quantity,
                    price=0,  # Market order
                    order_type='MARKET',
                    product_type='INTRADAY'
                )
                
                if order_id:
                    order['status'] = 'PLACED'
                    order['order_id'] = order_id
                    order['mode'] = 'live'
                else:
                    order['status'] = 'REJECTED'
                    order['error'] = 'Order placement failed'
            
            # Track order
            if order['status'] in ['FILLED', 'PLACED']:
                self.completed_orders.append(order)
                logger.info(
                    f"✅ BUY Order {'Simulated' if self.is_paper_mode else 'Placed'}: "
                    f"{symbol} x{quantity} @ ₹{price:.2f}"
                )
            else:
                logger.warning(f"❌ BUY Order Rejected: {symbol}")
            
            return order
            
        except Exception as e:
            order['status'] = 'ERROR'
            order['error'] = str(e)
            logger.error(f"❌ Error placing buy order for {symbol}: {e}")
            return order
    
    def place_sell_order(self, symbol: str, token: str, price: float, 
                         quantity: int, reason: str = "MANUAL") -> Dict:
        """
        Place a sell order.
        
        Args:
            symbol: Stock symbol
            token: Stock token
            price: Exit price (0 for market order)
            quantity: Number of shares
            reason: Exit reason (TARGET, STOP_LOSS, MANUAL, SQUARE_OFF)
            
        Returns:
            Dict with order details and status
        """
        order = {
            'symbol': symbol,
            'token': token,
            'type': 'SELL',
            'price': price,
            'quantity': quantity,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'status': 'PENDING'
        }
        
        try:
            if self.is_paper_mode:
                # Paper trading - simulate order
                success = self.paper_trader.place_sell_order(
                    symbol=symbol,
                    price=price,
                    reason=reason
                )
                order['status'] = 'FILLED' if success else 'REJECTED'
                order['order_id'] = f"PAPER_{datetime.now().strftime('%H%M%S')}"
                order['mode'] = 'paper'
                
            else:
                # Live trading - place real order
                order_id = self.broker.place_order(
                    symbol=symbol,
                    token=token,
                    transaction_type='SELL',
                    quantity=quantity,
                    price=0,  # Market order
                    order_type='MARKET',
                    product_type='INTRADAY'
                )
                
                if order_id:
                    order['status'] = 'PLACED'
                    order['order_id'] = order_id
                    order['mode'] = 'live'
                else:
                    order['status'] = 'REJECTED'
                    order['error'] = 'Order placement failed'
            
            # Track order
            if order['status'] in ['FILLED', 'PLACED']:
                self.completed_orders.append(order)
                logger.info(
                    f"✅ SELL Order {'Simulated' if self.is_paper_mode else 'Placed'}: "
                    f"{symbol} x{quantity} @ ₹{price:.2f} ({reason})"
                )
            else:
                logger.warning(f"❌ SELL Order Rejected: {symbol}")
            
            return order
            
        except Exception as e:
            order['status'] = 'ERROR'
            order['error'] = str(e)
            logger.error(f"❌ Error placing sell order for {symbol}: {e}")
            return order
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get status of an order.
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Order status dict or None
        """
        if self.is_paper_mode:
            # Paper orders are instant
            for order in self.completed_orders:
                if order.get('order_id') == order_id:
                    return order
            return None
        else:
            # Check with broker
            order_book = self.broker.get_order_book()
            if order_book:
                for order in order_book:
                    if order.get('orderid') == order_id:
                        return order
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        if self.is_paper_mode:
            # Remove from pending orders
            self.pending_orders = [
                o for o in self.pending_orders 
                if o.get('order_id') != order_id
            ]
            logger.info(f"📝 Paper order cancelled: {order_id}")
            return True
        else:
            # Cancel with broker
            result = self.broker.cancel_order(order_id)
            if result:
                logger.info(f"📝 Order cancelled: {order_id}")
            return result is not None
    
    def get_trades_today(self) -> List[Dict]:
        """Get all trades executed today"""
        if self.is_paper_mode:
            return self.paper_trader.get_trades_today()
        else:
            # Get from broker
            positions = self.broker.get_positions()
            if positions and 'day' in positions:
                return positions['day']
            return []
    
    def get_completed_orders(self) -> List[Dict]:
        """Get list of completed orders for today"""
        return self.completed_orders.copy()
    
    def get_pending_orders(self) -> List[Dict]:
        """Get list of pending orders"""
        return self.pending_orders.copy()
    
    def clear_order_history(self) -> None:
        """Clear order tracking (call at start of day)"""
        self.pending_orders = []
        self.completed_orders = []
        logger.info("🔄 Order history cleared")
