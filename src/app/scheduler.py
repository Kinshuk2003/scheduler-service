"""
Scheduler module for job scheduling logic.

This module implements the scheduling functionality following SOLID principles:
- Single Responsibility: Handles only scheduling logic
- Open/Closed: Easy to extend with new scheduling strategies
- Liskov Substitution: Consistent interface for different schedulers
- Interface Segregation: Separate concerns for different scheduling types
- Dependency Inversion: Depends on abstractions, not concretions
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Union
from croniter import croniter
import pytz
import logging

logger = logging.getLogger(__name__)


class ScheduleValidator:
    """
    Schedule validator following the Strategy pattern.
    This allows different validation strategies for different schedule types.
    """
    
    @staticmethod
    def validate_cron_expression(expr: str) -> bool:
        """Validate cron expression format."""
        try:
            croniter(expr)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_datetime_expression(expr: str) -> bool:
        """Validate datetime expression format."""
        try:
            # Try ISO format
            datetime.fromisoformat(expr.replace('Z', '+00:00'))
            return True
        except ValueError:
            try:
                # Try common formats
                datetime.strptime(expr, '%Y-%m-%d %H:%M:%S')
                return True
            except ValueError:
                return False
    
    @staticmethod
    def validate_interval_expression(expr: str) -> bool:
        """Validate interval expression format."""
        pattern = r'^(\d+)([smhd])$'
        return bool(re.match(pattern, expr.lower()))


def is_cron_expression(schedule_expr: str) -> bool:
    """
    Check if the schedule expression is a cron expression.
    
    Args:
        schedule_expr: The schedule expression to check
        
    Returns:
        True if it's a cron expression, False otherwise
    """
    parts = schedule_expr.strip().split()
    
    # Must have 5 parts for standard cron
    if len(parts) != 5:
        return False
    
    # Check if it's a valid cron expression
    try:
        croniter(schedule_expr)
        return True
    except (ValueError, TypeError):
        return False
    
    # Default to cron if it has 5 space-separated parts
    return len(parts) == 5


def calculate_next_run(schedule_expr: str, timezone: str = "UTC") -> Optional[datetime]:
    """
    Calculate the next run time for a job based on its schedule expression.
    
    This function handles different types of schedule expressions:
    - Cron expressions (e.g., "0 2 * * *")
    - Datetime expressions (e.g., "2024-01-01T12:00:00Z")
    - Interval expressions (e.g., "5m", "1h", "30s")
    
    Args:
        schedule_expr: The schedule expression
        timezone: The timezone for the calculation
        
    Returns:
        The next run time as a timezone-naive datetime object in UTC, or None if invalid
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        if is_cron_expression(schedule_expr):
            return _calculate_cron_next_run(schedule_expr, now, tz)
        elif ScheduleValidator.validate_datetime_expression(schedule_expr):
            return _calculate_datetime_next_run(schedule_expr, now, tz)
        elif ScheduleValidator.validate_interval_expression(schedule_expr):
            return _calculate_interval_next_run(schedule_expr, now, tz)
        else:
            logger.warning(f"Invalid schedule expression: {schedule_expr}")
            return None
            
    except Exception as e:
        logger.error(f"Error calculating next run for '{schedule_expr}': {str(e)}")
        return None


def _calculate_cron_next_run(schedule_expr: str, now: datetime, tz) -> Optional[datetime]:
    """Calculate next run time for cron expressions."""
    try:
        cron = croniter(schedule_expr, now)
        next_run = cron.get_next(datetime)
        
        # Ensure the timezone is correct
        if next_run.tzinfo is None:
            next_run = tz.localize(next_run)
        elif next_run.tzinfo != tz:
            next_run = next_run.astimezone(tz)
        
        # Convert to UTC and make timezone-naive for database storage
        next_run_utc = next_run.astimezone(pytz.UTC)
        return next_run_utc.replace(tzinfo=None)
        
    except Exception as e:
        logger.error(f"Error calculating cron next run: {str(e)}")
        return None


def _calculate_datetime_next_run(schedule_expr: str, now: datetime, tz) -> Optional[datetime]:
    """Calculate next run time for datetime expressions."""
    try:
        # Parse the datetime
        if schedule_expr.endswith('Z'):
            schedule_expr = schedule_expr.replace('Z', '+00:00')
        
        scheduled_time = datetime.fromisoformat(schedule_expr)
        
        # Handle timezone
        if scheduled_time.tzinfo is None:
            scheduled_time = tz.localize(scheduled_time)
        elif scheduled_time.tzinfo != tz:
            scheduled_time = scheduled_time.astimezone(tz)
        
        # If the scheduled time is in the past, return None (one-time job already passed)
        if scheduled_time <= now:
            return None
        
        # Convert to UTC and make timezone-naive for database storage
        scheduled_time_utc = scheduled_time.astimezone(pytz.UTC)
        return scheduled_time_utc.replace(tzinfo=None)
        
    except Exception as e:
        logger.error(f"Error calculating datetime next run: {str(e)}")
        return None


def _calculate_interval_next_run(schedule_expr: str, now: datetime, tz) -> Optional[datetime]:
    """Calculate next run time for interval expressions."""
    try:
        # Parse interval (e.g., "5m", "1h", "30s")
        pattern = r'^(\d+)([smhd])$'
        match = re.match(pattern, schedule_expr.lower())
        
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        # Calculate interval in seconds
        if unit == 's':
            interval_seconds = value
        elif unit == 'm':
            interval_seconds = value * 60
        elif unit == 'h':
            interval_seconds = value * 3600
        elif unit == 'd':
            interval_seconds = value * 86400
        else:
            return None
        
        # Calculate next run time
        next_run = now + timedelta(seconds=interval_seconds)
        
        # Convert to UTC and make timezone-naive for database storage
        next_run_utc = next_run.astimezone(pytz.UTC)
        return next_run_utc.replace(tzinfo=None)
        
    except Exception as e:
        logger.error(f"Error calculating interval next run: {str(e)}")
        return None


class Scheduler:
    """
    Main scheduler class following the Strategy pattern.
    This allows different scheduling strategies to be used interchangeably.
    """
    
    def __init__(self):
        self.validator = ScheduleValidator()
    
    def calculate_next_run(self, schedule_expr: str, timezone: str = "UTC") -> Optional[datetime]:
        """
        Calculate the next run time for a job.
        
        Args:
            schedule_expr: The schedule expression
            timezone: The timezone for the calculation
            
        Returns:
            The next run time as a timezone-naive datetime object in UTC, or None if invalid
        """
        return calculate_next_run(schedule_expr, timezone)
    
    def validate_schedule(self, schedule_expr: str) -> bool:
        """
        Validate a schedule expression.
        
        Args:
            schedule_expr: The schedule expression to validate
            
        Returns:
            True if valid, False otherwise
        """
        if is_cron_expression(schedule_expr):
            return self.validator.validate_cron_expression(schedule_expr)
        elif self.validator.validate_datetime_expression(schedule_expr):
            return True
        elif self.validator.validate_interval_expression(schedule_expr):
            return True
        else:
            return False


# Create a default scheduler instance
scheduler = Scheduler()
