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
            # Escape newlines and quotes for HTML attribute
            help_escaped = help_text.replace('\n', '\\n').replace('"', '&quot;')
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
) -> tuple[Activity | None, str, str]:
    """
    Render activity selection UI with calendar and dropdown.

    Returns:
        Tuple of (selected_activity, activity_id, metric_view)
    """
    df_activities = service.get_all_activities()
    if df_activities.empty:
        st.warning("No activities found.")
        return None, "", ""

    # Ensure datetime (already sorted by date desc from repository)
    df_activities["start_date_local"] = pd.to_datetime(
        df_activities["start_date_local"], utc=True
    )

    # Get date range for calendar
    min_date = df_activities["start_date_local"].min().date()
    max_date = df_activities["start_date_local"].max().date()

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

    # Get selected activity
    selected_row = df_for_selection[
        df_for_selection["name"] == selected_activity_name
    ].iloc[0]
    activity_id = selected_row["id"]
    activity = service.get_activity(activity_id)

    # Metric view selector
    col1, col2 = st.columns(2)
    with col1:
        metric_view = st.radio(
            "View:", ("Moving", "Total"), horizontal=True, label_visibility="collapsed"
        )
    with col2:
        st.caption("Choose between moving time or total time metrics")

    return activity, activity_id, metric_view


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


