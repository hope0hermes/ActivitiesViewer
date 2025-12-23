"""
Repository interface definition.
"""

from typing import Protocol, List, Optional
from datetime import date
from activities_viewer.domain.models import Activity, YearSummary


class ActivityRepository(Protocol):
    """
    Interface for accessing activity data.
    Implementations can be CSV-based, SQL-based, etc.
    """

    def get_activity(self, activity_id: int) -> Optional[Activity]:
        """Retrieve a single activity by ID."""
        ...

    def get_activities(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Activity]:
        """
        Retrieve a list of activities, optionally filtered by date range.
        """
        ...

    def get_year_summary(self, year: int) -> YearSummary:
        """
        Retrieve aggregated statistics for a specific year.
        """
        ...
