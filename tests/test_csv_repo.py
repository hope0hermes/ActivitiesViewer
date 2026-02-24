"""Tests for CSVActivityRepository — caching, numeric coercion, and stream loading."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from activities_viewer.repository.csv_repo import (
    _NON_NUMERIC_COLUMNS,
    CSVActivityRepository,
    _load_activities_df,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal CSV content that exercises date parsing, numeric coercion, and
# the string columns that should *not* be coerced.
_MINIMAL_CSV = """\
id;name;type;sport_type;start_date;start_date_local;distance;moving_time;elapsed_time;total_elevation_gain;average_watts;normalized_power;training_stress_score;power_tid_classification
1;Morning Ride;Ride;MountainBikeRide;2025-06-01T08:00:00Z;2025-06-01T10:00:00+02:00;50000;3600;4000;500;200;210;80;Polarized
2;Evening Run;Run;Run;2025-06-02T17:00:00Z;2025-06-02T19:00:00+02:00;10000;2400;2500;100;;;;"nan"
"""


def _write_csv(path: Path, content: str = _MINIMAL_CSV) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# _load_activities_df
# ---------------------------------------------------------------------------


class TestLoadActivitiesDf:
    """Unit tests for the free-standing loader function."""

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_activities_df(tmp_path / "nope.csv")

    def test_date_columns_are_datetime(self, tmp_path: Path) -> None:
        csv = _write_csv(tmp_path / "act.csv")
        df = _load_activities_df(csv)
        assert pd.api.types.is_datetime64_any_dtype(df["start_date"])
        assert pd.api.types.is_datetime64_any_dtype(df["start_date_local"])

    def test_numeric_columns_are_numeric(self, tmp_path: Path) -> None:
        csv = _write_csv(tmp_path / "act.csv")
        df = _load_activities_df(csv)
        for col in ("distance", "moving_time", "average_watts", "normalized_power"):
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} should be numeric"

    def test_string_columns_not_coerced(self, tmp_path: Path) -> None:
        csv = _write_csv(tmp_path / "act.csv")
        df = _load_activities_df(csv)
        # name, type, sport_type, power_tid_classification should remain objects
        assert df["name"].dtype == object
        assert df["type"].dtype == object
        assert df["power_tid_classification"].dtype == object

    def test_sorted_descending(self, tmp_path: Path) -> None:
        csv = _write_csv(tmp_path / "act.csv")
        df = _load_activities_df(csv)
        dates = df["start_date_local"].tolist()
        assert dates == sorted(dates, reverse=True)

    def test_nan_string_becomes_nan(self, tmp_path: Path) -> None:
        """The literal string 'nan' in a numeric column becomes NaN."""
        csv = _write_csv(tmp_path / "act.csv")
        df = _load_activities_df(csv)
        # Row 2 (Evening Run) has empty average_watts → should be NaN
        run_row = df[df["id"] == 2].iloc[0]
        assert pd.isna(run_row["average_watts"])


# ---------------------------------------------------------------------------
# CSVActivityRepository — caching
# ---------------------------------------------------------------------------


class TestCaching:
    """Verify mtime-based caching behaviour."""

    @pytest.fixture()
    def raw_csv(self, tmp_path: Path) -> Path:
        return _write_csv(tmp_path / "activities_raw.csv")

    def test_second_access_uses_cache(self, raw_csv: Path) -> None:
        """Two consecutive accesses should NOT reload the file."""
        repo = CSVActivityRepository(raw_csv)

        with patch(
            "activities_viewer.repository.csv_repo._load_activities_df",
            wraps=_load_activities_df,
        ) as spy:
            _ = repo.get_dataframe_raw()
            _ = repo.get_dataframe_raw()
            assert spy.call_count == 1, "File should be loaded only once"

    def test_cache_invalidation_on_file_change(
        self, raw_csv: Path, tmp_path: Path
    ) -> None:
        """Modifying the file on disk should trigger a reload."""
        repo = CSVActivityRepository(raw_csv)
        _ = repo.get_dataframe_raw()

        # Overwrite with updated content (add a third row)
        new_csv = _MINIMAL_CSV + (
            "3;Lunch Walk;Walk;Walk;"
            "2025-06-03T12:00:00Z;2025-06-03T14:00:00+02:00;"
            "5000;1800;1900;50;0;0;0;Balanced\n"
        )
        # Ensure mtime actually differs (some filesystems have 1 s resolution)
        time.sleep(0.05)
        raw_csv.write_text(new_csv)
        # Touch to guarantee mtime bump on coarse-resolution filesystems
        new_mtime = raw_csv.stat().st_mtime + 1
        import os

        os.utime(raw_csv, (new_mtime, new_mtime))

        df = repo.get_dataframe_raw()
        assert len(df) == 3, "Should have reloaded with new row"

    def test_invalidate_cache_forces_reload(self, raw_csv: Path) -> None:
        repo = CSVActivityRepository(raw_csv)
        _ = repo.get_dataframe_raw()

        with patch(
            "activities_viewer.repository.csv_repo._load_activities_df",
            wraps=_load_activities_df,
        ) as spy:
            repo.invalidate_cache()
            _ = repo.get_dataframe_raw()
            assert spy.call_count == 1, "invalidate_cache should force reload"

    def test_moving_file_cached_independently(self, tmp_path: Path) -> None:
        """Raw and moving files each have their own mtime tracking."""
        raw = _write_csv(tmp_path / "raw.csv")
        mov = _write_csv(tmp_path / "mov.csv")
        repo = CSVActivityRepository(raw, mov)

        with patch(
            "activities_viewer.repository.csv_repo._load_activities_df",
            wraps=_load_activities_df,
        ) as spy:
            _ = repo.get_dataframe_raw()
            _ = repo.get_dataframe_moving()
            # First call loads raw (1) + moving (1) = 2
            # Second call should use cache for both
            _ = repo.get_dataframe_raw()
            _ = repo.get_dataframe_moving()
            assert spy.call_count == 2, "Second round should use cache"

    def test_missing_moving_file_uses_raw_fallback(self, raw_csv: Path) -> None:
        repo = CSVActivityRepository(raw_csv)
        df_raw = repo.get_dataframe_raw()
        df_mov = repo.get_dataframe_moving()
        pd.testing.assert_frame_equal(df_raw, df_mov)


# ---------------------------------------------------------------------------
# CSVActivityRepository — data access
# ---------------------------------------------------------------------------


class TestDataAccess:
    """Basic smoke tests for repository data-access methods."""

    @pytest.fixture()
    def repo(self, tmp_path: Path) -> CSVActivityRepository:
        raw = _write_csv(tmp_path / "activities_raw.csv")
        return CSVActivityRepository(raw)

    def test_all_activities_returns_list(self, repo: CSVActivityRepository) -> None:
        activities = repo.all_activities
        assert isinstance(activities, list)
        assert len(activities) == 2

    def test_get_activity_by_id(self, repo: CSVActivityRepository) -> None:
        act = repo.get_activity(1)
        assert act is not None
        assert act.name == "Morning Ride"

    def test_get_activity_missing_returns_none(
        self, repo: CSVActivityRepository
    ) -> None:
        assert repo.get_activity(999) is None

    def test_get_activities_date_filter(
        self, repo: CSVActivityRepository
    ) -> None:
        # Only activities on 2025-06-02 or later
        acts = repo.get_activities(start_date=date(2025, 6, 2))
        assert len(acts) == 1
        assert acts[0].name == "Evening Run"

    def test_get_year_summary(self, repo: CSVActivityRepository) -> None:
        summary = repo.get_year_summary(2025)
        assert summary.activity_count == 2
        assert summary.total_distance == 60000.0

    def test_get_year_summary_empty_year(
        self, repo: CSVActivityRepository
    ) -> None:
        summary = repo.get_year_summary(2020)
        assert summary.activity_count == 0


# ---------------------------------------------------------------------------
# CSVActivityRepository — stream loading
# ---------------------------------------------------------------------------


class TestStreamLoading:
    """Tests for get_activity_stream."""

    def test_loads_stream_csv(self, tmp_path: Path) -> None:
        raw = _write_csv(tmp_path / "activities_raw.csv")
        streams = tmp_path / "Streams"
        streams.mkdir()
        stream_file = streams / "stream_1.csv"
        stream_file.write_text("time;watts;heartrate\n0;200;140\n1;210;142\n")

        repo = CSVActivityRepository(raw, streams_dir=streams)
        df = repo.get_activity_stream(1)
        assert len(df) == 2
        assert "watts" in df.columns

    def test_missing_stream_returns_empty(self, tmp_path: Path) -> None:
        raw = _write_csv(tmp_path / "activities_raw.csv")
        streams = tmp_path / "Streams"
        streams.mkdir()

        repo = CSVActivityRepository(raw, streams_dir=streams)
        df = repo.get_activity_stream(999)
        assert df.empty


# ---------------------------------------------------------------------------
# _NON_NUMERIC_COLUMNS completeness
# ---------------------------------------------------------------------------


class TestNonNumericColumnsCompleteness:
    """Ensure _NON_NUMERIC_COLUMNS covers all string/date fields in Activity."""

    def test_all_string_and_date_model_fields_listed(self) -> None:
        """Every Activity field typed as str or datetime should be in the
        exclusion set (or mapped via validation_alias)."""
        from activities_viewer.domain.models import Activity

        string_or_date_fields: set[str] = set()
        for name, info in Activity.model_fields.items():
            annotation = info.annotation
            # Unwrap Optional
            origin = getattr(annotation, "__origin__", None)
            args = getattr(annotation, "__args__", ())
            types_to_check = args if origin is not None else (annotation,)

            for t in types_to_check:
                if t is type(None):
                    continue
                if t is str or (isinstance(t, type) and issubclass(t, str)):
                    string_or_date_fields.add(name)
                # datetime check
                from datetime import datetime

                if t is datetime or (
                    isinstance(t, type) and issubclass(t, datetime)
                ):
                    string_or_date_fields.add(name)

        # Some model fields use validation_alias (e.g. map_id -> "map.id")
        # which means the CSV column name differs. We check either the field
        # name or the alias is in _NON_NUMERIC_COLUMNS.
        for field_name in string_or_date_fields:
            info = Activity.model_fields[field_name]
            alias = (
                info.validation_alias
                if info.validation_alias is not None
                else field_name
            )
            assert field_name in _NON_NUMERIC_COLUMNS or alias in _NON_NUMERIC_COLUMNS, (
                f"String/date field '{field_name}' (alias={alias}) "
                f"is missing from _NON_NUMERIC_COLUMNS"
            )
