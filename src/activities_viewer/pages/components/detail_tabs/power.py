import plotly.graph_objects as go
import streamlit as st

from activities_viewer.data.help_texts import get_help_text, get_metric_status
from activities_viewer.domain.models import Activity
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.utils.formatting import (
    get_metric,
    render_metric,
)

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
POWER_ZONE_THRESHOLDS = [0, 55, 75, 90, 105, 120, 150, float("inf")]

# HR zone ranges (typical % of LTHR - lactate threshold HR)
HR_ZONE_RANGES = {
    1: "<85% LTHR",
    2: "85-94% LTHR",
    3: "94-104% LTHR",
    4: "104-120% LTHR",
    5: ">120% LTHR",
}


def render_power_curve(
    activity: Activity, service: ActivityService, help_texts: dict
) -> None:
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
                        f"{v:.0f}W" if v > 0 else "" for v in yearly_best_power_curve
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
            legend={"orientation": "h", "y": 1.15, "x": 0},
            hovermode="x unified",
        )
        st.plotly_chart(fig_pc, width="stretch")
    else:
        st.info("No power curve data available.")


def render_summary_stats(activity: Activity, help_texts: dict) -> None:
    """Render summary stats for power and heart rate in two aligned columns."""

    col_power, col_hr = st.columns(2)

    with col_power:
        st.markdown("#### ⚡ Power Metrics")
        col1_pw, col2_pw = st.columns(2)
        col3_pw, col4_pw = st.columns(2)
        col5_pw, col6_pw = st.columns(2)
        col7_pw, col8_pw = st.columns(2)
        col9_pw, _ = st.columns(2)

        avg_pwr = get_metric(activity, "average_power")
        render_metric(
            col1_pw,
            "Avg Power",
            f"{avg_pwr:.0f} W" if avg_pwr else "-",
            get_help_text("avg_power", help_texts),
        )

        np_val = get_metric(activity, "normalized_power")
        render_metric(
            col2_pw,
            "Norm Power",
            f"{np_val:.0f} W" if np_val else "-",
            get_help_text("normalized_power", help_texts),
        )

        max_pwr = get_metric(activity, "max_power")
        render_metric(
            col3_pw,
            "Max Power",
            f"{max_pwr:.0f} W" if max_pwr else "-",
            help_text="Peak power during activity",
        )

        w_kg = get_metric(activity, "power_per_kg")
        render_metric(
            col4_pw,
            "W/kg",
            f"{w_kg:.2f}" if w_kg else "-",
            help_text="Average power normalized to body weight",
        )

        if_val = get_metric(activity, "intensity_factor")
        render_metric(
            col5_pw,
            "IF",
            f"{if_val:.2f}" if if_val else "-",
            get_help_text("intensity_factor", help_texts),
        )

        tss_val = get_metric(activity, "training_stress_score")
        render_metric(
            col6_pw,
            "TSS",
            f"{tss_val:.0f}" if tss_val else "-",
            get_help_text("tss", help_texts),
        )

        first_half_power = get_metric(activity, "first_half_power")
        render_metric(
            col7_pw,
            "First Half Power",
            f"{first_half_power:.0f} W" if first_half_power else "-",
            help_text="Average power during first half of ride",
        )

        second_half_power = get_metric(activity, "second_half_power")
        render_metric(
            col8_pw,
            "Second Half Power",
            f"{second_half_power:.0f} W" if second_half_power else "-",
            help_text="Average power during second half of ride",
        )

        power_drift = get_metric(activity, "power_drift")
        status = get_metric_status("power_drift", power_drift)
        render_metric(
            col9_pw,
            "Power Drift",
            f"{status.get('emoji', '')} {power_drift:.1f}%",
            get_help_text("power_drift", help_texts),
        )
        if status.get("label"):
            with col9_pw:
                st.caption(status["label"])

    with col_hr:
        st.markdown("#### ❤️ Heart Rate Metrics")
        col1_hr, _ = st.columns(2)
        col3_hr, _ = st.columns(2)
        col5_hr, col6_hr = st.columns(2)
        col7_hr, col8_hr = st.columns(2)
        col9_hr, _ = st.columns(2)

        avg_hr = get_metric(activity, "average_hr")
        render_metric(
            col1_hr,
            "Avg HR",
            f"{avg_hr:.0f} bpm" if avg_hr else "-",
            get_help_text("average_hr", help_texts),
        )

        max_hr = get_metric(activity, "max_hr")
        render_metric(
            col3_hr,
            "Max HR",
            f"{max_hr:.0f} bpm" if max_hr else "-",
            get_help_text("max_hr", help_texts),
        )

        ef = get_metric(activity, "efficiency_factor")
        render_metric(
            col5_hr,
            "EF",
            f"{ef:.2f}" if ef else "-",
            get_help_text("efficiency_factor", help_texts),
        )

        hr_tss = get_metric(activity, "hr_training_stress")
        render_metric(
            col6_hr,
            "HR TSS",
            f"{hr_tss:.0f}" if hr_tss else "-",
            get_help_text("hr_training_stress", help_texts),
        )

        first_half_hr = get_metric(activity, "first_half_hr")
        render_metric(
            col7_hr,
            "First Half HR",
            f"{first_half_hr:.0f} BPM" if first_half_hr else "-",
            get_help_text("first_half_hr", help_texts),
        )

        second_half_hr = get_metric(activity, "second_half_hr")
        render_metric(
            col8_hr,
            "Second Half HR",
            f"{second_half_hr:.0f} BPM" if second_half_hr else "-",
            get_help_text("second_half_hr", help_texts),
        )

        cardiac_drift = get_metric(activity, "cardiac_drift")
        status = get_metric_status("cardiac_drift", cardiac_drift)
        render_metric(
            col9_hr,
            "Cardiac Drift",
            f"{status.get('emoji', '')} {cardiac_drift:.1f}%",
            get_help_text("cardiac_drift", help_texts),
        )
        if status.get("label"):
            with col9_hr:
                st.caption(status["label"])

    st.markdown("#### ⚡ : ❤️ Power & HR Relationship Metrics")
    col_ef_1st, col_ef_2nd, col_ef_drift = st.columns(3)

    ef_1st = get_metric(activity, "first_half_ef")
    render_metric(
        col_ef_1st,
        "1st Half EF",
        f"{ef_1st:.2f}" if ef_1st else "-",
        get_help_text("first_half_ef", help_texts),
    )

    ef_2nd = get_metric(activity, "second_half_ef")
    render_metric(
        col_ef_2nd,
        "2nd Half EF",
        f"{ef_2nd:.2f}" if ef_2nd else "-",
        get_help_text("second_half_ef", help_texts),
    )

    decoupling = get_metric(activity, "power_hr_decoupling")
    status = get_metric_status("decoupling", decoupling)
    render_metric(
        col_ef_drift,
        "Decoupling",
        f"{status.get('emoji', '')} {decoupling:.1f}%",
        get_help_text("decoupling", help_texts),
    )
    if status.get("label"):
        with col_ef_drift:
            st.caption(status["label"])


