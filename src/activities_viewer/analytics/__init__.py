"""Analytics modules for Activities Viewer."""

from .insights import Insight, generate_weekly_insights, render_insights

__all__ = ["generate_weekly_insights", "render_insights", "Insight"]
