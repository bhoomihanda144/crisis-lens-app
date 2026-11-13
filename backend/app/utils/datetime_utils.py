"""
CrisisLens DateTime Utilities
Enforces ISO 8601 UTC timestamps and calculates contract-compliant freshness.
"""
from datetime import datetime, timezone
from typing import Dict, Any


def now_utc() -> datetime:
    """Returns current UTC datetime."""
    return datetime.now(timezone.utc)


def now_utc_iso() -> str:
    """Returns current UTC time formatted as ISO 8601: YYYY-MM-DDTHH:MM:SSZ"""
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(dt_str: str) -> datetime:
    """Parses an ISO 8601 string into a timezone-aware UTC datetime."""
    # Replace 'Z' with '+00:00' for fromisoformat compatibility
    clean_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_iso(dt: datetime) -> str:
    """Formats a datetime to UTC ISO 8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def calculate_freshness(reported_at_str: str) -> Dict[str, Any]:
    """
    Computes freshness status and age according to API Contract v1.0:
    - recent: age <= 60 minutes
    - aging:  61 <= age <= 240 minutes
    - stale:  age > 240 minutes
    """
    reported_dt = parse_iso(reported_at_str)
    now = now_utc()
    delta = now - reported_dt
    age_minutes = max(0, int(delta.total_seconds() / 60))

    if age_minutes <= 60:
        freshness_status = "recent"
    elif age_minutes <= 240:
        freshness_status = "aging"
    else:
        freshness_status = "stale"

    return {
        "status": freshness_status,
        "age_minutes": age_minutes,
        "last_updated": reported_at_str,
    }