def render_critical_power_model(activity: Activity, help_texts: dict) -> None:
    """Render Critical Power and W' metrics."""

    st.markdown("### ⚡ Critical Power Model")

    st.markdown("#### ⚙️ Model Configuration")
    col1, col2, col3 = st.columns(3)

    cp_config = get_metric(activity, "cp_config")
    render_metric(
        col1,
        "Critical Power (CP)",
        f"{cp_config:.0f} W" if cp_config else "-",
        "Configured CP value used for W' balance calculations",
    )

    w_prime_config = get_metric(activity, "w_prime_config")
    render_metric(
        col2,
        "Total W'",
        f"{(w_prime_config / 1000):.1f} kJ" if w_prime_config else "-",
        "Configured anaerobic work capacity used for W' balance tracking",
    )

    cp_widow_days = get_metric(activity, "cp_window_days")
    render_metric(
        col3,
        "CP Model Window",
        f"{cp_widow_days:.0f} days" if cp_widow_days else "-",
        "Time window used for CP model calculations",
    )

    st.markdown("#### Model Fit")
    col_fit1, col_fit2, _ = st.columns(3)

    cp = get_metric(activity, "cp")
    render_metric(
        col_fit1,
        "Computed CP",
        f"{cp:.0f} W" if cp else "-",
        get_help_text("cp", help_texts),
    )

    w_prime = get_metric(activity, "w_prime")
    render_metric(
        col_fit2,
        "Computed W'",
        f"{(w_prime / 1000):.1f} kJ" if w_prime else "-",
        get_help_text("w_prime", help_texts),
    )

    st.markdown("#### W' Balance Metrics")
    col_balance1, col_balance2, col_balance3, col_balance4 = st.columns(4)

    w_prime_balance_min = get_metric(activity, "w_prime_balance_min")
    render_metric(
        col_balance1,
        "Min W'",
        f"{(w_prime_balance_min / 1000):.1f} kJ" if w_prime_balance_min else "-",
        get_help_text("w_prime_balance_min", help_texts),
    )

    w_prime_depletion = get_metric(activity, "w_prime_depletion")
    render_metric(
        col_balance2,
        "W' Depletion",
        f"{w_prime_depletion:.1f}%" if w_prime_depletion else "-",
        get_help_text("w_prime_depletion", help_texts),
    )

    match_burn_count = get_metric(activity, "match_burn_count")
    render_metric(
        col_balance3,
        "Match Burns",
        f"{match_burn_count:.0f}" if match_burn_count else "-",
        get_help_text("match_burn_count", help_texts),
    )

    aei = get_metric(activity, "aei")
    render_metric(
        col_balance4,
        "AEI",
        f"{aei:.2f}" if aei else "-",
        get_help_text("aei", help_texts),
    )


