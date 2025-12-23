"""
Monthly Analysis Page Components.

Extracted rendering functions for the monthly analysis page tabs.
Each function handles a specific UI section to keep main() clean.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from activities_viewer.pages.components.activity_detail_components import render_metric

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT: Month Selector & Navigation
# ═══════════════════════════════════════════════════════════════════════════════


def render_month_selector(available_months: list, selected_sports: list) -> tuple:
    """
    Render month selector sidebar and return selected month and metric view.

    Args:
        available_months: Sorted list of month start dates
        selected_sports: List of selected sport types for filtering

    Returns:
        Tuple of (selected_month, metric_view, selected_sports)
    """
    with st.sidebar:
        st.header("Filters")

        # Get default date (from session state if navigated, else most recent month)
        default_date = st.session_state.get(
            "monthly_selected_date", pd.Timestamp(available_months[0]).date()
        )

        # Calendar date picker for month selection
        selected_date = st.date_input(
            "Select a date in the month",
            value=default_date,
            min_value=pd.Timestamp(available_months[-1]).date(),
            max_value=pd.Timestamp(available_months[0]).date(),
            help="Select any date in the month you want to analyze",
        )

        # Update session state when date picker changes
        st.session_state["monthly_selected_date"] = selected_date

        # Calculate month start from selected date
        selected_date_ts = pd.Timestamp(selected_date)
        month_start_selected = selected_date_ts.replace(day=1).normalize()

        # Find the closest month start in available_months
        selected_month = None
        for month in available_months:
            if month.year == month_start_selected.year and month.month == month_start_selected.month:
                selected_month = month
                break

        if selected_month is None and available_months:
            selected_month = available_months[0]

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

    return selected_month, metric_view, selected_sports


def render_month_navigation(
    available_months: list, selected_month: pd.Timestamp
) -> tuple:
    """
    Render month navigation buttons and display month range.

    Returns:
        Tuple of (month_start_display, month_end_display)
    """
    # Calculate month end
    if selected_month.month == 12:
        month_end = pd.Timestamp(year=selected_month.year + 1, month=1, day=1) - pd.Timedelta(days=1)
    else:
        month_end = pd.Timestamp(year=selected_month.year, month=selected_month.month + 1, day=1) - pd.Timedelta(days=1)

    # Month navigation with prev/next buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

    # Find current month index for navigation
    current_month_idx = (
        available_months.index(selected_month) if selected_month in available_months else 0
    )
    has_next_month = current_month_idx > 0  # Earlier in list = more recent
    has_prev_month = current_month_idx < len(available_months) - 1

    with nav_col1:
        if st.button(
            "◀ Prev",
            disabled=not has_prev_month,
            use_container_width=True,
            help="Go to previous month",
            key="monthly_prev",
        ):
            # Navigate to older month (higher index)
            new_month = available_months[current_month_idx + 1]
            st.session_state["monthly_selected_date"] = new_month.date()
            st.rerun()

    with nav_col2:
        st.subheader(
            f"{selected_month.strftime('%B %Y')}",
            anchor=False,
        )

    with nav_col3:
        if st.button(
            "Next ▶",
            disabled=not has_next_month,
            use_container_width=True,
            help="Go to next month",
            key="monthly_next",
        ):
            # Navigate to newer month (lower index)
            new_month = available_months[current_month_idx - 1]
            st.session_state["monthly_selected_date"] = new_month.date()
            st.rerun()

    return selected_month, month_end


def render_kpi_section(
    df_month: pd.DataFrame,
    df_prev_month: pd.DataFrame,
    metric_view: str,
    help_texts: dict,
    format_duration_fn,
    get_metric_fn,
) -> None:
    """
    Render KPI metrics section with hero and context metrics.

    Args:
        df_month: Current month activities
        df_prev_month: Previous month activities for comparison
        metric_view: "Moving" or "Raw"
        help_texts: Dictionary of help text strings
        format_duration_fn: Function to format duration
        get_metric_fn: Function to safely get metrics
    """
    # Calculate metrics
    total_dist = df_month["distance"].sum() / 1000
    total_time = df_month["moving_time"].sum()
    total_elev = df_month["total_elevation_gain"].sum()
    count = len(df_month)
    total_tss = get_metric_fn(df_month, "training_stress_score")
    total_work = get_metric_fn(df_month, "kilojoules")

    # Deltas from previous month
    prev_dist = df_prev_month["distance"].sum() / 1000 if not df_prev_month.empty else 0
    prev_time = df_prev_month["moving_time"].sum() if not df_prev_month.empty else 0
    prev_tss = (
        get_metric_fn(df_prev_month, "training_stress_score")
        if not df_prev_month.empty
        else 0
    )

    # Get training load state from latest activity
    ctl = atl = tsb = acwr = None
    if not df_month.empty:
        latest_activity = df_month.sort_values("start_date", ascending=False).iloc[0]
        ctl = latest_activity.get("chronic_training_load", None)
        atl = latest_activity.get("acute_training_load", None)
        tsb = latest_activity.get("training_stress_balance", None)
        acwr = latest_activity.get("acwr", None)

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 1: HERO METRICS (3 columns, large, most important)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 📊 Month at a Glance")

    hero1, hero2, hero3 = st.columns(3)

    with hero1:
        tss_delta = f"{total_tss - prev_tss:+.0f}" if prev_tss else None
        st.metric(
            "💪 Training Load",
            f"{total_tss:.0f} TSS",
            delta=tss_delta,
            help="Total Training Stress Score this month. Typical range: 1200-3000 TSS/month."
        )

    with hero2:
        if pd.notna(tsb):
            if tsb > 20:
                status_emoji, status = "🔋", "Fresh"
            elif 0 <= tsb <= 20:
                status_emoji, status = "🎯", "Ready"
            elif -10 <= tsb < 0:
                status_emoji, status = "⚠️", "Fatigued"
            else:
                status_emoji, status = "🔴", "Tired"
            tsb_value = f"{tsb:.0f}"
        else:
            status_emoji, status = "❓", "Unknown"
            tsb_value = "-"

        st.metric(
            f"{status_emoji} Form (TSB)",
            tsb_value,
            delta=status,
            delta_color="off",
            help="Training Stress Balance = CTL - ATL. Indicates freshness."
        )

    with hero3:
        time_delta = f"{(total_time - prev_time) / 3600:+.1f}h" if prev_time else None
        hours = int(total_time // 3600)
        mins = int((total_time % 3600) // 60)
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        st.metric(
            "⏱️ Training Time",
            time_str,
            delta=time_delta,
            help="Total moving time this month."
        )

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 2: CONTEXT METRICS (volume and secondary metrics)
    # ═══════════════════════════════════════════════════════════════════════════
    st.caption("📊 Volume & Training Load Details")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    render_metric(col1, "🚴 Distance", f"{total_dist:.1f} km", f"{total_dist - prev_dist:+.1f}" if prev_dist else None)
    render_metric(col2, "⛰️ Elevation", f"{total_elev:,.0f} m")
    render_metric(col3, "📝 Activities", f"{count}")
    render_metric(col4, "⚡ Work", f"{total_work:,.0f} kJ")

    # CTL and ATL
    ctl_value = f"{ctl:.0f}" if pd.notna(ctl) else "-"
    atl_value = f"{atl:.0f}" if pd.notna(atl) else "-"
    render_metric(col5, "📊 CTL (Fitness)", ctl_value, help_texts.get("chronic_training_load", ""))
    render_metric(col6, "⚡ ATL (Fatigue)", atl_value, help_texts.get("acute_training_load", ""))

    # Intensity row
    avg_np = get_metric_fn(df_month, "normalized_power", "mean")
    avg_if = get_metric_fn(df_month, "intensity_factor", "mean")
    avg_ef = get_metric_fn(df_month, "efficiency_factor", "mean")
    avg_vi = get_metric_fn(df_month, "variability_index", "mean")
    avg_fatigue = get_metric_fn(df_month, "fatigue_index", "mean")
    avg_hr = get_metric_fn(df_month, "average_hr", "mean")

    st.caption("⚡ Intensity & Efficiency")
    t1, t2, t3, t4, t5, t6 = st.columns(6)
    render_metric(t1, "Avg NP", f"{avg_np:.0f} W" if avg_np else "-", help_texts.get("normalized_power", ""))
    render_metric(t2, "Avg IF", f"{avg_if:.2f}" if avg_if else "-", help_texts.get("intensity_factor", ""))
    render_metric(t3, "Avg EF", f"{avg_ef:.2f}" if avg_ef else "-", help_texts.get("efficiency_factor", ""))
    render_metric(t4, "Avg VI", f"{avg_vi:.2f}" if avg_vi else "-", help_texts.get("variability_index", ""))
    render_metric(t5, "Fatigue Idx", f"{avg_fatigue:.1f}%" if avg_fatigue else "-", help_texts.get("fatigue_index", ""))

    # ACWR with status
    acwr_value = f"{acwr:.2f}" if pd.notna(acwr) else "-"
    acwr_status = (
        " ✅" if pd.notna(acwr) and 0.8 <= acwr <= 1.3 else
        " ⚠️" if pd.notna(acwr) and acwr > 1.3 else
        " 📉" if pd.notna(acwr) else ""
    )
    render_metric(t6, "ACWR", f"{acwr_value}{acwr_status}", help_texts.get("acwr", ""))

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

    if not df_month.empty:
        latest_activity = df_month.sort_values("start_date", ascending=False).iloc[0]

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
            st.info("No power profile data available for this month")


def render_overview_tab(
    df_month: pd.DataFrame,
    selected_month: pd.Timestamp,
    metric_view: str,
    calculate_monthly_tid_fn,
    format_duration_fn,
    settings,
    df_all_activities: pd.DataFrame = None,
    help_texts: dict = None,
) -> None:
    """
    Render the Overview tab with weekly breakdown and TID analysis.

    Args:
        df_month: Current month activities
        selected_month: Start of the month
        metric_view: "Moving" or "Raw"
        calculate_monthly_tid_fn: Function to calculate TID
        format_duration_fn: Function to format duration
        settings: Settings object with gear names
        df_all_activities: All activities (for Section 3 calculations)
        help_texts: Dictionary of help text strings
    """
    col_weekly, col_tid = st.columns([2, 1])

    with col_weekly:
        st.subheader("Weekly Breakdown")
        if not df_month.empty:
            df_month_weekly = df_month.copy()

            # Add week column
            df_month_weekly["week_start"] = (
                df_month_weekly["start_date_local"]
                - pd.to_timedelta(df_month_weekly["start_date_local"].dt.weekday, unit='D')
            ).dt.normalize()

            # Ensure TSS column exists
            tss_col = "training_stress_score"
            if tss_col not in df_month_weekly.columns:
                df_month_weekly[tss_col] = 0

            # Group by week
            weekly_stats = (
                df_month_weekly.groupby("week_start")
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
            weekly_stats["distance_km"] = weekly_stats["distance"] / 1000
            weekly_stats["time_hours"] = weekly_stats["moving_time"] / 3600

            # Sort by week
            weekly_stats = weekly_stats.sort_values("week_start")

            # Create week labels
            weekly_stats["week_label"] = weekly_stats["week_start"].dt.strftime("Week %d %b")

            # Dual-axis chart: Distance bars + TSS line
            fig_weekly = make_subplots(specs=[[{"secondary_y": True}]])

            fig_weekly.add_trace(
                go.Bar(
                    x=weekly_stats["week_label"],
                    y=weekly_stats["distance_km"],
                    name="Distance (km)",
                    marker_color="#3498db",
                ),
                secondary_y=False,
            )

            fig_weekly.add_trace(
                go.Scatter(
                    x=weekly_stats["week_label"],
                    y=weekly_stats[tss_col],
                    name="TSS",
                    line=dict(color="#e74c3c", width=3),
                    mode="lines+markers",
                ),
                secondary_y=True,
            )

            fig_weekly.update_layout(
                title="Weekly Volume & Training Load",
                legend=dict(x=0, y=1.1, orientation="h"),
                hovermode="x unified",
            )
            fig_weekly.update_yaxes(title_text="Distance (km)", secondary_y=False)
            fig_weekly.update_yaxes(title_text="TSS", secondary_y=True)

            st.plotly_chart(fig_weekly, use_container_width=True)
        else:
            st.info("No activities this month.")

    with col_tid:
        st.subheader("Monthly TID")
        tid = calculate_monthly_tid_fn(df_month, metric_view)

        if any(tid.values()):
            # Create horizontal bar chart
            tid_data = ["Z1 Low", "Z2 Moderate", "Z3 High"]
            tid_values = [tid["z1"], tid["z2"], tid["z3"]]
            tid_colors = ["#808080", "#3498db", "#e74c3c"]

            fig_tid = go.Figure()
            fig_tid.add_trace(
                go.Bar(
                    y=tid_data,
                    x=tid_values,
                    orientation="h",
                    marker_color=tid_colors,
                    text=[f"{v:.0f}%" for v in tid_values],
                    textposition="outside",
                )
            )
            fig_tid.update_layout(
                xaxis_title="% of Time",
                height=200,
                margin={"l": 80, "r": 40, "t": 20, "b": 40},
                showlegend=False,
            )
            st.plotly_chart(fig_tid, use_container_width=True)

            # TID Summary
            total_tid = sum(tid_values)
            if total_tid > 0:
                z1_ratio = tid["z1"] / total_tid * 100
                z3_ratio = tid["z3"] / total_tid * 100
                if z1_ratio > 75 and z3_ratio > 10:
                    st.success("✅ Polarized distribution - ideal for endurance")
                elif z1_ratio < 60:
                    st.warning("⚠️ Too much moderate intensity - consider polarizing")
                else:
                    st.info("ℹ️ Balanced intensity distribution")
        else:
            st.info("No TID data available.")

    # Activity Calendar Heatmap
    st.divider()
    st.subheader("📅 Activity Calendar")

    if not df_month.empty:
        df_calendar = df_month.copy()
        df_calendar["date"] = df_calendar["start_date_local"].dt.date

        # Aggregate by date
        daily_stats = df_calendar.groupby("date").agg({
            "training_stress_score": "sum",
            "distance": "sum",
            "id": "count"
        }).reset_index()
        daily_stats.columns = ["date", "tss", "distance", "count"]
        daily_stats["distance_km"] = daily_stats["distance"] / 1000

        # Create calendar heatmap data
        # Get all days in month
        if selected_month.month == 12:
            month_end = pd.Timestamp(year=selected_month.year + 1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            month_end = pd.Timestamp(year=selected_month.year, month=selected_month.month + 1, day=1) - pd.Timedelta(days=1)

        all_days = pd.date_range(start=selected_month, end=month_end, freq='D')

        # Create complete dataframe
        calendar_df = pd.DataFrame({"date": all_days.date})
        calendar_df = calendar_df.merge(daily_stats, on="date", how="left").fillna(0)

        # Add day info
        calendar_df["day_of_week"] = pd.to_datetime(calendar_df["date"]).dt.dayofweek
        calendar_df["week_of_month"] = (pd.to_datetime(calendar_df["date"]).dt.day - 1) // 7
        calendar_df["day_name"] = pd.to_datetime(calendar_df["date"]).dt.strftime("%a")

        # Create heatmap
        fig_calendar = go.Figure()

        # Pivot for heatmap
        heatmap_data = calendar_df.pivot(index="day_of_week", columns="week_of_month", values="tss")
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        fig_calendar.add_trace(
            go.Heatmap(
                z=heatmap_data.values,
                x=[f"Week {i+1}" for i in range(heatmap_data.shape[1])],
                y=day_labels,
                colorscale="YlOrRd",
                text=heatmap_data.values,
                texttemplate="%{text:.0f}",
                hovertemplate="<b>%{y}</b>, %{x}<br>TSS: %{z:.0f}<extra></extra>",
                showscale=True,
                colorbar=dict(title="TSS"),
            )
        )

        fig_calendar.update_layout(
            title="Daily TSS Heatmap",
            height=250,
            margin={"l": 60, "r": 20, "t": 40, "b": 20},
        )

        st.plotly_chart(fig_calendar, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Cumulative Volume Charts
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📈 Cumulative Volume")

    if not df_month.empty:
        # Sort activities by date for cumulative calculation
        df_cumulative = df_month.copy().sort_values("start_date_local")
        df_cumulative["date"] = df_cumulative["start_date_local"].dt.date

        # Calculate daily aggregates
        daily_volume = df_cumulative.groupby("date").agg({
            "distance": "sum",
            "moving_time": "sum",
            "total_elevation_gain": "sum",
            "training_stress_score": "sum",
        }).reset_index()

        daily_volume["distance_km"] = daily_volume["distance"] / 1000
        daily_volume["time_hours"] = daily_volume["moving_time"] / 3600

        # Create full date range and merge
        if selected_month.month == 12:
            month_end = pd.Timestamp(year=selected_month.year + 1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            month_end = pd.Timestamp(year=selected_month.year, month=selected_month.month + 1, day=1) - pd.Timedelta(days=1)

        all_days = pd.date_range(start=selected_month, end=month_end, freq='D')
        full_dates = pd.DataFrame({"date": all_days.date})
        daily_volume = full_dates.merge(daily_volume, on="date", how="left").fillna(0)

        # Calculate cumulative values
        daily_volume["cum_distance"] = daily_volume["distance_km"].cumsum()
        daily_volume["cum_time"] = daily_volume["time_hours"].cumsum()
        daily_volume["cum_elevation"] = daily_volume["total_elevation_gain"].cumsum()
        daily_volume["cum_tss"] = daily_volume["training_stress_score"].cumsum()

        col_dist, col_time = st.columns(2)

        with col_dist:
            # Cumulative Distance + daily bars
            fig_cum_dist = make_subplots(specs=[[{"secondary_y": True}]])

            fig_cum_dist.add_trace(
                go.Bar(
                    x=daily_volume["date"],
                    y=daily_volume["distance_km"],
                    name="Daily Distance",
                    marker_color="rgba(52, 152, 219, 0.5)",
                    hovertemplate="%{x}<br>Daily: %{y:.1f} km<extra></extra>",
                ),
                secondary_y=False,
            )

            fig_cum_dist.add_trace(
                go.Scatter(
                    x=daily_volume["date"],
                    y=daily_volume["cum_distance"],
                    name="Cumulative",
                    line=dict(color="#2980b9", width=3),
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(41, 128, 185, 0.2)",
                    hovertemplate="%{x}<br>Total: %{y:.1f} km<extra></extra>",
                ),
                secondary_y=True,
            )

            fig_cum_dist.update_layout(
                title="Cumulative Distance",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
                height=300,
            )
            fig_cum_dist.update_yaxes(title_text="Daily (km)", secondary_y=False)
            fig_cum_dist.update_yaxes(title_text="Cumulative (km)", secondary_y=True)
            fig_cum_dist.update_xaxes(tickformat="%d %b")

            st.plotly_chart(fig_cum_dist, use_container_width=True)

        with col_time:
            # Cumulative Time + daily bars
            fig_cum_time = make_subplots(specs=[[{"secondary_y": True}]])

            fig_cum_time.add_trace(
                go.Bar(
                    x=daily_volume["date"],
                    y=daily_volume["time_hours"],
                    name="Daily Time",
                    marker_color="rgba(46, 204, 113, 0.5)",
                    hovertemplate="%{x}<br>Daily: %{y:.1f} h<extra></extra>",
                ),
                secondary_y=False,
            )

            fig_cum_time.add_trace(
                go.Scatter(
                    x=daily_volume["date"],
                    y=daily_volume["cum_time"],
                    name="Cumulative",
                    line=dict(color="#27ae60", width=3),
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(39, 174, 96, 0.2)",
                    hovertemplate="%{x}<br>Total: %{y:.1f} h<extra></extra>",
                ),
                secondary_y=True,
            )

            fig_cum_time.update_layout(
                title="Cumulative Time",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
                height=300,
            )
            fig_cum_time.update_yaxes(title_text="Daily (hours)", secondary_y=False)
            fig_cum_time.update_yaxes(title_text="Cumulative (hours)", secondary_y=True)
            fig_cum_time.update_xaxes(tickformat="%d %b")

            st.plotly_chart(fig_cum_time, use_container_width=True)

        # Cumulative TSS + Elevation in second row
        col_tss, col_elev = st.columns(2)

        with col_tss:
            fig_cum_tss = make_subplots(specs=[[{"secondary_y": True}]])

            fig_cum_tss.add_trace(
                go.Bar(
                    x=daily_volume["date"],
                    y=daily_volume["training_stress_score"],
                    name="Daily TSS",
                    marker_color="rgba(231, 76, 60, 0.5)",
                    hovertemplate="%{x}<br>Daily: %{y:.0f}<extra></extra>",
                ),
                secondary_y=False,
            )

            fig_cum_tss.add_trace(
                go.Scatter(
                    x=daily_volume["date"],
                    y=daily_volume["cum_tss"],
                    name="Cumulative",
                    line=dict(color="#c0392b", width=3),
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(192, 57, 43, 0.2)",
                    hovertemplate="%{x}<br>Total: %{y:.0f}<extra></extra>",
                ),
                secondary_y=True,
            )

            fig_cum_tss.update_layout(
                title="Cumulative TSS",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
                height=300,
            )
            fig_cum_tss.update_yaxes(title_text="Daily TSS", secondary_y=False)
            fig_cum_tss.update_yaxes(title_text="Cumulative TSS", secondary_y=True)
            fig_cum_tss.update_xaxes(tickformat="%d %b")

            st.plotly_chart(fig_cum_tss, use_container_width=True)

        with col_elev:
            fig_cum_elev = make_subplots(specs=[[{"secondary_y": True}]])

            fig_cum_elev.add_trace(
                go.Bar(
                    x=daily_volume["date"],
                    y=daily_volume["total_elevation_gain"],
                    name="Daily Elevation",
                    marker_color="rgba(155, 89, 182, 0.5)",
                    hovertemplate="%{x}<br>Daily: %{y:.0f} m<extra></extra>",
                ),
                secondary_y=False,
            )

            fig_cum_elev.add_trace(
                go.Scatter(
                    x=daily_volume["date"],
                    y=daily_volume["cum_elevation"],
                    name="Cumulative",
                    line=dict(color="#8e44ad", width=3),
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(142, 68, 173, 0.2)",
                    hovertemplate="%{x}<br>Total: %{y:.0f} m<extra></extra>",
                ),
                secondary_y=True,
            )

            fig_cum_elev.update_layout(
                title="Cumulative Elevation",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
                height=300,
            )
            fig_cum_elev.update_yaxes(title_text="Daily (m)", secondary_y=False)
            fig_cum_elev.update_yaxes(title_text="Cumulative (m)", secondary_y=True)
            fig_cum_elev.update_xaxes(tickformat="%d %b")

            st.plotly_chart(fig_cum_elev, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # Training Load Evolution (CTL, ATL, TSB)
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("📊 Training Load Evolution")

    if not df_month.empty:
        # Get training load metrics from activities
        df_load = df_month.copy().sort_values("start_date_local")

        # Check if we have training load columns
        has_ctl = "chronic_training_load" in df_load.columns
        has_atl = "acute_training_load" in df_load.columns
        has_tsb = "training_stress_balance" in df_load.columns

        if has_ctl or has_atl or has_tsb:
            fig_load = go.Figure()

            if has_ctl:
                fig_load.add_trace(
                    go.Scatter(
                        x=df_load["start_date_local"],
                        y=df_load["chronic_training_load"],
                        name="CTL (Fitness)",
                        line=dict(color="#2ecc71", width=2),
                        mode="lines+markers",
                        hovertemplate="%{x}<br>CTL: %{y:.0f}<extra></extra>",
                    )
                )

            if has_atl:
                fig_load.add_trace(
                    go.Scatter(
                        x=df_load["start_date_local"],
                        y=df_load["acute_training_load"],
                        name="ATL (Fatigue)",
                        line=dict(color="#e74c3c", width=2),
                        mode="lines+markers",
                        hovertemplate="%{x}<br>ATL: %{y:.0f}<extra></extra>",
                    )
                )

            if has_tsb:
                fig_load.add_trace(
                    go.Scatter(
                        x=df_load["start_date_local"],
                        y=df_load["training_stress_balance"],
                        name="TSB (Form)",
                        line=dict(color="#3498db", width=2),
                        mode="lines+markers",
                        fill="tozeroy",
                        fillcolor="rgba(52, 152, 219, 0.2)",
                        hovertemplate="%{x}<br>TSB: %{y:.0f}<extra></extra>",
                    )
                )
                # Add reference zones for TSB
                fig_load.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)
                fig_load.add_hline(y=-10, line_dash="dot", line_color="orange", opacity=0.5,
                                   annotation_text="Overreach", annotation_position="right")
                fig_load.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.5,
                                   annotation_text="Fresh", annotation_position="right")

            fig_load.update_layout(
                title="Training Load Progression",
                xaxis_title="Date",
                yaxis_title="Training Load",
                legend=dict(x=0, y=1.15, orientation="h"),
                hovermode="x unified",
                height=350,
            )
            fig_load.update_xaxes(tickformat="%d %b")

            st.plotly_chart(fig_load, use_container_width=True)
        else:
            st.info("No training load data (CTL/ATL/TSB) available for this month.")

    # ═══════════════════════════════════════════════════════════════════════════
    # Efficiency & Intensity Evolution (IF, EF, TSS per activity)
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("⚡ Efficiency & Intensity Evolution")

    if not df_month.empty:
        df_eff = df_month.copy().sort_values("start_date_local")

        col_if_ef, col_tss_act = st.columns(2)

        with col_if_ef:
            # IF and EF over time
            has_if = "intensity_factor" in df_eff.columns and df_eff["intensity_factor"].notna().any()
            has_ef = "efficiency_factor" in df_eff.columns and df_eff["efficiency_factor"].notna().any()

            if has_if or has_ef:
                fig_eff = make_subplots(specs=[[{"secondary_y": True}]])

                if has_if:
                    fig_eff.add_trace(
                        go.Scatter(
                            x=df_eff["start_date_local"],
                            y=df_eff["intensity_factor"],
                            name="IF",
                            line=dict(color="#e67e22", width=2),
                            mode="lines+markers",
                            hovertemplate="%{x}<br>IF: %{y:.2f}<extra></extra>",
                        ),
                        secondary_y=False,
                    )
                    # IF reference zones
                    fig_eff.add_hline(y=0.75, line_dash="dot", line_color="gray", opacity=0.3,
                                      annotation_text="Endurance", secondary_y=False)
                    fig_eff.add_hline(y=0.85, line_dash="dot", line_color="gray", opacity=0.3,
                                      annotation_text="Tempo", secondary_y=False)
                    fig_eff.add_hline(y=0.95, line_dash="dot", line_color="gray", opacity=0.3,
                                      annotation_text="Threshold", secondary_y=False)

                if has_ef:
                    fig_eff.add_trace(
                        go.Scatter(
                            x=df_eff["start_date_local"],
                            y=df_eff["efficiency_factor"],
                            name="EF",
                            line=dict(color="#9b59b6", width=2),
                            mode="lines+markers",
                            hovertemplate="%{x}<br>EF: %{y:.2f}<extra></extra>",
                        ),
                        secondary_y=True,
                    )

                fig_eff.update_layout(
                    title="Intensity Factor & Efficiency Factor",
                    legend=dict(x=0, y=1.15, orientation="h"),
                    hovermode="x unified",
                    height=300,
                )
                fig_eff.update_yaxes(title_text="IF", secondary_y=False)
                fig_eff.update_yaxes(title_text="EF", secondary_y=True)
                fig_eff.update_xaxes(tickformat="%d %b")

                st.plotly_chart(fig_eff, use_container_width=True)
            else:
                st.info("No IF/EF data available.")

        with col_tss_act:
            # TSS per activity with NP overlay
            has_tss = "training_stress_score" in df_eff.columns
            has_np = "normalized_power" in df_eff.columns

            if has_tss:
                fig_tss_np = make_subplots(specs=[[{"secondary_y": True}]])

                # TSS bars
                fig_tss_np.add_trace(
                    go.Bar(
                        x=df_eff["start_date_local"],
                        y=df_eff["training_stress_score"],
                        name="TSS",
                        marker_color="rgba(231, 76, 60, 0.6)",
                        hovertemplate="%{x}<br>TSS: %{y:.0f}<extra></extra>",
                    ),
                    secondary_y=False,
                )

                if has_np and df_eff["normalized_power"].notna().any():
                    fig_tss_np.add_trace(
                        go.Scatter(
                            x=df_eff["start_date_local"],
                            y=df_eff["normalized_power"],
                            name="NP",
                            line=dict(color="#3498db", width=2),
                            mode="lines+markers",
                            hovertemplate="%{x}<br>NP: %{y:.0f}W<extra></extra>",
                        ),
                        secondary_y=True,
                    )

                fig_tss_np.update_layout(
                    title="TSS & Normalized Power per Activity",
                    legend=dict(x=0, y=1.15, orientation="h"),
                    hovermode="x unified",
                    height=300,
                )
                fig_tss_np.update_yaxes(title_text="TSS", secondary_y=False)
                fig_tss_np.update_yaxes(title_text="NP (W)", secondary_y=True)
                fig_tss_np.update_xaxes(tickformat="%d %b")

                st.plotly_chart(fig_tss_np, use_container_width=True)
            else:
                st.info("No TSS data available.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3: New Physiological Metrics
    # ═══════════════════════════════════════════════════════════════════════════

    if help_texts is not None and df_all_activities is not None:
        st.divider()

        # Section 3.1: Fitness Evolution
        with st.expander("📈 Fitness Evolution", expanded=False):
            render_fitness_evolution_section(df_month, df_all_activities, selected_month, help_texts)

        st.divider()

        # Section 3.2: Periodization Check
        with st.expander("🔄 Periodization Check", expanded=False):
            render_periodization_check(df_month, df_all_activities, selected_month, help_texts)

        st.divider()

        # Section 3.3: Aerobic Development
        with st.expander("❤️ Aerobic Development", expanded=False):
            render_aerobic_development(df_month, help_texts)

        st.divider()

        # Section 3.4: Training Consistency
        with st.expander("📅 Training Consistency", expanded=False):
            render_training_consistency(df_month, selected_month, help_texts)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.1: Fitness Evolution
# ═══════════════════════════════════════════════════════════════════════════════


def render_fitness_evolution_section(
    df_month: pd.DataFrame,
    df_all_activities: pd.DataFrame,
    selected_month: pd.Timestamp,
    help_texts: dict,
) -> None:
    """
    Render Fitness Evolution section with FTP estimates and power PRs.

    Args:
        df_month: Current month activities
        df_all_activities: All activities for trend analysis
        selected_month: Start of the month
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 📈 Fitness Evolution")

    # Check if FTP estimate data is available
    if "estimated_ftp" not in df_month.columns or df_month["estimated_ftp"].isna().all():
        st.info("FTP estimate data not available. Requires power meter data for calculation.")
        return

    # Get FTP estimates for the month
    df_month_ftp = df_month[df_month["estimated_ftp"].notna()].copy()

    if len(df_month_ftp) == 0:
        st.info("No FTP estimates available for this month.")
        return

    # Sort by date
    df_month_ftp = df_month_ftp.sort_values("start_date_local")

    # FTP start (first estimate) and end (last estimate)
    ftp_start = df_month_ftp.iloc[0]["estimated_ftp"]
    ftp_end = df_month_ftp.iloc[-1]["estimated_ftp"]
    ftp_change = ftp_end - ftp_start
    ftp_change_pct = (ftp_change / ftp_start * 100) if ftp_start > 0 else 0

    # 3-column layout for FTP metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "Est. FTP Start",
            f"{ftp_start:.0f} W",
            help_texts.get("ftp_start", "Estimated FTP at beginning of month")
        )

    with col2:
        render_metric(
            col2,
            "Est. FTP End",
            f"{ftp_end:.0f} W",
            help_texts.get("ftp_end", "Estimated FTP at end of month")
        )

    with col3:
        change_symbol = "✅" if ftp_change > 0 else "⚠️" if ftp_change < 0 else "➡️"
        render_metric(
            col3,
            "Change",
            f"{ftp_change:+.0f} W ({ftp_change_pct:+.1f}%) {change_symbol}",
            help_texts.get("ftp_change", "FTP change over the month. Positive = fitness improvement")
        )

    # FTP trend chart
    if len(df_month_ftp) > 1:
        fig_ftp = go.Figure()

        fig_ftp.add_trace(go.Scatter(
            x=df_month_ftp["start_date_local"],
            y=df_month_ftp["estimated_ftp"],
            mode='lines+markers',
            name='Estimated FTP',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=8)
        ))

        fig_ftp.update_layout(
            title="FTP Trend Over Month",
            xaxis_title="Date",
            yaxis_title="Estimated FTP (W)",
            hovermode="x unified",
            height=300
        )

        st.plotly_chart(fig_ftp, use_container_width=True)

    # Power PRs this month
    st.markdown("**🏆 Power PRs This Month:**")

    pr_durations = {
        "5min": ("power_5min", 300),
        "20min": ("power_20min", 1200),
        "60min": ("power_60min", 3600)
    }

    pr_cols = st.columns(len(pr_durations))

    for idx, (duration_name, (col_name, _)) in enumerate(pr_durations.items()):
        with pr_cols[idx]:
            if col_name in df_month.columns:
                max_power = df_month[col_name].max()
                if pd.notna(max_power) and max_power > 0:
                    st.metric(f"{duration_name}", f"{max_power:.0f} W")
                else:
                    st.caption(f"{duration_name}: -")
            else:
                st.caption(f"{duration_name}: -")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.2: Periodization Check
