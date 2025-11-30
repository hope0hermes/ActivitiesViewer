"""
Weekly Analysis Page.

Displays detailed analysis for a specific week including training load,
intensity distribution, efficiency trends, and activity breakdown.

This page uses extracted components for modular organization.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.pages.components.weekly_analysis_components import (
    render_week_selector,
    render_week_navigation,
    render_kpi_section,
    render_overview_tab,
    render_intensity_tab,
    render_trends_tab,
    render_activities_tab,
)

st.set_page_config(page_title="Weekly Analysis", page_icon="📅", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# HELP TEXTS
# ═══════════════════════════════════════════════════════════════════════════════

HELP_TEXTS = {
    "tss": (
        "Training Stress Score quantifies total training load. Weekly targets:\n"
        "• 300-400: Maintenance\n• 400-600: Building\n• 600-800: High load\n• 800+: Overreaching risk"
    ),
    "weekly_tid": (
        "Training Intensity Distribution across the week. Ideal polarized model:\n"
        "• 75-80% Low intensity (Z1)\n• 5-10% Moderate (Z2)\n• 15-20% High (Z3)"
    ),
    "avg_ef": (
        "Efficiency Factor = NP / Avg HR. Track weekly average to monitor aerobic fitness.\n"
        "Rising trend = improving aerobic efficiency."
    ),
    "fatigue_trend": (
        "Average fatigue index across activities. Lower is better.\n"
        "High values (>15%) suggest inadequate recovery or pacing issues."
    ),
}

# Helper functions (kept from original, needed by components)


def format_duration(seconds: float) -> str:
    """Format seconds into hours and minutes."""
    if pd.isna(seconds) or seconds == 0:
        return "-"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def get_metric(df: pd.DataFrame, column: str, agg: str = "sum") -> float:
    """Safely get aggregated metric from DataFrame."""
    if column not in df.columns:
        return 0
    series = df[column].dropna()
    if series.empty:
        return 0
    if agg == "sum":
        return series.sum()
    elif agg == "mean":
        return series.mean()
    elif agg == "max":
        return series.max()
    return 0

def calculate_weekly_tid(df: pd.DataFrame, prefix: str = "moving_") -> dict:
    """Calculate time-weighted TID across multiple activities."""
    z1_col = f"{prefix}power_tid_z1_percentage"
    z2_col = f"{prefix}power_tid_z2_percentage"
    z3_col = f"{prefix}power_tid_z3_percentage"

    if not all(col in df.columns for col in [z1_col, z2_col, z3_col, "moving_time"]):
        return {"z1": 0, "z2": 0, "z3": 0}

    # Time-weighted average
    total_time = df["moving_time"].sum()
    if total_time == 0:
        return {"z1": 0, "z2": 0, "z3": 0}

    z1 = (df[z1_col].fillna(0) * df["moving_time"]).sum() / total_time
    z2 = (df[z2_col].fillna(0) * df["moving_time"]).sum() / total_time
    z3 = (df[z3_col].fillna(0) * df["moving_time"]).sum() / total_time

    return {"z1": z1, "z2": z2, "z3": z3}


# This is used by components module for imports
__all__ = ["format_duration", "get_metric", "calculate_weekly_tid"]


def main():
    """Main page orchestrator."""
    st.title("📅 Weekly Analysis")

    if "activity_service" not in st.session_state:
        st.error(
            "Service not initialized. Please run the app from the main entry point."
        )
        return

    service: ActivityService = st.session_state.activity_service
    settings = st.session_state.get("settings", None)

    # Get all activities
    df_activities = service.get_all_activities()
    if df_activities.empty:
        st.warning("No activities found.")
        return

    # Ensure datetime
    df_activities["start_date_local"] = pd.to_datetime(
        df_activities["start_date_local"], utc=True
    )

    # Add week column (Start of the week - Monday)
    df_activities["week_start"] = (
        df_activities["start_date_local"]
        .dt.tz_localize(None)
        .dt.to_period("W-MON")
        .dt.start_time
    )

    # Get unique weeks for selector
    available_weeks = sorted(df_activities["week_start"].unique(), reverse=True)
    available_sports = sorted(df_activities["sport_type"].unique().tolist())

    # Week selector
    selected_week, metric_view, selected_sports = render_week_selector(
        available_weeks, available_sports
    )

    # Filter data for selected week
    df_week = df_activities[
        (df_activities["week_start"] == selected_week)
        & (df_activities["sport_type"].isin(selected_sports))
    ].copy()

    # Calculate previous week for comparison
    prev_week_start = selected_week - pd.Timedelta(weeks=1)
    df_prev_week = df_activities[
        (df_activities["week_start"] == prev_week_start)
        & (df_activities["sport_type"].isin(selected_sports))
    ]

    # Header & Navigation
    render_week_navigation(available_weeks, selected_week)
    st.divider()

    # KPI Section
    render_kpi_section(
        df_week,
        df_prev_week,
        metric_view,
        HELP_TEXTS,
        format_duration,
        get_metric,
    )
    st.divider()

    # Tabs for detailed analysis
    tab_overview, tab_intensity, tab_trends, tab_activities = st.tabs(
        ["📊 Overview", "🎯 Intensity Distribution", "📈 Trends", "📋 Activities"]
    )

    with tab_overview:
        render_overview_tab(
            df_week,
            metric_view,
            calculate_weekly_tid,
            format_duration,
            settings,
        )

    with tab_intensity:
        render_intensity_tab(df_week, metric_view)

    with tab_trends:
        render_trends_tab(
            df_activities,
            selected_week,
            selected_sports,
            metric_view,
            calculate_weekly_tid,
        )

    with tab_activities:
        render_activities_tab(
            df_week,
            metric_view,
            format_duration,
            settings,
        )


if __name__ == "__main__":
    main()
