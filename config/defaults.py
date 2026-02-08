"""Default configuration values"""

DEFAULT_CONFIG = {
    "trading_mode": "paper",
    
    "capital": {
        "use_percentage": True,
        "trading_percentage": 50,
        "fixed_amount": None,
        "per_trade_percentage": 25,
        "per_trade_fixed": None
    },
    
    "stock_selection": {
        "max_stocks": 2,
        "universe": "nifty50",
        "min_volume":  1000000,
        "min_price": 100,
        "max_price": 5000
    },
    
    # Active strategy (can be switched at runtime)
    "active_strategy": "three_minute",
    
    # Multi-strategy configuration
    "strategies": {
        "vwap_rsi": {
            "enabled": False,  # Disabled - focusing on 3-minute strategy
            "display_name": "VWAP + RSI Momentum",
            "description": "Price crosses VWAP with RSI confirmation for momentum entries",
            "stock_picker": "momentum",
            "params": {
                "stop_loss_percent": 0.5,
                "stop_loss_max": 0.75,
                "target_percent": 1.0,
                "target_max": 1.5,
                "trailing_stop_loss": False,
                "max_trades_per_day": 3,
                "rsi_oversold": 40,
                "rsi_overbought": 70,
                "consolidation_threshold": 0.005,
                "volume_breakout_threshold": 1.5,
                "use_pivot_confluence": True,
                "require_pivot_confluence": False
            }
        },
        "ohl": {
            "enabled": False,  # Disabled - focusing on 3-minute strategy
            "display_name": "OHL (Open=High/Low)",
            "description": "Trade based on first candle Open=High (bearish) or Open=Low (bullish) pattern",
            "stock_picker": "ohl",
            "params": {
                "stop_loss_percent": 1.0,
                "target_percent": 1.5,
                "buffer_percent": 0.06,
                "entry_window_start": "09:30",
                "entry_window_end": "09:45",
                "require_nifty_alignment": True,
                "use_range_breakout": True,
                "range_period_minutes": 15,
                "use_10min_sl": True,
                "risk_reward_ratio": 1.5,
                "max_sl_percent": 2.0,
                "max_trades_per_day": 3
            }
        },
        "three_minute": {
            "enabled": True,
            "display_name": "3-Minute Strategy (Pre-Open Gap)",
            "description": "Trade gap-up/gap-down stocks identified from NSE pre-open session with candle breakout confirmation",
            "stock_picker": "preopen_gap",
            "params": {
                "min_gap_percent": 1.0,
                "max_gap_percent": 8.0,
                "entry_window_start": "09:20",
                "entry_window_end": "10:30",
                "stop_loss_percent": 1.0,
                "target_percent": 2.0,
                "risk_reward_ratio": 2.0,
                "max_sl_percent": 2.0,
                "require_nifty_alignment": True,
                "use_opening_range_breakout": True,
                "opening_range_minutes": 5,
                "max_trades_per_day": 5
            }
        }
    },
    
    # Legacy strategy config (for backward compatibility)
    "strategy": {
        "name": "vwap_rsi",
        "stop_loss_percent": 0.5,
        "stop_loss_max":  0.75,
        "target_percent": 1.0,
        "target_max":  1.5,
        "trailing_stop_loss": False,
        "max_trades_per_day": 3,
        "rsi_oversold": 40,
        "rsi_overbought": 70
    },
    
    "risk":  {
        "max_daily_loss_percent": 2.0,
        "max_daily_loss_max": 3.0,
        "max_position_size_percent": 25
    },
    
    "timing":  {
        "analysis_start":  "08:30",
        "preopen_data_ready": "09:10",  # Final pre-open data available after this time
        "trading_start": "09:15",
        "no_new_trade_after": "15:00",
        "square_off_time": "15:15",
        "market_close": "15:30"
    },
    
    "alerts": {
        "sound_enabled": True,
        "desktop_notifications": True
    }
}