# ═══════════════════════════════════════════════════════════════════════════════


def render_periodization_check(
    df_month: pd.DataFrame,
    df_all_activities: pd.DataFrame,
    selected_month: pd.Timestamp,
    help_texts: dict,
) -> None:
    """
    Render Periodization Check section with block classification.

    Args:
        df_month: Current month activities
        df_all_activities: All activities for 3-month average calculation
        selected_month: Start of the month
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 🗓️ Periodization Check")

    # Calculate month metrics
    month_volume = df_month["moving_time"].sum() if "moving_time" in df_month.columns else 0
    month_avg_if = df_month["intensity_factor"].mean() if "intensity_factor" in df_month.columns else 0

    # Get previous 3 months for comparison
    month_start = selected_month
    three_months_ago = month_start - pd.DateOffset(months=3)

    df_prev_3months = df_all_activities[
        (df_all_activities["start_date_local"] >= three_months_ago) &
        (df_all_activities["start_date_local"] < month_start)
    ]

    if len(df_prev_3months) > 0:
        # Calculate 3-month averages
        df_prev_3months_copy = df_prev_3months.copy()
        df_prev_3months_copy["month_start"] = df_prev_3months_copy["start_date_local"].dt.to_period('M').apply(lambda x: x.start_time)

        monthly_volumes = df_prev_3months_copy.groupby("month_start")["moving_time"].sum()
        monthly_ifs = df_prev_3months_copy.groupby("month_start")["intensity_factor"].mean()

        rolling_3month_avg_volume = monthly_volumes.mean()
        rolling_3month_avg_if = monthly_ifs.mean()
    else:
        rolling_3month_avg_volume = month_volume
        rolling_3month_avg_if = month_avg_if

    # Calculate ratios
    volume_vs_avg = (month_volume / rolling_3month_avg_volume) if rolling_3month_avg_volume > 0 else 1.0
    intensity_vs_avg = (month_avg_if / rolling_3month_avg_if) if rolling_3month_avg_if > 0 else 1.0

    # Block classification
    if volume_vs_avg < 0.6:
        block_type = "🛌 RECOVERY"
        block_color = "#95a5a6"
    elif volume_vs_avg > 1.1 and intensity_vs_avg < 0.95:
        block_type = "🏗️ BASE"
        block_color = "#3498db"
    elif volume_vs_avg > 1.0 and intensity_vs_avg > 1.05:
        block_type = "💪 BUILD"
        block_color = "#f39c12"
    elif intensity_vs_avg > 1.1:
        block_type = "⚡ PEAK"
        block_color = "#e74c3c"
    else:
        block_type = "➡️ MAINTENANCE"
        block_color = "#2ecc71"

    # Count long rides (>3 hours)
    long_ride_count = len(df_month[df_month["moving_time"] > 10800]) if "moving_time" in df_month.columns else 0

    # Display block type prominently
    st.markdown(f"<h4 style='color: {block_color};'>Block Type: {block_type}</h4>", unsafe_allow_html=True)

    # 3-column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        volume_change_pct = (volume_vs_avg - 1) * 100
        arrow = "⬆️" if volume_change_pct > 5 else "⬇️" if volume_change_pct < -5 else "➡️"
        render_metric(
            col1,
            "Volume vs 3mo avg",
            f"{volume_change_pct:+.0f}% {arrow}",
            help_texts.get("volume_vs_avg", "Monthly volume compared to 3-month rolling average")
        )

    with col2:
        intensity_change_pct = (intensity_vs_avg - 1) * 100
        arrow = "⬆️" if intensity_change_pct > 5 else "⬇️" if intensity_change_pct < -5 else "➡️"
        render_metric(
            col2,
            "Intensity vs 3mo avg",
            f"{intensity_change_pct:+.0f}% {arrow}",
            help_texts.get("intensity_vs_avg", "Average intensity (IF) compared to 3-month rolling average")
        )

    with col3:
        render_metric(
            col3,
            "Long Rides (>3h)",
            f"{long_ride_count}",
            help_texts.get("long_rides", "Number of rides longer than 3 hours. Important for endurance development")
        )

    # Recommendation based on block type
    st.markdown("**💡 Recommendation:**")
    if "BUILD" in block_type:
        st.warning("High load block. Monitor recovery and schedule a recovery week.")
    elif "PEAK" in block_type:
        st.info("Peak intensity phase. Ensure adequate recovery between sessions.")
    elif "RECOVERY" in block_type:
        st.success("Recovery phase. Good time for adaptation and healing.")
    elif "BASE" in block_type:
        st.info("Aerobic base building. Focus on Z2 volume and consistency.")
    else:
        st.info("Maintenance phase. Steady training load.")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.3: Aerobic Development
# ═══════════════════════════════════════════════════════════════════════════════


def render_aerobic_development(
    df_month: pd.DataFrame,
    help_texts: dict,
) -> None:
    """
    Render Aerobic Development section with EF trend and decoupling.

    Args:
        df_month: Current month activities
        help_texts: Dictionary of help text strings
    """
    st.markdown("### ❤️ Aerobic Development")

    # Check if EF and decoupling data available
    if "efficiency_factor" not in df_month.columns or df_month["efficiency_factor"].isna().all():
        st.info("Efficiency Factor data not available. Requires power and heart rate data.")
        return

    df_month_ef = df_month[df_month["efficiency_factor"].notna()].copy()

    if len(df_month_ef) == 0:
        st.info("No Efficiency Factor data available for this month.")
        return

    # Sort by date
    df_month_ef = df_month_ef.sort_values("start_date_local")

    # Calculate EF trend (linear regression)
    import numpy as np
    from scipy import stats

    # Create day numbers for regression
    df_month_ef["days_from_start"] = (df_month_ef["start_date_local"] - df_month_ef["start_date_local"].min()).dt.days

    if len(df_month_ef) > 2:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            df_month_ef["days_from_start"],
            df_month_ef["efficiency_factor"]
        )

        # Convert slope to per-week
        ef_trend_per_week = slope * 7

        # Create regression line
        df_month_ef["ef_trend"] = intercept + slope * df_month_ef["days_from_start"]
    else:
        ef_trend_per_week = 0
        df_month_ef["ef_trend"] = df_month_ef["efficiency_factor"]

    # EF Trend Chart
    fig_ef = go.Figure()

    fig_ef.add_trace(go.Scatter(
        x=df_month_ef["start_date_local"],
        y=df_month_ef["efficiency_factor"],
        mode='markers',
        name='EF',
        marker=dict(size=8, color='#3498db')
    ))

    if len(df_month_ef) > 2:
        fig_ef.add_trace(go.Scatter(
            x=df_month_ef["start_date_local"],
            y=df_month_ef["ef_trend"],
            mode='lines',
            name='Trend',
            line=dict(color='#e74c3c', width=2, dash='dash')
        ))

    fig_ef.update_layout(
        title="Efficiency Factor Trend",
        xaxis_title="Date",
        yaxis_title="EF (W/bpm)",
        hovermode="x unified",
        height=300
    )

    st.plotly_chart(fig_ef, use_container_width=True)

    # Metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        trend_symbol = "✅" if ef_trend_per_week > 0 else "⚠️" if ef_trend_per_week < 0 else "➡️"
        render_metric(
            col1,
            "EF Trend",
            f"{ef_trend_per_week:+.2f}/week {trend_symbol}",
            help_texts.get("ef_trend", "Weekly change in Efficiency Factor. Positive = improving aerobic efficiency")
        )
        if ef_trend_per_week > 0.01:
            st.success("Improving aerobic fitness")
        elif ef_trend_per_week < -0.01:
            st.warning("Declining aerobic efficiency")
        else:
            st.info("Stable aerobic fitness")

    with col2:
        avg_decoupling = df_month_ef["cardiac_drift"].mean() if "cardiac_drift" in df_month_ef.columns else 0
        render_metric(
            col2,
            "Avg Decoupling",
            f"{avg_decoupling:.1f}%",
            help_texts.get("avg_decoupling", "Average cardiac drift. Lower = better aerobic fitness")
        )
        if avg_decoupling < 5:
            st.success("✅ Good aerobic fitness")
        elif avg_decoupling < 10:
            st.info("➡️ Moderate decoupling")
        else:
            st.warning("⚠️ High decoupling")

    with col3:
        if "cardiac_drift" in df_month_ef.columns and len(df_month_ef) > 2:
            # Calculate decoupling trend
            df_month_ef_cd = df_month_ef[df_month_ef["cardiac_drift"].notna()].copy()
            if len(df_month_ef_cd) > 2:
                cd_slope, _, _, _, _ = stats.linregress(
                    df_month_ef_cd["days_from_start"],
                    df_month_ef_cd["cardiac_drift"]
                )
                decoupling_trend_per_week = cd_slope * 7
            else:
                decoupling_trend_per_week = 0
        else:
            decoupling_trend_per_week = 0

        trend_symbol = "✅" if decoupling_trend_per_week < 0 else "⚠️" if decoupling_trend_per_week > 0 else "➡️"
        render_metric(
            col3,
            "Decoupling Trend",
            f"{decoupling_trend_per_week:+.2f}%/week {trend_symbol}",
            help_texts.get("decoupling_trend", "Weekly change in cardiac drift. Negative = improving aerobic fitness")
        )
        if decoupling_trend_per_week < -0.1:
            st.success("Improving aerobic fitness")
        elif decoupling_trend_per_week > 0.1:
            st.warning("Increasing fatigue/drift")
        else:
            st.info("Stable")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.4: Training Consistency
# ═══════════════════════════════════════════════════════════════════════════════


def render_training_consistency(
    df_month: pd.DataFrame,
    selected_month: pd.Timestamp,
    help_texts: dict,
) -> None:
    """
    Render Training Consistency section with training days, streaks, and gaps.

    Args:
        df_month: Current month activities
        selected_month: Start of the month
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 📊 Training Consistency")

    if df_month.empty:
        st.info("No activities this month.")
        return

    # Get unique training days
    df_month_copy = df_month.copy()
    df_month_copy["date_local"] = df_month_copy["start_date_local"].dt.date
    training_days = df_month_copy["date_local"].unique()
    training_days_count = len(training_days)

    # Calculate total days in month
    if selected_month.month == 12:
        month_end = pd.Timestamp(year=selected_month.year + 1, month=1, day=1) - pd.Timedelta(days=1)
    else:
        month_end = pd.Timestamp(year=selected_month.year, month=selected_month.month + 1, day=1) - pd.Timedelta(days=1)

    days_in_month = (month_end - selected_month).days + 1
    consistency_pct = (training_days_count / days_in_month * 100)

    # Calculate longest streak
    training_days_sorted = sorted(training_days)
    training_days_pd = pd.to_datetime(training_days_sorted)

    longest_streak = 1
    current_streak = 1

    for i in range(1, len(training_days_pd)):
        if (training_days_pd[i] - training_days_pd[i-1]).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    # Calculate longest gap
    longest_gap = 0
    if len(training_days_pd) > 1:
        for i in range(1, len(training_days_pd)):
            gap = (training_days_pd[i] - training_days_pd[i-1]).days - 1
            longest_gap = max(longest_gap, gap)

    # 3-column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "Training Days",
            f"{training_days_count} / {days_in_month} ({consistency_pct:.0f}%)",
            help_texts.get("training_days", "Number of days with at least one activity")
        )
        if consistency_pct >= 70:
            st.success("✅ Good consistency")
        elif consistency_pct >= 50:
            st.info("➡️ Moderate consistency")
        else:
            st.warning("⚠️ Low consistency")

    with col2:
        render_metric(
            col2,
            "Longest Streak",
            f"{longest_streak} days",
            help_texts.get("longest_streak", "Longest consecutive training days without a day off")
        )

    with col3:
        render_metric(
            col3,
            "Longest Gap",
            f"{longest_gap} days",
            help_texts.get("longest_gap", "Longest period without training in the month")
        )
        if longest_gap <= 3:
            st.success("✅ Normal")
        elif longest_gap <= 7:
            st.info("➡️ Week off")
        else:
            st.warning("⚠️ Extended break")


