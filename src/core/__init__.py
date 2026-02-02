"""Core module - Bot orchestration and configuration"""

# Only import config_manager at package level to avoid circular imports
# Import TradingBot and TradingScheduler directly from their modules when needed:
#   from src.core.bot import TradingBot
#   from src.core.scheduler import TradingScheduler
from .config_manager import ConfigManager, get_config

__all__ = ['ConfigManager', 'get_config']