import ast

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from activities_viewer.data.help_texts import get_help_text
from activities_viewer.domain.models import Activity
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils.formatting import (
    get_metric,
    render_metric,
)

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


def get_workout_type_info(workout_type: float | None = None) -> tuple[str, str]:
    """
    Get workout type label and emoji based on Strava workout_type code.

    Args:
        workout_type: Strava workout type code (10=Race, 11=Long Run, 12=Workout, etc.)

    Returns:
        Tuple of (label, emoji)
    """
    if workout_type is None or pd.isna(workout_type):
        return "General", "🚴"

    workout_type_int = int(workout_type)
    workout_types = {
        10: ("Race", "🏁"),
        11: ("Long Run/Ride", "🏃"),
        12: ("Workout/Intervals", "💪"),
        1: ("Easy", "😌"),
        2: ("Tempo", "⚡"),
        3: ("Threshold", "🔥"),
    }

    return workout_types.get(workout_type_int, ("General", "🚴"))


def apply_smoothing(data: pd.Series, window_size: int) -> pd.Series:
    """Apply rolling average smoothing to a series."""
    if window_size is None or window_size <= 1:
        return data
    return data.rolling(window=window_size, center=True, min_periods=1).mean()


def render_summary(activity: Activity, metric_view: str, help_texts: dict = None):
    """Render the activity summary section with key metrics."""
    if help_texts is None:
        help_texts = {}

    st.subheader("Activity Summary")

    # Get workout type info
    workout_type, workout_emoji = get_workout_type_info(
        getattr(activity, "workout_type", None)
    )

    # Pre-calculate key metrics
    distance_km = get_metric(activity, "distance")
    if distance_km:
        distance_km = distance_km / 1000

    time_field = "moving_time" if metric_view == "Moving Time" else "elapsed_time"
    duration = get_metric(activity, time_field)
    if duration:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    else:
        duration_str = "-"

    np_val = get_metric(activity, "normalized_power")
    tss = get_metric(activity, "training_stress_score")

    st.markdown(f"##### {workout_emoji} {workout_type}")

    hero1, hero2, hero3 = st.columns(3)

    # Tier 1 Metrics.
    render_metric(
        hero1, "🛣️ Distance", f"{distance_km:.1f} km" if distance_km else "-"
    )

    render_metric(
        hero2,
        "📈 Training Load", f"{tss:.0f} TSS" if tss else "-",
        help_text="Training Stress Score - quantifies physiological cost",
    )

    render_metric(
        hero3,
        "📊 Norm Power", f"{np_val:.0f} W" if np_val else "-",
        help_text="Normalized Power - represents the equivalent steady-state power"
    )

    st.divider()

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    col5, col6 = st.columns(2)
    col7, col8 = st.columns(2)
    col9, col10 = st.columns(2)

    time_label = "⏱️ Moving Time" if metric_view == "Moving Time" else "⏱️ Total Time"
    render_metric(
        col1, time_label, duration_str, get_help_text("moving_time", help_texts)
    )

    elevation = get_metric(activity, "total_elevation_gain")
    render_metric(col2, "⛰️ Elevation", f"{elevation:.0f} m" if elevation else "-")

    # Average Speed
    avg_speed = get_metric(activity, "average_speed")
    if avg_speed is None or pd.isna(avg_speed):
        distance = get_metric(activity, "distance")
        time_value = get_metric(activity, time_field)
        if distance and time_value and time_value > 0:
            avg_speed = distance / time_value
        else:
            avg_speed = None

    avg_speed_kmh = avg_speed * 3.6 if avg_speed and avg_speed > 0 else None
    render_metric(
        col3, "🚀 Speed", f"{avg_speed_kmh:.1f} km/h" if avg_speed_kmh else "-"
    )

    # Average Power
    avg_power = get_metric(activity, "average_power")
    render_metric(
        col4,
        "⚡ Avg Power",
        f"{avg_power:.0f} W" if avg_power else "-",
        get_help_text("avg_power", help_texts),
    )

    # Average HR
    avg_hr = get_metric(activity, "average_hr")
    render_metric(
        col5,
        "❤️ Avg HR",
        f"{avg_hr:.0f} bpm" if avg_hr else "-",
        get_help_text("average_hr", help_texts),
    )

    # Average Cadence
    avg_cadence = get_metric(activity, "average_cadence")
    render_metric(
        col6,
        "🔄 Cadence",
        f"{avg_cadence:.0f} rpm" if avg_cadence and avg_cadence > 0 else "-",
        get_help_text("average_cadence", help_texts),
    )

    # Intensity Factor
    if_val = get_metric(activity, "intensity_factor")
    render_metric(
        col7,
        "🎯 IF",
        f"{if_val:.2f}" if if_val else "-",
        get_help_text("intensity_factor", help_texts),
    )

    # Efficiency Factor
    ef = get_metric(activity, "efficiency_factor")
    render_metric(
        col8,
        "⚙️ EF",
        f"{ef:.2f}" if ef else "-",
        get_help_text("efficiency_factor", help_texts),
    )

    # Max HR
    max_hr = get_metric(activity, "max_hr")
    render_metric(
        col9,
        "💓 Max HR",
        f"{max_hr:.0f} bpm" if max_hr else "-",
        get_help_text("max_hr", help_texts),
    )

    # Energy
    calories = get_metric(activity, "kilojoules")
    render_metric(
        col10,
        "🔥 Energy",
        f"{calories:.0f} kJ" if calories else "-",
        get_help_text("kilojoules", help_texts),
    )


