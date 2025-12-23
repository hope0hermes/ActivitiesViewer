"""
Monthly Analysis - Deep-dive into monthly training patterns.

Provides aggregated monthly metrics, TID analysis, week-by-week breakdowns,
trend analysis over 6 months, and complete activity listings.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils import format_duration, get_metric_from_df, calculate_tid
from activities_viewer.data import HELP_TEXTS
from activities_viewer.pages.components.monthly_analysis_components import (
    render_activities_tab,
    render_intensity_tab,
    render_kpi_section,
    render_month_navigation,
    render_month_selector,
    render_overview_tab,
    render_trends_tab,
)

st.set_page_config(page_title="Monthly Analysis", page_icon="📅", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Alias for backward compatibility
get_metric = get_metric_from_df


def calculate_monthly_tid(df: pd.DataFrame, metric_view: str) -> dict:
    """
    Calculate Training Intensity Distribution for monthly data.

    Args:
        df: DataFrame with activities
        metric_view: "Moving" or "Raw"

    Returns:
        Dictionary with z1, z2, z3 percentages
    """
    tid = {"z1": 0, "z2": 0, "z3": 0}

    if df.empty:
        return tid

    # Use time-weighted averages from power zones
    time_col = "moving_time" if metric_view == "Moving Time" else "elapsed_time"
    if time_col not in df.columns:
        time_col = "moving_time"

    total_time = df[time_col].sum()
    if total_time == 0:
        return tid

    # Power zones: Z1=recovery, Z2=endurance, Z3=tempo, Z4=threshold, Z5-Z7=high intensity
    # TID mapping: Z1 low = power Z1+Z2, Z2 moderate = power Z3+Z4, Z3 high = power Z5+Z6+Z7

    for i in range(1, 8):
        col = f"power_z{i}_percentage"
        if col not in df.columns:
            continue

        weighted_pct = (df[col].fillna(0) * df[time_col]).sum() / total_time

        if i <= 2:
            tid["z1"] += weighted_pct
        elif i <= 4:
            tid["z2"] += weighted_pct
        else:
            tid["z3"] += weighted_pct

    return tid


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Main entry point for Monthly Analysis page."""
    st.title("📅 Monthly Analysis")

    if "activity_service" not in st.session_state:
        st.error(
            "Service not initialized. Please run the app from the main entry point."
        )
        return

    service: ActivityService = st.session_state.activity_service
    settings = st.session_state.get("settings", None)

    # Get all activities (will be filtered by metric_view later)
    df_activities = service.get_all_activities()
    if df_activities.empty:
        st.warning("No activities found.")
        return

    # Ensure date columns exist
    if "start_date_local" not in df_activities.columns:
        st.error("Missing date column in data.")
        return

    # Ensure datetime
    df_activities["start_date_local"] = pd.to_datetime(df_activities["start_date_local"])

    # Remove timezone info if present (work with local dates)
    if df_activities["start_date_local"].dt.tz is not None:
        df_activities["start_date_local"] = df_activities["start_date_local"].dt.tz_localize(None)

    # Add month start column
    df_activities["month_start"] = df_activities["start_date_local"].dt.to_period("M").dt.to_timestamp()

    # Get available months (sorted descending - most recent first)
    available_months = sorted(df_activities["month_start"].unique(), reverse=True)
    available_sports = df_activities["sport_type"].dropna().unique().tolist()

    # Month selector and settings
    selected_month, metric_view, selected_sports = render_month_selector(
        available_months, available_sports
    )

    if selected_month is None:
        st.warning("No months available.")
        return

    # Filter by selected month and sports
    df_month = df_activities[
        (df_activities["month_start"] == selected_month)
        & (df_activities["sport_type"].isin(selected_sports))
    ].copy()

    # Get previous month for comparisons
    prev_month = selected_month - pd.DateOffset(months=1)
    df_prev_month = df_activities[
        (df_activities["month_start"] == prev_month)
        & (df_activities["sport_type"].isin(selected_sports))
    ].copy()

    # Month navigation header
    render_month_navigation(available_months, selected_month)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # KPI Section
    # ═══════════════════════════════════════════════════════════════════════════
    render_kpi_section(
        df_month=df_month,
        df_prev_month=df_prev_month,
        metric_view=metric_view,
        help_texts=HELP_TEXTS,
        format_duration_fn=format_duration,
        get_metric_fn=get_metric,
    )

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # Tab Section
    # ═══════════════════════════════════════════════════════════════════════════
    tab_overview, tab_intensity, tab_trends, tab_activities = st.tabs(
        ["📊 Overview", "🎯 Intensity Distribution", "📈 Trends", "🏃 Activities"]
    )

    # Get settings for gear names
    settings = service.settings if hasattr(service, "settings") else None

    with tab_overview:
        render_overview_tab(
            df_month=df_month,
            selected_month=selected_month,
            metric_view=metric_view,
            calculate_monthly_tid_fn=calculate_monthly_tid,
            format_duration_fn=format_duration,
            settings=settings,
            df_all_activities=df_activities,
            help_texts=HELP_TEXTS,
        )

    with tab_intensity:
        render_intensity_tab(
            df_month=df_month,
            selected_month=selected_month,
            metric_view=metric_view,
        )

    with tab_trends:
        render_trends_tab(
            df_activities=df_activities,
            selected_month=selected_month,
            selected_sports=selected_sports,
            metric_view=metric_view,
            calculate_monthly_tid_fn=calculate_monthly_tid,
        )

    with tab_activities:
        render_activities_tab(
            df_month=df_month,
            metric_view=metric_view,
            format_duration_fn=format_duration,
            settings=settings,
        )


if __name__ == "__main__":
    main()
