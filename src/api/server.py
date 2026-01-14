"""Flask REST API Server for Dashboard"""

import os
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from loguru import logger
from typing import Optional

from src.core.config_manager import get_config


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
    
    # ==================== Static Files ====================
    
    @app.route('/')
    def serve_dashboard():
        """Serve the main dashboard page"""
        dashboard_path = os.path.join(os.path.dirname(__file__), '../../dashboard')
        return send_from_directory(dashboard_path, 'index.html')
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files"""
        dashboard_path = os.path.join(os.path.dirname(__file__), '../../dashboard')
        return send_from_directory(dashboard_path, filename)
    
    # ==================== Helper Functions ====================
    
    def success_response(data=None, message=None):
        """Create a success response"""
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)
    
    def error_response(error, code="ERROR"):
        """Create an error response"""
        return jsonify({
            'success': False,
            'error': error,
            'code': code,
            'timestamp': datetime.now().isoformat()
        }), 400
    
    def get_bot():
        """Get trading bot or return error"""
        bot = get_trading_bot()
        if bot is None:
            return None, error_response("Trading bot not initialized", "BOT_NOT_READY")
        return bot, None
    
    # ==================== Status & Info ====================
    
    @app.route('/api/status')
    def get_status():
        """Get complete bot status"""
        bot, err = get_bot()
        if err:
            return err
        
        return success_response(bot.get_status())
    
    @app.route('/api/account')
    def get_account():
        """Get account balance information"""
        bot, err = get_bot()
        if err:
            return err
        
        return success_response(bot.get_account_info())
    
    @app.route('/api/logs')
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
    def get_config_endpoint():
        """Get current configuration"""
        config = get_config()
        return success_response(config.get_all())
    
    @app.route('/api/config', methods=['POST'])
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
    
    # ==================== Trading Data ====================
    
    @app.route('/api/stocks/selected')
    def get_selected_stocks():
        """Get today's selected stocks"""
        bot, err = get_bot()
        if err:
            return err
        
        stocks = bot.selected_stocks if hasattr(bot, 'selected_stocks') else []
        
        return success_response({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'stocks': stocks
        })
    
    @app.route('/api/positions')
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
        
        return success_response({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trades': trades,
            'summary': summary
        })
    
    # ==================== Bot Control ====================
    
    @app.route('/api/bot/start', methods=['POST'])
    def start_bot():
        """Start the trading bot"""
        bot, err = get_bot()
        if err:
            return err
        
        try:
            bot.start()
            return success_response({
                'status': bot.status,
                'start_time': datetime.now().isoformat()
            }, "Trading bot started")
        except Exception as e:
            return error_response(str(e))
    
    @app.route('/api/bot/pause', methods=['POST'])
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
    
    # ==================== Health Check ====================
    
    @app.route('/api/health')
    def health_check():
        """API health check"""
        return success_response({
            'status': 'healthy',
            'bot_initialized': get_trading_bot() is not None
        })
    
    return app


def run_server(host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask server"""
    app = create_app()
    
    logger.info(f"🌐 Starting API server at http://{host}:{port}")
    logger.info(f"📊 Dashboard available at http://{host}:{port}/")
    
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_server(debug=True)