def render_overview_tab(activity: Activity, service: ActivityService, metric_view: str = "Moving", help_texts: dict = None) -> None:
    """Render the Overview tab with summary metrics, map, and time-series plots.
    
    Args:
        activity: Activity object to display
        service: ActivityService for data fetching
        metric_view: "Moving" or "Total" (for prefix selection)
        help_texts: Dictionary of help text strings
    """
    if help_texts is None:
        help_texts = {}

    # Determine field prefix based on metric view
    # "Moving" uses "moving_" prefix, "Total" uses "raw_" prefix
    prefix = "moving_" if metric_view == "Moving" else "raw_"

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

    # Duration (moving time)
    moving_time = get_metric(activity, "moving_time")
    if moving_time:
        hours = int(moving_time // 3600)
        minutes = int((moving_time % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    else:
        duration_str = "-"
    render_metric(col2, "⏱️ Moving Time", duration_str)

    # Elevation
    elevation = get_metric(activity, "total_elevation_gain")
    render_metric(col3, "⛰️ Elevation", f"{elevation:.0f} m" if elevation else "-")

    # Average Speed - try prefixed first, then base average_speed, then compute from distance/moving_time
    avg_speed = get_metric(activity, f"{prefix}average_speed")
    if avg_speed is None or pd.isna(avg_speed):
        # Try base average_speed from Strava API
        avg_speed = get_metric(activity, "average_speed")
    if avg_speed is None or pd.isna(avg_speed):
        # Compute from distance and moving_time if available
        distance = get_metric(activity, "distance")
        moving_time = get_metric(activity, "moving_time")
        if distance and moving_time and moving_time > 0:
            avg_speed = distance / moving_time  # In m/s
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

    # Average Power - use prefix
    avg_power = get_metric(activity, f"{prefix}average_power")
    render_metric(col1, "⚡ Avg Power", f"{avg_power:.0f} W" if avg_power else "-", get_help_text("avg_power", help_texts))

    # Normalized Power - use prefix
    np_val = get_metric(activity, f"{prefix}normalized_power")
    render_metric(col2, "📊 Norm Power", f"{np_val:.0f} W" if np_val else "-", get_help_text("normalized_power", help_texts))

    # TSS - use prefix
    tss = get_metric(activity, f"{prefix}training_stress_score")
    render_metric(col3, "📈 TSS", f"{tss:.0f}" if tss else "-", get_help_text("tss", help_texts))

    # Average HR - use prefix
    avg_hr = get_metric(activity, f"{prefix}average_hr")
    render_metric(col4, "❤️ Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-")

    # Max HR - use prefix
    max_hr = get_metric(activity, f"{prefix}max_hr")
    render_metric(col5, "💓 Max HR", f"{max_hr:.0f} bpm" if max_hr else "-")

    # Row 3: Additional metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    # Intensity Factor - use prefix
    if_val = get_metric(activity, f"{prefix}intensity_factor")
    render_metric(col1, "🎯 IF", f"{if_val:.2f}" if if_val else "-", get_help_text("intensity_factor", help_texts))

    # Efficiency Factor - use prefix
    ef = get_metric(activity, f"{prefix}efficiency_factor")
    render_metric(col2, "⚙️ EF", f"{ef:.2f}" if ef else "-", get_help_text("efficiency_factor", help_texts))

    # Average Cadence - use base field (no prefixed variants exist)
    avg_cadence = get_metric(activity, "average_cadence")
    render_metric(col3, "🔄 Cadence", f"{avg_cadence:.0f} rpm" if avg_cadence and avg_cadence > 0 else "-")

    # Calories
    calories = get_metric(activity, "kilojoules")
    render_metric(col4, "🔥 Energy", f"{calories:.0f} kJ" if calories else "-")

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

    prefix = "moving_" if metric_view == "Moving" else "raw_"

    # ===== SECTION 1: POWER CURVE (spans both columns) =====
    render_power_curve(activity, service, help_texts)

    st.divider()

    # ===== SECTION 2: Summary Stats (two columns, aligned) =====
    col_power, col_hr = st.columns(2)

    with col_power:
        st.markdown("#### ⚡ Power Metrics")
        c1, c2, c3 = st.columns(3)
        avg_pwr = get_metric(activity, f"{prefix}average_power")
        np_val = get_metric(activity, f"{prefix}normalized_power")
        max_pwr = get_metric(activity, f"{prefix}max_power")
        render_metric(c1, "Avg Power", f"{avg_pwr:.0f} W" if avg_pwr else "-", get_help_text("avg_power", help_texts))
        render_metric(c2, "Norm Power", f"{np_val:.0f} W" if np_val else "-", get_help_text("normalized_power", help_texts))
        render_metric(c3, "Max Power", f"{max_pwr:.0f} W" if max_pwr else "-")

        c1, c2, c3 = st.columns(3)
        w_kg = get_metric(activity, f"{prefix}power_per_kg")
        if_val = get_metric(activity, f"{prefix}intensity_factor")
        tss_val = get_metric(activity, f"{prefix}training_stress_score")
        render_metric(c1, "W/kg", f"{w_kg:.2f}" if w_kg else "-")
        render_metric(c2, "IF", f"{if_val:.2f}" if if_val else "-", get_help_text("intensity_factor", help_texts))
        render_metric(c3, "TSS", f"{tss_val:.0f}" if tss_val else "-", get_help_text("tss", help_texts))

    with col_hr:
        st.markdown("#### ❤️ Heart Rate Metrics")
        c1, c2, c3 = st.columns(3)
        avg_hr = get_metric(activity, f"{prefix}average_hr")
        max_hr = get_metric(activity, f"{prefix}max_hr")
        hr_tss = get_metric(activity, f"{prefix}hr_training_stress")
        render_metric(c1, "Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-")
        render_metric(c2, "Max HR", f"{max_hr:.0f} bpm" if max_hr else "-")
        render_metric(c3, "HR TSS", f"{hr_tss:.0f}" if hr_tss else "-")

        c1, c2, c3 = st.columns(3)
        ef = get_metric(activity, f"{prefix}efficiency_factor")
        decoupling = get_metric(activity, f"{prefix}power_hr_decoupling")
        hr_type = get_metric(activity, f"{prefix}hr_tid_classification")
        render_metric(c1, "EF", f"{ef:.2f}" if ef else "-", get_help_text("efficiency_factor", help_texts))
        render_metric(c2, "Decoupling", f"{decoupling:.1f}%" if decoupling else "-", get_help_text("decoupling", help_texts))
        render_metric(c3, "Type", hr_type if hr_type else "-")

    st.divider()

    # ===== SECTION 3: Zone Distributions (two columns, aligned) =====
    render_zone_distributions(activity, prefix, help_texts)


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


def render_zone_distributions(activity: Activity, prefix: str, help_texts: dict) -> None:
    """Render zone distributions side by side (aligned)."""

    # ===== POWER ZONES =====
    power_zones = []
    for i in range(1, 8):
        val = get_metric(activity, f"{prefix}power_z{i}_percentage")
        power_zones.append(float(val) if val else 0)

    # ===== HR ZONES =====
    hr_zones = []
    for i in range(1, 6):
        val = get_metric(activity, f"{prefix}hr_z{i}_percentage")
        hr_zones.append(float(val) if val else 0)

    power_total = sum(power_zones)
    hr_total = sum(hr_zones)

    # ===== ROW 1: Zone Distribution Charts (aligned) =====
    col_power_zones, col_hr_zones = st.columns(2)

    with col_power_zones:
        st.markdown("##### ⚡ Power Zone Distribution")
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
        else:
            st.info("No power zone data available.")

    with col_hr_zones:
        st.markdown("##### ❤️ HR Zone Distribution")
        if hr_total > 0:
            hr_zones_pct = [z / hr_total * 100 for z in hr_zones]
            fig_hz = go.Figure()
            fig_hz.add_trace(
                go.Bar(
                    y=[f"Z{i}" for i in range(1, 6)],
                    x=hr_zones_pct,
                    orientation="h",
                    marker_color=HR_ZONE_COLORS,
                    text=[f"{pct:.0f}%" for pct in hr_zones_pct],
                    textposition="outside",
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
        pol_idx = get_metric(activity, f"{prefix}power_polarization_index")
        tdr = get_metric(activity, f"{prefix}power_tdr")
        col_a.metric(
            "Polarization Index",
            f"{pol_idx:.2f}" if pol_idx else "-",
            help=help_texts.get("polarization_index", ""),
        )
        col_b.metric(
            "TDR",
            f"{tdr:.1f}" if tdr else "-",
            help=help_texts.get("tdr", ""),
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
        hr_pol_idx = get_metric(activity, f"{prefix}hr_polarization_index")
        hr_tdr = get_metric(activity, f"{prefix}hr_tdr")
        col_a.metric(
            "HR Polarization",
            f"{hr_pol_idx:.2f}" if hr_pol_idx else "-",
            help=help_texts.get("polarization_index", ""),
        )
        col_b.metric(
            "HR TDR",
            f"{hr_tdr:.1f}" if hr_tdr else "-",
            help=help_texts.get("tdr", ""),
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


def render_power_metrics_section(activity: Activity, prefix: str, help_texts: dict) -> None:
    """Render power metrics and distributions."""
    st.markdown("#### ⚡ Power Metrics")

    # Power Summary Stats
    c1, c2, c3 = st.columns(3)
    avg_pwr = get_metric(activity, f"{prefix}average_power")
    np_val = get_metric(activity, f"{prefix}normalized_power")
    max_pwr = get_metric(activity, f"{prefix}max_power")

    c1.metric("Avg Power", f"{avg_pwr:.0f} W" if avg_pwr else "-")
    c2.metric("Norm Power", f"{np_val:.0f} W" if np_val else "-")
    c3.metric("Max Power", f"{max_pwr:.0f} W" if max_pwr else "-")

    c1, c2, c3 = st.columns(3)
    w_kg = get_metric(activity, f"{prefix}power_per_kg")
    if_val = get_metric(activity, f"{prefix}intensity_factor")
    tss_val = get_metric(activity, f"{prefix}training_stress_score")

    c1.metric("W/kg", f"{w_kg:.2f}" if w_kg else "-")
    c2.metric("IF", f"{if_val:.2f}" if if_val else "-")
    c3.metric("TSS", f"{tss_val:.0f}" if tss_val else "-")

    st.divider()

    # Power Zone Distribution
    st.markdown("##### Power Zone Distribution")
    power_zones = []
    for i in range(1, 8):
        val = get_metric(activity, f"{prefix}power_z{i}_percentage")
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
        pol_idx = get_metric(activity, f"{prefix}power_polarization_index")
        tdr = get_metric(activity, f"{prefix}power_tdr")
        col_a.metric(
            "Polarization Index",
            f"{pol_idx:.2f}" if pol_idx else "-",
            help=help_texts.get("polarization_index", ""),
        )
        col_b.metric(
            "TDR",
            f"{tdr:.1f}" if tdr else "-",
            help=help_texts.get("tdr", ""),
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

    prefix = "moving_" if metric_view == "Moving" else "raw_"

    col1, col2 = st.columns(2)

    # --- Left Column: Power Fatigue ---
    with col1:
        st.markdown("#### ⚡ Power Fatigue")

        fatigue_idx = get_metric(activity, f"{prefix}fatigue_index")
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
        render_metric(col_a, "First Power", f"{first_power:.0f} W" if first_power else "-")
        render_metric(col_b, "Last Power", f"{last_power:.0f} W" if last_power else "-")
        render_metric(col_c, "Drop %", f"{power_drop_pct:.1f}%" if power_drop_pct is not None else "-")

    # --- Right Column: HR Fatigue ---
    with col2:
        st.markdown("#### ❤️ Heart Rate Fatigue")

        # Note: No prefixed HR fatigue metrics exist in the CSV
        # Only showing info message
        st.info("Not enough interval data for HR decay analysis.")

    st.divider()

    # Interval Distribution Section
    st.subheader("📊 Interval Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Power Intervals")
        power_trend = get_metric(activity, "interval_300s_power_trend")
        decay_rate = get_metric(activity, "interval_300s_decay_rate")

        col_a, col_b = st.columns(2)
        render_metric(col_a, "Avg Change", f"{power_trend:.2f} W/int" if power_trend else "-")
        render_metric(col_b, "Decay Rate", f"{decay_rate:.1f}%" if decay_rate else "-")

    with col2:
        st.markdown("##### HR Intervals")
        st.info("No HR interval data available.")
