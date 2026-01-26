"""Pre-Market Analyzer - Analyzes stocks before market opens and selects best candidates"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from .indicators import TechnicalIndicators, prepare_dataframe, get_latest_indicators
from .stock_scorer import StockScorer
from src.core.config_manager import get_config


class PreMarketAnalyzer:
    """
    Runs before market opens (8:30 AM).
    Analyzes all Nifty 50 stocks and selects top candidates for trading.
    """
    
    def __init__(self, broker=None):
        """
        Initialize Pre-Market Analyzer.
        
        Args:
            broker: AngelOneClient instance for fetching data (optional for testing)
        """
        self.broker = broker
        self.config = get_config()
        self.indicators = TechnicalIndicators()
        self.scorer = StockScorer()
        
        # Load Nifty 50 stock list
        self.stocks = self._load_nifty50()
        
        # Analysis results
        self.analyzed_stocks: List[Dict] = []
        self.selected_stocks: List[Dict] = []
    
    def _load_nifty50(self) -> List[Dict]:
        """Load Nifty 50 stock list from config file"""
        nifty50_path = Path("config/nifty50.json")
        
        if not nifty50_path.exists():
            logger.error("❌ Nifty 50 config file not found!")
            return []
        
        try:
            with open(nifty50_path, 'r') as f:
                data = json.load(f)
                return data.get('stocks', [])
        except Exception as e:
            logger.error(f"❌ Error loading Nifty 50 config: {e}")
            return []
    
    def analyze_stock(self, symbol: str, token: str) -> Optional[Dict]:
        """
        Analyze a single stock using historical data and indicators.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE-EQ")
            token: Stock token for API calls
            
        Returns:
            Dict with analysis results or None if failed
        """
        try:
            if not self.broker:
                logger.warning(f"⚠️ No broker connection for {symbol}")
                return None
            
            # Fetch historical data (last 5 days, 15-minute candles)
            historical_data = self.broker.get_historical_data(
                symbol=symbol,
                token=token,
                interval="FIFTEEN_MINUTE",
                days=5
            )
            
            if not historical_data or len(historical_data) < 20:
                logger.warning(f"⚠️ Insufficient data for {symbol}")
                return None
            
            # Convert to DataFrame
            df = prepare_dataframe(historical_data)
            
            # Calculate all indicators using the ta library
            df = TechnicalIndicators.calculate_all_indicators(df)
            
            # Get the latest indicator values
            latest = get_latest_indicators(df)
            
            # Prepare data for scoring
            stock_data = {
                'symbol': symbol,
                'token': token,
                'close': float(latest.get('close', 0)),
                'rsi': float(latest.get('rsi', 50)),
                'vwap': float(latest.get('vwap', latest.get('close', 0))),
                'sma_20': float(latest.get('sma_20', 0)),
                'ema_9': float(latest.get('ema_9', 0)),
                'ema_21': float(latest.get('ema_21', 0)),
                'atr': float(latest.get('atr', 0)),
                'volume_ratio': float(latest.get('volume_ratio', 1))
            }
            
            logger.debug(f"📊 Analyzed {symbol}: RSI={stock_data['rsi']:.1f}, ATR={stock_data['atr']:.2f}")
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    def analyze_all_stocks(self) -> List[Dict]:
        """
        Analyze all Nifty 50 stocks with rate limiting to avoid API throttling.
        
        Returns:
            List of analyzed stock data
        """
        import time
        
        logger.info("📊 Starting pre-market analysis...")
        logger.info(f"📋 Analyzing {len(self.stocks)} stocks")
        logger.info("⏱️ Rate limiting enabled (400ms delay between requests)")
        
        self.analyzed_stocks = []
        
        # Apply filters from config
        min_price = self.config.get('stock_selection.min_price', 100)
        max_price = self.config.get('stock_selection.max_price', 5000)
        
        # Rate limiting settings
        request_delay = 0.4  # 400ms delay between requests
        retry_delay = 2.0    # 2 second delay on rate limit error
        max_retries = 2      # Max retries for rate-limited requests
        
        total_stocks = len(self.stocks)
        analyzed_count = 0
        skipped_count = 0
        
        for i, stock in enumerate(self.stocks, 1):
            symbol = stock['symbol']
            token = stock['token']
            
            logger.info(f"  [{i}/{total_stocks}] Analyzing {symbol}...")
            
            # Retry logic for rate limiting
            analysis = None
            for retry in range(max_retries + 1):
                analysis = self.analyze_stock(symbol, token)
                
                if analysis is not None:
                    break
                    
                # If failed and not last retry, wait longer before retrying
                if retry < max_retries:
                    logger.debug(f"  ↻ Retrying {symbol} after {retry_delay}s delay...")
                    time.sleep(retry_delay)
            
            if analysis:
                # Apply price filter
                if not (min_price <= analysis['close'] <= max_price):
                    logger.debug(f"  ⏭️ {symbol} filtered: price {analysis['close']} outside range")
                    skipped_count += 1
                    continue
                
                # Add stock name
                analysis['name'] = stock.get('name', symbol)
                
                self.analyzed_stocks.append(analysis)
                analyzed_count += 1
            else:
                skipped_count += 1
            
            # Rate limiting: wait between requests (except after last stock)
            if i < total_stocks:
                time.sleep(request_delay)
        
        logger.info(f"✅ Successfully analyzed {analyzed_count} stocks ({skipped_count} skipped)")
        return self.analyzed_stocks
    
    def select_top_stocks(self, n: int = None) -> List[Dict]:
        """
        Select top N stocks based on composite score.
        
        Args:
            n: Number of stocks to select (uses config if not provided)
            
        Returns:
            List of selected stocks with entry points calculated
        """
        if n is None:
            n = self.config.max_stocks
        
        if not self.analyzed_stocks:
            logger.warning("⚠️ No analyzed stocks. Run analyze_all_stocks() first.")
            return []
        
        # Get top stocks by score
        top_stocks = self.scorer.get_top_stocks(self.analyzed_stocks, n)
        
        # Calculate entry points for selected stocks
        self.selected_stocks = []
        
        for stock in top_stocks:
            entry_points = self._calculate_entry_points(stock)
            stock.update(entry_points)
            stock['status'] = 'WATCHING'  # Initial status
            self.selected_stocks.append(stock)
            
            logger.info(
                f"✅ Selected {stock['symbol']} | "
                f"Score: {stock['composite_score']:.1f} | "
                f"Entry: ₹{stock['entry_price']:.2f} | "
                f"Target: ₹{stock['target_price']:.2f} | "
                f"SL: ₹{stock['stop_loss']:.2f}"
            )
        
        return self.selected_stocks
    
    def _calculate_entry_points(self, stock: Dict) -> Dict:
        """
        Calculate entry, target, and stop-loss prices for a stock.
        
        Uses ATR for dynamic risk management if available.
        Reflects logic in VWAPRSIStrategy.
        
        Args:
            stock: Stock data dictionary
            
        Returns:
            Dict with entry_price, target_price, stop_loss
        """
        stop_loss_percent = self.config.stop_loss_percent
        target_percent = self.config.target_percent
        
        # Use VWAP or current price as entry reference
        entry_price = stock.get('vwap', stock['close'])
        atr = stock.get('atr', 0)
        
        if atr > 0:
            # Dynamic ATR-based risk management (Match Strategy)
            stop_loss = entry_price - (2.0 * atr)
            target_price = entry_price + (4.0 * atr)
        else:
            # Fallback to fixed percentage
            target_price = entry_price * (1 + target_percent / 100)
            stop_loss = entry_price * (1 - stop_loss_percent / 100)
        
        return {
            'entry_price': round(entry_price, 2),
            'target_price': round(target_price, 2),
            'stop_loss': round(stop_loss, 2),
            'target_percent': target_percent,
            'stop_loss_percent': stop_loss_percent
        }
    
    def get_selected_stocks(self) -> List[Dict]:
        """Get the list of selected stocks for today"""
        return self.selected_stocks
    
    def get_analysis_summary(self) -> Dict:
        """
        Get summary of pre-market analysis.
        
        Returns:
            Dict with analysis summary
        """
        from src.utils.timezone import now_ist
        return {
            'timestamp': now_ist().isoformat(),
            'total_stocks_analyzed': len(self.analyzed_stocks),
            'stocks_selected': len(self.selected_stocks),
            'selected_stocks': [
                {
                    'symbol': s['symbol'],
                    'name': s.get('name', s['symbol']),
                    'score': s['composite_score'],
                    'entry': s['entry_price'],
                    'target': s['target_price'],
                    'stop_loss': s['stop_loss'],
                    'rsi': s['rsi']
                }
                for s in self.selected_stocks
            ],
            'config': {
                'max_stocks': self.config.max_stocks,
                'stop_loss_percent': self.config.stop_loss_percent,
                'target_percent': self.config.target_percent
            }
        }
    
    def run_analysis(self) -> List[Dict]:
        """
        Run complete pre-market analysis workflow.
        
        1. Analyze all Nifty 50 stocks
        2. Score and rank stocks
        3. Select top N stocks
        4. Calculate entry points
        
        Returns:
            List of selected stocks
        """
        logger.info("=" * 50)
        logger.info("  PRE-MARKET ANALYSIS")
        logger.info("=" * 50)
        
        # Step 1: Analyze all stocks
        self.analyze_all_stocks()
        
        # Step 2 & 3: Score, rank and select top stocks
        selected = self.select_top_stocks()
        
        # Log summary
        summary = self.get_analysis_summary()
        logger.info(f"📊 Analysis complete at {summary['timestamp']}")
        logger.info(f"📋 Analyzed: {summary['total_stocks_analyzed']} stocks")
        logger.info(f"✅ Selected: {summary['stocks_selected']} stocks")
        
        return selected
