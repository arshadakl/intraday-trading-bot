"""Main Trading Bot Orchestrator - Controls all components"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from src.utils.timezone import now_ist, now_ist_time

from src.core.config_manager import get_config, ConfigManager
from src.core.scheduler import TradingScheduler
from src.broker.angel_client import AngelOneClient
from src.broker.paper_trader import PaperTrader
from src.broker.websocket_client import AngelWebSocket
from src.analysis.pre_market import PreMarketAnalyzer
from src.analysis.stock_scorer import StockScorer
from src.strategy.base_strategy import BaseStrategy
from src.strategy.strategy_registry import StrategyRegistry
from src.strategy.risk_manager import RiskManager
from src.executor.order_manager import OrderManager
from src.executor.position_tracker import PositionTracker
from src.analysis.indicators import LiveIndicatorManager


class TradingBot:
    """
    Main trading bot that orchestrates all components. 
    Handles the complete trading workflow from analysis to execution.
    """
    
    def __init__(self):
        # Core components
        self.config: ConfigManager = get_config()
        self.scheduler = TradingScheduler()
        
        # Broker components
        self.angel_client: Optional[AngelOneClient] = None
        self.paper_trader: Optional[PaperTrader] = None
        self.websocket: Optional[AngelWebSocket] = None
        
        # Analysis components
        self.pre_market_analyzer: Optional[PreMarketAnalyzer] = None
        self.stock_scorer: Optional[StockScorer] = None
        
        # Strategy & Execution
        self.strategy: Optional[BaseStrategy] = None
        self.current_strategy_name: str = "vwap_rsi"  # Track active strategy name
        self.risk_manager: Optional[RiskManager] = None
        self.order_manager: Optional[OrderManager] = None
        self.position_tracker: Optional[PositionTracker] = None
        self.live_indicators = LiveIndicatorManager()
        
        # State
        self.status = "STOPPED"  # STOPPED, INITIALIZING, READY, RUNNING, PAUSED
        self.startup_mode = None  # PRE_MARKET, MARKET_HOURS, NON_MARKET
        self.selected_stocks: List[Dict] = []
        self.start_time: Optional[datetime] = None
        self.daily_stats = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl": 0.0
        }
        self.market_analysis = {
            "analyzed_at": None,
            "total_stocks_analyzed": 0,
            "stocks": [],
            "trading_suitable": False,
            "reason": ""
        }
        
        # Activity log (for dashboard)
        self.activity_log: List[Dict] = []
        self._log_lock = threading.Lock()
        
        # Signal cooldown tracking (prevents race condition)
        self._last_signal_time: Dict[str, datetime] = {}
        self._signal_cooldown_seconds = 60  # Minimum 60 seconds between signals for same stock
        
        # Pending orders tracking
        self.pending_orders: Dict[str, Dict] = {} # order_id -> order_details
        self._pending_lock = threading.Lock()
        
        # Cooldown tracking
        self._last_exit_time: Dict[str, datetime] = {}
        self._exit_cooldown_minutes = 5 # Prevent re-entry for 5 minutes after exit
        
        # Ensure data directories exist
        Path("data/daily").mkdir(parents=True, exist_ok=True)
        Path("data/trades").mkdir(parents=True, exist_ok=True)
        Path("data/reports").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
        
        logger.info("🤖 Trading Bot initialized")
        self._log_activity("SYSTEM", "Trading Bot initialized")
    
    def _log_activity(self, category: str, message: str, data: Dict = None) -> None:
        """Add an entry to the activity log"""
        with self._log_lock:
            entry = {
                "timestamp": now_ist().isoformat(),
                "time": now_ist().strftime("%H:%M:%S"),
                "category": category,
                "message":  message,
                "data": data or {}
            }
            self.activity_log.append(entry)
            # Keep only last 100 entries
            if len(self.activity_log) > 100:
                self.activity_log = self.activity_log[-100:]
    
    def get_activity_log(self, limit: int = 50) -> List[Dict]:
        """Get recent activity log entries"""
        with self._log_lock:
            return self.activity_log[-limit:][::-1]  # Return newest first
    
    def get_current_mode(self) -> str:
        """
        Dynamically determine the current operating mode based on real-time state.
        This is different from startup_mode which is set once at startup.
        
        Returns:
            str: TRADING, READY_TO_TRADE, WAITING_FOR_ANALYSIS, MONITORING_ONLY, MARKET_CLOSING, ANALYSIS_COMPLETE, or NON_MARKET
        """
        now = now_ist_time()
        timing = self.config.get("timing", {})
        
        market_open = datetime.strptime(timing.get("trading_start", "09:15"), "%H:%M").time()
        no_new_trades = datetime.strptime(timing.get("no_new_trade_after", "15:00"), "%H:%M").time()
        market_close = datetime.strptime(timing.get("market_close", "15:30"), "%H:%M").time()
        
        # Check if WebSocket is connected and actively monitoring
        is_monitoring = self.websocket is not None and hasattr(self.websocket, 'is_connected') and self.websocket.is_connected
        
        # Check if we have positions
        has_positions = self.position_tracker and len(self.position_tracker.get_all_positions()) > 0
        
        # Within trading hours
        if market_open <= now <= no_new_trades:
            if is_monitoring or has_positions:
                return "TRADING"
            elif self.selected_stocks:
                return "READY_TO_TRADE"
            else:
                return "WAITING_FOR_ANALYSIS"
        
        # Within monitoring-only hours (after no_new_trades but before close)
        elif no_new_trades < now <= market_close:
            if has_positions:
                return "MONITORING_ONLY"  # Just watching existing positions
            else:
                return "MARKET_CLOSING"
        
        # Outside market hours
        else:
            if self.selected_stocks:
                return "ANALYSIS_COMPLETE"
            else:
                return "NON_MARKET"
    
    # ==================== Initialization ====================
    
    def initialize(self) -> bool:
        """Initialize all components and connect to broker"""
        self.status = "INITIALIZING"
        self._log_activity("SYSTEM", "Initializing bot components...")
        
        try:
            # 1. Initialize Angel One client
            logger.info("📡 Connecting to Angel One...")
            self.angel_client = AngelOneClient()
            
            if not self.angel_client.login():
                logger.error("❌ Failed to login to Angel One")
                self._log_activity("ERROR", "Failed to login to Angel One")
                return False
            
            # Get account info
            profile = self.angel_client.get_profile()
            if profile:
                logger.info(f"👤 Logged in as: {profile.get('name', 'Unknown')}")
                self._log_activity("AUTH", f"Logged in as {profile.get('name')}")
            
            # 2. Get account balance
            balance = self.angel_client.get_available_balance()
            logger.info(f"💰 Account Balance: ₹{balance:,.2f}")
            
            # 3. Initialize paper trader if in paper mode
            if self.config.is_paper_mode:
                # Use default balance if API returns 0 (e.g., due to rate limiting)
                paper_balance = balance if balance > 0 else self.config.get("capital.default_paper_balance", 100000.0)
                if balance <= 0:
                    logger.warning(f"⚠️ API returned 0 balance, using default paper balance: ₹{paper_balance:,.2f}")
                self.paper_trader = PaperTrader(initial_balance=paper_balance)
                logger.info(f"📝 Paper Trading Mode - Balance: ₹{paper_balance:,.2f}")
                self._log_activity("MODE", f"Paper trading enabled with ₹{paper_balance:,.2f}")
            else:
                logger.warning("⚠️ LIVE TRADING MODE - Real money will be used!")
                self._log_activity("MODE", "LIVE TRADING MODE ENABLED", {"warning": True})
            
            # 4. Initialize analysis components
            self.pre_market_analyzer = PreMarketAnalyzer(self.angel_client)
            self.stock_scorer = StockScorer()
            
            # 5. Register and initialize strategy from registry (dynamic, not hardcoded)
            # Import strategies here to trigger registration (avoids circular imports)
            from src.strategy.vwap_rsi_strategy import VWAPRSIStrategy  # noqa: F401
            from src.strategy.ohl_strategy import OHLStrategy  # noqa: F401
            
            active_strategy_name = self.config.get('active_strategy', 'vwap_rsi')
            if not StrategyRegistry.is_registered(active_strategy_name):
                logger.warning(f"⚠️ Strategy '{active_strategy_name}' not found, falling back to 'vwap_rsi'")
                active_strategy_name = 'vwap_rsi'
            
            self.strategy = StrategyRegistry.get_strategy(active_strategy_name)
            self.current_strategy_name = active_strategy_name
            strategy_meta = StrategyRegistry.get_metadata(active_strategy_name)
            logger.info(f"📈 Active Strategy: {strategy_meta.get('display_name', active_strategy_name)}")
            self._log_activity("STRATEGY", f"Loaded strategy: {active_strategy_name}")
            
            # 6. Initialize risk manager
            # Use paper_balance if in paper mode (which has the fallback), otherwise use actual balance
            capital_for_risk = paper_balance if self.config.is_paper_mode else balance
            trading_capital = self._calculate_trading_capital(capital_for_risk)
            self.risk_manager = RiskManager(trading_capital=trading_capital)
            
            # 7. Initialize order manager and position tracker
            self.order_manager = OrderManager(
                broker=self.angel_client,
                paper_trader=self.paper_trader
            )
            self.position_tracker = PositionTracker()
            
            # 8. Sync persisted positions from paper_trader to position_tracker
            if self.config.is_paper_mode and self.paper_trader:
                self._sync_positions_from_paper_trader()
            
            self.status = "READY"
            logger.success("✅ Bot initialized successfully!")
            self._log_activity("SYSTEM", "Bot initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            self._log_activity("ERROR", f"Initialization failed: {str(e)}")
            self.status = "STOPPED"
            return False
    
    def _calculate_trading_capital(self, total_balance: float) -> float:
        """Calculate trading capital based on config"""
        if self.config.get("capital.use_percentage"):
            percentage = self.config.get("capital.trading_percentage", 50)
            return total_balance * (percentage / 100)
        else:
            fixed = self.config.get("capital.fixed_amount") or total_balance
            return min(fixed, total_balance)
    
    def _sync_positions_from_paper_trader(self) -> None:
        """Sync persisted positions from paper_trader to position_tracker on startup"""
        if not self.paper_trader or not self.position_tracker:
            return
        
        # Get positions from paper_trader (already loaded from JSON)
        paper_positions = self.paper_trader.get_positions()
        
        if not paper_positions:
            logger.info("📂 No positions to sync from paper_trader")
            return
        
        logger.info(f"🔄 Syncing {len(paper_positions)} position(s) from paper_trader to position_tracker")
        
        for pos in paper_positions:
            self.position_tracker.add_position(
                symbol=pos['symbol'],
                token=pos['token'],
                entry_price=pos['entry_price'],
                quantity=pos['quantity'],
                stop_loss=pos['stop_loss'],
                target=pos['target']
            )
            
            # Also add to selected_stocks so they get monitored
            if not any(s['symbol'] == pos['symbol'] for s in self.selected_stocks):
                self.selected_stocks.append({
                    'symbol': pos['symbol'],
                    'token': pos['token'],
                    'entry_price': pos['entry_price'],
                    'stop_loss': pos['stop_loss'],
                    'target_price': pos['target'],
                    'ltp': pos.get('current_price', pos['entry_price']),
                    'vwap': pos['entry_price'],  # Approximate
                    'rsi': 50,  # Neutral
                    'atr': 0,
                    'volume_ratio': 1.0
                })
        
        logger.success(f"✅ Synced {len(paper_positions)} position(s) - will be monitored on WebSocket connect")
        self._log_activity("SYNC", f"Restored {len(paper_positions)} persisted position(s)")

    # ==================== Market Analysis ====================
    
    def run_pre_market_analysis(self) -> List[Dict]:
        """
        Run pre-market analysis to select stocks for today.
        Called before market opens (e.g., 8:30 AM) or on late startup.
        """
        logger.info("=" * 60)
        logger.info("📊 MARKET ANALYSIS - STOCK SELECTION")
        logger.info("=" * 60)
        self._log_activity("ANALYSIS", "Starting market analysis")
        
        try:
            # Get all Nifty 50 stocks with their technical indicators
            logger.info("🔍 Analyzing Nifty 50 stocks...")
            analyzed_stocks = self.pre_market_analyzer.analyze_all_stocks()
            
            # Update market analysis for dashboard
            self.market_analysis["analyzed_at"] = now_ist().isoformat()
            self.market_analysis["total_stocks_analyzed"] = len(analyzed_stocks)
            
            # [FIX] Check if analysis returned no stocks (API failure scenario)
            if not analyzed_stocks or len(analyzed_stocks) == 0:
                error_msg = "Market analysis failed - No stocks could be analyzed. API rate limit or connection issue."
                logger.error(f"❌ {error_msg}")
                self._log_activity("ERROR", error_msg)
                self.market_analysis["trading_suitable"] = False
                self.market_analysis["reason"] = error_msg
                self.market_analysis["stocks"] = []
                self.selected_stocks = []
                return []
            
            # Score and rank stocks using the StockScorer
            logger.info("📊 Scoring and ranking stocks...")
            scored_stocks = self.stock_scorer.rank_stocks(analyzed_stocks)
            
            # Select top N stocks
            max_stocks = self.config.max_stocks
            self.selected_stocks = scored_stocks[:max_stocks]
            
            if self.selected_stocks:
                logger.info(f"✅ Found {len(scored_stocks)} stocks, selected top {len(self.selected_stocks)}")
                logger.info("")
                logger.info("=" * 60)
                logger.info("📋 SELECTED STOCKS FOR TRADING")
                logger.info("=" * 60)
                
                # Log selected stocks with detailed info
                for i, stock in enumerate(self.selected_stocks, 1):
                    # Calculate entry points for each stock
                    entry_info = self.strategy.calculate_entry_points(stock)
                    stock.update(entry_info)
                    
                    ltp = stock.get('ltp', stock.get('close', 0))
                    entry = stock.get('entry_price', ltp)
                    stop_loss = stock.get('stop_loss', 0)
                    target = stock.get('target_price', 0)
                    composite_score = stock.get('composite_score', 0)
                    
                    logger.info(f"")
                    logger.info(f"📌 STOCK #{i}: {stock['symbol']}")
                    logger.info(f"   ├─ Composite Score: {composite_score:.2f}")
                    logger.info(f"   ├─ LTP         : ₹{ltp:.2f}")
                    logger.info(f"   ├─ Entry Price : ₹{entry:.2f}")
                    sl_pct = abs(entry - stop_loss) / entry * 100 if entry > 0 else 0
                    target_pct = abs(target - entry) / entry * 100 if entry > 0 else 0
                    
                    logger.info(f"   ├─ Stop Loss   : ₹{stop_loss:.2f} ({sl_pct:.2f}%)")
                    logger.info(f"   └─ Target      : ₹{target:.2f} ({target_pct:.2f}%)")
                    
                    self._log_activity(
                        "SELECTION",
                        f"Selected {stock['symbol']} (Score: {composite_score:.1f}) - Entry: ₹{entry:.2f}, SL: ₹{stop_loss:.2f}, Target: ₹{target:.2f}",
                        {
                            "symbol": stock['symbol'],
                            "composite_score": composite_score,
                            "ltp": ltp,
                            "entry_price": entry,
                            "stop_loss": stop_loss,
                            "target_price": target
                        }
                    )
                    
                    # Seed LiveIndicatorManager with historical data for the selected stock
                    try:
                        hist_df = self.pre_market_analyzer.broker.get_historical_data(
                            symbol=stock['symbol'],
                            token=stock['token'],
                            interval="ONE_MINUTE",
                            days=1 # 1 day of 1-minute candles is ~375 candles, plenty for RSI
                        )
                        if hist_df:
                            from src.analysis.indicators import prepare_dataframe
                            df = prepare_dataframe(hist_df)
                            self.live_indicators.update(stock['symbol'], {'ltp': ltp}, df)
                            logger.info(f"   └─ Seeded live indicators with historical data")
                    except Exception as e:
                        logger.warning(f"   └─ Failed to seed live indicators: {e}")
                
                logger.info("")
                logger.info("=" * 60)
            else:
                logger.warning("⚠️ No stocks met the selection criteria")
            
            # Store analyzed stocks for dashboard
            self.market_analysis["stocks"] = [
                {
                    "symbol": s['symbol'],
                    "composite_score": s.get('composite_score', 0),
                    "volatility_score": s.get('volatility_score', 0),
                    "volume_score": s.get('volume_score', 0),
                    "trend_score": s.get('trend_score', 0),
                    "momentum_score": s.get('momentum_score', 0),
                    "rsi": s.get('rsi', 0),
                    "ltp": s.get('ltp', s.get('close', 0)),
                    "entry_price": s.get('entry_price', 0),
                    "stop_loss": s.get('stop_loss', 0),
                    "target_price": s.get('target_price', 0)
                }
                for s in self.selected_stocks
            ]
            
            self._log_activity(
                "ANALYSIS",
                f"Analysis complete. Analyzed {len(scored_stocks)} stocks, selected {len(self.selected_stocks)}."
            )
            
            return self.selected_stocks
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ Market analysis error: {e}")
            logger.debug(f"Full traceback:\n{error_details}")
            self._log_activity("ERROR", f"Market analysis failed: {str(e)}")
            
            # [FIX] Ensure dashboard shows proper error state
            self.market_analysis["analyzed_at"] = now_ist().isoformat()
            self.market_analysis["total_stocks_analyzed"] = 0
            self.market_analysis["trading_suitable"] = False
            self.market_analysis["reason"] = f"Analysis failed: {str(e)}"
            self.market_analysis["stocks"] = []
            self.selected_stocks = []
            return []
    
    # ==================== Trading Loop ====================
    
    def _on_price_update(self, symbol: str, price_data: Dict) -> None:
        """Callback for real-time price updates"""
        indicators = None
        try:
            current_price = float(price_data.get('ltp', 0))
            
            # Update position tracker
            self.position_tracker.update_price(symbol, current_price)
            
            # Check for entry signals (if not in position)
            if not self.position_tracker.has_position(symbol):
                stock_info = next(
                    (s for s in self.selected_stocks if s['symbol'] == symbol),
                    None
                )
                if stock_info:
                    # Check signal cooldown to prevent race condition
                    last_signal = self._last_signal_time.get(symbol)
                    if last_signal:
                        time_since_signal = (now_ist() - last_signal).total_seconds()
                        if time_since_signal < self._signal_cooldown_seconds:
                            return  # Skip - too soon after last signal
                    
                    # Get real-time dynamic indicators
                    indicators = self.live_indicators.update(symbol, price_data)
                    
                    # [CRITICAL] Safety check for indicators
                    if not isinstance(indicators, dict):
                        logger.error(f"❌ {symbol}: indicators is {type(indicators)} instead of dict. Content: {indicators}")
                        return
                        
                    # Update stock_info with latest indicators for dashboard/logging
                    try:
                        stock_info.update(indicators)
                    except Exception as e:
                        logger.debug(f"⚠️ {symbol}: Info update skipped: {e}")
                    
                    signal = self.strategy.check_entry_signal(stock_info, current_price, indicators)
                    can_trade, reason = self.risk_manager.can_trade()
                    
                    if signal and can_trade:
                        # [CRITICAL] Check if we already have a pending order for this symbol
                        with self._pending_lock:
                            is_pending = any(o['symbol'] == symbol for o in self.pending_orders.values())
                        
                        if is_pending:
                            logger.debug(f"⏳ Skipping entry for {symbol}: Order already pending")
                            return
                            
                        # [CRITICAL] Check exit cooldown
                        last_exit = self._last_exit_time.get(symbol)
                        if last_exit:
                            if (now_ist() - last_exit).total_seconds() < (self._exit_cooldown_minutes * 60):
                                logger.debug(f"⏳ Skipping entry for {symbol}: In exit cooldown")
                                return
                        
                        success = self._execute_entry(stock_info, signal)
                        if success:
                            self._last_signal_time[symbol] = now_ist()  # Only set cooldown on success
            
            # Check for exit signals (if in position)
            else:
                position = self.position_tracker.get_position(symbol)
                # Get indicators for exit check
                # Get real-time dynamic indicators for exit check
                indicators = self.live_indicators.update(symbol, price_data)
                
                if not isinstance(indicators, dict):
                    logger.error(f"❌ {symbol}: exit indicators is {type(indicators)}. Content: {indicators}")
                    return
                
                # Update stock_info if it exists for this symbol (optional but good for dashboard)
                # This ensures dashboard shows latest indicators for held positions too
                stock_info = next((s for s in self.selected_stocks if s['symbol'] == symbol), None)
                if stock_info:
                    try:
                        stock_info.update(indicators)
                    except: pass
                
                signal = self.strategy.check_exit_signal(position, current_price, indicators)
                if signal: 
                    self._execute_exit(position, signal, current_price)
                    
        except Exception as e: 
            import traceback
            err_msg = str(e)
            if "NoneType" in err_msg and "iterable" in err_msg:
                # Extra debug for the infamous NoneType error
                try:
                    logger.error(f"DETECTED NONETYPE ITERATION ERROR for {symbol}")
                    logger.error(f"Indicators: {indicators if 'indicators' in locals() else 'NOT DEFINED'}")
                    logger.error(f"Price Data: {price_data}")
                except: pass
            
            logger.error(f"Price update error for {symbol}: {e}\n{traceback.format_exc()}")
    
    def _execute_entry(self, stock: Dict, signal: Dict) -> bool:
        """Execute an entry order"""
        symbol = stock['symbol']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        target = signal['target']
        
        # Calculate quantity based on risk
        quantity = self.risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss
        )
        
        if quantity <= 0:
            logger.warning(f"⚠️ Cannot calculate position size for {symbol}")
            return False
        
        # Place order
        order_result = self.order_manager.place_buy_order(
            symbol=symbol,
            token=stock['token'],
            price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target
        )
        
        if order_result.get('status') == 'FILLED':
            # Track position immediately if filled
            self._add_to_tracker(symbol, stock, entry_price, quantity, stop_loss, target)
            return True
            
        elif order_result.get('status') == 'PLACED':
            # If only placed (limit order), track for polling
            order_id = order_result.get('order_id')
            if order_id:
                with self._pending_lock:
                    self.pending_orders[order_id] = {
                        'symbol': symbol,
                        'stock_info': stock,
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'stop_loss': stop_loss,
                        'target': target,
                        'placed_at': now_ist()
                    }
                logger.info(f"⏳ Order {order_id} PLACED - Waiting for fill...")
                return True
        
        return False
        
    def _add_to_tracker(self, symbol, stock, entry_price, quantity, stop_loss, target):
        """Helper to add a filled position to the tracker"""
        self.position_tracker.add_position(
            symbol=symbol,
            token=stock['token'],
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target
        )
        self.daily_stats['trades'] += 1
        
        self._log_activity(
            "TRADE",
            f"BUY {quantity} {symbol} @ ₹{entry_price:.2f}",
            {"stop_loss": stop_loss, "target": target}
        )

    def _poll_pending_orders(self) -> None:
        """Periodic task to check status of pending orders"""
        if not self.pending_orders:
            return
            
        logger.debug(f"🔍 Polling {len(self.pending_orders)} pending orders")
        
        with self._pending_lock:
            order_ids = list(self.pending_orders.keys())
            
        for order_id in order_ids:
            try:
                status_info = self.order_manager.get_order_status(order_id)
                if not status_info:
                    continue
                    
                status = status_info.get('status')
                
                if status == 'FILLED':
                    with self._pending_lock:
                        details = self.pending_orders.pop(order_id)
                        
                    logger.success(f"✅ Order {order_id} FILLED for {details['symbol']}")
                    self._add_to_tracker(
                        details['symbol'],
                        details['stock_info'],
                        details['entry_price'],
                        details['quantity'],
                        details['stop_loss'],
                        details['target']
                    )
                    
                elif status in ['REJECTED', 'CANCELLED']:
                    with self._pending_lock:
                        details = self.pending_orders.pop(order_id)
                    logger.warning(f"❌ Order {order_id} for {details['symbol']} was {status}")
                    self._log_activity("ORDER", f"Order {order_id} {status}", {"symbol": details['symbol']})
                    
                # Handle timeout (optional) - check within lock to avoid race condition
                else:
                    with self._pending_lock:
                        if order_id in self.pending_orders:
                            placed_at = self.pending_orders[order_id].get('placed_at')
                            if placed_at and (now_ist() - placed_at).total_seconds() > 300:  # 5 mins
                                details = self.pending_orders.pop(order_id)
                                logger.warning(f"⏰ Order {order_id} TIMEOUT - Removing from tracking")
                    
            except Exception as e:
                logger.error(f"Error polling order {order_id}: {e}")
        
        return None
    
    def _log_heartbeat(self) -> None:
        """Periodic heartbeat to show bot is alive"""
        mode = self.get_current_mode()
        positions_count = len(self.position_tracker.get_all_positions()) if self.position_tracker else 0
        
        status_emoji = {
            "TRADING": "🟢",
            "READY_TO_TRADE": "🟡",
            "WAITING_FOR_ANALYSIS": "🟠",
            "MONITORING_ONLY": "🔵",
            "MARKET_CLOSING": "🟣",
            "ANALYSIS_COMPLETE": "⚪",
            "NON_MARKET": "⚫"
        }
        
        emoji = status_emoji.get(mode, "⚪")
        logger.info(f"{emoji} Heartbeat: Bot is running | Mode: {mode} | Positions: {positions_count} | P&L: ₹{self.daily_stats.get('pnl', 0):+.2f}")
    
    def _execute_exit(self, position: Dict, signal: Dict, price: float) -> None:
        """Execute an exit order"""
        symbol = position['symbol']
        reason = signal['reason']
        
        order_result = self.order_manager.place_sell_order(
            symbol=symbol,
            token=position['token'],
            price=price,
            quantity=position['quantity'],
            reason=reason
        )
        
        if order_result.get('status') in ['FILLED', 'PLACED']:
            # Calculate P&L
            pnl = (price - position['entry_price']) * position['quantity']
            self.daily_stats['pnl'] += pnl
            
            if pnl >= 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1
                # Note: Do NOT call risk_manager.record_loss here as it would double-count
                # Risk manager tracks its own stats internally
            
            # Update risk manager with the trade result
            self.risk_manager.record_trade(pnl)
            
            # Remove from tracker
            self.position_tracker.remove_position(symbol, price, reason)
            
            self._log_activity(
                "TRADE",
                f"SELL {position['quantity']} {symbol} @ ₹{price:.2f} | P&L: ₹{pnl:+.2f}",
                {"reason": reason, "pnl": pnl}
            )
            
            # Set exit time for cooldown tracking
            self._last_exit_time[symbol] = now_ist()
    
    def square_off_all(self) -> None:
        """Square off all open positions (called at 3:15 PM)"""
        logger.info("🔴 Squaring off all positions...")
        self._log_activity("SYSTEM", "Initiating square off of all positions")
        
        positions = self.position_tracker.get_all_positions()
        
        for position in positions:
            # Get current price
            if self.angel_client:
                current_price = self.angel_client.get_ltp(
                    position['symbol'],
                    position['token']
                )
                if current_price:
                    self._execute_exit(
                        position,
                        {"reason": "SQUARE_OFF"},
                        current_price
                    )
        
        logger.info("✅ All positions squared off")
        self._log_activity("SYSTEM", "All positions squared off")
    
    # ==================== Bot Control ====================
    
    def start(self) -> bool:
        """Start the trading bot with smart startup based on current time"""
        if self.status == "RUNNING":
            logger.warning("⚠️ Bot is already running")
            return False
        
        if self.status != "READY":
            if not self.initialize():
                return False
        
        self.status = "RUNNING"
        self.start_time = now_ist()
        
        # Reset daily stats
        self.daily_stats = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        
        # Detect startup mode based on current time
        self._detect_startup_mode()
        
        # Setup daily schedule for future tasks
        self._setup_schedule()
        
        # Run startup actions based on mode
        self._execute_startup_actions()
        
        # Start scheduler for future scheduled tasks
        self.scheduler.start()
        
        return True
    
    def _detect_startup_mode(self) -> None:
        """Detect the startup mode based on current time"""
        now = now_ist_time()
        timing = self.config.get("timing", {})
        
        analysis_time = datetime.strptime(timing.get("analysis_start", "08:30"), "%H:%M").time()
        market_open = datetime.strptime(timing.get("trading_start", "09:15"), "%H:%M").time()
        no_new_trades = datetime.strptime(timing.get("no_new_trade_after", "15:00"), "%H:%M").time()
        market_close = datetime.strptime(timing.get("market_close", "15:30"), "%H:%M").time()
        
        if now < analysis_time:
            # Started before 8:30 AM - PRE_MARKET mode
            self.startup_mode = "PRE_MARKET"
            logger.info("=" * 60)
            logger.info("🌅 STARTUP MODE: PRE-MARKET")
            logger.info("=" * 60)
            logger.info(f"⏰ Current Time: {now.strftime('%H:%M:%S')}")
            logger.info(f"📋 Pre-market analysis will run at: {timing.get('analysis_start', '08:30')}")
            logger.info(f"📊 Trading will start at: {timing.get('trading_start', '09:15')}")
            logger.info("✅ Bot will follow normal schedule")
            self._log_activity("STARTUP", "Pre-market mode - Normal schedule", {
                "mode": "PRE_MARKET",
                "description": "Bot started before market. Will follow normal schedule."
            })
        
        elif now >= analysis_time and now < market_open:
            # Started between 8:30 AM and 9:15 AM - Run analysis now, wait for market
            self.startup_mode = "PRE_MARKET"
            logger.info("=" * 60)
            logger.info("🌅 STARTUP MODE: PRE-MARKET (Analysis Window)")
            logger.info("=" * 60)
            logger.info(f"⏰ Current Time: {now.strftime('%H:%M:%S')}")
            logger.info("📋 Running pre-market analysis now")
            logger.info(f"📊 Trading will start at: {timing.get('trading_start', '09:15')}")
            logger.info("✅ Scheduler will start trading at market open")
            self._log_activity("STARTUP", "Pre-market analysis mode - Trade at open", {
                "mode": "PRE_MARKET",
                "description": "Bot started during analysis window. Will analyze now, trade at market open."
            })
            
        elif now >= market_open and now <= no_new_trades:
            # Started during market hours (9:15 AM - 3:00 PM)
            self.startup_mode = "MARKET_HOURS"
            logger.info("=" * 60)
            logger.info("📈 STARTUP MODE: MARKET HOURS - ACTIVE TRADING")
            logger.info("=" * 60)
            logger.info(f"⏰ Current Time: {now.strftime('%H:%M:%S')}")
            logger.info("🔍 Will analyze market immediately and trade if suitable")
            logger.info(f"⏳ Trading allowed until: {timing.get('no_new_trade_after', '15:00')}")
            self._log_activity("STARTUP", "Market hours mode - Immediate analysis", {
                "mode": "MARKET_HOURS",
                "description": "Bot started during market hours. Analyzing immediately for trade opportunities."
            })
            
        elif now > no_new_trades and now <= market_close:
            # Started after 3:00 PM but before 3:30 PM - Late to trade
            self.startup_mode = "NON_MARKET"
            logger.info("=" * 60)
            logger.info("🌆 STARTUP MODE: NON-MARKET (Too Late)")
            logger.info("=" * 60)
            logger.info(f"⏰ Current Time: {now.strftime('%H:%M:%S')}")
            logger.info("⚠️ Too late for new trades today (after 3:00 PM)")
            logger.info("📊 Will analyze stocks for tomorrow's reference")
            self._log_activity("STARTUP", "Non-market mode - Analysis only", {
                "mode": "NON_MARKET",
                "description": "Too late for trading. Analyzing for reference only."
            })
            
        else:
            # Started outside market hours (before 8:30 AM or after 3:30 PM)
            self.startup_mode = "NON_MARKET"
            logger.info("=" * 60)
            logger.info("🌙 STARTUP MODE: NON-MARKET (Outside Hours)")
            logger.info("=" * 60)
            logger.info(f"⏰ Current Time: {now.strftime('%H:%M:%S')}")
            logger.info("📊 Market is closed. Will analyze stocks for reference")
            logger.info("❌ No trading will occur")
            self._log_activity("STARTUP", "Non-market mode - Analysis only", {
                "mode": "NON_MARKET",
                "description": "Market is closed. Running analysis for reference only."
            })
    
    def _execute_startup_actions(self) -> None:
        """Execute appropriate actions based on startup mode"""
        if self.startup_mode == "PRE_MARKET":
            # Check if we're in the analysis window (8:30-9:15)
            now = now_ist_time()
            timing = self.config.get("timing", {})
            analysis_time = datetime.strptime(timing.get("analysis_start", "08:30"), "%H:%M").time()
            market_open = datetime.strptime(timing.get("trading_start", "09:15"), "%H:%M").time()
            
            if now >= analysis_time and now < market_open:
                # In analysis window - run analysis now, scheduler will start trading at 9:15
                logger.success("🚀 Trading bot started in PRE-MARKET mode (Analysis Window)!")
                logger.info("🔍 Running pre-market analysis immediately...")
                self._log_activity("SYSTEM", "Running pre-market analysis - trading will start at market open")
                
                # Run analysis immediately
                self.run_pre_market_analysis()
                
                if self.selected_stocks:
                    logger.info("=" * 60)
                    logger.info("📊 ANALYSIS COMPLETE - WAITING FOR MARKET OPEN")
                    logger.info("=" * 60)
                    logger.info(f"✅ Found {len(self.selected_stocks)} stocks - Trading will start at {timing.get('trading_start', '09:15')}")
                    self._log_activity("ANALYSIS", f"Analysis complete. {len(self.selected_stocks)} stocks selected. Waiting for market open.")
                    self.market_analysis["trading_suitable"] = True
                    self.market_analysis["reason"] = f"Analysis complete. Trading will start at {timing.get('trading_start', '09:15')}"
                else:
                    logger.warning("⚠️ No suitable stocks found for trading")
                    self.market_analysis["trading_suitable"] = False
                    self.market_analysis["reason"] = "No stocks met selection criteria"
            else:
                # Before analysis time - just wait
                logger.success("🚀 Trading bot started in PRE-MARKET mode!")
                logger.info("📅 Waiting for scheduled tasks...")
                self._log_activity("SYSTEM", f"Bot ready - Waiting for scheduled analysis at {timing.get('analysis_start', '08:30')}")
            
        elif self.startup_mode == "MARKET_HOURS":
            logger.success("🚀 Trading bot started in MARKET HOURS mode!")
            logger.info("🔍 Running immediate market analysis...")
            self._log_activity("SYSTEM", "Starting immediate market analysis")
            
            # Run analysis immediately
            self.run_pre_market_analysis()
            
            # Check if trading is suitable
            if self.selected_stocks:
                logger.info("=" * 60)
                logger.info("📊 ANALYSIS COMPLETE - TRADING DECISION")
                logger.info("=" * 60)
                
                can_trade, reason = self.risk_manager.can_trade()
                
                if can_trade:
                    logger.success(f"✅ Trading conditions suitable! Monitoring {len(self.selected_stocks)} stocks")
                    self._log_activity("TRADING", f"Starting live monitoring for {len(self.selected_stocks)} stocks")
                    
                    # Start WebSocket monitoring
                    self._start_monitoring()
                    
                    self.market_analysis["trading_suitable"] = True
                    self.market_analysis["reason"] = "Market conditions and stock analysis favorable for trading"
                else:
                    logger.warning(f"⚠️ Trading not possible: {reason}")
                    self._log_activity("TRADING", f"Cannot trade: {reason}")
                    self.market_analysis["trading_suitable"] = False
                    self.market_analysis["reason"] = reason
            else:
                logger.warning("⚠️ No suitable stocks found for trading")
                self._log_activity("ANALYSIS", "No suitable stocks found for trading")
                self.market_analysis["trading_suitable"] = False
                self.market_analysis["reason"] = "No stocks met selection criteria"
                
        elif self.startup_mode == "NON_MARKET":
            logger.success("🚀 Trading bot started in NON-MARKET mode!")
            logger.info("🔍 Running analysis for reference only...")
            self._log_activity("SYSTEM", "Running analysis for reference (no trading)")
            
            # Run analysis but don't start monitoring
            self.run_pre_market_analysis()
            
            if self.selected_stocks:
                logger.info("=" * 60)
                logger.info("📊 ANALYSIS COMPLETE - REFERENCE ONLY")
                logger.info("=" * 60)
                logger.info(f"📋 Found {len(self.selected_stocks)} potential stocks for next session")
                self._log_activity("ANALYSIS", f"Reference analysis complete. {len(self.selected_stocks)} stocks identified for next session")
            else:
                logger.info("📊 No stocks met criteria during analysis")
                
            self.market_analysis["trading_suitable"] = False
            self.market_analysis["reason"] = "Non-market hours - Analysis for reference only"
            logger.info("❌ No trading will occur (market closed)")

    
    def _setup_schedule(self) -> None:
        """Setup daily trading schedule"""
        timing = self.config.get("timing", {})
        
        # Pre-market analysis
        self.scheduler.schedule_task(
            "pre_market_analysis",
            timing.get("analysis_start", "08:30"),
            self.run_pre_market_analysis
        )
        
        # Reset daily state just before market open
        self.scheduler.schedule_task(
            "daily_reset",
            "09:14",
            self._reset_daily_state
        )
        
        # Start monitoring at market open
        self.scheduler.schedule_task(
            "start_monitoring",
            timing.get("trading_start", "09:15"),
            self._start_monitoring
        )
        
        # Square off
        self.scheduler.schedule_task(
            "square_off",
            timing.get("square_off_time", "15:15"),
            self.square_off_all
        )
        
        # Daily report
        self.scheduler.schedule_task(
            "daily_report",
            timing.get("market_close", "15:30"),
            self._generate_daily_report
        )
        
        # Periodic polling for pending orders (every 10 seconds)
        self.scheduler.schedule_interval(
            "poll_pending_orders",
            10,
            self._poll_pending_orders
        )
        
        # Heartbeat log (every 5 minutes) to show bot is alive
        self.scheduler.schedule_interval(
            "heartbeat",
            300,  # 5 minutes
            self._log_heartbeat
        )
    
    def _reset_daily_state(self) -> None:
        """Reset daily state before market opens"""
        logger.info("🔄 Resetting daily state...")
        
        # Reset daily stats
        self.daily_stats = {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0
        }
        
        # Reset strategy state
        if self.strategy and hasattr(self.strategy, 'reset_daily'):
            self.strategy.reset_daily()
        
        # Reset risk manager
        if self.risk_manager:
            self.risk_manager.reset_daily()
        
        # Reset exit cooldown tracking
        self._last_exit_time.clear()
        
        # Reset live indicators for fresh cumulative VWAP
        if self.live_indicators:
            self.live_indicators.reset_all()
        
        self._log_activity("SYSTEM", "Daily state reset complete")
    
    def _start_monitoring(self) -> None:
        """Start WebSocket monitoring for selected stocks"""
        if not self.selected_stocks:
            logger.warning("⚠️ No stocks selected for monitoring")
            return
        
        # Update startup_mode to MARKET_HOURS since we're now actively trading
        if self.startup_mode != "MARKET_HOURS":
            logger.info("📈 Transitioning to MARKET_HOURS mode - Active trading begins")
            self.startup_mode = "MARKET_HOURS"
            self.market_analysis["trading_suitable"] = True
            self.market_analysis["reason"] = "Market open - Active trading in progress"
            self._log_activity("SYSTEM", "Transitioned to MARKET_HOURS mode")
        
        # Prepare tokens in correct format for WebSocket
        # WebSocket expects: [{'exchange_type': 1, 'token': '2885', 'symbol': 'RELIANCE-EQ'}]
        tokens = [
            {
                'exchange_type': 1,  # NSE
                'token': stock['token'],
                'symbol': stock['symbol']
            }
            for stock in self.selected_stocks
        ]
        
        # Use market_api_key for WebSocket
        self.websocket = AngelWebSocket(
            api_key=self.angel_client.market_api_key,
            client_id=self.angel_client.client_id,
            feed_token=self.angel_client.feed_token,
            auth_token=self.angel_client.auth_token
        )
        
        self.websocket.on_price_update = self._on_price_update
        self.websocket.subscribe(tokens)
        self.websocket.connect()
        
        logger.info(f"📡 WebSocket monitoring started for {len(tokens)} stocks")
        self._log_activity("TRADING", f"Active trading started - Monitoring {len(tokens)} stocks via WebSocket")
    
    def switch_strategy(self, strategy_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Switch to a different trading strategy at runtime.
        
        Safety Rules:
        - Cannot switch if positions are open (unless force=True)
        - Cannot switch to non-existent strategy
        - Will reset daily state on new strategy
        
        Args:
            strategy_name: Name of strategy to switch to
            force: If True, allows switching even with open positions (dangerous!)
            
        Returns:
            Dict with success status and message
        """
        result = {"success": False, "message": "", "previous": self.current_strategy_name}
        
        # Check if strategy exists
        if not StrategyRegistry.is_registered(strategy_name):
            available = ", ".join(StrategyRegistry.list_strategies())
            result["message"] = f"Unknown strategy: '{strategy_name}'. Available: {available}"
            logger.warning(f"⚠️ {result['message']}")
            return result
        
        # Check if same strategy
        if strategy_name == self.current_strategy_name:
            result["message"] = f"Already using strategy: {strategy_name}"
            result["success"] = True
            return result
        
        # Check for open positions
        if self.position_tracker:
            position_count = self.position_tracker.get_position_count()
            if position_count > 0 and not force:
                result["message"] = (
                    f"Cannot switch strategy with {position_count} open position(s). "
                    "Close positions first or use force=True (dangerous!)"
                )
                logger.warning(f"⚠️ {result['message']}")
                return result
            elif position_count > 0 and force:
                logger.warning(f"⚠️ Force-switching strategy with {position_count} open positions!")
        
        # Perform the switch
        try:
            old_strategy = self.current_strategy_name
            old_meta = StrategyRegistry.get_metadata(old_strategy)
            
            # Get new strategy instance (do not update current_strategy_name yet)
            self.strategy = StrategyRegistry.get_strategy(strategy_name)
            new_meta = StrategyRegistry.get_metadata(strategy_name)
            
            # Reset daily state on new strategy
            if hasattr(self.strategy, 'reset_daily'):
                self.strategy.reset_daily()
            
            # Update config before committing in-memory strategy name
            try:
                self.config.set('active_strategy', strategy_name)
            except Exception as config_error:
                # Attempt to roll back in-memory strategy to previous one
                logger.error(
                    f"❌ Failed to update active_strategy in config while switching from "
                    f"{old_strategy} to {strategy_name}: {config_error}"
                )
                try:
                    # Best-effort rollback to previous strategy
                    self.strategy = StrategyRegistry.get_strategy(old_strategy)
                except Exception as rollback_error:
                    logger.error(
                        f"❌ Failed to roll back to previous strategy {old_strategy}: {rollback_error}"
                    )
                raise config_error
            
            # At this point config is consistent; commit the in-memory strategy name
            self.current_strategy_name = strategy_name
            
            # Log the switch
            logger.success(
                f"✅ Strategy switched: {old_meta.get('display_name', old_strategy)} → "
                f"{new_meta.get('display_name', strategy_name)}"
            )
            self._log_activity(
                "STRATEGY", 
                f"Switched from {old_strategy} to {strategy_name}",
                {"old": old_strategy, "new": strategy_name}
            )
            
            result["success"] = True
            result["message"] = f"Successfully switched to {new_meta.get('display_name', strategy_name)}"
            result["new"] = strategy_name
            
            return result
            
        except Exception as e:
            result["message"] = f"Failed to switch strategy: {str(e)}"
            logger.error(f"❌ {result['message']}")
            return result
    
    def get_available_strategies(self) -> List[Dict]:
        """
        Get list of all available strategies with their metadata.
        
        Returns:
            List of strategy info dicts
        """
        strategies = StrategyRegistry.get_all_strategies_info()
        
        # Mark which one is active
        for s in strategies:
            s['is_active'] = (s['name'] == self.current_strategy_name)
        
        return strategies
    
    def get_strategy_params(self, strategy_name: str = None) -> Dict:
        """
        Get parameters for a strategy.
        
        Args:
            strategy_name: Strategy to get params for. If None, uses active strategy.
            
        Returns:
            Dict of strategy parameters
        """
        name = strategy_name or self.current_strategy_name
        
        # Get from config
        params = self.config.get(f'strategies.{name}.params', {})
        
        # Add metadata
        meta = StrategyRegistry.get_metadata(name)
        
        return {
            "name": name,
            "display_name": meta.get('display_name', name),
            "description": meta.get('description', ''),
            "params": params,
            "default_params": meta.get('default_params', {})
        }
    
    def update_strategy_params(self, strategy_name: str, params: Dict) -> bool:
        """
        Update parameters for a strategy.
        
        Args:
            strategy_name: Strategy to update
            params: New parameter values (will be merged with existing)
            
        Returns:
            True if successful
        """
        try:
            # Get current params
            current = self.config.get(f'strategies.{strategy_name}.params', {})
            
            # Merge new params
            current.update(params)
            
            # Save
            self.config.set(f'strategies.{strategy_name}.params', current)
            
            # If this is the active strategy, reinitialize it
            if strategy_name == self.current_strategy_name:
                self.strategy = StrategyRegistry.get_strategy(strategy_name)
                if hasattr(self.strategy, 'reset_daily'):
                    self.strategy.reset_daily()
            
            logger.info(f"📝 Updated params for {strategy_name}: {params}")
            self._log_activity("STRATEGY", f"Updated params for {strategy_name}", params)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update strategy params: {e}")
            return False
    
    def pause(self) -> bool:
        """Pause trading (keep monitoring but don't trade)"""
        if self.status != "RUNNING":
            logger.warning("⚠️ Bot is not running")
            return False
        
        self.status = "PAUSED"
        logger.info("⏸️ Trading bot paused")
        self._log_activity("SYSTEM", "Trading bot paused")
        return True
    
    def resume(self) -> bool:
        """Resume trading"""
        if self.status != "PAUSED":
            logger.warning("⚠️ Bot is not paused")
            return False
        
        self.status = "RUNNING"
        logger.info("▶️ Trading bot resumed")
        self._log_activity("SYSTEM", "Trading bot resumed")
        return True
    
    def stop(self) -> bool:
        """Stop the trading bot"""
        # Square off if any positions open
        if self.position_tracker and self.position_tracker.get_all_positions():
            self.square_off_all()
        
        # Stop scheduler
        self.scheduler.stop()
        
        # Disconnect WebSocket
        if self.websocket:
            self.websocket.disconnect()
        
        # Generate report
        self._generate_daily_report()
        
        self.status = "STOPPED"
        logger.info("⏹️ Trading bot stopped")
        self._log_activity("SYSTEM", "Trading bot stopped")
        
        return True
    
    def shutdown(self) -> None:
        """Complete shutdown of the bot"""
        self.stop()
        
        if self.angel_client:
            self.angel_client.logout()
        
        logger.info("👋 Trading bot shutdown complete")
    
    # ==================== Reports & Status ====================
    
    def _generate_daily_report(self) -> Dict:
        """Generate and save daily trading report"""
        report = {
            "date": now_ist().strftime("%Y-%m-%d"),
            "mode": self.config.trading_mode,
            "stats": self.daily_stats,
            "trades": self.order_manager.get_trades_today() if self.order_manager else [],
            "final_balance": self.get_account_info().get("total_balance", 0)
        }
        
        # Save to file
        filepath = Path(f"data/reports/{report['date']}.json")
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📋 Daily report saved to {filepath}")
        self._log_activity("REPORT", f"Daily report generated. P&L: ₹{self.daily_stats['pnl']:+.2f}")
        
        return report
    
    def get_status(self) -> Dict:
        """Get comprehensive bot status"""
        from datetime import datetime
        import platform
        
        # Get dynamic current mode for frontend
        current_mode = self.get_current_mode()
        
        # Determine if WebSocket is connected
        ws_connected = self.websocket is not None and hasattr(self.websocket, 'is_connected') and self.websocket.is_connected
        
        # Get current times for display
        ist_now = now_ist()
        server_now = datetime.now()  # Server's actual local time (no timezone conversion)
        
        # Try to detect server timezone
        try:
            import time
            if time.daylight:
                tz_offset = -time.altzone / 3600
                tz_name = time.tzname[1]
            else:
                tz_offset = -time.timezone / 3600
                tz_name = time.tzname[0]
        except:
            tz_offset = 0
            tz_name = "Unknown"
        
        return {
            "status": self.status,
            "startup_mode": self.startup_mode,
            "current_mode": current_mode,  # Dynamic real-time mode
            "is_actively_trading": ws_connected and self.scheduler.is_trading_hours(),
            "mode": self.config.trading_mode,
            "is_paper_mode": self.config.is_paper_mode,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "selected_stocks": self.selected_stocks,
            "market_analysis": self.market_analysis,
            "positions": self.position_tracker.get_all_positions() if self.position_tracker else [],
            "daily_stats": self.daily_stats,
            "account": self.get_account_info(),
            "strategy": {
                "active": self.current_strategy_name,
                "display_name": StrategyRegistry.get_metadata(self.current_strategy_name).get('display_name', self.current_strategy_name),
                "available": StrategyRegistry.list_strategies(),
                "can_switch": (self.position_tracker.get_position_count() == 0) if self.position_tracker else True
            },
            "server_time": {
                "ist": ist_now.strftime("%H:%M:%S"),
                "ist_date": ist_now.strftime("%Y-%m-%d"),
                "server": server_now.strftime("%H:%M:%S"),  # Actual server time
                "server_date": server_now.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "offset": f"UTC{tz_offset:+.1f}" if tz_offset != 0 else "UTC"
            },
            "config": {
                "max_stocks": self.config.max_stocks,
                "stop_loss": self.config.stop_loss_percent,
                "target": self.config.target_percent,
                "max_daily_loss": self.config.max_daily_loss_percent
            }
        }
    
    def get_account_info(self) -> Dict:
        """Get account balance information"""
        if self.config.is_paper_mode and self.paper_trader:
            summary = self.paper_trader.get_daily_summary()
            return {
                "total_balance": summary.get("current_balance", 0),
                "available_balance": summary.get("available_balance", 0),
                "used_margin": summary.get("current_balance", 0) - summary.get("available_balance", 0),
                "daily_pnl": summary.get("daily_pnl", 0)
            }
        
        if self.angel_client:
            funds = self.angel_client.get_funds()
            if funds:
                return {
                    "total_balance": float(funds.get("net", 0)),
                    "available_balance": float(funds.get("availablecash", 0)),
                    "used_margin": float(funds.get("utiliseddebits", 0)),
                    "daily_pnl": self.daily_stats.get("pnl", 0)
                }
        
        return {
            "total_balance": 0,
            "available_balance": 0,
            "used_margin": 0,
            "daily_pnl": 0
        }
    
    def switch_trading_mode(self, mode: str) -> bool:
        """Switch between paper and live trading mode"""
        if mode not in ["paper", "live"]:
            logger.error(f"❌ Invalid mode: {mode}")
            return False
        
        if self.status == "RUNNING":
            logger.error("❌ Cannot switch mode while bot is running. Stop the bot first.")
            return False
        
        self.config.trading_mode = mode
        
        # Reinitialize if needed
        if mode == "paper" and self.angel_client:
            balance = self.angel_client.get_available_balance()
            self.paper_trader = PaperTrader(initial_balance=balance)
        
        logger.info(f"✅ Switched to {mode.upper()} trading mode")
        self._log_activity("MODE", f"Switched to {mode.upper()} trading mode")
        
        return True
    
    def update_config(self, updates: Dict) -> bool:
        """Update configuration settings"""
        try:
            for key, value in updates.items():
                self.config.set(key, value)
            
            # Update strategy if relevant settings changed
            if self.strategy:
                self.strategy.stop_loss_percent = self.config.stop_loss_percent
                self.strategy.target_percent = self.config.target_percent
            
            logger.info(f"⚙️ Configuration updated: {updates}")
            self._log_activity("CONFIG", f"Configuration updated", updates)
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update config: {e}")
            return False