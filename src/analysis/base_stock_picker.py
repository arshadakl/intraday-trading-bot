"""Base Stock Picker - Abstract base class for stock selection strategies"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from loguru import logger


class BaseStockPicker(ABC):
    """
    Abstract base class for stock selection strategies.
    
    Each trading strategy may have different criteria for selecting
    stocks to trade. This class defines the interface that all
    stock pickers must implement.
    
    Examples:
    - Momentum Picker: High volume + clear trend (for VWAP/RSI)
    - OHL Picker: Gap detection + Open=High/Low patterns
    - Breakout Picker: Near resistance + tight consolidation
    """
    
    def __init__(self, name: str):
        """
        Initialize stock picker.
        
        Args:
            name: Picker name for identification
        """
        self.name = name
    
    @abstractmethod
    def get_scoring_weights(self) -> Dict[str, float]:
        """
        Return scoring weights for this picker.
        
        Weights should sum to 1.0 and define the importance
        of each factor in stock selection.
        
        Returns:
            Dict mapping factor names to weights
            Example: {'volatility': 0.25, 'volume': 0.25, 'trend': 0.25, 'momentum': 0.25}
        """
        pass
    
    @abstractmethod
    def calculate_stock_score(self, stock_data: Dict) -> float:
        """
        Calculate a score (0-100) for a stock.
        
        Higher scores indicate better candidates for trading
        with this picker's strategy.
        
        Args:
            stock_data: Dict with stock info and indicators
                - symbol: str
                - price: float
                - atr: float
                - rsi: float
                - volume_ratio: float
                - sma_20: float
                - ema_9: float
                - vwap: float (optional)
                - prev_close: float (optional)
                - open: float (optional)
                - high: float (optional)
                - low: float (optional)
        
        Returns:
            Score from 0 to 100
        """
        pass
    
    @abstractmethod
    def filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """
        Apply picker-specific filters to stock list.
        
        This is called before scoring to eliminate stocks
        that don't meet basic criteria for this strategy.
        
        Args:
            stocks: List of stock data dicts
        
        Returns:
            Filtered list of stocks
        """
        pass
    
    def select_top_stocks(self, stocks: List[Dict], n: int = 2) -> List[Dict]:
        """
        Select top N stocks based on this picker's criteria.
        
        Default implementation:
        1. Filter stocks using picker-specific filters
        2. Score each remaining stock
        3. Sort by score descending
        4. Return top N
        
        Args:
            stocks: List of stock data dicts
            n: Number of stocks to select
        
        Returns:
            Top N stocks sorted by score
        """
        # Step 1: Filter
        filtered = self.filter_stocks(stocks)
        logger.debug(f"{self.name}: {len(filtered)}/{len(stocks)} stocks passed filters")
        
        if not filtered:
            logger.warning(f"{self.name}: No stocks passed filters")
            return []
        
        # Step 2: Score
        scored = []
        for stock in filtered:
            try:
                score = self.calculate_stock_score(stock)
                scored.append({**stock, 'picker_score': score})
            except Exception as e:
                logger.warning(f"Error scoring {stock.get('symbol', 'UNKNOWN')}: {e}")
                continue
        
        # Step 3: Sort by score
        scored.sort(key=lambda x: x.get('picker_score', 0), reverse=True)
        
        # Step 4: Return top N
        top_stocks = scored[:n]
        
        if top_stocks:
            logger.info(
                f"{self.name}: Selected top {len(top_stocks)} stocks: "
                f"{[s['symbol'] + f' ({s.get(\"picker_score\", 0):.1f})' for s in top_stocks]}"
            )
        
        return top_stocks
    
    def get_required_indicators(self) -> List[str]:
        """
        Return list of indicators required by this picker.
        
        Override if picker needs specific indicators.
        Default: common set of indicators.
        
        Returns:
            List of indicator names
        """
        return ['rsi', 'atr', 'sma_20', 'ema_9', 'volume_ratio', 'vwap']
    
    def get_required_data_fields(self) -> List[str]:
        """
        Return list of data fields required by this picker.
        
        Override if picker needs specific OHLCV fields.
        
        Returns:
            List of field names
        """
        return ['symbol', 'token', 'price', 'open', 'high', 'low', 'close', 'volume']


class DefaultStockPicker(BaseStockPicker):
    """
    Default stock picker using balanced scoring.
    
    Used when no specific picker is configured.
    Scores based on volatility, volume, trend, and momentum equally.
    """
    
    def __init__(self):
        super().__init__("default")
        self.weights = {
            'volatility': 0.25,
            'volume': 0.25,
            'trend': 0.25,
            'momentum': 0.25
        }
        self.min_price = 100
        self.max_price = 5000
    
    def get_scoring_weights(self) -> Dict[str, float]:
        return self.weights.copy()
    
    def filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """Filter by price range"""
        filtered = []
        for stock in stocks:
            price = stock.get('price', stock.get('close', 0))
            if self.min_price <= price <= self.max_price:
                filtered.append(stock)
        return filtered
    
    def calculate_stock_score(self, stock_data: Dict) -> float:
        """Calculate balanced score"""
        scores = {}
        
        # Volatility score (ATR as % of price)
        price = stock_data.get('price', stock_data.get('close', 0))
        atr = stock_data.get('atr', 0)
        if price > 0 and atr > 0:
            atr_pct = (atr / price) * 100
            if atr_pct < 0.5:
                scores['volatility'] = atr_pct * 60
            elif atr_pct < 1.0:
                scores['volatility'] = 30 + (atr_pct - 0.5) * 60
            elif atr_pct < 3.0:
                scores['volatility'] = 60 + (atr_pct - 1.0) * 20
            else:
                scores['volatility'] = max(50, 100 - (atr_pct - 3.0) * 10)
        else:
            scores['volatility'] = 50
        
        # Volume score
        volume_ratio = stock_data.get('volume_ratio', 1.0)
        if volume_ratio < 0.5:
            scores['volume'] = volume_ratio * 60
        elif volume_ratio < 1.0:
            scores['volume'] = 30 + (volume_ratio - 0.5) * 40
        elif volume_ratio < 1.5:
            scores['volume'] = 50 + (volume_ratio - 1.0) * 40
        elif volume_ratio < 3.0:
            scores['volume'] = 70 + (volume_ratio - 1.5) * 13.33
        else:
            scores['volume'] = min(100, 90 + (volume_ratio - 3.0) * 2)
        
        # Trend score
        close = stock_data.get('close', price)
        sma_20 = stock_data.get('sma_20', close)
        ema_9 = stock_data.get('ema_9', close)
        if sma_20 > 0 and ema_9 > 0:
            price_vs_sma = (close - sma_20) / sma_20 * 100
            price_vs_ema = (close - ema_9) / ema_9 * 100
            if (price_vs_sma > 0 and price_vs_ema > 0) or \
               (price_vs_sma < 0 and price_vs_ema < 0):
                trend_strength = abs(price_vs_sma) + abs(price_vs_ema)
                scores['trend'] = min(100, 50 + trend_strength * 10)
            else:
                scores['trend'] = 30 + abs(price_vs_ema) * 5
        else:
            scores['trend'] = 50
        
        # Momentum score (RSI)
        rsi = stock_data.get('rsi', 50)
        if 40 <= rsi <= 60:
            distance_from_50 = abs(rsi - 50)
            scores['momentum'] = 100 - distance_from_50
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            distance = min(abs(rsi - 40), abs(rsi - 60))
            scores['momentum'] = 60 + distance * 2
        else:
            scores['momentum'] = 40
        
        # Weighted average
        total = sum(
            scores.get(k, 50) * self.weights[k]
            for k in self.weights
        )
        
        return total


class MomentumStockPicker(BaseStockPicker):
    """
    Momentum-focused stock picker for VWAP/RSI strategy.
    
    Prioritizes:
    - High volume (liquidity for quick trades)
    - Clear trend (momentum continuation)
    - Moderate volatility (enough movement, not extreme)
    """
    
    def __init__(self):
        super().__init__("momentum")
        self.weights = {
            'volume': 0.30,      # Volume most important
            'trend': 0.30,       # Clear trend for momentum
            'volatility': 0.25,  # Moderate volatility
            'momentum': 0.15     # RSI positioning
        }
        self.min_price = 100
        self.max_price = 5000
        self.min_volume_ratio = 1.0  # Require at least average volume
    
    def get_scoring_weights(self) -> Dict[str, float]:
        return self.weights.copy()
    
    def filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """Filter by price and minimum volume"""
        filtered = []
        for stock in stocks:
            price = stock.get('price', stock.get('close', 0))
            volume_ratio = stock.get('volume_ratio', 0)
            
            if not (self.min_price <= price <= self.max_price):
                continue
            
            if volume_ratio < self.min_volume_ratio:
                continue
            
            filtered.append(stock)
        
        return filtered
    
    def calculate_stock_score(self, stock_data: Dict) -> float:
        """Calculate momentum-weighted score"""
        # Use same scoring logic as DefaultStockPicker
        # but with momentum-focused weights
        default_picker = DefaultStockPicker()
        default_picker.weights = self.weights
        return default_picker.calculate_stock_score(stock_data)


# Registry for stock pickers
class StockPickerRegistry:
    """
    Registry for stock pickers.
    Similar to StrategyRegistry but for stock selection.
    """
    
    _pickers: Dict[str, BaseStockPicker] = {}
    
    @classmethod
    def register(cls, name: str, picker: BaseStockPicker) -> None:
        """Register a stock picker"""
        cls._pickers[name] = picker
        logger.debug(f"📝 Registered stock picker: {name}")
    
    @classmethod
    def get_picker(cls, name: str) -> BaseStockPicker:
        """Get a registered picker by name"""
        if name not in cls._pickers:
            logger.warning(f"Unknown picker '{name}', using default")
            return cls._pickers.get('default', DefaultStockPicker())
        return cls._pickers[name]
    
    @classmethod
    def list_pickers(cls) -> List[str]:
        """List all registered picker names"""
        return list(cls._pickers.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if picker is registered"""
        return name in cls._pickers


# Register default pickers
StockPickerRegistry.register('default', DefaultStockPicker())
StockPickerRegistry.register('momentum', MomentumStockPicker())