def render_pacing_analysis(activity: Activity, help_texts: dict = None):
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
            get_help_text("negative_split_index", help_texts),
        )
        with col1:
            st.caption(nsi_label)
    else:
        render_metric(
            col1,
            "Negative Split Index",
            "-",
            get_help_text("negative_split_index", help_texts),
        )

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
            get_help_text("match_burn_count", help_texts),
        )
        with col2:
            st.caption(burn_label)
    else:
        render_metric(
            col2, "Match Burns", "-", get_help_text("match_burn_count", help_texts)
        )

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
            get_help_text("time_above_90_ftp", help_texts),
        )
        with col3:
            st.caption(f"{time_label} ({pct:.1f}% of ride)")
    else:
        render_metric(
            col3,
            "Time in Red (>90% FTP)",
            "-",
            get_help_text("time_above_90_ftp", help_texts),
        )


def render_climbing_analysis(activity: Activity, help_texts: dict = None):
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
            col1, "VAM", f"{vam_emoji} {vam:.0f} m/h", get_help_text("vam", help_texts)
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
            get_help_text("climbing_power_per_kg", help_texts),
        )
        with col2:
            st.caption(wkg_label)
    else:
        render_metric(
            col2,
            "Climbing W/kg",
            "-",
            get_help_text("climbing_power_per_kg", help_texts),
        )

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
            col3, "Climbing Time", time_str, get_help_text("climbing_time", help_texts)
        )
        with col3:
            st.caption(f"{pct:.0f}% of ride")
    else:
        render_metric(
            col3, "Climbing Time", "-", get_help_text("climbing_time", help_texts)
        )


def render_route_map(activity: Activity, service: ActivityService):
    """Render the route map for the activity.

    Args:
        activity: Activity object to display
        service: ActivityService for data fetching
    """
    stream = service.get_activity_stream(activity.id)

    if stream.empty:
        st.info("No GPS data available for this activity.")
        return

    # Parse latlng if string
    if "latlng" in stream.columns:
        if isinstance(stream["latlng"].iloc[0], str):
            stream["latlng"] = stream["latlng"].apply(
                lambda x: ast.literal_eval(x)
                if pd.notna(x) and x != "[]" else None
            )
        map_data = stream.dropna(subset=["latlng"])
    else:
        map_data = pd.DataFrame()

    with st.expander("🗺️ Route Map", expanded=False):
        if map_data.empty:
            st.info("No GPS data available.")
            return
        start_loc = map_data["latlng"].iloc[0]
        m = folium.Map(location=start_loc, zoom_start=12)
        points = map_data["latlng"].tolist()
        folium.PolyLine(
            points, color="#e74c3c", weight=4, opacity=0.8
        ).add_to(m)
        m.fit_bounds(m.get_bounds())
        st_folium(m, width=None, height=400)


