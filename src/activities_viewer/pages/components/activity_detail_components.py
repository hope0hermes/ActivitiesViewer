"""
Activity Detail Page Components.

Extracted rendering functions for the activity detail page tabs.
Each function handles a specific UI section to keep main() clean.
"""

import ast

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from activities_viewer.domain.models import Activity
from activities_viewer.services.activity_service import ActivityService

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & COLORS
# ═══════════════════════════════════════════════════════════════════════════════

ROLLING_WINDOW_SECONDS = [None, 5, 30, 60, 300]

# Color scheme for metrics
METRIC_COLORS = {
    "speed": "#3498db",
    "power": "#f1c40f",
    "hr": "#e74c3c",
    "cadence": "#2ecc71",
    "grade": "#9b59b6",
    "elevation": "#95a5a6",
}

# Power zone colors (Z1-Z7)
POWER_ZONE_COLORS = [
    "#808080",  # Z1 - Grey
    "#3498db",  # Z2 - Blue
    "#2ecc71",  # Z3 - Green
    "#f1c40f",  # Z4 - Yellow
    "#e67e22",  # Z5 - Orange
    "#e74c3c",  # Z6 - Red
    "#8e44ad",  # Z7 - Violet
]

# HR zone colors (Z1-Z5)
HR_ZONE_COLORS = [
    "#808080",  # Z1 - Grey
    "#3498db",  # Z2 - Blue
    "#2ecc71",  # Z3 - Green
    "#e67e22",  # Z4 - Orange
    "#e74c3c",  # Z5 - Red
]

# Zone definitions for hover text
# These are typical trainer road power zones (as % of FTP)
POWER_ZONE_RANGES = {
    1: "0-55% FTP",
    2: "55-75% FTP",
    3: "75-90% FTP",
    4: "90-105% FTP",
    5: "105-120% FTP",
    6: "120-150% FTP",
    7: ">150% FTP",
}

# Power zone thresholds as % of FTP
POWER_ZONE_THRESHOLDS = [0, 55, 75, 90, 105, 120, 150, float('inf')]

