"""Flask REST API Server for Dashboard"""

import os
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from loguru import logger
from typing import Optional

import numpy as np
import pandas as pd
from src.core.config_manager import get_config
from flask.json.provider import DefaultJSONProvider

def sanitize_for_json(obj):
    """
    Recursively sanitize data for JSON serialization.
    Converts NaN, Infinity to None, and numpy types to native Python types.
    """
    if obj is None:
        return None
    
    # Handle pandas NA/NaN/NaT
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    
    # Handle numpy types
    if isinstance(obj, (np.float64, np.float32, np.float16)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    if isinstance(obj, (np.uint64, np.uint32, np.uint16, np.uint8)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [sanitize_for_json(x) for x in obj.tolist()]
    
    # Handle Python float NaN/Infinity
    if isinstance(obj, float):
        if obj != obj or obj == float('inf') or obj == float('-inf'):  # NaN check: NaN != NaN
            return None
        return obj
    
    # Handle datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # Handle pandas Timestamp
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    
    # Recursively handle dicts
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    
    # Recursively handle lists/tuples
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(x) for x in obj]
    
    # Return as-is for other types (str, int, bool, etc.)
    return obj


class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider to handle numpy types and NaN values for trading/analysis data"""
    
    def dumps(self, obj, **kwargs):
        """Override dumps to sanitize data before serialization"""
        sanitized = sanitize_for_json(obj)
        return super().dumps(sanitized, **kwargs)
    
    def default(self, obj):
        """Fallback for any types not caught by sanitize_for_json"""
        try:
            if isinstance(obj, (np.float64, np.float32)):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return float(obj)
            if isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if pd.isna(obj):
                return None
        except:
            pass
        return super().default(obj)

# Try to import auth module (requires PyJWT)
# If not available, run without authentication
try:
    from src.api.auth import (
        require_auth, 
        request_auth_code, 
        verify_auth_code,
        verify_jwt_token
    )
    AUTH_ENABLED = True
    logger.info("🔐 Dashboard authentication enabled")
except ImportError as e:
    AUTH_ENABLED = False
    logger.warning(f"⚠️ Auth module import failed: {e}")
    logger.warning("   Install with: pip install PyJWT")
    
    # Create dummy decorators/functions when auth is disabled
    def require_auth(f):
        return f
    def request_auth_code():
        return {'success': False, 'error': 'Auth not available - install PyJWT'}, 503
    def verify_auth_code(code):
        return {'success': False, 'error': 'Auth not available - install PyJWT'}, 503
    def verify_jwt_token(token):
        return True, {'email': 'anonymous'}, 'Auth disabled'


# Global bot reference (will be set by run.py)
_trading_bot = None


def set_trading_bot(bot) -> None:
    """Set the trading bot instance for API access"""
    global _trading_bot
    _trading_bot = bot


def get_trading_bot():
    """Get the trading bot instance"""
    return _trading_bot


def create_app() -> Flask:
    """Create and configure Flask application"""
    
    # Create Flask app
    app = Flask(__name__, 
                static_folder='../../dashboard',
                static_url_path='/static')
    
    # Enable CORS
    CORS(app)
    
    # Use custom JSON provider to handle numpy types
    app.json = CustomJSONProvider(app)
    
    # ==================== Static Files ====================
    
    @app.route('/')
    def serve_dashboard():
        """Serve the main dashboard page (checks auth via JS)"""
        dashboard_path = os.path.join(os.path.dirname(__file__), '../../dashboard')
        return send_from_directory(dashboard_path, 'index.html')
    
    @app.route('/login')
    def serve_login():
        """Serve the login page"""
        dashboard_path = os.path.join(os.path.dirname(__file__), '../../dashboard')
        return send_from_directory(dashboard_path, 'login.html')
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files"""
        dashboard_path = os.path.join(os.path.dirname(__file__), '../../dashboard')
        return send_from_directory(dashboard_path, filename)
    
    # ==================== Authentication Endpoints ====================
    
    @app.route('/api/auth/request-code', methods=['POST'])
    def auth_request_code():
        """Request an authentication code (sent to configured email)"""
        result, status_code = request_auth_code()
        return jsonify(result), status_code
    
    @app.route('/api/auth/verify-code', methods=['POST'])
    def auth_verify_code():
        """Verify authentication code and get JWT token"""
        data = request.get_json() or {}
        code = data.get('code', '')
        result, status_code = verify_auth_code(code)
        return jsonify(result), status_code
    
    @app.route('/api/auth/validate', methods=['GET'])
    def auth_validate():
        """Check if current token is valid"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'valid': False}), 200
        
        token = auth_header[7:]
        valid, payload, message = verify_jwt_token(token)
        
        return jsonify({
            'valid': valid,
            'message': message,
            'email': payload.get('email') if payload else None
        }), 200
    
    # ==================== Helper Functions ====================
    
    def success_response(data=None, message=None):
        """Create a success response"""
        from src.utils.timezone import now_ist
        response = {
            'success': True,
            'timestamp': now_ist().isoformat()
        }
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)
    
    def error_response(error, code="ERROR"):
        """Create an error response"""
        from src.utils.timezone import now_ist
        return jsonify({
            'success': False,
            'error': error,
            'code': code,
            'timestamp': now_ist().isoformat()
        }), 400
    
    def get_bot():
        """Get trading bot or return error"""
        bot = get_trading_bot()
        if bot is None:
            return None, error_response("Trading bot not initialized", "BOT_NOT_READY")
        return bot, None
    
    # ==================== Status & Info ====================
    
    @app.route('/api/status')
    @require_auth
    def get_status():
        """Get complete bot status"""
        bot, err = get_bot()
        if err:
            return err
        
        return success_response(bot.get_status())
    
    @app.route('/api/account')
    @require_auth
    def get_account():
        """Get account balance information"""
        bot, err = get_bot()
        if err:
            return err
        
        return success_response(bot.get_account_info())
    
    @app.route('/api/logs')
    @require_auth
    def get_logs():
        """Get recent activity logs"""
        bot, err = get_bot()
        if err:
            return err
        
        limit = request.args.get('limit', 50, type=int)
        logs = bot.get_activity_log(limit)
        
        return success_response({'logs': logs})
    
    # ==================== Configuration ====================
    
    @app.route('/api/config', methods=['GET'])
    @require_auth
    def get_config_endpoint():
        """Get current configuration"""
        config = get_config()
        return success_response(config.get_all())
    
    @app.route('/api/config', methods=['POST'])
    @require_auth
    def update_config():
        """Update configuration values"""
        try:
            config = get_config()
            updates = request.get_json()
            
            if not updates:
                return error_response("No update data provided")
            
            updated_keys = []
            for key, value in updates.items():
                config.set(key, value, save=False)
                updated_keys.append(key)
            
            config.save()
            
            # Update bot if running
            bot = get_trading_bot()
            if bot:
                bot.update_config(updates)
            
            return success_response({
                'updated_keys': updated_keys
            }, "Configuration updated")
            
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/mode', methods=['POST'])
    @require_auth
    def switch_mode():
        """Switch trading mode (paper/live)"""
        try:
            data = request.get_json()
            mode = data.get('mode', 'paper')
            
            if mode not in ['paper', 'live']:
                return error_response("Mode must be 'paper' or 'live'")
            
            bot, err = get_bot()
            if err:
                return err
            
            bot.switch_trading_mode(mode)
            
            warning = None
            if mode == 'live':
                warning = "⚠️ Real money will be used for trading"
            
            response_data = {'mode': mode}
            if warning:
                response_data['warning'] = warning
            
            return success_response(response_data, f"Switched to {mode.upper()} trading mode")
            
        except Exception as e:
            return error_response(str(e))
    
    # ==================== Strategy Management ====================
    
    @app.route('/api/strategies', methods=['GET'])
    @require_auth
    def list_strategies():
        """List all available trading strategies"""
        try:
            bot, err = get_bot()
            if err:
                # Return basic strategy info even if bot not running
                # Import strategies to trigger registration via decorators
                from src.strategy.strategy_registry import StrategyRegistry
                from src.strategy.vwap_rsi_strategy import VWAPRSIStrategy  # noqa: F401
                from src.strategy.ohl_strategy import OHLStrategy  # noqa: F401
                strategies = StrategyRegistry.get_all_strategies_info()
                return success_response({
                    'strategies': strategies,
                    'active': None,
                    'can_switch': False
                })
            
            strategies = bot.get_available_strategies()
            can_switch = bot.position_tracker.get_position_count() == 0 if bot.position_tracker else True
            
            return success_response({
                'strategies': strategies,
                'active': bot.current_strategy_name,
                'can_switch': can_switch
            })
            
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/strategy/active', methods=['GET'])
    @require_auth
    def get_active_strategy():
        """Get current active strategy info"""
        try:
            bot, err = get_bot()
            if err:
                return err
            
            strategy_info = bot.get_strategy_params()
            strategy_info['can_switch'] = (
                bot.position_tracker.get_position_count() == 0 
                if bot.position_tracker else True
            )
            
            return success_response(strategy_info)
            
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/strategy/switch', methods=['POST'])
    @require_auth
    def switch_strategy():
        """Switch to a different trading strategy"""
        try:
            bot, err = get_bot()
            if err:
                return err
            
            data = request.get_json()
            strategy_name = data.get('strategy')
            force = data.get('force', False)
            repick_stocks = data.get('repick_stocks', True)  # Default to repick
            
            if not strategy_name:
                return error_response("Strategy name is required")
            
            result = bot.switch_strategy(strategy_name, force=force, repick_stocks=repick_stocks)
            
            if result['success']:
                response_data = {
                    'active': result.get('new', strategy_name),
                    'previous': result.get('previous')
                }
                # Include stock repicking info if available
                if result.get('stocks_repicked'):
                    response_data['stocks_repicked'] = True
                    response_data['new_stocks'] = result.get('new_stocks', [])
                elif 'repick_error' in result:
                    response_data['stocks_repicked'] = False
                    response_data['repick_error'] = result.get('repick_error')
                    
                return success_response(response_data, result['message'])
            else:
                return error_response(result['message'])
            
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/strategy/<strategy_name>/params', methods=['GET'])
    @require_auth
    def get_strategy_params(strategy_name):
        """Get parameters for a specific strategy"""
        try:
            bot, err = get_bot()
            if err:
                return err
            
            params = bot.get_strategy_params(strategy_name)
            return success_response(params)
            
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/strategy/<strategy_name>/params', methods=['POST'])
    @require_auth
    def update_strategy_params(strategy_name):
        """Update parameters for a specific strategy"""
        try:
            bot, err = get_bot()
            if err:
                return err
            
            data = request.get_json()
            if not data:
                return error_response("No parameters provided")
            
            success = bot.update_strategy_params(strategy_name, data)
            
            if success:
                return success_response(
                    {'strategy': strategy_name, 'updated': data},
                    f"Updated {strategy_name} parameters"
                )
            else:
                return error_response("Failed to update parameters")
            
        except Exception as e:
            return error_response(str(e))
    
    # ==================== Trading Data ====================
    
    @app.route('/api/stocks/selected')
    @require_auth
    def get_selected_stocks():
        """Get today's selected stocks"""
        bot, err = get_bot()
        if err:
            return err
        
        stocks = bot.selected_stocks if hasattr(bot, 'selected_stocks') else []
        
        from src.utils.timezone import now_ist
        return success_response({
            'date': now_ist().strftime('%Y-%m-%d'),
            'stocks': stocks
        })
    
    @app.route('/api/positions')
    @require_auth
    def get_positions():
        """Get open positions"""
        bot, err = get_bot()
        if err:
            return err
        
        if hasattr(bot, 'position_tracker'):
            summary = bot.position_tracker.get_position_summary()
            return success_response(summary)
        
        return success_response({
            'open_count': 0,
            'positions': [],
            'unrealized_pnl': 0
        })
    
    @app.route('/api/trades/today')
    @require_auth
    def get_trades_today():
        """Get today's completed trades"""
        bot, err = get_bot()
        if err:
            return err
        
        trades = []
        summary = {'total_trades': 0, 'total_pnl': 0, 'win_rate': 0}
        
        if hasattr(bot, 'order_manager'):
            trades = bot.order_manager.get_trades_today()
        
        if hasattr(bot, 'risk_manager'):
            stats = bot.risk_manager.get_daily_stats()
            summary = {
                'total_trades': stats['trades'],
                'total_pnl': stats['pnl'],
                'win_rate': stats['win_rate']
            }
        
        from src.utils.timezone import now_ist
        return success_response({
            'date': now_ist().strftime('%Y-%m-%d'),
            'trades': trades,
            'summary': summary
        })
    
    # ==================== Bot Control ====================
    
    @app.route('/api/bot/start', methods=['POST'])
    @require_auth
    def start_bot():
        """Start the trading bot"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            bot.start()
            from src.utils.timezone import now_ist
            return success_response({
                'status': bot.status,
                'start_time': now_ist().isoformat()
            }, "Trading bot started")
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/bot/pause', methods=['POST'])
    @require_auth
    def pause_bot():
        """Pause trading"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            bot.pause()
            return success_response({
                'status': bot.status
            }, "Trading paused")
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/bot/resume', methods=['POST'])
    @require_auth
    def resume_bot():
        """Resume trading"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            bot.resume()
            return success_response({
                'status': bot.status
            }, "Trading resumed")
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/bot/stop', methods=['POST'])
    @require_auth
    def stop_bot():
        """Stop the trading bot"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            # Square off all positions
            bot.square_off_all()
            bot.stop()
            
            final_pnl = 0
            if hasattr(bot, 'risk_manager'):
                final_pnl = bot.risk_manager.get_daily_pnl()
            
            return success_response({
                'status': bot.status,
                'final_pnl': final_pnl
            }, "Trading bot stopped")
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/position/exit', methods=['POST'])
    @require_auth
    def exit_position():
        """Exit a specific position manually"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            data = request.get_json()
            symbol = data.get('symbol')
            
            if not symbol:
                return error_response("Symbol is required")
            
            # TODO: Implement position exit
            return success_response({
                'symbol': symbol,
                'status': 'EXIT_REQUESTED'
            }, f"Exit requested for {symbol}")
            
        except Exception as e:
            return error_response(str(e))
    
    # ==================== Log File & Reports ====================
    
    @app.route('/api/logs/file')
    @require_auth
    def get_log_file():
        """Get the last N lines of the log file"""
        from pathlib import Path
        
        lines = request.args.get('lines', 200, type=int)
        lines = min(lines, 1000)  # Cap at 1000 lines for performance
        
        log_path = Path("logs/bot.log")
        if not log_path.exists():
            return error_response("Log file not found", "FILE_NOT_FOUND")
        
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:]
            
            return success_response({
                'lines': [line.rstrip() for line in tail_lines],
                'total': len(tail_lines),
                'file': str(log_path)
            })
        except Exception as e:
            return error_response(f"Error reading log file: {e}")
    
    @app.route('/api/reports')
    @require_auth
    def get_reports_list():
        """Get list of available daily reports"""
        from pathlib import Path
        import json
        
        reports_dir = Path("data/reports")
        if not reports_dir.exists():
            return success_response({'reports': []})
        
        reports = []
        for file in sorted(reports_dir.glob("*.json"), reverse=True):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                reports.append({
                    'date': file.stem,
                    'filename': file.name,
                    'trades': data.get('stats', {}).get('trades', 0),
                    'pnl': data.get('stats', {}).get('pnl', 0)
                })
            except:
                reports.append({'date': file.stem, 'filename': file.name, 'trades': 0, 'pnl': 0})
        
        return success_response({'reports': reports})
    
    @app.route('/api/reports/<date>')
    @require_auth
    def get_report_by_date(date):
        """Get detailed report for a specific date"""
        from pathlib import Path
        import json
        
        report_path = Path(f"data/reports/{date}.json")
        if not report_path.exists():
            return error_response(f"Report for {date} not found", "NOT_FOUND")
        
        try:
            with open(report_path, "r") as f:
                data = json.load(f)
            return success_response(data)
        except Exception as e:
            return error_response(f"Error reading report: {e}")
    
    # ==================== Health Check ====================
    
    @app.route('/api/health')
    def health_check():
        """API health check"""
        return success_response({
            'status': 'healthy',
            'bot_initialized': get_trading_bot() is not None
        })
    
    return app


def run_server(host: str = None, port: int = 5000, debug: bool = False):
    """
    Run the Flask server.
    
    Args:
        host: Host to bind to. Defaults to:
              - '0.0.0.0' (public) if DASHBOARD_PUBLIC=true in env
              - '127.0.0.1' (local only) otherwise
        port: Port number (default 5000)
        debug: Enable debug mode
    """
    import os
    import logging
    
    # Suppress Flask's default logging to console to reduce noise
    if not debug:
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    
    # Allow public access if DASHBOARD_PUBLIC=true or host explicitly set to 0.0.0.0
    if host is None:
        is_public = os.environ.get('DASHBOARD_PUBLIC', 'false').lower() == 'true'
        host = '0.0.0.0' if is_public else '127.0.0.1'
    
    app = create_app()
    
    logger.info("="*60)
    if host == '0.0.0.0':
        logger.info(f"🌐 API server starting at http://0.0.0.0:{port} (PUBLIC ACCESS)")
        logger.info(f"📊 Dashboard accessible from any device on your network")
    else:
        logger.info(f"🌐 API server starting at http://{host}:{port}")
        logger.info(f"📊 Dashboard: http://{host}:{port}/")
    logger.info("="*60)
    logger.info("✅ Bot is now running. Logs are being written to logs/bot.log")
    logger.info("💡 Press Ctrl+C to stop the bot gracefully")
    logger.info("="*60)
    
    # IMPORTANT: use_reloader=False is intentional for trading bots
    # - Prevents unexpected restarts that could cause missed trades or duplicate orders
    # - Preserves bot state (positions, WebSocket connections, order tracking)
    # - For code changes, manually restart the server
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == '__main__':
    run_server(debug=True)
