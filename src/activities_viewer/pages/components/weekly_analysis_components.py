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
from activities_viewer.analytics.insights import generate_weekly_insights, render_insights

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
    Render KPI metrics section with hero and context metrics.

    Args:
        df_week: Current week activities
        df_prev_week: Previous week activities for comparison
        metric_view: "Moving" or "Raw"
        help_texts: Dictionary of help text strings
        format_duration_fn: Function to format duration
        get_metric_fn: Function to safely get metrics
    """
    # Calculate metrics
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

    # Get training load state from latest activity
    ctl = atl = tsb = acwr = None
    if not df_week.empty:
        latest_activity = df_week.sort_values("start_date", ascending=False).iloc[0]
        ctl = latest_activity.get("chronic_training_load", None)
        atl = latest_activity.get("acute_training_load", None)
        tsb = latest_activity.get("training_stress_balance", None)
        acwr = latest_activity.get("acwr", None)

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 1: HERO METRICS (3 columns, large, most important)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 📊 Week at a Glance")

    hero1, hero2, hero3 = st.columns(3)

    with hero1:
        tss_delta = f"{total_tss - prev_tss:+.0f}" if prev_tss else None
        st.metric(
            "💪 Training Load",
            f"{total_tss:.0f} TSS",
            delta=tss_delta,
            help="Total Training Stress Score this week. Typical range: 300-700 TSS/week."
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
            help="Total moving time this week."
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
    avg_np = get_metric_fn(df_week, "normalized_power", "mean")
    avg_if = get_metric_fn(df_week, "intensity_factor", "mean")
    avg_ef = get_metric_fn(df_week, "efficiency_factor", "mean")
    avg_vi = get_metric_fn(df_week, "variability_index", "mean")
    avg_fatigue = get_metric_fn(df_week, "fatigue_index", "mean")
    avg_hr = get_metric_fn(df_week, "average_hr", "mean")

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

    # ════════════════════════════════════════════════════════════════════════════
    # INSIGHTS & RECOMMENDATIONS
    # ════════════════════════════════════════════════════════════════════════════

    # Only show insights if we have valid training load data
    if pd.notna(ctl) and pd.notna(atl) and pd.notna(tsb) and pd.notna(acwr):
        st.divider()
        insights = generate_weekly_insights(
            df_week=df_week,
            ctl=ctl,
            atl=atl,
            tsb=tsb,
            acwr=acwr,
            weekly_tss=total_tss,
        )
        render_insights(insights)

    # Row 4: CP Model & Durability metrics
    st.divider()
    st.markdown("#### 💪 Power Profile & Durability")

    if not df_week.empty:
        latest_activity = df_week.sort_values("start_date", ascending=False).iloc[0]

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
    df_all_activities: pd.DataFrame = None,
    help_texts: dict = None,
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
        df_all_activities: All activities (for Section 2 calculations)
        help_texts: Dictionary of help text strings
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

    # Equipment Usage (Horizontal Bar)
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

        # Sort by distance for better visualization
        gear_stats = gear_stats.sort_values("Dist (km)")

        fig_gear = px.bar(
            gear_stats,
            y="Gear",
            x="Dist (km)",
            color="Count",
            orientation="h",
            title="Distance by Equipment",
            color_continuous_scale="Blues",
        )
        fig_gear.update_layout(height=300)
        st.plotly_chart(fig_gear, use_container_width=True)
    else:
        st.info("No gear data available.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2: New Physiological Metrics
    # ═══════════════════════════════════════════════════════════════════════════

    if help_texts is not None and df_all_activities is not None:
        st.divider()

        # Section 2.1: Recovery & Readiness
        with st.expander("🔋 Recovery & Readiness", expanded=False):
            render_recovery_readiness_section(df_week, df_all_activities, selected_week, help_texts)

        st.divider()

        # Section 2.2: Training Type Distribution
        with st.expander("🎯 Training Type Distribution", expanded=False):
            render_training_type_distribution(df_week, help_texts)

        st.divider()

        # Section 2.3: Progressive Overload
        with st.expander("📈 Progressive Overload", expanded=False):
            render_progressive_overload(df_week, df_all_activities, selected_week, help_texts)

        st.divider()

        # Section 2.4: Intensity-Specific Volume
        with st.expander("⏱️ Intensity-Specific Volume", expanded=False):
            render_intensity_specific_volume(df_week, help_texts)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2.1: Recovery & Readiness
# ═══════════════════════════════════════════════════════════════════════════════


def render_recovery_readiness_section(
    df_week: pd.DataFrame,
    df_all_activities: pd.DataFrame,
    selected_week: pd.Timestamp,
    help_texts: dict,
) -> None:
    """
    Render Recovery & Readiness section with Monotony, Strain, and Rest Days.

    Args:
        df_week: Current week activities
        df_all_activities: All activities for calculating 4-week average
        selected_week: Start of the week (Monday)
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 💤 Recovery & Readiness")

    # Calculate daily TSS
    tss_col = "training_stress_score"
    if tss_col not in df_week.columns:
        st.info("TSS data not available for recovery analysis.")
        return

    # Create complete week with all 7 days
    week_start = selected_week.normalize() if isinstance(selected_week, pd.Timestamp) else pd.Timestamp(selected_week)
    week_dates = pd.date_range(start=week_start, periods=7, freq='D')

    # Group activities by date and sum TSS
    df_week_copy = df_week.copy()
    df_week_copy["date_local"] = df_week_copy["start_date_local"].dt.date
    daily_tss = df_week_copy.groupby("date_local")[tss_col].sum()

    # Create full week with 0 for days without activities
    daily_tss_full = pd.Series(0.0, index=week_dates.date)
    daily_tss_full.update(daily_tss)
    daily_tss_values = daily_tss_full.values

    # Calculate Monotony Index
    if len(daily_tss_values) > 1 and daily_tss_values.std() > 0:
        monotony = daily_tss_values.mean() / daily_tss_values.std()
    else:
        monotony = 0.0

    # Calculate Strain Index
    weekly_tss = daily_tss_values.sum()
    strain = weekly_tss * monotony

    # Calculate Rest Days (TSS < 20)
    rest_days = (daily_tss_values < 20).sum()

    # 3-column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "Rest Days",
            f"{rest_days} / 7",
            help_texts.get("rest_days", "Days with no activity or TSS < 20")
        )
        if rest_days >= 2:
            st.success("✅ Adequate recovery time")
        elif rest_days == 1:
            st.warning("⚠️ Consider more rest")
        else:
            st.error("🔴 Insufficient recovery")

    with col2:
        render_metric(
            col2,
            "Monotony Index",
            f"{monotony:.2f}",
            help_texts.get("monotony", "Mean daily TSS / Standard deviation. Lower = more varied training")
        )
        if monotony < 1.5:
            st.success("✅ Low risk - good variety")
        elif monotony < 2.0:
            st.warning("⚠️ Monitor - moderate risk")
        else:
            st.error("🔴 High risk - too repetitive")

    with col3:
        render_metric(
            col3,
            "Strain Index",
            f"{strain:.0f}",
            help_texts.get("strain", "Weekly TSS × Monotony. Combines load and variation")
        )
        if strain < 3000:
            st.success("✅ Manageable load")
        elif strain < 6000:
            st.warning("⚠️ Moderate strain")
        else:
            st.error("🔴 High strain - recovery critical")

    # Interpretation guide
    with st.expander("📊 Recovery Metrics Guide"):
        st.markdown("""
        **Monotony Index:**
        - <1.5: ✅ Safe - Good training variety
        - 1.5-2.0: ⚠️ Monitor - Moderate risk of overtraining
        - >2.0: 🔴 High risk - Training too repetitive

        **Strain Index:**
        - <3000: ✅ Appropriate load
        - 3000-6000: ⚠️ Moderate - Monitor recovery
        - >6000: 🔴 High - Prioritize recovery

        **Rest Days:**
        - 2+: ✅ Adequate recovery for most athletes
        - 1: ⚠️ May need more rest depending on intensity
        - 0: 🔴 High injury/overtraining risk
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2.2: Training Type Distribution
# ═══════════════════════════════════════════════════════════════════════════════


def render_training_type_distribution(
    df_week: pd.DataFrame,
    help_texts: dict,
) -> None:
    """
    Render Training Type Distribution based on Intensity Factor (IF).

    Args:
        df_week: Current week activities
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 🎯 Training Type Distribution")

    # Check if IF data is available
    if "intensity_factor" not in df_week.columns or df_week["intensity_factor"].isna().all():
        st.info("Intensity Factor (IF) data not available for training type classification.")
        return

    # Classify rides by IF
    def classify_training_type(if_value):
        if pd.isna(if_value):
            return "Unknown"
        elif if_value < 0.65:
            return "💤 Recovery"
        elif if_value < 0.75:
            return "🚴 Endurance"
        elif if_value < 0.85:
            return "🔥 Tempo"
        elif if_value < 0.95:
            return "⚡ Threshold"
        else:
            return "🚀 VO2max+"

    df_week_copy = df_week.copy()
    df_week_copy["training_type"] = df_week_copy["intensity_factor"].apply(classify_training_type)

    # Count rides by type
    type_counts = df_week_copy["training_type"].value_counts()
    total_rides = len(df_week_copy[df_week_copy["training_type"] != "Unknown"])

    if total_rides == 0:
        st.info("No rides with valid IF data this week.")
        return

    # Create ordered categories
    type_order = ["💤 Recovery", "🚴 Endurance", "🔥 Tempo", "⚡ Threshold", "🚀 VO2max+"]
    type_data = []

    for ttype in type_order:
        count = type_counts.get(ttype, 0)
        percentage = (count / total_rides * 100) if total_rides > 0 else 0
        if count > 0:
            type_data.append({
                "Type": ttype,
                "Count": count,
                "Percentage": percentage
            })

    if type_data:
        # Create stacked bar chart
        import plotly.graph_objects as go

        fig = go.Figure()

        colors = {
            "💤 Recovery": "#95a5a6",
            "🚴 Endurance": "#2ecc71",
            "🔥 Tempo": "#f39c12",
            "⚡ Threshold": "#e74c3c",
            "🚀 VO2max+": "#9b59b6"
        }

        for item in type_data:
            fig.add_trace(go.Bar(
                name=item["Type"],
                x=[item["Percentage"]],
                y=["Training Week"],
                orientation='h',
                marker_color=colors.get(item["Type"], "#3498db"),
                text=f"{item['Count']} ({item['Percentage']:.0f}%)",
                textposition='auto',
                hovertemplate=f"<b>{item['Type']}</b><br>{item['Count']} rides ({item['Percentage']:.1f}%)<extra></extra>"
            ))

        fig.update_layout(
            barmode='stack',
            height=150,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Percentage of Rides",
            yaxis=dict(showticklabels=False)
        )
        fig.update_xaxes(range=[0, 100])

        st.plotly_chart(fig, use_container_width=True)

        # Show breakdown table
        st.markdown("**Training Type Breakdown:**")
        for item in type_data:
            st.markdown(f"- {item['Type']}: **{item['Count']} rides** ({item['Percentage']:.1f}%)")

    # Training type guide
    with st.expander("📊 Training Type Classification (IF-based)"):
        st.markdown("""
        **Recovery (IF < 0.65)** 💤
        - Active recovery, easy spin
        - Focus: Muscle repair, blood flow

        **Endurance (IF 0.65-0.75)** 🚴
        - Aerobic base building
        - Focus: Mitochondrial adaptation, fat oxidation

        **Tempo (IF 0.75-0.85)** 🔥
        - Sweet spot training
        - Focus: Lactate clearance, muscular endurance

        **Threshold (IF 0.85-0.95)** ⚡
        - FTP/CP intervals
        - Focus: Lactate threshold improvement

        **VO2max+ (IF > 0.95)** 🚀
        - High intensity intervals
        - Focus: Maximal aerobic power, anaerobic capacity
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2.3: Progressive Overload
# ═══════════════════════════════════════════════════════════════════════════════


def render_progressive_overload(
    df_week: pd.DataFrame,
    df_all_activities: pd.DataFrame,
    selected_week: pd.Timestamp,
    help_texts: dict,
) -> None:
    """
    Render Progressive Overload section comparing this week to 4-week average.

    Args:
        df_week: Current week activities
        df_all_activities: All activities for calculating 4-week average
        selected_week: Start of the week (Monday)
        help_texts: Dictionary of help text strings
    """
    st.markdown("### 📈 Progressive Overload")

    tss_col = "training_stress_score"
    if tss_col not in df_week.columns or tss_col not in df_all_activities.columns:
        st.info("TSS data not available for progressive overload analysis.")
        return

    # This week TSS
    this_week_tss = df_week[tss_col].sum()

    # Calculate 4-week average TSS (excluding current week)
    week_start = selected_week.normalize() if isinstance(selected_week, pd.Timestamp) else pd.Timestamp(selected_week)
    week_end = week_start + pd.Timedelta(days=7)

    # Get last 4 weeks before current week
    four_weeks_ago = week_start - pd.Timedelta(days=28)
    df_previous_4weeks = df_all_activities[
        (df_all_activities["start_date_local"] >= four_weeks_ago) &
        (df_all_activities["start_date_local"] < week_start)
    ]

    if len(df_previous_4weeks) > 0:
        # Group by week and sum TSS
        df_previous_4weeks_copy = df_previous_4weeks.copy()
        df_previous_4weeks_copy["week_start"] = df_previous_4weeks_copy["start_date_local"].dt.to_period('W').apply(lambda x: x.start_time)
        weekly_tss = df_previous_4weeks_copy.groupby("week_start")[tss_col].sum()
        four_week_avg_tss = weekly_tss.mean()
    else:
        four_week_avg_tss = 0

    # Calculate progression percentage
    if four_week_avg_tss > 0:
        progression_pct = ((this_week_tss - four_week_avg_tss) / four_week_avg_tss) * 100
    else:
        progression_pct = 0

    # 3-column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "This Week TSS",
            f"{this_week_tss:.0f}",
            help_texts.get("this_week_tss", "Total Training Stress Score for the current week")
        )

    with col2:
        render_metric(
            col2,
            "4-Week Avg TSS",
            f"{four_week_avg_tss:.0f}",
            help_texts.get("four_week_avg_tss", "Average weekly TSS over the previous 4 weeks")
        )

    with col3:
        delta_symbol = "📈" if progression_pct > 0 else "📉" if progression_pct < 0 else "➡️"
        render_metric(
            col3,
            "Progression",
            f"{delta_symbol} {progression_pct:+.1f}%",
            help_texts.get("progression", "Week-over-week TSS change. Optimal: 3-10% increase")
        )

        if 3 <= progression_pct <= 10:
            st.success("✅ Optimal progression")
        elif progression_pct > 10:
            st.warning("⚠️ Above target - monitor recovery")
        elif progression_pct < -10:
            st.info("💤 Recovery week detected")
        else:
            st.info("➡️ Maintaining load")

    # Progression guide
    with st.expander("📊 Progressive Overload Guide"):
        st.markdown("""
        **Optimal Progression:**
        - **+3% to +10%**: ✅ Safe, sustainable load increase
        - **+10% to +20%**: ⚠️ Above target - ensure adequate recovery
        - **>+20%**: 🔴 High risk - consider reducing load
        - **-10% to +3%**: ➡️ Maintenance phase
        - **<-10%**: 💤 Recovery/taper week

        **Guidelines:**
        - Increase load gradually (rule of thumb: <10% per week)
        - Plan recovery weeks every 3-4 weeks (20-40% reduction)
        - Monitor TSB and subjective fatigue
        - Adjust based on response to training
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2.4: Intensity-Specific Volume
# ═══════════════════════════════════════════════════════════════════════════════


def render_intensity_specific_volume(
    df_week: pd.DataFrame,
    help_texts: dict,
) -> None:
    """
    Render Intensity-Specific Volume section with Z2, Sweet Spot, and VO2max time.

    Args:
        df_week: Current week activities
        help_texts: Dictionary of help text strings
    """
    st.markdown("### ⏱️ Intensity-Specific Volume")

    # Calculate total moving time
    total_time_seconds = df_week["moving_time"].sum() if "moving_time" in df_week.columns else 0

    if total_time_seconds == 0:
        st.info("No activity data available for intensity-specific volume analysis.")
        return

    # Z2 Volume (from power_z2_percentage)
    z2_time_seconds = 0
    if "power_z2_percentage" in df_week.columns and "moving_time" in df_week.columns:
        df_week_copy = df_week.copy()
        df_week_copy["z2_time"] = (df_week_copy["power_z2_percentage"] / 100) * df_week_copy["moving_time"]
        z2_time_seconds = df_week_copy["z2_time"].sum()

    # Sweet Spot time (pre-computed in StravaAnalyzer)
    ss_time_seconds = 0
    if "time_sweet_spot" in df_week.columns:
        ss_time_seconds = df_week["time_sweet_spot"].sum()

    # VO2max time (time above 90% FTP, pre-computed in StravaAnalyzer)
    vo2max_time_seconds = 0
    if "time_above_90_ftp" in df_week.columns:
        vo2max_time_seconds = df_week["time_above_90_ftp"].sum()

    # Format durations
    def format_time(seconds):
        if seconds == 0:
            return "0 min"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}min"
        else:
            return f"{minutes}min"

    # Calculate percentages
    z2_pct = (z2_time_seconds / total_time_seconds * 100) if total_time_seconds > 0 else 0
    ss_pct = (ss_time_seconds / total_time_seconds * 100) if total_time_seconds > 0 else 0
    vo2max_pct = (vo2max_time_seconds / total_time_seconds * 100) if total_time_seconds > 0 else 0

    # 3-column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "Z2 Volume",
            format_time(z2_time_seconds),
            help_texts.get("z2_volume", "Time in Zone 2 (56-75% FTP). Aerobic base building")
        )
        st.caption(f"**{z2_pct:.1f}%** of total time")

    with col2:
        render_metric(
            col2,
            "Sweet Spot Time",
            format_time(ss_time_seconds),
            help_texts.get("sweet_spot_time", "Time at 88-94% FTP. Highly effective for FTP improvement")
        )
        st.caption(f"**{ss_pct:.1f}%** of total time")

    with col3:
        render_metric(
            col3,
            "VO2max Time",
            format_time(vo2max_time_seconds),
            help_texts.get("vo2max_time", "Time above 90% FTP. High intensity training for maximal aerobic power")
        )
        st.caption(f"**{vo2max_pct:.1f}%** of total time")

    # Intensity distribution guide
    with st.expander("📊 Intensity-Specific Training Guide"):
        st.markdown("""
        **Z2 (Aerobic Endurance) - 56-75% FTP:**
        - Primary adaptation: Mitochondrial density, fat oxidation
        - Recommended: 60-80% of total weekly volume for base building
        - Benefits: Aerobic base, recovery, metabolic efficiency

        **Sweet Spot - 88-94% FTP:**
        - Primary adaptation: FTP improvement, lactate clearance
        - Recommended: 10-20% of weekly volume during build phase
        - Benefits: Time-efficient FTP gains, muscular endurance

        **VO2max - >90% FTP:**
        - Primary adaptation: Maximal aerobic power, anaerobic capacity
        - Recommended: 5-10% of weekly volume
        - Benefits: Peak power, race-specific fitness

        **Polarized Model (80/20 Rule):**
        - 80% low intensity (Z1-Z2)
        - 20% high intensity (Threshold, VO2max)
        - Minimal moderate intensity (Tempo)
        """)


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
