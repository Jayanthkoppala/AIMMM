"""
API Usage Tracker for CoinGecko
Tracks API calls to stay within monthly limits.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection


class APITracker:
    """Track CoinGecko API usage to stay within limits."""
    
    def __init__(self):
        self.calls_today: Dict[str, int] = {}  # Date -> count
        self.calls_this_minute: int = 0
        self.last_minute_reset: datetime = datetime.now()
        self.last_month_reset: Optional[datetime] = None
    
    def _get_today_key(self) -> str:
        """Get today's date as string key."""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _reset_minute_counter_if_needed(self):
        """Reset minute counter if a minute has passed."""
        now = datetime.now()
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.calls_this_minute = 0
            self.last_minute_reset = now
    
    def _reset_monthly_if_needed(self):
        """Reset monthly counter if a new month has started."""
        now = datetime.now()
        if self.last_month_reset is None:
            self.last_month_reset = now
            return
        
        # Check if we're in a new month
        if now.month != self.last_month_reset.month or now.year != self.last_month_reset.year:
            logger.info("New month detected - resetting API usage counter")
            self.calls_today = {}
            self.last_month_reset = now
    
    def can_make_request(self) -> bool:
        """
        Check if we can make an API request without exceeding limits.
        
        Returns:
            True if request can be made, False otherwise
        """
        self._reset_minute_counter_if_needed()
        self._reset_monthly_if_needed()
        
        # Check per-minute rate limit
        if self.calls_this_minute >= settings.COINGECKO_API_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded: {self.calls_this_minute}/{settings.COINGECKO_API_LIMIT_PER_MINUTE} calls this minute")
            return False
        
        # Check monthly limit (approximate)
        today_key = self._get_today_key()
        calls_today = self.calls_today.get(today_key, 0)
        days_in_month = 30
        estimated_monthly = calls_today * days_in_month
        
        if estimated_monthly >= settings.COINGECKO_API_LIMIT_MONTHLY * 0.95:  # 95% threshold
            logger.warning(f"Approaching monthly limit: ~{estimated_monthly}/{settings.COINGECKO_API_LIMIT_MONTHLY} calls")
            return False
        
        return True
    
    def record_call(self):
        """Record an API call."""
        self._reset_minute_counter_if_needed()
        self._reset_monthly_if_needed()
        
        self.calls_this_minute += 1
        today_key = self._get_today_key()
        self.calls_today[today_key] = self.calls_today.get(today_key, 0) + 1
        
        # Log periodically
        if self.calls_this_minute % 10 == 0:
            logger.debug(f"API calls this minute: {self.calls_this_minute}/{settings.COINGECKO_API_LIMIT_PER_MINUTE}")
    
    def get_usage_stats(self) -> Dict:
        """Get current API usage statistics."""
        self._reset_monthly_if_needed()
        
        today_key = self._get_today_key()
        calls_today = self.calls_today.get(today_key, 0)
        days_in_month = 30
        estimated_monthly = calls_today * days_in_month
        
        return {
            "calls_today": calls_today,
            "calls_this_minute": self.calls_this_minute,
            "rate_limit_per_minute": settings.COINGECKO_API_LIMIT_PER_MINUTE,
            "estimated_monthly": estimated_monthly,
            "monthly_limit": settings.COINGECKO_API_LIMIT_MONTHLY,
            "percentage_used": (estimated_monthly / settings.COINGECKO_API_LIMIT_MONTHLY * 100) if settings.COINGECKO_API_LIMIT_MONTHLY > 0 else 0
        }


# Global API tracker instance
api_tracker = APITracker()

