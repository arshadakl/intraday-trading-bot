"""
Technical Indicators Module
Uses 'ta' library for calculations (easy to install, no C compilation)
"""

import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from ta.trend import SMAIndicator, EMAIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger


class TechnicalIndicators:
    """
    Calculate technical indicators for stock analysis.
    All methods accept pandas Series or DataFrame.
    """
    
    @staticmethod
    def calculate_rsi(
        close_prices: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        RSI measures momentum on a scale of 0-100.
        - RSI < 30: Oversold (potential buy)
        - RSI > 70: Overbought (potential sell)
        - RSI 40-60: Neutral zone (our entry zone)
        
        Args:
            close_prices: Series of closing prices
            period: RSI period (default 14)
            
        Returns:
            Series of RSI values
        """
        try:
            rsi_indicator = RSIIndicator(close=close_prices, window=period)
            return rsi_indicator.rsi()
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series([50] * len(close_prices))  # Return neutral RSI on error
    
    @staticmethod
    def calculate_vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP).
        
        VWAP is the average price weighted by volume.
        - Price > VWAP: Bullish (buyers in control)
        - Price < VWAP: Bearish (sellers in control)
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            volume: Series of volume
            
        Returns:
            Series of VWAP values
        """
        try:
            vwap_indicator = VolumeWeightedAveragePrice(
                high=high,
                low=low,
                close=close,
                volume=volume
            )
            return vwap_indicator.volume_weighted_average_price()
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return close  # Return close price as fallback
    
    @staticmethod
    def calculate_vwap_manual(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        Calculate VWAP manually (alternative method).
        
        Formula: VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
        Typical Price = (High + Low + Close) / 3
        """
        try:
            typical_price = (high + low + close) / 3
            vwap = (typical_price * volume).cumsum() / volume.cumsum()
            return vwap
        except Exception as e:
            logger.error(f"Error calculating manual VWAP: {e}")
            return close
    
    @staticmethod
    def calculate_sma(
        prices: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            prices: Series of prices
            period: SMA period (default 20)
            
        Returns:
            Series of SMA values
        """
        try:
            sma_indicator = SMAIndicator(close=prices, window=period)
            return sma_indicator.sma_indicator()
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(
        prices: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).
        
        EMA gives more weight to recent prices.
        
        Args:
            prices: Series of prices
            period: EMA period (default 20)
            
        Returns:
            Series of EMA values
        """
        try:
            ema_indicator = EMAIndicator(close=prices, window=period)
            return ema_indicator.ema_indicator()
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        ATR measures volatility.
        Higher ATR = More volatile (good for intraday)
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            period: ATR period (default 14)
            
        Returns:
            Series of ATR values
        """
        try:
            atr_indicator = AverageTrueRange(
                high=high,
                low=low,
                close=close,
                window=period
            )
            return atr_indicator.average_true_range()
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            # Manual calculation as fallback
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=period).mean()
    
    @staticmethod
    def calculate_volume_ratio(
        volume: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Calculate Volume Ratio (current volume vs average).
        
        Ratio > 1: Above average volume (confirms momentum)
        Ratio < 1: Below average volume (weak momentum)
        
        Args:
            volume: Series of volume values
            period: Period for average (default 20)
            
        Returns:
            Series of volume ratios
        """
        try:
            avg_volume = volume.rolling(window=period).mean()
            return volume / avg_volume
        except Exception as e:
            logger.error(f"Error calculating volume ratio: {e}")
            return pd.Series([1.0] * len(volume))
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators at once and add to DataFrame.
        
        Expects DataFrame with columns: open, high, low, close, volume
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        try:
            # Make a copy to avoid modifying original
            result = df.copy()
            
            # RSI
            result['rsi'] = TechnicalIndicators.calculate_rsi(result['close'])
            
            # VWAP
            result['vwap'] = TechnicalIndicators.calculate_vwap(
                result['high'],
                result['low'],
                result['close'],
                result['volume']
            )
            
            # Moving Averages
            result['sma_20'] = TechnicalIndicators.calculate_sma(result['close'], 20)
            result['ema_9'] = TechnicalIndicators.calculate_ema(result['close'], 9)
            result['ema_21'] = TechnicalIndicators.calculate_ema(result['close'], 21)
            
            # ATR (Volatility)
            result['atr'] = TechnicalIndicators.calculate_atr(
                result['high'],
                result['low'],
                result['close']
            )
            
            # Volume Ratio
            result['volume_ratio'] = TechnicalIndicators.calculate_volume_ratio(
                result['volume']
            )
            
            # Price vs VWAP (for signals)
            result['price_above_vwap'] = result['close'] > result['vwap']
            
            # Fill NaN values
            result = result.bfill().ffill()
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return df


class SignalGenerator:
    """
    Generate trading signals based on indicators.
    """
    
    def __init__(
        self,
        rsi_oversold: int = 40,
        rsi_overbought: int = 70,
        volume_threshold: float = 1.0
    ):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.volume_threshold = volume_threshold
    
    def check_buy_signal(
        self,
        current_price: float,
        vwap: float,
        rsi: float,
        volume_ratio: float,
        prev_price: float = None,
        prev_vwap: float = None
    ) -> bool:
        """
        Check if conditions are met for a BUY signal.
        
        Conditions (all must be true):
        1. Price crosses above VWAP
        2. RSI is between oversold and neutral (40-60)
        3. Volume is above average
        
        Args:
            current_price: Current stock price
            vwap: Current VWAP value
            rsi: Current RSI value
            volume_ratio: Current volume vs average
            prev_price: Previous price (for crossover detection)
            prev_vwap: Previous VWAP (for crossover detection)
            
        Returns:
            True if buy signal, False otherwise
        """
        # Condition 1: Price above VWAP
        price_above_vwap = current_price > vwap
        
        # Condition 1b: Price crossed above VWAP (if previous data available)
        if prev_price is not None and prev_vwap is not None:
            was_below_vwap = prev_price <= prev_vwap
            crossover = price_above_vwap and was_below_vwap
        else:
            crossover = price_above_vwap
        
        # Condition 2: RSI in favorable zone (not overbought)
        rsi_favorable = self.rsi_oversold <= rsi <= 60
        
        # Condition 3: Good volume
        good_volume = volume_ratio >= self.volume_threshold
        
        return crossover and rsi_favorable and good_volume
    
    def check_sell_signal(
        self,
        current_price: float,
        entry_price: float,
        stop_loss: float,
        target: float,
        rsi: float,
        vwap: float
    ) -> Optional[Dict]:
        """
        Check if conditions are met for a SELL signal.
        
        Exit Conditions (any triggers exit):
        1. Price hits target
        2. Price hits stop-loss
        3. RSI > 70 (overbought)
        4. Price crosses below VWAP
        
        Args:
            current_price: Current stock price
            entry_price: Entry price of position
            stop_loss: Stop-loss price
            target: Target price
            rsi: Current RSI value
            vwap: Current VWAP value
            
        Returns:
            Dict with exit reason if should exit, None otherwise
        """
        # Check target
        if current_price >= target:
            return {"action": "SELL", "reason": "TARGET"}
        
        # Check stop-loss
        if current_price <= stop_loss:
            return {"action": "SELL", "reason": "STOP_LOSS"}
        
        # Check RSI overbought
        if rsi >= self.rsi_overbought:
            return {"action": "SELL", "reason": "RSI_OVERBOUGHT"}
        
        # Check VWAP breakdown
        if current_price < vwap:
            # Only exit on VWAP breakdown if we have some profit
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            if pnl_percent > 0.3:  # At least 0.3% profit
                return {"action": "SELL", "reason": "VWAP_BREAKDOWN"}
        
        return None


# ============== Helper Functions ==============

def prepare_dataframe(candles: List[Dict]) -> pd.DataFrame:
    """
    Convert candle data from API to pandas DataFrame.
    
    Args:
        candles: List of candle dicts with timestamp, open, high, low, close, volume
        
    Returns:
        DataFrame with proper types and index
    """
    df = pd.DataFrame(candles)
    
    # Ensure column names are lowercase
    df.columns = df.columns.str.lower()
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    # Ensure numeric types
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def get_latest_indicators(df: pd.DataFrame) -> Dict:
    """
    Get the latest indicator values from a DataFrame.
    
    Args:
        df: DataFrame with calculated indicators
        
    Returns:
        Dict with latest values of all indicators
    """
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    return {
        "close": latest.get("close", 0),
        "rsi": latest.get("rsi", 50),
        "vwap": latest.get("vwap", latest.get("close", 0)),
        "sma_20": latest.get("sma_20", 0),
        "ema_9": latest.get("ema_9", 0),
        "ema_21": latest.get("ema_21", 0),
        "atr": latest.get("atr", 0),
        "volume_ratio": latest.get("volume_ratio", 1.0),
        "price_above_vwap": latest.get("price_above_vwap", False)
    }


# Backward compatibility aliases
class Indicators(TechnicalIndicators):
    """Alias for backward compatibility"""
    pass


def calculate_indicators_for_stock(df: pd.DataFrame) -> pd.DataFrame:
    """Alias for backward compatibility"""
    return TechnicalIndicators.calculate_all_indicators(df)

class LiveIndicatorManager:
    """
    Manages real-time indicator calculations using 1-minute candle aggregation.
    Ensures that indicators like RSI reflect meaningful price action rather than tick noise.
    Also tracks cumulative daily VWAP according to standard formulas.
    """
    
    def __init__(self, candle_interval_minutes: int = 1):
        self.candle_interval = candle_interval_minutes
        self.histories: Dict[str, pd.DataFrame] = {}
        self.current_candles: Dict[str, Dict] = {} # Tracking current partial candle
        self.vwap_stats: Dict[str, Dict] = {} # total_pv, total_volume for cumulative VWAP
    
    def update(self, symbol: str, price_data: Dict, historical_candles: Optional[pd.DataFrame] = None) -> Dict:
        """
        Update indicators with a new price tick.
        
        Args:
            symbol: Stock symbol
            price_data: Latest tick data (ltp, volume, open, high, low)
            historical_candles: Optional past 1-minute candles for initialization
            
        Returns:
            Dict of latest indicator values
        """
        from src.utils.timezone import now_ist
        now = now_ist()
        ltp = float(price_data.get('ltp', 0))
        volume = float(price_data.get('volume', 0))
        
        # 1. Initialize if needed
        if symbol not in self.histories:
            if historical_candles is not None:
                self.histories[symbol] = historical_candles.copy().tail(100)
            else:
                self.histories[symbol] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            self.vwap_stats[symbol] = {'total_pv': 0.0, 'total_volume': 0.0}
            self.current_candles[symbol] = self._reset_candle(ltp, now)
            self.current_candles[symbol]['last_total_volume'] = volume # Baseline immediately
    
    def is_candle_closed(self, symbol: str) -> bool:
        """
        Check if current 1-minute candle has closed.
        
        Returns True in the last 2 seconds of each minute to signal
        that the candle is complete and ready for analysis.
        
        Edge cases handled:
        - Second rollover (59→0)
        - Symbol not initialized
        """
        if symbol not in self.current_candles:
            return False
        
        from src.utils.timezone import now_ist
        now = now_ist()
        
        # Close candle in last 2 seconds of minute
        candle_close_buffer = 2
        return now.second >= (60 - candle_close_buffer)
    
    def get_closed_candle_data(self, symbol: str) -> Optional[Dict]:
        """
        Get complete candle data only when candle has closed.
        
        This is critical for professional trading - we wait for candle
        confirmation before generating signals, not trade on tick noise.
        
        Returns:
            Dict with OHLCV data if candle is closed, None otherwise
        """
        if not self.is_candle_closed(symbol):
            return None
        
        current = self.current_candles.get(symbol)
        if not current:
            return None
        
        return {
            'open': current['open'],
            'high': current['high'],
            'low': current['low'],
            'close': current['close'],
            'volume': current['volume'],
            'timestamp': current['timestamp'],
            'is_closed': True
        }

        # 2. Cumulative VWAP Update (Standard Intraday Formula)
        # Cumulative VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        # For ticks, we use ltp * tick_volume. If tick_volume isn't available, we use cumulative volume changes.
        stats = self.vwap_stats[symbol]
        last_vol = self.current_candles[symbol]['last_total_volume']
        tick_vol = max(0, volume - last_vol) if last_vol > 0 else 0
        
        # Update cumulative totals
        stats['total_pv'] += ltp * tick_vol
        stats['total_volume'] += tick_vol
        cumulative_vwap = stats['total_pv'] / stats['total_volume'] if stats['total_volume'] > 0 else ltp

        # 3. Candle Aggregation (1-minute)
        current = self.current_candles[symbol]
        candle_minute = now.replace(second=0, microsecond=0)
        
        if candle_minute > current['timestamp']:
            # Time to close the current candle and start a new one
            new_row = pd.DataFrame([{
                'open': current['open'],
                'high': current['high'],
                'low': current['low'],
                'close': current['close'],
                'volume': current['volume']
            }], index=[current['timestamp']])
            
            self.histories[symbol] = pd.concat([self.histories[symbol], new_row]).tail(100)
            
            # Reset for new minute
            self.current_candles[symbol] = self._reset_candle(ltp, candle_minute)
            self.current_candles[symbol]['volume'] = tick_vol
        else:
            # Update existing partial candle
            current['high'] = max(current['high'], ltp)
            current['low'] = min(current['low'], ltp)
            current['close'] = ltp
            current['volume'] += tick_vol
        
        current['last_total_volume'] = volume

        # 4. Indicators Calculation
        # We combine completed history with the current live partial candle for the absolute latest indicators
        history = self.histories[symbol]
        if len(history) < 2: # Not enough data yet
            return {
                "close": ltp,
                "rsi": 50,
                "vwap": cumulative_vwap,
                "atr": 0,
                "volume_ratio": 1.0
            }
            
        # Create a temp DF including the current partial candle for RSI/SMA calculation
        live_df = pd.concat([history, pd.DataFrame([{
            'open': current['open'],
            'high': current['high'],
            'low': current['low'],
            'close': current['close'],
            'volume': current['volume']
        }], index=[current['timestamp']])])
        
        calculated = TechnicalIndicators.calculate_all_indicators(live_df)
        latest = get_latest_indicators(calculated)
        
        # Override rolling VWAP with our Cumulative Daily VWAP
        latest['vwap'] = cumulative_vwap
        
        # Add candle data for professional signal confirmation
        latest['candle_data'] = self.get_closed_candle_data(symbol)
        
        return latest

    def _reset_candle(self, price: float, timestamp: datetime) -> Dict:
        """Initialize or reset a candle record"""
        return {
            'timestamp': timestamp.replace(second=0, microsecond=0),
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0,
            'last_total_volume': 0 # Used to track volume increments
        }
