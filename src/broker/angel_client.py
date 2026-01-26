"""Angel One SmartAPI Client Wrapper - Multi API Key Support"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pyotp
from SmartApi import SmartConnect
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class AngelOneClient:
    """
    Wrapper for Angel One SmartAPI.
    Supports multiple API keys for Trading, Historical, and Market APIs.
    
    Uses:
    - Trading API Key: For login, orders, positions
    - Historical API Key: For candle data (getCandleData)
    - Market API Key: For WebSocket feed token
    """
    
    def __init__(self):
        # Load credentials
        self.client_id = os.getenv("ANGEL_CLIENT_ID")
        self.password = os.getenv("ANGEL_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET")
        
        # Load API keys for different purposes
        self.trading_api_key = os.getenv("ANGEL_TRADING_API_KEY") or os.getenv("ANGEL_API_KEY")
        self.historical_api_key = os.getenv("ANGEL_HISTORICAL_API_KEY") or self.trading_api_key
        self.market_api_key = os.getenv("ANGEL_MARKET_API_KEY") or self.trading_api_key
        
        # Validate required credentials
        if not all([self.trading_api_key, self.client_id, self.password, self.totp_secret]):
            raise ValueError(
                "Missing Angel One API credentials. "
                "Please check your .env file for: "
                "ANGEL_TRADING_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET"
            )
        
        # SmartConnect instances for different API types
        self.smart_api = SmartConnect(api_key=self.trading_api_key)
        self.historical_api = SmartConnect(api_key=self.historical_api_key)
        self.market_api = SmartConnect(api_key=self.market_api_key)
        
        # Auth tokens
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.is_authenticated = False
        
        logger.info(f"📊 Angel Client initialized with Client ID: {self.client_id}")
    
    def login(self) -> bool:
        """Authenticate with Angel One API using all API keys"""
        try:
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            
            # Login with Trading API (primary)
            data = self.smart_api.generateSession(
                self.client_id,
                self.password,
                totp
            )
            
            if data.get("status"):
                self.auth_token = data["data"]["jwtToken"]
                self.refresh_token = data["data"]["refreshToken"]
                self.feed_token = self.smart_api.getfeedToken()
                self.is_authenticated = True
                
                # Also authenticate Historical API
                self._auth_historical_api()
                
                # Also authenticate Market API (for WebSocket)
                self._auth_market_api()
                
                logger.success(f"✅ Logged in successfully: {self.client_id}")
                return True
            else:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"❌ Login failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login exception: {e}")
            return False
    
    def _auth_historical_api(self) -> bool:
        """Authenticate Historical Data API"""
        try:
            if self.historical_api_key != self.trading_api_key:
                totp = pyotp.TOTP(self.totp_secret).now()
                self.historical_api.generateSession(
                    self.client_id,
                    self.password,
                    totp
                )
                logger.debug("✅ Historical API authenticated")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Historical API auth failed (will use Trading API): {e}")
            self.historical_api = self.smart_api
            return False
    
    def _auth_market_api(self) -> bool:
        """Authenticate Market Feeds API and get feed token"""
        try:
            if self.market_api_key != self.trading_api_key:
                totp = pyotp.TOTP(self.totp_secret).now()
                data = self.market_api.generateSession(
                    self.client_id,
                    self.password,
                    totp
                )
                if data.get("status"):
                    self.feed_token = self.market_api.getfeedToken()
                    logger.debug("✅ Market API authenticated")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Market API auth failed (will use Trading API): {e}")
            self.market_api = self.smart_api
            return False
    
    def get_feed_token(self) -> str:
        """Get feed token for WebSocket connection"""
        return self.feed_token
    
    def get_auth_token(self) -> str:
        """Get auth token"""
        return self.auth_token
    
    def get_profile(self) -> Optional[Dict]:
        """Get user profile information"""
        if not self.is_authenticated:
            logger.warning("Not authenticated")
            return None
            
        try:
            profile = self.smart_api.getProfile(self.refresh_token)
            return profile.get("data")
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return None
    
    def get_funds(self) -> Optional[Dict]:
        """Get account funds/balance"""
        if not self.is_authenticated:
            return None
            
        try:
            funds = self.smart_api.rmsLimit()
            if funds.get("status"):
                return funds.get("data")
            return None
        except Exception as e:
            logger.error(f"Error fetching funds: {e}")
            return None
    
    def get_available_balance(self) -> float:
        """Get available trading balance"""
        funds = self.get_funds()
        if funds:
            return float(funds.get("net", 0))
        return 0.0
    
    def get_ltp(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[float]:
        """Get Last Traded Price for a symbol"""
        if not self.is_authenticated:
            return None
            
        try:
            data = self.smart_api.ltpData(exchange, symbol, token)
            if data.get("status"):
                return float(data["data"]["ltp"])
            return None
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str, token: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get full quote data for a symbol"""
        if not self.is_authenticated:
            return None
            
        try:
            data = self.smart_api.getQuote(exchange, symbol, token)
            if data.get("status"):
                return data["data"]
            return None
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None
    
    def get_historical_data(
        self,
        symbol: str,
        token: str,
        interval: str = "FIFTEEN_MINUTE",
        days: int = 5,
        exchange: str = "NSE"
    ) -> Optional[List[Dict]]:
        """
        Get historical candle data using Historical Data API.
        
        Intervals: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, 
                   THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        """
        if not self.is_authenticated:
            return None
            
        try:
            from src.utils.timezone import now_ist
            to_date = now_ist()
            from_date = to_date - timedelta(days=days)
            
            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M")
            }
            
            # Use Historical API for candle data
            data = self.historical_api.getCandleData(params)
            
            if data.get("status") and data.get("data"):
                candles = data["data"]
                return [
                    {
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": int(candle[5])
                    }
                    for candle in candles
                ]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def get_previous_day_ohlc(self, symbol: str, token: str,
                              exchange: str = "NSE") -> Optional[Dict]:
        """
        Get previous day's OHLC for pivot point calculation.
        
        This is used during pre-market analysis to calculate daily
        pivot points and support/resistance levels.
        
        Args:
            symbol: Stock symbol
            token: Stock token
            exchange: Exchange (default NSE)
        
        Returns:
            Dict with high, low, close, date or None if unavailable
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated - cannot fetch prev day OHLC")
            return None
        
        try:
            # Fetch last 3 days to handle weekends/holidays
            data = self.get_historical_data(
                symbol=symbol,
                token=token,
                interval="ONE_DAY",
                days=5,  # Extra buffer for long weekends
                exchange=exchange
            )
            
            if not data or len(data) < 2:
                logger.warning(
                    f"{symbol}: Insufficient daily data for pivot calculation "
                    f"(got {len(data) if data else 0} days)"
                )
                return None
            
            # Get second-to-last day (yesterday)
            yesterday = data[-2]
            
            # Validate data
            high = float(yesterday.get('high', 0))
            low = float(yesterday.get('low', 0))
            close = float(yesterday.get('close', 0))
            
            if high <= 0 or low <= 0 or close <= 0:
                logger.warning(f"{symbol}: Invalid prev day OHLC data")
                return None
            
            return {
                'high': high,
                'low': low,
                'close': close,
                'date': yesterday.get('timestamp', 'unknown')
            }
        
        except Exception as e:
            logger.error(f"Error fetching prev day OHLC for {symbol}: {e}")
            return None
    
    def place_order(
        self,
        symbol: str,
        token: str,
        transaction_type: str,  # BUY or SELL
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET",
        exchange: str = "NSE",
        product_type: str = "INTRADAY"
    ) -> Optional[str]:
        """Place an order using Trading API and return order ID"""
        if not self.is_authenticated:
            return None
            
        try:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": product_type,
                "duration": "DAY",
                "quantity": quantity
            }
            
            if order_type == "LIMIT":
                order_params["price"] = price
            
            # Use Trading API for orders
            response = self.smart_api.placeOrder(order_params)
            
            if response.get("status"):
                order_id = response["data"]["orderid"]
                logger.info(f"📝 Order placed: {order_id} | {transaction_type} {quantity} {symbol}")
                return order_id
            else:
                logger.error(f"Order failed: {response.get('message')}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def get_order_book(self) -> Optional[List[Dict]]:
        """Get all orders for today"""
        if not self.is_authenticated:
            return None
            
        try:
            orders = self.smart_api.orderBook()
            if orders.get("status"):
                return orders.get("data", [])
            return None
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return None
    
    def get_positions(self) -> Optional[List[Dict]]:
        """Get all open positions"""
        if not self.is_authenticated:
            return None
            
        try:
            positions = self.smart_api.position()
            if positions.get("status"):
                return positions.get("data", [])
            return None
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return None
    
    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> bool:
        """Cancel an order"""
        if not self.is_authenticated:
            return False
            
        try:
            response = self.smart_api.cancelOrder(order_id, variety)
            if response.get("status"):
                logger.info(f"Order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def logout(self) -> bool:
        """Logout from Angel One"""
        try:
            self.smart_api.terminateSession(self.client_id)
            self.is_authenticated = False
            logger.info("👋 Logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False