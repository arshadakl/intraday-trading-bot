"""Nifty Index Tracker - Track Nifty index for market trend correlation"""

from typing import Dict, Optional
from datetime import datetime, time
from loguru import logger

from src.utils.timezone import now_ist, now_ist_time


class NiftyIndexTracker:
    """
    Tracks Nifty 50 index for market trend correlation.
    
    Used by strategies like OHL to determine:
    - Market direction (bullish/bearish)
    - Whether to take long or short trades
    - Overall market sentiment
    
    Data sources:
    - WebSocket feed (real-time)
    - Historical API (for opening price)
    """
    
    # Nifty token from config/nifty50.json
    NIFTY_TOKEN = "99926000"
    NIFTY_SYMBOL = "NIFTY"
    
    def __init__(self):
        # Daily state
        self.open_price: Optional[float] = None
        self.prev_close: Optional[float] = None  # Yesterday's closing price
        self.current_price: Optional[float] = None
        self.day_high: Optional[float] = None
        self.day_low: Optional[float] = None
        self.last_update: Optional[datetime] = None
        
        # Trend tracking
        self.trend: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
        self.trend_strength: float = 0.0  # 0 to 1
        
        # First candle data (for OHL detection on index)
        self.first_candle_high: Optional[float] = None
        self.first_candle_low: Optional[float] = None
        self.first_15min_high: Optional[float] = None
        self.first_15min_low: Optional[float] = None
    
    def reset_daily(self) -> None:
        """Reset all state for new trading day (preserves prev_close)"""
        self.open_price = None
        # NOTE: Do NOT reset prev_close — it's needed for gap calculation
        self.current_price = None
        self.day_high = None
        self.day_low = None
        self.last_update = None
        self.trend = "NEUTRAL"
        self.trend_strength = 0.0
        self.first_candle_high = None
        self.first_candle_low = None
        self.first_15min_high = None
        self.first_15min_low = None
        logger.debug("📊 Nifty tracker reset for new day")
    
    def set_prev_close(self, value: float) -> None:
        """Set yesterday's closing price for gap calculation"""
        if value and value > 0:
            self.prev_close = value
            logger.info(f"📊 Nifty prev_close set: {self.prev_close:.2f}")
    
    def get_gap_percent(self) -> float:
        """Get opening gap percentage: ((open - prev_close) / prev_close) * 100"""
        if self.prev_close and self.prev_close > 0 and self.open_price:
            return ((self.open_price - self.prev_close) / self.prev_close) * 100
        return 0.0
    
    def get_gap_status(self, threshold: float = 0.2) -> str:
        """Get gap status: GAP_UP, GAP_DOWN, or FLAT (based on threshold %)"""
        gap_pct = self.get_gap_percent()
        if gap_pct > threshold:
            return "GAP_UP"
        elif gap_pct < -threshold:
            return "GAP_DOWN"
        return "FLAT"
    
    def update(self, price_data: Dict) -> None:
        """
        Update Nifty data from WebSocket feed.
        
        Args:
            price_data: Dict with ltp, open, high, low from WebSocket
        """
        try:
            ltp = float(price_data.get('ltp', 0))
            if ltp <= 0:
                return
            
            self.current_price = ltp
            self.last_update = now_ist()
            
            # Get OHLC from WebSocket (it provides day's values)
            ws_open = float(price_data.get('open', 0))
            ws_high = float(price_data.get('high', 0))
            ws_low = float(price_data.get('low', 0))
            
            if ws_open > 0 and self.open_price is None:
                self.open_price = ws_open
                logger.info(f"📊 Nifty open price set: {self.open_price:.2f}")
            
            if ws_high > 0:
                self.day_high = ws_high
            if ws_low > 0:
                self.day_low = ws_low
            
            # Update first candle data (only in first minute)
            current_time = now_ist_time()
            market_open_plus_1 = time(9, 16)
            
            if current_time < market_open_plus_1:
                # Still in first candle, update high/low
                if self.first_candle_high is None or ltp > self.first_candle_high:
                    self.first_candle_high = ltp
                if self.first_candle_low is None or ltp < self.first_candle_low:
                    self.first_candle_low = ltp
            
            # Update first 15 min range (9:15 - 9:30)
            market_open_plus_15 = time(9, 30)
            if current_time < market_open_plus_15:
                if self.first_15min_high is None or ltp > self.first_15min_high:
                    self.first_15min_high = ltp
                if self.first_15min_low is None or ltp < self.first_15min_low:
                    self.first_15min_low = ltp
            
            # Update trend
            self._update_trend()
            
        except Exception as e:
            logger.debug(f"Nifty update error: {e}")
    
    def _update_trend(self) -> None:
        """Calculate current market trend based on price vs open"""
        if self.open_price is None or self.current_price is None:
            self.trend = "NEUTRAL"
            self.trend_strength = 0.0
            return
        
        # Calculate change from open
        change_pct = ((self.current_price - self.open_price) / self.open_price) * 100
        
        # Determine trend
        if change_pct > 0.1:  # More than 0.1% up
            self.trend = "BULLISH"
            self.trend_strength = min(1.0, abs(change_pct) / 1.0)  # Normalize to 1% max
        elif change_pct < -0.1:  # More than 0.1% down
            self.trend = "BEARISH"
            self.trend_strength = min(1.0, abs(change_pct) / 1.0)
        else:
            self.trend = "NEUTRAL"
            self.trend_strength = 0.0
    
    def is_bullish(self) -> bool:
        """Check if Nifty is in bullish trend"""
        return self.trend == "BULLISH"
    
    def is_bearish(self) -> bool:
        """Check if Nifty is in bearish trend"""
        return self.trend == "BEARISH"
    
    def is_neutral(self) -> bool:
        """Check if Nifty is in neutral/sideways trend"""
        return self.trend == "NEUTRAL"
    
    def get_change_percent(self) -> float:
        """Get current change from open in percentage"""
        if self.open_price is None or self.current_price is None:
            return 0.0
        return ((self.current_price - self.open_price) / self.open_price) * 100
    
    def get_change_points(self) -> float:
        """Get current change from open in points"""
        if self.open_price is None or self.current_price is None:
            return 0.0
        return self.current_price - self.open_price
    
    def get_intraday_range_percent(self) -> float:
        """Get intraday range as percentage of open"""
        if self.day_high is None or self.day_low is None or self.open_price is None:
            return 0.0
        return ((self.day_high - self.day_low) / self.open_price) * 100
    
    def should_trade_direction(self, signal_direction: str) -> bool:
        """
        Check if a trade direction aligns with Nifty trend.
        
        For OHL strategy:
        - If Nifty is bullish, only take BUY signals
        - If Nifty is bearish, only take SELL/SHORT signals
        - If neutral, allow both (but with caution)
        
        Args:
            signal_direction: "BUY" or "SELL"
            
        Returns:
            True if trade direction aligns with market
        """
        signal_direction = signal_direction.upper()
        
        if self.trend == "BULLISH":
            return signal_direction == "BUY"
        elif self.trend == "BEARISH":
            return signal_direction == "SELL"
        else:
            # Neutral - allow both with lower confidence
            return True
    
    def get_status(self) -> Dict:
        """Get current Nifty status for logging/display"""
        return {
            "symbol": self.NIFTY_SYMBOL,
            "token": self.NIFTY_TOKEN,
            "prev_close": self.prev_close,
            "open": self.open_price,
            "current": self.current_price,
            "high": self.day_high,
            "low": self.day_low,
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "gap_pct": round(self.get_gap_percent(), 2),
            "gap_status": self.get_gap_status(),
            "change_pct": self.get_change_percent(),
            "change_pts": self.get_change_points(),
            "range_pct": self.get_intraday_range_percent(),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "first_15min_high": self.first_15min_high,
            "first_15min_low": self.first_15min_low
        }
    
    def is_volatile_day(self, threshold_pct: float = 1.5) -> bool:
        """
        Check if today is a high volatility day.
        
        High volatility days (like Budget day) should be avoided
        or traded with extra caution.
        
        Args:
            threshold_pct: Range percentage threshold (default 1.5%)
            
        Returns:
            True if intraday range exceeds threshold
        """
        return self.get_intraday_range_percent() > threshold_pct
    
    def is_range_bound(self, threshold_pct: float = 0.3) -> bool:
        """
        Check if market is in a tight range (sideways).
        
        Range-bound markets are risky for breakout strategies.
        
        Args:
            threshold_pct: Minimum range for trending market
            
        Returns:
            True if intraday range is below threshold
        """
        return self.get_intraday_range_percent() < threshold_pct


# Singleton instance
_nifty_tracker: Optional[NiftyIndexTracker] = None


def get_nifty_tracker() -> NiftyIndexTracker:
    """Get or create the singleton Nifty tracker instance"""
    global _nifty_tracker
    if _nifty_tracker is None:
        _nifty_tracker = NiftyIndexTracker()
    return _nifty_tracker
