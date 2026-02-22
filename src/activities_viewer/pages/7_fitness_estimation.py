"""
Fitness Auto-Estimation Page.

Estimate FTP from 20-minute power peaks and max HR from hard efforts
in historical activity data. Helps users configure their athlete profile
without lab testing.
"""

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from activities_viewer.config import Settings
from activities_viewer.repository.csv_repo import CSVActivityRepository
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.services.fitness_estimation import (
    compute_rolling_ftp,
    estimate_ftp_from_activities,
    estimate_max_hr_from_activities,
    estimate_weight_trend,
)

st.set_page_config(page_title="Fitness Estimation", page_icon="📈", layout="wide")


# ─── Service initialization ──────────────────────────────────────────────


def init_services(settings: Settings) -> ActivityService:
    """Initialize activity service."""
    raw_file = (
        settings.activities_raw_file
        if hasattr(settings, "activities_raw_file")
        else settings.activities_enriched_file
    )
    moving_file = (
        settings.activities_moving_file
        if hasattr(settings, "activities_moving_file")
        else None
    )
    repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)
    return ActivityService(repo)


# ─── Charts ──────────────────────────────────────────────────────────────


def plot_ftp_history(ftp_df: pd.DataFrame, current_ftp: float) -> go.Figure:
    """Plot FTP estimation history with current FTP reference line."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ftp_df["date"],
        y=ftp_df["estimated_ftp"],
        mode="markers",
        name="Estimated FTP (95% of 20min)",
        marker={"size": 8, "color": "#1f77b4"},
        text=ftp_df["activity_name"],
        hovertemplate="%{x|%Y-%m-%d}<br>FTP: %{y:.0f}W<br>%{text}<extra></extra>",
    ))

    # Rolling FTP trend
    rolling = compute_rolling_ftp(ftp_df)
    if not rolling.empty:
        fig.add_trace(go.Scatter(
            x=rolling["date"],
            y=rolling["rolling_ftp"],
            mode="lines",
            name="42-day rolling max",
            line={"color": "#ff7f0e", "width": 2},
        ))

    # Current FTP reference
    fig.add_hline(
        y=current_ftp,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Current FTP: {current_ftp:.0f}W",
    )

    fig.update_layout(
        title="FTP Estimation History",
        xaxis_title="Date",
        yaxis_title="Power (W)",
        height=400,
        hovermode="x unified",
    )
    return fig


def plot_max_hr_history(hr_df: pd.DataFrame, current_max_hr: int) -> go.Figure:
    """Plot max HR observations across activities."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hr_df["date"],
        y=hr_df["max_hr_recorded"],
        mode="markers",
        name="Max HR recorded",
        marker={"size": 8, "color": "#d62728"},
        text=hr_df["activity_name"],
        hovertemplate="%{x|%Y-%m-%d}<br>Max HR: %{y} bpm<br>%{text}<extra></extra>",
    ))

    fig.add_hline(
        y=current_max_hr,
        line_dash="dash",
        line_color="blue",
        annotation_text=f"Current Max HR: {current_max_hr} bpm",
    )

    fig.update_layout(
        title="Max Heart Rate Observations",
        xaxis_title="Date",
        yaxis_title="Heart Rate (bpm)",
        height=400,
    )
    return fig


# ─── Main page ───────────────────────────────────────────────────────────


