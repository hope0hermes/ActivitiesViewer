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
    # Volume & Load Metrics
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
    # Training Load State
    "chronic_training_load": (
        "CTL (Chronic Training Load): 42-day exponentially weighted TSS.\n"
        "Represents overall fitness. Higher = more training capacity.\n"
        "• <50: Building phase\n• 50-100: Consistent training\n• 100-150: High fitness\n• >150: Elite"
    ),
    "acute_training_load": (
        "ATL (Acute Training Load): 7-day exponentially weighted TSS.\n"
        "Represents recent fatigue. High values indicate accumulated stress.\n"
        "• <50: Fresh\n• 50-100: Normal training\n• >100: High fatigue"
    ),
    "training_stress_balance": (
        "TSB (Training Stress Balance): CTL - ATL.\n"
        "Indicates form/freshness. Optimal race readiness: -10 to +20.\n"
        "• >20: Very fresh (may lose fitness)\n• 0-20: Race ready\n• -10 to 0: Productive training\n• <-10: Overreached"
    ),
    "acwr": (
        "ACWR (Acute:Chronic Workload Ratio): ATL ÷ CTL.\n"
        "Injury risk indicator. Sweet spot: 0.8-1.3.\n"
        "• <0.8: Undertraining\n• 0.8-1.3: Optimal\n• 1.3-1.5: Caution\n• >1.5: High injury risk"
    ),
    # Power Profile
    "cp": (
        "CP (Critical Power): Maximum sustainable power for extended efforts (>3 min).\n"
        "Derived from power-duration curve. Similar to FTP.\n"
        "• <200W: Beginner\n• 200-300W: Fit\n• 300-400W: Very fit\n• >400W: Elite"
    ),
    "w_prime": (
        "W' (W-prime): Anaerobic work capacity above CP.\n"
        "Amount of work available for efforts above CP before exhaustion.\n"
        "• <15kJ: Low\n• 15-25kJ: Average\n• >25kJ: High anaerobic capacity"
    ),
    "cp_r_squared": (
        "R² (Model Fit Quality): Goodness of fit for CP model (0-1).\n"
        "Higher values = more reliable CP and W' estimates.\n"
        "• <0.85: Poor fit\n• 0.85-0.95: Good\n• >0.95: Excellent"
    ),
    "aei": (
        "AEI (Aerobic Efficiency Index): Normalized anaerobic capacity (J/kg).\n"
        "Indicates athlete profile type.\n"
        "• <0.7: Balanced\n• 0.7-0.85: Aerobic bias\n• >0.85: Strong aerobic profile"
    ),
    # Section 2: Recovery & Readiness
    "rest_days": """Days with no activity or TSS < 20.
Adequate recovery time prevents overtraining and allows adaptation.
• 2+: ✅ Good recovery
• 1: ⚠️ May need more rest
• 0: 🔴 High overtraining risk""",
    "monotony": """Mean daily TSS divided by standard deviation.
Measures training variety. Lower values indicate better variation.
• <1.5: ✅ Good variety
• 1.5-2.0: ⚠️ Moderate risk
• >2.0: 🔴 Too repetitive""",
    "strain": """Weekly TSS × Monotony Index.
Combines training load with variation. Higher values = greater stress.
• <3000: ✅ Manageable
• 3000-6000: ⚠️ Moderate
• >6000: 🔴 High strain""",
    # Section 2: Progressive Overload
    "this_week_tss": """Total Training Stress Score for the current week.
Quantifies overall training load across all activities.""",
    "four_week_avg_tss": """Average weekly TSS over the previous 4 weeks.
Provides baseline for comparing current week's load.""",
    "progression": """Week-over-week TSS change as percentage.
Optimal progression: 3-10% increase per week.
• +3 to +10%: ✅ Optimal
• +10 to +20%: ⚠️ Monitor recovery
• >+20%: 🔴 High risk
• <-10%: 💤 Recovery week""",
    # Section 2: Intensity-Specific Volume
    "z2_volume": """Time spent in Zone 2 (56-75% FTP).
Aerobic base building, mitochondrial adaptation.
Target: 60-80% of weekly volume for base phase.""",
    "sweet_spot_time": """Time at 88-94% FTP (Sweet Spot range).
Highly effective for FTP improvement.
Target: 10-20% of weekly volume during build phase.""",
    "vo2max_time": """Time above 90% FTP (VO2max and above).
High intensity training for maximal aerobic power.
Target: 5-10% of weekly volume.""",
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

def calculate_weekly_tid(df: pd.DataFrame, metric_view: str = "Moving Time") -> dict:
    """Calculate time-weighted TID across multiple activities."""
    # Note: Column names no longer have prefixes (raw and moving are in separate files)
    z1_col = "power_tid_z1_percentage"
    z2_col = "power_tid_z2_percentage"
    z3_col = "power_tid_z3_percentage"

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
