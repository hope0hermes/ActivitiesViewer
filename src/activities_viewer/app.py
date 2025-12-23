"""
Main Streamlit application entry point for ActivitiesViewer.

This is the main dashboard entry point. It requires a valid configuration
file to be provided via the CLI:

    activities-viewer run --config config.yaml
"""

import logging
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from activities_viewer import __version__
    from activities_viewer.config import Settings, load_settings
    from activities_viewer.repository.csv_repo import CSVActivityRepository
    from activities_viewer.services.activity_service import ActivityService
    from activities_viewer.components.goal_tracker import render_goal_progress
except ImportError:
    # Fallback for when running directly from source without package installation
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from activities_viewer import __version__
    from activities_viewer.config import Settings, load_settings
    from activities_viewer.repository.csv_repo import CSVActivityRepository
    from activities_viewer.services.activity_service import ActivityService
    from activities_viewer.components.goal_tracker import render_goal_progress

logger = logging.getLogger(__name__)


# Configure page before any other streamlit calls
def configure_page(settings: Settings) -> None:
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=settings.page_title,
        page_icon=settings.page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def init_services(settings: Settings) -> ActivityService:
    """Initialize application services."""
    if settings.data_source_type == "csv":
        # Use dual-file format (new) if available, fallback to enriched file (legacy)
        raw_file = settings.activities_raw_file if hasattr(settings, 'activities_raw_file') else settings.activities_enriched_file
        moving_file = settings.activities_moving_file if hasattr(settings, 'activities_moving_file') else None
        repo = CSVActivityRepository(raw_file, moving_file)
    else:
        # Fallback or future SQL implementation
        raw_file = settings.activities_raw_file if hasattr(settings, 'activities_raw_file') else settings.activities_enriched_file
        moving_file = settings.activities_moving_file if hasattr(settings, 'activities_moving_file') else None
        repo = CSVActivityRepository(raw_file, moving_file)

    return ActivityService(repo)


