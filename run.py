import os
import sys
import signal
import atexit
from pathlib import Path
from loguru import logger

# Configuration
PID_FILE = Path("logs/bot.pid")

def setup_single_instance():
    """Ensure only one instance of the bot is running."""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            
            # Check if the process is actually running
            is_running = False
            if os.name == 'nt':
                # Windows-specific reliable check
                import subprocess
                try:
                    # Add timeout to prevent hanging if tasklist is unresponsive
                    output = subprocess.check_output(
                        ['tasklist', '/FI', f'PID eq {old_pid}', '/NH'],
                        creationflags=0x08000000,
                        stderr=subprocess.DEVNULL,
                        timeout=5  # 5 seconds timeout
                    ).decode('utf-8', errors='ignore')
                    is_running = str(old_pid) in output
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️ PID check timed out for {old_pid}. Assuming process is not running.")
                    is_running = False
                except Exception as e:
                    logger.warning(f"⚠️ PID check failed: {e}. Assuming process is not running.")
                    is_running = False
            else:
                # Unix-specific reliable check
                try:
                    os.kill(old_pid, 0)
                    is_running = True
                except (OSError, ProcessLookupError):
                    is_running = False

            if is_running:
                logger.error(f"⚠️ Bot is already running (PID: {old_pid}). Exiting to prevent duplicate trades.")
                sys.exit(1)
            else:
                logger.info("Found stale PID file, taking over...")
        except Exception as e:
            logger.debug(f"PID check error: {e}")
            pass

    # Write current PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # Register cleanup
    atexit.register(lambda: PID_FILE.unlink(missing_ok=True))

# Ensure directories exist first
Path("logs").mkdir(exist_ok=True)
setup_single_instance()
Path("data/daily").mkdir(parents=True, exist_ok=True)
Path("data/trades").mkdir(parents=True, exist_ok=True)
Path("data/reports").mkdir(parents=True, exist_ok=True)


# Configure logging with IST timezone
from src.utils.timezone import now_ist, now_ist_time

logger.remove()

# Custom format function for IST timestamps
def format_ist_time(record):
    """Format log time in IST"""
    ist_now = now_ist()
    record["extra"]["ist_time"] = ist_now.strftime("%Y-%m-%d %H:%M:%S")
    record["extra"]["ist_time_short"] = ist_now.strftime("%H:%M:%S")
    return True

logger.add(
    sys.stdout,
    format="<green>{extra[ist_time_short]}</green> | <level>{level:<8}</level> | <cyan>{message}</cyan>",
    level="INFO",
    filter=format_ist_time
)
logger.add(
    "logs/bot.log",
    rotation="1 day",
    retention="7 days",
    format="{extra[ist_time]} IST | {level:<8} | {message}",
    level="DEBUG",
    filter=format_ist_time
)


def main():
    """Main function"""
    from src.core.bot import TradingBot
    from src.core.config_manager import get_config
    
    logger.info("=" * 50)
    logger.info("  INTRADAY TRADING BOT")
    logger.info("=" * 50)
    
    # Load config
    config = get_config()
    logger.info(f"Trading Mode: {config.trading_mode.upper()}")
    logger.info(f"Max Stocks: {config.max_stocks}")
    logger.info(f"Stop Loss: {config.stop_loss_percent}%")
    logger.info(f"Target: {config.target_percent}%")
    
    # Initialize bot
    bot = TradingBot()
    
    try:
        if bot.initialize():
            logger.success("Bot initialized successfully!")
            
            # Get status
            status = bot.get_status()
            balance = status.get('account', {}).get('available_balance', 0)
            logger.info(f"Account Balance: Rs.{balance:,.2f}")
            
            # Auto-start the bot (this triggers startup mode detection and analysis)
            logger.info("Auto-starting bot with smart startup logic...")
            if bot.start():
                logger.success(f"Bot started in {bot.startup_mode} mode")
            
            # Start the API server for dashboard (this will block)
            from src.api.server import set_trading_bot, run_server
            set_trading_bot(bot)
            
            logger.info("")
            logger.info("="*60)
            logger.info("🚀 TRADING BOT IS READY")
            logger.info("="*60)
            logger.info(f"Status: {bot.get_current_mode()}")
            logger.info(f"Mode: {bot.startup_mode}")
            # Safely check stocks count
            stocks = getattr(bot, "selected_stocks", None)
            try:
                stock_count = len(stocks) if stocks is not None else 0
            except TypeError:
                stock_count = 0
            logger.info(f"Stocks: {stock_count} stocks ready")
            logger.info("="*60)
            logger.info("")
            
            # This will block and keep the bot running
            run_server()
            
        else:
            logger.error("Failed to initialize bot")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot.shutdown()
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()