"""Main entry point for the Trading Bot"""

import sys
from pathlib import Path
from loguru import logger

# Ensure directories exist first
Path("logs").mkdir(exist_ok=True)
Path("data/daily").mkdir(parents=True, exist_ok=True)
Path("data/trades").mkdir(parents=True, exist_ok=True)
Path("data/reports").mkdir(parents=True, exist_ok=True)

# Import IST timezone utility for logging
from src.utils.timezone import IST

# Configure logging with IST timestamps
logger.remove()

# Custom time function for loguru to use IST
def ist_time_func(record, format_string):
    from datetime import datetime
    return datetime.now(IST).strftime(format_string)

logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)
logger.add(
    "logs/bot.log",
    rotation="1 day",
<<<<<<< Updated upstream
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
=======
    retention="3 days",
    format="{time:YYYY-MM-DD HH:mm:ss} IST | {level:<8} | {message}",
>>>>>>> Stashed changes
    level="DEBUG"
)

# Patch loguru's time to use IST
logger.configure(patcher=lambda record: record.update(time=ist_time_func(record, "%Y-%m-%d %H:%M:%S")))


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
            
            logger.info("Starting API server for dashboard...")
            
            # Start the API server for dashboard
            from src.api.server import set_trading_bot, run_server
            set_trading_bot(bot)
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