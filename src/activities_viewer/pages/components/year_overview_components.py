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

    with st.expander("ℹ️ Understanding Year KPIs", expanded=False):
        st.markdown("""
        **Volume Metrics**: Distance, Time, Elevation - measure total training volume

        **Intensity Metrics**: TSS, Avg IF, Avg EF - measure training quality and efficiency

        **Fatigue Metrics**: Avg Fatigue Index - tracks power sustainability over activities
        """)

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

    # Row 1: Volume metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚴 Distance", f"{total_dist:,.0f} km", delta=delta_dist)
    col2.metric("⏱️ Moving Time", f"{total_time / 3600:,.0f} h", delta=delta_time)
    col3.metric("⛰️ Elevation", f"{total_elev:,.0f} m", delta=delta_elev)
    col4.metric("📝 Activities", f"{count}", delta=delta_count)

    # Row 2: Intensity and efficiency metrics
    col5, col6, col7, col8 = st.columns(4)
    col5.metric(
        "💪 Total TSS", f"{total_tss:,.0f}", delta=delta_tss, help=help_texts.get("tss", "")
    )
    col6.metric("⚡ Avg NP", f"{avg_np:.0f} W" if avg_np else "N/A")
    col7.metric("📊 Avg IF", f"{avg_if:.2f}" if avg_if else "N/A")
    col8.metric(
        "🔋 Avg EF",
        f"{avg_ef:.2f}" if avg_ef else "N/A",
        help=help_texts.get("efficiency_factor", ""),
    )

    # Row 3: Training Load & Fitness visualization
    st.divider()
    st.markdown("#### 📊 Training Load State (End of Year)")

    # Get latest activity metrics
    if not df.empty:
        latest_activity = df.sort_values("start_date", ascending=False).iloc[0]

        ctl = latest_activity.get("chronic_training_load", None)
        atl = latest_activity.get("acute_training_load", None)
        tsb = latest_activity.get("training_stress_balance", None)
        acwr = latest_activity.get("acwr", None)

        # Create bar charts for training load metrics
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        fig = make_subplots(
            rows=1, cols=4,
            specs=[[{'type': 'bar'}, {'type': 'bar'}, {'type': 'bar'}, {'type': 'bar'}]],
            subplot_titles=('CTL (Fitness)', 'ATL (Fatigue)', 'TSB (Form)', 'ACWR (Injury Risk)')
        )

        # CTL interpretation
        ctl_interpretation = ""
        if pd.notna(ctl):
            if ctl < 50:
                ctl_interpretation = "Low fitness (building phase)"
                ctl_color = "lightgray"
            elif ctl < 100:
                ctl_interpretation = "Moderate fitness (consistent training)"
                ctl_color = "lightblue"
            elif ctl < 150:
                ctl_interpretation = "High fitness (peak training)"
                ctl_color = "lightgreen"
            else:
                ctl_interpretation = "Elite fitness (racing/peak)"
                ctl_color = "darkgreen"
        else:
            ctl_color = "lightgray"

        ctl_value = f"{ctl:.1f}" if pd.notna(ctl) else "0"
        ctl_hover = f"<b>CTL (Chronic Training Load)</b><br>42-day fitness level<br>Value: {ctl_value}<br>Status: {ctl_interpretation}<br>Optimal: 80-120"
        fig.add_trace(go.Bar(
            x=['CTL'],
            y=[ctl if pd.notna(ctl) else 0],
            marker=dict(color=[ctl_color]),
            hovertext=[ctl_hover],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False
        ), row=1, col=1)

        # ATL interpretation
        atl_interpretation = ""
        if pd.notna(atl):
            if atl < 50:
                atl_interpretation = "Fresh, low fatigue"
                atl_color = "lightgray"
            elif atl < 100:
                atl_interpretation = "Moderate fatigue (normal training week)"
                atl_color = "lightyellow"
            else:
                atl_interpretation = "High fatigue (accumulating load)"
                atl_color = "lightcoral"
        else:
            atl_color = "lightgray"

        atl_value = f"{atl:.1f}" if pd.notna(atl) else "0"
        atl_hover = f"<b>ATL (Acute Training Load)</b><br>7-day fatigue level<br>Value: {atl_value}<br>Status: {atl_interpretation}<br>Optimal: 30-70"
        fig.add_trace(go.Bar(
            x=['ATL'],
            y=[atl if pd.notna(atl) else 0],
            marker=dict(color=[atl_color]),
            hovertext=[atl_hover],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False
        ), row=1, col=2)

        # TSB interpretation
        if pd.notna(tsb):
            if tsb < -50:
                tsb_interpretation = "Extremely exhausted - AVOID RACING"
                tsb_color = "darkred"
            elif tsb < -10:
                tsb_interpretation = "Fatigued but building fitness"
                tsb_color = "lightyellow"
            elif tsb <= 20:
                tsb_interpretation = "Fresh and race-ready (OPTIMAL)"
                tsb_color = "lightgreen"
            else:
                tsb_interpretation = "Very fresh/detrained"
                tsb_color = "lightyellow"
        else:
            tsb_color = "lightgray"
            tsb_interpretation = "N/A"

        tsb_value = f"{tsb:.1f}" if pd.notna(tsb) else "0"
        tsb_hover = f"<b>TSB (Training Stress Balance)</b><br>Form & freshness (CTL - ATL)<br>Value: {tsb_value}<br>Status: {tsb_interpretation}<br>Optimal: -10 to +20"
        fig.add_trace(go.Bar(
            x=['TSB'],
            y=[tsb if pd.notna(tsb) else 0],
            marker=dict(color=[tsb_color]),
            hovertext=[tsb_hover],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False
        ), row=1, col=3)

        # ACWR interpretation
        if pd.notna(acwr):
            if acwr < 0.8:
                acwr_interpretation = "Undertraining (low injury risk)"
                acwr_color = "lightyellow"
            elif acwr <= 1.3:
                acwr_interpretation = "Optimal zone (safe training)"
                acwr_color = "lightgreen"
            elif acwr <= 1.5:
                acwr_interpretation = "Caution zone (moderate injury risk)"
                acwr_color = "lightyellow"
            else:
                acwr_interpretation = "Danger zone (HIGH INJURY RISK)"
                acwr_color = "lightcoral"
        else:
            acwr_color = "lightgray"
            acwr_interpretation = "N/A"

        acwr_value = f"{acwr:.2f}" if pd.notna(acwr) else "0"
        acwr_hover = f"<b>ACWR (Acute:Chronic Workload Ratio)</b><br>Injury risk (ATL ÷ CTL)<br>Value: {acwr_value}<br>Status: {acwr_interpretation}<br>Optimal: 0.8-1.3"
        fig.add_trace(go.Bar(
            x=['ACWR'],
            y=[acwr if pd.notna(acwr) else 0],
            marker=dict(color=[acwr_color]),
            hovertext=[acwr_hover],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False
        ), row=1, col=4)

        fig.update_yaxes(title_text="Value", row=1, col=1)
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Add help text below
        with st.expander("ℹ️ Training Load Metrics Explained"):
            st.markdown("""
            - **CTL (Chronic Training Load)**: 42-day rolling average TSS. Your long-term fitness level. Higher = fitter.
            - **ATL (Acute Training Load)**: 7-day rolling average TSS. Your recent fatigue level. Higher = more tired.
            - **TSB (Training Stress Balance)**: CTL - ATL. Your current form/freshness.
              - 🟢 -10 to +20: Fresh, race-ready
              - 🟡 -50 to -10: Fatigued, high training load
              - 🔴 <-50 or >+20: Extremely fatigued or detrained
            - **ACWR (Acute:Chronic Workload Ratio)**: ATL / CTL. Injury risk indicator.
              - 🟢 0.8-1.3: Optimal training zone
              - 🟡 <0.8 or 1.3-1.5: Caution zone
              - 🔴 >1.5: High injury risk
            """)

    # Row 4: CP Model & Durability visualization
    st.divider()
    st.markdown("#### 💪 Power Profile & Durability")

    # CP model metrics (latest values)
    if not df.empty:
        latest_activity = df.sort_values("start_date", ascending=False).iloc[0]
        cp = latest_activity.get("cp", None)
        w_prime = latest_activity.get("w_prime", None)
        r_squared = latest_activity.get("cp_r_squared", None)
        aei = latest_activity.get("aei", None)

        # Durability metrics (year average)
        avg_sustainability = safe_mean_fn(df["power_sustainability_index"])
        avg_variability = safe_mean_fn(df["variability_index"])
        avg_fatigue_idx = safe_mean_fn(df["fatigue_index"])
        avg_decoupling = safe_mean_fn(df["power_hr_decoupling"])

        # Create two columns for visualizations
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Power Profile (Latest)**")
            # CP Model bar chart
            import plotly.graph_objects as go
            fig_cp = go.Figure()

            if pd.notna(cp) and pd.notna(w_prime):
                # Create hover text for each metric
                cp_hover = f"CP: {cp:.0f}W<br>Sustainable power threshold (~FTP)<br>Typical: 200-300W (fit), 300-400W (very fit), 400+W (elite)"
                w_prime_hover = f"W': {w_prime/1000:.1f}kJ<br>Anaerobic capacity above CP<br>Typical: 15-25kJ (fit), 25-35kJ (very fit), 35+kJ (elite)"
                r2_hover = f"R²: {r_squared:.3f}<br>Model fit quality<br>Target >0.95 (excellent), >0.90 (good), <0.80 (poor)"
                aei_hover = f"AEI: {aei:.2f}<br>Aerobic efficiency (0-1 scale)<br>0.3-0.5 (sprinter), 0.5-0.7 (all-rounder), 0.7-0.95 (endurance)"

                fig_cp.add_trace(go.Bar(
                    x=['CP (W)', 'W\' (kJ)', 'R²', 'AEI'],
                    y=[cp if pd.notna(cp) else 0,
                       (w_prime / 1000) if pd.notna(w_prime) else 0,
                       (r_squared * 100) if pd.notna(r_squared) else 0,
                       (aei * 100) if pd.notna(aei) else 0],
                    text=[f"{cp:.0f}" if pd.notna(cp) else "N/A",
                          f"{w_prime/1000:.1f}" if pd.notna(w_prime) else "N/A",
                          f"{r_squared:.3f}" if pd.notna(r_squared) else "N/A",
                          f"{aei:.2f}" if pd.notna(aei) else "N/A"],
                    textposition='auto',
                    marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
                    hovertext=[cp_hover, w_prime_hover, r2_hover, aei_hover],
                    hovertemplate='<b>%{x}</b><br>%{hovertext}<extra></extra>'
                ))

                fig_cp.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False,
                    yaxis_title="Value",
                    hovermode='x'
                )

                st.plotly_chart(fig_cp, use_container_width=True)
            else:
                st.info("No CP model data available")

        with col_right:
            st.markdown("**Durability Metrics (Year Avg)**")
            # Durability radar chart
            fig_dur = go.Figure()

            if any(pd.notna(x) for x in [avg_sustainability, avg_variability, avg_fatigue_idx, avg_decoupling]):
                # Normalize values to 0-100 scale for radar chart
                sustainability_norm = avg_sustainability if pd.notna(avg_sustainability) else 0
                variability_norm = (2.0 - avg_variability) * 50 if pd.notna(avg_variability) else 0  # Invert: lower is better
                fatigue_norm = 100 - avg_fatigue_idx if pd.notna(avg_fatigue_idx) else 0  # Invert: lower is better
                decoupling_norm = 100 - (avg_decoupling * 2) if pd.notna(avg_decoupling) else 0  # Invert: lower is better

                # Create hover text for each dimension
                hover_text = [
                    f"Power Sustainability: {avg_sustainability:.1f}%<br>Ability to maintain power<br>>90% = excellent, >75% = good, <75% = needs work",
                    f"Variability (VI): {avg_variability:.2f}<br>Pacing consistency (1.0=perfect)<br>1.05-1.10 = steady, >1.15 = variable",
                    f"Fatigue Index: {avg_fatigue_idx:.1f}%<br>Power drop over activity<br>0-5% = excellent, >15% = poor endurance",
                    f"Power-HR Decoupling: {avg_decoupling:.1f}%<br>Aerobic fitness indicator<br>0-3% = excellent, >8% = poor aerobic base"
                ]

                fig_dur.add_trace(go.Scatterpolar(
                    r=[sustainability_norm, variability_norm, fatigue_norm, decoupling_norm],
                    theta=['Sustainability', 'Pacing', 'Endurance', 'Aerobic Fitness'],
                    fill='toself',
                    name='Durability',
                    hovertext=hover_text,
                    hovertemplate='<b>%{theta}</b><br>%{hovertext}<extra></extra>'
                ))

                fig_dur.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )
                    ),
                    height=300,
                    margin=dict(l=40, r=40, t=20, b=20),
                    showlegend=False
                )

                st.plotly_chart(fig_dur, use_container_width=True)
            else:
                st.info("No durability data available")

        # Add detailed metrics below charts
        with st.expander("ℹ️ Power Profile & Durability Explained"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("""
                **Power Profile:**
                - **CP**: Critical Power - sustainable threshold (~FTP)
                - **W'**: Anaerobic capacity above CP (in kJ)
                - **R²**: Model fit quality (>0.95 = excellent)
                - **AEI**: Aerobic efficiency (higher = more aerobic)
                """)
            with col_b:
                st.markdown(f"""
                **Durability (Year Avg):**
                - **Sustainability**: {avg_sustainability:.1f}% (higher = better)
                - **Variability**: {avg_variability:.2f} (1.0 = steady, >1.05 = variable)
                - **Fatigue**: {avg_fatigue_idx:.1f}% (lower = better endurance)
                - **Decoupling**: {avg_decoupling:.1f}% (lower = better aerobic fitness)
                """ if all(pd.notna(x) for x in [avg_sustainability, avg_variability, avg_fatigue_idx, avg_decoupling]) else """
                **Durability (Year Avg):**
                - Data not available for all metrics
                """)


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
    yearly_tid = calculate_time_weighted_tid_fn(df, prefix)

    col_tid1, col_tid2 = st.columns([1, 2])

    with col_tid1:
        # TID pie chart
        if yearly_tid["z1"] > 0 or yearly_tid["z2"] > 0 or yearly_tid["z3"] > 0:
            fig_tid = go.Figure(
                data=[
                    go.Pie(
                        labels=["Zone 1 (Low)", "Zone 2 (Moderate)", "Zone 3 (High)"],
                        values=[yearly_tid["z1"], yearly_tid["z2"], yearly_tid["z3"]],
                        hole=0.4,
                        marker_colors=["#2ecc71", "#f1c40f", "#e74c3c"],
                        textinfo="label+percent",
                        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
                    )
                ]
            )
            fig_tid.update_layout(
                title=f"Yearly TID ({selected_year})", showlegend=False
            )
            st.plotly_chart(fig_tid, width="stretch")
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
                lambda x: pd.Series(calculate_time_weighted_tid_fn(x, prefix)),
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
            st.plotly_chart(fig_monthly_tid, width="stretch")

    # Polarization metrics
    avg_pol = safe_mean_fn(df["power_polarization_index"])

    pol_col1, pol_col2, pol_col3, pol_col4 = st.columns(4)
    pol_col1.metric(
        "Zone 1 (Low)", f"{yearly_tid['z1']:.1f}%", help="Time below aerobic threshold"
    )
    pol_col2.metric(
        "Zone 2 (Moderate)", f"{yearly_tid['z2']:.1f}%", help="Tempo/sweetspot zone"
    )
    pol_col3.metric(
        "Zone 3 (High)", f"{yearly_tid['z3']:.1f}%", help="Above lactate threshold"
    )
    pol_col4.metric(
        "Avg Polarization Index",
        f"{avg_pol:.2f}" if avg_pol else "N/A",
        help=help_texts.get("polarization_index", ""),
    )


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

    col1.metric("📈 End CTL", f"{latest_ctl:.1f}")
    col2.metric("📉 End ATL", f"{latest_atl:.1f}")
    col3.metric("⚖️ End TSB", f"{latest_tsb:.1f}")
    col4.metric("🎯 End ACWR", f"{latest_acwr:.2f}")


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
        st.metric(
            "Longest Distance",
            f"{longest_dist['distance'] / 1000:.1f} km",
            delta=f"{longest_dist['name'][:25]}...",
        )

    with col_e2:
        longest_time = df.loc[df["moving_time"].idxmax()]
        st.metric(
            "Longest Duration",
            format_duration_fn(longest_time["moving_time"]),
            delta=f"{longest_time['name'][:25]}...",
        )

    with col_e3:
        highest_elev = df.loc[df["total_elevation_gain"].idxmax()]
        st.metric(
            "Most Elevation",
            f"{highest_elev['total_elevation_gain']:,.0f} m",
            delta=f"{highest_elev['name'][:25]}...",
        )

    with col_e4:
        np_col = "normalized_power"
        if np_col in df.columns and df[np_col].notna().any():
            highest_np = df.loc[df[np_col].idxmax()]
            st.metric(
                "Highest NP",
                f"{highest_np[np_col]:.0f} W",
                delta=f"{highest_np['name'][:25]}...",
            )
        else:
            st.metric("Highest NP", "N/A")