def render_anaerobic_recovery_metrics(activity: Activity, help_texts: dict):
    st.markdown("### 💪 Anaerobic & Recovery Metrics")

    col_wprime, col_recovery = st.columns(2)

    # W' Balance Metrics (from pre-computed data)
    with col_wprime:
        st.markdown("#### ⚡ W' Balance")
        w_prime_balance_min = get_metric(activity, "w_prime_balance_min")
        w_prime_depletion = get_metric(activity, "w_prime_depletion")
        cp_window_days = get_metric(activity, "cp_window_days")

        # Get configured W' value used for balance calculations
        # Note: This is from settings (e.g., 13000 J), not the CP model computed value
        w_prime_config = get_metric(activity, "w_prime_config")

        if w_prime_config is not None and w_prime_balance_min is not None:
            # Display W' metrics from pre-computed data
            c1, c2 = st.columns(2)
            render_metric(
                c1,
                "Total W'",
                f"{(w_prime_config / 1000):.1f} kJ",
                help_text="Configured anaerobic work capacity used for W' balance tracking",
            )
            render_metric(
                c2,
                "Min W'",
                f"{(w_prime_balance_min / 1000):.1f} kJ",
                help_text="Lowest W' balance reached during ride",
            )

            # W' depletion percentage (pre-computed)
            if w_prime_depletion is not None:
                status = get_metric_status("w_prime_depletion", w_prime_depletion)
                st.markdown(
                    f"**W' Depletion:** {status.get('emoji', '')} {w_prime_depletion:.0f}% ({status.get('label', '')})"
                )

            # Display CP window if available
            if cp_window_days:
                st.caption(f"CP model window: {cp_window_days:.0f} days")
        else:
            st.info("W' Balance data not available. Ensure CP and W' are configured in settings.")

    # HR Recovery Rate
    with col_recovery:
        st.markdown("#### 💓 HR Recovery")
        max_hr = get_metric(activity, "max_hr")
        avg_hr = get_metric(activity, "average_hr")
        hr_recovery = get_metric(activity, "hr_recovery_rate")

        c1, c2 = st.columns(2)
        render_metric(
            c1,
            "Max HR",
            f"{max_hr:.0f} bpm" if max_hr else "-",
            help_text="Peak heart rate during activity",
        )
        render_metric(
            c2,
            "Avg HR",
            f"{avg_hr:.0f} bpm" if avg_hr else "-",
            help_text="Time-weighted average heart rate",
        )

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
            st.markdown(
                f"**Recovery Rate:** {recovery_emoji} {hr_recovery:.1f} bpm/min ({recovery_label})"
            )
            st.caption("HR drop per minute during rest periods")
        else:
            st.caption(
                "HR recovery rate requires rest periods detected in the activity."
            )


