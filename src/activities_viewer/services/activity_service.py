"""
Service layer for Activity-related business logic.
"""

from typing import List, Optional
from datetime import date
import pandas as pd

from activities_viewer.domain.models import Activity, YearSummary
from activities_viewer.repository.base import ActivityRepository


class ActivityService:
    """
    Service for managing activities.
    Decouples the UI from the Repository.
    """

    def __init__(self, repository: ActivityRepository):
        self.repository = repository

    def get_activity(self, activity_id: int, metric_view: str = "Moving Time") -> Optional[Activity]:
        """Get a single activity with support for metric_view selection."""
        if metric_view == "Raw Time" and hasattr(self.repository, 'get_activity_raw'):
            return self.repository.get_activity_raw(activity_id)
        elif hasattr(self.repository, 'get_activity_moving'):
            return self.repository.get_activity_moving(activity_id)
        return self.repository.get_activity(activity_id)

    def get_activities_for_year(self, year: int, metric_view: str = "Moving Time") -> List[Activity]:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        if metric_view == "Raw Time" and hasattr(self.repository, 'get_activities_raw'):
            return self.repository.get_activities_raw(start_date, end_date)
        elif hasattr(self.repository, 'get_activities_moving'):
            return self.repository.get_activities_moving(start_date, end_date)
        return self.repository.get_activities(start_date, end_date)

    def get_year_summary(self, year: int) -> YearSummary:
        return self.repository.get_year_summary(year)

    def get_available_years(self) -> List[int]:
        """
        Get a list of years available in the dataset.
        This might require extending the repository interface or just fetching all and extracting years.
        For MVP, fetching all is fine.
        """
        # Optimization: Add get_years() to Repository later.
        all_activities = self.repository.get_activities()
        years = {a.start_date_local.year for a in all_activities}
        return sorted(list(years), reverse=True)

    def get_all_activities(self, metric_view: str = "Moving Time") -> "pd.DataFrame":
        """
        Get all activities as a pandas DataFrame.

        Args:
            metric_view: Either "Raw Time" or "Moving Time" to select dataset.
        """
        if metric_view == "Raw Time" and hasattr(self.repository, 'get_dataframe_raw'):
            return self.repository.get_dataframe_raw()
        elif hasattr(self.repository, 'get_dataframe_moving'):
            return self.repository.get_dataframe_moving()

        activities = self.repository.get_activities()
        if not activities:
            return pd.DataFrame()
        return pd.DataFrame([a.model_dump() for a in activities])

    def get_recent_activities(self, count: int = 10, metric_view: str = "Moving Time") -> "pd.DataFrame":
        """
        Get the most recent activities as a pandas DataFrame.

        Args:
            count: Number of recent activities to return.
            metric_view: Either "Raw Time" or "Moving Time" to select dataset.

        Returns:
            DataFrame with the most recent activities, sorted by date descending.
        """
        df = self.get_all_activities(metric_view)
        if df.empty:
            return df
        # Sort by start_date_local descending and take the first `count`
        df = df.sort_values("start_date_local", ascending=False)
        return df.head(count)

    def get_activity_stream(self, activity_id: int) -> "pd.DataFrame":
        """
        Get the stream data for an activity.
        """
        # This requires the repository to support streams, which the base protocol currently doesn't show.
        # Assuming the underlying repository might have it or we need to add it.
        # For now, let's check the repository implementation.
        if hasattr(self.repository, 'get_activity_stream'):
             return self.repository.get_activity_stream(activity_id)
        return pd.DataFrame()
