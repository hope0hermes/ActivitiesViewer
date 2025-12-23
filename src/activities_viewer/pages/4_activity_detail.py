"""
Activity Detail Page.
Displays detailed metrics, maps, and charts for a single activity.

This page uses extracted components for modular organization.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils import format_duration, get_metric_from_object
from activities_viewer.data import HELP_TEXTS
from activities_viewer.pages.components.activity_detail_components import (
    render_activity_selector,
    render_activity_navigation,
    render_overview_tab,
    render_power_hr_tab,
    render_durability_tab,
    render_training_load_tab,
)

st.set_page_config(page_title="Activity Detail", page_icon="🚴", layout="wide")

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
    """Main page orchestrator."""
    st.title("🚴 Activity Detail")

    if "activity_service" not in st.session_state:
        st.error(
            "Service not initialized. Please run the app from the main entry point."
        )
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

    # Render tabs with components
    tab_overview, tab_power_hr, tab_durability, tab_training = st.tabs(
        ["🗺️ Overview", "⚡ Power & Heart Rate", "🔋 Durability & Fatigue", "📊 Training Load & Power Profile"]
    )

    with tab_overview:
        render_overview_tab(activity, service, metric_view, HELP_TEXTS)

    with tab_power_hr:
        render_power_hr_tab(activity, service, metric_view, HELP_TEXTS)

    with tab_durability:
        render_durability_tab(activity, metric_view, HELP_TEXTS)

    with tab_training:
        render_training_load_tab(activity, metric_view, HELP_TEXTS)


if __name__ == "__main__":
    main()
