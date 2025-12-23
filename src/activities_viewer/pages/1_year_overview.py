"""
Year Overview Page.

Displays comprehensive aggregated statistics and trends for a selected year.
Includes training intensity distribution, efficiency trends, power curve PRs,
gear usage statistics, and monthly progression analysis.

This page uses extracted components for modular organization.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils import format_duration, safe_mean, safe_sum, calculate_tid
from activities_viewer.data import HELP_TEXTS
from activities_viewer.pages.components.year_overview_components import (
    render_year_selector,
    render_sport_filter,
    render_kpi_section,
    render_power_curve_section,
    render_tid_section,
    render_training_load_section,
    render_trends_tab,
    render_efficiency_tab,
    render_gear_tab,
    render_distributions_tab,
    render_patterns_tab,
    render_extremes_section,
    render_performance_trajectory,
    render_season_phases,
    render_year_over_year_comparison,
    render_annual_statistics,
    render_risk_analysis,
)

st.set_page_config(page_title="Year Overview", page_icon="📊", layout="wide")


def get_gear_name(gear_id: str | None, settings) -> str:
    """Get human-readable gear name from ID."""
    if not gear_id or pd.isna(gear_id):
        return "Unknown"
    return settings.gear_names.get(gear_id, gear_id)


# Alias for backward compatibility with components
calculate_time_weighted_tid = calculate_tid

# This is used by components module for imports
__all__ = ["get_gear_name", "calculate_time_weighted_tid"]


def main():
    """Main page orchestrator."""
    st.title("📊 Year Overview")

    if "activity_service" not in st.session_state:
        st.error(
            "Service not initialized. Please run the app from the main entry point."
        )
        return

    service: ActivityService = st.session_state.activity_service
    settings = st.session_state.get("settings")

    # Year Selector
    available_years = service.get_available_years()
    if not available_years:
        st.warning("No activities found.")
        return

    selected_year, metric_view = render_year_selector(available_years)

    # --- Data Loading ---
    activities_current = service.get_activities_for_year(selected_year, metric_view)
    if not activities_current:
        st.info(f"No activities found for {selected_year}.")
        return

    df_current = pd.DataFrame([a.model_dump() for a in activities_current])

    # Previous Year (for comparison)
    prev_year = selected_year - 1
    activities_prev = service.get_activities_for_year(prev_year, metric_view)
    df_prev = (
        pd.DataFrame([a.model_dump() for a in activities_prev])
        if activities_prev
        else pd.DataFrame()
    )

    # Sport type filter
    with st.sidebar:
        available_sports = sorted(df_current["sport_type"].unique().tolist())
        selected_sports = st.multiselect(
            "Sport Types",
            available_sports,
            default=available_sports,
            help="Filter by sport type",
        )

    # Apply sport filter
    df = df_current[df_current["sport_type"].isin(selected_sports)].copy()
    if df.empty:
        st.warning("No activities match the selected filters.")
        return

    df_prev_filtered = pd.DataFrame()
    if not df_prev.empty:
        df_prev_filtered = df_prev[df_prev["sport_type"].isin(selected_sports)].copy()

    # KPI Section
    render_kpi_section(
        df,
        df_prev_filtered,
        metric_view,
        HELP_TEXTS,
        safe_mean,
        safe_sum,
    )
    st.divider()

    # Power Curve PRs
    with st.expander("🏆 Power Curve PRs", expanded=False):
        render_power_curve_section(df, HELP_TEXTS)

    # TID Analysis
    with st.expander("📊 Training Intensity Distribution", expanded=False):
        render_tid_section(
            df,
            metric_view,
            calculate_time_weighted_tid,
            safe_mean,
            HELP_TEXTS,
            selected_year,
        )

    # Training Load Progression (CTL/ATL/TSB)
    render_training_load_section(df)
    st.divider()

    # Tabs for detailed analysis
    tab_trends, tab_efficiency, tab_gear, tab_dist, tab_weekday = st.tabs(
        [
            "📅 Monthly Trends",
            "⚡ Efficiency & Fatigue",
            "🚲 Gear Usage",
            "📊 Distributions",
            "📆 Patterns",
        ]
    )

    with tab_trends:
        render_trends_tab(df, metric_view, safe_mean)

    with tab_efficiency:
        # Pre-calculate metrics for efficiency tab (columns no longer have prefixes)
        avg_ef = safe_mean(df.get("efficiency_factor", pd.Series(dtype=float)))
        avg_fatigue = safe_mean(df.get("fatigue_index", pd.Series(dtype=float)))
        render_efficiency_tab(df, metric_view, safe_mean, HELP_TEXTS, avg_ef, avg_fatigue)

    with tab_gear:
        render_gear_tab(df, settings, HELP_TEXTS, get_gear_name)

    with tab_dist:
        render_distributions_tab(df, metric_view, safe_mean)

    with tab_weekday:
        render_patterns_tab(df, metric_view)

    # Activity Extremes
    render_extremes_section(df, metric_view, format_duration)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4: Advanced Annual Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    # Section 4.1: Performance Trajectory
    with st.expander("📈 Performance Trajectory", expanded=False):
        render_performance_trajectory(df, selected_year, HELP_TEXTS)

    with st.expander("📅 Season Phases", expanded=False):
        render_season_phases(df, selected_year, HELP_TEXTS)

    with st.expander("📊 Year-over-Year Comparison", expanded=False):
        render_year_over_year_comparison(df, df_prev_filtered, selected_year, HELP_TEXTS)

    with st.expander("📋 Annual Statistics", expanded=False):
        render_annual_statistics(df, selected_year, format_duration, HELP_TEXTS)

    with st.expander("⚠️ Risk Analysis", expanded=False):
        render_risk_analysis(df, selected_year, HELP_TEXTS)


if __name__ == "__main__":
    main()
