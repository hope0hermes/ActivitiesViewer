"""
Weekly Analysis Page Components.

Extracted rendering functions for the weekly analysis page tabs.
Each function handles a specific UI section to keep main() clean.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT: Week Selector & Navigation
# ═══════════════════════════════════════════════════════════════════════════════


def render_week_selector(available_weeks: list, selected_sports: list) -> tuple:
    """
    Render week selector sidebar and return selected week and metric view.

    Args:
        available_weeks: Sorted list of week start dates
        selected_sports: List of selected sport types for filtering

    Returns:
        Tuple of (selected_week, metric_view, selected_sports)
    """
    with st.sidebar:
        st.header("Filters")

        # Get default date (from session state if navigated, else most recent week)
        default_date = st.session_state.get(
            "weekly_selected_date", pd.Timestamp(available_weeks[0]).date()
        )

        # Calendar date picker for week selection
        selected_date = st.date_input(
            "Select a date in the week",
            value=default_date,
            min_value=pd.Timestamp(available_weeks[-1]).date(),
            max_value=pd.Timestamp(available_weeks[0]).date(),
            help="Select any date in the week you want to analyze",
        )

        # Update session state when date picker changes
        st.session_state["weekly_selected_date"] = selected_date

        # Calculate week start from selected date
        selected_date_ts = pd.Timestamp(selected_date)
        days_since_monday = selected_date_ts.weekday()
        week_start_selected = (
            selected_date_ts - pd.Timedelta(days=days_since_monday)
        ).normalize()

        # Find the closest week start in available_weeks
        selected_week = None
        for week in available_weeks:
            if (
                (week - pd.Timedelta(days=1))
                <= week_start_selected
                <= (week + pd.Timedelta(days=7))
            ):
                selected_week = week
                break

        if selected_week is None and available_weeks:
            selected_week = available_weeks[0]

        # Filter by sport
        available_sports = sorted(selected_sports)
        selected_sports = st.multiselect(
            "Sport Types", available_sports, default=available_sports
        )

        st.divider()
        st.subheader("⚙️ Metric View")
        metric_view = st.radio(
            "Data perspective",
            ["Moving", "Raw"],
            horizontal=True,
            help="Moving excludes stopped time. Raw includes all time.",
        )

    return selected_week, metric_view, selected_sports


def render_week_navigation(
    available_weeks: list, selected_week: pd.Timestamp
) -> tuple:
    """
    Render week navigation buttons and display week range.

    Returns:
        Tuple of (week_start_display, week_end_display)
    """
    week_end = selected_week + pd.Timedelta(days=6)

    # Week navigation with prev/next buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

    # Find current week index for navigation
    current_week_idx = (
        available_weeks.index(selected_week) if selected_week in available_weeks else 0
    )
    has_next_week = current_week_idx > 0  # Earlier in list = more recent
    has_prev_week = current_week_idx < len(available_weeks) - 1

    with nav_col1:
        if st.button(
            "◀ Prev",
            disabled=not has_prev_week,
            use_container_width=True,
            help="Go to previous week",
        ):
            # Navigate to older week (higher index)
            new_week = available_weeks[current_week_idx + 1]
            st.session_state["weekly_selected_date"] = new_week.date()
            st.rerun()

    with nav_col2:
        st.subheader(
            f"Week of {selected_week.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}",
            anchor=False,
        )

    with nav_col3:
        if st.button(
            "Next ▶",
            disabled=not has_next_week,
            use_container_width=True,
            help="Go to next week",
        ):
            # Navigate to newer week (lower index)
            new_week = available_weeks[current_week_idx - 1]
            st.session_state["weekly_selected_date"] = new_week.date()
            st.rerun()

    return selected_week, week_end


def render_kpi_section(
    df_week: pd.DataFrame,
    df_prev_week: pd.DataFrame,
    metric_view: str,
    help_texts: dict,
    format_duration_fn,
    get_metric_fn,
) -> None:
    """
    Render KPI metrics section with volume and intensity metrics.

    Args:
        df_week: Current week activities
        df_prev_week: Previous week activities for comparison
        metric_view: "Moving" or "Raw"
        help_texts: Dictionary of help text strings
        format_duration_fn: Function to format duration
        get_metric_fn: Function to safely get metrics
    """
    prefix = "moving_" if metric_view == "Moving" else "raw_"

    # Row 1: Volume Metrics
    total_dist = df_week["distance"].sum() / 1000
    total_time = df_week["moving_time"].sum()
    total_elev = df_week["total_elevation_gain"].sum()
    count = len(df_week)
    total_tss = get_metric_fn(df_week, f"{prefix}training_stress_score")
    total_work = get_metric_fn(df_week, "kilojoules")

    # Deltas from previous week
    prev_dist = df_prev_week["distance"].sum() / 1000 if not df_prev_week.empty else 0
    prev_time = df_prev_week["moving_time"].sum() if not df_prev_week.empty else 0
    prev_tss = (
        get_metric_fn(df_prev_week, f"{prefix}training_stress_score")
        if not df_prev_week.empty
        else 0
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric(
        "Distance",
        f"{total_dist:,.1f} km",
        delta=f"{total_dist - prev_dist:+.1f} km" if prev_dist else None,
    )
    col2.metric(
        "Time",
        format_duration_fn(total_time),
        delta=f"{(total_time - prev_time) / 3600:+.1f}h" if prev_time else None,
    )
    col3.metric("Elevation", f"{total_elev:,.0f} m")
    col4.metric("Activities", f"{count}")
    col5.metric(
        "TSS",
        f"{total_tss:,.0f}",
        delta=f"{total_tss - prev_tss:+.0f}" if prev_tss else None,
        help=help_texts.get("tss", ""),
    )
    col6.metric("Work", f"{total_work:,.0f} kJ")

    # Row 2: Intensity & Efficiency Metrics
    avg_np = get_metric_fn(df_week, f"{prefix}normalized_power", "mean")
    avg_if = get_metric_fn(df_week, f"{prefix}intensity_factor", "mean")
    avg_ef = get_metric_fn(df_week, f"{prefix}efficiency_factor", "mean")
    avg_vi = get_metric_fn(df_week, f"{prefix}variability_index", "mean")
    avg_fatigue = get_metric_fn(df_week, f"{prefix}fatigue_index", "mean")
    avg_hr = get_metric_fn(df_week, f"{prefix}average_hr", "mean")

    t1, t2, t3, t4, t5, t6 = st.columns(6)
    t1.metric("Avg NP", f"{avg_np:.0f} W" if avg_np else "-")
    t2.metric("Avg IF", f"{avg_if:.2f}" if avg_if else "-")
    t3.metric("Avg EF", f"{avg_ef:.2f}" if avg_ef else "-", help=help_texts.get("avg_ef", ""))
    t4.metric("Avg VI", f"{avg_vi:.2f}" if avg_vi else "-")
    t5.metric(
        "Avg Fatigue",
        f"{avg_fatigue:.1f}%" if avg_fatigue else "-",
        help=help_texts.get("fatigue_trend", ""),
    )
    t6.metric("Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-")


def render_overview_tab(
    df_week: pd.DataFrame,
    metric_view: str,
    calculate_weekly_tid_fn,
    format_duration_fn,
    settings,
) -> None:
    """
    Render the Overview tab with daily breakdown and TID analysis.

    Args:
        df_week: Current week activities
        metric_view: "Moving" or "Raw"
        calculate_weekly_tid_fn: Function to calculate TID
        format_duration_fn: Function to format duration
        settings: Settings object with gear names
    """
    prefix = "moving_" if metric_view == "Moving" else "raw_"
    col_daily, col_tid = st.columns([2, 1])

    with col_daily:
        st.subheader("Daily Breakdown")
        if not df_week.empty:
            df_week_daily = df_week.copy()
            df_week_daily["day_name"] = df_week_daily["start_date_local"].dt.day_name()
            days_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]

            # Ensure TSS column exists
            tss_col = f"{prefix}training_stress_score"
            if tss_col not in df_week_daily.columns:
                df_week_daily[tss_col] = 0

            # Group by day with multiple metrics
            daily_stats = (
                df_week_daily.groupby("day_name")
                .agg(
                    {
                        "distance": "sum",
                        "moving_time": "sum",
                        tss_col: "sum",
                        "total_elevation_gain": "sum",
                    }
                )
                .reindex(days_order)
                .fillna(0)
                .reset_index()
            )
            daily_stats["distance_km"] = daily_stats["distance"] / 1000
            daily_stats["time_hours"] = daily_stats["moving_time"] / 3600

            # Dual-axis chart: Distance bars + TSS line
            fig_daily = make_subplots(specs=[[{"secondary_y": True}]])

            fig_daily.add_trace(
                go.Bar(
                    x=daily_stats["day_name"],
                    y=daily_stats["distance_km"],
                    name="Distance (km)",
                    marker_color="#3498db",
                ),
                secondary_y=False,
            )

            fig_daily.add_trace(
                go.Scatter(
                    x=daily_stats["day_name"],
                    y=daily_stats[tss_col],
                    name="TSS",
                    line=dict(color="#e74c3c", width=3),
                    mode="lines+markers",
                ),
                secondary_y=True,
            )

            fig_daily.update_layout(
                title="Daily Volume & Training Load",
                legend=dict(x=0, y=1.1, orientation="h"),
                hovermode="x unified",
            )
            fig_daily.update_yaxes(title_text="Distance (km)", secondary_y=False)
            fig_daily.update_yaxes(title_text="TSS", secondary_y=True)

            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("No activities this week.")

    with col_tid:
        st.subheader("Weekly TID")
        tid = calculate_weekly_tid_fn(df_week, prefix)

        if any(tid.values()):
            fig_tid = px.pie(
                values=[tid["z1"], tid["z2"], tid["z3"]],
                names=["Low (<76% FTP)", "Moderate (76-90%)", "High (>90%)"],
                color_discrete_sequence=["#2ecc71", "#f1c40f", "#e74c3c"],
                hole=0.4,
            )
            fig_tid.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_tid, use_container_width=True)

            # TID metrics
            col_a, col_b = st.columns(2)
            pol_idx = (tid["z1"] + tid["z3"]) / max(tid["z2"], 0.1)
            col_a.metric(
                "Polarization Index",
                f"{pol_idx:.1f}",
                help="(Z1+Z3)/Z2. Higher = more polarized. Target: >4",
            )
            col_b.metric(
                "Z1:Z3 Ratio",
                f"{tid['z1'] / max(tid['z3'], 0.1):.1f}",
                help="Low:High ratio. Target: 2-4 for polarized training",
            )
        else:
            st.info("No TID data available.")

    # Gear & Time-of-Day Analysis
    col_gear, col_time = st.columns(2)

    with col_gear:
        st.subheader("Equipment Usage")
        if "gear_id" in df_week.columns and df_week["gear_id"].notna().any():
            gear_stats = (
                df_week.groupby("gear_id")
                .agg(
                    {
                        "distance": "sum",
                        "moving_time": "sum",
                        "id": "count",
                    }
                )
                .reset_index()
            )
            gear_stats["distance_km"] = gear_stats["distance"] / 1000
            gear_stats.columns = [
                "Gear ID",
                "Distance",
                "Time",
                "Count",
                "Dist (km)",
            ]

            # Map gear names if available
            if settings and hasattr(settings, "gear_names"):
                gear_stats["Gear"] = gear_stats["Gear ID"].map(
                    lambda x: settings.gear_names.get(x, x)
                )
            else:
                gear_stats["Gear"] = gear_stats["Gear ID"]

            fig_gear = px.bar(
                gear_stats,
                x="Gear",
                y="Dist (km)",
                color="Count",
                title="Distance by Equipment",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_gear, use_container_width=True)
        else:
            st.info("No gear data available.")

    with col_time:
        st.subheader("Ride Start Times")
        if not df_week.empty:
            df_week_copy = df_week.copy()
            df_week_copy["hour"] = df_week_copy["start_date_local"].dt.hour
            hour_counts = (
                df_week_copy["hour"].value_counts().sort_index().reset_index()
            )
            hour_counts.columns = ["Hour", "Count"]

            fig_hour = px.bar(
                hour_counts,
                x="Hour",
                y="Count",
                title="Activity Start Time Distribution",
                color="Count",
                color_continuous_scale="Viridis",
            )
            fig_hour.update_xaxes(tickmode="linear", dtick=2)
            st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.info("No activities this week.")


def render_intensity_tab(df_week: pd.DataFrame, metric_view: str) -> None:
    """
    Render the Intensity Distribution tab with power and HR zones.

    Args:
        df_week: Current week activities
        metric_view: "Moving" or "Raw"
    """
    prefix = "moving_" if metric_view == "Moving" else "raw_"
    col_pz, col_hrz = st.columns(2)

    with col_pz:
        st.subheader("Weekly Power Zone Distribution")
        # Aggregate power zones across all activities (time-weighted)
        power_zones = []
        zone_names = [
            "Z1 Recovery",
            "Z2 Endurance",
            "Z3 Tempo",
            "Z4 Threshold",
            "Z5 VO2max",
            "Z6 Anaerobic",
            "Z7 Sprint",
        ]
        total_time = df_week["moving_time"].sum()

        for i in range(1, 8):
            col_name = f"{prefix}power_z{i}_percentage"
            if col_name in df_week.columns and total_time > 0:
                weighted_pct = (
                    df_week[col_name].fillna(0) * df_week["moving_time"]
                ).sum() / total_time
                power_zones.append(weighted_pct)
            else:
                power_zones.append(0)

        if any(power_zones):
            fig_pz = px.bar(
                x=zone_names,
                y=power_zones,
                title="Time in Power Zones (Weekly Aggregate)",
                labels={"x": "Zone", "y": "% of Time"},
                color=power_zones,
                color_continuous_scale="YlOrRd",
            )
            st.plotly_chart(fig_pz, use_container_width=True)
        else:
            st.info("No power zone data available.")

    with col_hrz:
        st.subheader("Weekly HR Zone Distribution")
        hr_zones = []
        hr_zone_names = [
            "Z1 Easy",
            "Z2 Aerobic",
            "Z3 Tempo",
            "Z4 Threshold",
            "Z5 Max",
        ]

        for i in range(1, 6):
            col_name = f"{prefix}hr_z{i}_percentage"
            if col_name in df_week.columns and total_time > 0:
                weighted_pct = (
                    df_week[col_name].fillna(0) * df_week["moving_time"]
                ).sum() / total_time
                hr_zones.append(weighted_pct)
            else:
                hr_zones.append(0)

        if any(hr_zones):
            fig_hrz = px.bar(
                x=hr_zone_names,
                y=hr_zones,
                title="Time in HR Zones (Weekly Aggregate)",
                labels={"x": "Zone", "y": "% of Time"},
                color=hr_zones,
                color_continuous_scale="Reds",
            )
            st.plotly_chart(fig_hrz, use_container_width=True)
        else:
            st.info("No HR zone data available.")

    # Per-Activity Intensity Comparison
    st.subheader("Activity Intensity Comparison")
    if not df_week.empty:
        if_col = f"{prefix}intensity_factor"
        tss_col = f"{prefix}training_stress_score"

        # Ensure columns exist
        if if_col not in df_week.columns:
            df_week[if_col] = None
        if tss_col not in df_week.columns:
            df_week[tss_col] = 0

        df_intensity = df_week[["name", "start_date_local", if_col, tss_col]].copy()
        df_intensity = df_intensity.dropna(subset=[if_col])

        if not df_intensity.empty:
            df_intensity["activity"] = (
                df_intensity["start_date_local"].dt.strftime("%a")
                + ": "
                + df_intensity["name"].str[:20]
            )

            fig_if = px.bar(
                df_intensity,
                x="activity",
                y=if_col,
                color=tss_col,
                title="Intensity Factor by Activity (color = TSS)",
                labels={if_col: "IF", "activity": "Activity"},
                color_continuous_scale="Viridis",
            )
            fig_if.add_hline(y=0.75, line_dash="dot", annotation_text="Endurance")
            fig_if.add_hline(y=0.85, line_dash="dot", annotation_text="Tempo")
            fig_if.add_hline(y=0.95, line_dash="dot", annotation_text="Threshold")
            st.plotly_chart(fig_if, use_container_width=True)
        else:
            st.info("No intensity data for this week.")


def render_trends_tab(
    df_activities: pd.DataFrame,
    selected_week: pd.Timestamp,
    selected_sports: list,
    metric_view: str,
    calculate_weekly_tid_fn,
) -> None:
    """
    Render the Trends tab with 12-week performance analysis.

    Args:
        df_activities: All activities DataFrame
        selected_week: Current week
        selected_sports: Selected sport types
        metric_view: "Moving" or "Raw"
        calculate_weekly_tid_fn: Function to calculate TID
    """
    prefix = "moving_" if metric_view == "Moving" else "raw_"

    st.subheader("12-Week Performance Trends")

    # Get last 12 weeks of data
    start_trend = selected_week - pd.Timedelta(weeks=11)
    df_trend = df_activities[
        (df_activities["week_start"] >= start_trend)
        & (df_activities["week_start"] <= selected_week)
        & (df_activities["sport_type"].isin(selected_sports))
    ].copy()

    if not df_trend.empty:
        # Ensure columns exist
        for col in [
            f"{prefix}training_stress_score",
            f"{prefix}efficiency_factor",
            f"{prefix}intensity_factor",
            f"{prefix}fatigue_index",
        ]:
            if col not in df_trend.columns:
                df_trend[col] = 0

        # Aggregate weekly metrics
        weekly_trend = (
            df_trend.groupby("week_start")
            .agg(
                {
                    "distance": "sum",
                    f"{prefix}training_stress_score": "sum",
                    f"{prefix}efficiency_factor": "mean",
                    f"{prefix}intensity_factor": "mean",
                    f"{prefix}fatigue_index": "mean",
                    "moving_time": "sum",
                }
            )
            .reset_index()
        )
        weekly_trend["distance_km"] = weekly_trend["distance"] / 1000
        weekly_trend["hours"] = weekly_trend["moving_time"] / 3600

        col_vol, col_eff = st.columns(2)

        with col_vol:
            # Volume Trend: Distance + TSS
            fig_vol = make_subplots(specs=[[{"secondary_y": True}]])

            fig_vol.add_trace(
                go.Bar(
                    x=weekly_trend["week_start"],
                    y=weekly_trend["distance_km"],
                    name="Distance (km)",
                    marker_color="#3498db",
                ),
                secondary_y=False,
            )

            fig_vol.add_trace(
                go.Scatter(
                    x=weekly_trend["week_start"],
                    y=weekly_trend[f"{prefix}training_stress_score"],
                    name="TSS",
                    line=dict(color="#e74c3c", width=3),
                    mode="lines+markers",
                ),
                secondary_y=True,
            )

            fig_vol.update_layout(
                title="Volume & Load Trend",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
            )
            fig_vol.update_yaxes(title_text="Distance (km)", secondary_y=False)
            fig_vol.update_yaxes(title_text="TSS", secondary_y=True)
            st.plotly_chart(fig_vol, use_container_width=True)

        with col_eff:
            # Efficiency Trend: EF + IF
            fig_eff = make_subplots(specs=[[{"secondary_y": True}]])

            fig_eff.add_trace(
                go.Scatter(
                    x=weekly_trend["week_start"],
                    y=weekly_trend[f"{prefix}efficiency_factor"],
                    name="Efficiency Factor",
                    line=dict(color="#2ecc71", width=3),
                    mode="lines+markers",
                ),
                secondary_y=False,
            )

            fig_eff.add_trace(
                go.Scatter(
                    x=weekly_trend["week_start"],
                    y=weekly_trend[f"{prefix}intensity_factor"],
                    name="Avg IF",
                    line=dict(color="#9b59b6", width=2, dash="dot"),
                    mode="lines+markers",
                ),
                secondary_y=True,
            )

            fig_eff.update_layout(
                title="Efficiency & Intensity Trend",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
            )
            fig_eff.update_yaxes(title_text="EF (NP/HR)", secondary_y=False)
            fig_eff.update_yaxes(title_text="IF (NP/FTP)", secondary_y=True)
            st.plotly_chart(fig_eff, use_container_width=True)

        # Weekly TID Trend
        st.subheader("Weekly Training Intensity Distribution Trend")
        weekly_tid = []
        for week in weekly_trend["week_start"]:
            week_data = df_trend[df_trend["week_start"] == week]
            tid = calculate_weekly_tid_fn(week_data, prefix)
            weekly_tid.append(
                {
                    "week": week,
                    "Z1 Low": tid["z1"],
                    "Z2 Moderate": tid["z2"],
                    "Z3 High": tid["z3"],
                }
            )

        df_tid_trend = pd.DataFrame(weekly_tid)

        if not df_tid_trend.empty:
            fig_tid_trend = go.Figure()
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["week"],
                    y=df_tid_trend["Z1 Low"],
                    name="Z1 Low",
                    marker_color="#2ecc71",
                )
            )
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["week"],
                    y=df_tid_trend["Z2 Moderate"],
                    name="Z2 Moderate",
                    marker_color="#f1c40f",
                )
            )
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["week"],
                    y=df_tid_trend["Z3 High"],
                    name="Z3 High",
                    marker_color="#e74c3c",
                )
            )
            fig_tid_trend.update_layout(
                barmode="stack",
                title="Weekly Training Intensity Distribution",
                yaxis_title="% of Time",
                legend=dict(x=0, y=1.1, orientation="h"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_tid_trend, use_container_width=True)
    else:
        st.info("No trend data available.")


def render_activities_tab(
    df_week: pd.DataFrame,
    metric_view: str,
    format_duration_fn,
    settings,
) -> None:
    """
    Render the Activities tab with dataframe of weekly activities.

    Args:
        df_week: Current week activities
        metric_view: "Moving" or "Raw"
        format_duration_fn: Function to format duration
        settings: Settings object with gear names
    """
    prefix = "moving_" if metric_view == "Moving" else "raw_"

    st.subheader("Activities This Week")
    if not df_week.empty:
        # Prepare DataFrame for display
        cols_map = {
            "start_date_local": "Date",
            "name": "Name",
            "sport_type": "Sport",
            "distance": "Distance",
            "moving_time": "Time",
            "total_elevation_gain": "Elevation",
            f"{prefix}normalized_power": "NP",
            f"{prefix}intensity_factor": "IF",
            f"{prefix}efficiency_factor": "EF",
            f"{prefix}training_stress_score": "TSS",
            "gear_id": "Gear",
            "id": "id",
        }

        # Ensure columns exist
        for col in cols_map.keys():
            if col not in df_week.columns:
                df_week[col] = None

        df_display = df_week[list(cols_map.keys())].rename(columns=cols_map).copy()
        df_display = df_display.sort_values("Date", ascending=False).reset_index(
            drop=True
        )

        # Conversions
        df_display["Distance"] = df_display["Distance"] / 1000
        df_display["Time"] = df_display["Time"].apply(format_duration_fn)

        # Map gear names
        if settings and hasattr(settings, "gear_names"):
            df_display["Gear"] = df_display["Gear"].map(
                lambda x: settings.gear_names.get(x, x) if pd.notna(x) else "-"
            )

        column_config = {
            "Date": st.column_config.DatetimeColumn(
                "Date", format="ddd D MMM, HH:mm", width="medium"
            ),
            "Name": st.column_config.TextColumn("Name", width="large"),
            "Sport": st.column_config.TextColumn("Sport", width="small"),
            "Distance": st.column_config.NumberColumn("Dist (km)", format="%.1f"),
            "Time": st.column_config.TextColumn("Time"),
            "Elevation": st.column_config.NumberColumn("Elev (m)", format="%d"),
            "NP": st.column_config.NumberColumn("NP (W)", format="%d"),
            "IF": st.column_config.NumberColumn("IF", format="%.2f"),
            "EF": st.column_config.NumberColumn("EF", format="%.2f"),
            "TSS": st.column_config.NumberColumn("TSS", format="%d"),
            "Gear": st.column_config.TextColumn("Gear", width="medium"),
            "id": None,
        }

        st.info("💡 Select a row to view activity details.")

        event = st.dataframe(
            df_display,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        if event.selection.rows:
            selected_index = event.selection.rows[0]
            selected_row = df_display.iloc[selected_index]
            activity_id = int(selected_row["id"])
            st.session_state["selected_activity_id"] = activity_id
            st.switch_page("pages/3_activity_detail.py")
    else:
        st.info("No activities found for this week.")
