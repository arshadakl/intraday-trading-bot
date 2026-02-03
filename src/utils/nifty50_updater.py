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
            List of stock data with symbol, name, and other details
        """
        try:
            fetcher = self._ensure_fetcher()
            
            # Fetch raw pre-open data (contains all Nifty 50 stocks)
            raw_data = fetcher.fetch_preopen_data()
            
            if not raw_data:
                logger.error("❌ No data returned from NSE pre-open API")
                return []
            
            stocks = []
            for item in raw_data:
                symbol = item.get('symbol', '')
                
                if not symbol:
                    continue
                
                stock = {
                    'symbol': symbol,
                    'name': symbol,  # Pre-open API doesn't give company name
                    'iep': item.get('iep', 0),
                    'prev_close': item.get('prev_close', 0),
                }
                stocks.append(stock)
            
            logger.info(f"📊 Fetched {len(stocks)} Nifty 50 constituents from NSE pre-open API")
            return stocks
            
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
        Update the Nifty 50 stock list.
        
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
        
        # Load existing config
        existing_config = self.load_existing_config()
        existing_stocks = existing_config.get('stocks', [])
        
        # Create lookup by symbol (without -EQ suffix)
        existing_lookup = {}
        for stock in existing_stocks:
            base_symbol = stock['symbol'].replace('-EQ', '').upper()
            existing_lookup[base_symbol] = stock
        
        # Create set of current NSE symbols
        nse_symbols = {s['symbol'].upper() for s in nse_stocks}
        existing_symbols = set(existing_lookup.keys())
        
        # Find additions and removals
        added_symbols = nse_symbols - existing_symbols
        removed_symbols = existing_symbols - nse_symbols
        unchanged_symbols = nse_symbols & existing_symbols
        
        result['added'] = list(added_symbols)
        result['removed'] = list(removed_symbols)
        result['unchanged'] = list(unchanged_symbols)
        
        # Log changes
        if added_symbols:
            logger.info(f"➕ New stocks to add: {sorted(added_symbols)}")
        if removed_symbols:
            logger.info(f"➖ Stocks removed from Nifty 50: {sorted(removed_symbols)}")
        
        # Build updated stock list
        updated_stocks = []
        missing_tokens = []
        
        for nse_stock in nse_stocks:
            symbol = nse_stock['symbol'].upper()
            
            if symbol in existing_lookup:
                # Keep existing stock with token
                stock = existing_lookup[symbol].copy()
                # Update name if changed
                if nse_stock.get('name'):
                    stock['name'] = nse_stock['name']
                updated_stocks.append(stock)
            else:
                # New stock - add without token
                new_stock = {
                    'symbol': f"{symbol}-EQ",
                    'token': "",  # Token needs to be added manually or fetched from broker
                    'name': nse_stock.get('name', symbol)
                }
                updated_stocks.append(new_stock)
                missing_tokens.append(symbol)
        
        result['missing_tokens'] = missing_tokens
        result['total_stocks'] = len(updated_stocks)
        
        if missing_tokens:
            logger.warning(f"⚠️ Stocks missing tokens (need manual update): {missing_tokens}")
        
        # Update config
        updated_config = {
            'stocks': updated_stocks,
            'index': existing_config.get('index', {"symbol": "NIFTY", "token": "99926000"}),
            '_updated': datetime.now().isoformat(),
            '_source': 'NSE India API'
        }
        
        # Save config
        if self.save_config(updated_config):
            result['success'] = True
            logger.info(f"✅ Nifty 50 list updated: {len(updated_stocks)} stocks")
        
        return result['success'], result
    
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


# CLI support
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n🔄 Updating Nifty 50 Stock List from NSE India...\n")
    
    success = update_nifty50_stocks()
    
    sys.exit(0 if success else 1)