def render_intensity_tab(df_month: pd.DataFrame, selected_month: pd.Timestamp, metric_view: str) -> None:
    """
    Render the Intensity Distribution tab with power and HR zones.

    Args:
        df_month: Current month activities
        selected_month: Start of the month
        metric_view: "Moving" or "Raw"
    """
    col_pz, col_hrz = st.columns(2)

    with col_pz:
        st.subheader("Monthly Power Zone Distribution")
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
        power_zone_ranges = [
            "0-55% FTP",
            "55-75% FTP",
            "75-90% FTP",
            "90-105% FTP",
            "105-120% FTP",
            "120-150% FTP",
            ">150% FTP",
        ]
        total_time = df_month["moving_time"].sum()

        for i in range(1, 8):
            col_name = f"power_z{i}_percentage"
            if col_name in df_month.columns and total_time > 0:
                weighted_pct = (
                    df_month[col_name].fillna(0) * df_month["moving_time"]
                ).sum() / total_time
                power_zones.append(weighted_pct)
            else:
                power_zones.append(0)

        if any(power_zones):
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
        st.subheader("Monthly HR Zone Distribution")
        hr_zones = []
        hr_zone_names = [
            "Z1 Easy",
            "Z2 Aerobic",
            "Z3 Tempo",
            "Z4 Threshold",
            "Z5 Max",
        ]
        hr_zone_ranges = [
            "<85% LTHR",
            "85-94% LTHR",
            "94-104% LTHR",
            "104-120% LTHR",
            ">120% LTHR",
        ]

        for i in range(1, 6):
            col_name = f"hr_z{i}_percentage"
            if col_name in df_month.columns and total_time > 0:
                weighted_pct = (
                    df_month[col_name].fillna(0) * df_month["moving_time"]
                ).sum() / total_time
                hr_zones.append(weighted_pct)
            else:
                hr_zones.append(0)

        if any(hr_zones):
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

    # Weekly Intensity Comparison
    st.subheader("Weekly Intensity Comparison")
    if not df_month.empty:
        df_intensity = df_month.copy()

        # Add week column
        df_intensity["week_start"] = (
            df_intensity["start_date_local"]
            - pd.to_timedelta(df_intensity["start_date_local"].dt.weekday, unit='D')
        ).dt.normalize()

        # Aggregate by week
        if_col = "intensity_factor"
        tss_col = "training_stress_score"

        if if_col not in df_intensity.columns:
            df_intensity[if_col] = None
        if tss_col not in df_intensity.columns:
            df_intensity[tss_col] = 0

        weekly_if = df_intensity.groupby("week_start").agg({
            if_col: "mean",
            tss_col: "sum",
            "moving_time": "sum"
        }).reset_index()

        weekly_if["week_label"] = weekly_if["week_start"].dt.strftime("Week %d %b")
        weekly_if = weekly_if.dropna(subset=[if_col])

        if not weekly_if.empty:
            # Create horizontal bar chart
            fig_weekly_if = go.Figure()
            fig_weekly_if.add_trace(
                go.Bar(
                    y=weekly_if["week_label"],
                    x=weekly_if[if_col],
                    orientation="h",
                    marker_color=weekly_if[tss_col],
                    marker_colorscale="Viridis",
                    text=[f"{v:.2f}" for v in weekly_if[if_col]],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Avg IF: %{x:.2f}<br>TSS: %{marker.color:.0f}<extra></extra>",
                )
            )
            fig_weekly_if.update_layout(
                xaxis_title="Average Intensity Factor",
                height=max(200, len(weekly_if) * 40),
                margin={"l": 100, "r": 60, "t": 20, "b": 20},
                showlegend=False,
                xaxis_range=[0, 1.2],
            )
            fig_weekly_if.add_vline(x=0.75, line_dash="dot", annotation_text="Endurance")
            fig_weekly_if.add_vline(x=0.85, line_dash="dot", annotation_text="Tempo")
            fig_weekly_if.add_vline(x=0.95, line_dash="dot", annotation_text="Threshold")
            st.plotly_chart(fig_weekly_if, use_container_width=True)
        else:
            st.info("No intensity data for this month.")


