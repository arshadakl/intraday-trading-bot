"""Configuration Manager - Load, save, and manage all settings"""

import json
import os
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from config.defaults import DEFAULT_CONFIG


class ConfigManager:
    """Manages all bot configurations with easy access methods"""
    
    def __init__(self, config_path: str = "config/settings. json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"✅ Configuration loaded from {self.config_path}")
                    return self._merge_with_defaults(config)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error reading config file: {e}")
                return DEFAULT_CONFIG. copy()
        else:
            logger.warning(f"⚠️ Config file not found, creating default at {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, config: dict) -> dict:
        """Merge loaded config with defaults to ensure all keys exist"""
        merged = DEFAULT_CONFIG.copy()
        
        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(merged, config)
    
    def _save_config(self, config: dict) -> None:
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"💾 Configuration saved to {self. config_path}")
    
    def save(self) -> None:
        """Save current configuration"""
        self._save_config(self.config)
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("🔄 Configuration reloaded")
    
    def get(self, key: str, default:  Any = None) -> Any:
        """
        Get a configuration value using dot notation
        Example: config.get('strategy.stop_loss_percent')
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a configuration value using dot notation
        Example:  config.set('strategy.stop_loss_percent', 0.75)
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        
        if save:
            self. save()
        logger.info(f"⚙️ Config updated: {key} = {value}")
    
    def get_all(self) -> dict:
        """Get all configurations"""
        return self.config. copy()
    
    def update_multiple(self, updates: dict) -> None:
        """Update multiple configuration values at once"""
        for key, value in updates.items():
            self.set(key, value, save=False)
        self.save()
    
    # ==================== Convenience Properties ====================
    
    @property
    def is_paper_mode(self) -> bool:
        """Check if running in paper trading mode"""
        return self.config.get("trading_mode", "paper") == "paper"
    
    @property
    def trading_mode(self) -> str:
        """Get current trading mode"""
        return self.config.get("trading_mode", "paper")
    
    @trading_mode.setter
    def trading_mode(self, mode: str) -> None:
        """Set trading mode (paper/live)"""
        if mode not in ["paper", "live"]: 
            raise ValueError("Trading mode must be 'paper' or 'live'")
        self.set("trading_mode", mode)
    
    @property
    def max_stocks(self) -> int:
        """Get maximum stocks to trade"""
        return self.get("stock_selection. max_stocks", 2)
    
    @property
    def stop_loss_percent(self) -> float:
        """Get stop loss percentage"""
        return self.get("strategy.stop_loss_percent", 0.5)
    
    @property
    def target_percent(self) -> float:
        """Get target percentage"""
        return self.get("strategy. target_percent", 1.0)
    
    @property
    def max_daily_loss_percent(self) -> float:
        """Get maximum daily loss percentage"""
        return self. get("risk.max_daily_loss_percent", 2.0)
    
    @property
    def max_trades_per_day(self) -> int:
        """Get maximum trades per day"""
        return self. get("strategy.max_trades_per_day", 3)


# ==================== Singleton Instance ====================

_config_manager:  Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config() -> ConfigManager:
    """Reload and return the configuration manager"""
    global _config_manager
    if _config_manager is not None:
        _config_manager.reload()
    else:
        _config_manager = ConfigManager()
    return _config_manager