"""
Training Analysis - The Fluid Explorer

This unified analysis page replaces the separate Year/Month/Week pages with a
"zoomable" interface. Users select a Time Range and View Mode to explore their
training data at any granularity without switching pages.

Concept: Instead of clicking "Year Page" then "Month Page", you select a
Time Range [Last 4 Weeks | This Year | All Time | Custom] and a View Mode
[Overview | Physiology | Power Profile | Equipment].
"""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from activities_viewer.config import Settings
from activities_viewer.data import HELP_TEXTS
from activities_viewer.repository.csv_repo import CSVActivityRepository
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.services.analysis_service import AnalysisService
from activities_viewer.utils.formatting import format_watts, render_metric

st.set_page_config(page_title="Training Analysis", page_icon="📈", layout="wide")


def init_services(settings: Settings) -> ActivityService:
    """Initialize application services."""
    if settings.data_source_type == "csv":
        raw_file = (
            settings.activities_raw_file
            if hasattr(settings, "activities_raw_file")
            else settings.activities_enriched_file
        )
        moving_file = (
            settings.activities_moving_file
            if hasattr(settings, "activities_moving_file")
            else None
        )
        repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)
    else:
        raw_file = (
            settings.activities_raw_file
            if hasattr(settings, "activities_raw_file")
            else settings.activities_enriched_file
        )
        moving_file = (
            settings.activities_moving_file
            if hasattr(settings, "activities_moving_file")
            else None
        )
        repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)

    return ActivityService(repo)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def init_session_state():
    """Initialize session state for the analysis page."""
    if "analysis_date_range" not in st.session_state:
        # Default to current year
        st.session_state.analysis_date_range = "This Year"

    if "analysis_view_mode" not in st.session_state:
        # Default to Overview
        st.session_state.analysis_view_mode = "Overview"

    if "analysis_custom_start" not in st.session_state:
        st.session_state.analysis_custom_start = datetime.now() - timedelta(days=90)

    if "analysis_custom_end" not in st.session_state:
        st.session_state.analysis_custom_end = datetime.now()

    if "analysis_metric_view" not in st.session_state:
        # Default to Moving Time
        st.session_state.analysis_metric_view = "Moving Time"


def get_date_range(
    range_type: str, custom_start: datetime, custom_end: datetime
) -> tuple[datetime, datetime]:
    """
    Convert range type to actual start/end dates.

    Args:
        range_type: One of "Last 4 Weeks", "Last 12 Weeks", "This Year", "All Time", "Custom"
        custom_start: Custom start date (used if range_type is "Custom")
        custom_end: Custom end date (used if range_type is "Custom")

    Returns:
        Tuple of (start_date, end_date)
    """
    now = datetime.now()

    if range_type == "Last 4 Weeks":
        return (now - timedelta(weeks=4), now)
    elif range_type == "Last 12 Weeks":
        return (now - timedelta(weeks=12), now)
    elif range_type == "This Year":
        return (datetime(now.year, 1, 1), now)
    elif range_type == "Last Year":
        last_year = now.year - 1
        return (datetime(last_year, 1, 1), datetime(last_year, 12, 31))
    elif range_type == "All Time":
        # Use a very early date to capture all activities
        return (datetime(2000, 1, 1), now)
    elif range_type == "Custom":
        return (custom_start, custom_end)
    else:
        # Default to current year
        return (datetime(now.year, 1, 1), now)


def compute_period_deltas(
    load_stats: dict,
    start_date: datetime,
    end_date: datetime,
    activity_service: "ActivityService",
    analysis_service: "AnalysisService",
) -> dict:
    """
    Compute metric deltas by comparing current period to previous period.

    Args:
        load_stats: Current period's aggregated load metrics
        start_date: Start of the current period
        end_date: End of the current period
        activity_service: Service for fetching activities
        analysis_service: Service for aggregating metrics

    Returns:
        Dictionary with formatted delta values for: volume, tss, distance, activities
    """
    deltas = {}

    if not (start_date and end_date and activity_service and analysis_service):
        return deltas

    # Calculate period duration
    period_duration = end_date - start_date
    previous_start = start_date - period_duration
    previous_end = start_date

    # Load activities for the previous period
    prev_df = activity_service.get_activities_in_range(
        previous_start, previous_end, metric_view="Moving Time"
    )

    if prev_df.empty:
        return deltas

    # Get previous period stats
    prev_stats = analysis_service.aggregate_load(prev_df)

    # Calculate deltas
    volume_delta = load_stats["total_hours"] - prev_stats["total_hours"]
    tss_delta = load_stats["total_tss"] - prev_stats["total_tss"]
    distance_delta = load_stats["total_distance_km"] - prev_stats["total_distance_km"]
    activity_delta = load_stats["activity_count"] - prev_stats["activity_count"]

    # Format deltas as strings with + or - prefix
    deltas["volume"] = (
        f"+{volume_delta:.1f}h" if volume_delta >= 0 else f"{volume_delta:.1f}h"
    )
    deltas["tss"] = f"+{tss_delta:.0f}" if tss_delta >= 0 else f"{tss_delta:.0f}"
    deltas["distance"] = (
        f"+{distance_delta:.0f}" if distance_delta >= 0 else f"{distance_delta:.0f}"
    )
    deltas["activities"] = (
        f"+{activity_delta}" if activity_delta >= 0 else f"{activity_delta}"
    )

    return deltas


def compute_physiology_deltas(
    physio_stats: dict,
    df: pd.DataFrame,
    activity_service: "ActivityService",
    analysis_service: "AnalysisService",
) -> dict:
    """
    Compute physiology metric deltas by comparing to previous period.

    Args:
        physio_stats: Current period's aggregated physiology metrics
        df: Current period's DataFrame (to determine date range)
        activity_service: Service for fetching activities
        analysis_service: Service for aggregating metrics

    Returns:
        Dictionary with formatted delta values for: ef, decoupling
    """
    deltas = {}

    if df.empty or not activity_service or not analysis_service:
        return deltas

    # Get current period date range
    start_date = df["start_date_local"].min()
    end_date = df["start_date_local"].max()

    # Calculate period duration
    period_duration = end_date - start_date
    previous_start = start_date - period_duration
    previous_end = start_date

    # Load activities for the previous period
    prev_df = activity_service.get_activities_in_range(
        previous_start, previous_end, metric_view="Moving Time"
    )

    if prev_df.empty:
        return deltas

    # Get previous period physiology stats
    prev_stats = analysis_service.aggregate_physiology(prev_df, filter_steady_state=True)

    # Calculate EF delta
    if (
        physio_stats.get("avg_efficiency_factor", 0) > 0
        and prev_stats.get("avg_efficiency_factor", 0) > 0
    ):
        ef_delta = (
            physio_stats["avg_efficiency_factor"] - prev_stats["avg_efficiency_factor"]
        )
        deltas["ef"] = f"+{ef_delta:.2f}" if ef_delta >= 0 else f"{ef_delta:.2f}"

    # Calculate decoupling delta (lower is better, so invert the sign for display)
    if (
        physio_stats.get("avg_decoupling", 0) > 0
        and prev_stats.get("avg_decoupling", 0) > 0
    ):
        decoupling_delta = (
            physio_stats["avg_decoupling"] - prev_stats["avg_decoupling"]
        )
        # Note: For decoupling, negative is good (improved), so we keep the sign as-is
        deltas["decoupling"] = (
            f"+{decoupling_delta:.1f}%" if decoupling_delta >= 0 else f"{decoupling_delta:.1f}%"
        )

    return deltas


def compute_tid_deltas(
    tid_stats: dict,
    df: pd.DataFrame,
    activity_service: "ActivityService",
    analysis_service: "AnalysisService",
) -> dict:
    """
    Compute TID (Training Intensity Distribution) deltas.

    Args:
        tid_stats: Current period's TID stats
        df: Current period's DataFrame
        activity_service: Service for fetching activities
        analysis_service: Service for aggregating metrics

    Returns:
        Dictionary with formatted delta values for: z1, z2, z3
    """
    deltas = {}

    if df.empty or not activity_service or not analysis_service:
        return deltas

    # Get current period date range
    start_date = df["start_date_local"].min()
    end_date = df["start_date_local"].max()

    # Calculate period duration
    period_duration = end_date - start_date
    previous_start = start_date - period_duration
    previous_end = start_date

    # Load activities for the previous period
    prev_df = activity_service.get_activities_in_range(
        previous_start, previous_end, metric_view="Moving Time"
    )

    if prev_df.empty:
        return deltas

    # Get previous period TID stats
    prev_stats = analysis_service.aggregate_tid(prev_df)

    # Calculate zone deltas
    for zone in ["z1", "z2", "z3"]:
        curr_key = f"tid_{zone}_percentage"
        if curr_key in tid_stats and curr_key in prev_stats:
            delta = tid_stats[curr_key] - prev_stats[curr_key]
            deltas[zone] = f"+{delta:.1f}%" if delta >= 0 else f"{delta:.1f}%"

    return deltas


def compute_recovery_deltas(
    recovery: dict,
    df: pd.DataFrame,
    activity_service: "ActivityService",
    analysis_service: "AnalysisService",
) -> dict:
    """
    Compute recovery metric deltas.

    Args:
        recovery: Current period's recovery metrics
        df: Current period's DataFrame
        activity_service: Service for fetching activities
        analysis_service: Service for aggregating metrics

    Returns:
        Dictionary with formatted delta values for: monotony, strain, rest_days
    """
    deltas = {}

    if df.empty or not activity_service or not analysis_service:
        return deltas

    # Get current period date range
    start_date = df["start_date_local"].min()
    end_date = df["start_date_local"].max()

    # Calculate period duration
    period_duration = end_date - start_date
    previous_start = start_date - period_duration
    previous_end = start_date

    # Load activities for the previous period
    prev_df = activity_service.get_activities_in_range(
        previous_start, previous_end, metric_view="Moving Time"
    )

    if prev_df.empty:
        return deltas

    # Get previous period recovery stats
    prev_recovery = analysis_service.get_recovery_metrics(prev_df)

    # Calculate monotony delta (lower is generally better)
    if recovery.get("monotony_index", 0) > 0 and prev_recovery.get("monotony_index", 0) > 0:
        mono_delta = recovery["monotony_index"] - prev_recovery["monotony_index"]
        deltas["monotony"] = f"+{mono_delta:.2f}" if mono_delta >= 0 else f"{mono_delta:.2f}"

    # Calculate strain delta
    if recovery.get("strain_index", 0) > 0 and prev_recovery.get("strain_index", 0) > 0:
        strain_delta = recovery["strain_index"] - prev_recovery["strain_index"]
        deltas["strain"] = f"+{strain_delta:.0f}" if strain_delta >= 0 else f"{strain_delta:.0f}"

    # Calculate rest days delta
    rest_delta = recovery.get("rest_days", 0) - prev_recovery.get("rest_days", 0)
    deltas["rest_days"] = f"+{rest_delta}" if rest_delta >= 0 else f"{rest_delta}"

    return deltas


