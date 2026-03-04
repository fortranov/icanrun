"""
General utility helpers used across the application.
"""
from datetime import date, datetime
from typing import Optional


def format_duration(minutes: int) -> str:
    """
    Convert duration in minutes to human-readable 'Xh Ym' format.

    Examples:
        90  -> '1h 30m'
        45  -> '45m'
        60  -> '1h'
    """
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def weeks_until(target_date: date) -> int:
    """Calculate the number of full weeks from today until target_date."""
    today = date.today()
    delta = (target_date - today).days
    return max(0, delta // 7)


def get_weekday_name(weekday: int) -> str:
    """
    Return Russian weekday name for a given weekday number (0=Monday).
    """
    names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    return names.get(weekday, "")


def to_utc_datetime(d: date) -> datetime:
    """Convert a date to a UTC datetime at midnight."""
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def safe_divide(numerator: float, denominator: float) -> float:
    """Safe division, returns 0.0 if denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator
