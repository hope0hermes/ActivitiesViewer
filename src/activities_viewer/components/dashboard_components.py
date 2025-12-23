"""
Dashboard Components - Hero components for the main dashboard.

This module provides the visual components for the new goal-driven dashboard:
- Goal Progress Card: Visual progress toward training goal
- Current Status Card: PMC state (CTL/ATL/TSB)
- Recent Activity Sparklines: Last 7 days of volume and intensity
"""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from activities_viewer.services.goal_service import GoalService, GoalStatus
from activities_viewer.domain.models import Goal
from activities_viewer.utils.formatting import format_watts, format_wkg, format_duration


def render_goal_progress_card(
    goal: Goal,
    current_ftp: float,
    weight_kg: float,
    goal_service: Optional[GoalService] = None,
) -> None:
    """
    Render the hero goal progress card.

    Shows visual progress bar from start to target W/kg with status indicators.

    Args:
        goal: Goal object with target and timeline
        current_ftp: Current FTP in watts
        weight_kg: Current body weight in kg
        goal_service: GoalService instance (creates one if not provided)
    """
    if goal_service is None:
        goal_service = GoalService()

    # Get comprehensive goal summary
    summary = goal_service.get_goal_summary(current_ftp, weight_kg, goal)

    st.subheader("🎯 Goal Progress")

    # ═══════════════════════════════════════════════════════════════════════════
    # TOP ROW: Key Metrics
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Current",
            format_wkg(summary["current_wkg"]),
            delta=f"{summary['ahead_behind_wkg']:+.3f} W/kg",
            delta_color="normal" if summary["on_pace"] else "inverse",
            help=f"Current: {current_ftp:.0f} W / {weight_kg:.1f} kg",
        )

    with col2:
        st.metric(
            "Target",
            format_wkg(summary["target_wkg"]),
            help=f"Goal by {goal.target_date.strftime('%b %d, %Y')}",
        )

    with col3:
        # Status with color coding
        status_emoji = {
            GoalStatus.AHEAD: "🚀",
            GoalStatus.ON_TRACK: "✅",
            GoalStatus.BEHIND: "⚠️",
            GoalStatus.CRITICAL: "🔴",
        }
        emoji = status_emoji.get(summary["status"], "")

        st.metric(
            "Status",
            f"{emoji} {summary['status_label']}",
            help=f"Expected now: {summary['expected_wkg_now']:.2f} W/kg",
        )

    with col4:
        weeks_left = summary["weeks_remaining"]
        st.metric(
            "Time Remaining",
            f"{weeks_left:.1f} weeks",
            delta=f"{summary['days_remaining']} days",
            help=f"Target date: {goal.target_date.strftime('%B %d, %Y')}",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PROGRESS BAR
    # ═══════════════════════════════════════════════════════════════════════════
    progress_value = min(max(summary["progress_percentage"] / 100, 0), 1.0)

    # Color based on status
    if summary["status"] == GoalStatus.AHEAD:
        bar_color = "#28a745"  # Green
    elif summary["status"] == GoalStatus.ON_TRACK:
        bar_color = "#17a2b8"  # Blue
    elif summary["status"] == GoalStatus.BEHIND:
        bar_color = "#ffc107"  # Yellow
    else:  # CRITICAL
        bar_color = "#dc3545"  # Red

    # Custom HTML progress bar for color control
    st.markdown(
        f"""
        <div style="margin: 10px 0;">
            <div style="background-color: #e9ecef; border-radius: 5px; height: 30px; position: relative;">
                <div style="background-color: {bar_color}; width: {progress_value * 100}%; height: 100%; border-radius: 5px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">{summary["progress_percentage"]:.1f}%</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # BOTTOM ROW: Required Effort
    # ═══════════════════════════════════════════════════════════════════════════
    col1, col2 = st.columns(2)

    with col1:
        wkg_remaining = summary["wkg_remaining"]
        ftp_remaining = wkg_remaining * weight_kg
        st.info(
            f"**Remaining Improvement Needed:** {wkg_remaining:.3f} W/kg ({ftp_remaining:.0f} W)",
            icon="🎯",
        )

    with col2:
        weekly_gain = summary["required_weekly_gain"]
        weekly_watts = weekly_gain * weight_kg

        # Determine if the required rate is achievable
        # Typical sustained gains: 0.01-0.02 W/kg per week
        if weekly_gain <= 0:
            msg = "🏆 **Goal achieved!** Maintain your fitness."
            msg_type = "success"
        elif weekly_gain <= 0.015:
            msg = f"✅ **Required Rate:** {weekly_gain:.4f} W/kg/week ({weekly_watts:.1f} W) - Achievable"
            msg_type = "success"
        elif weekly_gain <= 0.025:
            msg = f"⚠️ **Required Rate:** {weekly_gain:.4f} W/kg/week ({weekly_watts:.1f} W) - Challenging"
            msg_type = "warning"
        else:
            msg = f"🔴 **Required Rate:** {weekly_gain:.4f} W/kg/week ({weekly_watts:.1f} W) - Very Difficult"
            msg_type = "error"

        if msg_type == "success":
            st.success(msg, icon="💪")
        elif msg_type == "warning":
            st.warning(msg, icon="⚡")
        else:
            st.error(msg, icon="🚨")


def render_status_card(pmc_data: pd.DataFrame) -> None:
    """
    Render current PMC status card.

    Shows CTL (Fitness), ATL (Fatigue), TSB (Form) with color coding.

    Args:
        pmc_data: DataFrame with ctl, atl, tsb columns
    """
    st.subheader("📊 Current Training Status")

    if pmc_data.empty:
        st.info(
            "No PMC data available. Complete more activities to see your fitness trends."
        )
        return

    # Get the most recent values
    latest = pmc_data.iloc[-1]
    ctl = latest.get("ctl", 0)
    atl = latest.get("atl", 0)
    tsb = latest.get("tsb", 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        # CTL (Fitness) - higher is better, but very slow to change
        st.metric(
            "Fitness (CTL)",
            f"{ctl:.0f}",
            help="Chronic Training Load - Your long-term fitness (42-day average)",
        )

        # Fitness interpretation
        if ctl > 100:
            fitness_status = "🏆 Excellent"
        elif ctl > 70:
            fitness_status = "💪 Strong"
        elif ctl > 50:
            fitness_status = "✅ Good"
        else:
            fitness_status = "📈 Building"

        st.caption(fitness_status)

    with col2:
        # ATL (Fatigue) - shows recent training load
        st.metric(
            "Fatigue (ATL)",
            f"{atl:.0f}",
            help="Acute Training Load - Your recent training stress (7-day average)",
        )

        # Fatigue interpretation
        if atl > ctl * 1.5:
            fatigue_status = "🔥 Very High"
        elif atl > ctl * 1.2:
            fatigue_status = "😰 High"
        elif atl > ctl * 0.8:
            fatigue_status = "💪 Moderate"
        else:
            fatigue_status = "😌 Low"

        st.caption(fatigue_status)

    with col3:
        # TSB (Form) - the key indicator for readiness
        # Color based on TSB value
        if tsb > 10:
            tsb_color = "normal"  # Green - Fresh
            form_status = "🔋 Fresh"
            form_help = "Well-rested and ready for hard efforts"
        elif tsb > 5:
            tsb_color = "off"  # Neutral - Ready
            form_status = "💪 Ready"
            form_help = "Good balance, ready to train"
        elif tsb > -10:
            tsb_color = "off"  # Neutral - Optimal
            form_status = "⚡ Optimal"
            form_help = "Ideal training state"
        elif tsb > -30:
            tsb_color = "inverse"  # Red - Tired
            form_status = "😴 Tired"
            form_help = "Accumulated fatigue, consider recovery"
        else:
            tsb_color = "inverse"  # Red - Overreached
            form_status = "🚨 Overreached"
            form_help = "High fatigue! Recovery needed"

        st.metric(
            "Form (TSB)",
            f"{tsb:+.0f}",
            delta=form_status,
            delta_color=tsb_color,
            help=f"Training Stress Balance (CTL - ATL). {form_help}",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # TREND VISUALIZATION (Mini Chart)
    # ═══════════════════════════════════════════════════════════════════════════

    # Show last 30 days of PMC if available
    if len(pmc_data) > 1:
        recent_pmc = pmc_data.tail(30)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=recent_pmc["date"]
                if "date" in recent_pmc.columns
                else recent_pmc.index,
                y=recent_pmc["ctl"],
                name="Fitness (CTL)",
                line=dict(color="#17a2b8", width=2),
                mode="lines",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=recent_pmc["date"]
                if "date" in recent_pmc.columns
                else recent_pmc.index,
                y=recent_pmc["atl"],
                name="Fatigue (ATL)",
                line=dict(color="#ffc107", width=2),
                mode="lines",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=recent_pmc["date"]
                if "date" in recent_pmc.columns
                else recent_pmc.index,
                y=recent_pmc["tsb"],
                name="Form (TSB)",
                line=dict(color="#28a745", width=2),
                mode="lines",
                fill="tozeroy",
                fillcolor="rgba(40, 167, 69, 0.1)",
            )
        )

        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title="",
            yaxis_title="TSS",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)


def render_recent_activity_sparklines(
    activities_df: pd.DataFrame, days: int = 7
) -> None:
    """
    Render sparkline charts for recent activity volume and intensity.

    Shows last N days of Volume (hours, bar chart) and Intensity (TSS, line chart).

    Args:
        activities_df: DataFrame with all activities
        days: Number of recent days to display (default: 7)
    """
    st.subheader(f"📈 Last {days} Days")

    if activities_df.empty:
        st.info("No recent activities to display.")
        return

    # Ensure date column is datetime
    df = activities_df.copy()
    df["start_date_local"] = pd.to_datetime(df["start_date_local"])

    # Remove timezone if present
    if df["start_date_local"].dt.tz is not None:
        df["start_date_local"] = df["start_date_local"].dt.tz_localize(None)

    # Filter for last N days
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_df = df[df["start_date_local"] >= cutoff_date].copy()

    if recent_df.empty:
        st.info(f"No activities in the last {days} days.")
        return

    # Aggregate by date
    recent_df["date"] = recent_df["start_date_local"].dt.date
    daily_stats = (
        recent_df.groupby("date")
        .agg({"moving_time": "sum", "training_stress_score": "sum", "distance": "sum"})
        .reset_index()
    )

    # Convert moving time to hours
    daily_stats["hours"] = daily_stats["moving_time"] / 3600
    daily_stats["distance_km"] = daily_stats["distance"] / 1000

    # Create date range to fill missing days
    date_range = pd.date_range(
        start=cutoff_date.date(), end=datetime.now().date(), freq="D"
    )

    full_range = pd.DataFrame({"date": date_range.date})
    daily_stats = full_range.merge(daily_stats, on="date", how="left").fillna(0)

    # ═══════════════════════════════════════════════════════════════════════════
    # DUAL SPARKLINES
    # ═══════════════════════════════════════════════════════════════════════════

    # Create subplots with shared x-axis
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Volume (Hours)", "Training Stress (TSS)"),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5],
    )

    # Volume (Bar chart)
    fig.add_trace(
        go.Bar(
            x=daily_stats["date"],
            y=daily_stats["hours"],
            name="Hours",
            marker_color="#17a2b8",
            hovertemplate="<b>%{x}</b><br>Volume: %{y:.1f}h<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Intensity (Line chart)
    fig.add_trace(
        go.Scatter(
            x=daily_stats["date"],
            y=daily_stats["training_stress_score"],
            name="TSS",
            line=dict(color="#28a745", width=3),
            mode="lines+markers",
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(40, 167, 69, 0.2)",
            hovertemplate="<b>%{x}</b><br>TSS: %{y:.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    fig.update_yaxes(title_text="Hours", row=1, col=1)
    fig.update_yaxes(title_text="TSS", row=2, col=1)

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY STATS
    # ═══════════════════════════════════════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_hours = daily_stats["hours"].sum()
        st.metric("Total Volume", f"{total_hours:.1f}h")

    with col2:
        total_tss = daily_stats["training_stress_score"].sum()
        st.metric("Total TSS", f"{total_tss:.0f}")

    with col3:
        total_distance = daily_stats["distance_km"].sum()
        st.metric("Total Distance", f"{total_distance:.0f} km")

    with col4:
        activity_count = len(recent_df)
        st.metric("Activities", f"{activity_count}")
