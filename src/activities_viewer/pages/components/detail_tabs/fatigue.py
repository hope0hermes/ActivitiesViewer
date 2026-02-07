import streamlit as st

from activities_viewer.data.help_texts import get_help_text, get_metric_status
from activities_viewer.domain.models import Activity
from activities_viewer.utils.formatting import (
    get_metric,
    render_metric,
)


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
        render_metric(
            c1,
            "Fatigue Index",
            f"{fatigue_idx:.1f}%" if fatigue_idx else "-",
            get_help_text("fatigue_index", help_texts),
        )
        render_metric(
            c2,
            "Power Decay",
            f"{decay_rate:.1f}%" if decay_rate else "-",
            get_help_text("power_decay", help_texts),
        )

        # Power durability metrics
        first_half_power = get_metric(activity, "first_half_power")
        second_half_power = get_metric(activity, "second_half_power")
        power_drift = get_metric(activity, "power_drift")

        st.markdown("##### Power Drift Analysis")
        col_a, col_b = st.columns(2)
        render_metric(
            col_a,
            "First Half Power",
            f"{first_half_power:.0f} W" if first_half_power else "-",
            help_text="Average power during first half of ride",
        )
        render_metric(
            col_b,
            "Second Half Power",
            f"{second_half_power:.0f} W" if second_half_power else "-",
            help_text="Average power during second half of ride",
        )

        # Power Drift with interpretation
        col_c, _ = st.columns([10, 1])
        if power_drift is not None:
            status = get_metric_status("power_drift", power_drift)
            render_metric(
                col_c,
                "Power Drift",
                f"{status.get('emoji', '')} {power_drift:.1f}%",
                get_help_text("power_drift", help_texts),
            )
            if status.get("label"):
                with col_c:
                    st.caption(status["label"])
        else:
            render_metric(
                col_c,
                "Power Drift",
                "-",
                get_help_text("power_drift", help_texts),
            )

    # --- Right Column: HR Fatigue ---
    with col2:
        st.markdown("#### ❤️ Heart Rate Fatigue")

        # HR fatigue metrics from effort distribution
        hr_decoupling = get_metric(activity, "power_hr_decoupling")
        hr_tss = get_metric(activity, "hr_training_stress")
        cardiac_drift = get_metric(activity, "cardiac_drift")
        first_half_hr = get_metric(activity, "first_half_hr")
        second_half_hr = get_metric(activity, "second_half_hr")

        c1, c2 = st.columns(2)
        render_metric(
            c1,
            "HR Decoupling",
            f"{hr_decoupling:.1f}%" if hr_decoupling is not None else "-",
            get_help_text("power_hr_decoupling", help_texts),
        )
        render_metric(
            c2,
            "HR TSS",
            f"{hr_tss:.0f}" if hr_tss else "-",
            get_help_text("hr_training_stress", help_texts),
        )

        st.markdown("##### Effort Distribution")
        col_a, col_b = st.columns(2)
        render_metric(
            col_a,
            "First Half HR",
            f"{first_half_hr:.0f} BPM" if first_half_hr else "-",
            get_help_text("first_half_hr", help_texts),
        )
        render_metric(
            col_b,
            "Second Half HR",
            f"{second_half_hr:.0f} BPM" if second_half_hr else "-",
            get_help_text("second_half_hr", help_texts),
        )

        col_c, _ = st.columns([10, 1])
        # Cardiac Drift with interpretation
        if cardiac_drift is not None:
            status = get_metric_status("cardiac_drift", cardiac_drift)
            render_metric(
                col_c,
                "Cardiac Drift",
                f"{status.get('emoji', '')} {cardiac_drift:.1f}%",
                get_help_text("cardiac_drift", help_texts),
            )
            if status.get("label"):
                with col_c:
                    st.caption(status["label"])
        else:
            render_metric(
                col_c, "Cardiac Drift", "-", get_help_text("cardiac_drift", help_texts)
            )

    st.divider()

    # Interval Distribution Section
    with st.expander("📊 Interval Analysis", expanded=False):
        st.subheader("📊 Interval Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Power Intervals")
            power_trend = get_metric(activity, "interval_300s_power_trend")
            decay_rate = get_metric(activity, "interval_300s_decay_rate")

            col_a, col_b = st.columns(2)
            render_metric(
                col_a,
                "Avg Change",
                f"{power_trend:.2f} W/int" if power_trend else "-",
                get_help_text("interval_300s_power_trend", help_texts),
            )
            render_metric(
                col_b,
                "Decay Rate",
                f"{decay_rate:.1f}%" if decay_rate else "-",
                get_help_text("interval_300s_decay_rate", help_texts),
            )

        with col2:
            st.markdown("##### HR Intervals")

            # HR TID metrics
            hr_tid_z1 = get_metric(activity, "hr_tid_z1_percentage")
            hr_tid_z2 = get_metric(activity, "hr_tid_z2_percentage")
            hr_tid_z3 = get_metric(activity, "hr_tid_z3_percentage")
            hr_polarization = get_metric(activity, "hr_polarization_index")

            col_a, col_b = st.columns(2)
            render_metric(
                col_a,
                "Polarization Index",
                f"{hr_polarization:.2f}" if hr_polarization else "-",
                get_help_text("hr_polarization_index", help_texts),
            )

            st.markdown("**HR Zone Distribution (TID):**")
            col_x, col_y, col_z = st.columns(3)
            render_metric(
                col_x,
                "Z1 %",
                f"{hr_tid_z1:.1f}%" if hr_tid_z1 else "-",
                get_help_text("hr_tid_z1_percentage", help_texts),
            )
            render_metric(
                col_y,
                "Z2 %",
                f"{hr_tid_z2:.1f}%" if hr_tid_z2 else "-",
                get_help_text("hr_tid_z2_percentage", help_texts),
            )
            render_metric(
                col_z,
                "Z3 %",
                f"{hr_tid_z3:.1f}%" if hr_tid_z3 else "-",
                get_help_text("hr_tid_z3_percentage", help_texts),
            )
