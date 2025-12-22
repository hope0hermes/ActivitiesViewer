"""
Monthly Analysis - Deep-dive into monthly training patterns.

Provides aggregated monthly metrics, TID analysis, week-by-week breakdowns,
trend analysis over 6 months, and complete activity listings.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
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
# HELP TEXTS
# ═══════════════════════════════════════════════════════════════════════════════
HELP_TEXTS = {
    "ctl": """**Chronic Training Load (CTL)** - 42-day exponentially weighted average of daily TSS.
Represents your 'fitness' accumulated over training.
- <50: Building/recovery phase
- 50-80: Moderate training
- 80-120: High performance level
- >120: Elite/peak fitness""",
    "atl": """**Acute Training Load (ATL)** - 7-day exponentially weighted average of daily TSS.
Represents recent training stress ('fatigue').
- Low ATL = well recovered
- High ATL = accumulated fatigue""",
    "tsb": """**Training Stress Balance (TSB)** - Form indicator (CTL - ATL).
- TSB > 20: Very fresh, might need more load
- TSB 0-20: Optimal zone for racing
- TSB -10-0: Productive training zone
- TSB < -10: Overreached, recovery needed""",
    "acwr": """**Acute:Chronic Workload Ratio (ACWR)** - Injury risk indicator.
- <0.8: Undertraining, might lose fitness
- 0.8-1.3: Sweet spot for adaptation
- 1.3-1.5: Caution zone
- >1.5: High injury risk!""",
    "cp": """**Critical Power (CP)** - The boundary between steady-state and non-steady-state exercise.
Maximum power sustainable for efforts >3 minutes.
Your aerobic ceiling - higher CP = better endurance capacity.""",
    "w_prime": """**W' (W-prime)** - Anaerobic work capacity above CP.
The amount of work you can do above CP before exhaustion.
- <15kJ: Lower sprint reserve
- 15-25kJ: Average
- >25kJ: Strong anaerobic capacity""",
    "r_squared": """**R² (R-squared)** - Goodness of fit for CP model.
How well the mathematical model fits your power data.
- <0.90: Fair (use estimates cautiously)
- 0.90-0.95: Good (reliable)
- >0.95: Excellent (very reliable)""",
    "aei": """**Aerobic Endurance Index (AEI)** - Ratio indicating aerobic vs anaerobic profile.
- >0.85: Very aerobic profile
- 0.70-0.85: Aerobic profile
- 0.55-0.70: Balanced
- <0.55: Anaerobic profile""",
    "ef": """**Efficiency Factor (EF)** - Power produced per heartbeat (NP/Avg HR).
Higher EF = better aerobic efficiency. Improves with fitness.
Track over time to monitor aerobic development.""",
    "fatigue_trend": """**Fatigue Index** - Cardiac drift during activity.
Measures how much HR rises relative to power over time.
- Low (<5%): Good durability
- Medium (5-10%): Normal fatigue
- High (>10%): Significant drift""",
    "avg_ef": """Average Efficiency Factor across all rides this month.
Higher values indicate better overall aerobic efficiency.""",
    "tid": """**Training Intensity Distribution (TID)** - Time spent in each intensity zone.
- Z1 Low: Below aerobic threshold (<80% LTHR)
- Z2 Moderate: Between thresholds (80-100% LTHR)
- Z3 High: Above lactate threshold (>100% LTHR)

Polarized training (80% Z1, 20% Z3) is optimal for most athletes.""",
    # Section 3: Fitness Evolution
    "ftp_start": """Estimated FTP at the beginning of the month.
Based on power duration curve analysis from recent activities.""",
    "ftp_end": """Estimated FTP at the end of the month.
Based on power duration curve analysis from recent activities.""",
    "ftp_change": """Change in estimated FTP over the month.
• Positive: Fitness improvement ✅
• Negative: May need recovery or training adjustment ⚠️
• Stable (±2W): Maintenance phase ➡️""",
    # Section 3: Periodization Check
    "volume_vs_avg": """Monthly training volume compared to 3-month rolling average.
• +10% or more: High volume block 📈
• -10% or less: Recovery/taper block 📉
• ±10%: Maintenance ➡️""",
    "intensity_vs_avg": """Average ride intensity (IF) compared to 3-month rolling average.
• Higher: BUILD/PEAK phase (harder efforts) ⚡
• Lower: BASE phase (endurance focus) 🏗️
• Similar: Maintenance ➡️""",
    "long_rides": """Number of rides longer than 3 hours.
Critical for endurance development and aerobic capacity.
Target: 1-2 per week during base phase.""",
    # Section 3: Aerobic Development
    "ef_trend": """Weekly rate of change in Efficiency Factor.
Positive trend = improving aerobic efficiency ✅
• >0.02/week: Significant improvement
• 0-0.02/week: Gradual improvement
• <0: May need more Z2 volume or recovery""",
    "avg_decoupling": """Average cardiac drift across all activities this month.
Lower values indicate better aerobic fitness.
• <5%: Excellent aerobic fitness ✅
• 5-10%: Good aerobic fitness ➡️
• >10%: May need more Z2 base work ⚠️""",
    "decoupling_trend": """Weekly rate of change in cardiac drift.
Negative trend (decreasing drift) = improving aerobic fitness ✅
• <-0.2%/week: Significant improvement
• -0.2 to 0: Gradual improvement
• >0: Increasing fatigue or deconditioning""",
    # Section 3: Training Consistency
    "training_days": """Number of days with at least one activity.
Higher consistency = better adaptation and fitness gains.
• 70%+: Excellent consistency ✅
• 50-70%: Good consistency ➡️
• <50%: Consider improving consistency ⚠️""",
    "longest_streak": """Longest run of consecutive training days.
Very long streaks (>14 days) may indicate need for rest days.""",
    "longest_gap": """Longest period without training.
• 1-3 days: Normal recovery ✅
• 4-7 days: Planned rest week ➡️
• >7 days: Extended break (illness, vacation, etc.) ⚠️""",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    if pd.isna(seconds) or seconds == 0:
        return "-"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


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
    return 0


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
