"""Stock Scorer - Ranks stocks based on intraday trading potential"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger

from .indicators import TechnicalIndicators


class StockScorer:
    """
    Scores stocks for intraday trading potential.
    Uses multiple factors to create a composite score (0-100).
    """
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'volatility': 0.25,   # Higher ATR = better for intraday
            'volume': 0.25,       # Higher volume = better liquidity
            'trend': 0.25,        # Clear trend = better signals
            'momentum': 0.25      # RSI in favorable zone
        }
    
    def calculate_volatility_score(self, atr: float, price: float) -> float:
        """
        Score based on ATR as percentage of price.
        Higher volatility = higher score (good for intraday).
        
        Args:
            atr: Average True Range value
            price: Current stock price
            
        Returns:
            Score from 0-100
        """
        if price <= 0:
            return 0
            
        atr_percent = (atr / price) * 100
        
        # Ideal ATR% for intraday: 1-3%
        # < 0.5% = too low volatility (score: 0-30)
        # 0.5-1% = moderate (score: 30-60)
        # 1-3% = ideal (score: 60-100)
        # > 3% = too volatile (score decreases)
        
        if atr_percent < 0.5:
            return atr_percent * 60  # 0-30
        elif atr_percent < 1.0:
            return 30 + (atr_percent - 0.5) * 60  # 30-60
        elif atr_percent < 3.0:
            return 60 + (atr_percent - 1.0) * 20  # 60-100
        else:
            return max(50, 100 - (atr_percent - 3.0) * 10)  # Decreases after 3%
    
    def calculate_volume_score(self, volume_ratio: float) -> float:
        """
        Score based on volume compared to average.
        Higher volume = higher score (better liquidity).
        
        Args:
            volume_ratio: Current volume / Average volume
            
        Returns:
            Score from 0-100
        """
        if pd.isna(volume_ratio) or volume_ratio <= 0:
            return 50
            
        # Ideal volume ratio: > 1.5x average
        # < 0.5x = low volume (score: 0-30)
        # 0.5-1x = below average (score: 30-50)
        # 1-1.5x = average (score: 50-70)
        # 1.5-3x = good (score: 70-90)
        # > 3x = excellent (score: 90-100)
        
        if volume_ratio < 0.5:
            return volume_ratio * 60  # 0-30
        elif volume_ratio < 1.0:
            return 30 + (volume_ratio - 0.5) * 40  # 30-50
        elif volume_ratio < 1.5:
            return 50 + (volume_ratio - 1.0) * 40  # 50-70
        elif volume_ratio < 3.0:
            return 70 + (volume_ratio - 1.5) * 13.33  # 70-90
        else:
            return min(100, 90 + (volume_ratio - 3.0) * 2)  # 90-100
    
    def calculate_trend_score(self, close: float, sma_20: float, ema_9: float) -> float:
        """
        Score based on trend clarity.
        Clear uptrend or downtrend = higher score.
        
        Args:
            close: Current closing price
            sma_20: 20-period SMA
            ema_9: 9-period EMA
            
        Returns:
            Score from 0-100
        """
        if pd.isna(sma_20) or pd.isna(ema_9) or sma_20 <= 0 or ema_9 <= 0:
            return 50  # Neutral if no data
        
        # Calculate trend strength
        # Price above both MAs = uptrend
        # Price below both MAs = downtrend
        # Mixed = no clear trend
        
        price_vs_sma = (close - sma_20) / sma_20 * 100
        price_vs_ema = (close - ema_9) / ema_9 * 100
        
        # Both positive or both negative = clear trend
        if (price_vs_sma > 0 and price_vs_ema > 0) or \
           (price_vs_sma < 0 and price_vs_ema < 0):
            # Stronger deviation = clearer trend
            trend_strength = abs(price_vs_sma) + abs(price_vs_ema)
            return min(100, 50 + trend_strength * 10)
        else:
            # Mixed signals = lower score
            return 30 + abs(price_vs_ema) * 5
    
    def calculate_momentum_score(self, rsi: float) -> float:
        """
        Score based on RSI position.
        RSI in 40-60 zone (neutral) = best for entries.
        
        Args:
            rsi: Current RSI value (0-100)
            
        Returns:
            Score from 0-100
        """
        if pd.isna(rsi):
            return 50  # Neutral if no data
        
        # Ideal RSI for entries: 40-60 (not overbought/oversold)
        # 40-60 = ideal zone (score: 80-100)
        # 30-40 or 60-70 = acceptable (score: 60-80)
        # 20-30 or 70-80 = caution zone (score: 40-60)
        # < 20 or > 80 = extreme (score: 20-40)
        
        if 40 <= rsi <= 60:
            # Perfect zone - higher score for closer to 50
            distance_from_50 = abs(rsi - 50)
            return 100 - distance_from_50
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            return 70
        elif 20 <= rsi < 30 or 70 < rsi <= 80:
            return 50
        else:
            return 30
    
    def score_stock(self, data: Dict) -> Dict:
        """
        Calculate composite score for a stock.
        
        Args:
            data: Dict containing:
                - symbol: Stock symbol
                - close: Current/last close price
                - atr: Average True Range
                - volume_ratio: Current volume / Average volume
                - sma_20: 20-period SMA
                - ema_9: 9-period EMA
                - rsi: Current RSI
                
        Returns:
            Dict with individual scores and composite score
        """
        try:
            # Calculate individual scores
            volatility_score = self.calculate_volatility_score(
                data.get('atr', 0),
                data.get('close', 1)
            )
            volume_score = self.calculate_volume_score(
                data.get('volume_ratio', 1)
            )
            trend_score = self.calculate_trend_score(
                data.get('close', 0),
                data.get('sma_20', 0),
                data.get('ema_9', 0)
            )
            momentum_score = self.calculate_momentum_score(
                data.get('rsi', 50)
            )
            
            # Calculate weighted composite score
            composite_score = (
                volatility_score * self.weights['volatility'] +
                volume_score * self.weights['volume'] +
                trend_score * self.weights['trend'] +
                momentum_score * self.weights['momentum']
            )
            
            return {
                'symbol': data.get('symbol', 'UNKNOWN'),
                'token': data.get('token'),  # Essential for WebSocket subscription
                'name': data.get('name', data.get('symbol', 'UNKNOWN')),
                'close': data.get('close', 0),
                'ltp': data.get('ltp', data.get('close', 0)),  # Last traded price
                'vwap': data.get('vwap', data.get('close', 0)),
                'sma_20': data.get('sma_20', 0),
                'ema_9': data.get('ema_9', 0),
                'ema_21': data.get('ema_21', 0),
                'volatility_score': round(volatility_score, 2),
                'volume_score': round(volume_score, 2),
                'trend_score': round(trend_score, 2),
                'momentum_score': round(momentum_score, 2),
                'composite_score': round(composite_score, 2),
                'rsi': round(data.get('rsi', 50), 2),
                'atr': round(data.get('atr', 0), 2),
                'volume_ratio': round(data.get('volume_ratio', 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error scoring stock {data.get('symbol', 'UNKNOWN')}: {e}")
            return {
                'symbol': data.get('symbol', 'UNKNOWN'),
                'composite_score': 0,
                'error': str(e)
            }
    
    def rank_stocks(self, stocks_data: List[Dict]) -> List[Dict]:
        """
        Score and rank multiple stocks.
        
        Args:
            stocks_data: List of stock data dictionaries
            
        Returns:
            List of scored stocks, sorted by composite score (descending)
        """
        scored_stocks = []
        
        for stock_data in stocks_data:
            scored = self.score_stock(stock_data)
            scored_stocks.append(scored)
        
        # Sort by composite score (highest first)
        scored_stocks.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        # Add rank
        for i, stock in enumerate(scored_stocks):
            stock['rank'] = i + 1
        
        return scored_stocks
    
    def get_top_stocks(self, stocks_data: List[Dict], n: int = 2) -> List[Dict]:
        """
        Get top N stocks by score.
        
        Args:
            stocks_data: List of stock data dictionaries
            n: Number of top stocks to return
            
        Returns:
            List of top N scored stocks
        """
        ranked = self.rank_stocks(stocks_data)
        return ranked[:n]