# HR zone ranges (typical % of LTHR - lactate threshold HR)
HR_ZONE_RANGES = {
    1: "<85% LTHR",
    2: "85-94% LTHR",
    3: "94-104% LTHR",
    4: "104-120% LTHR",
    5: ">120% LTHR",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_help_text(metric_key: str, help_texts: dict) -> str:
    """
    Get help text for a metric by its key.

    Args:
        metric_key: The metric key (e.g., "avg_power", "fatigue_index")
        help_texts: Dictionary mapping metric keys to help text

    Returns:
        Help text string, or empty string if not found
    """
    return help_texts.get(metric_key, "")


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


def render_metric(column, label: str, value: str, help_text: str = None) -> None:
    """
    Render a metric with responsive sizing that doesn't get truncated.
    Uses custom HTML instead of st.metric() for better control.

    Args:
        column: Streamlit column to render in
        label: Metric label (e.g., "Average Power")
        value: Metric value to display (e.g., "245 W")
        help_text: Optional help/documentation text shown on hover
    """
    with column:
        # Create a responsive metric card with proper text sizing and help text support
        if help_text:
            # Convert newlines to HTML entity and escape quotes for HTML attribute
            help_escaped = help_text.replace('\n', '&#10;').replace('"', '&quot;')
            # HTML with tooltip on hover
            metric_html = f"""
            <div style="
                position: relative;
                padding: 12px 6px;
                background-color: rgba(240, 242, 246, 0.7);
                border-radius: 6px;
                text-align: center;
                min-height: 70px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                cursor: help;
                border: 1px solid rgba(200, 200, 200, 0.3);
            " title="{help_escaped}">
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 3px;
                    width: 100%;
                    min-height: 16px;
                    flex-wrap: wrap;
                ">
                    <div style="
                        font-size: 11px;
                        color: #888;
                        font-weight: 500;
                        text-align: center;
                    ">{label}</div>
                    <div style="
                        font-size: 10px;
                        color: #0066cc;
                        font-weight: bold;
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        border: 1px solid #0066cc;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-shrink: 0;
                        line-height: 1;
                    ">ℹ</div>
                </div>
                <div style="
                    font-size: 16px;
                    font-weight: bold;
                    color: #262730;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    line-height: 1.4;
                    width: 100%;
                    text-align: center;
                    margin-top: 4px;
                ">{value}</div>
            </div>
            """
        else:
            # HTML without tooltip
            metric_html = f"""
            <div style="
                padding: 12px 6px;
                background-color: rgba(240, 242, 246, 0.7);
                border-radius: 6px;
                text-align: center;
                min-height: 70px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            ">
                <div style="
                    font-size: 11px;
                    color: #888;
                    margin-bottom: 6px;
                    font-weight: 500;
                    text-align: center;
                ">{label}</div>
                <div style="
                    font-size: 16px;
                    font-weight: bold;
                    color: #262730;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    line-height: 1.4;
                    width: 100%;
                    text-align: center;
                ">{value}</div>
            </div>
            """
        st.markdown(metric_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY SELECTOR
# ═══════════════════════════════════════════════════════════════════════════════


def render_activity_selector(
    service: ActivityService,
    metric_view: str,
) -> tuple[Activity | None, str]:
    """
    Render activity selection UI with calendar and dropdown.

    Args:
        service: ActivityService instance
        metric_view: Either "Moving Time" or "Raw Time"

    Returns:
        Tuple of (selected_activity, activity_id)
    """
    df_activities = service.get_all_activities(metric_view)
    if df_activities.empty:
        st.warning("No activities found.")
        return None, ""

    # Ensure datetime (already sorted by date desc from repository)
    df_activities["start_date_local"] = pd.to_datetime(
        df_activities["start_date_local"], utc=True
    )

    # Get date range for calendar
    min_date = df_activities["start_date_local"].min().date()
    max_date = df_activities["start_date_local"].max().date()

    # Check if activity was pre-selected via navigation buttons
    if "selected_activity_id" in st.session_state:
        pre_selected_id = st.session_state.selected_activity_id
        # Find the pre-selected activity
        if pre_selected_id in df_activities["id"].values:
            activity_id = pre_selected_id
            activity = service.get_activity(activity_id, metric_view)
            return activity, activity_id

    # Calendar date picker
    col_cal, col_select = st.columns([1, 2])

    with col_cal:
        selected_date = st.date_input(
            "📅 Select date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            help="Pick a date to filter activities",
        )

    # Filter activities for selected date
    df_on_date = df_activities[
        df_activities["start_date_local"].dt.date == selected_date
    ]

    with col_select:
        if df_on_date.empty:
            st.info(f"No activities on {selected_date}. Showing all activities.")
            # Fall back to all activities
            activity_options = df_activities["name"].values
            df_for_selection = df_activities
        else:
            activity_options = df_on_date["name"].values
            df_for_selection = df_on_date

        selected_activity_name = st.selectbox(
            "Select an activity",
            activity_options,
            index=0,
            help="Choose which activity to analyze",
        )

    # Get selected activity with metric_view
    selected_row = df_for_selection[
        df_for_selection["name"] == selected_activity_name
    ].iloc[0]
    activity_id = selected_row["id"]
    activity = service.get_activity(activity_id, metric_view)

    return activity, activity_id


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════


def render_activity_navigation(
    service: ActivityService,
    current_activity_id: str,
    metric_view: str,
) -> None:
    """
    Render activity navigation buttons (prev/next) and display activity info.

    Args:
        service: ActivityService instance
        current_activity_id: ID of currently displayed activity
        metric_view: Either "Moving Time" or "Raw Time"
    """
    df_activities = service.get_all_activities(metric_view)
    if df_activities.empty:
        return

    # Sort by date descending (newest first)
    df_activities = df_activities.sort_values("start_date_local", ascending=False)
    activity_ids = df_activities["id"].tolist()

    # Find current activity index
    try:
        current_idx = activity_ids.index(current_activity_id)
    except ValueError:
        return

    has_prev = current_idx < len(activity_ids) - 1  # Older activity
    has_next = current_idx > 0  # Newer activity

    # Navigation with prev/next buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

    with nav_col1:
        if st.button(
            "◀ Prev",
            disabled=not has_prev,
            use_container_width=True,
            help="Go to previous activity (older)",
        ):
            prev_activity_id = activity_ids[current_idx + 1]
            st.session_state["selected_activity_id"] = prev_activity_id
            st.rerun()

    with nav_col2:
        current_activity = df_activities[df_activities["id"] == current_activity_id].iloc[0]
        activity_date = pd.to_datetime(current_activity["start_date_local"]).strftime("%B %d, %Y")
        activity_name = current_activity["name"]
        st.subheader(f"{activity_name} • {activity_date}", anchor=False)

    with nav_col3:
        if st.button(
            "Next ▶",
            disabled=not has_next,
            use_container_width=True,
            help="Go to next activity (newer)",
        ):
            next_activity_id = activity_ids[current_idx - 1]
            st.session_state["selected_activity_id"] = next_activity_id
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════

# Workout type mapping
WORKOUT_TYPES = {
    0: ("Ride", "🚴"),
    1: ("Race", "🏁"),
    2: ("Long Ride", "🛣️"),
    3: ("Commute", "🏙️"),
    4: ("Indoor", "🏠"),
    5: ("Trainer", "🎯"),
    10: ("Recovery", "💤"),
    11: ("Intervals", "⚡"),
    12: ("Workout", "💪"),
}


def get_workout_type_info(workout_type: float | None) -> tuple[str, str]:
    """Get workout type name and emoji."""
    if workout_type is None or pd.isna(workout_type):
        return "Ride", "🚴"
    return WORKOUT_TYPES.get(int(workout_type), ("Ride", "🚴"))


# ═══════════════════════════════════════════════════════════════════════════════
# NEW ANALYSIS SECTIONS (December 2025)
# ═══════════════════════════════════════════════════════════════════════════════


def render_pacing_analysis(activity: Activity, help_texts: dict = None) -> None:
    """Render pacing analysis section with negative split, match burns, and time in red.

    Args:
        activity: Activity object to display
        help_texts: Dictionary of help text strings
    """
    if help_texts is None:
        help_texts = {}

    st.markdown("#### 📊 Pacing Analysis")

    col1, col2, col3 = st.columns(3)

    # Negative Split Index
    nsi = get_metric(activity, "negative_split_index")
    if nsi:
        if nsi > 1.05:
            nsi_label = "Negative Split ✅"
            nsi_emoji = "🟢"
        elif nsi >= 0.95:
            nsi_label = "Even Pacing ✅"
            nsi_emoji = "🟢"
        elif nsi >= 0.85:
            nsi_label = "Slight Fade ⚠️"
            nsi_emoji = "🟡"
        else:
            nsi_label = "Significant Fade 🔴"
            nsi_emoji = "🔴"

        render_metric(
            col1,
            "Negative Split Index",
            f"{nsi_emoji} {nsi:.2f}",
            get_help_text("negative_split_index", help_texts)
        )
        with col1:
            st.caption(nsi_label)
    else:
        render_metric(col1, "Negative Split Index", "-", get_help_text("negative_split_index", help_texts))

    # Match Burns
    match_burns = get_metric(activity, "match_burn_count")
    if match_burns is not None:
        if match_burns <= 2:
            burn_label = "Steady ride"
            burn_emoji = "🟢"
        elif match_burns <= 5:
            burn_label = "Interval workout"
            burn_emoji = "🟡"
        elif match_burns <= 10:
            burn_label = "Dynamic ride"
            burn_emoji = "🟠"
        else:
            burn_label = "Racing effort"
            burn_emoji = "🔴"

        render_metric(
            col2,
            "Match Burns",
            f"{burn_emoji} {int(match_burns)}",
            get_help_text("match_burn_count", help_texts)
        )
        with col2:
            st.caption(burn_label)
    else:
        render_metric(col2, "Match Burns", "-", get_help_text("match_burn_count", help_texts))

    # Time Above 90% FTP
    time_above = get_metric(activity, "time_above_90_ftp")
    if time_above is not None and time_above > 0:
        minutes = int(time_above // 60)
        seconds = int(time_above % 60)
        time_str = f"{minutes}:{seconds:02d}" if minutes > 0 else f"{seconds}s"

        # Get percentage of ride
        moving_time = get_metric(activity, "moving_time", 1)
        pct = (time_above / moving_time * 100) if moving_time else 0

        if time_above < 300:  # <5 min
            time_emoji = "🟢"
            time_label = "Light stimulus"
        elif time_above < 900:  # <15 min
            time_emoji = "🟡"
            time_label = "Good stimulus"
        elif time_above < 1800:  # <30 min
            time_emoji = "🟠"
            time_label = "Hard session"
        else:
            time_emoji = "🔴"
            time_label = "Very hard session"

        render_metric(
            col3,
            "Time in Red (>90% FTP)",
            f"{time_emoji} {time_str}",
            get_help_text("time_above_90_ftp", help_texts)
        )
        with col3:
            st.caption(f"{time_label} ({pct:.1f}% of ride)")
    else:
        render_metric(col3, "Time in Red (>90% FTP)", "-", get_help_text("time_above_90_ftp", help_texts))


def render_climbing_analysis(activity: Activity, help_texts: dict = None) -> None:
    """Render climbing analysis section with VAM, climbing W/kg, and climbing time.

    Args:
        activity: Activity object to display
        help_texts: Dictionary of help text strings
    """
    if help_texts is None:
        help_texts = {}

    st.markdown("#### ⛰️ Climbing Analysis")

    col1, col2, col3 = st.columns(3)

    # VAM
    vam = get_metric(activity, "vam")
    if vam:
        # Categorize VAM
        if vam < 800:
            vam_label = "Recreational pace"
            vam_emoji = "🟢"
        elif vam < 1000:
            vam_label = "Strong amateur"
            vam_emoji = "🟡"
        elif vam < 1200:
            vam_label = "Cat 2-3 racer"
            vam_emoji = "🟠"
        elif vam < 1400:
            vam_label = "Cat 1 / Pro domestic"
            vam_emoji = "🔴"
        else:
            vam_label = "World Tour level"
            vam_emoji = "🏆"

        render_metric(
            col1,
            "VAM",
            f"{vam_emoji} {vam:.0f} m/h",
            get_help_text("vam", help_texts)
        )
        with col1:
            st.caption(vam_label)
    else:
        render_metric(col1, "VAM", "-", get_help_text("vam", help_texts))

    # Climbing W/kg
    climbing_wkg = get_metric(activity, "climbing_power_per_kg")
    if climbing_wkg:
        # Categorize W/kg
        if climbing_wkg < 3.0:
            wkg_label = "Recreational"
            wkg_emoji = "🟢"
        elif climbing_wkg < 3.5:
            wkg_label = "Strong amateur"
            wkg_emoji = "🟡"
        elif climbing_wkg < 4.0:
            wkg_label = "Cat 2-3 racer"
            wkg_emoji = "🟠"
        elif climbing_wkg < 4.5:
            wkg_label = "Cat 1 / Pro domestic"
            wkg_emoji = "🔴"
        else:
            wkg_label = "World Tour level"
            wkg_emoji = "🏆"

        render_metric(
            col2,
            "Climbing W/kg",
            f"{wkg_emoji} {climbing_wkg:.1f}",
            get_help_text("climbing_power_per_kg", help_texts)
        )
        with col2:
            st.caption(wkg_label)
    else:
        render_metric(col2, "Climbing W/kg", "-", get_help_text("climbing_power_per_kg", help_texts))

    # Climbing Time
    climbing_time = get_metric(activity, "climbing_time")
    if climbing_time is not None and climbing_time > 0:
        hours = int(climbing_time // 3600)
        minutes = int((climbing_time % 3600) // 60)
        seconds = int(climbing_time % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}:{seconds:02d}"
        else:
            time_str = f"{seconds}s"

        # Get percentage of ride
        moving_time = get_metric(activity, "moving_time", 1)
        pct = (climbing_time / moving_time * 100) if moving_time else 0

        render_metric(
            col3,
            "Climbing Time",
            time_str,
            get_help_text("climbing_time", help_texts)
        )
        with col3:
            st.caption(f"{pct:.0f}% of ride")
    else:
        render_metric(col3, "Climbing Time", "-", get_help_text("climbing_time", help_texts))


def render_overview_tab(activity: Activity, service: ActivityService, metric_view: str = "Moving Time", help_texts: dict = None) -> None:
    """Render the Overview tab with summary metrics, map, and time-series plots.

    Args:
        activity: Activity object to display
        service: ActivityService for data fetching
        metric_view: "Moving" or "Total" (for prefix selection)
        help_texts: Dictionary of help text strings
    """
    if help_texts is None:
        help_texts = {}

    # ─────────────────────────────────────────────────────────────────────────
    # ACTIVITY SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Activity Summary")

    # Get workout type info
    workout_type, workout_emoji = get_workout_type_info(
        getattr(activity, "workout_type", None)
    )

    # Row 1: Basic metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    # Distance
    distance_km = get_metric(activity, "distance")
    if distance_km:
        distance_km = distance_km / 1000
    render_metric(col1, "🛣️ Distance", f"{distance_km:.1f} km" if distance_km else "-")

    # Duration - use moving_time or elapsed_time based on selection
    time_field = "moving_time" if metric_view == "Moving Time" else "elapsed_time"
    time_label = "⏱️ Moving Time" if metric_view == "Moving Time" else "⏱️ Total Time"
    duration = get_metric(activity, time_field)
    if duration:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    else:
        duration_str = "-"
    render_metric(col2, time_label, duration_str)

    # Elevation
    elevation = get_metric(activity, "total_elevation_gain")
    render_metric(col3, "⛰️ Elevation", f"{elevation:.0f} m" if elevation else "-")

    # Average Speed - try average_speed, then compute from distance/time
    avg_speed = get_metric(activity, "average_speed")
    if avg_speed is None or pd.isna(avg_speed):
        # Try computing from distance and time
        pass
    if avg_speed is None or pd.isna(avg_speed):
        # Compute from distance and time if available (use moving_time or elapsed_time based on selection)
        distance = get_metric(activity, "distance")
        time_value = get_metric(activity, time_field)  # Use the same time_field from above
        if distance and time_value and time_value > 0:
            avg_speed = distance / time_value  # In m/s
        else:
            avg_speed = None

    if avg_speed and avg_speed > 0:
        avg_speed_kmh = avg_speed * 3.6
    else:
        avg_speed_kmh = None
    render_metric(col4, "🚀 Avg Speed", f"{avg_speed_kmh:.1f} km/h" if avg_speed_kmh else "-")

    # Workout Type
    render_metric(col5, f"{workout_emoji} Type", workout_type)

    # Row 2: Power & HR metrics (if available)
    col1, col2, col3, col4, col5 = st.columns(5)

    # Average Power
    avg_power = get_metric(activity, "average_power")
    render_metric(col1, "⚡ Avg Power", f"{avg_power:.0f} W" if avg_power else "-", get_help_text("avg_power", help_texts))

    # Normalized Power
    np_val = get_metric(activity, "normalized_power")
    render_metric(col2, "📊 Norm Power", f"{np_val:.0f} W" if np_val else "-", get_help_text("normalized_power", help_texts))

    # TSS
    tss = get_metric(activity, "training_stress_score")
    render_metric(col3, "📈 TSS", f"{tss:.0f}" if tss else "-", get_help_text("tss", help_texts))

    # Average HR
    avg_hr = get_metric(activity, "average_hr")
    render_metric(col4, "❤️ Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-", get_help_text("average_hr", help_texts))

    # Max HR
    max_hr = get_metric(activity, "max_hr")
    render_metric(col5, "💓 Max HR", f"{max_hr:.0f} bpm" if max_hr else "-", get_help_text("max_hr", help_texts))

    # Row 3: Additional metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    # Intensity Factor
    if_val = get_metric(activity, "intensity_factor")
    render_metric(col1, "🎯 IF", f"{if_val:.2f}" if if_val else "-", get_help_text("intensity_factor", help_texts))

    # Efficiency Factor
    ef = get_metric(activity, "efficiency_factor")
    render_metric(col2, "⚙️ EF", f"{ef:.2f}" if ef else "-", get_help_text("efficiency_factor", help_texts))

    # Average Cadence
    avg_cadence = get_metric(activity, "average_cadence")
    if avg_cadence is None or pd.isna(avg_cadence):
        # Fall back if not available
        avg_cadence = get_metric(activity, "average_cadence")
    render_metric(col3, "🔄 Cadence", f"{avg_cadence:.0f} rpm" if avg_cadence and avg_cadence > 0 else "-", get_help_text("average_cadence", help_texts))

    # Calories
    calories = get_metric(activity, "kilojoules")
    render_metric(col4, "🔥 Energy", f"{calories:.0f} kJ" if calories else "-", get_help_text("kilojoules", help_texts))

    # Start time
    start_time = getattr(activity, "start_date_local", None)
    if start_time:
        if hasattr(start_time, "strftime"):
            time_str = start_time.strftime("%H:%M")
        else:
            time_str = str(start_time)[:16]
    else:
        time_str = "-"
    render_metric(col5, "🕐 Start", time_str)

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # NEW ANALYSIS SECTIONS
    # ─────────────────────────────────────────────────────────────────────────

    # Pacing Analysis - always show if we have power data
    avg_power = get_metric(activity, "average_power")
    if avg_power:
        render_pacing_analysis(activity, help_texts)
        st.divider()

    # Climbing Analysis - always present
    render_climbing_analysis(activity, help_texts)
    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # ROUTE MAP
    # ─────────────────────────────────────────────────────────────────────────
    stream = service.get_activity_stream(activity.id)

    if not stream.empty:
        # Parse latlng if string
        if "latlng" in stream.columns:
            if isinstance(stream["latlng"].iloc[0], str):
                stream["latlng"] = stream["latlng"].apply(
                    lambda x: ast.literal_eval(x)
                    if pd.notna(x) and x != "[]"
                    else None
                )
            map_data = stream.dropna(subset=["latlng"])
        else:
            map_data = pd.DataFrame()

        st.subheader("Route Map")
        if not map_data.empty:
            start_loc = map_data["latlng"].iloc[0]
            m = folium.Map(location=start_loc, zoom_start=12)
            points = map_data["latlng"].tolist()
            folium.PolyLine(points, color="#e74c3c", weight=4, opacity=0.8).add_to(m)
            m.fit_bounds(m.get_bounds())
            st_folium(m, width=None, height=400)
        else:
            st.info("No GPS data available.")

        # Create synchronized plots with shared x-axis
        st.subheader("Activity Metrics")

        # Smoothing control
        smoothing = st.pills(
            label="Apply rolling average smoothing to time-series plots",
            options=ROLLING_WINDOW_SECONDS,
        )

        # Prepare all data - initialize with distance or time
        if "distance" in stream.columns:
            plot_data = stream[["distance"]].copy()
            # Convert to km for better readability
            plot_data["distance_km"] = plot_data["distance"] / 1000
        elif "time" in stream.columns:
            plot_data = stream[["time"]].copy()
        else:
            plot_data = pd.DataFrame(index=stream.index)

        # Speed
        if "velocity_smooth" in stream.columns:
            plot_data["speed_kmh"] = apply_smoothing(
                stream["velocity_smooth"] * 3.6, smoothing
            )
            has_speed = True
        else:
            has_speed = False

        # Power
        if "watts" in stream.columns:
            plot_data["watts"] = apply_smoothing(stream["watts"], smoothing)
            has_power = True
        else:
            has_power = False

        # Heart Rate
        if "heartrate" in stream.columns:
            plot_data["heartrate"] = apply_smoothing(stream["heartrate"], smoothing)
            has_hr = True
        else:
            has_hr = False

        # Cadence
        if "cadence" in stream.columns:
            plot_data["cadence"] = apply_smoothing(stream["cadence"], smoothing)
            has_cadence = True
        else:
            has_cadence = False

        # Grade
        if "grade_smooth" in stream.columns:
            plot_data["grade"] = apply_smoothing(stream["grade_smooth"], smoothing)
            has_grade = True
        else:
            has_grade = False

        # Elevation
        if "altitude" in stream.columns:
            plot_data["altitude"] = apply_smoothing(stream["altitude"], smoothing)
            has_elevation = True
        else:
            has_elevation = False

        # Count active metrics (including elevation)
        num_metrics = sum(
            [has_speed, has_power, has_hr, has_cadence, has_grade, has_elevation]
        )

        if num_metrics > 0:
            # Create subplots - one per metric with shared x-axis
            fig_sync = make_subplots(
                rows=num_metrics,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=[],
            )

            # Build custom hover text with all metrics
            hover_texts = []
            for idx in range(len(plot_data)):
                hover_parts = []
                if "distance_km" in plot_data.columns:
                    hover_parts.append(
                        f"<b>Distance: {plot_data['distance_km'].iloc[idx]:.2f} km</b>"
                    )
                elif "time" in plot_data.columns:
                    time_sec = plot_data['time'].iloc[idx]
                    mins, secs = divmod(int(time_sec), 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0:
                        hover_parts.append(f"<b>Time: {hours}:{mins:02d}:{secs:02d}</b>")
                    else:
                        hover_parts.append(f"<b>Time: {mins}:{secs:02d}</b>")
                else:
                    hover_parts.append(f"<b>Point {idx}</b>")
                if has_speed:
                    hover_parts.append(
                        f"Speed: {plot_data['speed_kmh'].iloc[idx]:.1f} km/h"
                    )
                if has_power:
                    hover_parts.append(
                        f"Power: {plot_data['watts'].iloc[idx]:.0f} W"
                    )
                if has_hr:
                    hover_parts.append(
                        f"HR: {plot_data['heartrate'].iloc[idx]:.0f} bpm"
                    )
                if has_cadence:
                    hover_parts.append(
                        f"Cadence: {plot_data['cadence'].iloc[idx]:.0f} rpm"
                    )
                if has_grade:
                    hover_parts.append(
                        f"Grade: {plot_data['grade'].iloc[idx]:.1f}%"
                    )
                if has_elevation:
                    hover_parts.append(
                        f"Elevation: {plot_data['altitude'].iloc[idx]:.0f}m"
                    )
                hover_texts.append("<br>".join(hover_parts))

            # Determine x-axis data and label
            if "distance_km" in plot_data.columns:
                x_data = plot_data["distance_km"]
                x_label = "Distance (km)"
            elif "time" in plot_data.columns:
                x_data = plot_data["time"] / 60  # Convert to minutes
                x_label = "Time (min)"
            else:
                x_data = plot_data.index
                x_label = "Data Point"

            # Track row number
            row = 1

            if has_speed:
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["speed_kmh"],
                        name="Speed (km/h)",
                        line={"color": METRIC_COLORS["speed"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(title_text="Speed (km/h)", row=row, col=1)
                row += 1

            if has_power:
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["watts"],
                        name="Power (W)",
                        line={"color": METRIC_COLORS["power"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(title_text="Power (W)", row=row, col=1)
                row += 1

            if has_hr:
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["heartrate"],
                        name="Heart Rate (bpm)",
                        line={"color": METRIC_COLORS["hr"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(title_text="HR (bpm)", row=row, col=1)
                row += 1

            if has_cadence:
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["cadence"],
                        name="Cadence (rpm)",
                        line={"color": METRIC_COLORS["cadence"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(title_text="Cadence (rpm)", row=row, col=1)
                row += 1

            if has_grade:
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["grade"],
                        name="Grade (%)",
                        line={"color": METRIC_COLORS["grade"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(title_text="Grade (%)", row=row, col=1)
                row += 1

            if has_elevation:
                min_elev = plot_data["altitude"].min()
                fig_sync.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=plot_data["altitude"],
                        name="Elevation (m)",
                        line={"color": METRIC_COLORS["elevation"], "width": 2},
                        customdata=hover_texts,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    row=row,
                    col=1,
                )
                fig_sync.update_yaxes(
                    title_text="Elevation (m)",
                    row=row,
                    col=1,
                    range=[min_elev - 50, plot_data["altitude"].max() + 50],
                )

            fig_sync.update_xaxes(title_text=x_label, row=num_metrics, col=1)
            fig_sync.update_layout(
                height=100 * num_metrics,
                hovermode="x unified",
                margin={"l": 60, "r": 20, "t": 20, "b": 40},
                showlegend=False,
            )
            st.plotly_chart(fig_sync, use_container_width=True)
        else:
            st.info("No time-series data available.")
    else:
        st.info("No activity stream data available.")


# ═══════════════════════════════════════════════════════════════════════════════
# POWER & HEART RATE TAB
# ═══════════════════════════════════════════════════════════════════════════════


def render_power_hr_tab(
    activity: Activity,
    service: ActivityService,
    metric_view: str,
    help_texts: dict,
) -> None:
    """Render the Power & Heart Rate analysis tab."""
    st.subheader(f"Power & Heart Rate Analysis ({metric_view})")

    # ===== SECTION 1: POWER CURVE (spans both columns) =====
    render_power_curve(activity, service, help_texts)

    st.divider()

    # ===== SECTION 2: Summary Stats (two columns, aligned) =====
    col_power, col_hr = st.columns(2)

    with col_power:
        st.markdown("#### ⚡ Power Metrics")
        c1, c2, c3 = st.columns(3)
        avg_pwr = get_metric(activity, "average_power")
        np_val = get_metric(activity, "normalized_power")
        max_pwr = get_metric(activity, "max_power")
        render_metric(c1, "Avg Power", f"{avg_pwr:.0f} W" if avg_pwr else "-", get_help_text("avg_power", help_texts))
        render_metric(c2, "Norm Power", f"{np_val:.0f} W" if np_val else "-", get_help_text("normalized_power", help_texts))
        render_metric(c3, "Max Power", f"{max_pwr:.0f} W" if max_pwr else "-", help_text="Peak power during activity")

        c1, c2, c3 = st.columns(3)
        w_kg = get_metric(activity, "power_per_kg")
        if_val = get_metric(activity, "intensity_factor")
        tss_val = get_metric(activity, "training_stress_score")
        render_metric(c1, "W/kg", f"{w_kg:.2f}" if w_kg else "-", help_text="Average power normalized to body weight")
        render_metric(c2, "IF", f"{if_val:.2f}" if if_val else "-", get_help_text("intensity_factor", help_texts))
        render_metric(c3, "TSS", f"{tss_val:.0f}" if tss_val else "-", get_help_text("tss", help_texts))

    with col_hr:
        st.markdown("#### ❤️ Heart Rate Metrics")
        c1, c2, c3 = st.columns(3)
        avg_hr = get_metric(activity, "average_hr")
        max_hr = get_metric(activity, "max_hr")
        hr_tss = get_metric(activity, "hr_training_stress")
        render_metric(c1, "Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-", get_help_text("average_hr", help_texts))
        render_metric(c2, "Max HR", f"{max_hr:.0f} bpm" if max_hr else "-", get_help_text("max_hr", help_texts))
        render_metric(c3, "HR TSS", f"{hr_tss:.0f}" if hr_tss else "-", get_help_text("hr_training_stress", help_texts))

        c1, c2, c3 = st.columns(3)
        ef = get_metric(activity, "efficiency_factor")
        decoupling = get_metric(activity, "power_hr_decoupling")
        hr_type = get_metric(activity, "hr_tid_classification")
        render_metric(c1, "EF", f"{ef:.2f}" if ef else "-", get_help_text("efficiency_factor", help_texts))
        render_metric(c2, "Decoupling", f"{decoupling:.1f}%" if decoupling else "-", get_help_text("decoupling", help_texts))
        render_metric(c3, "Type", hr_type if hr_type else "-", get_help_text("tid_classification", help_texts))

    st.divider()

    # ===== SECTION 1.3: ENHANCED POWER-HR METRICS =====
    st.markdown("### 💪 Anaerobic & Recovery Metrics")

    col_wprime, col_recovery = st.columns(2)

    # W' Balance Plot
    with col_wprime:
        st.markdown("#### ⚡ W' Balance")
        w_prime = get_metric(activity, "w_prime")
        w_prime_min = get_metric(activity, "w_prime_balance_min")

        if w_prime and w_prime_min is not None:
            # Display W' metrics
            c1, c2 = st.columns(2)
            render_metric(c1, "Total W'", f"{(w_prime/1000):.1f} kJ" if w_prime else "-", help_text="Anaerobic work capacity above critical power")
            render_metric(c2, "Min W'", f"{(w_prime_min/1000):.1f} kJ" if w_prime_min else "-", help_text="Lowest W' balance reached during ride")

            # W' depletion percentage
            if w_prime > 0:
                depletion_pct = (w_prime - w_prime_min) / w_prime * 100
                if depletion_pct < 30:
                    depl_color = "🟢"
                    depl_label = "Low depletion"
                elif depletion_pct < 60:
                    depl_color = "🟡"
                    depl_label = "Moderate depletion"
                else:
                    depl_color = "🔴"
                    depl_label = "High depletion"
                st.markdown(f"**W' Depletion:** {depl_color} {depletion_pct:.0f}% ({depl_label})")
        else:
            st.info("W' Balance data not available for this activity.")

    # HR Recovery Rate
    with col_recovery:
        st.markdown("#### 💓 HR Recovery")
        max_hr = get_metric(activity, "max_hr")
        avg_hr = get_metric(activity, "average_hr")
        hr_recovery = get_metric(activity, "hr_recovery_rate")

        c1, c2 = st.columns(2)
        render_metric(c1, "Max HR", f"{max_hr:.0f} bpm" if max_hr else "-", help_text="Peak heart rate during activity")
        render_metric(c2, "Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-", help_text="Time-weighted average heart rate")

        if hr_recovery is not None:
            # HR recovery interpretation
            if hr_recovery > 25:
                recovery_emoji = "🟢"
                recovery_label = "Excellent recovery"
            elif hr_recovery > 15:
                recovery_emoji = "🟡"
                recovery_label = "Good recovery"
            elif hr_recovery > 5:
                recovery_emoji = "🟠"
                recovery_label = "Fair recovery"
            else:
                recovery_emoji = "🔴"
                recovery_label = "Poor recovery"
            st.markdown(f"**Recovery Rate:** {recovery_emoji} {hr_recovery:.1f} bpm/min ({recovery_label})")
            st.caption("HR drop per minute during rest periods")
        else:
            st.caption("HR recovery rate requires rest periods detected in the activity.")

    st.divider()

    # ===== SECTION 3: Zone Distributions (two columns, aligned) =====
    render_zone_distributions(activity, help_texts)


def render_power_curve(activity: Activity, service: ActivityService, help_texts: dict) -> None:
    """Render power curve section with yearly best comparison."""
    st.markdown("### ⚡ Power Curve (Peak Powers)")
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
    power_curve_values = []

    for duration in power_curve_durations:
        val = get_metric(activity, f"power_curve_{duration}")
        power_curve_values.append(float(val) if val else 0)

    # Get yearly best power curve for comparison
    activity_year = activity.start_date_local.year
    yearly_activities = service.get_activities_for_year(activity_year)
    yearly_best_power_curve = [0] * len(power_curve_durations)

    for yearly_activity in yearly_activities:
        for i, duration in enumerate(power_curve_durations):
            yearly_val = get_metric(yearly_activity, f"power_curve_{duration}")
            if yearly_val:
                yearly_best_power_curve[i] = max(
                    yearly_best_power_curve[i], float(yearly_val)
                )

    if any(power_curve_values):
        fig_pc = go.Figure()

        # Add yearly best as background (lighter color)
        if any(yearly_best_power_curve):
            fig_pc.add_trace(
                go.Bar(
                    x=power_curve_labels,
                    y=yearly_best_power_curve,
                    marker_color="rgba(189, 195, 199, 0.3)",
                    name="Yearly Best",
                    text=[
                        f"{v:.0f}W" if v > 0 else ""
                        for v in yearly_best_power_curve
                    ],
                    textposition="outside",
                )
            )

        # Add current activity (foreground)
        fig_pc.add_trace(
            go.Bar(
                x=power_curve_labels,
                y=power_curve_values,
                marker_color="#f1c40f",
                name="This Activity",
                text=[f"{v:.0f}W" if v > 0 else "" for v in power_curve_values],
                textposition="outside",
            )
        )

        fig_pc.update_layout(
            yaxis_title="Power (W)",
            xaxis_title="Duration",
            margin={"t": 30, "b": 40},
            height=300,
            barmode="overlay",
            legend=dict(orientation="h", y=1.15, x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_pc, use_container_width=True)
    else:
        st.info("No power curve data available.")


def render_zone_distributions(activity: Activity, help_texts: dict) -> None:
    """Render zone distributions side by side (aligned)."""

    # ===== POWER ZONES =====
    power_zones = []
    for i in range(1, 8):
        val = get_metric(activity, f"power_z{i}_percentage")
        power_zones.append(float(val) if val else 0)

    # ===== HR ZONES =====
    hr_zones = []
    for i in range(1, 6):
        val = get_metric(activity, f"hr_z{i}_percentage")
        hr_zones.append(float(val) if val else 0)

    power_total = sum(power_zones)
    hr_total = sum(hr_zones)

    # ===== ROW 1: Zone Distribution Charts (aligned) =====
    col_power_zones, col_hr_zones = st.columns(2)

    with col_power_zones:
        st.markdown("##### ⚡ Power Zone Distribution")
        if power_total > 0:
            power_zones_pct = [z / power_total * 100 for z in power_zones]
            # Get pre-computed zone boundaries from activity
            zone_boundaries = [get_metric(activity, f"power_zone_{i}") for i in range(1, 7)]
            # Create custom hover text with zone ranges and watts
            hover_text = []
            for i, pct in enumerate(power_zones_pct):
                zone_num = i + 1
                range_str = POWER_ZONE_RANGES[zone_num]
                if zone_num < 7 and i < len(zone_boundaries) and zone_boundaries[i]:
                    # Z1-Z6: show range from previous boundary to current boundary
                    lower = int(zone_boundaries[i-1]) if i > 0 and zone_boundaries[i-1] else 0
                    upper = int(zone_boundaries[i])
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} ({lower}-{upper}W)")
                elif zone_num == 7 and i > 0 and zone_boundaries[i-1]:
                    # Z7: show > highest boundary
                    lower = int(zone_boundaries[i-1])
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} (>{lower}W)")
                else:
                    # Fallback if boundaries not available
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str}")
            fig_pz = go.Figure()
            fig_pz.add_trace(
                go.Bar(
                    y=[f"Z{i}" for i in range(1, 8)],
                    x=power_zones_pct,
                    orientation="h",
                    marker_color=POWER_ZONE_COLORS,
                    text=[f"{pct:.0f}%" for pct in power_zones_pct],
                    textposition="outside",
                    customdata=hover_text,
                    hovertemplate="%{customdata}<extra></extra>",
                )
            )
            fig_pz.update_layout(
                xaxis_title="% of Time",
                yaxis_title="Power Zone",
                height=250,
                margin={"l": 60, "r": 60, "t": 20, "b": 20},
                showlegend=False,
            )
            st.plotly_chart(fig_pz, use_container_width=True)
        else:
            st.info("No power zone data available.")

    with col_hr_zones:
        st.markdown("##### ❤️ HR Zone Distribution")
        if hr_total > 0:
            hr_zones_pct = [z / hr_total * 100 for z in hr_zones]
            # Get pre-computed zone boundaries from activity
            zone_boundaries = [get_metric(activity, f"hr_zone_{i}") for i in range(1, 6)]
            # Create custom hover text with zone ranges and bpm
            hover_text = []
            for i, pct in enumerate(hr_zones_pct):
                zone_num = i + 1
                range_str = HR_ZONE_RANGES[zone_num]
                if zone_num < 5 and i < len(zone_boundaries) and zone_boundaries[i]:
                    # Z1-Z4: show range from previous boundary to current boundary
                    lower = int(zone_boundaries[i-1]) if i > 0 and zone_boundaries[i-1] else 0
                    upper = int(zone_boundaries[i])
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} ({lower}-{upper} bpm)")
                elif zone_num == 5 and i > 0 and zone_boundaries[i-1]:
                    # Z5: show > highest boundary
                    lower = int(zone_boundaries[i-1])
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} (>{lower} bpm)")
                else:
                    # Fallback if boundaries not available
                    hover_text.append(f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str}")
            fig_hz = go.Figure()
            fig_hz.add_trace(
                go.Bar(
                    y=[f"Z{i}" for i in range(1, 6)],
                    x=hr_zones_pct,
                    orientation="h",
                    marker_color=HR_ZONE_COLORS,
                    text=[f"{pct:.0f}%" for pct in hr_zones_pct],
                    textposition="outside",
                    customdata=hover_text,
                    hovertemplate="%{customdata}<extra></extra>",
                )
            )
            fig_hz.update_layout(
                xaxis_title="% of Time",
                yaxis_title="HR Zone",
                height=250,
                margin={"l": 60, "r": 60, "t": 20, "b": 20},
                showlegend=False,
            )
            st.plotly_chart(fig_hz, use_container_width=True)
        else:
            st.info("No HR zone data available.")

    st.divider()

    # ===== ROW 2: TID Metrics (aligned) =====
    col_power_tid, col_hr_tid = st.columns(2)

    with col_power_tid:
        st.markdown("##### Power Training Intensity Distribution")
        col_a, col_b = st.columns(2)
        pol_idx = get_metric(activity, "power_polarization_index")
        tdr = get_metric(activity, "power_tdr")
        render_metric(
            col_a,
            "📊 Polarization Index",
            f"{pol_idx:.2f}" if pol_idx else "-",
            help_texts.get("polarization_index", ""),
        )
        render_metric(
            col_b,
            "⚖️ TDR",
            f"{tdr:.1f}" if tdr else "-",
            help_texts.get("tdr", ""),
        )

        # Power TID Bar Plot
        if power_total > 0:
            z1_pct = (power_zones[0] / power_total * 100) if power_total > 0 else 0
            z2_pct = (power_zones[1] / power_total * 100) if power_total > 0 else 0
            z3_pct = sum(power_zones[2:]) / power_total * 100 if power_total > 0 else 0

            fig_tid = go.Figure()
            fig_tid.add_trace(
                go.Bar(
                    x=["Low (Z1)", "Moderate (Z2)", "High (Z3+)"],
                    y=[z1_pct, z2_pct, z3_pct],
                    marker_color=["#808080", "#3498db", "#e74c3c"],
                    text=[f"{v:.0f}%" for v in [z1_pct, z2_pct, z3_pct]],
                    textposition="outside",
                )
            )
            fig_tid.update_layout(
                yaxis_title="% of Time",
                height=250,
                margin={"l": 40, "r": 40, "t": 20, "b": 40},
                showlegend=False,
            )
            st.plotly_chart(fig_tid, use_container_width=True)

    with col_hr_tid:
        st.markdown("##### HR Training Intensity Distribution")
        col_a, col_b = st.columns(2)
        hr_pol_idx = get_metric(activity, "hr_polarization_index")
        hr_tdr = get_metric(activity, "hr_tdr")
        render_metric(
            col_a,
            "❤️ HR Polarization",
            f"{hr_pol_idx:.2f}" if hr_pol_idx else "-",
            help_texts.get("polarization_index", ""),
        )
        render_metric(
            col_b,
            "⚖️ HR TDR",
            f"{hr_tdr:.1f}" if hr_tdr else "-",
            help_texts.get("tdr", ""),
        )

        # HR TID Bar Plot
        if hr_total > 0:
            z1_pct = (hr_zones[0] / hr_total * 100) if hr_total > 0 else 0
            z2_pct = (hr_zones[1] / hr_total * 100) if hr_total > 0 else 0
            z3_pct = sum(hr_zones[2:]) / hr_total * 100 if hr_total > 0 else 0

            fig_hr_tid = go.Figure()
            fig_hr_tid.add_trace(
                go.Bar(
                    x=["Low (Z1)", "Moderate (Z2)", "High (Z3+)"],
                    y=[z1_pct, z2_pct, z3_pct],
                    marker_color=["#808080", "#3498db", "#e74c3c"],
                    text=[f"{v:.0f}%" for v in [z1_pct, z2_pct, z3_pct]],
                    textposition="outside",
                )
            )
            fig_hr_tid.update_layout(
                yaxis_title="% of Time",
                height=250,
                margin={"l": 40, "r": 40, "t": 20, "b": 40},
                showlegend=False,
            )
            st.plotly_chart(fig_hr_tid, use_container_width=True)


def render_power_metrics_section(activity: Activity, help_texts: dict) -> None:
    """Render power metrics and distributions."""
    st.markdown("#### ⚡ Power Metrics")

    # Power Summary Stats
    c1, c2, c3 = st.columns(3)
    avg_pwr = get_metric(activity, "average_power")
    np_val = get_metric(activity, "normalized_power")
    max_pwr = get_metric(activity, "max_power")

    render_metric(c1, "⚡ Avg Power", f"{avg_pwr:.0f} W" if avg_pwr else "-", get_help_text("avg_power", help_texts))
    render_metric(c2, "📊 Norm Power", f"{np_val:.0f} W" if np_val else "-", get_help_text("normalized_power", help_texts))
    render_metric(c3, "📈 Max Power", f"{max_pwr:.0f} W" if max_pwr else "-", help_text="Peak power during activity")

    c1, c2, c3 = st.columns(3)
    w_kg = get_metric(activity, "power_per_kg")
    if_val = get_metric(activity, "intensity_factor")
    tss_val = get_metric(activity, "training_stress_score")

    render_metric(c1, "🏋️ W/kg", f"{w_kg:.2f}" if w_kg else "-", help_text="Average power normalized to body weight")
    render_metric(c2, "🎯 IF", f"{if_val:.2f}" if if_val else "-", get_help_text("intensity_factor", help_texts))
    render_metric(c3, "📈 TSS", f"{tss_val:.0f}" if tss_val else "-", get_help_text("tss", help_texts))

    st.divider()

    # Power Zone Distribution
    st.markdown("##### Power Zone Distribution")
    power_zones = []
    for i in range(1, 8):
        val = get_metric(activity, f"power_z{i}_percentage")
        power_zones.append(float(val) if val else 0)

    power_total = sum(power_zones)
    if power_total > 0:
        power_zones_pct = [z / power_total * 100 for z in power_zones]

        fig_pz = go.Figure()
        fig_pz.add_trace(
            go.Bar(
                y=[f"Z{i}" for i in range(1, 8)],
                x=power_zones_pct,
                orientation="h",
                marker_color=POWER_ZONE_COLORS,
                text=[f"{pct:.0f}%" for pct in power_zones_pct],
                textposition="outside",
            )
        )
        fig_pz.update_layout(
            xaxis_title="% of Time",
            yaxis_title="Power Zone",
            height=250,
            margin={"l": 60, "r": 60, "t": 20, "b": 20},
            showlegend=False,
        )
        st.plotly_chart(fig_pz, use_container_width=True)

        st.divider()

        # Power TID Metrics
        st.markdown("##### Power Training Intensity Distribution")
        col_a, col_b = st.columns(2)
        pol_idx = get_metric(activity, "power_polarization_index")
        tdr = get_metric(activity, "power_tdr")
        render_metric(
            col_a,
            "📊 Polarization Index",
            f"{pol_idx:.2f}" if pol_idx else "-",
            help_texts.get("polarization_index", ""),
        )
        render_metric(
            col_b,
            "⚖️ TDR",
            f"{tdr:.1f}" if tdr else "-",
            help_texts.get("tdr", ""),
        )

        # Power TID Bar Plot
        z1_pct = (power_zones[0] / power_total * 100) if power_total > 0 else 0
        z2_pct = (power_zones[1] / power_total * 100) if power_total > 0 else 0
        z3_pct = sum(power_zones[2:]) / power_total * 100 if power_total > 0 else 0

        fig_tid = go.Figure()
        fig_tid.add_trace(
            go.Bar(
                x=["Low (Z1)", "Moderate (Z2)", "High (Z3+)"],
                y=[z1_pct, z2_pct, z3_pct],
                marker_color=["#808080", "#3498db", "#e74c3c"],
                text=[f"{v:.0f}%" for v in [z1_pct, z2_pct, z3_pct]],
                textposition="outside",
            )
        )
        fig_tid.update_layout(
            yaxis_title="% of Time",
            height=300,
            margin={"l": 40, "r": 40, "t": 20, "b": 40},
            showlegend=False,
        )
        st.plotly_chart(fig_tid, use_container_width=True)
    else:
        st.info("No power zone data available.")


# ═══════════════════════════════════════════════════════════════════════════════
# DURABILITY & FATIGUE TAB
# ═══════════════════════════════════════════════════════════════════════════════


def render_durability_tab(
    activity: Activity, metric_view: str, help_texts: dict
) -> None:
    """Render the Durability & Fatigue analysis tab."""
    st.subheader(f"Durability & Fatigue Analysis ({metric_view})")

    col1, col2 = st.columns(2)

    # --- Left Column: Power Fatigue ---
    with col1:
        st.markdown("#### ⚡ Power Fatigue")

        fatigue_idx = get_metric(activity, "fatigue_index")
        decay_rate = get_metric(activity, "interval_300s_decay_rate")

        c1, c2 = st.columns(2)
        render_metric(c1, "Fatigue Index", f"{fatigue_idx:.1f}%" if fatigue_idx else "-", get_help_text("fatigue_index", help_texts))
        render_metric(c2, "Power Decay", f"{decay_rate:.1f}%" if decay_rate else "-", get_help_text("power_decay", help_texts))

        # Power durability metrics
        first_power = get_metric(activity, "interval_300s_first_power")
        last_power = get_metric(activity, "interval_300s_last_power")
        power_trend = get_metric(activity, "interval_300s_power_trend")

        if first_power and last_power and first_power > 0:
            power_drop_pct = ((first_power - last_power) / first_power) * 100
        else:
            power_drop_pct = None

        st.markdown("##### 300s Interval Analysis")
        col_a, col_b, col_c = st.columns(3)
        render_metric(col_a, "First Power", f"{first_power:.0f} W" if first_power else "-", help_text="Power in first 300s of ride")
        render_metric(col_b, "Last Power", f"{last_power:.0f} W" if last_power else "-", help_text="Power in final 300s of ride")
        render_metric(col_c, "Drop %", f"{power_drop_pct:.1f}%" if power_drop_pct is not None else "-", get_help_text("interval_300s_decay_rate", help_texts))

    # --- Right Column: HR Fatigue ---
    with col2:
        st.markdown("#### ❤️ Heart Rate Fatigue")

        # HR fatigue metrics from effort distribution
        hr_decoupling = get_metric(activity, "power_hr_decoupling")
        hr_tss = get_metric(activity, "hr_training_stress")
        cardiac_drift = get_metric(activity, "cardiac_drift")
        first_half_ef = get_metric(activity, "first_half_ef")
        second_half_ef = get_metric(activity, "second_half_ef")

        c1, c2 = st.columns(2)
        render_metric(c1, "HR Decoupling", f"{hr_decoupling:.1f}%" if hr_decoupling is not None else "-", get_help_text("power_hr_decoupling", help_texts))
        render_metric(c2, "HR TSS", f"{hr_tss:.0f}" if hr_tss else "-", get_help_text("hr_training_stress", help_texts))

        st.markdown("##### Effort Distribution")
        col_a, col_b = st.columns(2)
        render_metric(col_a, "First Half EF", f"{first_half_ef:.2f}" if first_half_ef else "-", get_help_text("first_half_ef", help_texts))

        # Cardiac Drift with interpretation
        if cardiac_drift is not None:
            if cardiac_drift < 3:
                drift_emoji = "🟢"
                drift_label = "Excellent"
            elif cardiac_drift < 5:
                drift_emoji = "🟡"
                drift_label = "Good"
            elif cardiac_drift < 8:
                drift_emoji = "🟠"
                drift_label = "Moderate"
            else:
                drift_emoji = "🔴"
                drift_label = "Poor/Fatigued"
            render_metric(col_b, "Cardiac Drift", f"{drift_emoji} {cardiac_drift:.1f}%", get_help_text("cardiac_drift", help_texts))
            with col_b:
                st.caption(drift_label)
        else:
            render_metric(col_b, "Cardiac Drift", "-", get_help_text("cardiac_drift", help_texts))

    st.divider()

    # Interval Distribution Section
    st.subheader("📊 Interval Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Power Intervals")
        power_trend = get_metric(activity, "interval_300s_power_trend")
        decay_rate = get_metric(activity, "interval_300s_decay_rate")

        col_a, col_b = st.columns(2)
        render_metric(col_a, "Avg Change", f"{power_trend:.2f} W/int" if power_trend else "-", get_help_text("interval_300s_power_trend", help_texts))
        render_metric(col_b, "Decay Rate", f"{decay_rate:.1f}%" if decay_rate else "-", get_help_text("interval_300s_decay_rate", help_texts))

    with col2:
        st.markdown("##### HR Intervals")

        # HR TID metrics
        hr_tid_z1 = get_metric(activity, "hr_tid_z1_percentage")
        hr_tid_z2 = get_metric(activity, "hr_tid_z2_percentage")
        hr_tid_z3 = get_metric(activity, "hr_tid_z3_percentage")
        hr_polarization = get_metric(activity, "hr_polarization_index")

        col_a, col_b = st.columns(2)
        render_metric(col_a, "Polarization Index", f"{hr_polarization:.2f}" if hr_polarization else "-", get_help_text("hr_polarization_index", help_texts))

        st.markdown("**HR Zone Distribution (TID):**")
        col_x, col_y, col_z = st.columns(3)
        render_metric(col_x, "Z1 %", f"{hr_tid_z1:.1f}%" if hr_tid_z1 else "-", get_help_text("hr_tid_z1_percentage", help_texts))
        render_metric(col_y, "Z2 %", f"{hr_tid_z2:.1f}%" if hr_tid_z2 else "-", get_help_text("hr_tid_z2_percentage", help_texts))
        render_metric(col_z, "Z3 %", f"{hr_tid_z3:.1f}%" if hr_tid_z3 else "-", get_help_text("hr_tid_z3_percentage", help_texts))


def render_training_load_tab(
    activity: Activity, metric_view: str, help_texts: dict
) -> None:
    """
    Render the Training Load & Power Profile tab.

    Displays:
    - Longitudinal training load metrics (CTL, ATL, TSB, ACWR)
    - Critical Power model metrics (CP, W', R², AEI)

    These metrics are computed separately for raw and moving data modes,
    reflecting different training load assessments based on data source.
    """
    st.subheader(f"📊 Training Load & Power Profile ({metric_view})")

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1: TRAINING LOAD METRICS
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("### Training Load State")
    st.markdown("Time-weighted exponential averages as of this activity's date:")

    col1, col2, col3, col4 = st.columns(4)

    # CTL (Chronic Training Load)
    ctl = get_metric(activity, "chronic_training_load")
    render_metric(
        col1,
        "CTL (42d)",
        f"{ctl:.1f}" if ctl else "-",
        get_help_text("chronic_training_load", help_texts)
    )

    # ATL (Acute Training Load)
    atl = get_metric(activity, "acute_training_load")
    render_metric(
        col2,
        "ATL (7d)",
        f"{atl:.1f}" if atl else "-",
        get_help_text("acute_training_load", help_texts)
    )

    # TSB (Training Stress Balance)
    tsb = get_metric(activity, "training_stress_balance")
    tsb_color = "🟢" if tsb is not None and -10 <= tsb <= 20 else ("🟡" if tsb is not None and -50 <= tsb < -10 else "🔴")
    render_metric(
        col3,
        "TSB",
        f"{tsb_color} {tsb:.1f}" if tsb else "-",
        get_help_text("training_stress_balance", help_texts)
    )

    # ACWR (Acute:Chronic Workload Ratio)
    acwr = get_metric(activity, "acwr")
    acwr_color = "🟢" if acwr is not None and 0.8 <= acwr <= 1.3 else ("🟡" if acwr is not None and acwr <= 1.5 else "🔴")
    render_metric(
        col4,
        "ACWR",
        f"{acwr_color} {acwr:.2f}" if acwr else "-",
        get_help_text("acwr", help_texts)
    )

    # Training State Summary
    if tsb is not None:
        if tsb > 20:
            state = "✅ Well-rested - Good for intensity work"
            state_color = "green"
        elif 0 <= tsb <= 20:
            state = "🎯 Optimal zone - Productive training"
            state_color = "blue"
        elif -10 <= tsb < 0:
            state = "⚠️ Elevated fatigue - Productive but stressed"
            state_color = "orange"
        elif tsb < -10:
            state = "🔴 Overreached - Recovery needed"
            state_color = "red"
        else:
            state = "❓ Unknown state"
            state_color = "gray"

        st.markdown(f"**Training State:** <span style='color:{state_color}'>{state}</span>", unsafe_allow_html=True)

    st.divider()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2: CRITICAL POWER MODEL
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("### Critical Power Model")
    st.markdown("Power-duration curve fit from 90-day rolling window:")

    col1, col2, col3, col4 = st.columns(4)

    # CP (Critical Power)
    cp = get_metric(activity, "cp")
    render_metric(
        col1,
        "CP (W)",
        f"{cp:.0f}" if cp else "-",
        get_help_text("cp", help_texts)
    )

    # W' (W-prime)
    w_prime = get_metric(activity, "w_prime")
    render_metric(
        col2,
        "W' (kJ)",
        f"{(w_prime/1000):.1f}" if w_prime else "-",
        get_help_text("w_prime", help_texts)
    )

    # R² (Model fit quality)
    r_squared = get_metric(activity, "cp_r_squared")
    r_sq_color = "🟢" if r_squared is not None and r_squared > 0.95 else ("🟡" if r_squared is not None and r_squared > 0.85 else "🔴")
    render_metric(
        col3,
        "R²",
        f"{r_sq_color} {r_squared:.3f}" if r_squared else "-",
        get_help_text("cp_r_squared", help_texts)
    )

    # AEI (Anaerobic Energy Index)
    aei = get_metric(activity, "aei")
    render_metric(
        col4,
        "AEI (J/kg)",
        f"{aei:.1f}" if aei else "-",
        get_help_text("aei", help_texts)
    )

    # Model details
    st.markdown("#### Model Details")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Hyperbolic Model:** P(t) = CP + W'/t")
        if cp is not None:
            st.markdown(f"""
- **CP** = {cp:.0f}W - Sustainable power for extended efforts
- **W'** = {w_prime/1000:.1f}kJ - Anaerobic work capacity
- **AEI** = {aei:.1f}J/kg - Normalized anaerobic capacity
            """)

    with col2:
        st.markdown("**Fit Quality:**")
        if r_squared is not None:
            fit_desc = "Excellent ✅" if r_squared > 0.95 else ("Good 👍" if r_squared > 0.85 else "Fair ⚠️")
            st.markdown(f"""
- **R²** = {r_squared:.3f} ({fit_desc})
- **Window** = 90 days rolling
- **Data Points** = Multiple durations in power curve
            """)

    st.markdown("---")
    st.markdown("""
**Notes:**
- Metrics computed from 90-day rolling power curve (most recent 90 calendar days)
- CP model evolves as fitness changes
- R² > 0.95 indicates excellent model fit quality
- Compare AEI over time to track anaerobic capacity changes
""")

