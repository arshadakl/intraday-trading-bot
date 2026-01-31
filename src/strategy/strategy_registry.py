"""Strategy Registry - Central registry for all trading strategies"""

from typing import Dict, Type, List, Optional, Callable
from loguru import logger

from .base_strategy import BaseStrategy


class StrategyRegistry:
    """
    Central registry for all trading strategies.
    
    Provides:
    - Strategy registration via decorator or method
    - Strategy lookup by name
    - List of all available strategies
    - Strategy metadata (display name, description, default params)
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _metadata: Dict[str, Dict] = {}
    _stock_pickers: Dict[str, str] = {}  # strategy_name -> picker_name
    
    @classmethod
    def register(
        cls,
        name: str,
        display_name: str = None,
        description: str = "",
        stock_picker: str = "default",
        default_params: Dict = None
    ) -> Callable:
        """
        Decorator to register a strategy class.
        
        Usage:
            @StrategyRegistry.register(
                name="vwap_rsi",
                display_name="VWAP + RSI Momentum",
                description="Price crosses VWAP with RSI confirmation",
                stock_picker="momentum"
            )
            class VWAPRSIStrategy(BaseStrategy):
                ...
        
        Args:
            name: Unique strategy identifier (used in config)
            display_name: Human-readable name for UI
            description: Strategy description
            stock_picker: Name of stock picker to use
            default_params: Default strategy parameters
        
        Returns:
            Decorator function
        """
        def decorator(strategy_class: Type[BaseStrategy]) -> Type[BaseStrategy]:
            cls._strategies[name] = strategy_class
            cls._metadata[name] = {
                "display_name": display_name or name.replace("_", " ").title(),
                "description": description,
                "default_params": default_params or {}
            }
            cls._stock_pickers[name] = stock_picker
            logger.debug(f"📝 Registered strategy: {name} ({display_name})")
            return strategy_class
        
        return decorator
    
    @classmethod
    def register_strategy(
        cls,
        name: str,
        strategy_class: Type[BaseStrategy],
        display_name: str = None,
        description: str = "",
        stock_picker: str = "default",
        default_params: Dict = None
    ) -> None:
        """
        Programmatically register a strategy class.
        
        Args:
            name: Unique strategy identifier
            strategy_class: Strategy class to register
            display_name: Human-readable name
            description: Strategy description
            stock_picker: Stock picker name
            default_params: Default parameters
        """
        cls._strategies[name] = strategy_class
        cls._metadata[name] = {
            "display_name": display_name or name.replace("_", " ").title(),
            "description": description,
            "default_params": default_params or {}
        }
        cls._stock_pickers[name] = stock_picker
        logger.info(f"📝 Registered strategy: {name}")
    
    @classmethod
    def get_strategy(cls, name: str) -> BaseStrategy:
        """
        Get an instance of a registered strategy.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If strategy not found
        """
        if name not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown strategy: '{name}'. Available: {available}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class()
    
    @classmethod
    def get_strategy_class(cls, name: str) -> Type[BaseStrategy]:
        """
        Get the class (not instance) of a registered strategy.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Strategy class
        """
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: '{name}'")
        return cls._strategies[name]
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        Get list of all registered strategy names.
        
        Returns:
            List of strategy identifiers
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def get_metadata(cls, name: str) -> Dict:
        """
        Get metadata for a strategy.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Dict with display_name, description, default_params
        """
        return cls._metadata.get(name, {})
    
    @classmethod
    def get_stock_picker(cls, name: str) -> str:
        """
        Get the stock picker name for a strategy.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Stock picker name
        """
        return cls._stock_pickers.get(name, "default")
    
    @classmethod
    def get_all_strategies_info(cls) -> List[Dict]:
        """
        Get information about all registered strategies.
        
        Returns:
            List of dicts with name, display_name, description
        """
        result = []
        for name in cls._strategies:
            meta = cls._metadata.get(name, {})
            result.append({
                "name": name,
                "display_name": meta.get("display_name", name),
                "description": meta.get("description", ""),
                "stock_picker": cls._stock_pickers.get(name, "default"),
                "default_params": meta.get("default_params", {})
            })
        return result
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a strategy is registered.
        
        Args:
            name: Strategy identifier
            
        Returns:
            True if registered
        """
        return name in cls._strategies
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered strategies. Useful for testing."""
        cls._strategies.clear()
        cls._metadata.clear()
        cls._stock_pickers.clear()
