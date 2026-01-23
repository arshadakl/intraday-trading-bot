"""Timezone utility for handling Indian Standard Time (IST) consistently"""

from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

# Indian Standard Time timezone
IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """
    Get current datetime in Indian Standard Time (IST).
    
    Returns:
        datetime: Current datetime in IST timezone
    """
    return datetime.now(IST)


def now_ist_time() -> dt_time:
    """
    Get current time in Indian Standard Time (IST).
    
    Returns:
        time: Current time in IST timezone
    """
    return now_ist().time()


def now_ist_date():
    """
    Get current date in Indian Standard Time (IST).
    
    Returns:
        date: Current date in IST timezone
    """
    return now_ist().date()


def format_ist_datetime(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime in IST timezone.
    
    Args:
        dt: datetime to format (defaults to current time)
        fmt: strftime format string
    
    Returns:
        str: Formatted datetime string in IST
    """
    if dt is None:
        dt = now_ist()
    elif dt.tzinfo is None:
        # Assume naive datetime is already IST
        dt = dt.replace(tzinfo=IST)
    else:
        # Convert to IST if it's in a different timezone
        dt = dt.astimezone(IST)
    
    return dt.strftime(fmt)


def to_ist(dt: datetime) -> datetime:
    """
    Convert any datetime to IST timezone.
    
    Args:
        dt: datetime to convert
    
    Returns:
        datetime: datetime in IST timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is already IST
        return dt.replace(tzinfo=IST)
    else:
        # Convert to IST
        return dt.astimezone(IST)
