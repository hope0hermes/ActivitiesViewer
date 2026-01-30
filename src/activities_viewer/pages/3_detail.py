"""
Activity Detail Page - Context-Aware Analysis (Phase 5).

Displays detailed metrics, maps, and charts for a single activity.
Enhanced with contextual header and metrics sections that adapt to activity type.
"""

import json
import os
import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.config import Settings
from activities_viewer.repository.csv_repo import CSVActivityRepository
from activities_viewer.utils import get_metric_from_object
from activities_viewer.data import HELP_TEXTS
from activities_viewer.pages.components.activity_detail_components import (
    render_activity_selector,
    render_activity_navigation,
    render_contextual_header,
    render_contextual_metrics,
    # render_durability_tab,
    # render_overview_tab,
    # render_power_hr_tab,
    render_training_load_tab,
)
from activities_viewer.pages.components.detail_tabs.overview import render_overview_tab
from activities_viewer.pages.components.detail_tabs.power import render_power_hr_tab
from activities_viewer.pages.components.detail_tabs.fatigue import render_durability_tab


st.set_page_config(page_title="Activity Detail", page_icon="🚴", layout="wide")


def init_services(settings: Settings) -> ActivityService:
    """Initialize application services."""
    if settings.data_source_type == "csv":
        raw_file = (
            settings.activities_raw_file
            if hasattr(settings, "activities_raw_file")
            else settings.activities_enriched_file
        )
        moving_file = (
            settings.activities_moving_file
            if hasattr(settings, "activities_moving_file")
            else None
        )
        repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)
    else:
        raw_file = (
            settings.activities_raw_file
            if hasattr(settings, "activities_raw_file")
            else settings.activities_enriched_file
        )
        moving_file = (
            settings.activities_moving_file
            if hasattr(settings, "activities_moving_file")
            else None
        )
        repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)

    return ActivityService(repo)


# Helper functions (kept from original, needed by components)


def apply_smoothing(data: pd.Series, window_size: int) -> pd.Series:
    """Apply rolling average smoothing to a series."""
    if window_size is None or window_size <= 1:
        return data
    return data.rolling(window=window_size, center=True, min_periods=1).mean()


# Alias for backward compatibility
get_metric = get_metric_from_object

# This is used by the components module for imports
__all__ = ["apply_smoothing", "get_metric"]


def main():
    """Main page orchestrator with context-aware layout."""
    # Initialize settings and service if not already done
    if "settings" not in st.session_state:
        config_json = os.environ.get("ACTIVITIES_VIEWER_CONFIG")
        if config_json:
            try:
                config_data = json.loads(config_json)
                st.session_state.settings = Settings(**config_data)
            except Exception as e:
                st.error(f"Failed to load configuration: {e}")
                return
        else:
            st.error(
                "Service not initialized. Please run the app from the main entry point."
            )
            return

    if "activity_service" not in st.session_state:
        try:
            st.session_state.activity_service = init_services(st.session_state.settings)
        except Exception as e:
            st.error(f"Failed to initialize services: {e}")
            return

    service: ActivityService = st.session_state.activity_service

    # Metric view selector in sidebar - always visible
    with st.sidebar:
        st.subheader("View Options")

        # Initialize session state if not present
        if "metric_view_selection" not in st.session_state:
            st.session_state.metric_view_selection = "Moving Time"

        metric_view = st.radio(
            "Metric View:",
            ("Moving Time", "Raw Time"),
            key="metric_view_selection",
            help="Moving Time: Metrics calculated only during movement\nRaw Time: Metrics calculated for total activity duration",
        )

        st.divider()

        st.subheader("Filters")

        # Get all activities to extract available sport types
        all_activities = service.get_all_activities(metric_view)
        if not all_activities.empty:
            available_sports = sorted(all_activities["sport_type"].unique().tolist())
            selected_sports = st.multiselect(
                "Sport Types",
                available_sports,
                default=available_sports
                if "detail_sport_filter" not in st.session_state
                else st.session_state.detail_sport_filter,
                help="Filter by sport type",
            )
            st.session_state.detail_sport_filter = selected_sports

    # Render activity selector with metric_view
    activity, activity_id = render_activity_selector(service, metric_view)
    if activity is None:
        return

    # Reload activity to ensure correct metric_view data is used
    # (in case metric_view changed but activity selection didn't)
    activity = service.get_activity(activity_id, metric_view)

    # Render activity navigation (prev/next buttons)
    render_activity_navigation(service, activity_id, metric_view)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5: CONTEXTUAL HEADER & METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    # Contextual header shows top 4 metrics based on activity type
    render_contextual_header(activity, metric_view, HELP_TEXTS)

    # Contextual metrics section adapts to workout type and intensity
    render_contextual_metrics(activity, service, metric_view, HELP_TEXTS)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # DEEP DIVE TABS (Preserved from v1)
    # ═══════════════════════════════════════════════════════════════════════════

    # Render tabs with components
    tab_overview, tab_power_hr, tab_training = st.tabs(
        [
            "🗺️ Overview & All Metrics",
            "⚡ Power & Heart Rate",
            # "🔋 Durability & Fatigue",
            "📊 Training Load & Power Profile",
        ]
    )

    with tab_overview:
        render_overview_tab(activity, service, metric_view, HELP_TEXTS)

    with tab_power_hr:
        render_power_hr_tab(activity, service, metric_view, HELP_TEXTS)

    # with tab_durability:
    #     render_durability_tab(activity, metric_view, HELP_TEXTS)

    with tab_training:
        render_training_load_tab(activity, metric_view, HELP_TEXTS)


if __name__ == "__main__":
    main()
