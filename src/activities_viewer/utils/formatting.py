"""Shared formatting utilities for the dashboard."""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Union


def render_metric(
    column,
    label: str,
    value: str,
    help_text: str = None,
    label_size: int = 12,
    value_size: int = 28,
    custom_style: bool = False,
) -> None:
    """
    Render a metric with responsive sizing that doesn't get truncated.
    Uses custom HTML instead of st.metric() for better control.

    Args:
        column: Streamlit column to render in
        label: Metric label (e.g., "Average Power")
        value: Metric value to display (e.g., "245 W")
        help_text: Optional help/documentation text shown on hover
        label_size: Font size for the label in pixels (default: 12)
        value_size: Font size for the value in pixels (default: 28)
    """
    if custom_style is False:
        with column:
            st.metric(label, value, help_text)
            return
    with column:
        # Create a responsive metric card with proper text sizing and help text support
        if help_text:
            # Convert newlines to HTML entity and escape quotes for HTML attribute
            help_escaped = help_text.replace("\n", "&#10;").replace('"', "&quot;")
            # HTML with tooltip on hover
            metric_html = f"""
            <div style="
                position: relative;
                padding: 12px 6px;
                background-color: rgba(240, 242, 246, 0.7);
                border-radius: 6px;
                text-align: center;
                min-height: 70px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                cursor: help;
                border: 1px solid rgba(200, 200, 200, 0.3);
            " title="{help_escaped}">
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 3px;
                    width: 100%;
                    min-height: 16px;
                    flex-wrap: wrap;
                ">
                    <div style="
                        font-size: {label_size}px;
                        color: #888;
                        font-weight: 500;
                        text-align: center;
                    ">{label}</div>
                    <div style="
                        font-size: 10px;
                        color: #0066cc;
                        font-weight: bold;
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        border: 1px solid #0066cc;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-shrink: 0;
                        line-height: 1;
                    ">ℹ</div>
                </div>
                <div style="
                    font-size: {value_size}px;
                    font-weight: bold;
                    color: #262730;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    line-height: 1.4;
                    width: 100%;
                    text-align: center;
                    margin-top: 4px;
                ">{value}</div>
            </div>
            """
        else:
            # HTML without tooltip
            metric_html = f"""
            <div style="
                padding: 12px 6px;
                background-color: rgba(240, 242, 246, 0.7);
                border-radius: 6px;
                text-align: center;
                min-height: 70px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            ">
                <div style="
                    font-size: {label_size}px;
                    color: #888;
                    margin-bottom: 6px;
                    font-weight: 500;
                    text-align: center;
                ">{label}</div>
                <div style="
                    font-size: {value_size}px;
                    font-weight: bold;
                    color: #262730;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    line-height: 1.4;
                    width: 100%;
                    text-align: center;
                ">{value}</div>
            </div>
            """
        st.markdown(metric_html, unsafe_allow_html=True)


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
    if seconds is None or pd.isna(seconds) or seconds == 0:
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
    """Format power value.

    Args:
        watts: Power value in watts
        include_unit: Whether to include "W" unit

    Returns:
        Formatted power string, or "-" if invalid
    """
    if watts is None or pd.isna(watts) or watts == 0:
        return "-"
    if include_unit:
        return f"{watts:.0f} W"
    return f"{watts:.0f}"


def format_watts(watts: float) -> str:
    """Format power in watts with unit.

    Args:
        watts: Power value in watts

    Returns:
        Formatted power string with unit (e.g., "250 W"), or "-" if invalid
    """
    if watts is None or pd.isna(watts):
        return "-"
    return f"{int(watts)} W"


def format_wkg(value: float) -> str:
    """Format power per kilogram with 2 decimals.

    Args:
        value: Power-to-weight ratio in W/kg

    Returns:
        Formatted W/kg string (e.g., "3.85 W/kg"), or "-" if invalid
    """
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.2f} W/kg"


def format_date(date: Union[datetime, str, None], format_str: str = "%Y-%m-%d") -> str:
    """Format date to string.

    Args:
        date: Date object or string to format
        format_str: strftime format string

    Returns:
        Formatted date string, or "-" if invalid
    """
    if date is None:
        return "-"

    if isinstance(date, datetime):
        return date.strftime(format_str)

    if isinstance(date, str):
        # If already a string, try to parse and reformat
        try:
            parsed = pd.to_datetime(date)
            if pd.notna(parsed):
                return parsed.strftime(format_str)
        except:
            # If parsing fails, return as-is if it looks like a date
            if len(date) >= 8:  # Reasonable minimum for a date string
                return date

    return "-"


def format_distance(meters: float, unit: str = "km") -> str:
    """Format distance value.

    Args:
        meters: Distance in meters
        unit: Output unit ("km" or "m")

    Returns:
        Formatted distance string, or "-" if invalid
    """
    if meters is None or pd.isna(meters) or meters == 0:
        return "-"
    if unit == "km":
        return f"{meters / 1000:.1f} km"
    return f"{meters:.0f} m"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage value.

    Args:
        value: Percentage value
        decimals: Number of decimal places

    Returns:
        Formatted percentage string, or "-" if invalid
    """
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}%"
