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
        
        # Cache for historical data (key: (symbol, token, interval), value: (data, timestamp))
        self._hist_cache: Dict[tuple, tuple] = {}
        self._hist_cache_ttl = 60  # Cache TTL in seconds
        
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
        
        if token == "99926000" and symbol.upper() == "NIFTY":
            return self._get_nifty_index_quote()
        
        try:
            ltp_result = self.smart_api.ltpData(exchange, symbol, token)
            if ltp_result and ltp_result.get("status"):
                data = ltp_result.get("data", {})
                return {
                    "symbol": data.get("symbol"),
                    "token": data.get("token"),
                    "ltp": data.get("ltp"),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "previousClose": data.get("previousClose"),
                    "volume": data.get("volume"),
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None
    
    def _get_nifty_index_quote(self) -> Optional[Dict]:
        """Get NIFTY index quote from NSE pre-open data"""
        try:
            from src.analysis.nse_preopen_fetcher import get_nse_preopen_fetcher
            fetcher = get_nse_preopen_fetcher(segment='nifty')
            data = fetcher.fetch_final_preopen_data(wait_if_not_ready=False)
            if data and len(data) > 0:
                nifty_info = data[0]
                return {
                    "symbol": "NIFTY",
                    "token": "99926000",
                    "ltp": nifty_info.get('iep'),
                    "open": nifty_info.get('open'),
                    "high": nifty_info.get('high'),
                    "low": nifty_info.get('low'),
                    "previousClose": nifty_info.get('previousClose') or nifty_info.get('pp'),
                }
        except Exception as e:
            logger.error(f"Error fetching NIFTY from NSE: {e}")
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
        
        Intervals: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE,
                   FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        
        Date format expected by API: "YYYY-MM-DD HH:MM"
        """
        if not self.is_authenticated:
            return None
        
        # [FIX] Validate symboltoken before making API call — empty token causes AB1004
        if not token or str(token).strip() == "":
            logger.warning(f"⚠️ {symbol}: Cannot fetch historical data — symboltoken is empty")
            return None
        
        import time
        from src.utils.timezone import now_ist_time
        
        # Check cache first
        cache_key = (symbol, token, interval, days)
        if cache_key in self._hist_cache:
            cached_data, cached_time = self._hist_cache[cache_key]
            if time.time() - cached_time < self._hist_cache_ttl:
                return cached_data
        
        # [FIX] Reduce retries during market hours (9:00-15:30) when API is overloaded
        current_time = now_ist_time()
        is_market_hours = (current_time.hour == 9 and current_time.minute >= 0) or \
                         (9 < current_time.hour < 15) or \
                         (current_time.hour == 15 and current_time.minute <= 30)
        
        # During market hours: fail fast (1 retry only), outside market hours: retry more
        max_retries = 1 if is_market_hours else 2
        retry_delay = 0.5 if is_market_hours else 1  # Faster fail during market hours
        
        # Validate interval against SmartAPI supported values
        valid_intervals = [
            "ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE", "TEN_MINUTE",
            "FIFTEEN_MINUTE", "THIRTY_MINUTE", "ONE_HOUR", "ONE_DAY"
        ]
        if interval not in valid_intervals:
            logger.warning(f"⚠️ {symbol}: Invalid interval '{interval}'. Using FIFTEEN_MINUTE.")
            interval = "FIFTEEN_MINUTE"
        
        for attempt in range(max_retries):
            try:
                from src.utils.timezone import now_ist
                to_date = now_ist()
                from_date = to_date - timedelta(days=days)
                
                # [FIX] Clamp times to market hours for intraday intervals
                # SmartAPI returns no data for timestamps outside 9:00-15:30
                if interval != "ONE_DAY":
                    # Clamp to_date to max 15:30 of today
                    market_close_today = to_date.replace(hour=15, minute=30, second=0, microsecond=0)
                    if to_date > market_close_today:
                        to_date = market_close_today
                    
                    # Clamp from_date to 9:00 of that day
                    from_date_market_open = from_date.replace(hour=9, minute=0, second=0, microsecond=0)
                    if from_date < from_date_market_open:
                        from_date = from_date_market_open
                
                params = {
                    "exchange": exchange,
                    "symboltoken": str(token),
                    "interval": interval,
                    "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                    "todate": to_date.strftime("%Y-%m-%d %H:%M")
                }
                
                # Use Historical API for candle data
                data = self.historical_api.getCandleData(params)
                
                if data.get("status"):
                    if data.get("data"):
                        candles = data["data"]
                        result = [
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
                        self._hist_cache[cache_key] = (result, time.time())
                        return result
                    else:
                        logger.debug(f"{symbol}: No data in successful response")
                        return None
                
                # If we got here, status is False
                message = data.get("message", "").lower()
                error_code = data.get("errorcode", "")
                
                # [FIX] Rate limit or bad param error — fail fast, don't retry during market hours
                if "access denied" in message or "exceeding access rate" in message or error_code == "AB1004":
                    if attempt < max_retries - 1:
                        logger.debug(f"⏳ Rate limit hit for {symbol} ({error_code}). Quick retry {attempt+1}/{max_retries}")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Final attempt failed — log once and return
                        logger.debug(f"❌ {symbol}: API error ({error_code}) — skipping")
                        return None
                
                logger.error(f"Error fetching historical data for {symbol}: {data.get('message')} ({error_code})")
                return None
                
            except Exception as e:
                logger.error(f"Exception fetching historical data for {symbol}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
        
        return None
    
    def get_historical_data_for_date(
        self,
        symbol: str,
        token: str,
        date_str: str,
        interval: str = "THREE_MINUTE",
        exchange: str = "NSE",
        include_prev_day: bool = True,
    ) -> Optional[List[Dict]]:
        """
        Get historical candle data for a specific date.
        Used by the backtester to fetch data for past dates.
        
        Args:
            symbol: Stock symbol (e.g., "SBIN-EQ")
            token: Angel One symbol token
            date_str: Date string in YYYY-MM-DD format
            interval: Candle interval (default THREE_MINUTE for strategy)
            exchange: Exchange (default NSE)
            include_prev_day: If True, fetches prev day data too (for gap calculation)
        
        Returns:
            List of candle dicts or None
        """
        if not self.is_authenticated:
            return None
        
        if not token or str(token).strip() == "":
            return None
        
        import time as time_mod
        from datetime import datetime, timedelta
        
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"⚠️ Invalid date format: {date_str}")
            return None
        
        # Set date range: include previous trading day for gap calculation
        if include_prev_day:
            from_date = (target_date - timedelta(days=3))  # 3 days back to handle weekends
            from_str = from_date.strftime("%Y-%m-%d") + " 09:00"
        else:
            from_str = date_str + " 09:00"
        
        to_str = date_str + " 15:30"
        
        try:
            params = {
                "exchange": exchange,
                "symboltoken": str(token),
                "interval": interval,
                "fromdate": from_str,
                "todate": to_str,
            }
            
            data = self.historical_api.getCandleData(params)
            
            if data and data.get("status") and data.get("data"):
                candles = data["data"]
                result = [
                    {
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": int(candle[5]),
                    }
                    for candle in candles
                ]
                return result
            
            error_code = data.get("errorcode", "") if data else ""
            if error_code:
                logger.debug(f"📊 Backtest data fetch for {symbol}/{date_str}: {error_code}")
            return None
            
        except Exception as e:
            logger.debug(f"📊 Backtest fetch error for {symbol}/{date_str}: {e}")
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