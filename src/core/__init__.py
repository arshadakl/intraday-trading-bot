"""Core module - Bot orchestration and configuration"""

from . config_manager import ConfigManager, get_config
from .bot import TradingBot
from .scheduler import TradingScheduler