def render_power_and_hr_zone_distributions(activity: Activity, help_texts: dict) -> None:
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

    col_power_zones, col_hr_zones = st.columns(2)

    with col_power_zones:
        st.markdown("##### ⚡ Power Zone Distribution")
        if power_total > 0:
            power_zones_pct = [z / power_total * 100 for z in power_zones]
            # Get pre-computed zone boundaries from activity
            zone_boundaries = [
                get_metric(activity, f"power_zone_{i}") for i in range(1, 7)
            ]
            # Create custom hover text with zone ranges and watts
            hover_text = []
            for i, pct in enumerate(power_zones_pct):
                zone_num = i + 1
                range_str = POWER_ZONE_RANGES[zone_num]
                if zone_num < 7 and i < len(zone_boundaries) and zone_boundaries[i]:
                    # Z1-Z6: show range from previous boundary to current boundary
                    lower = (
                        int(zone_boundaries[i - 1])
                        if i > 0 and zone_boundaries[i - 1]
                        else 0
                    )
                    upper = int(zone_boundaries[i])
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} ({lower}-{upper}W)"
                    )
                elif zone_num == 7 and i > 0 and zone_boundaries[i - 1]:
                    # Z7: show > highest boundary
                    lower = int(zone_boundaries[i - 1])
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} (>{lower}W)"
                    )
                else:
                    # Fallback if boundaries not available
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str}"
                    )
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
            st.plotly_chart(fig_pz, width="stretch")
        else:
            st.info("No power zone data available.")

    with col_hr_zones:
        st.markdown("##### ❤️ HR Zone Distribution")
        if hr_total > 0:
            hr_zones_pct = [z / hr_total * 100 for z in hr_zones]
            # Get pre-computed zone boundaries from activity
            zone_boundaries = [
                get_metric(activity, f"hr_zone_{i}") for i in range(1, 6)
            ]
            # Create custom hover text with zone ranges and bpm
            hover_text = []
            for i, pct in enumerate(hr_zones_pct):
                zone_num = i + 1
                range_str = HR_ZONE_RANGES[zone_num]
                if zone_num < 5 and i < len(zone_boundaries) and zone_boundaries[i]:
                    # Z1-Z4: show range from previous boundary to current boundary
                    lower = (
                        int(zone_boundaries[i - 1])
                        if i > 0 and zone_boundaries[i - 1]
                        else 0
                    )
                    upper = int(zone_boundaries[i])
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} ({lower}-{upper} bpm)"
                    )
                elif zone_num == 5 and i > 0 and zone_boundaries[i - 1]:
                    # Z5: show > highest boundary
                    lower = int(zone_boundaries[i - 1])
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str} (>{lower} bpm)"
                    )
                else:
                    # Fallback if boundaries not available
                    hover_text.append(
                        f"<b>Z{zone_num}</b><br>{pct:.1f}% time<br>{range_str}"
                    )
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
            st.plotly_chart(fig_hz, width="stretch")
        else:
            st.info("No HR zone data available.")


def render_power_and_hr_tid(activity: Activity, help_texts: dict) -> None:

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

    # ===== ROW 2: TID Metrics (aligned) =====
    col_power_tid, col_hr_tid = st.columns(2)

    with col_power_tid:
        st.markdown("##### Power Training Intensity Distribution")

        power_type = get_metric(activity, "power_tid_classification")
        render_metric(
            col_power_tid,
            "Type",
            power_type if power_type else "-",
            get_help_text("tid_classification", help_texts),
        )

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
            st.plotly_chart(fig_tid, width="stretch")

    with col_hr_tid:
        st.markdown("##### HR Training Intensity Distribution")

        hr_type = get_metric(activity, "hr_tid_classification")
        render_metric(
            col_hr_tid,
            "Type",
            hr_type if hr_type else "-",
            get_help_text("tid_classification", help_texts),
        )

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
            st.plotly_chart(fig_hr_tid, width="stretch")


def render_power_hr_tab(
    activity: Activity,
    service: ActivityService,
    metric_view: str,
    help_texts: dict,
) -> None:
    """Render the Power & Heart Rate analysis tab."""
    st.subheader(f"Power & Heart Rate Analysis ({metric_view})")

    # Power curve
    render_power_curve(activity, service, help_texts)
    st.divider()

    # Summary Stats (two columns, aligned)
    render_summary_stats(activity, help_texts)
    st.divider()

    # Critical Power Model
    render_critical_power_model(activity, help_texts)
    st.divider()

    # Enhanced Power-HR Metrics
    render_anaerobic_recovery_metrics(activity, help_texts)
    st.divider()

    # Power and HR Zone Distributions (aligned)
    render_power_and_hr_zone_distributions(activity, help_texts)
    st.divider()

    # Power and HR TID Metrics (aligned)
    render_power_and_hr_tid(activity, help_texts)
