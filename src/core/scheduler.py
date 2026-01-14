"""Trading Scheduler - Manages daily trading schedule"""

import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from loguru import logger


class TradingScheduler: 
    """Manages the daily trading schedule"""
    
    def __init__(self):
        self.is_running = False
        self. scheduler_thread:  Optional[threading.Thread] = None
        self.jobs = {}
        
    def _parse_time(self, time_str: str) -> str:
        """Ensure time string is in HH:MM format"""
        if len(time_str) == 5:
            return time_str
        return time_str + ":00"
    
    def schedule_task(self, name: str, time_str: str, task:  Callable) -> None:
        """Schedule a task at a specific time"""
        formatted_time = self._parse_time(time_str)
        job = schedule.every().day.at(formatted_time).do(task)
        self.jobs[name] = job
        logger.info(f"📅 Scheduled '{name}' at {formatted_time}")
    
    def schedule_interval(self, name: str, seconds: int, task: Callable) -> None:
        """Schedule a task to run every N seconds"""
        job = schedule.every(seconds).seconds.do(task)
        self.jobs[name] = job
        logger.info(f"🔄 Scheduled '{name}' every {seconds} seconds")
    
    def cancel_task(self, name: str) -> bool:
        """Cancel a scheduled task"""
        if name in self. jobs:
            schedule.cancel_job(self.jobs[name])
            del self.jobs[name]
            logger.info(f"❌ Cancelled task '{name}'")
            return True
        return False
    
    def cancel_all(self) -> None:
        """Cancel all scheduled tasks"""
        schedule.clear()
        self.jobs = {}
        logger.info("❌ All scheduled tasks cancelled")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def start(self) -> None:
        """Start the scheduler in a background thread"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("✅ Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        logger.info("⏹️ Scheduler stopped")
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        now = datetime.now().time()
        market_open = datetime. strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        return market_open <= now <= market_close
    
    def is_trading_hours(self, no_new_trade_after: str = "15:00") -> bool:
        """Check if current time allows new trades"""
        now = datetime. now().time()
        market_open = datetime.strptime("09:15", "%H:%M").time()
        cutoff = datetime.strptime(no_new_trade_after, "%H:%M").time()
        return market_open <= now <= cutoff
    
    def time_until(self, time_str: str) -> timedelta:
        """Get time remaining until a specific time today"""
        now = datetime.now()
        target = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if target < now:
            target += timedelta(days=1)
        return target - now
    
    def get_next_market_open(self) -> datetime:
        """Get the next market opening time"""
        now = datetime. now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        if now >= market_open:
            market_open += timedelta(days=1)
        
        # Skip weekends
        while market_open.weekday() >= 5:  # Saturday = 5, Sunday = 6
            market_open += timedelta(days=1)
        
        return market_open