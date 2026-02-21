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
    
    # Strategy configuration
    "strategies": {
        "three_minute": {
            "enabled": True,
            "display_name": "3-Minute Strategy (Pre-Open Gap)",
            "description": "Mean reversion strategy - fade the gap. Short strongest on gap-up, long weakest on gap-down",
            "stock_picker": "preopen_gap",
            "params": {
                "min_gap_percent": 1.0,
                "max_gap_percent": 8.0,
                "entry_window_start": "09:20",
                "entry_window_end": "10:30",
                "stop_loss_percent": 1.0,
                "target_percent": 1.0,
                "risk_reward_ratio": 1.0,
                "max_sl_percent": 2.0,
                "require_nifty_alignment": False,
                "use_opening_range_breakout": True,
                "opening_range_minutes": 3,
                "max_trades_per_day": 2,
                "no_new_trade_after": "14:30",
                "max_daily_losses": 2,
                "first_candle_sl_threshold": 1.0,
                "volume_breakout_multiplier": 1.2,
                "require_candle_close": True
            }
        }
    },
    
    # Legacy strategy config (for backward compatibility)
    "strategy": {
        "name": "three_minute",
        "stop_loss_percent": 1.0,
        "stop_loss_max":  2.0,
        "target_percent": 1.0,
        "target_max":  2.0,
        "trailing_stop_loss": False,
        "max_trades_per_day": 2,
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
        "preopen_data_ready": "09:10",  # Final IEP data available only after 9:10 AM
        "trading_start": "09:15",
        "no_new_trade_after": "14:30",
        "square_off_time": "15:15",
        "market_close": "15:30"
    },
    
    "alerts": {
        "sound_enabled": True,
        "desktop_notifications": True
    }
}
