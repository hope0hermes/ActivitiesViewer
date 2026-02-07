"""
Repository interface definition.
"""

from datetime import date
from typing import Protocol

from activities_viewer.domain.models import Activity, YearSummary


class ActivityRepository(Protocol):
    """
    Interface for accessing activity data.
    Implementations can be CSV-based, SQL-based, etc.
    """

    def get_activity(self, activity_id: int) -> Activity | None:
        """Retrieve a single activity by ID."""
        ...

    def get_activities(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        """
        Retrieve a list of activities, optionally filtered by date range.
        """
        ...

    def get_year_summary(self, year: int) -> YearSummary:
        """
        Retrieve aggregated statistics for a specific year.
        """
        ...
