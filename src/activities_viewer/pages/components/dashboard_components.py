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
from activities_viewer.utils.formatting import format_watts, format_wkg, format_duration, render_metric


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

    value_size = 28
    render_metric(
        col1,
        label="Current W/Kg",
        value=f'{summary["current_wkg"]:.1f}',
        help_text=(
            f"Current: {current_ftp:.0f} W / {weight_kg:.1f} kg\nDelta: "
            f"{summary['ahead_behind_wkg']:+.3f} W/kg"
        ),
        value_size=value_size,
    )

    render_metric(
        col2,
        label="Target W/Kg",
        value=f'{summary["target_wkg"]:.1f}',
        help_text=f"Goal by {goal.target_date.strftime('%b %d, %Y')}",
        value_size=value_size,
    )

    # Status with color coding
    status_emoji = {
        GoalStatus.AHEAD: "🚀",
        GoalStatus.ON_TRACK: "✅",
        GoalStatus.BEHIND: "⚠️",
        GoalStatus.CRITICAL: "🔴",
    }
    emoji = status_emoji.get(summary["status"], "")

    render_metric(
        col3,
        label="Status",
        value=f"{emoji} {summary['status_label']}",
        help_text=f"Expected now: {summary['expected_wkg_now']:.2f} W/kg",
        value_size=value_size - 4,
    )

    render_metric(
        col4,
        label="Weeks Remaining",
        value=f"{int(summary['weeks_remaining']):d}",
        help_text=(
            f"Target date: {goal.target_date.strftime('%B %d, %Y')}\nDays: "
            f"{summary['days_remaining']}"
        ),
        value_size=value_size,
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

    Shows CTL (Fitness), ATL (Fatigue), TSB (Form) with color coding and trend arrows.

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

    # Compute 7-day deltas for trend arrows
    ctl_delta = None
    atl_delta = None
    tsb_delta = None

    if len(pmc_data) >= 7:
        # Get value from 7 days ago
        previous = pmc_data.iloc[-7]
        prev_ctl = previous.get("ctl", 0)
        prev_atl = previous.get("atl", 0)
        prev_tsb = previous.get("tsb", 0)

        if prev_ctl > 0:
            delta = ctl - prev_ctl
            ctl_delta = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        if prev_atl > 0:
            delta = atl - prev_atl
            atl_delta = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        delta = tsb - prev_tsb
        tsb_delta = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"

    col1, col2, col3 = st.columns(3)

    # CTL (Fitness) - higher is better, but very slow to change
    render_metric(
        col1,
        label="Fitness (CTL)",
        value=f"{ctl:.0f}",
        help_text="Chronic Training Load - Your long-term fitness (42-day average)",
        delta=ctl_delta,
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

    with col1:
        st.caption(fitness_status)

    # ATL (Fatigue) - shows recent training load
    render_metric(
        col2,
        label="Fatigue (ATL)",
        value=f"{atl:.0f}",
        help_text="Acute Training Load - Your recent training stress (7-day average)",
        delta=atl_delta,
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

    with col2:
        st.caption(fatigue_status)

    # TSB (Form) - the key indicator for readiness
    # Color based on TSB value
    if tsb > 10:
        form_status = "🔋 Fresh"
        form_help = "Well-rested and ready for hard efforts"
    elif tsb > 5:
        form_status = "💪 Ready"
        form_help = "Good balance, ready to train"
    elif tsb > -10:
        form_status = "⚡ Optimal"
        form_help = "Ideal training state"
    elif tsb > -30:
        form_status = "😴 Tired"
        form_help = "Accumulated fatigue, consider recovery"
    else:
        form_status = "🚨 Overreached"
        form_help = "High fatigue! Recovery needed"

    render_metric(
        col3,
        label="Form (TSB)",
        value=f"{tsb:+.0f}",
        help_text=f"Training Stress Balance (CTL - ATL)\n{form_status}: {form_help}",
        delta=tsb_delta,
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

        st.plotly_chart(fig, width="stretch")


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
        subplot_titles=("", ""),
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

    st.plotly_chart(fig, width="stretch")

    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY STATS
    # ═══════════════════════════════════════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_hours = daily_stats["hours"].sum()
        render_metric(
            col1,
            label="Total Volume",
            value=f"{total_hours:.1f}h",
            help_text="Total training volume in the last 7 days",
        )

    with col2:
        total_tss = daily_stats["training_stress_score"].sum()
        render_metric(
            col2,
            label="Total TSS",
            value=f"{total_tss:.0f}",
            help_text="Total Training Stress Score in the last 7 days",
        )

    with col3:
        total_distance = daily_stats["distance_km"].sum()
        render_metric(
            col3,
            label="Total Distance",
            value=f"{total_distance:.1f} km",
            help_text="Total distance covered in the last 7 days",
        )

    with col4:
        activity_count = len(recent_df)
        render_metric(
            col4,
            label="Activities",
            value=f"{activity_count}",
            help_text="Number of activities in the last 7 days",
        )


def render_training_calendar(
    df: pd.DataFrame,
    months: int = 3,
) -> None:
    """
    Render a GitHub-style training calendar heat map showing daily TSS.

    Shows the last N months of training with:
    - Daily TSS as color intensity (darker = higher load)
    - Rest days clearly visible (gray/empty)
    - Week structure preserved (Mon-Sun rows)

    Args:
        df: DataFrame of activities with start_date_local and training_stress_score
        months: Number of months to display (default: 3)
    """
    import numpy as np
    from datetime import date
    import calendar

    st.subheader("📅 Training Calendar")

    if df.empty:
        st.info("No activities available to display in calendar.")
        return

    # Prepare data
    df_copy = df.copy()
    df_copy["start_date_local"] = pd.to_datetime(df_copy["start_date_local"])
    if df_copy["start_date_local"].dt.tz is not None:
        df_copy["start_date_local"] = df_copy["start_date_local"].dt.tz_localize(None)

    df_copy["date"] = df_copy["start_date_local"].dt.date

    # Aggregate TSS per day (in case of multiple activities)
    daily_tss = df_copy.groupby("date")["training_stress_score"].sum().reset_index()
    daily_tss.columns = ["date", "tss"]

    # Create date range for the last N months
    end_date = date.today()
    start_date = date(end_date.year, end_date.month, 1) - timedelta(days=30 * (months - 1))
    # Align to Monday of that week
    start_date = start_date - timedelta(days=start_date.weekday())

    # Create full date range
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    full_dates = pd.DataFrame({"date": [d.date() for d in date_range]})

    # Merge with actual TSS data
    calendar_data = full_dates.merge(daily_tss, on="date", how="left")
    calendar_data["tss"] = calendar_data["tss"].fillna(0)

    # Add week and day information
    calendar_data["weekday"] = pd.to_datetime(calendar_data["date"]).dt.weekday  # 0=Mon, 6=Sun
    calendar_data["week"] = pd.to_datetime(calendar_data["date"]).dt.isocalendar().week
    calendar_data["year"] = pd.to_datetime(calendar_data["date"]).dt.year
    calendar_data["month"] = pd.to_datetime(calendar_data["date"]).dt.month

    # Create week index for x-axis (continuous weeks across months)
    calendar_data["week_idx"] = (
        (pd.to_datetime(calendar_data["date"]) - pd.to_datetime(start_date)).dt.days // 7
    )

    # Create the heatmap using Plotly
    # Pivot to create matrix: rows=weekday, cols=week_idx
    pivot = calendar_data.pivot(index="weekday", columns="week_idx", values="tss")

    # Get date labels for hover
    date_labels = calendar_data.pivot(index="weekday", columns="week_idx", values="date")

    # Define color scale based on TSS thresholds
    # Rest day: 0, Easy: 1-50, Moderate: 50-100, Hard: 100-150, Very Hard: 150+
    max_tss = calendar_data["tss"].max() if calendar_data["tss"].max() > 0 else 100

    # Create custom hover text
    hover_text = []
    for weekday in range(7):
        row_text = []
        for week_idx in pivot.columns:
            if weekday in pivot.index and week_idx in pivot.columns:
                tss_val = pivot.loc[weekday, week_idx] if pd.notna(pivot.loc[weekday, week_idx]) else 0
                date_val = date_labels.loc[weekday, week_idx] if pd.notna(date_labels.loc[weekday, week_idx]) else ""
                if tss_val == 0:
                    intensity = "Rest Day"
                elif tss_val < 50:
                    intensity = "Easy"
                elif tss_val < 100:
                    intensity = "Moderate"
                elif tss_val < 150:
                    intensity = "Hard"
                else:
                    intensity = "Very Hard"
                row_text.append(f"{date_val}<br>TSS: {tss_val:.0f}<br>{intensity}")
            else:
                row_text.append("")
        hover_text.append(row_text)

    # Weekday labels
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Get month labels for x-axis
    month_positions = []
    month_labels = []
    for week_idx in sorted(pivot.columns):
        dates_in_week = calendar_data[calendar_data["week_idx"] == week_idx]["date"].values
        if len(dates_in_week) > 0:
            first_date = pd.to_datetime(dates_in_week[0])
            if first_date.day <= 7:  # First week of month
                month_positions.append(week_idx)
                month_labels.append(first_date.strftime("%b"))

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=weekday_labels,
            colorscale=[
                [0, "#ebedf0"],      # Rest day (light gray)
                [0.01, "#c6e48b"],   # Very easy (light green)
                [0.25, "#7bc96f"],   # Easy (green)
                [0.5, "#239a3b"],    # Moderate (darker green)
                [0.75, "#196127"],   # Hard (dark green)
                [1.0, "#0e4429"],    # Very hard (very dark green)
            ],
            hoverinfo="text",
            text=hover_text,
            showscale=True,
            colorbar=dict(
                title="TSS",
                tickvals=[0, max_tss * 0.25, max_tss * 0.5, max_tss * 0.75, max_tss],
                ticktext=["Rest", "Easy", "Mod", "Hard", "V.Hard"],
            ),
            xgap=2,
            ygap=2,
        )
    )

    fig.update_layout(
        height=200,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(
            tickmode="array",
            tickvals=month_positions,
            ticktext=month_labels,
            side="bottom",
            showgrid=False,
        ),
        yaxis=dict(
            showgrid=False,
            autorange="reversed",  # Mon at top
        ),
        plot_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary stats below calendar
    col1, col2, col3, col4 = st.columns(4)

    # Calculate period stats
    period_df = calendar_data[calendar_data["tss"] > 0]
    total_days = len(calendar_data)
    active_days = len(period_df)
    rest_days = total_days - active_days
    total_tss = calendar_data["tss"].sum()
    avg_daily_tss = total_tss / active_days if active_days > 0 else 0

    with col1:
        render_metric(
            col1,
            label="Active Days",
            value=f"{active_days}",
            help_text=f"Days with training in last {months} months",
        )

    with col2:
        render_metric(
            col2,
            label="Rest Days",
            value=f"{rest_days}",
            help_text="Days without training",
        )

    with col3:
        render_metric(
            col3,
            label="Total TSS",
            value=f"{total_tss:.0f}",
            help_text=f"Total Training Stress Score over {months} months",
        )

    with col4:
        render_metric(
            col4,
            label="Avg Daily TSS",
            value=f"{avg_daily_tss:.0f}",
            help_text="Average TSS on active days",
        )
