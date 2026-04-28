"""Calendar helpers — use UTC for app-wide \"today\" to match booking/exam logic."""

from datetime import UTC, date, datetime


def utc_today() -> date:
    return datetime.now(UTC).date()
