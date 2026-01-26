"""Pivot Point Calculator for support/resistance levels"""

from typing import Dict, Optional
from loguru import logger


class PivotPointCalculator:
    """
    Calculate daily pivot points for support/resistance analysis.
    
    Uses previous day's High, Low, Close to calculate standard pivot
    points and support/resistance levels.
    
    Professional traders use pivot confluence with VWAP for higher
    probability trade setups.
    """
    
    def __init__(self):
        """Initialize calculator with empty cache"""
        self.cached_pivots: Dict[str, Dict] = {}
    
    def calculate_standard_pivots(self, high: float, low: float, 
                                  close: float) -> Optional[Dict]:
        """
        Calculate standard pivot points.
        
        Formula:
        - Pivot = (H + L + C) / 3
        - R1 = 2*Pivot - L
        - R2 = Pivot + (H - L)
        - R3 = H + 2*(Pivot - L)
        - S1 = 2*Pivot - H
        - S2 = Pivot - (H - L)
        - S3 = L - 2*(H - Pivot)
        
        Args:
            high: Previous day's high
            low: Previous day's low
            close: Previous day's close
        
        Returns:
            Dict with all pivot levels or None if invalid data
        """
        # Edge case: Invalid inputs
        if high <= 0 or low <= 0 or close <= 0:
            logger.warning(
                f"Invalid OHLC data for pivot calculation: "
                f"H={high} L={low} C={close}"
            )
            return None
        
        # Edge case: Illogical values
        if low > high:
            logger.warning(
                f"Inconsistent OHLC: Low ({low}) > High ({high})"
            )
            return None
        
        if close > high or close < low:
            logger.warning(
                f"Close ({close}) outside H/L range ({low}-{high})"
            )
            # Don't fail - close can be outside intraday range for gaps
        
        # Calculate pivot point
        pivot = (high + low + close) / 3
        
        # Resistance levels
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        
        # Support levels
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': round(pivot, 2),
            'r1': round(r1, 2),
            'r2': round(r2, 2),
            'r3': round(r3, 2),
            's1': round(s1, 2),
            's2': round(s2, 2),
            's3': round(s3, 2),
            'source_high': high,
            'source_low': low,
            'source_close': close
        }
    
    def check_pivot_confluence(self, current_price: float, vwap: float,
                               pivots: Optional[Dict], 
                               tolerance: float = 0.002) -> tuple[bool, str]:
        """
        Check if VWAP cross coincides with pivot level break.
        
        Professional trick: Double confirmation when price breaks
        BOTH VWAP and a pivot level simultaneously or sequentially.
        
        This dramatically increases win rate by filtering weak signals.
        
        Args:
            current_price: Current stock price
            vwap: Current VWAP value
            pivots: Dict with pivot levels (from calculate_standard_pivots)
            tolerance: % tolerance for "near" a pivot (default 0.2%)
        
        Returns:
            Tuple of (has_confluence: bool, reason: str)
        """
        # Edge case: Missing pivot data
        if not pivots:
            return False, ""
        
        # Edge case: Invalid price/vwap
        if current_price <= 0 or vwap <= 0:
            return False, ""
        
        # Check if price is above VWAP (bullish setup)
        if current_price <= vwap:
            return False, "Price below VWAP"
        
        # Get pivot levels
        pivot = pivots['pivot']
        r1 = pivots['r1']
        r2 = pivots['r2']
        s1 = pivots['s1']
        
        # Check proximity to pivot levels (bullish breakout scenarios)
        
        # Scenario 1: Price breaking above pivot point
        if abs(current_price - pivot) / pivot <= tolerance:
            if current_price > pivot:
                return True, "VWAP + Pivot Breakout"
        
        # Scenario 2: Price breaking above R1
        if abs(current_price - r1) / r1 <= tolerance:
            if current_price > r1:
                return True, "VWAP + R1 Breakout"
        
        # Scenario 3: Price above pivot, heading to R1
        if pivot < current_price < r1:
            # Check if we're far enough from pivot (confirmed break)
            if (current_price - pivot) / pivot > 0.003:  # 0.3% above pivot
                return True, "VWAP + Above Pivot"
        
        # Scenario 4: Price above R1, strong momentum
        if current_price > r1:
            return True, "VWAP + Above R1"
        
        # Scenario 5: Price bouncing off support (S1) with VWAP cross
        # This is for recovery trades
        if abs(current_price - s1) / s1 <= tolerance:
            if current_price > s1:  # Bouncing off support
                return True, "VWAP + S1 Bounce"
        
        return False, ""
    
    def cache_pivots(self, symbol: str, pivots: Dict) -> None:
        """
        Store calculated pivots for the trading day.
        
        Pivots are calculated once during pre-market and cached
        to avoid redundant calculations during trading hours.
        """
        if pivots:
            self.cached_pivots[symbol] = pivots
            logger.debug(
                f"{symbol}: Pivots cached - "
                f"P={pivots['pivot']} R1={pivots['r1']} S1={pivots['s1']}"
            )
    
    def get_cached_pivots(self, symbol: str) -> Optional[Dict]:
        """Retrieve cached pivot points for a symbol"""
        return self.cached_pivots.get(symbol)
    
    def clear_cache(self) -> None:
        """Clear all cached pivots (call at end of day)"""
        self.cached_pivots = {}
        logger.info("Pivot cache cleared")
