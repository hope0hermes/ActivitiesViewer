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
from activities_viewer.pages.components.activity_detail_components import render_metric

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
            ["Moving Time", "Raw Time"],
            horizontal=True,
            help="Moving Time excludes stopped time. Raw Time includes all time.",
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
    # Row 1: Volume Metrics
    total_dist = df_week["distance"].sum() / 1000
    total_time = df_week["moving_time"].sum()
    total_elev = df_week["total_elevation_gain"].sum()
    count = len(df_week)
    total_tss = get_metric_fn(df_week, "training_stress_score")
    total_work = get_metric_fn(df_week, "kilojoules")

    # Deltas from previous week
    prev_dist = df_prev_week["distance"].sum() / 1000 if not df_prev_week.empty else 0
    prev_time = df_prev_week["moving_time"].sum() if not df_prev_week.empty else 0
    prev_tss = (
        get_metric_fn(df_prev_week, "training_stress_score")
        if not df_prev_week.empty
        else 0
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    render_metric(col1, "Distance", f"{total_dist:,.1f} km", f"{total_dist - prev_dist:+.1f} km" if prev_dist else None)
    render_metric(col2, "Time", format_duration_fn(total_time), f"{(total_time - prev_time) / 3600:+.1f}h" if prev_time else None)
    render_metric(col3, "Elevation", f"{total_elev:,.0f} m")
    render_metric(col4, "Activities", f"{count}")
    render_metric(col5, "TSS", f"{total_tss:,.0f}", f"{total_tss - prev_tss:+.0f}" if prev_tss else None)
    render_metric(col6, "Work", f"{total_work:,.0f} kJ")

    # Row 2: Intensity & Efficiency Metrics
    avg_np = get_metric_fn(df_week, "normalized_power", "mean")
    avg_if = get_metric_fn(df_week, "intensity_factor", "mean")
    avg_ef = get_metric_fn(df_week, "efficiency_factor", "mean")
    avg_vi = get_metric_fn(df_week, "variability_index", "mean")
    avg_fatigue = get_metric_fn(df_week, "fatigue_index", "mean")
    avg_hr = get_metric_fn(df_week, "average_hr", "mean")

    t1, t2, t3, t4, t5, t6 = st.columns(6)
    render_metric(t1, "Avg NP", f"{avg_np:.0f} W" if avg_np else "-")
    render_metric(t2, "Avg IF", f"{avg_if:.2f}" if avg_if else "-")
    render_metric(t3, "Avg EF", f"{avg_ef:.2f}" if avg_ef else "-", help_texts.get("avg_ef", ""))
    render_metric(t4, "Avg VI", f"{avg_vi:.2f}" if avg_vi else "-")
    render_metric(t5, "Avg Fatigue", f"{avg_fatigue:.1f}%" if avg_fatigue else "-", help_texts.get("fatigue_trend", ""))
    render_metric(t6, "Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "-")

    # Row 3: Training Load State (from end of week)
    st.divider()
    st.markdown("#### 📊 Training Load State (End of Week)")

    if not df_week.empty:
        # Get latest activity metrics for training load
        latest_activity = df_week.sort_values("start_date", ascending=False).iloc[0]

        # Training Load Metrics (from latest activity)
        ctl = latest_activity.get("chronic_training_load", None)
        atl = latest_activity.get("acute_training_load", None)
        tsb = latest_activity.get("training_stress_balance", None)
        acwr = latest_activity.get("acwr", None)

        # Display metrics in 4 columns using render_metric
        col1, col2, col3, col4 = st.columns(4)

        # CTL (Chronic Training Load)
        ctl_value = f"{ctl:.0f}" if pd.notna(ctl) else "-"
        ctl_help = "42-day fitness level. Optimal: 80-120\nStatus: " + (
            "Building - Early in training block" if pd.notna(ctl) and ctl < 50 else
            "Consistent - Normal training load" if pd.notna(ctl) and ctl < 100 else
            "High - Peak training phase" if pd.notna(ctl) and ctl < 150 else
            "Elite - Competition ready"
        )
        render_metric(col1, "📊 CTL (Fitness)", ctl_value, ctl_help)

        # ATL (Acute Training Load)
        atl_value = f"{atl:.0f}" if pd.notna(atl) else "-"
        atl_help = "7-day fatigue level. Optimal: 30-70\nStatus: " + (
            "Fresh - Low recent fatigue" if pd.notna(atl) and atl < 50 else
            "Normal - Healthy training week" if pd.notna(atl) and atl < 100 else
            "High - Accumulating fatigue"
        )
        render_metric(col2, "⚡ ATL (Fatigue)", atl_value, atl_help)

        # TSB (Training Stress Balance)
        tsb_value = f"{tsb:.0f}" if pd.notna(tsb) else "-"
        tsb_help = "Form/freshness (CTL - ATL). Optimal: -10 to +20\nStatus: " + (
            "Exhausted - Avoid racing!" if pd.notna(tsb) and tsb < -50 else
            "Fatigued - Recovery needed" if pd.notna(tsb) and tsb < -10 else
            "Optimal - Ready for performance" if pd.notna(tsb) and tsb <= 20 else
            "Very fresh - Consider intensity"
        )
        render_metric(col3, "🎯 TSB (Form)", tsb_value, tsb_help)

        # ACWR (Acute:Chronic Workload Ratio)
        acwr_value = f"{acwr:.2f}" if pd.notna(acwr) else "-"
        acwr_help = "Injury risk indicator (ATL ÷ CTL). Optimal: 0.8-1.3\nStatus: " + (
            "Undertraining - Low injury risk" if pd.notna(acwr) and acwr < 0.8 else
            "Safe - Optimal training load" if pd.notna(acwr) and acwr <= 1.3 else
            "Caution - Moderate injury risk" if pd.notna(acwr) and acwr <= 1.5 else
            "High Risk - Reduce load!"
        )
        render_metric(col4, "⚠️ ACWR (Risk)", acwr_value, acwr_help)

        # Training State Summary
        if pd.notna(tsb):
            if tsb > 20:
                state = "✅ Well-rested - Good for intensity work"
                state_color = "green"
            elif 0 <= tsb <= 20:
                state = "🎯 Optimal zone - Productive training"
                state_color = "blue"
            elif -10 <= tsb < 0:
                state = "⚠️ Elevated fatigue - Productive but stressed"
                state_color = "orange"
            else:  # tsb < -10
                state = "🔴 Overreached - Recovery needed"
                state_color = "red"

            st.markdown(f"**Training State:** <span style='color:{state_color}'>{state}</span>", unsafe_allow_html=True)

        # Row 4: CP Model & Durability metrics
        st.divider()
        st.markdown("#### 💪 Power Profile & Durability")

        # CP model metrics (from latest activity)
        cp = latest_activity.get("cp", None)
        w_prime = latest_activity.get("w_prime", None)
        r_squared = latest_activity.get("cp_r_squared", None)
        aei = latest_activity.get("aei", None)

        # Display metrics in 4 columns using render_metric
        if any(pd.notna(x) for x in [cp, w_prime, r_squared, aei]):
            col1, col2, col3, col4 = st.columns(4)

            # CP (Critical Power)
            cp_value = f"{cp:.0f}W" if pd.notna(cp) else "-"
            cp_help = "Maximum sustained power for efforts >3 min. Category: " + (
                "Developing - Early stage training" if pd.notna(cp) and cp < 200 else
                "Fit - Solid cyclist" if pd.notna(cp) and cp < 300 else
                "Very Fit - Competitive fitness" if pd.notna(cp) and cp < 400 else
                "Elite - Professional level"
            )
            render_metric(col1, "⚡ CP (Power)", cp_value, cp_help)

            # W' (Anaerobic Capacity)
            w_prime_value = f"{w_prime/1000:.1f}kJ" if pd.notna(w_prime) else "-"
            w_prime_kj = w_prime / 1000 if pd.notna(w_prime) else None
            w_prime_help = "Anaerobic work capacity above CP. Capacity: " + (
                "Low - Build through intervals" if pd.notna(w_prime_kj) and w_prime_kj < 15 else
                "Average - Typical endurance cyclist" if pd.notna(w_prime_kj) and w_prime_kj < 25 else
                "High - Strong sprint ability"
            )
            render_metric(col2, "💥 W' (Anaerobic)", w_prime_value, w_prime_help)

            # R² (Model Fit)
            r2_value = f"{r_squared:.3f}" if pd.notna(r_squared) else "-"
            r2_help = "CP model goodness of fit (0-1). Quality: " + (
                "Fair - Use with caution" if pd.notna(r_squared) and r_squared <= 0.90 else
                "Good - Reliable estimates" if pd.notna(r_squared) and r_squared <= 0.95 else
                "Excellent - Very reliable"
            )
            render_metric(col3, "📊 R² (Fit)", r2_value, r2_help)

            # AEI (Aerobic Efficiency)
            aei_value = f"{aei:.2f}" if pd.notna(aei) else "-"
            aei_help = "Power per heartbeat. Profile: " + (
                "Very Aerobic - Endurance focused" if pd.notna(aei) and aei > 0.85 else
                "Aerobic - Balanced athlete" if pd.notna(aei) and aei > 0.70 else
                "Balanced - Mixed strengths"
            )
            render_metric(col4, "❤️ AEI (Efficiency)", aei_value, aei_help)
        else:
            st.info("No power profile data available for this week")


def render_overview_tab(
    df_week: pd.DataFrame,
    selected_week: pd.Timestamp,
    metric_view: str,
    calculate_weekly_tid_fn,
    format_duration_fn,
    settings,
) -> None:
    """
    Render the Overview tab with daily breakdown and TID analysis.

    Args:
        df_week: Current week activities
        selected_week: Start of the week (Monday)
        metric_view: "Moving" or "Raw"
        calculate_weekly_tid_fn: Function to calculate TID
        format_duration_fn: Function to format duration
        settings: Settings object with gear names
    """
    col_daily, col_tid = st.columns([2, 1])

    with col_daily:
        st.subheader("Daily Breakdown")
        if not df_week.empty:
            df_week_daily = df_week.copy()
            # Create a proper date column for grouping
            df_week_daily["date_local"] = df_week_daily["start_date_local"].dt.date
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
            tss_col = "training_stress_score"
            if tss_col not in df_week_daily.columns:
                df_week_daily[tss_col] = 0

            # Group by date (not day name) to capture all activities even if multiple on same day
            daily_stats = (
                df_week_daily.groupby(["date_local", "day_name"])
                .agg(
                    {
                        "distance": "sum",
                        "moving_time": "sum",
                        tss_col: "sum",
                        "total_elevation_gain": "sum",
                    }
                )
                .reset_index()
            )
            daily_stats["distance_km"] = daily_stats["distance"] / 1000
            daily_stats["time_hours"] = daily_stats["moving_time"] / 3600

            # Sort by date
            daily_stats = daily_stats.sort_values("date_local")

            # Create a complete week from Monday to Sunday using selected_week (which is always Monday)
            week_start = selected_week.normalize().date() if isinstance(selected_week, pd.Timestamp) else selected_week
            week_dates = pd.date_range(start=week_start, periods=7, freq='D').date
            day_names_full = pd.date_range(start=week_start, periods=7, freq='D').day_name()

            # Reindex to include all days of the week
            daily_display = []
            for date, day_name in zip(week_dates, day_names_full):
                day_data = daily_stats[daily_stats["date_local"] == date]
                if not day_data.empty:
                    daily_display.append({
                        "date_local": date,
                        "day_name": day_name,
                        "distance_km": day_data["distance_km"].sum(),
                        "time_hours": day_data["time_hours"].sum(),
                        "tss": day_data[tss_col].sum(),
                        "elevation_gain": day_data["total_elevation_gain"].sum(),
                    })
                else:
                    daily_display.append({
                        "date_local": date,
                        "day_name": day_name,
                        "distance_km": 0,
                        "time_hours": 0,
                        "tss": 0,
                        "elevation_gain": 0,
                    })

            daily_stats_full = pd.DataFrame(daily_display)

            # Create ordered day abbreviations (Mon-Sun)
            day_abbreviations = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            # Dual-axis chart: Distance bars + TSS line
            fig_daily = make_subplots(specs=[[{"secondary_y": True}]])

            fig_daily.add_trace(
                go.Bar(
                    x=day_abbreviations,
                    y=daily_stats_full["distance_km"],
                    name="Distance (km)",
                    marker_color="#3498db",
                ),
                secondary_y=False,
            )

            fig_daily.add_trace(
                go.Scatter(
                    x=day_abbreviations,
                    y=daily_stats_full["tss"],
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

    with col_tid:
        st.subheader("Weekly TID")
        tid = calculate_weekly_tid_fn(df_week, metric_view)

        if any(tid.values()):
            # Horizontal bar chart for TID
            fig_tid = go.Figure()

            fig_tid.add_trace(go.Bar(
                y=["Low\n(<76% FTP)", "Moderate\n(76-90%)", "High\n(>90%)"],
                x=[tid["z1"], tid["z2"], tid["z3"]],
                orientation='h',
                marker=dict(color=["#2ecc71", "#f1c40f", "#e74c3c"]),
                text=[f"{tid['z1']:.1f}%", f"{tid['z2']:.1f}%", f"{tid['z3']:.1f}%"],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>%{x:.1f}%<extra></extra>'
            ))

            fig_tid.update_layout(
                xaxis_title="% of Time",
                yaxis_title="Zone",
                height=250,
                margin=dict(l=100, r=20, t=20, b=20),
                showlegend=False,
                hovermode='y unified',
            )
            fig_tid.update_xaxes(range=[0, 100])

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


def render_intensity_tab(df_week: pd.DataFrame, selected_week: pd.Timestamp, metric_view: str) -> None:
    """
    Render the Intensity Distribution tab with power and HR zones.

    Args:
        df_week: Current week activities
        selected_week: Start of the week (Monday)
        metric_view: "Moving" or "Raw"
    """
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
        # Power zone ranges as % of FTP
        power_zone_ranges = [
            "0-55% FTP",
            "55-75% FTP",
            "75-90% FTP",
            "90-105% FTP",
            "105-120% FTP",
            "120-150% FTP",
            ">150% FTP",
        ]
        total_time = df_week["moving_time"].sum()

        for i in range(1, 8):
            col_name = f"power_z{i}_percentage"
            if col_name in df_week.columns and total_time > 0:
                weighted_pct = (
                    df_week[col_name].fillna(0) * df_week["moving_time"]
                ).sum() / total_time
                power_zones.append(weighted_pct)
            else:
                power_zones.append(0)

        if any(power_zones):
            # Create hover text with zone details
            hover_text = [
                f"<b>{zone_names[i]}</b><br>{power_zones[i]:.1f}% of time<br>{power_zone_ranges[i]}"
                for i in range(7)
            ]
            fig_pz = go.Figure()
            fig_pz.add_trace(
                go.Bar(
                    y=zone_names,
                    x=power_zones,
                    orientation="h",
                    marker_color=["#808080", "#3498db", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"],
                    text=[f"{pct:.0f}%" for pct in power_zones],
                    textposition="outside",
                    customdata=hover_text,
                    hovertemplate="%{customdata}<extra></extra>",
                )
            )
            fig_pz.update_layout(
                xaxis_title="% of Time",
                height=250,
                margin={"l": 100, "r": 60, "t": 20, "b": 20},
                showlegend=False,
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
        # HR zone ranges as % of LTHR
        hr_zone_ranges = [
            "<85% LTHR",
            "85-94% LTHR",
            "94-104% LTHR",
            "104-120% LTHR",
            ">120% LTHR",
        ]

        for i in range(1, 6):
            col_name = f"hr_z{i}_percentage"
            if col_name in df_week.columns and total_time > 0:
                weighted_pct = (
                    df_week[col_name].fillna(0) * df_week["moving_time"]
                ).sum() / total_time
                hr_zones.append(weighted_pct)
            else:
                hr_zones.append(0)

        if any(hr_zones):
            # Create hover text with zone details
            hover_text = [
                f"<b>{hr_zone_names[i]}</b><br>{hr_zones[i]:.1f}% of time<br>{hr_zone_ranges[i]}"
                for i in range(5)
            ]
            fig_hrz = go.Figure()
            fig_hrz.add_trace(
                go.Bar(
                    y=hr_zone_names,
                    x=hr_zones,
                    orientation="h",
                    marker_color=["#808080", "#3498db", "#2ecc71", "#e67e22", "#e74c3c"],
                    text=[f"{pct:.0f}%" for pct in hr_zones],
                    textposition="outside",
                    customdata=hover_text,
                    hovertemplate="%{customdata}<extra></extra>",
                )
            )
            fig_hrz.update_layout(
                xaxis_title="% of Time",
                height=200,
                margin={"l": 100, "r": 60, "t": 20, "b": 20},
                showlegend=False,
            )
            st.plotly_chart(fig_hrz, use_container_width=True)
        else:
            st.info("No HR zone data available.")

    # Per-Activity Intensity Comparison
    st.subheader("Daily Activity Intensity")
    if not df_week.empty:
        if_col = "intensity_factor"
        tss_col = "training_stress_score"

        # Ensure columns exist
        if if_col not in df_week.columns:
            df_week[if_col] = None
        if tss_col not in df_week.columns:
            df_week[tss_col] = 0

        # Create a full week dataframe with all 7 days (Mon-Sun)
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Create date range for the week
        week_dates = pd.date_range(start=selected_week, periods=7, freq="D")

        # Initialize full week data
        week_data = {
            "date": week_dates,
            "day_label": day_labels,
            "if": [None] * 7,
            "tss": [0] * 7,
            "activity_name": ["No activity"] * 7,
            "color_idx": list(range(7)),  # 0-6 for color mapping
        }

        # Power zone colors for each day (matching zone distribution)
        day_colors = ["#808080", "#3498db", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"]

        # Populate with actual activities
        df_intensity_temp = df_week[["name", "start_date_local", if_col, tss_col]].copy()

        for idx, (date, row) in enumerate(df_intensity_temp.iterrows()):
            date_local = row["start_date_local"]
            day_idx = (date_local - selected_week).days

            if 0 <= day_idx < 7:
                if pd.notna(row[if_col]):
                    week_data["if"][day_idx] = row[if_col]
                    week_data["tss"][day_idx] = row[tss_col]
                    week_data["activity_name"][day_idx] = row["name"][:25] if pd.notna(row["name"]) else "Activity"

        # Create dataframe for plotting
        df_plot = pd.DataFrame(week_data)

        # Create horizontal bar chart showing all days
        fig_daily = go.Figure()

        for idx, row in df_plot.iterrows():
            if row["if"] is not None:
                hover_text = f"<b>{row['day_label']}: {row['activity_name']}</b><br>IF: {row['if']:.2f}<br>TSS: {row['tss']:.0f}"
                fig_daily.add_trace(
                    go.Bar(
                        y=[row["day_label"]],
                        x=[row["if"]],
                        orientation="h",
                        marker_color=day_colors[idx],
                        text=f"{row['if']:.2f}",
                        textposition="outside",
                        hovertemplate=hover_text + "<extra></extra>",
                        showlegend=False,
                    )
                )
            else:
                # Show empty bar for days without activity
                fig_daily.add_trace(
                    go.Bar(
                        y=[row["day_label"]],
                        x=[0],
                        orientation="h",
                        marker_color="rgba(200, 200, 200, 0.3)",
                        text="—",
                        textposition="outside",
                        hovertemplate=f"<b>{row['day_label']}</b><br>No activity<extra></extra>",
                        showlegend=False,
                    )
                )

        fig_daily.update_layout(
            xaxis_title="Intensity Factor",
            height=250,
            margin={"l": 60, "r": 60, "t": 20, "b": 20},
            showlegend=False,
            xaxis_range=[0, 1.2],
        )
        fig_daily.add_vline(x=0.75, line_dash="dot", annotation_text="Endurance")
        fig_daily.add_vline(x=0.85, line_dash="dot", annotation_text="Tempo")
        fig_daily.add_vline(x=0.95, line_dash="dot", annotation_text="Threshold")
        st.plotly_chart(fig_daily, use_container_width=True)


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
            "training_stress_score",
            "efficiency_factor",
            "intensity_factor",
            "fatigue_index",
        ]:
            if col not in df_trend.columns:
                df_trend[col] = 0

        # Aggregate weekly metrics
        weekly_trend = (
            df_trend.groupby("week_start")
            .agg(
                {
                    "distance": "sum",
                    "training_stress_score": "sum",
                    "efficiency_factor": "mean",
                    "intensity_factor": "mean",
                    "fatigue_index": "mean",
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
                    y=weekly_trend["training_stress_score"],
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
                    y=weekly_trend["efficiency_factor"],
                    name="Efficiency Factor",
                    line=dict(color="#2ecc71", width=3),
                    mode="lines+markers",
                ),
                secondary_y=False,
            )

            fig_eff.add_trace(
                go.Scatter(
                    x=weekly_trend["week_start"],
                    y=weekly_trend["intensity_factor"],
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
            tid = calculate_weekly_tid_fn(week_data, metric_view)
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
            "normalized_power": "NP",
            "intensity_factor": "IF",
            "efficiency_factor": "EF",
            "training_stress_score": "TSS",
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
