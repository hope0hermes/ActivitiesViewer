"""CSV implementation of the ActivityRepository.

Uses file-modification-time (mtime) caching so that CSV data is only re-read
from disk when the underlying file has actually changed.  This avoids the
previous behaviour of unconditionally reloading ~190-column DataFrames on
every single method call (13 call-sites).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from activities_viewer.domain.models import Activity, YearSummary
from activities_viewer.repository.base import ActivityRepository

logger = logging.getLogger(__name__)

# Columns that should *not* be coerced to numeric (dates are handled
# separately; these are genuine string / mixed-type columns).
_NON_NUMERIC_COLUMNS: frozenset[str] = frozenset(
    {
        # Identity / text
        "name",
        "type",
        "sport_type",
        "gear_id",
        "timezone",
        "location_city",
        "location_state",
        "location_country",
        "visibility",
        "device_name",
        "upload_id_str",
        "external_id",
        # Geo / polyline
        "start_latlng",
        "end_latlng",
        "map.id",
        "map.summary_polyline",
        # Dates (converted explicitly below)
        "start_date",
        "start_date_local",
        # Classification strings from TID analysis
        "power_tid_classification",
        "hr_tid_classification",
    }
)


def _load_activities_df(file_path: Path) -> pd.DataFrame:
    """Load and preprocess an activities CSV exported by StravaAnalyzer.

    Numeric coercion is applied broadly: every column that is *not* a known
    date or string column is coerced via ``pd.to_numeric(errors='coerce')``.
    This replaces the previous approach of hard-coding 10 column names and
    ensures all ~190 metric columns are loaded with correct dtypes.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Activities file not found: {file_path}")

    # Read CSV with semicolon separator
    # low_memory=False prevents mixed type warnings for large files
    df = pd.read_csv(file_path, sep=";", low_memory=False)

    # Convert date columns
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["start_date_local"] = pd.to_datetime(df["start_date_local"])

    # Broad numeric coercion — skip known string/date columns
    for col in df.columns:
        if col not in _NON_NUMERIC_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by date descending (most recent first)
    df = df.sort_values("start_date_local", ascending=False).reset_index(drop=True)

    return df


class CSVActivityRepository(ActivityRepository):
    """Repository that reads from local CSV files (exported by StravaAnalyzer).

    Supports both new dual-file format (raw/moving) and legacy single-file
    format.  Uses **mtime-based caching** so data is only reloaded from disk
    when a file has actually been modified.
    """

    def __init__(
        self,
        raw_file_path: Path,
        moving_file_path: Path | None = None,
        streams_dir: Path | None = None,
    ) -> None:
        self.raw_file_path = raw_file_path
        self.moving_file_path = moving_file_path
        self.streams_dir = streams_dir

        # Cached DataFrames + their mtime at load time
        self._df_raw: pd.DataFrame | None = None
        self._df_moving: pd.DataFrame | None = None
        self._raw_mtime: float = 0.0
        self._moving_mtime: float = 0.0

    # ── Cache management ──────────────────────────────────────────────────

    def _ensure_data_loaded(self) -> None:
        """Reload CSVs only when the file on disk has changed."""
        # --- raw file ---
        raw_mtime = (
            self.raw_file_path.stat().st_mtime
            if self.raw_file_path.exists()
            else 0.0
        )
        if self._df_raw is None or raw_mtime != self._raw_mtime:
            logger.debug("Loading raw CSV: %s", self.raw_file_path)
            self._df_raw = _load_activities_df(self.raw_file_path)
            self._raw_mtime = raw_mtime

        # --- moving file ---
        if self.moving_file_path and self.moving_file_path.exists():
            moving_mtime = self.moving_file_path.stat().st_mtime
            if self._df_moving is None or moving_mtime != self._moving_mtime:
                logger.debug("Loading moving CSV: %s", self.moving_file_path)
                self._df_moving = _load_activities_df(self.moving_file_path)
                self._moving_mtime = moving_mtime
        elif self._df_moving is None:
            # Fallback: use raw data as moving data if not available
            self._df_moving = self._df_raw.copy()

        # Post-condition: both DataFrames are guaranteed non-None after this
        # method returns.  The assert satisfies mypy and guards against bugs.
        assert self._df_raw is not None  # noqa: S101
        assert self._df_moving is not None  # noqa: S101

    @property
    def _raw(self) -> pd.DataFrame:
        """Return the raw DataFrame, guaranteed non-None after ``_ensure_data_loaded``."""
        assert self._df_raw is not None  # noqa: S101
        return self._df_raw

    @property
    def _moving(self) -> pd.DataFrame:
        """Return the moving DataFrame, guaranteed non-None after ``_ensure_data_loaded``."""
        assert self._df_moving is not None  # noqa: S101
        return self._df_moving

    def invalidate_cache(self) -> None:
        """Force the next access to reload from disk."""
        self._df_raw = None
        self._df_moving = None
        self._raw_mtime = 0.0
        self._moving_mtime = 0.0

    def get_activity(self, activity_id: int) -> Activity | None:
        """Get activity from raw dataset (default)."""
        self._ensure_data_loaded()
        row = self._raw[self._raw["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    def get_activity_raw(self, activity_id: int) -> Activity | None:
        """Get activity from raw dataset (all data points)."""
        self._ensure_data_loaded()
        row = self._raw[self._raw["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    def get_activity_moving(self, activity_id: int) -> Activity | None:
        """Get activity from moving dataset (motion only)."""
        self._ensure_data_loaded()
        row = self._moving[self._moving["id"] == activity_id]
        if row.empty:
            return None

        return Activity(**row.iloc[0].to_dict())

    @property
    def all_activities(self) -> list[Activity]:
        """Get all activities from raw dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._raw)

    @property
    def all_activities_raw(self) -> list[Activity]:
        """Get all activities from raw dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._raw)

    @property
    def all_activities_moving(self) -> list[Activity]:
        """Get all activities from moving dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._moving)

    def get_activities(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._raw, start_date, end_date)

    def get_activities_raw(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        """Get activities from raw (all data points) dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._raw, start_date, end_date)

    def get_activities_moving(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[Activity]:
        """Get activities from moving (motion only) dataset."""
        self._ensure_data_loaded()
        return self._get_activities_from_df(self._moving, start_date, end_date)

    def get_dataframe_raw(self) -> pd.DataFrame:
        """Get raw activities dataframe (all data points)."""
        self._ensure_data_loaded()
        return self._raw.copy()

    def get_dataframe_moving(self) -> pd.DataFrame:
        """Get moving activities dataframe (motion only)."""
        self._ensure_data_loaded()
        return self._moving.copy()

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
        df_year = self._raw[self._raw["start_date_local"].dt.year == year]

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
            logger.warning("Stream file not found: %s", stream_file)
            return pd.DataFrame()

        try:
            return pd.read_csv(stream_file, sep=";")
        except Exception:
            return pd.DataFrame()