def main():
    """Main page entry point."""
    if "settings" not in st.session_state:
        config_json = os.environ.get("ACTIVITIES_VIEWER_CONFIG")
        if config_json:
            try:
                config_data = json.loads(config_json)
                st.session_state.settings = Settings(**config_data)
            except Exception as e:
                st.error(f"Failed to load configuration: {e}")
                st.stop()
        else:
            st.info("⏳ Waiting for configuration... Please navigate from the main page.")
            st.stop()

    settings = st.session_state.settings

    st.title("📈 Fitness Auto-Estimation")
    st.markdown(
        """
        Estimate your key fitness parameters from your activity data.
        These estimates help you configure your athlete profile without
        requiring lab testing.

        **How it works:**
        - **FTP**: Estimated as 95% of your best 20-minute power (Coggan protocol)
        - **Max HR**: Observed from the highest heart rates recorded during hard efforts
        - **Weight**: Tracked from activity data if available
        """
    )

    # Load data
    try:
        service = init_services(settings)
        df = service.get_all_activities()
    except Exception as e:
        st.error(f"Failed to load activities: {e}")
        st.stop()

    if df.empty:
        st.warning("No activity data available.")
        st.stop()

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════
    # FTP ESTIMATION
    # ═══════════════════════════════════════════════════════════════════════

    st.header("⚡ FTP Estimation")

    ftp_df = estimate_ftp_from_activities(df)
    if ftp_df.empty:
        st.info(
            "No 20-minute power data found in your activities. "
            "This typically comes from rides with a power meter."
        )
    else:
        col1, col2, col3 = st.columns(3)
        best_ever = ftp_df["estimated_ftp"].max()
        recent_best = (
            ftp_df.loc[ftp_df["date"] >= ftp_df["date"].max() - pd.Timedelta(days=42)]
            ["estimated_ftp"].max()
        )

        with col1:
            st.metric("Current FTP (config)", f"{settings.ftp:.0f} W")
        with col2:
            st.metric(
                "Best estimate (all-time)",
                f"{best_ever:.0f} W",
                delta=f"{best_ever - settings.ftp:+.0f} W" if best_ever != settings.ftp else None,
            )
        with col3:
            st.metric(
                "Best estimate (last 42 days)",
                f"{recent_best:.0f} W",
                delta=f"{recent_best - settings.ftp:+.0f} W" if recent_best != settings.ftp else None,
            )

        # Chart
        st.plotly_chart(
            plot_ftp_history(ftp_df, settings.ftp),
            use_container_width=True,
        )

        # Data table
        with st.expander("📋 All FTP estimates", expanded=False):
            display_df = ftp_df.copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df.columns = ["Date", "Best 20min (W)", "Est. FTP (W)", "Activity"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════
    # MAX HR ESTIMATION
    # ═══════════════════════════════════════════════════════════════════════

    st.header("❤️ Max Heart Rate Estimation")

    hr_df = estimate_max_hr_from_activities(df)
    if hr_df.empty:
        st.info(
            "No heart rate data found in your activities. "
            "This requires a heart rate monitor."
        )
    else:
        col1, col2, col3 = st.columns(3)
        observed_max = hr_df["max_hr_recorded"].max()
        # Top 5 average (more robust than single peak)
        top5_avg = hr_df.head(5)["max_hr_recorded"].mean()

        with col1:
            st.metric("Current Max HR (config)", f"{settings.max_hr} bpm")
        with col2:
            st.metric(
                "Highest observed",
                f"{observed_max} bpm",
                delta=f"{observed_max - settings.max_hr:+d} bpm"
                if observed_max != settings.max_hr else None,
            )
        with col3:
            st.metric(
                "Top-5 average",
                f"{top5_avg:.0f} bpm",
                help="Average of your 5 highest recorded heart rates (more reliable than a single peak).",
            )

        # Sort by date for chart display
        hr_by_date = hr_df.sort_values("date")
        st.plotly_chart(
            plot_max_hr_history(hr_by_date, settings.max_hr),
            use_container_width=True,
        )

        with st.expander("📋 Top heart rate observations", expanded=False):
            display_df = hr_df.head(20).copy()
            display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
            display_df.columns = ["Date", "Max HR (bpm)", "Activity"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════
    # WEIGHT TRACKING
    # ═══════════════════════════════════════════════════════════════════════

    st.header("⚖️ Weight Trend")

    weight_df = estimate_weight_trend(df)
    if weight_df.empty:
        st.info(
            "No weight data found in your activities. "
            "Weight is sometimes recorded in Strava activity metadata."
        )
    else:
        latest = weight_df.iloc[-1]["weight_kg"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Weight (config)", f"{settings.weight_kg:.1f} kg")
        with col2:
            st.metric(
                "Latest from data",
                f"{latest:.1f} kg",
                delta=f"{latest - settings.weight_kg:+.1f} kg"
                if abs(latest - settings.weight_kg) > 0.1 else None,
            )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weight_df["date"],
            y=weight_df["weight_kg"],
            mode="lines+markers",
            name="Weight",
            line={"color": "#2ca02c"},
        ))
        fig.add_hline(
            y=settings.weight_kg,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Config: {settings.weight_kg:.1f} kg",
        )
        fig.update_layout(
            title="Weight Over Time",
            xaxis_title="Date",
            yaxis_title="Weight (kg)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════
    # RECOMMENDATIONS SUMMARY
    # ═══════════════════════════════════════════════════════════════════════

    st.header("💡 Recommendations")

    recommendations = []

    if not ftp_df.empty:
        recent_ftp = ftp_df.loc[
            ftp_df["date"] >= ftp_df["date"].max() - pd.Timedelta(days=42)
        ]["estimated_ftp"].max()
        diff = recent_ftp - settings.ftp
        if abs(diff) > 5:
            direction = "higher" if diff > 0 else "lower"
            recommendations.append(
                f"**FTP:** Your recent 20-min power data suggests an FTP "
                f"of **{recent_ftp:.0f}W** ({abs(diff):.0f}W {direction} "
                f"than your current config of {settings.ftp:.0f}W). "
                f"Consider updating your config."
            )

    if not hr_df.empty:
        observed_max = hr_df["max_hr_recorded"].max()
        if observed_max > settings.max_hr:
            recommendations.append(
                f"**Max HR:** You've recorded a heart rate of **{observed_max} bpm**, "
                f"which is higher than your configured max HR of {settings.max_hr} bpm. "
                f"Consider updating."
            )

    if not weight_df.empty:
        latest_w = weight_df.iloc[-1]["weight_kg"]
        if abs(latest_w - settings.weight_kg) > 1.0:
            recommendations.append(
                f"**Weight:** Your latest recorded weight ({latest_w:.1f} kg) "
                f"differs from your config ({settings.weight_kg:.1f} kg) "
                f"by more than 1 kg. Consider updating."
            )

    if recommendations:
        for rec in recommendations:
            st.markdown(f"- {rec}")
    else:
        st.success("✅ Your current settings appear to match your recent data well!")

    # W/kg summary
    if not ftp_df.empty:
        recent_ftp = ftp_df.loc[
            ftp_df["date"] >= ftp_df["date"].max() - pd.Timedelta(days=42)
        ]["estimated_ftp"].max()
        current_wkg = settings.ftp / settings.weight_kg
        est_wkg = recent_ftp / settings.weight_kg

        st.divider()
        st.subheader("🏋️ W/kg Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current W/kg", f"{current_wkg:.2f}")
        with col2:
            st.metric(
                "Estimated W/kg",
                f"{est_wkg:.2f}",
                delta=f"{est_wkg - current_wkg:+.2f}",
            )


if __name__ == "__main__":
    main()
else:
    main()
