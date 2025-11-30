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
    render_overview_tab,
    render_power_hr_tab,
    render_durability_tab,
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
    "intensity_factor": (
        "IF = NP / FTP. Categorizes workout intensity:\n"
        "• <0.75: Recovery\n"
        "• 0.75-0.85: Endurance\n"
        "• 0.85-0.95: Tempo\n"
        "• 0.95-1.05: Threshold\n"
        "• >1.05: VO2max"
    ),
    "tss": (
        "Training Stress Score = (duration × NP × IF) / (FTP × 3600) × 100. "
        "Quantifies total training load. Reference:\n"
        "• <150: Low\n• 150-300: Medium\n• 300-450: High\n• >450: Very High"
    ),
    "variability_index": (
        "VI = NP / Avg Power. Indicates power consistency:\n"
        "• 1.0-1.02: Very steady (time trial)\n"
        "• 1.02-1.05: Steady (solo ride)\n"
        "• 1.05-1.15: Variable (group ride)\n"
        "• >1.15: Highly variable (crits, surges)"
    ),
    "efficiency_factor": (
        "EF = NP / Avg HR. Tracks aerobic efficiency - higher is better. "
        "Compare over time for similar efforts to track fitness gains."
    ),
    "decoupling": (
        "% change in EF from 1st to 2nd half. Negative = fatigue/dehydration. "
        ">5% drift indicates aerobic system as limiter. Requires 1hr+ steady effort."
    ),
    # Fatigue Metrics
    "fatigue_index": (
        "% power decline from initial to final 5 minutes:\n"
        "• 0-5%: Excellent pacing\n"
        "• 5-15%: Good pacing\n"
        "• 15-25%: Moderate fatigue\n"
        "• >25%: Poor pacing or high fatigue"
    ),
    "power_decay": (
        "% power decrease from first to second half:\n"
        "• <5%: Excellent sustainability\n"
        "• 5-10%: Good\n"
        "• 10-20%: Moderate fade\n"
        "• >20%: Significant decay"
    ),
    "hr_fatigue_index": (
        "% HR increase from initial to final 5 minutes:\n"
        "• 0-5%: Excellent control\n"
        "• 5-10%: Good\n"
        "• 10-20%: Moderate drift\n"
        "• >20%: Significant drift"
    ),
    "hr_decay": (
        "% HR increase from first to second half:\n"
        "• <5%: Excellent control\n"
        "• 5-10%: Good\n"
        "• 10-20%: Moderate drift\n"
        "• >20%: Significant drift"
    ),
    # TID Metrics
    "polarization_index": (
        "PI = (Z1% + Z3%) / Z2%. Higher = more polarized:\n"
        "• >4.0: Highly polarized (ideal for endurance)\n"
        "• 2-4: Moderately polarized\n"
        "• <2: Pyramidal or threshold-focused"
    ),
    "tdr": (
        "Training Distribution Ratio = Z1% / Z3%:\n"
        "• >2.0: Polarized training\n"
        "• 1-2: Balanced\n"
        "• <1: High-intensity focused"
    ),
    "tid_classification": (
        "Training type based on intensity distribution:\n"
        "• Polarized: Z1+Z3 dominant, minimal Z2\n"
        "• Pyramidal: Z1 > Z2 > Z3\n"
        "• Threshold: Z2 dominant"
    ),
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

    # Render activity selector
    activity, activity_id, metric_view = render_activity_selector(service)
    if activity is None:
        return

    st.divider()

    # Render tabs with components
    tab_overview, tab_power_hr, tab_durability = st.tabs(
        ["🗺️ Overview", "⚡ Power & Heart Rate", "🔋 Durability & Fatigue"]
    )

    with tab_overview:
        render_overview_tab(activity, service, metric_view, HELP_TEXTS)

    with tab_power_hr:
        render_power_hr_tab(activity, service, metric_view, HELP_TEXTS)

    with tab_durability:
        render_durability_tab(activity, metric_view, HELP_TEXTS)


if __name__ == "__main__":
    main()
