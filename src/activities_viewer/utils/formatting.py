"""Shared formatting utilities for the dashboard."""

import pandas as pd


def format_duration(seconds: float, style: str = "short") -> str:
    """Format seconds into human-readable duration.

    Args:
        seconds: Duration in seconds
        style:
            - "short": "1h 30m"
            - "hms": "1:30:00"
            - "verbose": "1 hour 30 minutes"

    Returns:
        Formatted duration string, or "-" if invalid
    """
    if pd.isna(seconds) or seconds == 0:
        return "-"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if style == "short":
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    elif style == "hms":
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    elif style == "verbose":
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        return " ".join(parts) if parts else "0 minutes"

    return f"{hours}h {minutes}m"


def format_power(watts: float, include_unit: bool = True) -> str:
    """Format power value."""
    if pd.isna(watts) or watts == 0:
        return "-"
    if include_unit:
        return f"{watts:.0f} W"
    return f"{watts:.0f}"


def format_distance(meters: float, unit: str = "km") -> str:
    """Format distance value."""
    if pd.isna(meters) or meters == 0:
        return "-"
    if unit == "km":
        return f"{meters / 1000:.1f} km"
    return f"{meters:.0f} m"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage value."""
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}%"
