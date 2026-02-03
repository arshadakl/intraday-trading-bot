"""Pre-Open Gap Stock Picker - Stock selection for 3-Minute Strategy

This stock picker is specifically designed for the "3 Minute Strategy" which:
1. Fetches pre-open market data from NSE between 9:00-9:08 AM
2. Identifies stocks with significant gap-up (bullish) or gap-down (bearish) openings
3. Selects the best candidates based on gap size, volume, and other factors
4. Monitors for confirmation signals (candle breakout) after market opens

The picker is different from other pickers because it:
- Sources data from NSE pre-open API (not broker historical data)
- Prioritizes gap percentage as the primary selection criterion
- Works in two phases: Pre-open (stock picking) and Post-open (confirmation)
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from src.analysis.base_stock_picker import BaseStockPicker, StockPickerRegistry
from src.analysis.nse_preopen_fetcher import get_nse_preopen_fetcher, NSEPreOpenFetcher


class PreOpenGapPicker(BaseStockPicker):
    """
    Stock picker for the 3-Minute Strategy based on pre-open gap analysis.
    
    This picker identifies stocks with significant gaps from previous close
    during the pre-open session (9:00-9:08 AM IST).
    
    Selection Criteria:
    1. Gap Size: Primary factor - stocks with 1%+ gap are prioritized
    2. Volume: Higher pre-open volume indicates stronger conviction
    3. Price Range: Standard price range for position sizing (100-5000)
    4. Gap Type: Separates bullish (gap up) vs bearish (gap down) candidates
    
    Scoring weights favor stocks with:
    - Clear, significant gaps (not marginal)
    - High pre-open volume (institutional participation)
    - Price within tradeable range
    """
    
    def __init__(self):
        super().__init__("preopen_gap")
        
        # NSE Pre-Open Fetcher
        self.fetcher: Optional[NSEPreOpenFetcher] = None
        
        # Scoring weights
        self.weights = {
            'gap': 0.50,        # Gap size is primary factor
            'volume': 0.30,     # Volume confirms conviction
            'price_range': 0.10,  # Price within ideal range
            'gap_consistency': 0.10  # Gap direction consistent with volume
        }
        
        # Filters
        self.min_price = 100
        self.max_price = 5000
        self.min_gap_percent = 0.5      # Minimum gap to consider
        self.ideal_gap_percent = 2.0    # Ideal gap for scoring
        self.max_gap_percent = 8.0      # Avoid extreme gaps (possible news/events)
        self.min_volume = 10000         # Minimum pre-open volume
        
        # Selected stocks per type
        self.bullish_candidates: List[Dict] = []  # Gap up stocks
        self.bearish_candidates: List[Dict] = []  # Gap down stocks
        
    def _ensure_fetcher(self) -> NSEPreOpenFetcher:
        """Ensure the NSE fetcher is initialized."""
        if self.fetcher is None:
            self.fetcher = get_nse_preopen_fetcher(segment='nifty')
        return self.fetcher
    
    def get_scoring_weights(self) -> Dict[str, float]:
        return self.weights.copy()
    
    def filter_stocks(self, stocks: List[Dict]) -> List[Dict]:
        """
        Filter stocks suitable for 3-minute strategy.
        
        Filters applied:
        1. Price range (100-5000)
        2. Minimum gap (0.5%)
        3. Maximum gap (8% - avoid circuit limits)
        4. Minimum volume (10,000)
        """
        filtered = []
        
        for stock in stocks:
            symbol = stock.get('symbol', 'UNKNOWN')
            
            # Price filter (use IEP - Indicative Equilibrium Price)
            price = stock.get('iep', stock.get('last_price', 0))
            if not (self.min_price <= price <= self.max_price):
                logger.debug(f"{symbol}: Price {price} out of range")
                continue
            
            # Gap filter
            gap_percent = abs(stock.get('gap_percent', 0))
            if gap_percent < self.min_gap_percent:
                logger.debug(f"{symbol}: Gap {gap_percent:.2f}% too small")
                continue
            if gap_percent > self.max_gap_percent:
                logger.debug(f"{symbol}: Gap {gap_percent:.2f}% too extreme")
                continue
            
            # Volume filter
            volume = stock.get('volume', 0)
            if volume < self.min_volume:
                logger.debug(f"{symbol}: Volume {volume} too low")
                continue
            
            # Passed all filters
            filtered.append(stock)
        
        return filtered
    
    def calculate_stock_score(self, stock_data: Dict) -> float:
        """
        Calculate pre-open gap score for a stock.
        
        Prioritizes:
        - Significant gaps (>1%) - strong market sentiment
        - High pre-open volume (institutional participation)
        - Price within ideal trading range
        """
        scores = {}
        
        # 1. Gap Score (50%) - Primary factor
        gap_percent = abs(stock_data.get('gap_percent', 0))
        
        if gap_percent < 0.5:
            scores['gap'] = 20  # Marginal gap
        elif gap_percent < 1.0:
            # Scale 20-50 for 0.5-1.0% gaps
            scores['gap'] = 20 + ((gap_percent - 0.5) / 0.5) * 30
        elif gap_percent < self.ideal_gap_percent:
            # Scale 50-80 for 1.0-2.0% gaps
            scores['gap'] = 50 + ((gap_percent - 1.0) / 1.0) * 30
        elif gap_percent < 4.0:
            # Scale 80-100 for 2.0-4.0% gaps (ideal range)
            scores['gap'] = 80 + ((gap_percent - 2.0) / 2.0) * 20
        else:
            # Beyond 4%, start reducing (too extreme)
            scores['gap'] = max(60, 100 - (gap_percent - 4.0) * 10)
        
        # 2. Volume Score (30%)
        volume = stock_data.get('volume', 0)
        
        if volume < 10000:
            scores['volume'] = 20
        elif volume < 50000:
            scores['volume'] = 20 + ((volume - 10000) / 40000) * 30
        elif volume < 200000:
            scores['volume'] = 50 + ((volume - 50000) / 150000) * 30
        elif volume < 500000:
            scores['volume'] = 80 + ((volume - 200000) / 300000) * 15
        else:
            scores['volume'] = 95 + min(5, (volume - 500000) / 500000 * 5)
        
        # 3. Price Range Score (10%) - Prefer mid-range prices
        price = stock_data.get('iep', stock_data.get('last_price', 0))
        
        if price < 200:
            scores['price_range'] = 40  # Too cheap
        elif price < 500:
            scores['price_range'] = 60
        elif price < 1500:
            scores['price_range'] = 90  # Ideal range
        elif price < 3000:
            scores['price_range'] = 75
        else:
            scores['price_range'] = 50  # Too expensive
        
        # 4. Gap Consistency Score (10%)
        # Does the gap direction match volume activity?
        gap = stock_data.get('gap_percent', 0)
        final_quantity = stock_data.get('final_quantity', 0)
        
        # Simple consistency check
        if (gap > 0 and final_quantity > 0) or (gap < 0 and final_quantity >= 0):
            scores['gap_consistency'] = 80
        else:
            scores['gap_consistency'] = 50
        
        # Weighted average
        total = sum(
            scores.get(k, 50) * self.weights[k]
            for k in self.weights
        )
        
        return total
    
    def fetch_and_select_candidates(
        self, 
        max_stocks: int = 5, 
        min_gap: float = 1.0,
        force_refresh: bool = False,
        wait_for_data: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Fetch pre-open data and select gap candidates.
        
        This is the main method to call for stock selection.
        
        IMPORTANT: The final pre-open data is available after 9:10 AM.
        If called before 9:10 AM, this method will wait until 9:10 AM
        to ensure the fetched data is final and stable.
        
        Args:
            max_stocks: Maximum stocks to select per direction (up/down)
            min_gap: Minimum gap percentage to consider
            force_refresh: Force fresh data fetch
            wait_for_data: If True, wait until 9:10 AM for final data
            
        Returns:
            Dict with 'bullish' (gap up) and 'bearish' (gap down) candidates
        """
        fetcher = self._ensure_fetcher()
        
        # Check if data is final (after 9:10 AM)
        if wait_for_data and not fetcher.is_preopen_data_final():
            logger.info("📊 Pre-open data not yet final. Waiting until 9:10 AM...")
            fetcher.wait_for_final_data()
        
        # Fetch final pre-open data (this ensures we get the stable IEP values)
        preopen_data = fetcher.fetch_final_preopen_data(wait_if_not_ready=False)
        
        if not preopen_data:
            logger.warning("No pre-open data available")
            return {'bullish': [], 'bearish': []}
        
        logger.info(f"Processing {len(preopen_data)} stocks from final pre-open data")
        
        # Auto-update Nifty 50 config with latest stocks from pre-open data
        try:
            from src.utils.nifty50_updater import update_from_preopen_data
            update_from_preopen_data(preopen_data)
        except Exception as e:
            logger.warning(f"⚠️ Could not auto-update Nifty 50 list: {e}")
        
        # Update min gap filter
        self.min_gap_percent = min_gap
        
        # Separate by gap direction
        gap_up_stocks = [s for s in preopen_data if s.get('gap_percent', 0) >= min_gap]
        gap_down_stocks = [s for s in preopen_data if s.get('gap_percent', 0) <= -min_gap]
        
        # Apply filters
        filtered_gap_up = self.filter_stocks(gap_up_stocks)
        filtered_gap_down = self.filter_stocks(gap_down_stocks)
        
        # Score and select top stocks
        bullish = self.select_top_stocks(filtered_gap_up, max_stocks)
        bearish = self.select_top_stocks(filtered_gap_down, max_stocks)
        
        # Store for later access
        self.bullish_candidates = bullish
        self.bearish_candidates = bearish
        
        # Log summary
        if bullish:
            logger.info(f"📈 Gap UP Candidates: {[s['symbol'] for s in bullish]}")
            for s in bullish:
                logger.info(
                    f"   {s['symbol']}: Gap +{s['gap_percent']:.2f}%, "
                    f"IEP=₹{s.get('iep', 0):.2f}, Vol={s.get('volume', 0):,}"
                )
        
        if bearish:
            logger.info(f"📉 Gap DOWN Candidates: {[s['symbol'] for s in bearish]}")
            for s in bearish:
                logger.info(
                    f"   {s['symbol']}: Gap {s['gap_percent']:.2f}%, "
                    f"IEP=₹{s.get('iep', 0):.2f}, Vol={s.get('volume', 0):,}"
                )
        
        if not bullish and not bearish:
            logger.info("⚠️ No gap candidates found matching criteria")
        
        return {
            'bullish': bullish,
            'bearish': bearish
        }
    
    def get_watchlist(self) -> List[Dict]:
        """
        Get combined watchlist of all gap candidates for monitoring.
        
        Returns:
            List of all candidates (bullish + bearish) with signal type
        """
        watchlist = []
        
        for stock in self.bullish_candidates:
            stock_copy = stock.copy()
            stock_copy['signal_type'] = 'BULLISH'
            stock_copy['trade_direction'] = 'LONG'
            watchlist.append(stock_copy)
        
        for stock in self.bearish_candidates:
            stock_copy = stock.copy()
            stock_copy['signal_type'] = 'BEARISH'
            stock_copy['trade_direction'] = 'SHORT'
            watchlist.append(stock_copy)
        
        return watchlist
    
    def map_to_broker_format(self, nifty50_stocks: List[Dict]) -> List[Dict]:
        """
        Map pre-open candidates to broker format with token info.
        
        The pre-open data has symbol only. This maps to the full stock
        data needed for trading (token, symbol-EQ format, etc.)
        
        Args:
            nifty50_stocks: List of Nifty 50 stocks with tokens from config
            
        Returns:
            List of candidates mapped to broker format
        """
        # Create symbol lookup from Nifty 50 config
        symbol_lookup = {
            stock['symbol'].replace('-EQ', '').upper(): stock
            for stock in nifty50_stocks
        }
        
        mapped_watchlist = []
        
        for candidate in self.get_watchlist():
            symbol = candidate['symbol'].upper()
            
            if symbol in symbol_lookup:
                broker_stock = symbol_lookup[symbol]
                
                # Merge pre-open data with broker stock info
                mapped_stock = {
                    # From broker config
                    'symbol': broker_stock['symbol'],
                    'token': broker_stock['token'],
                    'name': broker_stock.get('name', symbol),
                    
                    # From pre-open data
                    'iep': candidate.get('iep', 0),
                    'prev_close': candidate.get('prev_close', 0),
                    'gap_percent': candidate.get('gap_percent', 0),
                    'gap_type': candidate.get('gap_type', 'NEUTRAL'),
                    'preopen_volume': candidate.get('volume', 0),
                    
                    # Trading direction
                    'signal_type': candidate.get('signal_type', 'NEUTRAL'),
                    'trade_direction': candidate.get('trade_direction', 'LONG'),
                    'picker_score': candidate.get('picker_score', 0),
                    
                    # Status
                    'status': 'WATCHING',
                    'source': 'preopen_gap'
                }
                
                mapped_watchlist.append(mapped_stock)
                logger.debug(f"Mapped {symbol} -> {broker_stock['symbol']} (token: {broker_stock['token']})")
            else:
                logger.warning(f"Symbol {symbol} not found in Nifty 50 config")
        
        return mapped_watchlist
    
    def get_required_indicators(self) -> List[str]:
        """Pre-open gap picker needs minimal indicators - primarily uses gap data."""
        return ['atr', 'open', 'high', 'low', 'close']
    
    def get_required_data_fields(self) -> List[str]:
        """Required fields for the strategy."""
        return [
            'symbol', 'token', 'iep', 'prev_close', 
            'gap_percent', 'gap_type', 'preopen_volume'
        ]
    
    def get_status(self) -> Dict:
        """Get current picker status."""
        return {
            'picker': self.name,
            'bullish_count': len(self.bullish_candidates),
            'bearish_count': len(self.bearish_candidates),
            'bullish_symbols': [s['symbol'] for s in self.bullish_candidates],
            'bearish_symbols': [s['symbol'] for s in self.bearish_candidates],
            'filters': {
                'min_gap': self.min_gap_percent,
                'max_gap': self.max_gap_percent,
                'min_volume': self.min_volume,
                'price_range': f"{self.min_price}-{self.max_price}"
            }
        }


# Register the picker
StockPickerRegistry.register('preopen_gap', PreOpenGapPicker())
