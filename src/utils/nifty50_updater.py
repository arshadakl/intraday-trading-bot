"""
Nifty 50 Stock List Updater

Fetches the current Nifty 50 constituents from NSE India API
and updates the local config/nifty50.json file.

This should be run daily before market opens to ensure the
trading bot has the latest Nifty 50 stocks.

Author: Trading Bot
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Nifty50Updater:
    """
    Automatically updates the Nifty 50 stock list from NSE India.
    
    Uses the NSE pre-open API (via NSEPreOpenFetcher) to get current 
    Nifty 50 constituents and merges with existing token data.
    
    New stocks that don't have tokens will be flagged for manual update.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the updater.
        
        Args:
            config_path: Path to nifty50.json config file
        """
        if config_path is None:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "nifty50.json"
        
        self.config_path = Path(config_path)
        self._fetcher = None
    
    def _ensure_fetcher(self):
        """Lazy initialization of NSE pre-open fetcher."""
        if self._fetcher is None:
            from src.analysis.nse_preopen_fetcher import NSEPreOpenFetcher
            self._fetcher = NSEPreOpenFetcher()
        return self._fetcher
    
    def fetch_nifty50_constituents(self) -> List[Dict]:
        """
        Fetch current Nifty 50 constituents from NSE API.
        
        Uses the NSEPreOpenFetcher which handles NSE's anti-bot measures.
        
        Returns:
            List of stock data with symbol, name, and all NSE metadata
        """
        try:
            fetcher = self._ensure_fetcher()
            
            # Fetch pre-open data (contains all Nifty 50 stocks)
            # Returns rich data with iep, change, change_percent, gap_percent, volume, etc.
            raw_data = fetcher.fetch_preopen_data()
            
            if not raw_data:
                logger.error("❌ No data returned from NSE pre-open API")
                return []
            
            # The fetcher already returns properly structured data
            # Just pass it through, preserving the order
            logger.info(f"📊 Fetched {len(raw_data)} Nifty 50 constituents from NSE pre-open API")
            return raw_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch Nifty 50 data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def load_existing_config(self) -> Dict:
        """Load existing nifty50.json config."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {"stocks": [], "index": {"symbol": "NIFTY", "token": "99926000"}}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"stocks": [], "index": {"symbol": "NIFTY", "token": "99926000"}}
    
    def save_config(self, config: Dict) -> bool:
        """Save updated config to file."""
        try:
            # Create backup first
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(self.load_existing_config(), f, indent=2)
                logger.info(f"📁 Backup saved to {backup_path}")
            
            # Save new config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Config saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")
            return False
    
    def update_nifty50_list(self, nse_stocks: Optional[List[Dict]] = None) -> Tuple[bool, Dict]:
        """
        Update the Nifty 50 stock list from NSE pre-open API.
        
        IMPORTANT: This method preserves the exact order of stocks from the NSE API.
        The order is based on pre-open market activity and is critical for the 
        3-minute strategy which uses this ordering for stock selection.
        
        Enforces exactly 50 stocks (filters invalid entries).
        
        Args:
            nse_stocks: Optional pre-fetched NSE stock data. If None, will fetch from API.
            
        Returns:
            Tuple of (success, result_dict with stats)
        """
        result = {
            'success': False,
            'added': [],
            'removed': [],
            'unchanged': [],
            'missing_tokens': [],
            'total_stocks': 0
        }
        
        # Fetch current Nifty 50 from NSE if not provided
        if nse_stocks is None:
            nse_stocks = self.fetch_nifty50_constituents()
        
        if not nse_stocks:
            logger.error("❌ No stocks to process - aborting update")
            return False, result
        
        # Load existing config for token lookup only
        existing_config = self.load_existing_config()
        existing_stocks = existing_config.get('stocks', [])
        
        # Create lookup by symbol for existing tokens
        existing_token_lookup = {}
        for stock in existing_stocks:
            base_symbol = stock.get('symbol', '').replace('-EQ', '').upper()
            if stock.get('token'):
                existing_token_lookup[base_symbol] = stock['token']
        
        # Track changes
        nse_symbols = {s.get('symbol', '').upper() for s in nse_stocks}
        existing_symbols = set(existing_token_lookup.keys())
        
        added_symbols = nse_symbols - existing_symbols
        removed_symbols = existing_symbols - nse_symbols
        unchanged_symbols = nse_symbols & existing_symbols
        
        result['added'] = list(added_symbols)
        result['removed'] = list(removed_symbols)
        result['unchanged'] = list(unchanged_symbols)
        
        if added_symbols:
            logger.info(f"➕ New stocks in Nifty 50: {sorted(added_symbols)}")
        if removed_symbols:
            logger.info(f"➖ Stocks removed from Nifty 50: {sorted(removed_symbols)}")
        
        # Build updated stock list - PRESERVING NSE API ORDER
        updated_stocks = []
        missing_tokens = []
        
        for idx, nse_stock in enumerate(nse_stocks):
            symbol = nse_stock.get('symbol', '').upper()
            if not symbol:
                continue
            
            # Get token from existing data if available
            token = existing_token_lookup.get(symbol, '')
            if not token:
                missing_tokens.append(symbol)
            
            # Create rich stock data with all NSE metadata
            stock_data = {
                'rank': idx + 1,  # Position in NSE pre-open order
                'symbol': f"{symbol}-EQ",
                'token': token,
                'name': symbol,  # NSE pre-open API doesn't provide company name
                
                # Price data from NSE
                'iep': nse_stock.get('iep', 0),  # Indicative Equilibrium Price
                'last_price': nse_stock.get('last_price', 0),
                'prev_close': nse_stock.get('prev_close', 0),
                
                # Change data
                'change': nse_stock.get('change', 0),
                'change_percent': nse_stock.get('change_percent', 0),
                
                # Gap analysis
                'gap_percent': nse_stock.get('gap_percent', 0),
                'gap_type': nse_stock.get('gap_type', 'NEUTRAL'),
                
                # Volume
                'volume': nse_stock.get('volume', 0),
                'final_quantity': nse_stock.get('final_quantity', 0),
                
                # Year high/low
                'year_high': nse_stock.get('year_high', 0),
                'year_low': nse_stock.get('year_low', 0),
            }
            
            updated_stocks.append(stock_data)
        
        # ---- Enforce exactly 50 stocks ----
        # NSE API may return >50 stocks; keep only the first 50 valid ones
        if len(updated_stocks) > 50:
            logger.warning(f"⚠️ NSE returned {len(updated_stocks)} stocks — trimming to 50")
            updated_stocks = updated_stocks[:50]
        
        # Re-rank after trimming
        for idx, stock in enumerate(updated_stocks):
            stock['rank'] = idx + 1
        
        result['missing_tokens'] = missing_tokens
        result['total_stocks'] = len(updated_stocks)
        
        if missing_tokens:
            logger.warning(f"⚠️ Stocks missing tokens: {missing_tokens}")
        
        # Update config with rich data structure
        updated_config = {
            'stocks': updated_stocks,  # Ordered by NSE pre-open ranking
            'index': existing_config.get('index', {"symbol": "NIFTY", "token": "99926000"}),
            'market_summary': {
                'advances': len([s for s in updated_stocks if s.get('change', 0) > 0]),
                'declines': len([s for s in updated_stocks if s.get('change', 0) < 0]),
                'unchanged': len([s for s in updated_stocks if s.get('change', 0) == 0]),
            },
            '_updated': datetime.now().isoformat(),
            '_source': 'NSE Pre-Open API',
            '_order': 'NSE pre-open ranking (important for 3-min strategy)'
        }
        
        # Save config
        if self.save_config(updated_config):
            result['success'] = True
            logger.info(f"✅ Nifty 50 list updated: {len(updated_stocks)} stocks (order preserved)")
        
        return result['success'], result
    
    def fetch_nifty_index_data(self, max_retries: int = 3, retry_delay: float = 2.0) -> Dict:
        """
        Fetch Nifty index-level data (prev_close, open) from AngelOne API.
        
        This is called at 9:15 AM to get fresh data for gap calculation.
        ALWAYS fetches from live API — never trusts stored JSON.
        
        Retries on failure because Nifty gap status is critical.
        
        Args:
            max_retries: Number of retry attempts (default 3)
            retry_delay: Seconds between retries (default 2.0)
            
        Returns:
            Dict with prev_close, open, ltp, gap_percent, gap_status
        """
        import time
        
        for attempt in range(max_retries):
            try:
                # Try AngelOne API
                from src.broker.angel_client import AngelOneClient
                # Get the bot's angel_client if available
                angel_client = None
                try:
                    from src.core.bot import get_bot
                    bot, err = get_bot()
                    if bot and hasattr(bot, 'angel_client') and bot.angel_client:
                        angel_client = bot.angel_client
                except Exception:
                    pass
                
                if angel_client and angel_client.is_authenticated:
                    quote = angel_client.get_quote(
                        symbol="NIFTY",
                        token="99926000",
                        exchange="NSE"
                    )
                    if quote:
                        prev_close = quote.get('previousClose') or quote.get('close')
                        open_price = quote.get('open')
                        ltp = quote.get('ltp')
                        
                        if prev_close and float(prev_close) > 0:
                            prev_close = float(prev_close)
                            open_price = float(open_price) if open_price else None
                            ltp = float(ltp) if ltp else None
                            
                            gap_percent = 0.0
                            gap_status = "FLAT"
                            if open_price and open_price > 0:
                                gap_percent = ((open_price - prev_close) / prev_close) * 100
                                if gap_percent > 0.2:
                                    gap_status = "GAP_UP"
                                elif gap_percent < -0.2:
                                    gap_status = "GAP_DOWN"
                            
                            index_data = {
                                "symbol": "NIFTY",
                                "token": "99926000",
                                "prev_close": round(prev_close, 2),
                                "open": round(open_price, 2) if open_price else None,
                                "ltp": round(ltp, 2) if ltp else None,
                                "gap_percent": round(gap_percent, 2),
                                "gap_status": gap_status,
                                "_fetched_at": datetime.now().isoformat(),
                                "_source": "angel_api"
                            }
                            
                            logger.info(
                                f"✅ Nifty index data fetched: "
                                f"PrevClose={prev_close:.2f} Open={open_price} "
                                f"Gap={gap_percent:+.2f}% ({gap_status})"
                            )
                            
                            # Save to nifty50.json index field
                            self._save_index_data(index_data)
                            return index_data
                
                logger.warning(
                    f"⚠️ Nifty index fetch attempt {attempt + 1}/{max_retries} failed "
                    f"— {'retrying...' if attempt < max_retries - 1 else 'no more retries'}"
                )
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logger.warning(
                    f"⚠️ Nifty index fetch attempt {attempt + 1}/{max_retries} error: {e} "
                    f"— {'retrying...' if attempt < max_retries - 1 else 'no more retries'}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        logger.error("❌ Failed to fetch Nifty index data after all retries")
        return {"symbol": "NIFTY", "token": "99926000", "prev_close": None, "open": None}
    
    def _save_index_data(self, index_data: Dict) -> None:
        """Save index data to the index field in nifty50.json"""
        try:
            config = self.load_existing_config()
            config['index'] = index_data
            self.save_config(config)
            logger.info("✅ Nifty index data saved to nifty50.json")
        except Exception as e:
            logger.error(f"❌ Failed to save index data: {e}")
    
    def get_update_summary(self, result: Dict) -> str:
        """Generate a human-readable update summary."""
        lines = [
            "=" * 50,
            "📊 NIFTY 50 UPDATE SUMMARY",
            "=" * 50,
            f"Total Stocks: {result.get('total_stocks', 0)}",
            f"Added: {len(result.get('added', []))}",
            f"Removed: {len(result.get('removed', []))}",
            f"Unchanged: {len(result.get('unchanged', []))}",
        ]
        
        if result.get('added'):
            lines.append(f"\n➕ Newly Added: {', '.join(sorted(result['added']))}")
        
        if result.get('removed'):
            lines.append(f"\n➖ Removed: {', '.join(sorted(result['removed']))}")
        
        if result.get('missing_tokens'):
            lines.append(f"\n⚠️ Missing Tokens (need manual update):")
            for symbol in result['missing_tokens']:
                lines.append(f"   - {symbol}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def update_from_json_file(self, json_file: str) -> Tuple[bool, Dict]:
        """
        Update Nifty 50 list from a saved JSON file.
        
        Use this when the NSE API is blocked. You can save the pre-open 
        API response to a file and use this method to update the config.
        
        Args:
            json_file: Path to JSON file with NSE pre-open data format
            
        Returns:
            Tuple of (success, result_dict with stats)
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Parse the NSE pre-open format
            if 'data' not in raw_data:
                logger.error("Invalid JSON format - no 'data' field")
                return False, {'success': False}
            
            stocks = []
            for item in raw_data['data']:
                metadata = item.get('metadata', {})
                symbol = metadata.get('symbol', '')
                
                if not symbol:
                    continue
                
                stocks.append({
                    'symbol': symbol,
                    'name': symbol,
                    'iep': metadata.get('iep', 0),
                    'prev_close': metadata.get('previousClose', 0),
                })
            
            logger.info(f"📊 Loaded {len(stocks)} stocks from {json_file}")
            return self.update_nifty50_list(nse_stocks=stocks)
            
        except Exception as e:
            logger.error(f"❌ Failed to load JSON file: {e}")
            return False, {'success': False}


def update_nifty50_stocks() -> bool:
    """
    Convenience function to update Nifty 50 stock list.
    Call this on bot startup or before market opens.
    
    Returns:
        True if update was successful
    """
    updater = Nifty50Updater()
    success, result = updater.update_nifty50_list()
    
    # Print summary
    print(updater.get_update_summary(result))
    
    return success


def update_from_preopen_data(preopen_data: List[Dict]) -> bool:
    """
    Update Nifty 50 list using already-fetched pre-open data.
    
    This is more efficient if you're already fetching pre-open data
    for the 3-minute strategy.
    
    Args:
        preopen_data: List of parsed pre-open data dicts
        
    Returns:
        True if update was successful
    """
    updater = Nifty50Updater()
    success, result = updater.update_nifty50_list(nse_stocks=preopen_data)
    
    # Print summary
    print(updater.get_update_summary(result))
    
    return success


def update_nifty50_at_market_open() -> bool:
    """
    Comprehensive Nifty 50 update function designed to run at 9:10 AM.
    
    This function:
    1. Fetches the latest Nifty 50 stock list from NSE pre-open API
    2. Updates config/nifty50.json with the new list (max 50 stocks)
    3. Fetches and fills in missing instrument tokens from Angel One
    4. Fetches Nifty index data (prev_close, open) for gap calculation
    
    Returns:
        True if update was successful
    """
    print("\n" + "=" * 60)
    print("  📊 NIFTY 50 DAILY UPDATE (9:10 AM)")
    print("=" * 60)
    
    # Step 1: Update Nifty 50 list from NSE
    print("\n🔄 Step 1: Fetching Nifty 50 constituents from NSE...")
    updater = Nifty50Updater()
    
    try:
        success, result = updater.update_nifty50_list()
        
        if success:
            logger.info("✅ NIFTY 50 UPDATE COMPLETE")
            
            # Fetch missing tokens after update
            if result.get('missing_tokens'):
                logger.info(f"🔄 Updating tokens for {len(result['missing_tokens'])} stocks...")
                try:
                    from src.utils.angel_token_fetcher import AngelTokenFetcher
                    token_fetcher = AngelTokenFetcher()
                    token_result = token_fetcher.update_nifty50_tokens()
                    
                    if token_result.get('updated', 0) > 0:
                        logger.info(f"✅ Updated {token_result['updated']} tokens")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch tokens: {e}")
            
            # Step 2: Fetch Nifty index data (prev_close, open) with retry
            logger.info("🔄 Step 2: Fetching Nifty index data for gap calculation...")
            index_data = updater.fetch_nifty_index_data(max_retries=3, retry_delay=2.0)
            
            if index_data.get('prev_close'):
                # Also update the NiftyIndexTracker singleton
                try:
                    from src.analysis.nifty_tracker import get_nifty_tracker
                    tracker = get_nifty_tracker()
                    tracker.set_prev_close(index_data['prev_close'])
                except Exception as e:
                    logger.debug(f"Could not update nifty_tracker: {e}")
            else:
                logger.warning("⚠️ Nifty index prev_close not available — gap analysis may be FLAT")
            
            # Step 3: Generate Daily Watchlist for 3-Minute Strategy
            try:
                from src.analysis.daily_watchlist import get_watchlist_manager
                manager = get_watchlist_manager()
                watchlist = manager.generate_daily_watchlist()
                logger.info(f"✅ Generated Daily Watchlist: {len(watchlist.get('stocks', {}).get('bullish', []))} Bullish, {len(watchlist.get('stocks', {}).get('bearish', []))} Bearish")
            except Exception as e:
                logger.error(f"❌ Failed to generate daily watchlist: {e}")
                
            return True
        else:
            logger.error("❌ Failed to update Nifty 50 list")
            return False
            
    except Exception as e:
        logger.error(f"❌ Market open update failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_nifty_index_gap_data(max_retries: int = 3) -> Dict:
    """
    Standalone function to fetch fresh Nifty index gap data at 9:15 AM.
    
    ALWAYS fetches from live API — never trusts stored JSON.
    Retries on failure because Nifty gap status is critical.
    
    Returns:
        Dict with prev_close, open, gap_percent, gap_status
    """
    updater = Nifty50Updater()
    return updater.fetch_nifty_index_data(max_retries=max_retries)


# CLI support
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n🔄 Updating Nifty 50 Stock List from NSE India...\n")
    
    success = update_nifty50_at_market_open()
    
    sys.exit(0 if success else 1)

