"""Trading Scheduler - Manages daily trading schedule"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from loguru import logger

from src.utils.timezone import now_ist, now_ist_time, IST


class TradingScheduler: 
    """Manages the daily trading schedule using IST timezone"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=IST)
        self.is_running = False
        self.jobs = {}
        
    def _parse_time(self, time_str: str) -> tuple[int, int]:
        """Parse time string to hour and minute"""
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return hour, minute
    
    def schedule_task(self, name: str, time_str: str, task: Callable) -> None:
        """Schedule a task at a specific IST time daily"""
        hour, minute = self._parse_time(time_str)
        
        # Create cron trigger for daily execution at IST time
        trigger = CronTrigger(hour=hour, minute=minute, timezone=IST)
        
        job = self.scheduler.add_job(
            func=task,
            trigger=trigger,
            id=name,
            name=name,
            replace_existing=True
        )
        self.jobs[name] = job
        logger.info(f"📅 Scheduled '{name}' at {time_str} IST")
    
    def schedule_interval(self, name: str, seconds: int, task: Callable) -> None:
        """Schedule a task to run every N seconds"""
        trigger = IntervalTrigger(seconds=seconds, timezone=IST)
        
        job = self.scheduler.add_job(
            func=task,
            trigger=trigger,
            id=name,
            name=name,
            replace_existing=True
        )
        self.jobs[name] = job
        logger.info(f"🔄 Scheduled '{name}' every {seconds} seconds")
    
    def cancel_task(self, name: str) -> bool:
        """Cancel a scheduled task"""
        if name in self.jobs:
            self.scheduler.remove_job(name)
            del self.jobs[name]
            logger.info(f"❌ Cancelled task '{name}'")
            return True
        return False
    
    def cancel_all(self) -> None:
        """Cancel all scheduled tasks"""
        self.scheduler.remove_all_jobs()
        self.jobs = {}
        logger.info("❌ All scheduled tasks cancelled")
    
    def start(self) -> None:
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ Scheduler started (IST timezone)")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
        logger.info("⏹️ Scheduler stopped")
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours (9:15 AM - 3:30 PM IST)"""
        now = now_ist_time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        return market_open <= now <= market_close
    
    def is_trading_hours(self, no_new_trade_after: str = "15:00") -> bool:
        """Check if current IST time allows new trades"""
        now = now_ist_time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        cutoff = datetime.strptime(no_new_trade_after, "%H:%M").time()
        return market_open <= now <= cutoff
    
    def time_until(self, time_str: str) -> timedelta:
        """Get time remaining until a specific IST time today"""
        now = now_ist()
        hour, minute = self._parse_time(time_str)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if target < now:
            target += timedelta(days=1)
        return target - now
    
    def get_next_market_open(self) -> datetime:
        """Get the next market opening time in IST"""
        now = now_ist()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        if now >= market_open:
            market_open += timedelta(days=1)
        
        # Skip weekends
        while market_open.weekday() >= 5:  # Saturday = 5, Sunday = 6
            market_open += timedelta(days=1)
        
        return market_open