def render_trends_tab(
    df_activities: pd.DataFrame,
    selected_month: pd.Timestamp,
    selected_sports: list,
    metric_view: str,
    calculate_monthly_tid_fn,
) -> None:
    """
    Render the Trends tab with 6-month performance analysis.

    Args:
        df_activities: All activities DataFrame
        selected_month: Current month
        selected_sports: Selected sport types
        metric_view: "Moving" or "Raw"
        calculate_monthly_tid_fn: Function to calculate TID
    """
    st.subheader("6-Month Performance Trends")

    # Get last 6 months of data
    start_trend = selected_month - pd.DateOffset(months=5)
    df_trend = df_activities[
        (df_activities["month_start"] >= start_trend)
        & (df_activities["month_start"] <= selected_month)
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

        # Aggregate monthly metrics
        monthly_trend = (
            df_trend.groupby("month_start")
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
        monthly_trend["distance_km"] = monthly_trend["distance"] / 1000
        monthly_trend["hours"] = monthly_trend["moving_time"] / 3600
        monthly_trend["month_label"] = monthly_trend["month_start"].dt.strftime("%b %Y")

        col_vol, col_eff = st.columns(2)

        with col_vol:
            # Volume Trend: Distance + TSS
            fig_vol = make_subplots(specs=[[{"secondary_y": True}]])

            fig_vol.add_trace(
                go.Bar(
                    x=monthly_trend["month_label"],
                    y=monthly_trend["distance_km"],
                    name="Distance (km)",
                    marker_color="#3498db",
                ),
                secondary_y=False,
            )

            fig_vol.add_trace(
                go.Scatter(
                    x=monthly_trend["month_label"],
                    y=monthly_trend["training_stress_score"],
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
                    x=monthly_trend["month_label"],
                    y=monthly_trend["efficiency_factor"],
                    name="Efficiency Factor",
                    line=dict(color="#2ecc71", width=3),
                    mode="lines+markers",
                ),
                secondary_y=False,
            )

            fig_eff.add_trace(
                go.Scatter(
                    x=monthly_trend["month_label"],
                    y=monthly_trend["intensity_factor"],
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
            fig_eff.update_yaxes(title_text="EF", secondary_y=False)
            fig_eff.update_yaxes(title_text="Avg IF", secondary_y=True)
            st.plotly_chart(fig_eff, use_container_width=True)

        # Monthly TID Trend
        st.subheader("Monthly Training Intensity Distribution Trend")

        tid_trend_data = []
        for month in monthly_trend["month_start"]:
            df_m = df_trend[df_trend["month_start"] == month]
            tid = calculate_monthly_tid_fn(df_m, metric_view)
            tid_trend_data.append({
                "month": month.strftime("%b %Y"),
                "Z1 Low": tid["z1"],
                "Z2 Moderate": tid["z2"],
                "Z3 High": tid["z3"],
            })

        if tid_trend_data:
            df_tid_trend = pd.DataFrame(tid_trend_data)
            fig_tid_trend = go.Figure()
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["month"],
                    y=df_tid_trend["Z1 Low"],
                    name="Z1 Low",
                    marker_color="#808080",
                )
            )
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["month"],
                    y=df_tid_trend["Z2 Moderate"],
                    name="Z2 Moderate",
                    marker_color="#3498db",
                )
            )
            fig_tid_trend.add_trace(
                go.Bar(
                    x=df_tid_trend["month"],
                    y=df_tid_trend["Z3 High"],
                    name="Z3 High",
                    marker_color="#e74c3c",
                )
            )
            fig_tid_trend.update_layout(
                barmode="stack",
                title="Monthly Training Intensity Distribution",
                yaxis_title="% of Time",
                legend=dict(x=0, y=1.1, orientation="h"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_tid_trend, use_container_width=True)

        # ═══════════════════════════════════════════════════════════════════════
        # 6-Month CTL/ATL Evolution
        # ═══════════════════════════════════════════════════════════════════════
        st.divider()
        st.subheader("📊 Training Load Evolution (6 Months)")

        # Get daily training load from each activity
        df_load_trend = df_trend.copy().sort_values("start_date_local")

        has_ctl = "chronic_training_load" in df_load_trend.columns
        has_atl = "acute_training_load" in df_load_trend.columns
        has_tsb = "training_stress_balance" in df_load_trend.columns

        if has_ctl or has_atl:
            fig_ctl_atl = go.Figure()

            if has_ctl:
                fig_ctl_atl.add_trace(
                    go.Scatter(
                        x=df_load_trend["start_date_local"],
                        y=df_load_trend["chronic_training_load"],
                        name="CTL (Fitness)",
                        line=dict(color="#2ecc71", width=2),
                        mode="lines",
                        hovertemplate="%{x|%d %b %Y}<br>CTL: %{y:.0f}<extra></extra>",
                    )
                )

            if has_atl:
                fig_ctl_atl.add_trace(
                    go.Scatter(
                        x=df_load_trend["start_date_local"],
                        y=df_load_trend["acute_training_load"],
                        name="ATL (Fatigue)",
                        line=dict(color="#e74c3c", width=2),
                        mode="lines",
                        hovertemplate="%{x|%d %b %Y}<br>ATL: %{y:.0f}<extra></extra>",
                    )
                )

            if has_tsb:
                fig_ctl_atl.add_trace(
                    go.Scatter(
                        x=df_load_trend["start_date_local"],
                        y=df_load_trend["training_stress_balance"],
                        name="TSB (Form)",
                        line=dict(color="#3498db", width=1.5),
                        mode="lines",
                        fill="tozeroy",
                        fillcolor="rgba(52, 152, 219, 0.15)",
                        hovertemplate="%{x|%d %b %Y}<br>TSB: %{y:.0f}<extra></extra>",
                    )
                )
                fig_ctl_atl.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)
                fig_ctl_atl.add_hline(y=-10, line_dash="dot", line_color="orange", opacity=0.3)
                fig_ctl_atl.add_hline(y=20, line_dash="dot", line_color="green", opacity=0.3)

            fig_ctl_atl.update_layout(
                title="CTL / ATL / TSB Over 6 Months",
                xaxis_title="Date",
                yaxis_title="Training Load",
                legend=dict(x=0, y=1.1, orientation="h"),
                hovermode="x unified",
                height=400,
            )
            fig_ctl_atl.update_xaxes(tickformat="%d %b %Y")

            st.plotly_chart(fig_ctl_atl, use_container_width=True)
        else:
            st.info("No CTL/ATL data available for trend analysis.")

        # ═══════════════════════════════════════════════════════════════════════
        # Monthly Cumulative Volume Comparison
        # ═══════════════════════════════════════════════════════════════════════
        st.divider()
        st.subheader("📈 Monthly Volume Comparison")

        col_dist_comp, col_time_comp = st.columns(2)

        with col_dist_comp:
            # Monthly distance comparison bar chart
            fig_dist_comp = go.Figure()
            fig_dist_comp.add_trace(
                go.Bar(
                    x=monthly_trend["month_label"],
                    y=monthly_trend["distance_km"],
                    name="Distance",
                    marker_color=["#3498db" if m != selected_month else "#e74c3c" for m in monthly_trend["month_start"]],
                    text=[f"{v:.0f}" for v in monthly_trend["distance_km"]],
                    textposition="outside",
                    hovertemplate="%{x}<br>Distance: %{y:.1f} km<extra></extra>",
                )
            )
            # Add average line
            avg_dist = monthly_trend["distance_km"].mean()
            fig_dist_comp.add_hline(y=avg_dist, line_dash="dash", line_color="gray",
                                    annotation_text=f"Avg: {avg_dist:.0f} km")

            fig_dist_comp.update_layout(
                title="Monthly Distance",
                yaxis_title="Distance (km)",
                height=300,
                showlegend=False,
            )
            st.plotly_chart(fig_dist_comp, use_container_width=True)

        with col_time_comp:
            # Monthly time comparison bar chart
            fig_time_comp = go.Figure()
            fig_time_comp.add_trace(
                go.Bar(
                    x=monthly_trend["month_label"],
                    y=monthly_trend["hours"],
                    name="Time",
                    marker_color=["#2ecc71" if m != selected_month else "#e74c3c" for m in monthly_trend["month_start"]],
                    text=[f"{v:.1f}h" for v in monthly_trend["hours"]],
                    textposition="outside",
                    hovertemplate="%{x}<br>Time: %{y:.1f} hours<extra></extra>",
                )
            )
            # Add average line
            avg_time = monthly_trend["hours"].mean()
            fig_time_comp.add_hline(y=avg_time, line_dash="dash", line_color="gray",
                                    annotation_text=f"Avg: {avg_time:.1f}h")

            fig_time_comp.update_layout(
                title="Monthly Time",
                yaxis_title="Time (hours)",
                height=300,
                showlegend=False,
            )
            st.plotly_chart(fig_time_comp, use_container_width=True)

        # ═══════════════════════════════════════════════════════════════════════
        # Daily Activity Heatmap (6 months)
        # ═══════════════════════════════════════════════════════════════════════
        st.divider()
        st.subheader("🗓️ Activity Density (6 Months)")

        # Create daily aggregates for 6 months
        df_daily = df_trend.copy()
        df_daily["date"] = df_daily["start_date_local"].dt.date

        daily_agg = df_daily.groupby("date").agg({
            "training_stress_score": "sum",
            "distance": "sum",
            "id": "count"
        }).reset_index()
        daily_agg.columns = ["date", "tss", "distance", "count"]

        # Create full date range
        all_days = pd.date_range(start=start_trend, end=selected_month + pd.DateOffset(months=1) - pd.Timedelta(days=1), freq='D')
        full_dates = pd.DataFrame({"date": all_days.date})
        daily_full = full_dates.merge(daily_agg, on="date", how="left").fillna(0)

        # Add week/day info
        daily_full["date_ts"] = pd.to_datetime(daily_full["date"])
        daily_full["week"] = daily_full["date_ts"].dt.isocalendar().week
        daily_full["year_week"] = daily_full["date_ts"].dt.strftime("%Y-W%W")
        daily_full["day_of_week"] = daily_full["date_ts"].dt.dayofweek

        # Create heatmap pivoted by week
        heatmap_pivot = daily_full.pivot(index="day_of_week", columns="year_week", values="tss")
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        fig_heatmap = go.Figure()
        fig_heatmap.add_trace(
            go.Heatmap(
                z=heatmap_pivot.values,
                x=list(range(len(heatmap_pivot.columns))),
                y=day_labels,
                colorscale="YlOrRd",
                hovertemplate="Week %{x}<br>%{y}<br>TSS: %{z:.0f}<extra></extra>",
                showscale=True,
                colorbar=dict(title="TSS"),
            )
        )

        fig_heatmap.update_layout(
            title="Daily TSS Heatmap (6 Months)",
            xaxis_title="Week",
            height=250,
            margin={"l": 60, "r": 20, "t": 40, "b": 40},
        )
        fig_heatmap.update_xaxes(
            tickmode='array',
            tickvals=list(range(0, len(heatmap_pivot.columns), 4)),
            ticktext=[heatmap_pivot.columns[i] if i < len(heatmap_pivot.columns) else "" for i in range(0, len(heatmap_pivot.columns), 4)]
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    else:
        st.info("No trend data available.")


def render_activities_tab(
    df_month: pd.DataFrame,
    metric_view: str,
    format_duration_fn,
    settings,
) -> None:
    """
    Render the Activities tab with dataframe of monthly activities.

    Args:
        df_month: Current month activities
        metric_view: "Moving" or "Raw"
        format_duration_fn: Function to format duration
        settings: Settings object with gear names
    """
    st.subheader("Activities This Month")
    if not df_month.empty:
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
            if col not in df_month.columns:
                df_month[col] = None

        df_display = df_month[list(cols_map.keys())].rename(columns=cols_map).copy()
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
            "id": None,  # Hidden column for linking
        }

        st.dataframe(
            df_display,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
        )

        # Summary stats
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Activities", len(df_display))
        col2.metric("Total Distance", f"{df_display['Distance'].sum():.1f} km")
        col3.metric("Total TSS", f"{df_display['TSS'].sum():.0f}")
        col4.metric("Avg IF", f"{df_display['IF'].mean():.2f}" if df_display['IF'].notna().any() else "-")
    else:
        st.info("No activities this month.")
