"""
Activity Detail Page.
Displays detailed metrics, maps, and charts for a single activity.

This page uses extracted components for modular organization.
"""

import pandas as pd
import streamlit as st

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.pages.components.activity_detail_components import (
    render_activity_selector,
    render_activity_navigation,
    render_overview_tab,
    render_power_hr_tab,
    render_durability_tab,
    render_training_load_tab,
)

st.set_page_config(page_title="Activity Detail", page_icon="🚴", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
# HELP TEXTS
# ═══════════════════════════════════════════════════════════════════════════════

HELP_TEXTS = {
    # Power Metrics
    "avg_power": "Time-weighted average power. Moving variant excludes stopped time.",
    "normalized_power": (
        "NP represents the power you could have maintained for the same physiological "
        "cost if output had been constant. Uses 30s rolling average raised to 4th power. "
        "More accurate than average power for variable efforts."
    ),
    "intensity_factor": """IF = NP / FTP. Categorizes workout intensity:
• <0.75: Recovery
• 0.75-0.85: Endurance
• 0.85-0.95: Tempo
• 0.95-1.05: Threshold
• >1.05: VO2max""",
    "tss": """Training Stress Score = (duration × NP × IF) / (FTP × 3600) × 100. Quantifies total training load. Reference:
• <150: Low
• 150-300: Medium
• 300-450: High
• >450: Very High""",
    "variability_index": """VI = NP / Avg Power. Indicates power consistency:
• 1.0-1.02: Very steady (time trial)
• 1.02-1.05: Steady (solo ride)
• 1.05-1.15: Variable (group ride)
• >1.15: Highly variable (crits, surges)""",
    "efficiency_factor": (
        "EF = NP / Avg HR. Tracks aerobic efficiency - higher is better. "
        "Compare over time for similar efforts to track fitness gains."
    ),
    "decoupling": (
        "% change in EF from 1st to 2nd half. Negative = fatigue/dehydration. "
        ">5% drift indicates aerobic system as limiter. Requires 1hr+ steady effort."
    ),
    # Fatigue Metrics
    "fatigue_index": """% power decline from initial to final 5 minutes:
• 0-5%: Excellent pacing
• 5-15%: Good pacing
• 15-25%: Moderate fatigue
• >25%: Poor pacing or high fatigue""",
    "power_decay": """% power decrease from first to second half:
• <5%: Excellent sustainability
• 5-10%: Good
• 10-20%: Moderate fade
• >20%: Significant decay""",
    "hr_fatigue_index": """% HR increase from initial to final 5 minutes:
• 0-5%: Excellent control
• 5-10%: Good
• 10-20%: Moderate drift
• >20%: Significant drift""",
    "hr_decay": """% HR increase from first to second half:
• <5%: Excellent control
• 5-10%: Good
• 10-20%: Moderate drift
• >20%: Significant drift""",
    # TID Metrics
    "polarization_index": """PI = (Z1% + Z3%) / Z2%. Higher = more polarized:
• >4.0: Highly polarized (ideal for endurance)
• 2-4: Moderately polarized
• <2: Pyramidal or threshold-focused""",
    "tdr": """Training Distribution Ratio = Z1% / Z3%:
• >2.0: Polarized training
• 1-2: Balanced
• <1: High-intensity focused""",
    "tid_classification": """Training type based on intensity distribution:
• Polarized: Z1+Z3 dominant, minimal Z2
• Pyramidal: Z1 > Z2 > Z3
• Threshold: Z2 dominant""",
    # Longitudinal Training Load Metrics
    "chronic_training_load": (
        "CTL - Chronic Training Load. 42-day exponential moving average of TSS. "
        "Represents aerobic fitness/adaptation level. Higher values indicate accumulated training stress and fitness gains."
    ),
    "acute_training_load": (
        "ATL - Acute Training Load. 7-day exponential moving average of TSS. "
        "Represents short-term fatigue/stress. High ATL relative to CTL indicates overtraining risk."
    ),
    "training_stress_balance": """TSB = CTL - ATL. Balance between fitness and fatigue:
• >20: Well-rested, good for intensity
• 0-20: Optimal training zone
• -10 to 0: Productive training, elevated fatigue
• -50 to -10: Overreached, needs recovery""",
    "acwr": """ACWR - Acute:Chronic Workload Ratio = ATL / CTL. Injury risk indicator:
• 0.8-1.3: Optimal for adaptation
• >1.5: High injury/overtraining risk
• <0.5: Insufficient training stimulus""",
    # Critical Power Metrics
    "cp": (
        "Critical Power (watts). Maximum sustainable power for extended efforts (>10min). "
        "Asymptote of power-duration curve. Computed from 90-day rolling power curve of this activity."
    ),
    "w_prime": (
        "W-prime (joules). Anaerobic work capacity above critical power. "
        "Depletes during intense efforts, recovers during rest. Computed from 90-day rolling power curve."
    ),
    "cp_r_squared": """R² of CP model fit (0-1). Goodness of power-duration curve fit:
• >0.95: Excellent fit
• 0.85-0.95: Good fit
• <0.85: Consider model quality""",
    "aei": (
        "AEI - Anaerobic Energy Index (J/kg). W-prime normalized to body weight. "
        "Higher = greater anaerobic capacity per kg. Compare over time for phenotype shifts."
    ),
    # NEW: Advanced Power Metrics
    "negative_split_index": """NP 2nd half / NP 1st half. Pacing analysis:
• >1.05: Negative split (building power) ✅
• 0.95-1.05: Even pacing ✅
• 0.85-0.95: Slight fade ⚠️
• <0.85: Significant fade 🔴""",
    "match_burn_count": """Number of significant W' expenditures (>50% depletion). Quantifies hard efforts/attacks:
• 0-2: Steady ride
• 3-5: Typical interval workout
• 6-10: Dynamic group ride
• >10: Criterium racing""",
    "time_above_90_ftp": """Seconds above 90% FTP (VO2max zone). High-intensity training stimulus:
• 0-5 min: Easy/recovery
• 5-15 min: Moderate stimulus
• 15-30 min: Significant workout
• >30 min: Hard VO2max session""",
    "cardiac_drift": """(EF 1st half - EF 2nd half) / EF 1st half × 100%. Aerobic fitness indicator:
• <3%: Excellent aerobic fitness ✅
• 3-5%: Good fitness ✅
• 5-8%: Moderate drift ⚠️
• >8%: Poor fitness or fatigue 🔴""",
    "estimated_ftp": """FTP estimate from best 20-min power × 0.95. Track progression:
• Compare to configured FTP
• Rising estimates = improving fitness
• Requires rides >20 minutes with sustained effort""",
    # NEW: Climbing Metrics
    "vam": """Velocità Ascensionale Media (m/h). Vertical ascent rate:
• <800 m/h: Recreational
• 800-1000 m/h: Strong amateur
• 1000-1200 m/h: Cat 2-3 racer
• 1200-1400 m/h: Cat 1/Pro domestic
• >1600 m/h: World Tour climber""",
    "climbing_time": (
        "Seconds spent on positive gradients. Shows climbing volume in the ride."
    ),
    "climbing_power": (
        "Average power on gradients >4%. Shows sustained climbing strength."
    ),
    "climbing_power_per_kg": """Climbing power / weight (W/kg). THE key metric for climbing:
• <3.0 W/kg: Recreational
• 3.0-3.5 W/kg: Strong amateur
• 3.5-4.0 W/kg: Cat 2-3 racer
• 4.0-4.5 W/kg: Cat 1/Pro domestic
• >5.5 W/kg: World Tour climber""",
    # 300s Interval Analysis
    "interval_300s_decay_rate": """% power decline across 300s intervals during the ride. Indicator of power sustainability:
• <5%: Excellent power maintenance
• 5-15%: Good power sustainability
• 15-25%: Moderate power drop
• >25%: Significant fatigue/power loss""",
    "interval_300s_power_trend": """Average change in power per 300s interval (W/interval). Trend direction:
• Positive: Building power across workout
• Negative: Declining power (fatigue accumulating)
• Near zero: Stable power throughout""",
    # HR Zone Distribution (TID) and Polarization
    "hr_polarization_index": """HR-based PI = (Z1% + Z3%) / Z2%. Training intensity distribution:
• >4.0: Highly polarized (ideal for endurance)
• 2-4: Moderately polarized
• <2: Pyramidal or threshold-focused""",
    "hr_tid_z1_percentage": """Percentage of activity in Z1 (Zone 1 - Recovery/Endurance). HR below aerobic threshold.
Higher % indicates emphasis on aerobic base building and recovery.""",
    "hr_tid_z2_percentage": """Percentage of activity in Z2 (Tempo/Threshold). HR at sustained intensity level.
Used to build aerobic capacity while maintaining conversational pace.""",
    "hr_tid_z3_percentage": """Percentage of activity in Z3 (VO2max/Anaerobic). HR at high intensity.
Short high-intensity efforts for aerobic power and capacity building.""",
    # Basic metrics (previously missing)
    "average_hr": "Time-weighted average heart rate during activity.",
    "max_hr": "Maximum heart rate recorded during the activity.",
    "average_cadence": "Average pedal cadence (RPM). Indicates pedaling efficiency and style.",
    "kilojoules": "Total energy expended during activity. Based on power and duration.",
    "moving_time": "Total time the bike was in motion (excludes stopped time).",
    "elapsed_time": "Total time from activity start to finish (includes stops).",
}

# Helper functions (kept from original, needed by components)


def format_duration(seconds: float) -> str:
    """Format seconds into hours and minutes."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def apply_smoothing(data: pd.Series, window_size: int) -> pd.Series:
    """Apply rolling average smoothing to a series."""
    if window_size is None or window_size <= 1:
        return data
    return data.rolling(window=window_size, center=True, min_periods=1).mean()


def get_metric(activity, field: str, default=None):
    """Safely get a metric value, handling NaN."""
    val = getattr(activity, field, default)
    if val is not None and pd.notna(val):
        return val
    return default


# This is used by the components module for imports
__all__ = ["format_duration", "apply_smoothing", "get_metric"]


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
