"""Daily Watchlist Manager for 3-Minute Strategy

This module manages the daily watchlist selection based on the 3-Minute Strategy.
It selects the Top 4 (Gap Up) and Bottom 4 (Gap Down) stocks from the Nifty 50 pre-open data.
It also handles the runtime filtering of these stocks based on the Nifty index trend at market open.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.utils.timezone import now_ist
from src.core.config_manager import get_config

logger = logging.getLogger(__name__)

class DailyWatchlistManager:
    """
    Manages the daily watchlist for the 3-Minute Strategy.
    
    Workflow:
    1. 9:10 AM: Selects 8 stocks (Top 4 + Bottom 4 by gap %) from Nifty 50 pre-open data.
    2. 9:15 AM: Filters to 4 stocks based on Nifty Index opening/trend.
       - If Nifty Gap Up/Bullish: Keep Top 4 Gap Ups (Long bias).
       - If Nifty Gap Down/Bearish: Keep Top 4 Gap Downs (Short bias).
       - If Neutral: Keep all 8 or filter by individual stock strength.
    """
    
    WATCHLIST_FILE = Path("config/daily_watchlist.json")
    NIFTY50_FILE = Path("config/nifty50.json")
    
    def __init__(self):
        self.config = get_config()
    
    def generate_daily_watchlist(self) -> Dict:
        """
        Generate the initial daily watchlist (8 stocks) from Nifty 50 pre-open data.
        
        Reads nifty50.json, sorts by gap %, and picks Top 4 + Bottom 4.
        Saves to daily_watchlist.json.
        """
        try:
            if not self.NIFTY50_FILE.exists():
                logger.error(f"❌ Nifty 50 file not found: {self.NIFTY50_FILE}")
                return {}
            
            with open(self.NIFTY50_FILE, 'r', encoding='utf-8') as f:
                nifty_data = json.load(f)
            
            stocks = nifty_data.get('stocks', [])
            if not stocks:
                logger.warning("⚠️ No stocks found in Nifty 50 data")
                return {}
            
            # Sort by gap_percent (descending)
            # High positive gaps first, high negative gaps last
            sorted_stocks = sorted(stocks, key=lambda x: x.get('gap_percent', 0), reverse=True)
            
            # Select Top 4 (Bullish) and Bottom 4 (Bearish)
            top_4 = sorted_stocks[:4]
            # Get bottom 4 and sort by gap ascending (most negative first)
            bottom_4 = sorted(sorted_stocks[-4:], key=lambda x: x.get('gap_percent', 0))
            
            # Ensure bottom 4 are actually negative gaps (or at least lower)
            # If all are positive, bottom 4 are just least positive
            
            watchlist_data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "generated_at": now_ist().isoformat(),
                "market_status": "PRE_OPEN",
                "strategy_name": "3-Minute Breakdown",
                "selection_criteria": "Top 4 Gap Up & Top 4 Gap Down",
                "nifty_trend": "WAITING",  # To be updated at 9:15
                "stocks": {
                    "bullish": top_4,
                    "bearish": bottom_4
                },
                "active_set": "BOTH"  # BOTH, BULLISH, BEARISH
            }
            
            self._save_watchlist(watchlist_data)
            logger.info(f"✅ Generated daily watchlist: {len(top_4)} Bullish, {len(bottom_4)} Bearish")
            return watchlist_data
            
        except Exception as e:
            logger.error(f"❌ Error generating daily watchlist: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def filter_watchlist_at_market_open(self, nifty_gap_percent: float, max_trades: int = 2) -> Dict:
        """
        Filter the watchlist at 9:15 AM based on Nifty opening gap.
        
        MEAN REVERSION LOGIC:
        - Nifty GAP_UP → SHORT top stocks (fade the gap)
        - Nifty GAP_DOWN → LONG bottom stocks (fade the gap)
        - FLAT → Both directions with split allocation
        
        Args:
            nifty_gap_percent: The gap percentage of Nifty 50 index
            max_trades: Maximum number of trades per day (default: 2)
            
        Returns:
            Updated watchlist dictionary with selected stocks for trading
        """
        watchlist = self.get_watchlist()
        if not watchlist:
            return {}
        
        # Gap threshold: 0.2% (strict to avoid noise)
        threshold = 0.2
        
        top_stocks = watchlist.get('stocks', {}).get('bullish', [])
        bottom_stocks = watchlist.get('stocks', {}).get('bearish', [])
        
        if nifty_gap_percent > threshold:
            # GAP UP: Short the strongest stocks (mean reversion)
            trend = "GAP_UP"
            active_set = "BEARISH"  # Short top stocks
            selected_stocks = top_stocks[:max_trades]
            trade_direction = "SHORT"
            summary = f"Nifty Gap Up ({nifty_gap_percent:.2f}%). Fading gap - SHORT top {max_trades} stocks."
            
        elif nifty_gap_percent < -threshold:
            # GAP DOWN: Long the weakest stocks (mean reversion)
            trend = "GAP_DOWN"
            active_set = "BULLISH"  # Long bottom stocks
            selected_stocks = bottom_stocks[:max_trades]
            trade_direction = "LONG"
            summary = f"Nifty Gap Down ({nifty_gap_percent:.2f}%). Fading gap - LONG bottom {max_trades} stocks."
            
        else:
            # FLAT: Both directions with split allocation
            trend = "FLAT"
            active_set = "BOTH"
            # Split max_trades between both directions
            trades_per_side = max(1, max_trades // 2)
            selected_stocks = {
                'long': bottom_stocks[:trades_per_side],
                'short': top_stocks[:trades_per_side]
            }
            trade_direction = "MIXED"
            summary = f"Nifty Flat ({nifty_gap_percent:.2f}%). Trading both sides - LONG bottom {trades_per_side}, SHORT top {trades_per_side}."
        
        watchlist['market_status'] = "OPEN"
        watchlist['nifty_trend'] = trend
        watchlist['nifty_gap_percent'] = nifty_gap_percent
        watchlist['active_set'] = active_set
        watchlist['selected_stocks'] = selected_stocks
        watchlist['trade_direction'] = trade_direction
        watchlist['max_trades'] = max_trades
        watchlist['filter_reason'] = summary
        watchlist['updated_at'] = now_ist().isoformat()
        
        self._save_watchlist(watchlist)
        logger.info(f"✅ Watchlist filtered: {summary}")
        return watchlist
    
    def get_watchlist(self) -> Dict:
        """Get the current daily watchlist."""
        if not self.WATCHLIST_FILE.exists():
            return {}
        
        try:
            with open(self.WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading watchlist: {e}")
            return {}
            
    def _save_watchlist(self, data: Dict) -> None:
        """Save watchlist to file."""
        self.WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# Singleton instance
_watchlist_manager: Optional[DailyWatchlistManager] = None

def get_watchlist_manager() -> DailyWatchlistManager:
    global _watchlist_manager
    if _watchlist_manager is None:
        _watchlist_manager = DailyWatchlistManager()
    return _watchlist_manager
