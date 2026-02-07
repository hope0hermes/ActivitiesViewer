"""
CSV implementation of the ActivityRepository.
"""

from datetime import date
from pathlib import Path

import pandas as pd

from activities_viewer.domain.models import Activity, YearSummary
from activities_viewer.repository.base import ActivityRepository


def _load_activities_df(file_path: Path) -> pd.DataFrame:
    """
    Load and preprocess the activities CSV.
    No caching - loads fresh from disk on every call.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Activities file not found: {file_path}")

    # Read CSV with semicolon separator
    # low_memory=False prevents mixed type warnings for large files
    df = pd.read_csv(file_path, sep=";", low_memory=False)

    # Convert date columns
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["start_date_local"] = pd.to_datetime(df["start_date_local"])

    # Ensure numeric columns are correct types (handling potential NaNs)
    numeric_cols = [
        "distance",
        "moving_time",
        "elapsed_time",
        "total_elevation_gain",
        "average_watts",
        "normalized_power",
        "training_stress_score",
        "chronic_training_load",
        "acute_training_load",
        "training_stress_balance",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by date descending (most recent first)
    df = df.sort_values("start_date_local", ascending=False).reset_index(drop=True)

    return df


class CSVActivityRepository(ActivityRepository):
    """
    Repository that reads from local CSV files (exported by StravaAnalyzer).
    Supports both new dual-file format (raw/moving) and legacy single-file format.
    """

    def __init__(self, raw_file_path: Path, moving_file_path: Path | None = None, streams_dir: Path | None = None):
        """Initialize with dual-file paths (new format) or fallback to single file (legacy)."""
        self.raw_file_path = raw_file_path
        self.moving_file_path = moving_file_path
        self.streams_dir = streams_dir

        # Store file paths but reload data on each access (no instance-level caching)
        # This ensures fresh data is loaded even when session_state persists the repository

    def _ensure_data_loaded(self) -> None:
        """Load data if not already loaded in this request."""
        # Load raw data (or fallback to enriched file if moving not provided)
        self._df_raw = _load_activities_df(self.raw_file_path)

        # Load moving data if available
        if self.moving_file_path and self.moving_file_path.exists():
            self._df_moving = _load_activities_df(self.moving_file_path)
        else:
            # Fallback: use raw data as moving data if not available
            self._df_moving = self._df_raw.copy()

    def get_activity(self, activity_id: int) -> Activity | None:
        """Get activity from raw dataset (default)."""
        self._ensure_data_loaded()
        row = self._df_raw[self._df_raw["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    def get_activity_raw(self, activity_id: int) -> Activity | None:
        """Get activity from raw dataset (all data points)."""
        self._ensure_data_loaded()
        row = self._df_raw[self._df_raw["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    def get_activity_moving(self, activity_id: int) -> Activity | None:
        """Get activity from moving dataset (motion only)."""
        self._ensure_data_loaded()
        row = self._df_moving[self._df_moving["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    @property
    def all_activities(self) -> list[Activity]:
        """Get all activities from raw dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_raw)

    @property
    def all_activities_raw(self) -> list[Activity]:
        """Get all activities from raw dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_raw)

    @property
    def all_activities_moving(self) -> list[Activity]:
        """Get all activities from moving dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_moving)

    def get_activities(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_raw, start_date, end_date)

    def get_activities_raw(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        """Get activities from raw (all data points) dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_raw, start_date, end_date)

    def get_activities_moving(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        """Get activities from moving (motion only) dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._df_moving, start_date, end_date)

    def get_dataframe_raw(self) -> pd.DataFrame:
        """Get raw activities dataframe (all data points)."""
        self._ensure_data_loaded()
        return self._df_raw.copy()

    def get_dataframe_moving(self) -> pd.DataFrame:
        """Get moving activities dataframe (motion only)."""
        self._ensure_data_loaded()
        return self._df_moving.copy()

    def _get_activities_from_df(
        self,
        df: pd.DataFrame,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Activity]:
        """Helper to get activities from a specific dataframe."""
        df_filtered = df

        if start_date:
            df_filtered = df_filtered[
                df_filtered["start_date_local"].dt.date >= start_date
            ]

        if end_date:
            df_filtered = df_filtered[
                df_filtered["start_date_local"].dt.date <= end_date
            ]

        # Convert to list of Activity objects
        # iterrows is slow, but for <2000 activities it's acceptable for MVP.
        # For better performance, we can use to_dict('records')
        return [Activity(**record) for record in df_filtered.to_dict("records")]

    def get_year_summary(self, year: int) -> YearSummary:
        self._ensure_data_loaded()
        df_year = self._df_raw[self._df_raw["start_date_local"].dt.year == year]

        if df_year.empty:
            return YearSummary(
                year=year,
                total_distance=0,
                total_time=0,
                total_elevation=0,
                activity_count=0,
            )

        return YearSummary(
            year=year,
            total_distance=df_year["distance"].sum(),
            total_time=df_year["moving_time"].sum(),
            total_elevation=df_year["total_elevation_gain"].sum(),
            activity_count=len(df_year),
            avg_power=df_year["normalized_power"].mean()
            if "normalized_power" in df_year.columns
            else None,
            total_tss=df_year["training_stress_score"].sum()
            if "training_stress_score" in df_year.columns
            else None,
        )

    def get_activity_stream(self, activity_id: int) -> pd.DataFrame:
        """
        Load stream data for a specific activity.
        Uses configured streams_dir or falls back to default location.
        """
        # Use configured streams_dir if available, otherwise fall back to legacy path
        if self.streams_dir is not None:
            streams_dir = self.streams_dir
        else:
            # Legacy fallback: Assuming raw_file_path is .../data_enriched/activities_raw.csv
            # And streams are in .../data/Streams/stream_{id}.csv
            streams_dir = self.raw_file_path.parent.parent / "data" / "Streams"

        stream_file = streams_dir / f"stream_{activity_id}.csv"

        if not stream_file.exists():
            print(f"Stream file not found: {stream_file}")
            return pd.DataFrame()

        try:
            return pd.read_csv(stream_file, sep=";")
        except Exception:
            return pd.DataFrame()
