"""OHL Stock Picker - Stock selection for Open=High/Low strategy"""

from typing import Dict, List, Optional
from loguru import logger

from src.analysis.base_stock_picker import BaseStockPicker, StockPickerRegistry


class OHLStockPicker(BaseStockPicker):
    """
    Stock picker optimized for OHL (Open=High or Open=Low) strategy.
    
    OHL works best with:
    - F&O stocks (high liquidity) - Nifty50 already provides this
    - Stocks with clear gaps (gap up/gap down from previous close)
    - Stocks with higher volume on opening
    - Moderate volatility (not too extreme)
    
    Selection Criteria:
    1. Gap Detection: Prefer stocks with clear gaps (> 0.5%)
    2. Volume Surge: Opening volume should be higher than average
    3. ATR Filter: Volatility between 1.5% - 4% (tradeable range)
    4. Price Filter: Standard price range for position sizing
    
    Scoring weights favor stocks that are more likely to show
    clean O=H or O=L patterns.
    """
    
    def __init__(self):
        super().__init__("ohl")
        
        # OHL-specific weights
        # Gap and volume are more important for OHL
        self.weights = {
            'gap': 0.35,        # Gap from previous close
            'volume': 0.30,     # Opening volume surge
            'volatility': 0.20, # ATR-based volatility
            'trend': 0.15       # Previous day trend clarity
        }
        
        # Filters
        self.min_price = 100
        self.max_price = 5000
        self.min_gap_percent = 0.3      # Minimum gap to consider
        self.ideal_gap_percent = 1.0    # Ideal gap for scoring
        self.max_gap_percent = 5.0      # Avoid extreme gaps (circuit limits)
        self.min_volume_ratio = 1.2     # Minimum volume vs average
        self.min_atr_percent = 1.0      # Minimum volatility
        self.max_atr_percent = 4.0      # Maximum volatility
    
    def get_scoring_weights(self) -> Dict[str, float]:
        return self.weights.copy()
    
    def filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """
        Filter stocks suitable for OHL strategy.
        
        Filters applied:
        1. Price range (100-5000)
        2. Minimum volume ratio (1.2x average)
        3. Avoid extreme gaps (>5%)
        4. Avoid very low volatility (<1%)
        """
        filtered = []
        
        for stock in stocks:
            symbol = stock.get('symbol', 'UNKNOWN')
            
            # Price filter
            price = stock.get('price', stock.get('close', stock.get('ltp', 0)))
            if not (self.min_price <= price <= self.max_price):
                logger.debug(f"{symbol}: Price {price} out of range")
                continue
            
            # Volume filter (if available)
            volume_ratio = stock.get('volume_ratio', 1.0)
            if volume_ratio < self.min_volume_ratio:
                logger.debug(f"{symbol}: Volume ratio {volume_ratio:.2f} too low")
                continue
            
            # Gap filter (avoid extreme gaps that might hit circuit)
            gap_percent = self._calculate_gap_percent(stock)
            if abs(gap_percent) > self.max_gap_percent:
                logger.debug(f"{symbol}: Gap {gap_percent:.2f}% too extreme")
                continue
            
            # Volatility filter
            atr_percent = self._calculate_atr_percent(stock)
            if atr_percent < self.min_atr_percent:
                logger.debug(f"{symbol}: ATR {atr_percent:.2f}% too low")
                continue
            if atr_percent > self.max_atr_percent:
                logger.debug(f"{symbol}: ATR {atr_percent:.2f}% too high")
                continue
            
            # Passed all filters
            filtered.append(stock)
        
        return filtered
    
    def calculate_stock_score(self, stock_data: Dict) -> float:
        """
        Calculate OHL-optimized score.
        
        Prioritizes:
        - Stocks with clear gaps (better trend indication)
        - High opening volume (institutional interest)
        - Moderate volatility (tradeable)
        """
        scores = {}
        
        # 1. Gap Score (35%)
        gap_percent = abs(self._calculate_gap_percent(stock_data))
        if gap_percent < self.min_gap_percent:
            scores['gap'] = 20  # Low gap = low score
        elif gap_percent < self.ideal_gap_percent:
            # Scale from 20 to 80 as gap increases
            scores['gap'] = 20 + (gap_percent / self.ideal_gap_percent) * 60
        elif gap_percent < 2.0:
            scores['gap'] = 80 + (gap_percent - 1.0) * 20  # 80-100
        else:
            # Beyond 2%, start reducing (too extreme)
            scores['gap'] = max(60, 100 - (gap_percent - 2.0) * 20)
        
        # 2. Volume Score (30%)
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < 1.0:
            scores['volume'] = volume_ratio * 50  # 0-50
        elif volume_ratio < 1.5:
            scores['volume'] = 50 + (volume_ratio - 1.0) * 40  # 50-70
        elif volume_ratio < 2.5:
            scores['volume'] = 70 + (volume_ratio - 1.5) * 30  # 70-100
        else:
            scores['volume'] = 100
        
        # 3. Volatility Score (20%)
        atr_percent = self._calculate_atr_percent(stock_data)
        if atr_percent < 1.5:
            scores['volatility'] = 30 + (atr_percent / 1.5) * 30  # 30-60
        elif atr_percent < 3.0:
            scores['volatility'] = 60 + ((atr_percent - 1.5) / 1.5) * 40  # 60-100
        else:
            scores['volatility'] = max(50, 100 - (atr_percent - 3.0) * 20)
        
        # 4. Trend Score (15%) - Previous day trend clarity
        scores['trend'] = self._calculate_trend_score(stock_data)
        
        # Weighted average
        total = sum(
            scores.get(k, 50) * self.weights[k]
            for k in self.weights
        )
        
        return total
    
    def _calculate_gap_percent(self, stock_data: Dict) -> float:
        """Calculate gap from previous close as percentage"""
        today_open = stock_data.get('open', stock_data.get('ltp', 0))
        prev_close = stock_data.get('prev_close', stock_data.get('close', today_open))
        
        if prev_close <= 0:
            return 0.0
        
        return ((today_open - prev_close) / prev_close) * 100
    
    def _calculate_atr_percent(self, stock_data: Dict) -> float:
        """Calculate ATR as percentage of price"""
        atr = stock_data.get('atr', 0)
        price = stock_data.get('price', stock_data.get('close', stock_data.get('ltp', 0)))
        
        if price <= 0 or atr <= 0:
            return 2.0  # Default to mid-range
        
        return (atr / price) * 100
    
    def _calculate_trend_score(self, stock_data: Dict) -> float:
        """
        Calculate previous day trend clarity score.
        
        Clearer previous day trend = better OHL setup
        """
        # If we have previous day OHLC, use it
        prev_high = stock_data.get('prev_high', 0)
        prev_low = stock_data.get('prev_low', 0)
        prev_close = stock_data.get('prev_close', 0)
        prev_open = stock_data.get('prev_open', prev_close)
        
        if prev_high <= 0 or prev_low <= 0 or prev_close <= 0:
            return 50  # Neutral if no data
        
        # Calculate previous day body vs range ratio
        body = abs(prev_close - prev_open)
        total_range = prev_high - prev_low
        
        if total_range <= 0:
            return 50
        
        body_ratio = body / total_range
        
        # Higher body ratio = clearer trend = better score
        return 30 + (body_ratio * 70)  # 30-100
    
    def detect_ohl_candidates(self, stocks: List[Dict], buffer_percent: float = 0.06) -> Dict[str, List[Dict]]:
        """
        Detect stocks with O=H or O=L pattern.
        
        This can be called after market opens (9:16+) to identify
        candidates for the OHL strategy.
        
        Args:
            stocks: List of stock data with today's OHLC
            buffer_percent: Tolerance for O=H/L matching (default 0.06%)
            
        Returns:
            Dict with 'bullish' (O=L) and 'bearish' (O=H) candidates
        """
        bullish = []  # Open = Low (price only went up from open)
        bearish = []  # Open = High (price only went down from open)
        
        for stock in stocks:
            symbol = stock.get('symbol', 'UNKNOWN')
            open_price = stock.get('open', 0)
            high_price = stock.get('high', 0)
            low_price = stock.get('low', 0)
            
            if open_price <= 0:
                continue
            
            buffer = open_price * (buffer_percent / 100)
            
            # Check O=H (bearish)
            if abs(open_price - high_price) <= buffer:
                stock['ohl_signal'] = 'BEARISH'
                stock['ohl_buffer_used'] = abs(open_price - high_price) / open_price * 100
                bearish.append(stock)
                logger.debug(f"{symbol}: O=H detected (bearish)")
            
            # Check O=L (bullish)
            elif abs(open_price - low_price) <= buffer:
                stock['ohl_signal'] = 'BULLISH'
                stock['ohl_buffer_used'] = abs(open_price - low_price) / open_price * 100
                bullish.append(stock)
                logger.debug(f"{symbol}: O=L detected (bullish)")
        
        return {
            'bullish': bullish,
            'bearish': bearish
        }
    
    def get_required_indicators(self) -> List[str]:
        """OHL needs specific data fields"""
        return ['atr', 'volume_ratio']
    
    def get_required_data_fields(self) -> List[str]:
        """OHL needs opening data + previous day close"""
        return [
            'symbol', 'token', 'price', 
            'open', 'high', 'low', 'close',
            'prev_close', 'prev_open', 'prev_high', 'prev_low',
            'volume'
        ]


# Register the picker
StockPickerRegistry.register('ohl', OHLStockPicker())
