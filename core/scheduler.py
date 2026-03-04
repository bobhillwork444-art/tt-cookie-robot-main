"""
Scheduler module for automated task execution
"""
import schedule
import threading
import time
import logging
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for running automation tasks on a schedule"""
    
    def __init__(self, task_callback: Callable):
        self.task_callback = task_callback
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.schedule_enabled = False
        self.next_run: Optional[datetime] = None
    
    def set_schedule(self, schedule_type: str, time_str: str = None, 
                     interval_minutes: int = None, days: list = None):
        """
        Set up the schedule
        
        Args:
            schedule_type: 'daily', 'interval', 'specific_days'
            time_str: Time in HH:MM format for daily/specific_days
            interval_minutes: Interval in minutes for 'interval' type
            days: List of days for 'specific_days' (0=Monday, 6=Sunday)
        """
        schedule.clear()
        
        if schedule_type == "daily" and time_str:
            schedule.every().day.at(time_str).do(self._run_task)
            logger.info(f"Scheduled daily at {time_str}")
            
        elif schedule_type == "interval" and interval_minutes:
            schedule.every(interval_minutes).minutes.do(self._run_task)
            logger.info(f"Scheduled every {interval_minutes} minutes")
            
        elif schedule_type == "specific_days" and time_str and days:
            day_names = ["monday", "tuesday", "wednesday", "thursday", 
                        "friday", "saturday", "sunday"]
            for day_num in days:
                if 0 <= day_num <= 6:
                    day_name = day_names[day_num]
                    getattr(schedule.every(), day_name).at(time_str).do(self._run_task)
            logger.info(f"Scheduled on days {days} at {time_str}")
        
        self._update_next_run()
    
    def _run_task(self):
        """Execute the scheduled task"""
        logger.info("Executing scheduled task")
        try:
            self.task_callback()
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")
        self._update_next_run()
    
    def _update_next_run(self):
        """Update the next run time"""
        next_job = schedule.next_run()
        if next_job:
            self.next_run = next_job
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.schedule_enabled = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        self.schedule_enabled = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def get_next_run(self) -> Optional[str]:
        """Get the next scheduled run time as string"""
        if self.next_run:
            return self.next_run.strftime("%Y-%m-%d %H:%M:%S")
        return None
    
    def is_scheduled(self) -> bool:
        """Check if any jobs are scheduled"""
        return len(schedule.get_jobs()) > 0
