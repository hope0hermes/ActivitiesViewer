"""
ActivitiesViewer - A Streamlit dashboard for cycling activities analysis.

This package provides a comprehensive dashboard for visualizing and analyzing
cycling activities data from Strava, including power metrics, training load,
and performance trends.
"""

__version__ = "1.3.0"
__author__ = "Israel Barragan"
__email__ = "abraham0vidal@gmail.com"


def get_version() -> str:
    """Get the current version of activities_viewer."""
    return __version__


def get_package_info() -> dict[str, str]:
    """Get package information including name and version."""
    return {
        "name": "activities-viewer",
        "version": __version__,
        "description": "A Streamlit dashboard for cycling activities analysis",
    }


__all__ = ["__version__", "__author__", "__email__", "get_version", "get_package_info"]
