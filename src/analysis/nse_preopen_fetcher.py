"""NSE Pre-Open Market Data Fetcher - Fetches pre-open market data from NSE India

This module handles fetching pre-open market data from NSE India's website/API.
The pre-open session runs from 9:00 AM - 9:08 AM IST, with price matching till 9:15 AM.

Data includes:
- Indicative Equilibrium Price (IEP) - The expected opening price
- Previous close
- Change percentage (gap up/down)
- Volume

This data is used by the 3-Minute Strategy to identify gap-up and gap-down candidates.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from loguru import logger

from src.utils.timezone import now_ist, now_ist_time


class NSEPreOpenFetcher:
    """
    Fetches pre-open market data from NSE India.
    
    NSE provides pre-open data through their website/API endpoints.
    This class handles:
    - Session management (cookies for NSE access)
    - Rate limiting (to avoid being blocked)
    - Data parsing and normalization
    - Caching (to reduce API calls)
    
    Usage:
        fetcher = NSEPreOpenFetcher()
        data = fetcher.fetch_preopen_data()
        gainers = fetcher.get_top_gainers(count=10)
        losers = fetcher.get_top_losers(count=10)
    """
    
    # NSE API endpoints
    NSE_BASE_URL = "https://www.nseindia.com"
    PREOPEN_API_URL = "https://www.nseindia.com/api/market-data-pre-open"
    
    # Segment keys for API
    SEGMENTS = {
        'nifty': 'NIFTY',
        'banknifty': 'BANKNIFTY',
        'fo': 'FO',
        'all': 'ALL',
        'sme': 'SME',
        'others': 'OTHERS'
    }
    
    # Request headers to mimic browser
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    def __init__(self, segment: str = 'nifty'):
        """
        Initialize the NSE Pre-Open Fetcher.
        
        Args:
            segment: Market segment to fetch data for ('nifty', 'banknifty', 'fo', 'all')
        """
        self.segment = self.SEGMENTS.get(segment.lower(), 'NIFTY')
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        
        # Caching
        self._cache: Dict = {}
        self._cache_time: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)  # Cache for 30 seconds
        self._lock = threading.Lock()
        
        # Rate limiting
        self._last_request_time: Optional[datetime] = None
        self._min_request_interval = 1.0  # Minimum 1 second between requests
        
        # Data storage
        self.preopen_data: List[Dict] = []
        self.last_fetch_time: Optional[datetime] = None
        
    def _initialize_session(self) -> bool:
        """
        Initialize session by visiting NSE homepage to get cookies.
        
        NSE requires specific cookies for API access. This method
        visits the homepage to obtain those cookies.
        
        Returns:
            True if session initialized successfully
        """
        try:
            logger.debug("Initializing NSE session...")
            
            # First visit the homepage to get cookies
            response = self.session.get(
                self.NSE_BASE_URL,
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.debug("NSE session initialized with cookies")
                return True
            else:
                logger.warning(f"NSE homepage returned status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to initialize NSE session: {e}")
            return False
    
    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            elapsed = (now_ist() - self._last_request_time).total_seconds()
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = now_ist()
    
    def fetch_preopen_data(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch pre-open market data from NSE.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of stock data dictionaries with pre-open info
        """
        with self._lock:
            # Check cache
            if not force_refresh and self._cache and self._cache_time:
                if now_ist() - self._cache_time < self._cache_duration:
                    logger.debug("Returning cached pre-open data")
                    return self._cache.get('data', [])
            
            # Rate limiting
            self._rate_limit()
            
            # Initialize session if needed
            if not self.session.cookies:
                if not self._initialize_session():
                    logger.error("Failed to initialize NSE session")
                    return []
                time.sleep(0.5)  # Small delay after cookie fetch
            
            try:
                # Fetch pre-open data
                url = f"{self.PREOPEN_API_URL}?key={self.segment}"
                logger.info(f"Fetching pre-open data from NSE for segment: {self.segment}")
                
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    raw_data = response.json()
                    
                    # Parse the data
                    parsed_data = self._parse_preopen_data(raw_data)
                    
                    # Update cache
                    self._cache = {'data': parsed_data, 'raw': raw_data}
                    self._cache_time = now_ist()
                    self.preopen_data = parsed_data
                    self.last_fetch_time = now_ist()
                    
                    logger.info(f"Successfully fetched {len(parsed_data)} stocks from pre-open data")
                    return parsed_data
                    
                elif response.status_code == 401 or response.status_code == 403:
                    # Session expired, reinitialize
                    logger.warning("NSE session expired, reinitializing...")
                    self.session.cookies.clear()
                    if self._initialize_session():
                        time.sleep(0.5)
                        return self.fetch_preopen_data(force_refresh=True)
                    return []
                    
                else:
                    logger.error(f"NSE API returned status {response.status_code}")
                    return []
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching pre-open data: {e}")
                return []
            except Exception as e:
                logger.error(f"Error parsing pre-open data: {e}")
                return []
    
    def _parse_preopen_data(self, raw_data: Dict) -> List[Dict]:
        """
        Parse raw NSE pre-open API response into normalized format.
        
        NSE API returns data in format:
        {
            "data": [
                {
                    "metadata": {
                        "symbol": "RELIANCE",
                        "lastPrice": 2850.0,
                        "change": 45.5,
                        "pChange": 1.62,
                        "previousClose": 2804.5,
                        "iep": 2850.0,  # Indicative Equilibrium Price
                        "totalTradedVolume": 125000,
                        ...
                    },
                    "detail": { ... }
                },
                ...
            ],
            "advances": 35,
            "declines": 15,
            "unchanged": 0
        }
        
        Args:
            raw_data: Raw API response
            
        Returns:
            List of normalized stock data dictionaries
        """
        parsed = []
        
        try:
            data_list = raw_data.get('data', [])
            
            for item in data_list:
                metadata = item.get('metadata', {})
                
                if not metadata:
                    continue
                
                symbol = metadata.get('symbol', '')
                if not symbol:
                    continue
                
                # Extract key fields
                stock_data = {
                    'symbol': symbol,
                    'symbol_eq': f"{symbol}-EQ",  # For trading (e.g., RELIANCE-EQ)
                    
                    # Price data
                    'iep': float(metadata.get('iep', 0)),  # Indicative Equilibrium Price
                    'last_price': float(metadata.get('lastPrice', 0)),
                    'prev_close': float(metadata.get('previousClose', 0)),
                    
                    # Change data
                    'change': float(metadata.get('change', 0)),
                    'change_percent': float(metadata.get('pChange', 0)),
                    
                    # Volume
                    'volume': int(metadata.get('totalTradedVolume', 0)),
                    'final_quantity': int(metadata.get('finalQuantity', 0)),
                    
                    # Additional fields
                    'year_high': float(metadata.get('yearHigh', 0)),
                    'year_low': float(metadata.get('yearLow', 0)),
                    
                    # Gap analysis
                    'gap_percent': 0.0,  # Will be calculated
                    'gap_type': 'NEUTRAL',  # BULLISH, BEARISH, NEUTRAL
                }
                
                # Calculate gap
                if stock_data['prev_close'] > 0 and stock_data['iep'] > 0:
                    gap = ((stock_data['iep'] - stock_data['prev_close']) / 
                           stock_data['prev_close']) * 100
                    stock_data['gap_percent'] = round(gap, 2)
                    
                    # Classify gap type
                    if gap >= 0.5:
                        stock_data['gap_type'] = 'BULLISH'  # Gap up
                    elif gap <= -0.5:
                        stock_data['gap_type'] = 'BEARISH'  # Gap down
                    else:
                        stock_data['gap_type'] = 'NEUTRAL'
                
                parsed.append(stock_data)
            
            # Sort by absolute gap percentage (highest gaps first)
            parsed.sort(key=lambda x: abs(x['gap_percent']), reverse=True)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing pre-open data: {e}")
            return []
    
    def get_top_gainers(self, count: int = 10, min_gap: float = 1.0) -> List[Dict]:
        """
        Get top gap-up stocks from pre-open data.
        
        Args:
            count: Number of stocks to return
            min_gap: Minimum gap percentage to consider (default 1%)
            
        Returns:
            List of top gainer stocks
        """
        if not self.preopen_data:
            self.fetch_preopen_data()
        
        gainers = [
            stock for stock in self.preopen_data
            if stock['gap_percent'] >= min_gap
        ]
        
        # Sort by gap percentage (highest first)
        gainers.sort(key=lambda x: x['gap_percent'], reverse=True)
        
        return gainers[:count]
    
    def get_top_losers(self, count: int = 10, min_gap: float = 1.0) -> List[Dict]:
        """
        Get top gap-down stocks from pre-open data.
        
        Args:
            count: Number of stocks to return
            min_gap: Minimum gap percentage to consider (default 1% - will be negated)
            
        Returns:
            List of top loser stocks
        """
        if not self.preopen_data:
            self.fetch_preopen_data()
        
        losers = [
            stock for stock in self.preopen_data
            if stock['gap_percent'] <= -min_gap
        ]
        
        # Sort by gap percentage (most negative first)
        losers.sort(key=lambda x: x['gap_percent'])
        
        return losers[:count]
    
    def get_gap_stocks(self, min_gap: float = 1.0, max_stocks: int = 10) -> Tuple[List[Dict], List[Dict]]:
        """
        Get both gap-up and gap-down stocks for trading.
        
        Args:
            min_gap: Minimum gap percentage (default 1%)
            max_stocks: Maximum stocks per category
            
        Returns:
            Tuple of (gainers, losers) lists
        """
        gainers = self.get_top_gainers(count=max_stocks, min_gap=min_gap)
        losers = self.get_top_losers(count=max_stocks, min_gap=min_gap)
        
        logger.info(
            f"Pre-open gap analysis: {len(gainers)} gainers (>{min_gap}%), "
            f"{len(losers)} losers (<-{min_gap}%)"
        )
        
        return gainers, losers
    
    def is_preopen_session(self) -> bool:
        """
        Check if current time is within pre-open session (9:00 - 9:08 AM IST).
        
        Returns:
            True if in pre-open session
        """
        now = now_ist_time()
        preopen_start = datetime.strptime("09:00", "%H:%M").time()
        preopen_end = datetime.strptime("09:08", "%H:%M").time()
        
        return preopen_start <= now <= preopen_end
    
    def is_preopen_matching(self) -> bool:
        """
        Check if current time is in price matching period (9:08 - 9:15 AM IST).
        
        Returns:
            True if in matching period
        """
        now = now_ist_time()
        matching_start = datetime.strptime("09:08", "%H:%M").time()
        matching_end = datetime.strptime("09:15", "%H:%M").time()
        
        return matching_start <= now <= matching_end
    
    def is_preopen_data_final(self) -> bool:
        """
        Check if pre-open data is final and ready for stock picking.
        
        NSE pre-open session:
        - 9:00-9:08 AM: Order entry period (data changes frequently)
        - 9:08-9:10 AM: Order matching period (final price being determined)
        - 9:10-9:15 AM: Final IEP available, data is stable
        
        The data is considered "final" after 9:10 AM when price matching
        is complete and IEP (Indicative Equilibrium Price) is confirmed.
        
        Returns:
            True if current time is after 9:10 AM (pre-open data is final)
        """
        now = now_ist_time()
        data_final_time = datetime.strptime("09:10", "%H:%M").time()
        
        return now >= data_final_time
    
    def is_before_market_open(self) -> bool:
        """
        Check if current time is before market opens (before 9:15 AM).
        
        Returns:
            True if before market open
        """
        now = now_ist_time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        
        return now < market_open
    
    def get_time_until_data_ready(self) -> int:
        """
        Get seconds until pre-open data is ready for stock picking.
        
        The final pre-open data is available at 9:10 AM.
        
        Returns:
            Seconds until 9:10 AM, or 0 if already past 9:10 AM
        """
        now = now_ist()
        target_time = now.replace(hour=9, minute=10, second=0, microsecond=0)
        
        if now >= target_time:
            return 0
        
        return int((target_time - now).total_seconds())
    
    def wait_for_final_data(self, callback=None) -> bool:
        """
        Wait until pre-open data is final (after 9:10 AM).
        
        This method blocks until 9:10 AM when the pre-open data is finalized.
        It's designed to be called when the bot starts before 9:10 AM.
        
        Args:
            callback: Optional callback function to call every 30 seconds while waiting
                      Signature: callback(seconds_remaining: int)
        
        Returns:
            True when data is ready, False if interrupted
        """
        seconds_remaining = self.get_time_until_data_ready()
        
        if seconds_remaining == 0:
            logger.info("📊 Pre-open data is already final (after 9:10 AM)")
            return True
        
        logger.info(f"⏳ Waiting {seconds_remaining} seconds for final pre-open data (until 9:10 AM)...")
        
        while seconds_remaining > 0:
            # Log and callback every 30 seconds
            if callback:
                callback(seconds_remaining)
            else:
                minutes = seconds_remaining // 60
                secs = seconds_remaining % 60
                logger.info(f"⏳ Pre-open data will be ready in {minutes}m {secs}s...")
            
            # Wait in smaller intervals for responsiveness
            wait_time = min(30, seconds_remaining)
            time.sleep(wait_time)
            
            seconds_remaining = self.get_time_until_data_ready()
        
        logger.info("✅ Pre-open data is now final! Ready for stock picking.")
        return True
    
    def fetch_final_preopen_data(self, wait_if_not_ready: bool = True) -> List[Dict]:
        """
        Fetch final pre-open data, optionally waiting if data is not ready.
        
        This is the main method to use for the 3-Minute Strategy.
        It ensures that the data fetched is the final, stable data after 9:10 AM.
        
        Args:
            wait_if_not_ready: If True and current time is before 9:10 AM,
                              wait until data is ready. If False, fetch anyway.
        
        Returns:
            List of stock data with final pre-open prices
        """
        if wait_if_not_ready and not self.is_preopen_data_final():
            self.wait_for_final_data()
        
        # Fetch fresh data (force refresh to get latest)
        data = self.fetch_preopen_data(force_refresh=True)
        
        if data:
            logger.info(f"📊 Fetched final pre-open data: {len(data)} stocks")
            # Log top gainers and losers
            gainers = [s for s in data if s['gap_percent'] >= 1.0][:3]
            losers = [s for s in data if s['gap_percent'] <= -1.0][:3]
            
            if gainers:
                gainer_info = [(s['symbol'], f"+{s['gap_percent']:.2f}%") for s in gainers]
                logger.info(f"  📈 Top Gainers: {gainer_info}")
            if losers:
                loser_info = [(s['symbol'], f"{s['gap_percent']:.2f}%") for s in losers]
                logger.info(f"  📉 Top Losers: {loser_info}")
        
        return data
    
    def get_market_breadth(self) -> Dict:
        """
        Get market breadth from pre-open data.
        
        Returns:
            Dict with advances, declines, unchanged counts
        """
        if not self._cache:
            self.fetch_preopen_data()
        
        raw_data = self._cache.get('raw', {})
        
        return {
            'advances': raw_data.get('advances', 0),
            'declines': raw_data.get('declines', 0),
            'unchanged': raw_data.get('unchanged', 0),
            'market_sentiment': self._calculate_sentiment(raw_data)
        }
    
    def _calculate_sentiment(self, raw_data: Dict) -> str:
        """Calculate overall market sentiment from advances/declines."""
        advances = raw_data.get('advances', 0)
        declines = raw_data.get('declines', 0)
        
        if advances == 0 and declines == 0:
            return 'NEUTRAL'
        
        ratio = advances / (advances + declines) if (advances + declines) > 0 else 0.5
        
        if ratio >= 0.65:
            return 'BULLISH'
        elif ratio <= 0.35:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def get_status(self) -> Dict:
        """Get current status of the fetcher."""
        return {
            'segment': self.segment,
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            'stocks_count': len(self.preopen_data),
            'is_preopen_session': self.is_preopen_session(),
            'is_matching_period': self.is_preopen_matching(),
            'market_breadth': self.get_market_breadth()
        }


# Singleton instance for global access
_nse_preopen_fetcher: Optional[NSEPreOpenFetcher] = None


def get_nse_preopen_fetcher(segment: str = 'nifty') -> NSEPreOpenFetcher:
    """
    Get the singleton NSE Pre-Open Fetcher instance.
    
    Args:
        segment: Market segment (nifty, banknifty, fo, all)
        
    Returns:
        NSEPreOpenFetcher instance
    """
    global _nse_preopen_fetcher
    
    if _nse_preopen_fetcher is None:
        _nse_preopen_fetcher = NSEPreOpenFetcher(segment=segment)
    
    return _nse_preopen_fetcher
