"""
Year Overview Page Components.

Extracted rendering functions for the year overview page tabs.
Each function handles a specific UI section to keep main() clean.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from activities_viewer.pages.components.activity_detail_components import render_metric


def render_year_selector(available_years: list) -> tuple:
    """
    Render year selector and metric view in sidebar.

    Args:
        available_years: List of available years

    Returns:
        Tuple of (selected_year, metric_view)
    """
    with st.sidebar:
        st.header("Filters")
        selected_year = st.selectbox("Select Year", available_years, index=0)

        # Metric view toggle
        st.subheader("Metric View")
        metric_view = st.radio(
            "Analysis Type",
            options=["Moving Time", "Raw Time"],
            index=0,
            help="Moving Time excludes stops; Raw Time includes all elapsed time",
        )

    return selected_year, metric_view


def render_sport_filter(df: pd.DataFrame) -> list:
    """
    Render sport type filter in sidebar.

    Args:
        df: DataFrame with activities

    Returns:
        List of selected sport types
    """
    with st.sidebar:
        available_sports = sorted(df["sport_type"].unique().tolist())
        selected_sports = st.multiselect(
            "Sport Types",
            available_sports,
            default=available_sports,
            help="Filter by sport type",
        )

    return selected_sports


def render_kpi_section(
    df: pd.DataFrame,
    df_prev: pd.DataFrame,
    metric_view: str,
    help_texts: dict,
    safe_mean_fn,
    safe_sum_fn,
) -> None:
    """
    Render KPI section with volume, intensity, and efficiency metrics.

    Args:
        df: Current year activities
        df_prev: Previous year activities
        metric_view: "Moving Time" or "Raw Time"
        help_texts: Dictionary of help text strings
        safe_mean_fn: Function to safely calculate mean
        safe_sum_fn: Function to safely calculate sum
    """

    st.subheader("📈 Key Performance Indicators")

    # Calculate aggregates
    total_dist = safe_sum_fn(df["distance"]) / 1000
    total_time = safe_sum_fn(df["moving_time"])
    total_elev = safe_sum_fn(df["total_elevation_gain"])
    count = len(df)
    total_tss = safe_sum_fn(df["training_stress_score"])
    avg_np = safe_mean_fn(df["normalized_power"])
    avg_if = safe_mean_fn(df["intensity_factor"])
    avg_ef = safe_mean_fn(df["efficiency_factor"])
    avg_fatigue = safe_mean_fn(df["fatigue_index"])

    # Calculate deltas
    delta_dist = delta_time = delta_elev = delta_count = delta_tss = None
    prev_tss = 0

    if not df_prev.empty:
        prev_dist = safe_sum_fn(df_prev["distance"]) / 1000
        prev_time = safe_sum_fn(df_prev["moving_time"])
        prev_elev = safe_sum_fn(df_prev["total_elevation_gain"])
        prev_count = len(df_prev)
        prev_tss = safe_sum_fn(df_prev["training_stress_score"])

        delta_dist = f"{total_dist - prev_dist:+,.0f} km"
        delta_time = f"{(total_time - prev_time) / 3600:+,.0f} h"
        delta_elev = f"{total_elev - prev_elev:+,.0f} m"
        delta_count = f"{count - prev_count:+d}"
        delta_tss = f"{total_tss - prev_tss:+,.0f}"

    # Get latest activity for training load state
    ctl = atl = tsb = acwr = None
    if not df.empty:
        latest_activity = df.sort_values("start_date", ascending=False).iloc[0]
        ctl = latest_activity.get("chronic_training_load", None)
        atl = latest_activity.get("acute_training_load", None)
        tsb = latest_activity.get("training_stress_balance", None)
        acwr = latest_activity.get("acwr", None)

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 1: HERO METRICS (3 columns, large, most important)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("##### 🎯 Year at a Glance")

    hero1, hero2, hero3 = st.columns(3)

    with hero1:
        tss_delta = f"{total_tss - prev_tss:+,.0f}" if prev_tss else None
        st.metric(
            "💪 Total Training Load",
            f"{total_tss:,.0f} TSS",
            delta=tss_delta,
            help="Total Training Stress Score accumulated this year. Higher = more training volume."
        )

    with hero2:
        ctl_value = f"{ctl:.0f}" if pd.notna(ctl) else "-"
        ctl_status = (
            "Building" if pd.notna(ctl) and ctl < 50 else
            "Consistent" if pd.notna(ctl) and ctl < 100 else
            "High" if pd.notna(ctl) and ctl < 150 else
            "Elite" if pd.notna(ctl) else "N/A"
        )
        st.metric(
            "📊 Current Fitness (CTL)",
            ctl_value,
            delta=ctl_status,
            delta_color="off",
            help="42-day exponentially weighted training load. Represents your current fitness level."
        )

    with hero3:
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
            help="Training Stress Balance = CTL - ATL. Indicates freshness for performance."
        )

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # TIER 2: CONTEXT METRICS (volume and secondary metrics, smaller columns)
    # ═══════════════════════════════════════════════════════════════════════════
    st.caption("📊 Volume & Efficiency Details")

    col1, col2, col3, col4, col5 = st.columns(5)
    render_metric(col1, "🚴 Distance", f"{total_dist:,.0f} km", delta_dist)
    render_metric(col2, "⏱️ Time", f"{total_time / 3600:,.0f} h", delta_time)
    render_metric(col3, "⛰️ Elevation", f"{total_elev:,.0f} m", delta_elev)
    render_metric(col4, "📝 Activities", f"{count}", delta_count)
    render_metric(col5, "⚡ Avg NP", f"{avg_np:.0f} W" if avg_np else "-")

    col6, col7, col8, col9, col10 = st.columns(5)
    render_metric(col6, "📊 Avg IF", f"{avg_if:.2f}" if avg_if else "-", help_texts.get("intensity_factor", ""))
    render_metric(col7, "🔋 Avg EF", f"{avg_ef:.2f}" if avg_ef else "-", help_texts.get("efficiency_factor", ""))
    render_metric(col8, "😓 Fatigue Idx", f"{avg_fatigue:.1f}%" if avg_fatigue else "-", help_texts.get("fatigue_index", ""))

    # ATL and ACWR in context tier
    atl_value = f"{atl:.0f}" if pd.notna(atl) else "-"
    acwr_value = f"{acwr:.2f}" if pd.notna(acwr) else "-"
    acwr_status = (
        "Safe ✅" if pd.notna(acwr) and 0.8 <= acwr <= 1.3 else
        "Caution ⚠️" if pd.notna(acwr) and acwr > 1.3 else
        "Low 📉" if pd.notna(acwr) else ""
    )
    render_metric(col9, "⚡ ATL (Fatigue)", atl_value, help_texts.get("acute_training_load", ""))
    render_metric(col10, "⚠️ ACWR", f"{acwr_value} {acwr_status}", help_texts.get("acwr", ""))

    # Training State Summary (if we have data)
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
        else:
            state = "🔴 Overreached - Recovery needed"
            state_color = "red"

        st.markdown(f"**Year-End Training State:** <span style='color:{state_color}'>{state}</span>", unsafe_allow_html=True)

    # Row 4: CP Model & Durability visualization
    st.divider()
    st.markdown("#### 💪 Power Profile & Durability")

    # CP model metrics (latest values)
    if not df.empty:
        latest_cp = df.sort_values("start_date", ascending=False).iloc[0]
        cp = latest_cp.get("cp", None)
        w_prime = latest_cp.get("w_prime", None)
        r_squared = latest_cp.get("cp_r_squared", None)
        aei = latest_cp.get("aei", None)

        # Durability metrics (year average)
        avg_sustainability = safe_mean_fn(df["power_sustainability_index"])
        avg_variability = safe_mean_fn(df["variability_index"])
        avg_fatigue_idx = safe_mean_fn(df["fatigue_index"])
        avg_decoupling = safe_mean_fn(df["power_hr_decoupling"])

        # Power Profile row with render_metric
        if any(pd.notna(x) for x in [cp, w_prime, r_squared, aei]):
            col1, col2, col3, col4 = st.columns(4)

            # CP (Critical Power)
            cp_value = f"{cp:.0f}W" if pd.notna(cp) else "-"
            cp_help = "Maximum sustained power for efforts >3 min. Category: " + (
                "Developing - Early stage training" if pd.notna(cp) and cp < 200 else
                "Fit - Solid cyclist" if pd.notna(cp) and cp < 300 else
                "Very Fit - Competitive fitness" if pd.notna(cp) and cp < 400 else
                "Elite - Professional level" if pd.notna(cp) else "N/A"
            )
            render_metric(col1, "⚡ CP (Power)", cp_value, cp_help)

            # W' (Anaerobic Capacity)
            w_prime_value = f"{w_prime/1000:.1f}kJ" if pd.notna(w_prime) else "-"
            w_prime_kj = w_prime / 1000 if pd.notna(w_prime) else None
            w_prime_help = "Anaerobic work capacity above CP. Capacity: " + (
                "Low - Build through intervals" if pd.notna(w_prime_kj) and w_prime_kj < 15 else
                "Average - Typical endurance cyclist" if pd.notna(w_prime_kj) and w_prime_kj < 25 else
                "High - Strong sprint ability" if pd.notna(w_prime_kj) else "N/A"
            )
            render_metric(col2, "💥 W' (Anaerobic)", w_prime_value, w_prime_help)

            # R² (Model Fit)
            r2_value = f"{r_squared:.3f}" if pd.notna(r_squared) else "-"
            r2_help = "CP model goodness of fit (0-1). Quality: " + (
                "Fair - Use with caution" if pd.notna(r_squared) and r_squared <= 0.90 else
                "Good - Reliable estimates" if pd.notna(r_squared) and r_squared <= 0.95 else
                "Excellent - Very reliable" if pd.notna(r_squared) else "N/A"
            )
            render_metric(col3, "📊 R² (Fit)", r2_value, r2_help)

            # AEI (Aerobic Efficiency)
            aei_value = f"{aei:.2f}" if pd.notna(aei) else "-"
            aei_help = "Power per heartbeat. Profile: " + (
                "Very Aerobic - Endurance focused" if pd.notna(aei) and aei > 0.85 else
                "Aerobic - Balanced athlete" if pd.notna(aei) and aei > 0.70 else
                "Balanced - Mixed strengths" if pd.notna(aei) else "N/A"
            )
            render_metric(col4, "❤️ AEI (Efficiency)", aei_value, aei_help)
        else:
            st.info("No power profile data available")

        # Durability section with metrics and radar chart
        st.markdown("**Durability Metrics (Year Avg)**")

        if any(pd.notna(x) for x in [avg_sustainability, avg_variability, avg_fatigue_idx, avg_decoupling]):
            col_metrics, col_radar = st.columns([1, 1])

            with col_metrics:
                # Durability metrics as render_metric
                d1, d2 = st.columns(2)
                d3, d4 = st.columns(2)

                sus_value = f"{avg_sustainability:.1f}%" if pd.notna(avg_sustainability) else "-"
                sus_help = "Ability to maintain power. >90% excellent, >75% good"
                render_metric(d1, "💪 Sustainability", sus_value, sus_help)

                vi_value = f"{avg_variability:.2f}" if pd.notna(avg_variability) else "-"
                vi_help = "Pacing consistency (1.0=perfect). 1.05-1.10 steady"
                render_metric(d2, "📊 Variability (VI)", vi_value, vi_help)

                fatigue_value = f"{avg_fatigue_idx:.1f}%" if pd.notna(avg_fatigue_idx) else "-"
                fatigue_help = "Power drop over activity. 0-5% excellent, >15% poor"
                render_metric(d3, "🔋 Fatigue Index", fatigue_value, fatigue_help)

                decouple_value = f"{avg_decoupling:.1f}%" if pd.notna(avg_decoupling) else "-"
                decouple_help = "Aerobic fitness indicator. 0-3% excellent, >8% poor"
                render_metric(d4, "❤️ Decoupling", decouple_value, decouple_help)

            with col_radar:
                # Durability radar chart
                # Normalize values to 0-100 scale for radar chart
                sustainability_norm = avg_sustainability if pd.notna(avg_sustainability) else 0
                variability_norm = (2.0 - avg_variability) * 50 if pd.notna(avg_variability) else 0  # Invert: lower is better
                fatigue_norm = 100 - avg_fatigue_idx if pd.notna(avg_fatigue_idx) else 0  # Invert: lower is better
                decoupling_norm = 100 - (avg_decoupling * 2) if pd.notna(avg_decoupling) else 0  # Invert: lower is better

                fig_dur = go.Figure()
                fig_dur.add_trace(go.Scatterpolar(
                    r=[sustainability_norm, variability_norm, fatigue_norm, decoupling_norm],
                    theta=['Sustainability', 'Pacing', 'Endurance', 'Aerobic'],
                    fill='toself',
                    name='Durability',
                    line_color='#3498db',
                    fillcolor='rgba(52, 152, 219, 0.3)',
                ))

                fig_dur.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )
                    ),
                    height=250,
                    margin=dict(l=40, r=40, t=20, b=20),
                    showlegend=False
                )

                st.plotly_chart(fig_dur, use_container_width=True)
        else:
            st.info("No durability data available")


def render_power_curve_section(df: pd.DataFrame, help_texts: dict) -> None:
    """
    Render power curve PRs section with best efforts for the year.

    Args:
        df: Year activities
        help_texts: Dictionary of help text strings
    """
    st.subheader("🏆 Power Curve PRs")

    with st.expander("ℹ️ Understanding Power Curve", expanded=False):
        st.markdown(help_texts.get("power_curve", ""))

    # Power curve durations and their column names
    power_curve_fields = [
        ("5s", "power_curve_5sec"),
        ("10s", "power_curve_10sec"),
        ("30s", "power_curve_30sec"),
        ("1min", "power_curve_1min"),
        ("2min", "power_curve_2min"),
        ("5min", "power_curve_5min"),
        ("10min", "power_curve_10min"),
        ("20min", "power_curve_20min"),
        ("30min", "power_curve_30min"),
        ("1hr", "power_curve_1hr"),
    ]

    # Get PRs for each duration
    prs = []
    for label, col in power_curve_fields:
        if col in df.columns:
            valid_data = df[df[col].notna()]
            if not valid_data.empty:
                max_idx = valid_data[col].idxmax()
                max_power = valid_data.loc[max_idx, col]
                activity_name = valid_data.loc[max_idx, "name"]
                activity_date = valid_data.loc[max_idx, "start_date_local"]
                prs.append(
                    {
                        "Duration": label,
                        "Power (W)": int(max_power) if pd.notna(max_power) else None,
                        "Activity": activity_name,
                        "Date": activity_date.strftime("%Y-%m-%d")
                        if pd.notna(activity_date)
                        else "",
                    }
                )

    if prs:
        pr_df = pd.DataFrame(prs)
        valid_prs = pr_df[pr_df["Power (W)"].notna()]

        col_pr1, col_pr2 = st.columns([2, 1])

        with col_pr1:
            # Power curve visualization
            if not valid_prs.empty:
                fig_pc = go.Figure()
                fig_pc.add_trace(
                    go.Bar(
                        x=valid_prs["Duration"],
                        y=valid_prs["Power (W)"],
                        marker_color="#e74c3c",
                        text=valid_prs["Power (W)"],
                        textposition="outside",
                        hovertemplate="<b>%{x}</b><br>Power: %{y}W<extra></extra>",
                    )
                )
                fig_pc.update_layout(
                    title="Power Curve - Best Efforts",
                    xaxis_title="Duration",
                    yaxis_title="Power (W)",
                    showlegend=False,
                )
                st.plotly_chart(fig_pc, width="stretch")

        with col_pr2:
            st.markdown("**Personal Records**")
            # Display PRs in a clean table
            display_df = valid_prs[["Duration", "Power (W)", "Date"]].copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No power curve data available.")


def render_tid_section(
    df: pd.DataFrame,
    metric_view: str,
    calculate_time_weighted_tid_fn,
    safe_mean_fn,
    help_texts: dict,
    selected_year: int,
) -> None:
    """
    Render Training Intensity Distribution analysis section.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
        calculate_time_weighted_tid_fn: Function to calculate TID
        safe_mean_fn: Function to safely calculate mean
        help_texts: Dictionary of help text strings
        selected_year: Current year for display
    """

    st.subheader("🎯 Training Intensity Distribution")

    with st.expander("ℹ️ Understanding TID", expanded=False):
        st.markdown(help_texts.get("tid", ""))
        st.markdown(help_texts.get("polarization_index", ""))

    # Calculate yearly TID
    yearly_tid = calculate_time_weighted_tid_fn(df, metric_view)

    col_tid1, col_tid2 = st.columns([1, 2])

    with col_tid1:
        # TID horizontal bar chart (consistent with other pages)
        if yearly_tid["z1"] > 0 or yearly_tid["z2"] > 0 or yearly_tid["z3"] > 0:
            tid_data = ["Z1 Low", "Z2 Moderate", "Z3 High"]
            tid_values = [yearly_tid["z1"], yearly_tid["z2"], yearly_tid["z3"]]
            tid_colors = ["#2ecc71", "#f1c40f", "#e74c3c"]

            fig_tid = go.Figure()
            fig_tid.add_trace(
                go.Bar(
                    y=tid_data,
                    x=tid_values,
                    orientation="h",
                    marker_color=tid_colors,
                    text=[f"{v:.1f}%" for v in tid_values],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>%{x:.1f}% of time<extra></extra>",
                )
            )
            fig_tid.update_layout(
                title=f"Yearly TID ({selected_year})",
                xaxis_title="% of Time",
                height=200,
                margin={"l": 100, "r": 60, "t": 40, "b": 40},
                showlegend=False,
            )
            st.plotly_chart(fig_tid, use_container_width=True)

            # TID Summary
            total_tid = sum(tid_values)
            if total_tid > 0:
                z1_ratio = yearly_tid["z1"] / total_tid * 100
                z3_ratio = yearly_tid["z3"] / total_tid * 100
                if z1_ratio > 75 and z3_ratio > 10:
                    st.success("✅ Polarized distribution - ideal for endurance")
                elif z1_ratio < 60:
                    st.warning("⚠️ Too much moderate intensity - consider polarizing")
                else:
                    st.info("ℹ️ Balanced intensity distribution")
        else:
            st.info("No TID data available.")

    with col_tid2:
        # Monthly TID trends
        df_copy = df.copy()
        df_copy["month"] = (
            pd.to_datetime(df_copy["start_date_local"], utc=True)
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        monthly_tid = (
            df_copy.groupby("month")
            .apply(
                lambda x: pd.Series(calculate_time_weighted_tid_fn(x, metric_view)),
                include_groups=False,
            )
            .reset_index()
        )

        if not monthly_tid.empty and "z1" in monthly_tid.columns:
            fig_monthly_tid = go.Figure()
            fig_monthly_tid.add_trace(
                go.Bar(
                    x=monthly_tid["month"],
                    y=monthly_tid["z1"],
                    name="Zone 1 (Low)",
                    marker_color="#2ecc71",
                )
            )
            fig_monthly_tid.add_trace(
                go.Bar(
                    x=monthly_tid["month"],
                    y=monthly_tid["z2"],
                    name="Zone 2 (Moderate)",
                    marker_color="#f1c40f",
                )
            )
            fig_monthly_tid.add_trace(
                go.Bar(
                    x=monthly_tid["month"],
                    y=monthly_tid["z3"],
                    name="Zone 3 (High)",
                    marker_color="#e74c3c",
                )
            )
            fig_monthly_tid.update_layout(
                title="Monthly TID Progression",
                barmode="stack",
                xaxis_title="Month",
                yaxis_title="Percentage",
                legend=dict(orientation="h", y=-0.15),
                hovermode="x unified",
            )
            st.plotly_chart(fig_monthly_tid, use_container_width=True)

    # Polarization metrics using render_metric
    avg_pol = safe_mean_fn(df["power_polarization_index"])

    pol_col1, pol_col2, pol_col3, pol_col4 = st.columns(4)
    render_metric(pol_col1, "Zone 1 (Low)", f"{yearly_tid['z1']:.1f}%", "Time below aerobic threshold")
    render_metric(pol_col2, "Zone 2 (Mod)", f"{yearly_tid['z2']:.1f}%", "Tempo/sweetspot zone")
    render_metric(pol_col3, "Zone 3 (High)", f"{yearly_tid['z3']:.1f}%", "Above lactate threshold")
    render_metric(pol_col4, "Polarization", f"{avg_pol:.2f}" if avg_pol else "N/A", help_texts.get("polarization_index", ""))


def render_training_load_section(df: pd.DataFrame) -> None:
    """
    Render CTL/ATL/TSB trends over the year showing fitness progression.

    Args:
        df: Year activities DataFrame
    """
    st.subheader("📊 Training Load Progression (CTL/ATL/TSB)")

    with st.expander("ℹ️ Understanding Training Load Metrics", expanded=False):
        st.markdown("""
        **CTL (Chronic Training Load)** - Blue line
        - 42-day rolling average of TSS
        - Represents your long-term fitness
        - Higher = more fit, but also more fatigue

        **ATL (Acute Training Load)** - Red line
        - 7-day rolling average of TSS
        - Represents recent training stress/fatigue
        - Spikes quickly with hard training

        **TSB (Training Stress Balance)** - Yellow line
        - Formula: CTL - ATL
        - Positive = fresh/recovered
        - Negative = fatigued
        - Optimal race form: -10 to +5

        **ACWR (Acute:Chronic Workload Ratio)** - Green dots
        - Formula: ATL / CTL
        - Sweet spot: 0.8 - 1.3
        - >1.5 = high injury risk
        - <0.8 = detraining risk
        """)

    # Filter to activities with CTL data
    df_ctl = df[df["chronic_training_load"].notna()].copy()

    if df_ctl.empty:
        st.info("No training load data available for this year.")
        return

    # Sort by date
    df_ctl = df_ctl.sort_values("start_date")

    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("CTL / ATL / TSB Trends", "ACWR (Acute:Chronic Ratio)"),
        vertical_spacing=0.12,
        row_heights=[0.7, 0.3]
    )

    # Plot CTL (Fitness)
    fig.add_trace(
        go.Scatter(
            x=df_ctl["start_date"],
            y=df_ctl["chronic_training_load"],
            name="CTL (Fitness)",
            line=dict(color="#3498db", width=2),
            hovertemplate="<b>CTL</b>: %{y:.1f}<br>Date: %{x|%Y-%m-%d}<extra></extra>"
        ),
        row=1, col=1
    )

    # Plot ATL (Fatigue)
    fig.add_trace(
        go.Scatter(
            x=df_ctl["start_date"],
            y=df_ctl["acute_training_load"],
            name="ATL (Fatigue)",
            line=dict(color="#e74c3c", width=2),
            hovertemplate="<b>ATL</b>: %{y:.1f}<br>Date: %{x|%Y-%m-%d}<extra></extra>"
        ),
        row=1, col=1
    )

    # Plot TSB (Form)
    fig.add_trace(
        go.Scatter(
            x=df_ctl["start_date"],
            y=df_ctl["training_stress_balance"],
            name="TSB (Form)",
            line=dict(color="#f39c12", width=2),
            fill='tozeroy',
            fillcolor='rgba(243, 156, 18, 0.1)',
            hovertemplate="<b>TSB</b>: %{y:.1f}<br>Date: %{x|%Y-%m-%d}<extra></extra>"
        ),
        row=1, col=1
    )

    # Add TSB reference zones
    fig.add_hrect(y0=-10, y1=20, line_width=0, fillcolor="green", opacity=0.05, row=1, col=1)
    fig.add_hrect(y0=-50, y1=-10, line_width=0, fillcolor="orange", opacity=0.05, row=1, col=1)

    # Plot ACWR
    fig.add_trace(
        go.Scatter(
            x=df_ctl["start_date"],
            y=df_ctl["acwr"],
            name="ACWR",
            mode='markers+lines',
            marker=dict(color="#2ecc71", size=4),
            line=dict(color="#2ecc71", width=1),
            hovertemplate="<b>ACWR</b>: %{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>"
        ),
        row=2, col=1
    )

    # Add ACWR reference zones
    fig.add_hrect(y0=0.8, y1=1.3, line_width=0, fillcolor="green", opacity=0.1, row=2, col=1)
    fig.add_hrect(y0=1.3, y1=2.0, line_width=0, fillcolor="red", opacity=0.1, row=2, col=1)
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

    # Update layout
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Load", row=1, col=1)
    fig.update_yaxes(title_text="Ratio", row=2, col=1, range=[0, 2])

    fig.update_layout(
        height=600,
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    latest_ctl = df_ctl["chronic_training_load"].iloc[-1]
    latest_atl = df_ctl["acute_training_load"].iloc[-1]
    latest_tsb = df_ctl["training_stress_balance"].iloc[-1]
    latest_acwr = df_ctl["acwr"].iloc[-1]

    render_metric(col1, "📈 End CTL", f"{latest_ctl:.1f}", "Fitness at year end")
    render_metric(col2, "📉 End ATL", f"{latest_atl:.1f}", "Fatigue at year end")
    render_metric(col3, "⚖️ End TSB", f"{latest_tsb:.1f}", "Form at year end")
    render_metric(col4, "🎯 End ACWR", f"{latest_acwr:.2f}", "Injury risk at year end")


def render_trends_tab(df: pd.DataFrame, metric_view: str, safe_mean_fn) -> None:
    """
    Render the trends tab with monthly volume and intensity analysis.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
        safe_mean_fn: Function to safely calculate mean
    """

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Monthly Volume + TSS
        df_copy = df.copy()
        df_copy["month_date"] = (
            pd.to_datetime(df_copy["start_date_local"], utc=True)
            .dt.tz_localize(None)
            .dt.normalize()
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        monthly_stats = (
            df_copy.groupby("month_date")
            .agg(
                {
                    "distance": "sum",
                    "total_elevation_gain": "sum",
                    "moving_time": "sum",
                    "training_stress_score": "sum",
                }
            )
            .reset_index()
        )
        monthly_stats["distance_km"] = monthly_stats["distance"] / 1000
        monthly_stats["hours"] = monthly_stats["moving_time"] / 3600

        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])

        fig_monthly.add_trace(
            go.Bar(
                x=monthly_stats["month_date"],
                y=monthly_stats["distance_km"],
                name="Distance (km)",
                marker_color="#3498db",
            ),
            secondary_y=False,
        )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_stats["month_date"],
                y=monthly_stats["training_stress_score"],
                name="TSS",
                line=dict(color="#e74c3c", width=3),
                mode="lines+markers",
            ),
            secondary_y=True,
        )

        fig_monthly.update_layout(
            title="Monthly Volume vs Training Stress",
            hovermode="x unified",
            legend=dict(x=0, y=1.1, orientation="h"),
        )
        fig_monthly.update_yaxes(title_text="Distance (km)", secondary_y=False)
        fig_monthly.update_yaxes(title_text="TSS", secondary_y=True)
        st.plotly_chart(fig_monthly, width="stretch")

    with col_right:
        # Cumulative Distance
        df_cum = df.sort_values("start_date_local").copy()
        df_cum["day_of_year"] = df_cum["start_date_local"].dt.dayofyear
        df_cum["cum_dist"] = df_cum["distance"].cumsum() / 1000

        fig_cum = go.Figure()
        fig_cum.add_trace(
            go.Scatter(
                x=df_cum["day_of_year"],
                y=df_cum["cum_dist"],
                mode="lines",
                name="Cumulative",
                line=dict(color="#3498db", width=3),
                fill="tozeroy",
                fillcolor="rgba(52, 152, 219, 0.2)",
            )
        )

        fig_cum.update_layout(
            title="Cumulative Distance",
            xaxis_title="Day of Year",
            yaxis_title="Distance (km)",
            hovermode="x unified",
        )
        st.plotly_chart(fig_cum, width="stretch")

    # Monthly NP and IF trends
    st.markdown("#### Monthly Intensity Metrics")
    df_copy = df.copy()
    df_copy["month_date"] = (
        pd.to_datetime(df_copy["start_date_local"], utc=True)
        .dt.tz_localize(None)
        .dt.normalize()
        .dt.to_period("M")
        .dt.to_timestamp()
    )
    monthly_intensity = (
        df_copy.groupby("month_date")
        .agg(
            {
                "normalized_power": "mean",
                "intensity_factor": "mean",
            }
        )
        .reset_index()
    )

    fig_intensity = make_subplots(specs=[[{"secondary_y": True}]])

    fig_intensity.add_trace(
        go.Scatter(
            x=monthly_intensity["month_date"],
            y=monthly_intensity["normalized_power"],
            name="Avg NP (W)",
            line=dict(color="#9b59b6", width=2),
            mode="lines+markers",
        ),
        secondary_y=False,
    )

    fig_intensity.add_trace(
        go.Scatter(
            x=monthly_intensity["month_date"],
            y=monthly_intensity["intensity_factor"],
            name="Avg IF",
            line=dict(color="#e67e22", width=2),
            mode="lines+markers",
        ),
        secondary_y=True,
    )

    fig_intensity.update_layout(
        title="Monthly Intensity Trends",
        hovermode="x unified",
        legend=dict(x=0, y=1.1, orientation="h"),
    )
    fig_intensity.update_yaxes(title_text="Normalized Power (W)", secondary_y=False)
    fig_intensity.update_yaxes(title_text="Intensity Factor", secondary_y=True)
    st.plotly_chart(fig_intensity, width="stretch")


def render_efficiency_tab(
    df: pd.DataFrame, metric_view: str, safe_mean_fn, help_texts: dict, avg_ef: float, avg_fatigue: float
) -> None:
    """
    Render the efficiency & fatigue tab with monthly trends.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
        safe_mean_fn: Function to safely calculate mean
        help_texts: Dictionary of help text strings
        avg_ef: Average efficiency factor
        avg_fatigue: Average fatigue index
    """

    with st.expander("ℹ️ Understanding Efficiency & Fatigue", expanded=False):
        st.markdown(help_texts.get("efficiency_factor", ""))
        st.markdown(help_texts.get("fatigue_index", ""))

    col_eff1, col_eff2 = st.columns(2)

    with col_eff1:
        # Monthly Efficiency Factor trend
        df_copy = df.copy()
        df_copy["month_date"] = (
            pd.to_datetime(df_copy["start_date_local"], utc=True)
            .dt.tz_localize(None)
            .dt.normalize()
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        monthly_ef = (
            df_copy.groupby("month_date")
            .agg({"efficiency_factor": "mean"})
            .reset_index()
        )

        if monthly_ef["efficiency_factor"].notna().any():
            fig_ef = go.Figure()
            fig_ef.add_trace(
                go.Scatter(
                    x=monthly_ef["month_date"],
                    y=monthly_ef["efficiency_factor"],
                    mode="lines+markers",
                    name="Avg EF",
                    line=dict(color="#2ecc71", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(46, 204, 113, 0.2)",
                )
            )

            fig_ef.update_layout(
                title="Monthly Efficiency Factor Trend",
                xaxis_title="Month",
                yaxis_title="Efficiency Factor (NP/HR)",
                hovermode="x unified",
            )
            st.plotly_chart(fig_ef, width="stretch")

            # EF interpretation
            if avg_ef:
                if avg_ef > 1.8:
                    st.success(
                        f"🏆 Excellent aerobic efficiency (Avg EF: {avg_ef:.2f})"
                    )
                elif avg_ef > 1.5:
                    st.info(f"✅ Good aerobic efficiency (Avg EF: {avg_ef:.2f})")
                else:
                    st.warning(f"📈 Room for improvement (Avg EF: {avg_ef:.2f})")
        else:
            st.info("No efficiency factor data available.")

    with col_eff2:
        # Monthly Fatigue Index trend
        monthly_fatigue = (
            df_copy.groupby("month_date")
            .agg({"fatigue_index": "mean"})
            .reset_index()
        )

        if monthly_fatigue["fatigue_index"].notna().any():
            fig_fatigue = go.Figure()
            fig_fatigue.add_trace(
                go.Scatter(
                    x=monthly_fatigue["month_date"],
                    y=monthly_fatigue["fatigue_index"],
                    mode="lines+markers",
                    name="Avg Fatigue Index",
                    line=dict(color="#e74c3c", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(231, 76, 60, 0.2)",
                )
            )
            fig_fatigue.update_layout(
                title="Monthly Fatigue Index Trend",
                xaxis_title="Month",
                yaxis_title="Fatigue Index (%)",
                hovermode="x unified",
            )
            st.plotly_chart(fig_fatigue, width="stretch")

            # Fatigue interpretation
            if avg_fatigue:
                if avg_fatigue < 5:
                    st.success(
                        f"🏆 Excellent fatigue resistance (Avg: {avg_fatigue:.1f}%)"
                    )
                elif avg_fatigue < 10:
                    st.info(f"✅ Good fatigue resistance (Avg: {avg_fatigue:.1f}%)")
                else:
                    st.warning(f"⚠️ High fatigue levels (Avg: {avg_fatigue:.1f}%)")
        else:
            st.info("No fatigue index data available.")

    # Decoupling Analysis
    st.markdown("#### Power-HR Decoupling Analysis")
    decoup_col = "power_hr_decoupling"
    if decoup_col in df.columns and df[decoup_col].notna().any():
        df_copy = df.copy()
        df_copy["month_date"] = (
            pd.to_datetime(df_copy["start_date_local"], utc=True)
            .dt.tz_localize(None)
            .dt.normalize()
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        monthly_decoup = (
            df_copy.groupby("month_date").agg({decoup_col: "mean"}).reset_index()
        )

        fig_decoup = go.Figure()
        fig_decoup.add_trace(
            go.Bar(
                x=monthly_decoup["month_date"],
                y=monthly_decoup[decoup_col],
                marker_color=[
                    "#2ecc71" if v < 5 else "#f1c40f" if v < 10 else "#e74c3c"
                    for v in monthly_decoup[decoup_col].fillna(0)
                ],
                hovertemplate="<b>%{x|%B}</b><br>Decoupling: %{y:.1f}%<extra></extra>",
            )
        )
        fig_decoup.update_layout(
            title="Monthly Average Decoupling",
            xaxis_title="Month",
            yaxis_title="Decoupling (%)",
            hovermode="x unified",
        )
        st.plotly_chart(fig_decoup, width="stretch")

        st.caption(
            "💡 Decoupling <5% indicates good aerobic fitness. >10% suggests fatigue or inadequate fitness."
        )


def render_gear_tab(df: pd.DataFrame, settings, help_texts: dict, get_gear_name_fn) -> None:
    """
    Render the gear usage tab with equipment statistics.

    Args:
        df: Year activities
        settings: Settings object with gear names
        help_texts: Dictionary of help text strings
        get_gear_name_fn: Function to get gear name
    """
    with st.expander("ℹ️ Understanding Gear Usage", expanded=False):
        st.markdown(help_texts.get("gear_usage", ""))

    if "gear_id" in df.columns and df["gear_id"].notna().any():
        # Calculate gear statistics
        gear_stats = (
            df.groupby("gear_id")
            .agg(
                {
                    "distance": "sum",
                    "moving_time": "sum",
                    "total_elevation_gain": "sum",
                    "id": "count",
                }
            )
            .reset_index()
        )
        gear_stats.columns = [
            "gear_id",
            "distance",
            "time",
            "elevation",
            "activities",
        ]
        gear_stats["distance_km"] = gear_stats["distance"] / 1000
        gear_stats["hours"] = gear_stats["time"] / 3600

        # Apply gear names
        gear_stats["gear_name"] = gear_stats["gear_id"].apply(
            lambda x: get_gear_name_fn(x, settings) if settings else x
        )

        col_gear1, col_gear2 = st.columns(2)

        with col_gear1:
            fig_gear_dist = px.pie(
                gear_stats,
                values="distance_km",
                names="gear_name",
                title="Distance by Gear",
                hole=0.4,
            )
            st.plotly_chart(fig_gear_dist, width="stretch")

        with col_gear2:
            fig_gear_time = px.pie(
                gear_stats,
                values="hours",
                names="gear_name",
                title="Time by Gear",
                hole=0.4,
            )
            st.plotly_chart(fig_gear_time, width="stretch")

        # Gear summary table
        st.markdown("#### Gear Summary")
        display_gear = gear_stats[
            ["gear_name", "distance_km", "hours", "elevation", "activities"]
        ].copy()
        display_gear.columns = [
            "Gear",
            "Distance (km)",
            "Hours",
            "Elevation (m)",
            "Activities",
        ]
        display_gear["Distance (km)"] = (
            display_gear["Distance (km)"].round(0).astype(int)
        )
        display_gear["Hours"] = display_gear["Hours"].round(1)
        display_gear["Elevation (m)"] = (
            display_gear["Elevation (m)"].round(0).astype(int)
        )
        st.dataframe(display_gear, use_container_width=True, hide_index=True)
    else:
        st.info("No gear data available.")


def render_distributions_tab(df: pd.DataFrame, metric_view: str, safe_mean_fn) -> None:
    """
    Render the distributions tab with power and activity type breakdown.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
        safe_mean_fn: Function to safely calculate mean
    """

    col1, col2 = st.columns(2)

    with col1:
        # Power Distribution
        np_col = "normalized_power"
        if np_col in df.columns and df[np_col].notna().any():
            fig_power = px.histogram(
                df.dropna(subset=[np_col]),
                x=np_col,
                nbins=30,
                title="Normalized Power Distribution",
                labels={np_col: "Normalized Power (W)"},
                color_discrete_sequence=["#9b59b6"],
            )
            st.plotly_chart(fig_power, width="stretch")
        else:
            st.info("No power data available.")

    with col2:
        # Activity Type Breakdown
        type_counts = df["sport_type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Count"]

        fig_pie = px.pie(
            type_counts,
            values="Count",
            names="Type",
            title="Activity Types",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, width="stretch")

    # TSS vs Distance scatter
    st.markdown("#### Training Load Analysis")
    tss_col = "training_stress_score"
    if tss_col in df.columns:
        df_scatter = df.dropna(subset=[tss_col]).copy()
        if not df_scatter.empty:
            df_scatter["distance_km"] = df_scatter["distance"] / 1000

            fig_scatter = px.scatter(
                df_scatter,
                x="distance_km",
                y=tss_col,
                color="sport_type",
                size="normalized_power"
                if "normalized_power" in df_scatter.columns
                else None,
                hover_data=["name", "start_date_local"],
                title="Distance vs TSS (Size = NP)",
                labels={
                    "distance_km": "Distance (km)",
                    tss_col: "Training Stress Score",
                },
            )
            st.plotly_chart(fig_scatter, width="stretch")


def render_patterns_tab(df: pd.DataFrame, metric_view: str) -> None:
    """
    Render the patterns tab with weekday and time-of-day analysis.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
    """

    col_w1, col_w2 = st.columns(2)

    # Prepare weekday data
    df_copy = df.copy()
    df_copy["weekday"] = df_copy["start_date_local"].dt.day_name()
    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    df_copy["weekday"] = pd.Categorical(
        df_copy["weekday"], categories=weekday_order, ordered=True
    )

    with col_w1:
        # Weekday activity count
        weekday_count = (
            df_copy.groupby("weekday", observed=True).size().reset_index(name="count")
        )

        fig_weekday_count = px.bar(
            weekday_count,
            x="weekday",
            y="count",
            title="Activities by Weekday",
            labels={"weekday": "Day", "count": "Count"},
            color="count",
            color_continuous_scale="Viridis",
        )
        fig_weekday_count.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_weekday_count, width="stretch")

    with col_w2:
        # Weekday distance
        weekday_dist = (
            df_copy.groupby("weekday", observed=True)
            .agg({"distance": "sum"})
            .reset_index()
        )
        weekday_dist["distance_km"] = weekday_dist["distance"] / 1000

        fig_weekday_dist = px.bar(
            weekday_dist,
            x="weekday",
            y="distance_km",
            title="Distance by Weekday",
            labels={"weekday": "Day", "distance_km": "Distance (km)"},
            color="distance_km",
            color_continuous_scale="Blues",
        )
        fig_weekday_dist.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_weekday_dist, width="stretch")

    # Time of day analysis
    st.markdown("#### Time of Day Analysis")
    df_copy["hour"] = df_copy["start_date_local"].dt.hour

    def categorize_time(hour):
        if 5 <= hour < 12:
            return "Morning (5-12)"
        elif 12 <= hour < 17:
            return "Afternoon (12-17)"
        else:
            return "Evening (17+)"

    df_copy["time_of_day"] = df_copy["hour"].apply(categorize_time)

    time_stats = (
        df_copy.groupby("time_of_day")
        .agg(
            {"id": "count", "distance": "sum", "normalized_power": "mean"}
        )
        .reset_index()
    )
    time_stats.columns = ["Time Period", "Activities", "Distance", "Avg NP"]
    time_stats["Distance (km)"] = (
        (time_stats["Distance"] / 1000).round(0).astype(int)
    )
    time_stats["Avg NP (W)"] = time_stats["Avg NP"].round(0)

    col_tod1, col_tod2 = st.columns(2)

    with col_tod1:
        fig_tod = px.pie(
            time_stats,
            values="Activities",
            names="Time Period",
            title="Activities by Time of Day",
            color="Time Period",
            color_discrete_map={
                "Morning (5-12)": "#f39c12",
                "Afternoon (12-17)": "#3498db",
                "Evening (17+)": "#9b59b6",
            },
            hole=0.4,
        )
        st.plotly_chart(fig_tod, width="stretch")

    with col_tod2:
        st.markdown("**Time of Day Summary**")
        display_tod = time_stats[
            ["Time Period", "Activities", "Distance (km)", "Avg NP (W)"]
        ]
        st.dataframe(display_tod, use_container_width=True, hide_index=True)


def render_extremes_section(df: pd.DataFrame, metric_view: str, format_duration_fn) -> None:
    """
    Render activity extremes section showing longest, highest metrics.

    Args:
        df: Year activities
        metric_view: "Moving Time" or "Raw Time"
        format_duration_fn: Function to format duration
    """

    st.divider()
    st.subheader("🏆 Activity Extremes")

    col_e1, col_e2, col_e3, col_e4 = st.columns(4)

    with col_e1:
        longest_dist = df.loc[df["distance"].idxmax()]
        render_metric(
            col_e1,
            "🛣️ Longest Distance",
            f"{longest_dist['distance'] / 1000:.1f} km",
            f"{longest_dist['name'][:30]}",
        )

    with col_e2:
        longest_time = df.loc[df["moving_time"].idxmax()]
        render_metric(
            col_e2,
            "⏱️ Longest Duration",
            format_duration_fn(longest_time["moving_time"]),
            f"{longest_time['name'][:30]}",
        )

    with col_e3:
        highest_elev = df.loc[df["total_elevation_gain"].idxmax()]
        render_metric(
            col_e3,
            "⛰️ Most Elevation",
            f"{highest_elev['total_elevation_gain']:,.0f} m",
            f"{highest_elev['name'][:30]}",
        )

    with col_e4:
        np_col = "normalized_power"
        if np_col in df.columns and df[np_col].notna().any():
            highest_np = df.loc[df[np_col].idxmax()]
            render_metric(
                col_e4,
                "⚡ Highest NP",
                f"{highest_np[np_col]:.0f} W",
                f"{highest_np['name'][:30]}",
            )
        else:
            render_metric(col_e4, "⚡ Highest NP", "N/A")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4.1: Performance Trajectory
# ═══════════════════════════════════════════════════════════════════════════════


def render_performance_trajectory(
    df: pd.DataFrame,
    selected_year: int,
    help_texts: dict,
) -> None:
    """
    Render Performance Trajectory section with FTP evolution and peak metrics.

    Args:
        df: Year activities
        selected_year: Selected year
        help_texts: Dictionary of help text strings
    """
    st.divider()
    st.markdown("### 📈 Performance Trajectory")

    # Check if FTP estimate data is available
    if "estimated_ftp" not in df.columns or df["estimated_ftp"].isna().all():
        st.info("FTP estimate data not available. Requires power meter data for calculation.")
        return

    # Get activities with FTP estimates
    df_ftp = df[df["estimated_ftp"].notna()].copy()

    if len(df_ftp) == 0:
        st.info("No FTP estimates available for this year.")
        return

    # Sort by date
    df_ftp = df_ftp.sort_values("start_date_local")

    # Group by month to get monthly averages
    df_ftp["month"] = df_ftp["start_date_local"].dt.to_period("M")
    monthly_ftp = df_ftp.groupby("month")["estimated_ftp"].mean().reset_index()
    monthly_ftp["month_name"] = monthly_ftp["month"].apply(lambda x: x.strftime("%b"))
    monthly_ftp["month_date"] = monthly_ftp["month"].apply(lambda x: x.to_timestamp())

    # Calculate year metrics
    ftp_start = df_ftp.iloc[0]["estimated_ftp"]
    ftp_end = df_ftp.iloc[-1]["estimated_ftp"]
    ftp_change = ftp_end - ftp_start
    ftp_change_pct = (ftp_change / ftp_start * 100) if ftp_start > 0 else 0
    peak_ftp = df_ftp["estimated_ftp"].max()
    peak_ftp_date = df_ftp.loc[df_ftp["estimated_ftp"].idxmax(), "start_date_local"]

    # Peak CTL
    peak_ctl = 0
    peak_ctl_date = None
    if "chronic_training_load" in df.columns and df["chronic_training_load"].notna().any():
        peak_ctl = df["chronic_training_load"].max()
        peak_ctl_date = df.loc[df["chronic_training_load"].idxmax(), "start_date_local"]

    # FTP Evolution Chart
    fig_ftp = go.Figure()

    fig_ftp.add_trace(go.Scatter(
        x=df_ftp["start_date_local"],
        y=df_ftp["estimated_ftp"],
        mode='markers',
        name='FTP Estimates',
        marker=dict(size=6, color='rgba(46, 204, 113, 0.4)'),
        hovertemplate='%{x}<br>FTP: %{y:.0f}W<extra></extra>'
    ))

    if len(monthly_ftp) > 1:
        fig_ftp.add_trace(go.Scatter(
            x=monthly_ftp["month_date"],
            y=monthly_ftp["estimated_ftp"],
            mode='lines+markers',
            name='Monthly Average',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=10),
            hovertemplate='%{x}<br>Avg FTP: %{y:.0f}W<extra></extra>'
        ))

    fig_ftp.update_layout(
        title="FTP Evolution",
        xaxis_title="Date",
        yaxis_title="Estimated FTP (W)",
        hovermode="x unified",
        height=350
    )

    st.plotly_chart(fig_ftp, use_container_width=True)

    # Year summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        change_symbol = "✅" if ftp_change > 0 else "⚠️" if ftp_change < 0 else "➡️"
        st.markdown(f"**Jan → Dec:** {ftp_start:.0f}W → {ftp_end:.0f}W  "
                   f"**({ftp_change:+.0f}W, {ftp_change_pct:+.1f}%) {change_symbol}**")

    with col2:
        peak_month = peak_ftp_date.strftime("%B") if peak_ftp_date else "N/A"
        st.markdown(f"**Peak FTP:** {peak_ftp:.0f}W ({peak_month})")

    with col3:
        if peak_ctl > 0:
            peak_ctl_month = peak_ctl_date.strftime("%B") if peak_ctl_date else "N/A"
            st.markdown(f"**Peak CTL:** {peak_ctl:.0f} ({peak_ctl_month})")
        else:
            st.markdown("**Peak CTL:** N/A")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4.2: Season Phases
# ═══════════════════════════════════════════════════════════════════════════════


def render_season_phases(
    df: pd.DataFrame,
    selected_year: int,
    help_texts: dict,
) -> None:
    """
    Render Season Phases section with timeline visualization.

    Args:
        df: Year activities
        selected_year: Selected year
        help_texts: Dictionary of help text strings
    """
    st.divider()
    st.markdown("### 🗓️ Season Phases")

    # Check for required data
    if "chronic_training_load" not in df.columns or df["chronic_training_load"].isna().all():
        st.info("CTL data not available for season phase detection.")
        return

    # Group by month
    df_monthly = df.copy()
    df_monthly["month"] = df_monthly["start_date_local"].dt.to_period("M")

    monthly_stats = df_monthly.groupby("month").agg({
        "chronic_training_load": "mean",
        "training_stress_balance": "mean",
        "intensity_factor": "mean",
        "moving_time": "sum",
    }).reset_index()

    monthly_stats["month_name"] = monthly_stats["month"].apply(lambda x: x.strftime("%b"))

    # Calculate annual averages
    annual_avg_volume = monthly_stats["moving_time"].mean()
    peak_ctl = monthly_stats["chronic_training_load"].max()

    # Detect phases for each month
    phases = []
    for idx, row in monthly_stats.iterrows():
        ctl = row["chronic_training_load"]
        tsb = row["training_stress_balance"]
        avg_if = row["intensity_factor"]
        volume = row["moving_time"]

        # Calculate CTL trend
        if idx > 0:
            prev_ctl = monthly_stats.iloc[idx - 1]["chronic_training_load"]
            ctl_trend = ctl - prev_ctl
        else:
            ctl_trend = 0

        # Phase detection logic
        if pd.isna(ctl) or pd.isna(avg_if):
            phase = "TRANSITION"
        elif ctl_trend < 0 and volume < 0.5 * annual_avg_volume:
            phase = "OFF-SEASON"
        elif ctl_trend > 0 and avg_if < 0.72:
            phase = "BASE"
        elif ctl_trend > 0 and avg_if > 0.75:
            phase = "BUILD"
        elif ctl > 0.9 * peak_ctl and tsb > -5:
            phase = "PEAK/RACE"
        elif ctl_trend < 0 and tsb > 10:
            phase = "RECOVERY"
        else:
            phase = "TRANSITION"

        phases.append(phase)

    monthly_stats["phase"] = phases

    # Create timeline visualization
    phase_colors = {
        "OFF-SEASON": "#95a5a6",
        "BASE": "#3498db",
        "BUILD": "#f39c12",
        "PEAK/RACE": "#e74c3c",
        "RECOVERY": "#2ecc71",
        "TRANSITION": "#9b59b6"
    }

    fig_timeline = go.Figure()

    for phase_name, color in phase_colors.items():
        phase_data = monthly_stats[monthly_stats["phase"] == phase_name]
        if len(phase_data) > 0:
            fig_timeline.add_trace(go.Bar(
                x=phase_data["month_name"],
                y=[1] * len(phase_data),
                name=phase_name,
                marker_color=color,
                hovertemplate=f"<b>{phase_name}</b><br>%{{x}}<extra></extra>"
            ))

    fig_timeline.update_layout(
        title="Season Timeline",
        xaxis_title="Month",
        yaxis=dict(showticklabels=False, showgrid=False),
        barmode='overlay',
        height=200,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig_timeline, use_container_width=True)

    # Phase summary
    phase_counts = monthly_stats["phase"].value_counts()
    st.markdown("**Phase Distribution:**")
    for phase in ["BASE", "BUILD", "PEAK/RACE", "RECOVERY", "OFF-SEASON", "TRANSITION"]:
        if phase in phase_counts:
            weeks = phase_counts[phase] * 4  # Approximate weeks
            st.markdown(f"- **{phase}**: {phase_counts[phase]} months (~{weeks} weeks)")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4.3: Year-over-Year Comparison
# ═══════════════════════════════════════════════════════════════════════════════


def render_year_over_year_comparison(
    df_current: pd.DataFrame,
    df_previous: pd.DataFrame,
    selected_year: int,
    help_texts: dict,
) -> None:
    """
    Render Year-over-Year Comparison section.

    Args:
        df_current: Current year activities
        df_previous: Previous year activities
        selected_year: Selected year
        help_texts: Dictionary of help text strings
    """
    st.divider()
    st.markdown("### 📊 Year-over-Year Comparison")

    if df_previous.empty:
        st.info(f"No data available for {selected_year - 1} to compare.")
        return

    # Calculate metrics for both years
    def calc_year_metrics(df):
        total_hours = df["moving_time"].sum() / 3600
        total_distance = df["distance"].sum() / 1000
        total_tss = df["training_stress_score"].sum() if "training_stress_score" in df.columns else 0

        peak_ftp = 0
        if "estimated_ftp" in df.columns:
            peak_ftp = df["estimated_ftp"].max() if df["estimated_ftp"].notna().any() else 0

        peak_ctl = 0
        if "chronic_training_load" in df.columns:
            peak_ctl = df["chronic_training_load"].max() if df["chronic_training_load"].notna().any() else 0

        avg_ef = 0
        if "efficiency_factor" in df.columns:
            avg_ef = df["efficiency_factor"].mean() if df["efficiency_factor"].notna().any() else 0

        return {
            "hours": total_hours,
            "distance": total_distance,
            "tss": total_tss,
            "peak_ftp": peak_ftp,
            "peak_ctl": peak_ctl,
            "avg_ef": avg_ef
        }

    current_metrics = calc_year_metrics(df_current)
    previous_metrics = calc_year_metrics(df_previous)

    # Create comparison table
    st.markdown(f"#### {selected_year - 1} vs {selected_year}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**Metric**")
        st.markdown("Total Hours")
        st.markdown("Total Distance")
        st.markdown("Total TSS")
        st.markdown("Peak FTP")
        st.markdown("Peak CTL")
        st.markdown("Avg EF")

    with col2:
        st.markdown(f"**{selected_year - 1}**")
        st.markdown(f"{previous_metrics['hours']:.0f}h")
        st.markdown(f"{previous_metrics['distance']:,.0f} km")
        st.markdown(f"{previous_metrics['tss']:,.0f}")
        st.markdown(f"{previous_metrics['peak_ftp']:.0f} W" if previous_metrics['peak_ftp'] > 0 else "N/A")
        st.markdown(f"{previous_metrics['peak_ctl']:.0f}" if previous_metrics['peak_ctl'] > 0 else "N/A")
        st.markdown(f"{previous_metrics['avg_ef']:.2f}" if previous_metrics['avg_ef'] > 0 else "N/A")

    with col3:
        st.markdown(f"**{selected_year}**")
        st.markdown(f"{current_metrics['hours']:.0f}h")
        st.markdown(f"{current_metrics['distance']:,.0f} km")
        st.markdown(f"{current_metrics['tss']:,.0f}")
        st.markdown(f"{current_metrics['peak_ftp']:.0f} W" if current_metrics['peak_ftp'] > 0 else "N/A")
        st.markdown(f"{current_metrics['peak_ctl']:.0f}" if current_metrics['peak_ctl'] > 0 else "N/A")
        st.markdown(f"{current_metrics['avg_ef']:.2f}" if current_metrics['avg_ef'] > 0 else "N/A")

    with col4:
        st.markdown("**Δ**")

        # Calculate deltas
        for metric in ["hours", "distance", "tss", "peak_ftp", "peak_ctl", "avg_ef"]:
            if previous_metrics[metric] > 0 and current_metrics[metric] > 0:
                delta_pct = ((current_metrics[metric] - previous_metrics[metric]) / previous_metrics[metric]) * 100
                symbol = "✅" if delta_pct > 0 else "⚠️" if delta_pct < -5 else "➡️"
                st.markdown(f"{delta_pct:+.0f}% {symbol}")
            else:
                st.markdown("N/A")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4.4: Annual Statistics
# ═══════════════════════════════════════════════════════════════════════════════


def render_annual_statistics(
    df: pd.DataFrame,
    selected_year: int,
    format_duration_fn,
    help_texts: dict,
) -> None:
    """
    Render Annual Statistics section.

    Args:
        df: Year activities
        selected_year: Selected year
        format_duration_fn: Function to format duration
        help_texts: Dictionary of help text strings
    """
    st.divider()
    st.markdown("### 🏆 Annual Statistics")

    # Calculate statistics
    total_hours = df["moving_time"].sum() / 3600

    # Biggest week
    df_weekly = df.copy()
    df_weekly["week_start"] = (df_weekly["start_date_local"] -
                                pd.to_timedelta(df_weekly["start_date_local"].dt.weekday, unit='D')).dt.normalize()
    weekly_hours = df_weekly.groupby("week_start")["moving_time"].sum() / 3600
    biggest_week_hours = weekly_hours.max()
    biggest_week_date = weekly_hours.idxmax()
    biggest_week_num = biggest_week_date.isocalendar()[1] if biggest_week_hours > 0 else 0

    # Longest ride
    longest_ride = df.loc[df["moving_time"].idxmax()]
    longest_ride_time = longest_ride["moving_time"]

    # Training days
    df["date_local"] = df["start_date_local"].dt.date
    training_days = len(df["date_local"].unique())
    total_days = 366 if selected_year % 4 == 0 else 365  # Leap year check

    # Most climbing
    most_climbing = df.loc[df["total_elevation_gain"].idxmax()]
    most_climbing_elev = most_climbing["total_elevation_gain"]

    # Highest NP
    highest_np = 0
    if "normalized_power" in df.columns and df["normalized_power"].notna().any():
        highest_np = df["normalized_power"].max()

    # Display in 2 rows, 3 columns
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric(
            col1,
            "Total Hours",
            f"{total_hours:.0f}h",
            help_texts.get("total_hours", "Total training time for the year")
        )

    with col2:
        render_metric(
            col2,
            "Biggest Week",
            f"{biggest_week_hours:.1f}h",
            f"Week {biggest_week_num}" if biggest_week_num > 0 else "N/A"
        )

    with col3:
        render_metric(
            col3,
            "Longest Ride",
            format_duration_fn(longest_ride_time),
            longest_ride["name"][:30] if "name" in longest_ride else "N/A"
        )

    col4, col5, col6 = st.columns(3)

    with col4:
        render_metric(
            col4,
            "Training Days",
            f"{training_days} / {total_days}",
            f"{training_days / total_days * 100:.0f}% consistency"
        )

    with col5:
        render_metric(
            col5,
            "Most Climbing",
            f"{most_climbing_elev:,.0f}m",
            most_climbing["name"][:30] if "name" in most_climbing else "N/A"
        )

    with col6:
        if highest_np > 0:
            render_metric(
                col6,
                "Highest NP",
                f"{highest_np:.0f} W",
                help_texts.get("highest_np", "Highest normalized power for a single activity")
            )
        else:
            render_metric(col6, "Highest NP", "N/A")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4.5: Risk Analysis
# ═══════════════════════════════════════════════════════════════════════════════


def render_risk_analysis(
    df: pd.DataFrame,
    selected_year: int,
    help_texts: dict,
) -> None:
    """
    Render Training Risk Analysis section.

    Args:
        df: Year activities
        selected_year: Selected year
        help_texts: Dictionary of help text strings
    """
    st.divider()
    st.markdown("### ⚠️ Training Risk Analysis")

    # High ACWR weeks
    high_acwr_weeks = 0
    if "acwr" in df.columns:
        df_weekly = df.copy()
        df_weekly["week_start"] = (df_weekly["start_date_local"] -
                                    pd.to_timedelta(df_weekly["start_date_local"].dt.weekday, unit='D')).dt.normalize()
        weekly_acwr = df_weekly.groupby("week_start")["acwr"].mean()
        high_acwr_weeks = (weekly_acwr > 1.5).sum()

    # Overreach periods (TSB < -30)
    overreach_days = 0
    overreach_periods = 0
    if "training_stress_balance" in df.columns:
        df_sorted = df.sort_values("start_date_local")
        df_sorted["date_local"] = df_sorted["start_date_local"].dt.date
        daily_tsb = df_sorted.groupby("date_local")["training_stress_balance"].mean()
        overreach_mask = daily_tsb < -30
        overreach_days = overreach_mask.sum()

        # Count continuous overreach periods
        in_overreach = False
        for is_overreach in overreach_mask:
            if is_overreach and not in_overreach:
                overreach_periods += 1
                in_overreach = True
            elif not is_overreach:
                in_overreach = False

    # Training consistency
    df["date_local"] = df["start_date_local"].dt.date
    training_days = len(df["date_local"].unique())
    total_days = 366 if selected_year % 4 == 0 else 365
    consistency_pct = (training_days / total_days) * 100

    # Longest training break
    training_dates = sorted(df["date_local"].unique())
    training_dates_pd = pd.to_datetime(training_dates)

    longest_gap = 0
    if len(training_dates_pd) > 1:
        for i in range(1, len(training_dates_pd)):
            gap = (training_dates_pd[i] - training_dates_pd[i-1]).days - 1
            longest_gap = max(longest_gap, gap)

    # Calculate risk score
    risk_score = 0
    risk_factors = []

    if high_acwr_weeks > 5:
        risk_score += 2
        risk_factors.append("High ACWR frequency")
    elif high_acwr_weeks > 2:
        risk_score += 1

    if overreach_periods > 3:
        risk_score += 2
        risk_factors.append("Frequent overreaching")
    elif overreach_periods > 1:
        risk_score += 1

    if consistency_pct < 50:
        risk_score += 2
        risk_factors.append("Low consistency")
    elif consistency_pct < 70:
        risk_score += 1

    if longest_gap > 14:
        risk_score += 1
        risk_factors.append("Extended training break")

    # Determine risk level
    if risk_score == 0:
        risk_level = "LOW"
        risk_color = "#2ecc71"
        risk_message = "✅ Excellent load management"
    elif risk_score <= 2:
        risk_level = "MODERATE"
        risk_color = "#f39c12"
        risk_message = "⚠️ Monitor recovery and consistency"
    else:
        risk_level = "HIGH"
        risk_color = "#e74c3c"
        risk_message = "🔴 Review training plan and recovery"

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric(
            col1,
            "High ACWR Weeks",
            f"{high_acwr_weeks}",
            help_texts.get("high_acwr_weeks", "Weeks with ACWR > 1.5 (injury risk)")
        )

    with col2:
        render_metric(
            col2,
            "Overreach Periods",
            f"{overreach_periods}",
            f"{overreach_days} days total" if overreach_days > 0 else "N/A"
        )

    with col3:
        render_metric(
            col3,
            "Training Consistency",
            f"{consistency_pct:.0f}%",
            f"{training_days}/{total_days} days"
        )

    with col4:
        render_metric(
            col4,
            "Longest Break",
            f"{longest_gap} days",
            help_texts.get("longest_break", "Longest period without training")
        )

    # Risk score summary
    st.markdown(f"<h4 style='color: {risk_color};'>💡 Risk Score: {risk_level}</h4>", unsafe_allow_html=True)
    st.markdown(f"**{risk_message}**")

    if risk_factors:
        st.markdown("**Risk Factors:**")
        for factor in risk_factors:
            st.markdown(f"- {factor}")