def render_time_series_plots(activity: Activity, service: ActivityService) -> None:
    """Render time-series plots for activity metrics."""
    stream = service.get_activity_stream(activity.id)
    if stream.empty:
        st.info("No time-series data available for this activity.")
        return

    # Create synchronized plots with shared x-axis
    with st.expander("📈 Activity Metrics Time Series", expanded=False):
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
                    time_sec = plot_data["time"].iloc[idx]
                    mins, secs = divmod(int(time_sec), 60)
                    hours, mins = divmod(mins, 60)
                    if hours > 0:
                        hover_parts.append(
                            f"<b>Time: {hours}:{mins:02d}:{secs:02d}</b>"
                        )
                    else:
                        hover_parts.append(f"<b>Time: {mins}:{secs:02d}</b>")
                else:
                    hover_parts.append(f"<b>Point {idx}</b>")
                if has_speed:
                    hover_parts.append(
                        f"Speed: {plot_data['speed_kmh'].iloc[idx]:.1f} km/h"
                    )
                if has_power:
                    hover_parts.append(f"Power: {plot_data['watts'].iloc[idx]:.0f} W")
                if has_hr:
                    hover_parts.append(
                        f"HR: {plot_data['heartrate'].iloc[idx]:.0f} bpm"
                    )
                if has_cadence:
                    hover_parts.append(
                        f"Cadence: {plot_data['cadence'].iloc[idx]:.0f} rpm"
                    )
                if has_grade:
                    hover_parts.append(f"Grade: {plot_data['grade'].iloc[idx]:.1f}%")
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
            st.plotly_chart(fig_sync, width="stretch")
        else:
            st.info("No time-series data available.")


def render_exportable_table(activity: Activity, service: ActivityService) -> None:
    with st.expander("📋 Show All Metrics (Complete Data Export)", expanded=False):
        st.caption("**Complete activity data** - all metrics from CSV export")

        # Import MetricRegistry to get formatted values
        from activities_viewer.domain.metrics import MetricRegistry

        # Get all activity fields
        activity_dict = activity.model_dump()

        # Organize metrics by category using MetricRegistry
        categorized_metrics = {}
        uncategorized_metrics = {}

        for field_name, value in activity_dict.items():
            # Skip None/NaN values
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue

            # Try to find metric definition
            metric_def = MetricRegistry.get_by_id(field_name)

            if metric_def:
                category = metric_def.category.value
                if category not in categorized_metrics:
                    categorized_metrics[category] = []

                # Format value using metric's formatter
                formatted_value = metric_def.format_func(value)

                categorized_metrics[category].append(
                    {
                        "Metric": metric_def.label,
                        "Value": formatted_value,
                        "Description": metric_def.help_text,
                    }
                )
            else:
                # Uncategorized/meta fields
                uncategorized_metrics[field_name] = value

        # Display categorized metrics
        for category, metrics in sorted(categorized_metrics.items()):
            st.markdown(f"**{category}**")
            df_cat = pd.DataFrame(metrics)
            st.dataframe(df_cat, width="stretch", hide_index=True)

        # Display uncategorized fields (metadata, IDs, etc.)
        if uncategorized_metrics:
            st.markdown("**Metadata & Identifiers**")
            meta_data = []
            for field, value in sorted(uncategorized_metrics.items()):
                # Format field name nicely
                label = field.replace("_", " ").title()
                meta_data.append({"Field": label, "Value": str(value)})

            df_meta = pd.DataFrame(meta_data)
            st.dataframe(df_meta, width="stretch", hide_index=True)


def render_overview_tab(
    activity: Activity,
    service: ActivityService,
    metric_view: str = "Moving Time",
    help_texts: dict = None,
) -> None:
    """Render the Overview tab with summary metrics, map, and time-series plots.

    Args:
        activity: Activity object to display
        service: ActivityService for data fetching
        metric_view: "Moving" or "Total" (for prefix selection)
        help_texts: Dictionary of help text strings
    """

    # High-level summary metrics
    render_summary(activity, metric_view, help_texts)
    st.divider()

    # Pacing Analysis - always show if we have power data
    avg_power = get_metric(activity, "average_power")
    if avg_power:
        render_pacing_analysis(activity, help_texts)
        st.divider()

    # Climbing Analysis - always present
    render_climbing_analysis(activity, help_texts)
    st.divider()

    # Route Map
    render_route_map(activity, service)
    st.divider()

    # Time-Series Plots
    render_time_series_plots(activity, service)
    st.divider()

    # Render exportable full metrics table
    render_exportable_table(activity, service)


