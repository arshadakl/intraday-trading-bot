"""
Angel One Token Fetcher

Fetches instrument tokens from Angel One's public instrument master file.
This is required to get the correct trading tokens for Nifty 50 stocks.

Usage:
    python -m src.utils.angel_token_fetcher ETERNAL JIOFIN TRENT
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class AngelTokenFetcher:
    """
    Fetches instrument tokens from Angel One's instrument master.
    
    Angel One provides a public JSON file with all tradeable instruments.
    This class downloads and parses it to find tokens by symbol.
    """
    
    # Angel One instrument master URL
    INSTRUMENT_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    
    # Cache file path
    CACHE_FILE = "data/angel_instruments.json"
    
    # Cache duration in seconds (24 hours)
    CACHE_DURATION = 86400
    
    def __init__(self):
        self._instruments = None
        self._cache_path = Path(__file__).parent.parent.parent / self.CACHE_FILE
    
    def _load_cache(self) -> Optional[List[Dict]]:
        """Load instruments from cache if valid."""
        try:
            if self._cache_path.exists():
                # Check cache age
                cache_age = time.time() - self._cache_path.stat().st_mtime
                if cache_age < self.CACHE_DURATION:
                    with open(self._cache_path, 'r') as f:
                        return json.load(f)
                    logger.debug("Using cached instrument data")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_cache(self, data: List[Dict]) -> None:
        """Save instruments to cache."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_path, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Saved {len(data)} instruments to cache")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def fetch_instruments(self, force_refresh: bool = False) -> List[Dict]:
        """
        Fetch all instruments from Angel One.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of instrument dictionaries
        """
        if self._instruments and not force_refresh:
            return self._instruments
        
        # Try cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                self._instruments = cached
                return cached
        
        # Fetch from API
        logger.info("📥 Downloading Angel One instrument master...")
        
        try:
            response = requests.get(self.INSTRUMENT_URL, timeout=60)
            response.raise_for_status()
            
            instruments = response.json()
            self._instruments = instruments
            
            # Save to cache
            self._save_cache(instruments)
            
            logger.info(f"✅ Downloaded {len(instruments)} instruments")
            return instruments
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch instruments: {e}")
            
            # Try loading stale cache as fallback
            if self._cache_path.exists():
                logger.info("Using stale cache as fallback")
                with open(self._cache_path, 'r') as f:
                    return json.load(f)
            
            return []
    
    def get_token_by_symbol(
        self, 
        symbol: str, 
        exchange: str = "NSE",
        instrument_type: str = ""
    ) -> Optional[str]:
        """
        Get instrument token for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "ETERNAL")
            exchange: Exchange (NSE, BSE)
            instrument_type: Filter by instrument type (EQ, FUT, etc.)
            
        Returns:
            Token string or None if not found
        """
        instruments = self.fetch_instruments()
        
        # Normalize symbol
        symbol = symbol.upper().replace("-EQ", "")
        
        for inst in instruments:
            if inst.get('exch_seg') != exchange:
                continue
            
            inst_symbol = inst.get('symbol', '').upper()
            
            # Check exact match or symbol-EQ format
            if inst_symbol == symbol or inst_symbol == f"{symbol}-EQ":
                # Filter by instrument type if specified
                if instrument_type:
                    if inst.get('instrumenttype', '') != instrument_type:
                        continue
                
                return inst.get('token')
        
        return None
    
    def get_tokens_for_symbols(self, symbols: List[str]) -> Dict[str, Optional[str]]:
        """
        Get tokens for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to token (None if not found)
        """
        instruments = self.fetch_instruments()
        
        # Build lookup for efficiency
        nse_instruments = {}
        for inst in instruments:
            if inst.get('exch_seg') == 'NSE':
                sym = inst.get('symbol', '').upper()
                nse_instruments[sym] = inst.get('token')
                # Also store without -EQ suffix
                if sym.endswith('-EQ'):
                    nse_instruments[sym[:-3]] = inst.get('token')
        
        # Look up each symbol
        result = {}
        for symbol in symbols:
            sym = symbol.upper().replace('-EQ', '')
            result[symbol] = nse_instruments.get(sym) or nse_instruments.get(f"{sym}-EQ")
        
        return result
    
    def update_nifty50_tokens(self) -> Dict:
        """
        Update missing tokens in nifty50.json.
        
        Returns:
            Dict with update stats
        """
        config_path = Path(__file__).parent.parent.parent / "config" / "nifty50.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load nifty50.json: {e}")
            return {'success': False, 'error': str(e)}
        
        # Find stocks with missing tokens
        missing = []
        for stock in config.get('stocks', []):
            if not stock.get('token'):
                missing.append(stock['symbol'])
        
        if not missing:
            logger.info("✅ All stocks have tokens")
            return {'success': True, 'updated': 0}
        
        logger.info(f"🔍 Looking up tokens for: {missing}")
        
        # Fetch tokens
        tokens = self.get_tokens_for_symbols(missing)
        
        # Update config
        updated = 0
        still_missing = []
        
        for stock in config.get('stocks', []):
            if not stock.get('token'):
                symbol = stock['symbol']
                token = tokens.get(symbol)
                if token:
                    stock['token'] = token
                    updated += 1
                    logger.info(f"✅ Updated {symbol}: token={token}")
                else:
                    still_missing.append(symbol)
                    logger.warning(f"⚠️ Token not found for {symbol}")
        
        # Save updated config
        if updated > 0:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Updated {updated} tokens in nifty50.json")
        
        return {
            'success': True,
            'updated': updated,
            'still_missing': still_missing
        }


def fetch_missing_tokens() -> bool:
    """
    Convenience function to update missing tokens in nifty50.json.
    
    Returns:
        True if successful
    """
    fetcher = AngelTokenFetcher()
    result = fetcher.update_nifty50_tokens()
    
    if result.get('still_missing'):
        print(f"\n⚠️ Could not find tokens for: {result['still_missing']}")
        print("These may have different symbol names in Angel One")
    
    return result.get('success', False)


# CLI support
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        # Look up specific symbols
        symbols = sys.argv[1:]
        fetcher = AngelTokenFetcher()
        tokens = fetcher.get_tokens_for_symbols(symbols)
        
        print("\n📊 Token Lookup Results:")
        print("-" * 40)
        for symbol, token in tokens.items():
            status = f"✅ {token}" if token else "❌ Not found"
            print(f"{symbol}: {status}")
    else:
        # Update missing tokens in nifty50.json
        print("\n🔄 Updating missing tokens in nifty50.json...\n")
        fetch_missing_tokens()
