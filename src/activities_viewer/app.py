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
    from activities_viewer.services.goal_service import GoalService
    from activities_viewer.services.analysis_service import AnalysisService
    from activities_viewer.domain.models import Goal
    from activities_viewer.pages.components.dashboard_components import (
        render_goal_progress_card,
        render_status_card,
        render_recent_activity_sparklines,
        render_training_calendar,
        render_wkg_trend_chart,
    )
except ImportError:
    # Fallback for when running directly from source without package installation
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from activities_viewer import __version__
    from activities_viewer.config import Settings, load_settings
    from activities_viewer.repository.csv_repo import CSVActivityRepository
    from activities_viewer.services.activity_service import ActivityService
    from activities_viewer.services.goal_service import GoalService
    from activities_viewer.services.analysis_service import AnalysisService
    from activities_viewer.domain.models import Goal
    from activities_viewer.pages.components.dashboard_components import (
        render_goal_progress_card,
        render_status_card,
        render_recent_activity_sparklines,
        render_training_calendar,
        render_wkg_trend_chart,
    )

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
    else:
        # Fallback or future SQL implementation
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


def main():
    """Main application entry point."""
    # Load settings from environment variable (passed by CLI) or session state
    if "settings" not in st.session_state:
        settings = None

        # Try to load from environment variable first (set by CLI)
        config_json = os.environ.get("ACTIVITIES_VIEWER_CONFIG")
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

    # Get all activities for dashboard
    df_all = service.get_all_activities()

    if df_all.empty:
        st.warning("⚠️ No activity data found. Please check your configuration.")
        st.stop()

    # ═══════════════════════════════════════════════════════════════════════════
    # GOAL PROGRESS CARD (if goal is configured)
    # ═══════════════════════════════════════════════════════════════════════════

    if settings.target_wkg and settings.target_date:
        try:
            from datetime import datetime

            # Create Goal object from settings
            baseline_ftp = (
                settings.baseline_ftp
                if hasattr(settings, "baseline_ftp") and settings.baseline_ftp
                else settings.ftp
            )
            baseline_date = (
                datetime.strptime(settings.baseline_date, "%Y-%m-%d")
                if hasattr(settings, "baseline_date") and settings.baseline_date
                else datetime.now()
            )
            target_date = datetime.strptime(settings.target_date, "%Y-%m-%d")

            goal = Goal(
                target_wkg=settings.target_wkg,
                target_date=target_date,
                start_wkg=baseline_ftp / settings.weight_kg,
                start_date=baseline_date,
            )

            # Instantiate GoalService
            goal_service = GoalService()

            # Render goal progress card
            render_goal_progress_card(
                goal=goal,
                current_ftp=settings.ftp,
                weight_kg=settings.weight_kg,
                goal_service=goal_service,
            )

            st.divider()

            # ═══════════════════════════════════════════════════════════════════════════
            # W/KG TREND CHART
            # ═══════════════════════════════════════════════════════════════════════════

            render_wkg_trend_chart(
                activities_df=df_all,
                goal=goal,
                weight_kg=settings.weight_kg,
                months=12,
            )

            st.divider()

        except Exception as e:
            st.error(f"Error rendering goal progress: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # CURRENT STATUS CARD (PMC)
    # ═══════════════════════════════════════════════════════════════════════════

    try:
        analysis_service = AnalysisService()
        pmc_data = analysis_service.get_pmc_data(df_all)

        render_status_card(pmc_data)

        st.divider()

    except Exception as e:
        st.error(f"Error rendering status card: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # RECENT ACTIVITY SPARKLINES
    # ═══════════════════════════════════════════════════════════════════════════

    try:
        render_recent_activity_sparklines(df_all, days=7)

        st.divider()

    except Exception as e:
        st.error(f"Error rendering activity sparklines: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING CALENDAR HEAT MAP
    # ═══════════════════════════════════════════════════════════════════════════

    try:
        render_training_calendar(df_all, months=3)

        st.divider()

    except Exception as e:
        st.error(f"Error rendering training calendar: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # NAVIGATION INFO
    # ═══════════════════════════════════════════════════════════════════════════

    st.markdown("""
    ### 🚀 Navigation
    Use the sidebar to explore your training data in detail:

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
