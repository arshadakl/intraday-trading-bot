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
            "display_name": "3-Minute Breakout Strategy",
            "description": "Breakout strategy using 3-minute reference candle. SHORT top stocks on gap-up, LONG bottom stocks on gap-down.",
            "stock_picker": "preopen_gap",
            "params": {
                "gap_threshold_percent": 0.2,
                "large_candle_percent": 1.0,
                "stop_loss_percent": 1.0,
                "target_percent": 1.0,
                "max_trades_per_day": 2,
                "stocks_per_side": 4,
                "no_new_trade_after": "15:00"
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
        "no_new_trade_after": "15:00",
        "square_off_time": "15:15",
        "market_close": "15:30"
    },
    
    "alerts": {
        "sound_enabled": True,
        "desktop_notifications": True
    }
}
