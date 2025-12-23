"""Goal progress tracking component."""

from datetime import datetime

import pandas as pd
import streamlit as st

from activities_viewer.config import Settings


def render_goal_progress(settings: Settings, current_ftp: float | None = None) -> None:
    """Render goal progress section.

    Args:
        settings: App settings with goal configuration
        current_ftp: Current estimated FTP (optional, defaults to config FTP)
    """
    if not settings.target_wkg:
        return  # No goal configured

    # Use provided FTP or default to config FTP
    if current_ftp is None:
        current_ftp = settings.ftp

    st.header("🎯 Goal Progress")

    current_wkg = current_ftp / settings.weight_kg
    target_wkg = settings.target_wkg
    baseline_ftp = settings.baseline_ftp or settings.ftp
    baseline_wkg = baseline_ftp / settings.weight_kg

    # Calculate progress
    total_gain_needed = target_wkg - baseline_wkg
    current_gain = current_wkg - baseline_wkg
    progress_pct = (
        (current_gain / total_gain_needed * 100) if total_gain_needed > 0 else 0
    )

    # Time remaining
    weeks_remaining = None
    days_remaining = None
    if settings.target_date:
        try:
            target_dt = datetime.strptime(settings.target_date, "%Y-%m-%d")
            days_remaining = (target_dt - datetime.now()).days
            weeks_remaining = days_remaining / 7
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 1: HERO METRICS (3 columns, large)
    # ═══════════════════════════════════════════════════════════════════════════

    col1, col2, col3 = st.columns(3)

    with col1:
        delta = f"+{current_gain:.2f}" if current_gain > 0 else f"{current_gain:.2f}"
        st.metric(
            "Current W/kg",
            f"{current_wkg:.2f}",
            delta=delta,
            help="Your current FTP divided by weight. Baseline was "
            f"{baseline_wkg:.2f} W/kg ({baseline_ftp:.0f}W @ {settings.weight_kg}kg)",
        )

    with col2:
        st.metric(
            "Target W/kg",
            f"{target_wkg:.2f}",
            help="Your goal W/kg",
        )

    with col3:
        if weeks_remaining is not None:
            required_weekly = (
                (target_wkg - current_wkg) / weeks_remaining
                if weeks_remaining > 0
                else 0
            )
            on_track = required_weekly <= 0.02  # ~0.02 W/kg per week is achievable
            status = "✅ On Track" if on_track else "⚠️ Behind"
            weeks_text = f"{weeks_remaining:.0f} weeks left"
            st.metric(
                "Status",
                status,
                weeks_text,
                help=f"Need +{required_weekly:.3f} W/kg per week to reach goal",
            )
        else:
            st.metric("Progress", f"{progress_pct:.0f}%")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # PROGRESS VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

    # Progress bar
    progress_value = min(progress_pct / 100, 1.0)
    st.progress(progress_value)

    # Progress caption
    st.caption(
        f"Progress: {progress_pct:.1f}% ({current_wkg:.2f} → {target_wkg:.2f} W/kg)"
    )

    # Timeline info
    if days_remaining is not None:
        if days_remaining > 0:
            st.success(
                f"**{days_remaining} days** until target date ({settings.target_date})"
            )
        elif days_remaining == 0:
            st.warning("🎯 **Target date is today!**")
        else:
            st.error(f"⏰ Target date was {abs(days_remaining)} days ago")

    # Breakdown info
    st.caption("Goal Breakdown")
    breakdown_col1, breakdown_col2, breakdown_col3 = st.columns(3)

    with breakdown_col1:
        st.metric(
            "Gain Needed",
            f"+{total_gain_needed:.2f} W/kg",
            help="Total W/kg improvement from baseline to target",
        )

    with breakdown_col2:
        st.metric(
            "Gained So Far",
            f"+{current_gain:.2f} W/kg",
            help="W/kg improvement from baseline to current",
        )

    with breakdown_col3:
        remaining_gain = target_wkg - current_wkg
        st.metric(
            "Remaining",
            f"+{remaining_gain:.2f} W/kg",
            help="W/kg improvement still needed to reach target",
        )
