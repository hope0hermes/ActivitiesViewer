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
)

st.set_page_config(page_title="Year Overview", page_icon="📊", layout="wide")

# ============================================================================
# HELP TEXTS
# ============================================================================
HELP_TEXTS = {
    "tss": """**Training Stress Score (TSS)**
    Quantifies total training load for the year. Higher values indicate more training stress accumulated.
    - <3000: Light training year
    - 3000-6000: Moderate training year
    - 6000-10000: Serious amateur
    - >10000: Elite/Professional level training""",
    "tid": """**Training Intensity Distribution (TID)**
    How your training is distributed across intensity zones:
    - **Zone 1 (Low)**: Below aerobic threshold - recovery and base building
    - **Zone 2 (Moderate)**: Between thresholds - tempo/sweetspot work
    - **Zone 3 (High)**: Above lactate threshold - hard intervals

    **Polarized training** targets 80% Zone 1, minimal Zone 2, 15-20% Zone 3.""",
    "polarization_index": """**Polarization Index**
    Measures how polarized your training is:
    - **>2.0**: Well-polarized (good for endurance)
    - **1.5-2.0**: Moderately polarized
    - **<1.5**: Threshold-focused (more Zone 2)

    Research suggests polarized training is most effective for endurance.""",
    "efficiency_factor": """**Efficiency Factor (EF)**
    Ratio of Normalized Power to Average Heart Rate (NP/HR).
    - **Higher is better** - more power for same cardiac effort
    - Trending upward over year = improving aerobic fitness
    - Seasonal variations are normal""",
    "fatigue_index": """**Fatigue Index**
    Measures power degradation over activities:
    - **<5%**: Excellent fatigue resistance
    - **5-10%**: Good endurance
    - **10-15%**: Average
    - **>15%**: Indicates fatigue issues

    Lower is better - shows ability to maintain power.""",
    "power_curve": """**Power Curve PRs**
    Best power outputs for various durations throughout the year.
    These represent your peak performance capabilities:
    - **5s-30s**: Neuromuscular power (sprints)
    - **1-5min**: Anaerobic capacity (VO2max efforts)
    - **20min-1hr**: Threshold/FTP power (sustained efforts)""",
    "gear_usage": """**Gear Usage Statistics**
    Breakdown of distance, time, and elevation by equipment.
    Helps track:
    - Equipment wear and maintenance needs
    - Training distribution across bikes
    - Preferred equipment for different activities""",
}


def format_duration(seconds: float) -> str:
    """Format seconds into hours and minutes."""
    if pd.isna(seconds) or seconds == 0:
        return "0h 0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def safe_mean(series: pd.Series) -> float:
    """Calculate mean, handling NaN values."""
    valid = series.dropna()
    return valid.mean() if len(valid) > 0 else 0.0


def safe_sum(series: pd.Series) -> float:
    """Calculate sum, handling NaN values."""
    return series.fillna(0).sum()


def get_gear_name(gear_id: str | None, settings) -> str:
    """Get human-readable gear name from ID."""
    if not gear_id or pd.isna(gear_id):
        return "Unknown"
    return settings.gear_names.get(gear_id, gear_id)


def calculate_time_weighted_tid(df: pd.DataFrame, metric_view: str = "Moving Time") -> dict:
    """Calculate time-weighted TID percentages for a group of activities."""
    # Note: Column names no longer have prefixes (raw and moving are in separate files)
    z1_col = "power_tid_z1_percentage"
    z2_col = "power_tid_z2_percentage"
    z3_col = "power_tid_z3_percentage"

    # Filter to activities that have TID data
    valid_df = df.dropna(subset=[z1_col, z2_col, z3_col])

    if valid_df.empty:
        return {"z1": 0, "z2": 0, "z3": 0}

    # Weight by moving time
    total_time = valid_df["moving_time"].sum()
    if total_time == 0:
        return {"z1": 0, "z2": 0, "z3": 0}

    weighted_z1 = (valid_df[z1_col] * valid_df["moving_time"]).sum() / total_time
    weighted_z2 = (valid_df[z2_col] * valid_df["moving_time"]).sum() / total_time
    weighted_z3 = (valid_df[z3_col] * valid_df["moving_time"]).sum() / total_time

    return {"z1": weighted_z1, "z2": weighted_z2, "z3": weighted_z3}


# This is used by components module for imports
__all__ = ["format_duration", "safe_mean", "safe_sum", "get_gear_name", "calculate_time_weighted_tid"]


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
    render_power_curve_section(df, HELP_TEXTS)
    st.divider()

    # TID Analysis
    render_tid_section(
        df,
        metric_view,
        calculate_time_weighted_tid,
        safe_mean,
        HELP_TEXTS,
        selected_year,
    )
    st.divider()

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


if __name__ == "__main__":
    main()
