"""
Weekly Analysis Page.

Displays detailed analysis for a specific week including training load,
intensity distribution, efficiency trends, and activity breakdown.

This page uses extracted components for modular organization.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils import format_duration, get_metric_from_df, calculate_tid
from activities_viewer.data import HELP_TEXTS
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

# Aliases for backward compatibility
get_metric = get_metric_from_df
calculate_weekly_tid = calculate_tid

# This is used by components module for imports
__all__ = ["calculate_weekly_tid"]


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

    # Week selector (includes metric_view selector)
    available_weeks = []
    available_sports = []
    selected_week = None
    metric_view = "Moving Time"
    selected_sports = []

    # Get all activities (will be filtered by metric_view later in render function)
    df_activities = service.get_all_activities()
    if df_activities.empty:
        st.warning("No activities found.")
        return

    # Ensure datetime (keep as local timezone, don't force UTC)
    df_activities["start_date_local"] = pd.to_datetime(
        df_activities["start_date_local"]
    )

    # Remove timezone info if present (work with local dates)
    if df_activities["start_date_local"].dt.tz is not None:
        df_activities["start_date_local"] = df_activities["start_date_local"].dt.tz_localize(None)

    # Add week column (Start of the week - Monday)
    # Subtract weekday offset (0=Monday, 6=Sunday) to get Monday of each week
    df_activities["week_start"] = (
        df_activities["start_date_local"]
        - pd.to_timedelta(df_activities["start_date_local"].dt.weekday, unit='D')
    ).dt.normalize()

    # Get unique weeks for selector
    available_weeks = sorted(df_activities["week_start"].unique(), reverse=True)
    available_sports = sorted(df_activities["sport_type"].unique().tolist())

    # Week selector
    selected_week, metric_view, selected_sports = render_week_selector(
        available_weeks, available_sports
    )

    # Reload activities with selected metric_view
    df_activities = service.get_all_activities(metric_view)
    df_activities["start_date_local"] = pd.to_datetime(
        df_activities["start_date_local"]
    )

    # Remove timezone info if present (work with local dates)
    if df_activities["start_date_local"].dt.tz is not None:
        df_activities["start_date_local"] = df_activities["start_date_local"].dt.tz_localize(None)

    # Add week column (Start of the week - Monday)
    # Subtract weekday offset (0=Monday, 6=Sunday) to get Monday of each week
    df_activities["week_start"] = (
        df_activities["start_date_local"]
        - pd.to_timedelta(df_activities["start_date_local"].dt.weekday, unit='D')
    ).dt.normalize()

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
            selected_week,
            metric_view,
            calculate_weekly_tid,
            format_duration,
            settings,
            df_all_activities=df_activities,
            help_texts=HELP_TEXTS,
        )

    with tab_intensity:
        render_intensity_tab(df_week, selected_week, metric_view)

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