def main():
    """Main application entry point."""
    # Load settings from environment variable (passed by CLI) or session state
    if "settings" not in st.session_state:
        settings = None

        # Try to load from environment variable first (set by CLI)
        config_json = os.environ.get('ACTIVITIES_VIEWER_CONFIG')
        if config_json:
            try:
                config_data = json.loads(config_json)
                settings = Settings(**config_data)
                st.session_state.settings = settings
            except Exception as e:
                st.error(f"Failed to load configuration from CLI: {e}")
                st.stop()
        else:
            # Fallback: try to load from config file in current directory
            config_file = Path("config.yaml")
            if config_file.exists():
                try:
                    settings = load_settings(config_file)
                    st.session_state.settings = settings
                except Exception as e:
                    st.error(f"Failed to load configuration: {e}")
                    st.stop()
            else:
                st.error(
                    """
                    ❌ Configuration file not found!

                    Please run ActivitiesViewer with a configuration file:

                        activities-viewer run --config config.yaml

                    Or place a `config.yaml` file in the current directory.

                    See `examples/config.yaml` for a configuration template.
                    """
                )
                st.stop()

    settings = st.session_state.settings
    configure_page(settings)

    # Initialize Services
    if "activity_service" not in st.session_state:
        try:
            st.session_state.activity_service = init_services(settings)
        except Exception as e:
            st.error(f"Failed to initialize services: {e}")
            st.stop()

    # Main content
    st.title(f"{settings.page_icon} {settings.page_title}")

    service = st.session_state.activity_service

    # Get recent data for quick status
    df_all = service.get_all_activities()
    if not df_all.empty:
        # Current fitness status
        st.header("📊 Current Status")

        # Get most recent CTL/ATL/TSB values
        df_sorted = df_all.sort_values("start_date_local")
        latest = df_sorted.iloc[-1]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            ctl = latest.get("chronic_training_load", 0)
            if ctl and not pd.isna(ctl):
                st.metric("Fitness (CTL)", f"{ctl:.0f}")
            else:
                st.metric("Fitness (CTL)", "N/A")

        with col2:
            atl = latest.get("acute_training_load", 0)
            if atl and not pd.isna(atl):
                st.metric("Fatigue (ATL)", f"{atl:.0f}")
            else:
                st.metric("Fatigue (ATL)", "N/A")

        with col3:
            tsb = latest.get("training_stress_balance", 0)
            if tsb and not pd.isna(tsb):
                status = "Fresh 🔋" if tsb > 10 else "Tired 😴" if tsb < -20 else "Ready 💪"
                st.metric("Form (TSB)", f"{tsb:.0f}", status)
            else:
                st.metric("Form (TSB)", "N/A")

        with col4:
            # This week's TSS
            from datetime import datetime, timedelta
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())

            # Ensure date column is datetime
            df_all_copy = df_all.copy()
            df_all_copy["start_date_local"] = pd.to_datetime(df_all_copy["start_date_local"])

            # Remove timezone if present
            if df_all_copy["start_date_local"].dt.tz is not None:
                df_all_copy["start_date_local"] = df_all_copy["start_date_local"].dt.tz_localize(None)

            # Filter for this week
            df_week = df_all_copy[df_all_copy["start_date_local"] >= week_start]
            week_tss = df_week["training_stress_score"].sum() if not df_week.empty else 0
            st.metric("This Week TSS", f"{week_tss:.0f}")

        st.divider()

        # Recent activities
        st.header("🕐 Recent Activities")
        recent = df_sorted.tail(5).iloc[::-1]  # Last 5, reversed to show newest first

        for _, row in recent.iterrows():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{row['name']}**")
            with col2:
                distance_km = row.get('distance', 0) / 1000 if row.get('distance') else 0
                st.write(f"{distance_km:.1f} km")
            with col3:
                tss = row.get('training_stress_score', 0)
                st.write(f"{tss:.0f} TSS" if tss else "-")
            with col4:
                date = pd.to_datetime(row['start_date_local'])
                st.write(date.strftime("%b %d"))

        st.divider()

        # Goal Progress (if configured)
        render_goal_progress(settings)

    # Keep existing welcome message but shorter
    st.markdown("""
    ### 🚀 Navigation
    Use the sidebar to explore your training data in detail.

    - 📊 **Year Overview**: Annual summary and trends
    - 📅 **Monthly Analysis**: Deep-dive into monthly patterns
    - 📅 **Weekly Analysis**: Recent performance tracking
    - 🚴 **Activity Detail**: Individual ride analysis
    - 🤖 **AI Coach**: Ask questions about your training
    """)

    # Sidebar
    with st.sidebar:
        st.header("📊 Navigation")
        st.info(
            """
            Select a page from the sidebar to explore your activities:

            - 📊 **Year Overview**: Annual summary
            - 📅 **Weekly Analysis**: Recent trends
            - 🚴 **Activity Detail**: Individual rides
            """
        )

        st.divider()

        with st.expander("⚙️ Athlete Settings", expanded=False):
            st.metric("FTP", f"{settings.ftp:.0f} W")
            st.metric("Weight", f"{settings.weight_kg:.1f} kg")
            st.metric("Max HR", f"{settings.max_hr} bpm")

        st.divider()

        with st.expander("📁 Data Configuration", expanded=False):
            try:
                settings.validate_files()
                st.success("✅ All data files found and valid")

                # Show data summary
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("📍 Data Directory")
                    st.code(str(settings.data_dir), language="text")
                with col2:
                    st.caption("📊 Enriched File")
                    st.code(settings.activities_enriched_file.name, language="text")

            except FileNotFoundError as e:
                st.error(f"❌ Configuration Error\n\n{e}")

        st.divider()
        st.caption(f"ActivitiesViewer v{__version__}")


if __name__ == "__main__":
    main()
