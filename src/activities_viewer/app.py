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

import streamlit as st

try:
    from activities_viewer import __version__
    from activities_viewer.config import Settings, load_settings
    from activities_viewer.repository.csv_repo import CSVActivityRepository
    from activities_viewer.services.activity_service import ActivityService
except ImportError:
    # Fallback for when running directly from source without package installation
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from activities_viewer import __version__
    from activities_viewer.config import Settings, load_settings
    from activities_viewer.repository.csv_repo import CSVActivityRepository
    from activities_viewer.services.activity_service import ActivityService

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

    st.markdown(
        """
        ## Welcome to Activities Viewer

        A comprehensive dashboard for analyzing your cycling activities from Strava.

        ### 📊 Features

        - **Year Overview**: Annual statistics, training load trends, and zone distribution
        - **Weekly Analysis**: Recent performance tracking and week-over-week comparisons
        - **Activity Details**: Deep-dive analysis with route maps and power profiles

        ### 🚀 Getting Started

        Use the sidebar to navigate between different views of your training data.

        ---

        **Status**: 🚧 Under Development - Phase 1 (MVP)
        """
    )

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

        st.header("⚙️ Athlete Settings")
        st.metric("FTP", f"{settings.ftp:.0f} W")
        st.metric("Weight", f"{settings.weight_kg:.1f} kg")
        st.metric("Max HR", f"{settings.max_hr} bpm")

        st.divider()

        st.header("📁 Data Configuration")
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