# ═══════════════════════════════════════════════════════════════════════════
# VIEW MODE RENDERERS
# ═══════════════════════════════════════════════════════════════════════════


def render_overview_view(
    df: pd.DataFrame,
    analysis_service: AnalysisService,
    start_date: datetime = None,
    end_date: datetime = None,
    activity_service: "ActivityService" = None,
):
    """
    Render the Overview view mode.

    Includes: Volume trends, TSS distribution, Intensity distribution (TID).
    Ports logic from render_trends_tab and render_distributions_tab.

    Args:
        df: Filtered activities dataframe for the selected period
        analysis_service: Service for calculating metrics
        start_date: Start of the current period (for delta calculation)
        end_date: End of the current period (for delta calculation)
        activity_service: Service for fetching activities (used for delta calculation)
    """
    st.subheader("📊 Overview")

    if df.empty:
        st.info("No activities in the selected time range.")
        return

    # Aggregate load metrics
    load_stats = analysis_service.aggregate_load(df)

    # Compute deltas by comparing to previous period
    deltas = compute_period_deltas(
        load_stats, start_date, end_date, activity_service, analysis_service
    )
    # ═══════════════════════════════════════════════════════════════════════════

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # value_size = 28
    render_metric(
        col1,
        label="Total Volume",
        value=f"{load_stats['total_hours']:.1f}h",
        help_text="Total moving time",
        delta=deltas.get('volume'),
    )

    render_metric(
        col2,
        label="Total TSS",
        value=f"{load_stats['total_tss']:.0f}",
        help_text="Total Training Stress Score",
        delta=deltas.get('tss'),
        # custom_style=True,
    )

    render_metric(
        col3,
        label="Total Distance",
        value=f"{load_stats['total_distance_km']:.0f} km",
        help_text="Total distance covered",
        delta=deltas.get('distance'),
    )

    render_metric(
        col4,
        label="Activities",
        value=f"{load_stats['activity_count']}",
        help_text="Number of activities",
        delta=deltas.get('activities'),
    )

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # TRENDS: Monthly/Weekly Volume and TSS
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("📈 Trends")

    # Determine aggregation period based on date range
    date_range_days = (df["start_date_local"].max() - df["start_date_local"].min()).days

    if date_range_days > 180:
        # More than 6 months: aggregate by month
        freq = "M"  # Month End (use "M" for older pandas compatibility)
    elif date_range_days > 60:
        # 2-6 months: aggregate by week
        freq = "W-MON"  # Week starting Monday
    else:
        # Less than 2 months: aggregate by day
        freq = "D"

    # Prepare data
    df_trends = df.copy()
    df_trends["start_date_local"] = pd.to_datetime(df_trends["start_date_local"])

    # Remove timezone if present
    if df_trends["start_date_local"].dt.tz is not None:
        df_trends["start_date_local"] = df_trends["start_date_local"].dt.tz_localize(
            None
        )

    # Group by period
    df_trends["period"] = (
        df_trends["start_date_local"].dt.to_period(freq).dt.to_timestamp()
    )

    period_stats = (
        df_trends.groupby("period")
        .agg({"moving_time": "sum", "training_stress_score": "sum", "distance": "sum"})
        .reset_index()
    )

    period_stats["hours"] = period_stats["moving_time"] / 3600
    period_stats["distance_km"] = period_stats["distance"] / 1000

    # Create dual-axis chart
    fig = make_subplots(
        rows=3,
        cols=1,
        vertical_spacing=0.12,
        row_heights=[0.35, 0.35, 0.3],
    )

    # Distance (km)
    fig.add_trace(
        go.Bar(
            x=period_stats["period"],
            y=period_stats["distance_km"],
            name="km",
            marker_color="#dc3545",
            hovertemplate="<b>%{x}</b><br>Distance: %{y:.1f} km<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Volume (hours)
    fig.add_trace(
        go.Bar(
            x=period_stats["period"],
            y=period_stats["hours"],
            name="Hours",
            marker_color="#17a2b8",
            hovertemplate="<b>%{x}</b><br>Volume: %{y:.1f}h<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # TSS
    fig.add_trace(
        go.Bar(
            x=period_stats["period"],
            y=period_stats["training_stress_score"],
            name="TSS",
            marker_color="#28a745",
            hovertemplate="<b>%{x}</b><br>TSS: %{y:.0f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=3, col=1)

    fig.update_yaxes(title_text="Km", row=1, col=1)
    fig.update_yaxes(title_text="Hours", row=2, col=1)
    fig.update_yaxes(title_text="TSS", row=3, col=1)

    fig.update_layout(height=700, showlegend=False, hovermode="x unified")

    st.plotly_chart(fig, width="stretch")

    # ═══════════════════════════════════════════════════════════════════════════
    # INTENSITY DISTRIBUTION (TID)
    # ═══════════════════════════════════════════════════════════════════════════

    st.divider()
    st.subheader("🎯 Training Intensity Distribution")

    # Get TID stats
    tid_stats = analysis_service.aggregate_tid(df)

    # Compute TID deltas vs previous period
    tid_deltas = compute_tid_deltas(tid_stats, df, activity_service, analysis_service)

    col1, col2, col3 = st.columns(3)

    render_metric(
        col1,
        label="Zone 1 (Easy)",
        value=f"{tid_stats['tid_z1_percentage']:.1f}%",
        help_text="<55% FTP - Recovery and base building",
        delta=tid_deltas.get("z1"),
    )

    render_metric(
        col2,
        label="Zone 2 (Moderate)",
        value=f"{tid_stats['tid_z2_percentage']:.1f}%",
        help_text="55-90% FTP - Tempo and threshold work",
        delta=tid_deltas.get("z2"),
    )

    render_metric(
        col3,
        label="Zone 3 (Hard)",
        value=f"{tid_stats['tid_z3_percentage']:.1f}%",
        help_text=">90% FTP - High intensity intervals",
        delta=tid_deltas.get("z3"),
    )

    # TID Pie Chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Zone 1 (Easy)", "Zone 2 (Moderate)", "Zone 3 (Hard)"],
                values=[
                    tid_stats["tid_z1_percentage"],
                    tid_stats["tid_z2_percentage"],
                    tid_stats["tid_z3_percentage"],
                ],
                marker={"colors": ["#28a745", "#ffc107", "#dc3545"]},
                hole=0.3,
                hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        height=500,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.1, "xanchor": "center", "x": 0.5},
    )

    st.plotly_chart(fig, width="stretch")

    # TID Educational Content (Phase 5.9)
    with st.expander("ℹ️ Understanding Training Intensity Distribution (TID)"):
        st.markdown("""
        **What is TID?**

        Training Intensity Distribution shows how you split your training time
        across intensity zones:
        - **Zone 1** (0-55% FTP): Easy recovery rides, base building
        - **Zone 2** (55-90% FTP): Tempo and threshold work, "sweet spot"
        - **Zone 3** (>90% FTP): VO2max intervals, sprints, races

        **Ideal Distribution** (80/20 Rule):
        - **~75-80%** in Zone 1 (low intensity)
        - **~5-10%** in Zone 2 (threshold)
        - **~15-20%** in Zone 3 (high intensity)

        This "polarized" approach maximizes aerobic development while minimizing fatigue.

        **Common Mistakes**:
        - ❌ Too much Zone 2 (threshold) - accumulates fatigue without clear benefits
        - ❌ Not enough easy miles - limits aerobic base
        - ❌ Not enough high intensity - misses specific adaptations

        **Source**: Seiler & Tønnessen (2009), *Intervals, Thresholds, and Long Slow Distance*
        """)

    # Polarization assessment
    polarization_index = tid_stats["tid_z1_percentage"] + tid_stats["tid_z3_percentage"]

    if polarization_index > 85:
        polarization_msg = (
            "🎯 **Highly Polarized** - Excellent distribution for endurance development"
        )
        msg_type = "success"
    elif polarization_index > 70:
        polarization_msg = (
            "✅ **Well Polarized** - Good balance of easy and hard training"
        )
        msg_type = "info"
    else:
        polarization_msg = (
            "⚠️ **Moderate Distribution** - Consider more polarized approach"
        )
        msg_type = "warning"

    if msg_type == "success":
        st.success(polarization_msg, icon="💪")
    elif msg_type == "info":
        st.info(polarization_msg, icon="ℹ️")
    else:
        st.warning(polarization_msg, icon="⚡")

    # ═══════════════════════════════════════════════════════════════════════════
    # PERIODIZATION CHECK (NEW - Phase 5.6)
    # ═══════════════════════════════════════════════════════════════════════════

    st.divider()
    st.subheader("📅 Periodization Check")

    # Classify training phase
    phase_info = analysis_service.classify_training_phase(df)

    # Display phase with color coding
    phase_colors = {
        "Base Building": "#2ecc71",
        "Build/Intensification": "#f39c12",
        "Peak/Race Prep": "#e74c3c",
        "Taper/Recovery": "#3498db",
        "Overload (Risky)": "#c0392b",
        "Transition/Off-Season": "#95a5a6",
        "Maintenance": "#1abc9c",
        "General Training": "#34495e",
        "Unknown": "#7f8c8d",
    }

    phase = phase_info["phase"]

    col1, _ = st.columns([2, 1])
    col2, col3 = st.columns(2)

    render_metric(
        col1,
        label="Current Phase",
        value=phase,
        help_text="\n".join(key for key, _ in phase_colors.items()),
    )
    render_metric(
        col2,
        label="Volume Trend",
        value=f"{phase_info.get('current_volume_hours', 0):.1f}hr",
        help_text="Total volume in current period",
    )
    render_metric(
        col3,
        label="Intensity (IF)",
        value=f"{phase_info.get('current_avg_if', 0):.2f}",
        help_text="Average Intensity Factor in current period",
    )

    # Phase recommendations
    if phase == "Overload (Risky)":
        st.error(
            (
                "⚠️ **Warning**: Both volume and intensity increasing simultaneously. "
                "High injury risk. Consider reducing one parameter."
            ),
            icon="🚨",
        )
    elif phase == "Base Building":
        st.success(
            "✅ **Good**: Classic base building - volume up, intensity controlled.",
            icon="💪",
        )
    elif phase == "Build/Intensification":
        st.info(
            "📈 **On Track**: Building intensity while managing volume. Monitor recovery closely.",
            icon="📊",
        )
    elif phase == "Taper/Recovery":
        st.info(
            "💤 **Recovery Phase**: Volume reduction detected. Maintain intensity for race sharpness.",
            icon="😌",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CUMULATIVE PROGRESSION (NEW - Phase 5.6)
    # ═══════════════════════════════════════════════════════════════════════════

    st.divider()
    st.subheader("📈 Cumulative Progression")

    # Sort by date and calculate cumulative values
    df_cum = df.sort_values("start_date_local").copy()
    df_cum["cumulative_distance_km"] = df_cum["distance"].cumsum() / 1000
    df_cum["cumulative_time_hours"] = df_cum["moving_time"].cumsum() / 3600
    df_cum["cumulative_elevation_m"] = df_cum["total_elevation_gain"].cumsum()

    # Summary stats
    col1, col2, col3 = st.columns(3)
    value_size = 28
    render_metric(
        col1,
        label="Total Distance",
        value=f"{df_cum['cumulative_distance_km'].iloc[-1]:.0f} km",
        help_text="Total distance covered",
        value_size=value_size,
    )
    render_metric(
        col2,
        label="Total Time",
        value=f"{df_cum['cumulative_time_hours'].iloc[-1]:.0f} hr",
        help_text="Total moving time",
        value_size=value_size,
    )
    render_metric(
        col3,
        label="Total Climbing",
        value=f"{df_cum['cumulative_elevation_m'].iloc[-1]:.0f} m",
        help_text="Total elevation gain",
        value_size=value_size,
    )

    # Create three-panel cumulative chart
    fig_cum = make_subplots(
        rows=3,
        cols=1,
        vertical_spacing=0.08,
        row_heights=[0.33, 0.33, 0.33],
    )

    # Distance
    fig_cum.add_trace(
        go.Scatter(
            x=df_cum["start_date_local"],
            y=df_cum["cumulative_distance_km"],
            mode="lines",
            name="Distance",
            line={"color": "#3498db", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(52, 152, 219, 0.2)",
            hovertemplate="<b>%{x}</b><br>%{y:.0f} km<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Time
    fig_cum.add_trace(
        go.Scatter(
            x=df_cum["start_date_local"],
            y=df_cum["cumulative_time_hours"],
            mode="lines",
            name="Time",
            line={"color": "#2ecc71", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(46, 204, 113, 0.2)",
            hovertemplate="<b>%{x}</b><br>%{y:.1f} hours<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Elevation
    fig_cum.add_trace(
        go.Scatter(
            x=df_cum["start_date_local"],
            y=df_cum["cumulative_elevation_m"],
            mode="lines",
            name="Elevation",
            line={"color": "#e74c3c", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(231, 76, 60, 0.2)",
            hovertemplate="<b>%{x}</b><br>%{y:.0f} m<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig_cum.update_yaxes(title_text="Distance (km)", row=1, col=1)
    fig_cum.update_yaxes(title_text="Time (hr)", row=2, col=1)
    fig_cum.update_yaxes(title_text="Elevation (m)", row=3, col=1)
    fig_cum.update_xaxes(title_text="", row=1, col=1)
    fig_cum.update_xaxes(title_text="", row=2, col=1)
    fig_cum.update_xaxes(title_text="Date", row=3, col=1)

    fig_cum.update_layout(height=700, showlegend=False, hovermode="x unified")

    st.plotly_chart(fig_cum, width="stretch")


def render_physiology_view(
    df: pd.DataFrame,
    analysis_service: AnalysisService,
    activity_service: "ActivityService" = None,
):
    """
    Render the Physiology view mode.

    Includes: Efficiency Factor trends, Power:HR Decoupling, HR analysis.
    Ports logic from render_efficiency_tab and render_patterns_tab.

    CRITICAL: Applies smart filtering (Z2 rides only) as per Section 6.
    """
    st.subheader("💓 Physiology")

    if df.empty:
        st.info("No activities in the selected time range.")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # AGGREGATED PHYSIOLOGY METRICS (with smart filtering)
    # ═══════════════════════════════════════════════════════════════════════════

    physio_stats = analysis_service.aggregate_physiology(df, filter_steady_state=True)

    # Compute trend deltas vs previous period
    physio_deltas = compute_physiology_deltas(
        physio_stats, df, activity_service, analysis_service
    )

    col1, col2, col3 = st.columns(3)

    value_size=32
    render_metric(
        col1,
        label="Avg Efficiency Factor",
        value=f"{physio_stats['avg_efficiency_factor']:.2f}",
        help_text="Average EF from steady-state rides (Z2 only). Higher is better.",
        value_size=value_size,
        delta=physio_deltas.get("ef"),
    )
    render_metric(
        col2,
        label="Avg Decoupling",
        value=f"{physio_stats['avg_decoupling']:.2f}%",
        help_text="Average Pw:HR decoupling from steady rides (<5% is good)",
        value_size=value_size,
        delta=physio_deltas.get("decoupling"),
    )
    render_metric(
        col3,
        label="Filtered Activities",
        value=f"{physio_stats['filtered_activity_count']}",
        help_text="Number of steady-state rides used for analysis",
        value_size=value_size,
    )

    if physio_stats["filtered_activity_count"] == 0:
        st.warning(
            "No steady-state rides found in this period. Efficiency metrics require "
            "rides with IF < 0.75 and no race designation."
        )
        return

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICIENCY FACTOR TRENDS (Smart Filtered)
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("📈 Efficiency Factor Trend")

    # Filter to Rides only (exclude Runs and other activity types)
    df_rides = df[df["type"] == "Ride"].copy()

    if df_rides.empty:
        st.info("No cycling rides available for efficiency trend analysis. Try adjusting your filters.")
    else:
        # Get efficiency trends with smart filtering (using rides-only data)
        ef_trends = analysis_service.get_efficiency_trends(df_rides, filter_steady_state=True)

        if ef_trends.empty:
            st.info("No steady-state cycling rides for efficiency trend analysis.")
        else:
            # Calculate thresholds dynamically based on DISPLAYED data (not hardcoded!)
            # This ensures percentiles match the actual time range being viewed
            import numpy as np
            ef_values = ef_trends["efficiency_factor"].values
            threshold_poor = np.percentile(ef_values, 25)      # Bottom 25%
            threshold_moderate = np.percentile(ef_values, 66)  # Middle 66%
            threshold_good = np.percentile(ef_values, 90)      # Top 10%

            # Create discrete color categories based on DATA-DRIVEN thresholds
            def categorize_ef(val):
                if val > threshold_good:
                    return "Excellent"
                elif val > threshold_moderate:
                    return "Good"
                elif val > threshold_poor:
                    return "Moderate"
                else:
                    return "Poor"

        ef_trends["ef_category"] = ef_trends["efficiency_factor"].apply(categorize_ef)

        # Define discrete colors
        ef_color_map = {
            "Excellent": "#28a745",
            "Good": "#17a2b8",
            "Moderate": "#ffc107",
            "Poor": "#dc3545"
        }

        ef_trends["color"] = ef_trends["ef_category"].map(ef_color_map)

        # Create scatter plot with discrete colors
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=ef_trends["date"],
                y=ef_trends["efficiency_factor"],
                mode="markers",
                name="Efficiency Factor",
                marker={"size": 8, "color": ef_trends["color"]},
                hovertemplate="<b>%{x}</b><br>EF: %{y:.2f}<extra></extra>",
            )
        )

        # Add threshold reference lines (using dynamic thresholds)
        fig.add_hline(
            y=threshold_good,
            line_dash="dash",
            line_color="#28a745",
            line_width=2,
            annotation_text=f"Excellent ({threshold_good:.2f})",
            annotation_position="right",
        )

        fig.add_hline(
            y=threshold_moderate,
            line_dash="dash",
            line_color="#17a2b8",
            line_width=2,
            annotation_text=f"Good ({threshold_moderate:.2f})",
            annotation_position="right",
        )

        fig.add_hline(
            y=threshold_poor,
            line_dash="dash",
            line_color="#ffc107",
            line_width=2,
            annotation_text=f"Moderate ({threshold_poor:.2f})",
            annotation_position="right",
        )

        # Add trendline if enough data points
        if len(ef_trends) >= 3:
            from scipy import stats

            # Convert dates to numeric for regression
            ef_trends["date_numeric"] = (
                ef_trends["date"] - ef_trends["date"].min()
            ).dt.days

            valid_data = ef_trends.dropna(subset=["efficiency_factor", "date_numeric"])
            if len(valid_data) >= 3:
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    valid_data["date_numeric"], valid_data["efficiency_factor"]
                )

                trendline_y = slope * valid_data["date_numeric"] + intercept

                fig.add_trace(
                    go.Scatter(
                        x=valid_data["date"],
                        y=trendline_y,
                        mode="lines",
                        name="Trend",
                        line={"color": "rgba(0, 0, 0, 0.3)", "dash": "dash", "width": 2},
                        hovertemplate="Trend: %{y:.2f}<extra></extra>",
                    )
                )

                # Show trend interpretation
                if slope > 0.001:
                    trend_msg = f"📈 **Improving**: +{slope * 30:.3f} EF/month"
                    st.success(trend_msg, icon="💪")
                elif slope < -0.001:
                    trend_msg = f"📉 **Declining**: {slope * 30:.3f} EF/month"
                    st.warning(trend_msg, icon="⚠️")
                else:
                    st.info("➡️ **Stable**: EF holding steady", icon="✅")

        fig.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Efficiency Factor",
            hovermode="closest",
        )

        st.plotly_chart(fig, width="stretch")

        # EF interpretation (using dynamic thresholds)
        avg_ef = ef_trends["efficiency_factor"].mean()
        if avg_ef > threshold_good:
            st.success(
                f"✅ **Excellent aerobic power** - Top 10% for this period (> {threshold_good:.2f})",
                icon="💪",
            )
        elif avg_ef > threshold_moderate:
            st.success(
                f"✅ **Good aerobic power** - Above average for this period ({threshold_moderate:.2f}-{threshold_good:.2f})",
                icon="👍",
            )
        elif avg_ef > threshold_poor:
            st.info(
                f"ℹ️ **Moderate aerobic power** - Typical for this period ({threshold_poor:.2f}-{threshold_moderate:.2f})",
                icon="📊",
            )
        else:
            st.warning(
                f"⚠️ **Below average** - Bottom 25% for this period (< {threshold_poor:.2f})", icon="🏃"
            )

    # Educational note about Efficiency Factor
    with st.expander("ℹ️ Understanding Efficiency Factor (EF)", expanded=False):
        st.markdown(f"""
        **Efficiency Factor** is a measure of your aerobic power output relative
            to heart rate effort.

        **Formula**: EF = Average Power (W) ÷ Average Heart Rate (bpm)

        **What it means**:
        - Higher EF = more power output for the same heart rate effort
        - Indicates improved aerobic efficiency and fitness
        - Typical range: 1.5-2.0 W/bpm for most trained cyclists

        **Your performance categories** (based on rides in the current view):
        - **Excellent (> {threshold_good:.2f} W/bpm)**: Top 10% - your best rides
            in this period
        - **Good ({threshold_moderate:.2f}-{threshold_good:.2f} W/bpm)**: 66-90th
            percentile - above average
        - **Moderate ({threshold_poor:.2f}-{threshold_moderate:.2f} W/bpm)**:
            25-66th percentile - typical performance
        - **Poor (< {threshold_poor:.2f} W/bpm)**: Bottom 25% - below your standard
            for this period

        **Why it matters**:
        - Tracks your aerobic fitness gains over time
        - Shows if your training is building aerobic capacity efficiently
        - Better fitness = more power for the same heart rate effort

        **How to improve**:
        - **Zone 2 base building**: Most effective for aerobic development
        - **Long, steady efforts**: 60-180 min rides build aerobic capacity
        - **Consistency**: Regular training matters more than intensity
        - **Recovery**: Adequate sleep and stress management support fitness gains
        - **Avoid overtraining**: Excessive hard efforts can impair aerobic development

        **Note**: EF is personal and sport-specific. These thresholds are
        **dynamically calculated** from the cycling rides displayed in your current
        time range. Compare your rides to your own performance, not external standards.

        **Data shown**: Only steady-state cycling rides (IF < 0.75, non-race) with
        power meter data
        """)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # DECOUPLING ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("💔 Power:HR Decoupling")

    if 'ef_trends' in locals() and not ef_trends.empty and "decoupling" in ef_trends.columns:
        # Create discrete color categories (mirroring cardiac drift categories)
        def categorize_decoupling(val):
            if val > -3:
                return "Excellent"
            elif val > -5:
                return "Good"
            elif val > -8:
                return "Moderate"
            else:
                return "Poor"

        ef_trends["decoupling_category"] = ef_trends["decoupling"].apply(categorize_decoupling)

        # Define discrete colors
        color_map = {
            "Excellent": "#28a745",
            "Good": "#17a2b8",
            "Moderate": "#ffc107",
            "Poor": "#dc3545"
        }

        ef_trends["color"] = ef_trends["decoupling_category"].map(color_map)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=ef_trends["date"],
                y=ef_trends["decoupling"],
                mode="markers",
                name="Decoupling",
                marker={
                    "size": 8,
                    "color": ef_trends["color"],
                },
                hovertemplate="<b>%{x}</b><br>Decoupling: %{y:.2f}%<extra></extra>",
            )
        )

        # Add threshold reference lines
        fig.add_hline(
            y=-3,
            line_dash="dash",
            line_color="#28a745",
            line_width=2,
            annotation_text="Excellent (-3%)",
            annotation_position="right",
        )

        fig.add_hline(
            y=-5,
            line_dash="dash",
            line_color="#17a2b8",
            line_width=2,
            annotation_text="Good (-5%)",
            annotation_position="right",
        )

        fig.add_hline(
            y=-8,
            line_dash="dash",
            line_color="#ffc107",
            line_width=2,
            annotation_text="Moderate (-8%)",
            annotation_position="right",
        )

        fig.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Decoupling (%)",
            hovermode="closest",
        )

        st.plotly_chart(fig, width="stretch")

        # Decoupling interpretation
        avg_decoupling = ef_trends["decoupling"].mean()
        if avg_decoupling > -3:
            st.success(
                "✅ **Excellent aerobic endurance** - Minimal efficiency drop (< 3%)",
                icon="💪",
            )
        elif avg_decoupling > -5:
            st.success(
                "✅ **Good aerobic endurance** - Low efficiency decline",
                icon="👍",
            )
        elif avg_decoupling > -8:
            st.info(
                "ℹ️ **Moderate drift** - Room for improvement in aerobic base",
                icon="📈",
            )
        else:
            st.warning(
                "⚠️ **Significant drift** - Focus on building aerobic endurance", icon="🏃"
            )

        # Educational note about Power:HR Decoupling
        with st.expander("ℹ️ Understanding Power:HR Decoupling", expanded=False):
            st.markdown("""
            **Power:HR Decoupling** measures how your Efficiency Factor (Power/HR)
            changes from the first half to the second half of a ride.

            **Formula**: Decoupling % = (2nd Half EF - 1st Half EF) / 1st Half EF × 100

            **What it means**:
            - **Negative values** = EF decreased = HR drifted upward for same
                power output (normal fatigue)
            - **Positive values** = EF increased = HR stayed lower = unusual
                (better in 2nd half)
            - More negative = more cardiac drift = less aerobic endurance

            **Interpretation** (typical values are negative):
            - **> -3%**: Excellent aerobic endurance (minimal EF drop/HR drift)
            - **-3% to -5%**: Good endurance fitness
            - **-5% to -8%**: Moderate drift (room for improvement)
            - **< -8%**: Significant fatigue/drift (work on aerobic base)

            **What causes EF to drop (HR to drift up)**:
            - Depletion of muscle glycogen (carbohydrate stores)
            - Accumulation of lactate and metabolic byproducts
            - Dehydration and rising core temperature
            - Increased sympathetic nervous system activation
            - Less aerobic base = more reliance on glycolytic metabolism

            **How to improve** (minimize negative decoupling):
            - **More Z2 volume**: Build deep aerobic base for glycogen sparing
            - **Better fueling**: Take in carbs during rides > 90 min (60-90g/hr)
            - **Hydration**: Maintain fluid balance to prevent cardiac drift
            - **Recovery**: Adequate sleep and stress management
            - **Long, steady rides**: Trains your body to maintain efficiency

            **Note**: This metric tracks EF decline, not raw HR drift. Values near
            zero or slightly positive indicate excellent endurance.

            **Data shown**: Only steady-state rides (IF < 0.75, non-race) with
            power meter data
            """)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # CARDIAC DRIFT ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("💓 Cardiac Drift")

    if 'ef_trends' in locals() and not ef_trends.empty and "cardiac_drift" in ef_trends.columns:
        # Filter out zero/NaN cardiac drift values
        drift_data = ef_trends[
            ef_trends["cardiac_drift"].notna() & (ef_trends["cardiac_drift"] > 0)
        ].copy()

        if drift_data.empty:
            st.info("No cardiac drift data available for this period.")
        else:
            # Create discrete color categories (positive values = drift occurred)
            def categorize_drift(val):
                if val < 3:
                    return "Excellent"
                elif val < 5:
                    return "Good"
                elif val < 8:
                    return "Moderate"
                else:
                    return "Poor"

            drift_data["drift_category"] = drift_data["cardiac_drift"].apply(categorize_drift)

            # Define discrete colors
            drift_color_map = {
                "Excellent": "#28a745",
                "Good": "#17a2b8",
                "Moderate": "#ffc107",
                "Poor": "#dc3545"
            }

            drift_data["color"] = drift_data["drift_category"].map(drift_color_map)

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=drift_data["date"],
                    y=drift_data["cardiac_drift"],
                    mode="markers",
                    name="Cardiac Drift",
                    marker={
                        "size": 8,
                        "color": drift_data["color"],
                    },
                    hovertemplate="<b>%{x}</b><br>Cardiac Drift: %{y:.2f}%<extra></extra>",
                )
            )

            # Add threshold reference lines
            fig.add_hline(
                y=3,
                line_dash="dash",
                line_color="#28a745",
                line_width=2,
                annotation_text="Excellent (3%)",
                annotation_position="right",
            )

            fig.add_hline(
                y=5,
                line_dash="dash",
                line_color="#17a2b8",
                line_width=2,
                annotation_text="Good (5%)",
                annotation_position="right",
            )

            fig.add_hline(
                y=8,
                line_dash="dash",
                line_color="#ffc107",
                line_width=2,
                annotation_text="Moderate (8%)",
                annotation_position="right",
            )

            fig.update_layout(
                height=400,
                xaxis_title="Date",
                yaxis_title="Cardiac Drift (%)",
                hovermode="closest",
            )

            st.plotly_chart(fig, width="stretch")

            # Drift interpretation
            avg_drift = drift_data["cardiac_drift"].mean()
            if avg_drift < 3:
                st.success(
                    "✅ **Excellent aerobic fitness** - Minimal cardiac drift (< 3%)",
                    icon="💪",
                )
            elif avg_drift < 5:
                st.success(
                    "✅ **Good aerobic fitness** - Low cardiac drift",
                    icon="👍",
                )
            elif avg_drift < 8:
                st.info(
                    "ℹ️ **Moderate drift** - Room for improvement in aerobic base",
                    icon="📈",
                )
            else:
                st.warning(
                    "⚠️ **Significant drift** - Focus on building aerobic endurance", icon="🏃"
                )

            # Educational note about Cardiac Drift
            with st.expander("ℹ️ Understanding Cardiac Drift", expanded=False):
                st.markdown("""
                **Cardiac Drift** measures how much your heart rate increases relative
                to power output during a ride.

                **Formula**: Drift % = (1st Half EF - 2nd Half EF) / 1st Half EF × 100

                **What it means**:
                - **Positive values** = EF decreased = HR drifted upward for same power output
                - **Higher values** = more cardiac drift = less aerobic fitness
                - This is the **inverse** of Power:HR Decoupling (same physiological
                    phenomenon, opposite sign)

                **Interpretation** (typical values are positive):
                - **< 3%**: Excellent aerobic fitness (minimal HR drift)
                - **3-5%**: Good aerobic fitness
                - **5-8%**: Moderate drift (room for improvement)
                - **> 8%**: Significant drift (work on aerobic base)

                **What causes cardiac drift**:
                - Depletion of muscle glycogen (carbohydrate stores)
                - Accumulation of lactate and metabolic byproducts
                - Dehydration and rising core temperature
                - Increased sympathetic nervous system activation
                - Less aerobic base = more reliance on glycolytic metabolism

                **How to improve** (minimize cardiac drift):
                - **More Z2 volume**: Build deep aerobic base for glycogen sparing
                - **Better fueling**: Take in carbs during rides > 90 min (60-90g/hr)
                - **Hydration**: Maintain fluid balance to prevent cardiac drift
                - **Recovery**: Adequate sleep and stress management
                - **Long, steady rides**: Trains your body to maintain efficiency

                **Relationship to Decoupling**:
                - Cardiac Drift = (1st - 2nd) / 1st × 100 → **positive** values
                    indicate drift
                - Power:HR Decoupling = (2nd - 1st) / 1st × 100 → **negative**
                    values indicate drift
                - They measure the same thing with opposite mathematical signs

                **Data shown**: Only steady-state rides (IF < 0.75, non-race)
                with power meter data
                """)
    else:
        st.info("No cardiac drift data available for this period.")

    # ═══════════════════════════════════════════════════════════════════════════
    # DAILY INTENSITY PATTERN (Phase 5.7 - NEW)
    # Shows daily IF timeline for periods < 30 days
    # ═══════════════════════════════════════════════════════════════════════════

    # Calculate period length
    if not df.empty and "start_date_local" in df.columns:
        df_dates = df.copy()
        df_dates["start_date_local"] = pd.to_datetime(df_dates["start_date_local"])
        if df_dates["start_date_local"].dt.tz is not None:
            df_dates["start_date_local"] = df_dates["start_date_local"].dt.tz_localize(
                None
            )

        period_days = (
            df_dates["start_date_local"].max() - df_dates["start_date_local"].min()
        ).days

        if period_days <= 30 and period_days > 0:
            st.divider()
            st.subheader("📅 Daily Intensity Pattern")

            # Aggregate daily IF (weighted by time)
            df_daily = df_dates.copy()
            df_daily["date"] = df_daily["start_date_local"].dt.date

            # Calculate weighted average IF per day
            daily_if = (
                df_daily.groupby("date")
                .apply(
                    lambda x: (x["intensity_factor"].fillna(0) * x["moving_time"]).sum()
                    / x["moving_time"].sum()
                    if x["moving_time"].sum() > 0
                    else 0
                )
                .reset_index()
            )
            daily_if.columns = ["date", "avg_if"]
            daily_if["date"] = pd.to_datetime(daily_if["date"])

            # Color code by intensity zone
            def get_if_zone_color(if_value):
                if if_value < 0.55:
                    return "#808080"  # Z1 Recovery
                elif if_value < 0.75:
                    return "#3498db"  # Z2 Endurance
                elif if_value < 0.90:
                    return "#2ecc71"  # Z3 Tempo
                elif if_value < 1.05:
                    return "#f1c40f"  # Z4 Threshold
                else:
                    return "#e74c3c"  # Z5+ High intensity

            daily_if["color"] = daily_if["avg_if"].apply(get_if_zone_color)
            daily_if["zone_name"] = daily_if["avg_if"].apply(
                lambda x: "Recovery"
                if x < 0.55
                else "Endurance"
                if x < 0.75
                else "Tempo"
                if x < 0.90
                else "Threshold"
                if x < 1.05
                else "VO2max+"
            )

            # Create bar chart
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=daily_if["date"],
                    y=daily_if["avg_if"],
                    marker_color=daily_if["color"],
                    hovertemplate="<b>%{x}</b><br>Avg IF: %{y:.2f}<br>%{customdata}<extra></extra>",
                    customdata=daily_if["zone_name"],
                )
            )

            # Add zone reference lines
            fig.add_hline(
                y=0.75,
                line_dash="dot",
                line_color="gray",
                annotation_text="Endurance/Tempo (0.75 IF)",
            )
            fig.add_hline(
                y=0.90,
                line_dash="dot",
                line_color="gray",
                annotation_text="Tempo/Threshold (0.90 IF)",
            )

            fig.update_layout(
                title="Daily Intensity Distribution",
                xaxis_title="Date",
                yaxis_title="Intensity Factor (IF)",
                height=400,
                hovermode="x",
            )

            st.plotly_chart(fig, width="stretch")

            # Intensity pattern guidance
            recovery_days = len(daily_if[daily_if["avg_if"] < 0.55])
            endurance_days = len(
                daily_if[(daily_if["avg_if"] >= 0.55) & (daily_if["avg_if"] < 0.75)]
            )
            hard_days = len(daily_if[daily_if["avg_if"] >= 0.90])

            col1, col2, col3 = st.columns(3)
            value_size = 32
            render_metric(
                col1,
                label="Recovery Days",
                value=recovery_days,
                help_text="Number of easy days with IF < 0.55",
                value_size=value_size,
            )
            render_metric(
                col2,
                label="Endurance Days",
                value=endurance_days,
                help_text="Number of moderate days with 0.55 ≤ IF < 0.75",
                value_size=value_size,
            )
            render_metric(
                col3,
                label="Hard Days",
                value=hard_days,
                help_text="Number of hard days with IF ≥ 0.90",
                value_size=value_size,
            )

            # Provide guidance
            total_days = len(daily_if)
            if total_days > 0:
                hard_ratio = hard_days / total_days
                recovery_ratio = recovery_days / total_days

                if hard_ratio > 0.4:
                    st.warning(
                        (
                            "⚠️ **High hard day frequency** - Consider more recovery"
                            "/endurance days to prevent overtraining"
                        ),
                        icon="🔴",
                    )
                elif recovery_ratio < 0.2 and total_days >= 7:
                    st.info(
                        "💡 **Low recovery volume** - Aim for 1-2 easy days per week",
                        icon="📘",
                    )
                else:
                    st.success(
                        "✅ **Balanced intensity distribution** - Good mix of hard/easy days",
                        icon="💪",
                    )

    # ═══════════════════════════════════════════════════════════════════════════
    # WEEKLY TID EVOLUTION (Phase 5.7 - NEW)
    # Shows TID evolution over time for periods > 4 weeks
    # ═══════════════════════════════════════════════════════════════════════════

    if not df.empty and "start_date_local" in df.columns:
        df_dates = df.copy()
        df_dates["start_date_local"] = pd.to_datetime(df_dates["start_date_local"])
        if df_dates["start_date_local"].dt.tz is not None:
            df_dates["start_date_local"] = df_dates["start_date_local"].dt.tz_localize(
                None
            )

        period_days = (
            df_dates["start_date_local"].max() - df_dates["start_date_local"].min()
        ).days

        if period_days > 28:  # More than 4 weeks
            st.divider()
            st.subheader("📊 Weekly TID Evolution")

            with st.spinner("Calculating weekly TID distribution..."):
                # Calculate weekly TID breakdown
                df_weekly = df_dates.copy()
                df_weekly["week"] = df_weekly["start_date_local"].dt.to_period("W")

                # Aggregate time in each zone per week
                weekly_tid_data = []
                for week, week_df in df_weekly.groupby("week"):
                    total_time = week_df["moving_time"].sum()

                    if total_time > 0:
                        # Calculate time-weighted percentage in each zone
                        z1_time = 0
                        z2_time = 0
                        z3_time = 0

                        for _, activity in week_df.iterrows():
                            act_time = activity["moving_time"]

                            # Get zone percentages (these are already time-weighted within the activity)
                            z1_pct = (
                                activity.get("power_z1_percentage", 0) / 100
                                if pd.notna(activity.get("power_z1_percentage"))
                                else 0
                            )
                            z2_pct = (
                                activity.get("power_z2_percentage", 0) / 100
                                if pd.notna(activity.get("power_z2_percentage"))
                                else 0
                            )
                            # Z3 is zones 3-7 combined
                            z3_pct = sum(
                                [
                                    activity.get(f"power_z{i}_percentage", 0) / 100
                                    if pd.notna(activity.get(f"power_z{i}_percentage"))
                                    else 0
                                    for i in range(3, 8)
                                ]
                            )

                            z1_time += act_time * z1_pct
                            z2_time += act_time * z2_pct
                            z3_time += act_time * z3_pct

                        # Convert to percentages of total weekly time
                        z1_pct_week = (
                            (z1_time / total_time * 100) if total_time > 0 else 0
                        )
                        z2_pct_week = (
                            (z2_time / total_time * 100) if total_time > 0 else 0
                        )
                        z3_pct_week = (
                            (z3_time / total_time * 100) if total_time > 0 else 0
                        )

                        # Calculate polarization index (Z1+Z3) / Z2 ratio
                        polarization = (
                            ((z1_pct_week + z3_pct_week) / z2_pct_week)
                            if z2_pct_week > 0
                            else 0
                        )

                        weekly_tid_data.append(
                            {
                                "week": week.to_timestamp(),
                                "week_str": week.strftime("%Y-W%V"),
                                "z1": z1_pct_week,
                                "z2": z2_pct_week,
                                "z3": z3_pct_week,
                                "polarization": polarization,
                                "total_hours": total_time / 3600,
                            }
                        )

                if weekly_tid_data:
                    tid_df = pd.DataFrame(weekly_tid_data)

                    # Create stacked area chart
                    fig = make_subplots(
                        rows=2,
                        cols=1,
                        row_heights=[0.7, 0.3],
                        subplot_titles=(
                            # "Weekly TID Distribution",
                            "",
                            "Polarization Index",
                        ),
                        vertical_spacing=0.15,
                    )

                    # Stacked area chart of Z1/Z2/Z3
                    fig.add_trace(
                        go.Scatter(
                            x=tid_df["week"],
                            y=tid_df["z1"],
                            name="Z1 (Low)",
                            mode="lines",
                            line={"width": 0},
                            stackgroup="one",
                            fillcolor="rgba(128, 128, 128, 0.6)",
                            hovertemplate="<b>%{x}</b><br>Z1: %{y:.1f}%<extra></extra>",
                        ),
                        row=1,
                        col=1,
                    )

                    fig.add_trace(
                        go.Scatter(
                            x=tid_df["week"],
                            y=tid_df["z2"],
                            name="Z2 (Moderate)",
                            mode="lines",
                            line={"width": 0},
                            stackgroup="one",
                            fillcolor="rgba(52, 152, 219, 0.6)",
                            hovertemplate="<b>%{x}</b><br>Z2: %{y:.1f}%<extra></extra>",
                        ),
                        row=1,
                        col=1,
                    )

                    fig.add_trace(
                        go.Scatter(
                            x=tid_df["week"],
                            y=tid_df["z3"],
                            name="Z3 (High)",
                            mode="lines",
                            line={"width": 0},
                            stackgroup="one",
                            fillcolor="rgba(231, 76, 60, 0.6)",
                            hovertemplate="<b>%{x}</b><br>Z3: %{y:.1f}%<extra></extra>",
                        ),
                        row=1,
                        col=1,
                    )

                    # Polarization index line
                    fig.add_trace(
                        go.Scatter(
                            x=tid_df["week"],
                            y=tid_df["polarization"],
                            name="Polarization",
                            mode="lines+markers",
                            line={"color": "#9b59b6", "width": 2},
                            marker={"size": 6},
                            hovertemplate="<b>%{x}</b><br>Polarization: %{y:.2f}<extra></extra>",
                            showlegend=False,
                        ),
                        row=2,
                        col=1,
                    )

                    # Add reference line for ideal polarization (around 3.0-4.0)
                    fig.add_hline(
                        y=3.0,
                        line_dash="dash",
                        line_color="green",
                        annotation_text="Ideal (3.0)",
                        row=2,
                        col=1,
                    )

                    fig.update_xaxes(title_text="Week", row=2, col=1)
                    fig.update_yaxes(title_text="% of Time", row=1, col=1)
                    fig.update_yaxes(title_text="(Z1+Z3)/Z2", row=2, col=1)

                    fig.update_layout(
                        height=600,
                        hovermode="x unified",
                        legend={
                            "orientation": "h",
                            "yanchor": "bottom",
                            "y": 1.02,
                            "xanchor": "right",
                            "x": 1,
                        },
                    )

                    st.plotly_chart(fig, width="stretch")

                    # TID trend interpretation
                    avg_polarization = tid_df["polarization"].mean()
                    polarization_trend = (
                        "increasing"
                        if tid_df["polarization"].iloc[-1]
                        > tid_df["polarization"].iloc[0]
                        else "decreasing"
                    )

                    col1 = st.columns(1)[0]
                    render_metric(
                        col1,
                        label="Avg Polarization Index",
                        value=f"{avg_polarization:.2f}",
                        help_text="(Z1+Z3)/Z2 ratio. Higher = more polarized (good)",
                        value_size=32,

                    )
                    if avg_polarization >= 3.0:
                        st.success(
                            "✅ **Highly polarized training**",
                            icon="💪",
                        )
                    elif avg_polarization >= 2.0:
                        st.info(
                            "ℹ️ **Moderately polarized**",
                            icon="📈",
                        )
                    else:
                        st.warning(
                            (
                                "⚠️ **Low polarization** - Consider 80/20 approach: "
                                "more Z1/Z2, less threshold"
                            ),
                            icon="📘",
                        )
                    # with col2:
                    #     if avg_polarization >= 3.0:
                    #         st.success(
                    #             f"✅ **Highly polarized training**",
                    #             icon="💪",
                    #         )
                    #     elif avg_polarization >= 2.0:
                    #         st.info(
                    #             f"ℹ️ **Moderately polarized**",
                    #             icon="📈",
                    #         )
                    #     else:
                    #         st.warning(
                    #             (
                    #                 f"⚠️ **Low polarization** - Consider 80/20 approach: "
                    #                 "more Z1/Z2, less threshold"
                    #             ),
                    #             icon="📘",
                    #         )
                    st.info(f"Trend: {polarization_trend}")

                    # Educational note
                    with st.expander("ℹ️ Understanding Polarized Training"):
                        st.markdown("""
                        **Polarized Training** means spending most time at LOW
                        or HIGH intensity, avoiding the "middle zone":

                        - **~75-80%** in Z1-Z2 (Low/Moderate intensity)
                        - **~5-10%** in Z2 (Threshold/Tempo)
                        - **~15-20%** in Z3+ (High intensity intervals)

                        **Polarization Index**: Ratio of (Z1+Z3) time to Z2 time
                        - **>3.0**: Highly polarized (ideal for most athletes)
                        - **2.0-3.0**: Moderately polarized
                        - **<2.0**: Too much threshold work (common mistake)

                        **Why it works**: Low intensity builds aerobic base without
                        excessive fatigue. High intensity provides specific adaptations.
                        Middle zones accumulate fatigue without clear benefits.
                        """)


def render_power_profile_view(df: pd.DataFrame, analysis_service: AnalysisService):
    """
    Render the Power Profile view mode.

    Includes: Power curve (MMP), Peak power tracking, PRs.
    Ports logic from render_power_curve_section and render_extremes_section.
    """
    st.subheader("⚡ Power Profile")

    if df.empty:
        st.info("No activities in the selected time range.")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER CURVE (Mean Maximum Power)
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("📈 Power Curve (Peak Powers)")

    power_curve = analysis_service.get_power_curve_max(df)

    # Define durations for display (matching detail page)
    power_curve_durations = [
        "5sec",
        "10sec",
        "30sec",
        "1min",
        "2min",
        "5min",
        "10min",
        "20min",
        "30min",
        "1hr",
    ]
    power_curve_labels = [
        "5s",
        "10s",
        "30s",
        "1m",
        "2m",
        "5m",
        "10m",
        "20m",
        "30m",
        "1h",
    ]

    # Extract values for selected period
    power_curve_values = []
    for duration in power_curve_durations:
        col_name = f"power_curve_{duration}"
        val = power_curve.get(col_name, 0)
        power_curve_values.append(float(val) if val else 0)

    # Get yearly best power curve for comparison (always use current calendar year)
    service: ActivityService = st.session_state.activity_service
    metric_view = st.session_state.analysis_metric_view

    # Background: always use current calendar year
    current_year = datetime.now().year
    yearly_start = datetime(current_year, 1, 1)
    yearly_end = datetime(current_year, 12, 31, 23, 59, 59)
    yearly_df = service.get_activities_in_range(
        yearly_start, yearly_end, metric_view=metric_view
    )

    # Calculate yearly best power curve
    yearly_best_service = AnalysisService()
    yearly_best_curve = yearly_best_service.get_power_curve_max(yearly_df)

    yearly_best_power_curve = []
    for duration in power_curve_durations:
        col_name = f"power_curve_{duration}"
        val = yearly_best_curve.get(col_name, 0)
        yearly_best_power_curve.append(float(val) if val else 0)

    # Create two-column layout: chart on left, table on right
    col_chart, col_table = st.columns([2, 1])

    with col_chart:
        if any(power_curve_values):
            fig = go.Figure()

            # Add yearly best as background (lighter color)
            if any(yearly_best_power_curve):
                fig.add_trace(
                    go.Bar(
                        x=power_curve_labels,
                        y=yearly_best_power_curve,
                        marker_color="rgba(189, 195, 199, 0.3)",
                        name=f"{current_year} Best",
                        text=[
                            f"{v:.0f}W" if v > 0 else ""
                            for v in yearly_best_power_curve
                        ],
                        textposition="outside",
                    )
                )

            # Add selected period (foreground) - very transparent so background shows through
            fig.add_trace(
                go.Bar(
                    x=power_curve_labels,
                    y=power_curve_values,
                    marker_color="rgba(241, 196, 15, 0.35)",
                    name="Selected Period",
                    text=[f"{v:.0f}W" if v > 0 else "" for v in power_curve_values],
                    textposition="outside",
                )
            )

            fig.update_layout(
                yaxis_title="Power (W)",
                xaxis_title="Duration",
                margin={"t": 30, "b": 40},
                height=400,
                barmode="overlay",
                legend={"orientation": "h", "y": 1.15, "x": 0},
                hovermode="x unified",
            )

            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No power curve data available for this period.")

    with col_table:
        # Build table showing best effort activities for each duration
        st.markdown("**Best Efforts**")

        best_efforts = []
        for i, duration in enumerate(power_curve_durations):
            col_name = f"power_curve_{duration}"
            if col_name in df.columns and df[col_name].notna().any():
                valid_data = df[df[col_name].notna() & (df[col_name] > 0)]
                if not valid_data.empty:
                    max_idx = valid_data[col_name].idxmax()
                    max_power = valid_data.loc[max_idx, col_name]
                    activity_date = valid_data.loc[max_idx, "start_date_local"]
                    activity_id = (
                        valid_data.loc[max_idx, "id"]
                        if "id" in valid_data.columns
                        else None
                    )
                    best_efforts.append(
                        {
                            "Duration": power_curve_labels[i],
                            "Power (W)": int(max_power),
                            "Date": activity_date.strftime("%Y-%m-%d")
                            if pd.notna(activity_date)
                            else "",
                            "ID": activity_id,
                        }
                    )

        if best_efforts:
            # Display as a scrollable table with clickable dates
            df_efforts = pd.DataFrame(best_efforts)

            # Create a column with activity URLs for LinkColumn pointing to detail page
            df_efforts["Activity URL"] = df_efforts.apply(
                lambda row: f"/detail?activity_id={row['ID']}" if row["ID"] is not None else "",
                axis=1
            )

            st.markdown("**Best Efforts**")
            st.dataframe(
                df_efforts[["Duration", "Power (W)", "Date", "Activity URL"]],
                column_config={
                    "Duration": st.column_config.Column("Duration"),
                    "Power (W)": st.column_config.NumberColumn("Power (W)", format="%d W"),
                    "Date": st.column_config.Column("Date"),
                    "Activity URL": st.column_config.LinkColumn("Activity", display_text="link"),
                },
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No data")

    # ═══════════════════════════════════════════════════════════════════════════
    # KEY POWER BENCHMARKS
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("🏆 Key Power Benchmarks")

    col1, col2, col3, col4 = st.columns(4)

    render_metric(
        col1,
        label="5s (Sprint)",
        value=format_watts(power_curve.get("power_curve_5sec", 0)),
        help_text="Anaerobic power",
    )

    render_metric(
        col2,
        label="5min (VO2max)",
        value=format_watts(power_curve.get("power_curve_5min", 0)),
        help_text="VO2 max power",
    )

    render_metric(
        col3,
        label="FTP (20min×0.95)",
        value=format_watts(
            power_curve.get("power_curve_20min", 0) * 0.95
            if power_curve.get("power_curve_20min", 0) > 0
            else 0
        ),
        help_text="Estimated FTP from 20min power",
    )

    render_metric(
        col4,
        label="1hr (Endurance)",
        value=format_watts(power_curve.get("power_curve_1hr", 0)),
        help_text="Sustainable power",
    )

    # Power Curve Educational Content (Phase 5.9)
    with st.expander("ℹ️ Understanding Your Power Curve"):
        st.markdown("""
        **What is a Power Curve?**

        Your power curve (also called Mean Maximum Power or MMP) shows the highest
        average power you can sustain for different durations. It's like a "personal
        best" chart for power output.

        **Key Durations & What They Mean**:

        - **1-5 seconds**: **Neuromuscular Power** - Pure sprint capability, largely genetic
        - **5-10 seconds**: **Anaerobic Capacity** - Sprint finishing power
        - **1-2 minutes**: **Anaerobic Threshold** - Track sprint / finishing kick power
        - **5 minutes**: **VO2max Power** - Maximal aerobic power, hard intervals
        - **20 minutes**: **Functional Threshold Power** - FTP estimate (multiply by 0.95)
        - **1 hour**: **Sustained Threshold** - True FTP / time trial power
        - **6+ hours**: **Endurance Power** - Gran fondo / ultra-distance capability

        **How to Improve Each Zone**:

        - **Sprint (1-10s)**: Sprint intervals, track work, power starts
        - **VO2max (3-8min)**: 4-6 minute intervals at 105-120% FTP
        - **FTP (20-60min)**: Sweet spot (88-93% FTP), threshold intervals
        - **Endurance (1+ hrs)**: Long Z2 rides, base training

        **What's "Good"?**

        Power-to-weight ratios (W/kg) for FTP:
        - **5.0+ W/kg**: World Tour professional
        - **4.0-5.0 W/kg**: Elite amateur / domestic pro
        - **3.0-4.0 W/kg**: Competitive racer
        - **2.5-3.0 W/kg**: Strong recreational cyclist
        - **<2.5 W/kg**: Developing fitness

        **Source**: Coggan Power Profile, Allen & Coggan (2010)
        """)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # BEST PERFORMANCES (Phase 5.8 - NEW)
    # Shows top activities by various metrics
    # ═══════════════════════════════════════════════════════════════════════════

    st.subheader("🏆 Best Performances")

    if len(df) > 0:
        # Find best activities for each metric
        best_performances = []

        # Longest Distance
        if "distance" in df.columns and df["distance"].notna().any():
            idx_dist = df["distance"].idxmax()
            best_performances.append(
                {
                    "Metric": "🛣️ Longest Distance",
                    "Value": f"{df.loc[idx_dist, 'distance'] / 1000:.1f} km",
                    "Activity": df.loc[idx_dist, "name"][:40]
                    if "name" in df.columns
                    else "Unknown",
                    "Date": df.loc[idx_dist, "start_date_local"].strftime("%Y-%m-%d")
                    if "start_date_local" in df.columns
                    else "",
                    "ID": df.loc[idx_dist, "id"] if "id" in df.columns else None,
                }
            )

        # Most Elevation
        if (
            "total_elevation_gain" in df.columns
            and df["total_elevation_gain"].notna().any()
        ):
            idx_elev = df["total_elevation_gain"].idxmax()
            best_performances.append(
                {
                    "Metric": "⛰️ Most Climbing",
                    "Value": f"{df.loc[idx_elev, 'total_elevation_gain']:,.0f} m",
                    "Activity": df.loc[idx_elev, "name"][:40]
                    if "name" in df.columns
                    else "Unknown",
                    "Date": df.loc[idx_elev, "start_date_local"].strftime("%Y-%m-%d")
                    if "start_date_local" in df.columns
                    else "",
                    "ID": df.loc[idx_elev, "id"] if "id" in df.columns else None,
                }
            )

        # Highest TSS
        if (
            "training_stress_score" in df.columns
            and df["training_stress_score"].notna().any()
        ):
            idx_tss = df["training_stress_score"].idxmax()
            best_performances.append(
                {
                    "Metric": "💪 Highest TSS",
                    "Value": f"{df.loc[idx_tss, 'training_stress_score']:.0f}",
                    "Activity": df.loc[idx_tss, "name"][:40]
                    if "name" in df.columns
                    else "Unknown",
                    "Date": df.loc[idx_tss, "start_date_local"].strftime("%Y-%m-%d")
                    if "start_date_local" in df.columns
                    else "",
                    "ID": df.loc[idx_tss, "id"] if "id" in df.columns else None,
                }
            )

        # Highest Normalized Power
        if "normalized_power" in df.columns and df["normalized_power"].notna().any():
            idx_np = df["normalized_power"].idxmax()
            best_performances.append(
                {
                    "Metric": "⚡ Highest NP",
                    "Value": f"{df.loc[idx_np, 'normalized_power']:.0f} W",
                    "Activity": df.loc[idx_np, "name"][:40]
                    if "name" in df.columns
                    else "Unknown",
                    "Date": df.loc[idx_np, "start_date_local"].strftime("%Y-%m-%d")
                    if "start_date_local" in df.columns
                    else "",
                    "ID": df.loc[idx_np, "id"] if "id" in df.columns else None,
                }
            )

        # Best Efficiency Factor
        if "efficiency_factor" in df.columns and df["efficiency_factor"].notna().any():
            # Filter for valid EF values (exclude races and high IF)
            df_ef_valid = df[
                (df["efficiency_factor"].notna())
                & (df["efficiency_factor"] > 0)
                & (df.get("intensity_factor", 1.0) < 0.85)  # Exclude hard efforts
            ]
            if len(df_ef_valid) > 0:
                idx_ef = df_ef_valid["efficiency_factor"].idxmax()
                best_performances.append(
                    {
                        "Metric": "🎯 Best Efficiency",
                        "Value": f"{df.loc[idx_ef, 'efficiency_factor']:.2f}",
                        "Activity": df.loc[idx_ef, "name"][:40]
                        if "name" in df.columns
                        else "Unknown",
                        "Date": df.loc[idx_ef, "start_date_local"].strftime("%Y-%m-%d")
                        if "start_date_local" in df.columns
                        else "",
                        "ID": df.loc[idx_ef, "id"] if "id" in df.columns else None,
                    }
                )

        # Display as formatted table
        if best_performances:
            perf_df = pd.DataFrame(best_performances)

            # Display each as a card
            cols = st.columns(min(3, len(best_performances)))
            for i, (_, row) in enumerate(perf_df.iterrows()):
                with cols[i % 3]:
                    st.markdown(f"**{row['Metric']}**")
                    st.metric("", row["Value"])
                    st.caption(f"{row['Activity']}")
                    st.caption(f"📅 {row['Date']}")

                    # Add link to activity detail if ID is available
                    if row["ID"] is not None:
                        if st.button("View Details", key=f"perf_{i}"):
                            st.session_state.selected_activity_id = row["ID"]
                            st.switch_page("pages/3_detail.py")

            # Also show as table for easier comparison
            with st.expander("📊 Full Performance Table"):
                st.dataframe(
                    perf_df[["Metric", "Value", "Activity", "Date"]],
                    hide_index=True,
                    width="stretch",
                )
    else:
        st.info("No activities available for performance tracking.")


def render_recovery_view(
    df: pd.DataFrame,
    analysis_service: AnalysisService,
    activity_service: "ActivityService" = None,
):
    """
    Render the Recovery view mode (NEW - Phase 5.5).

    Includes: Recovery metrics (Monotony, Strain, Rest Days), Load trends, Recommendations.
    Ports logic from weekly_analysis_components.render_recovery_readiness_section().
    """
    st.subheader("💤 Recovery & Readiness")

    if df.empty:
        st.info("No activities in the selected time range.")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1: RECOVERY METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("### 📊 Recovery Metrics")

    # Calculate recovery metrics
    recovery = analysis_service.get_recovery_metrics(df)

    # Compute recovery deltas vs previous period
    recovery_deltas = compute_recovery_deltas(
        recovery, df, activity_service, analysis_service
    )

    col1, col2, col3 = st.columns(3)

    value_size = 24
    with col1:
        render_metric(
            col1,
            label="Rest Days",
            value=recovery["rest_days"],
            delta=recovery_deltas.get("rest_days"),
            help_text="Days with TSS < 20",
            value_size=value_size,
        )
        if recovery["rest_days"] >= 2:
            st.success("✅ Adequate recovery")
        elif recovery["rest_days"] == 1:
            st.warning("⚠️ Consider more rest")
        else:
            st.error("🔴 Insufficient recovery")

    with col2:
        monotony = recovery["monotony_index"]
        render_metric(
            col2,
            label="Monotony Index",
            value=f"{monotony:.2f}",
            help_text=HELP_TEXTS.get(
                "monotony_index", "Daily TSS variability. Lower = more varied training"
            ),
            value_size=value_size,
            delta=recovery_deltas.get("monotony"),
        )
        if monotony < 1.5:
            st.success("✅ Low risk")
        elif monotony < 2.0:
            st.warning("⚠️ Moderate risk")
        else:
            st.error("🔴 High risk - too repetitive")

    with col3:
        strain = recovery["strain_index"]
        render_metric(
            col3,
            label="Strain Index",
            value=f"{strain:.0f}",
            help_text=HELP_TEXTS.get(
                "strain_index", "Weekly TSS × Monotony. Combines load and variation"
            ),
            value_size=value_size,
            delta=recovery_deltas.get("strain"),
        )
        if strain < 3000:
            st.success("✅ Manageable")
        elif strain < 6000:
            st.warning("⚠️ Moderate strain")
        else:
            st.error("🔴 High strain")

    # Interpretation guide
    with st.expander("ℹ️ Understanding Recovery Metrics"):
        st.markdown("""
        **Monotony Index:**
        - <1.5: ✅ Safe - Good training variety
        - 1.5-2.0: ⚠️ Monitor - Moderate risk of overtraining
        - \\>2.0: 🔴 High risk - Training too repetitive

        **Strain Index:**
        - <3000: ✅ Appropriate load
        - 3000-6000: ⚠️ Moderate - Monitor recovery
        - \\>6000: 🔴 High - Prioritize recovery

        **Rest Days:**
        - 2+: ✅ Adequate recovery for most athletes
        - 1: ⚠️ May need more rest depending on intensity
        - 0: 🔴 Critical - Recovery day needed immediately

        **Source**: Foster (1998), Monitoring training in athletes with reference
        to overtraining syndrome
        """)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2: LOAD TRENDS (Daily TSS)
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("### 📈 Daily Training Load")

    if len(recovery["daily_tss_values"]) > 0:
        # Create bar chart of daily TSS
        df_daily = df.copy()
        df_daily["start_date_local"] = pd.to_datetime(df_daily["start_date_local"])
        if df_daily["start_date_local"].dt.tz is not None:
            df_daily["start_date_local"] = df_daily["start_date_local"].dt.tz_localize(
                None
            )

        df_daily["date_only"] = df_daily["start_date_local"].dt.date
        daily_tss_df = (
            df_daily.groupby("date_only")["training_stress_score"].sum().reset_index()
        )
        daily_tss_df.columns = ["Date", "TSS"]

        # Color bars by intensity
        colors = []
        for tss in daily_tss_df["TSS"]:
            if tss < 20:
                colors.append("#95a5a6")  # Gray - rest
            elif tss < 150:
                colors.append("#2ecc71")  # Green - moderate
            elif tss < 300:
                colors.append("#f39c12")  # Orange - hard
            else:
                colors.append("#e74c3c")  # Red - very hard

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=daily_tss_df["Date"],
                y=daily_tss_df["TSS"],
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>TSS: %{y:.0f}<extra></extra>",
            )
        )

        # Add reference lines
        fig.add_hline(
            y=150,
            line_dash="dash",
            line_color="orange",
            annotation_text="Hard day threshold (150 TSS)",
            annotation_position="right",
        )

        fig.update_layout(
            title="Daily Training Stress Score",
            xaxis_title="Date",
            yaxis_title="TSS",
            height=350,
            hovermode="x",
        )

        st.plotly_chart(fig, width="stretch")

        # Daily stats
        col1, col2, col3 = st.columns(3)
        value_size = 32
        render_metric(
            col1,
            label="Avg Daily TSS",
            value=f"{recovery['avg_daily_tss']:.0f}",
            value_size=value_size,
        )
        render_metric(
            col2,
            label="Max Daily TSS",
            value=f"{recovery['max_daily_tss']:.0f}",
            value_size=value_size,
        )
        render_metric(
            col3,
            label="Total TSS",
            value=f"{recovery['weekly_tss']:.0f}",
            value_size=value_size,
        )

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3: PMC (Performance Management Chart)
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("### 📊 Performance Management Chart")

    with st.spinner("Calculating PMC data..."):
        pmc_data = analysis_service.get_pmc_data(df)

    if not pmc_data.empty and len(pmc_data) > 1:
        fig = go.Figure()

        # CTL (Fitness)
        fig.add_trace(
            go.Scatter(
                x=pmc_data["date"],
                y=pmc_data["ctl"],
                mode="lines",
                name="CTL (Fitness)",
                line={"color": "#3498db", "width": 2},
                hovertemplate="<b>%{x}</b><br>CTL: %{y:.1f}<extra></extra>",
            )
        )

        # ATL (Fatigue)
        fig.add_trace(
            go.Scatter(
                x=pmc_data["date"],
                y=pmc_data["atl"],
                mode="lines",
                name="ATL (Fatigue)",
                line={"color": "#e74c3c", "width": 2},
                hovertemplate="<b>%{x}</b><br>ATL: %{y:.1f}<extra></extra>",
            )
        )

        # TSB (Form)
        fig.add_trace(
            go.Scatter(
                x=pmc_data["date"],
                y=pmc_data["tsb"],
                mode="lines",
                name="TSB (Form)",
                line={"color": "#2ecc71", "width": 2},
                fill="tozeroy",
                hovertemplate="<b>%{x}</b><br>TSB: %{y:.1f}<extra></extra>",
            )
        )

        # Add TSB zones
        fig.add_hrect(
            y0=-30,
            y1=-10,
            fillcolor="rgba(46, 204, 113, 0.1)",
            line_width=0,
            annotation_text="Race Ready Zone",
            annotation_position="top left",
        )

        fig.add_hrect(
            y0=-30,
            y1=-50,
            fillcolor="rgba(231, 76, 60, 0.1)",
            line_width=0,
            annotation_text="Overreached",
            annotation_position="bottom left",
        )

        fig.update_layout(
            title="Fitness (CTL), Fatigue (ATL), and Form (TSB)",
            xaxis_title="Date",
            yaxis_title="Training Load",
            height=400,
            hovermode="x unified",
            legend={
                "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1
            },
        )

        st.plotly_chart(fig, width="stretch")

        # Current PMC values
        latest = pmc_data.iloc[-1]
        col1, col2, col3 = st.columns(3)

        value_size = 32
        render_metric(
            col1,
            label="Current CTL",
            value=f"{latest['ctl']:.0f}",
            help_text="Chronic Training Load (42-day avg)",
            value_size=value_size,
        )
        render_metric(
            col2,
            label="Current ATL",
            value=f"{latest['atl']:.0f}",
            help_text="Acute Training Load (7-day avg)",
            value_size=value_size,
        )
        render_metric(
            col3,
            label="Current TSB",
            value=f"{latest['tsb']:.0f}",
            help_text="Training Stress Balance (CTL - ATL)",
            value_size=value_size,
        )

        tsb = latest["tsb"]
        if -30 <= tsb <= -10:
            st.success("✅ Race Ready Zone", icon="🏁")
        elif tsb < -30:
            st.error("⚠️ Overreached - Recovery needed", icon="🛑")
        elif tsb > 5:
            st.info("📈 Fresh - Good for hard training", icon="💪")

        # PMC Educational Content (Phase 5.9)
        with st.expander("ℹ️ Understanding the Performance Management Chart"):
            st.markdown("""
            **What is PMC?**

            The Performance Management Chart tracks your training load and recovery
            state using three metrics:

            **CTL (Chronic Training Load) - "Fitness"**
            - 42-day exponentially weighted average of daily TSS
            - Formula: Today's CTL = Yesterday's CTL + (Today's TSS - Yesterday's CTL) / 42
            - Represents your long-term fitness level
            - Higher CTL = better aerobic fitness (but slower to build)

            **ATL (Acute Training Load) - "Fatigue"**
            - 7-day exponentially weighted average of daily TSS
            - Formula: Today's ATL = Yesterday's ATL + (Today's TSS - Yesterday's ATL) / 7
            - Represents recent training stress
            - Spikes quickly with hard training

            **TSB (Training Stress Balance) - "Form"**
            - Formula: TSB = CTL - ATL
            - Represents your current recovery state:
              * **TSB > 5**: Fresh/Rested - Good for hard training
              * **TSB -10 to +5**: Neutral - Normal training
              * **TSB -30 to -10**: Race Ready - Optimal performance zone
              * **TSB < -30**: Overreached - Recovery needed immediately

            **How to Use It**:
            - Build CTL gradually during base/build phases (3-5 TSS/day increase)
            - Taper for races: Reduce volume 2-3 weeks out to let TSB rise into race-ready zone
            - Monitor ATL spikes: Sudden increases = injury/burnout risk
            - Never let TSB drop below -30 for extended periods

            **Source**: Coggan (2003), *Training and Racing with a Power Meter*
            """)
    else:
        st.info("Not enough data for PMC calculation (requires multiple days)")

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4: RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("### 💡 Recovery Recommendations")

    # Generate personalized recommendations
    recommendations = []

    if recovery["monotony_index"] > 2.0:
        recommendations.append(
            "🎯 **Add Training Variety**: High monotony detected. Mix up your "
            "workout types and intensities."
        )

    if recovery["strain_index"] > 6000:
        recommendations.append(
            "⚠️ **Reduce Load**: Very high strain index. Consider taking an easy "
            "week or rest days."
        )

    if recovery["rest_days"] < 2:
        recommendations.append(
            "💤 **Schedule Rest**: You need at least 2 rest/easy days per week "
            "for optimal recovery."
        )

    if pmc_data is not None and not pmc_data.empty:
        latest_tsb = pmc_data.iloc[-1]["tsb"]
        if latest_tsb < -30:
            recommendations.append(
                "🛑 **Recovery Week Needed**: TSB < -30 indicates overreaching. "
                "Take 3-5 easy days."
            )
        elif latest_tsb > 10:
            recommendations.append(
                "💪 **Good Time for Hard Training**: TSB > 10 indicates you're "
                "fresh and recovered."
            )

    if recovery["max_daily_tss"] > 400:
        recommendations.append(
            "📊 **Monitor Big Days**: Very high TSS days (>400) require 48+ hours "
            "recovery."
        )

    if not recommendations:
        recommendations.append(
            "✅ **Balanced Training**: Your recovery metrics look good. Keep up the "
            "current approach!"
        )

    for rec in recommendations:
        st.info(rec)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ═══════════════════════════════════════════════════════════════════════════


def main():
    """Main page orchestrator for the fluid Analysis page."""
    st.title("📈 Training Analysis - The Fluid Explorer")

    # Welcome info banner
    with st.expander("ℹ️ How to use this page", expanded=False):
        st.markdown("""
        This **unified analysis page** replaces the old separate Year/Month/Week pages with a flexible "zoomable" interface.

        **How it works:**
        1. **Select a Time Range** (Last 4 Weeks, This Year, Custom, etc.)
        2. **Choose a View Mode**:
           - **Overview**: Volume trends, TID, Training types, Periodization
           - **Physiology**: Efficiency Factor, Decoupling, Daily intensity patterns
           - **Power Profile**: Power curve, Peak power benchmarks, Best performances
           - **Recovery**: Monotony/Strain metrics, PMC (CTL/ATL/TSB), Training recommendations

        **New in v2.0:**
        - 🆕 Recovery view with Monotony Index, Strain Index, and PMC tracking
        - 📊 Weekly TID Evolution (for periods >4 weeks) with polarization analysis
        - 📅 Daily Intensity Pattern (for periods ≤30 days) with zone distribution
        - 🏆 Best Performances table in Power Profile view
        - 🎯 Training Type Distribution and Periodization Check in Overview
        - 📚 Educational expanders throughout with scientific references

        **Tip**: Use custom date ranges to analyze specific training blocks or compare periods!
        """)

    # Initialize settings and service if not already done
    if "settings" not in st.session_state:
        config_json = os.environ.get("ACTIVITIES_VIEWER_CONFIG")
        if config_json:
            try:
                config_data = json.loads(config_json)
                st.session_state.settings = Settings(**config_data)
            except Exception as e:
                st.error(f"Failed to load configuration: {e}")
                return
        else:
            st.error(
                "Service not initialized. Please run the app from the main entry point."
            )
            return

    if "activity_service" not in st.session_state:
        try:
            st.session_state.activity_service = init_services(st.session_state.settings)
        except Exception as e:
            st.error(f"Failed to initialize services: {e}")
            return

    service: ActivityService = st.session_state.activity_service

    # Initialize session state
    init_session_state()

    # ═══════════════════════════════════════════════════════════════════════════
    # SIDEBAR: METRIC VIEW SELECTOR
    # ═══════════════════════════════════════════════════════════════════════════

    with st.sidebar:
        st.subheader("View Options")

        metric_view = st.radio(
            "Metric View:",
            ("Moving Time", "Raw Time"),
            key="analysis_metric_view_selector",
            help="Moving Time: Metrics calculated only during movement\nRaw Time: Metrics calculated for total activity duration",
        )

        st.session_state.analysis_metric_view = metric_view

        st.divider()

        st.subheader("Filters")

        # Get all activities to extract available sport types
        all_activities = service.get_all_activities(metric_view)
        if not all_activities.empty:
            available_sports = sorted(all_activities["sport_type"].unique().tolist())
            selected_sports = st.multiselect(
                "Sport Types",
                available_sports,
                default=available_sports
                if "analysis_sport_filter" not in st.session_state
                else st.session_state.analysis_sport_filter,
                help="Filter by sport type",
            )
            st.session_state.analysis_sport_filter = selected_sports
        else:
            selected_sports = []

    # ═══════════════════════════════════════════════════════════════════════════
    # TOP-LEVEL CONTROLS
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("**Select a time range and view mode to explore your training data:**")

    col1, col2 = st.columns([2, 3])

    with col1:
        # Time Range Selector - bind directly to session state
        # Calculate current index
        current_range = st.session_state.analysis_date_range
        range_options = [
            "Last 4 Weeks",
            "Last 12 Weeks",
            "This Year",
            "Last Year",
            "All Time",
            "Custom",
        ]
        current_index = (
            range_options.index(current_range) if current_range in range_options else 2
        )

        time_range = st.selectbox(
            "📅 Time Range",
            range_options,
            index=current_index,
            key="time_range_selector_widget",
        )

        st.session_state.analysis_date_range = time_range

    # Custom date range if selected
    if time_range == "Custom":
        col_start, col_end = st.columns(2)
        with col_start:
            custom_start = st.date_input(
                "Start Date",
                value=st.session_state.analysis_custom_start.date(),
                key="custom_start_date",
            )
            st.session_state.analysis_custom_start = datetime.combine(
                custom_start, datetime.min.time()
            )

        with col_end:
            custom_end = st.date_input(
                "End Date",
                value=st.session_state.analysis_custom_end.date(),
                key="custom_end_date",
            )
            st.session_state.analysis_custom_end = datetime.combine(
                custom_end, datetime.max.time()
            )

    with col2:
        # View Mode Tabs
        view_mode = st.radio(
            "🔍 View Mode",
            ["Overview", "Physiology", "Power Profile", "Recovery"],
            horizontal=True,
            index=["Overview", "Physiology", "Power Profile", "Recovery"].index(
                st.session_state.analysis_view_mode
            )
            if st.session_state.analysis_view_mode
            in ["Overview", "Physiology", "Power Profile", "Recovery"]
            else 0,
            key="view_mode_selector",
        )

        st.session_state.analysis_view_mode = view_mode

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA LOADING
    # ═══════════════════════════════════════════════════════════════════════════

    # Get date range
    start_date, end_date = get_date_range(
        time_range,
        st.session_state.analysis_custom_start,
        st.session_state.analysis_custom_end,
    )

    # Load activities for the selected range
    with st.spinner("Loading activities..."):
        df = service.get_activities_in_range(
            start_date, end_date, metric_view=metric_view
        )

    # Apply sport type filter if available
    if (
        not df.empty
        and "analysis_sport_filter" in st.session_state
        and st.session_state.analysis_sport_filter
    ):
        df = df[df["sport_type"].isin(st.session_state.analysis_sport_filter)].copy()

    if df.empty:
        st.warning(
            f"No activities found between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')} matching the selected filters."
        )
        return

    # Display date range info
    st.info(
        f"📊 Analyzing **{len(df)} activities** from **{start_date.strftime('%b %d, %Y')}** to **{end_date.strftime('%b %d, %Y')}**",
        icon="📅",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDER SELECTED VIEW MODE
    # ═══════════════════════════════════════════════════════════════════════════

    # Instantiate AnalysisService
    analysis_service = AnalysisService()

    if view_mode == "Overview":
        render_overview_view(df, analysis_service, start_date, end_date, service)
    elif view_mode == "Physiology":
        render_physiology_view(df, analysis_service, service)
    elif view_mode == "Power Profile":
        render_power_profile_view(df, analysis_service)
    elif view_mode == "Recovery":
        render_recovery_view(df, analysis_service, service)


if __name__ == "__main__":
    main()
