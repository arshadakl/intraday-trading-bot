"""Angel One WebSocket Client for Real-time Data"""

import json
import threading
from typing import Callable, Optional, List, Dict
from loguru import logger


class AngelWebSocket:
    """
    WebSocket client for real-time market data.
    Uses Angel One's SmartWebSocketV2.
    """
    
    # Token modes
    LTP_MODE = 1
    QUOTE_MODE = 2
    SNAP_QUOTE_MODE = 3
    
    def __init__(self, api_key: str, client_id: str, feed_token: str, auth_token: str = None):
        self.api_key = api_key
        self.client_id = client_id
        self.feed_token = feed_token
        self.auth_token = auth_token or feed_token
        
        self.sws = None
        self.is_connected = False
        self.subscribed_tokens: List[Dict] = []
        
        # Callbacks
        self.on_price_update: Optional[Callable[[str, Dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Price cache
        self._price_cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
        # Reconnection settings
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10  # Increased for better resilience
    
    def connect(self) -> bool:
        """Connect to WebSocket"""
        try:
            from SmartApi.smartWebSocketV2 import SmartWebSocketV2
            
            self.sws = SmartWebSocketV2(
                self.auth_token,
                self.api_key,
                self.client_id,
                self.feed_token
            )
            
            # Set callbacks
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_error
            self.sws.on_close = self._on_close
            
            # Connect in a separate thread
            thread = threading.Thread(target=self.sws.connect, daemon=True)
            thread.start()
            
            logger.info("📡 WebSocket connecting...")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False
    
    def _on_open(self, wsapp) -> None:
        """Called when connection opens"""
        self.is_connected = True
        logger.success("📡 WebSocket connected")
        
        # Subscribe to tokens if any
        if self.subscribed_tokens:
            self._subscribe_tokens()
    
    def _on_data(self, wsapp, message) -> None:
        """Called when data is received"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            
            # Extract token and price info
            token = str(data.get("token", ""))
            
            if token:
                price_data = {
                    "token": token,
                    "ltp": float(data.get("last_traded_price", 0)) / 100,
                    "open": float(data.get("open_price_of_the_day", 0)) / 100,
                    "high": float(data.get("high_price_of_the_day", 0)) / 100,
                    "low": float(data.get("low_price_of_the_day", 0)) / 100,
                    "close": float(data.get("closed_price", 0)) / 100,
                    "volume": int(data.get("volume_trade_for_the_day", 0))
                }
                
                # Update cache
                with self._lock:
                    self._price_cache[token] = price_data
                
                # Call callback
                if self.on_price_update:
                    # Find symbol for this token
                    symbol = self._get_symbol_for_token(token)
                    self.on_price_update(symbol, price_data)
                    
        except Exception as e:
            logger.error(f"Error processing WebSocket data: {e}")
    
    def _on_error(self, wsapp, error) -> None:
        """Called on error"""
        logger.error(f"📡 WebSocket error: {error}")
        if self.on_error:
            self.on_error(str(error))
    
    def _on_close(self, wsapp, close_status, close_msg) -> None:
        """Called when connection closes - attempts auto-reconnect"""
        self.is_connected = False
        logger.warning(f"📡 WebSocket disconnected: {close_msg}")
        
        # Auto-reconnect logic with exponential backoff
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            wait_time = min(5 * self._reconnect_attempts, 60)  # Max 60 seconds
            logger.info(f"🔄 Attempting reconnect in {wait_time}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
            
            import time
            time.sleep(wait_time)
            
            if self.connect():
                logger.success("📡 WebSocket reconnected successfully!")
                self._reconnect_attempts = 0  # Reset counter on success
            else:
                logger.error("📡 Reconnection failed - will retry")
        else:
            logger.error(f"📡 Max reconnection attempts ({self._max_reconnect_attempts}) reached.")
            logger.info("💡 TIP: Restart the bot to try reconnecting")
    
    def reset_reconnect_counter(self) -> None:
        """Reset reconnection counter to allow fresh retry attempts"""
        self._reconnect_attempts = 0
        logger.info("🔄 WebSocket reconnection counter reset")
    
    def subscribe(self, tokens: List[Dict]) -> bool:
        """
        Subscribe to stock tokens for real-time data.
        
        Args:
            tokens: List of dicts with 'exchange_type', 'token' keys
                    e.g., [{'exchange_type': 1, 'token': '2885'}]
        """
        self.subscribed_tokens = tokens
        
        if self.is_connected:
            return self._subscribe_tokens()
        return True  # Will subscribe when connected
    
    def _subscribe_tokens(self) -> bool:
        """Internal method to subscribe to tokens"""
        try:
            if not self.sws or not self.subscribed_tokens:
                return False
            
            # Format for Angel One: [{'exchangeType': 1, 'tokens': ['2885', '3456']}]
            # Group by exchange type
            nse_tokens = []
            bse_tokens = []
            
            for t in self.subscribed_tokens:
                if t.get('exchange_type') == 1:
                    nse_tokens.append(t['token'])
                else:
                    bse_tokens.append(t['token'])
            
            token_list = []
            if nse_tokens:
                token_list.append({'exchangeType': 1, 'tokens': nse_tokens})
            if bse_tokens:
                token_list.append({'exchangeType': 2, 'tokens': bse_tokens})
            
            self.sws.subscribe("abc123", self.LTP_MODE, token_list)
            logger.info(f"📡 Subscribed to {len(self.subscribed_tokens)} tokens")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to tokens: {e}")
            return False
    
    def unsubscribe(self, tokens: List[Dict]) -> bool:
        """Unsubscribe from tokens"""
        try:
            if self.sws and self.is_connected:
                # Similar format as subscribe
                nse_tokens = [t['token'] for t in tokens if t.get('exchange_type') == 1]
                
                if nse_tokens:
                    self.sws.unsubscribe("abc123", self.LTP_MODE, 
                                        [{'exchangeType': 1, 'tokens': nse_tokens}])
                
                # Remove from subscribed list
                self.subscribed_tokens = [
                    t for t in self.subscribed_tokens 
                    if t not in tokens
                ]
                return True
        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
        return False
    
    def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        try:
            if self.sws:
                self.sws.close_connection()
                self.is_connected = False
                logger.info("📡 WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    def get_cached_price(self, token: str) -> Optional[Dict]:
        """Get cached price for a token"""
        with self._lock:
            return self._price_cache.get(token)
    
    def get_all_cached_prices(self) -> Dict[str, Dict]:
        """Get all cached prices"""
        with self._lock:
            return self._price_cache.copy()
    
    def _get_symbol_for_token(self, token: str) -> str:
        """Get symbol name for a token (from subscribed tokens)"""
        for t in self.subscribed_tokens:
            if t.get('token') == token:
                return t.get('symbol', token)
        logger.warning(f"⚠️ No symbol mapping found for token: {token}")
        return token
    
    def set_symbol_mapping(self, token: str, symbol: str) -> None:
        """Set a symbol mapping for a token"""
        for t in self.subscribed_tokens:
            if t.get('token') == token:
                t['symbol'] = symbol
                return
        # Add new mapping
        self.subscribed_tokens.append({'token': token, 'symbol': symbol})