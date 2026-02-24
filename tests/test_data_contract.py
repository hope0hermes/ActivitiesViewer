"""Contract tests: verify Activity model stays in sync with StravaAnalyzer output.

These tests run StravaAnalyzer on real fixture data and validate that the
Activity model can parse every row, covers all output columns, and that
expected column groups are present per activity type.

Phase 4 (model sync) and Phase 5 (contract tests) are coupled:
- When ``test_model_fields_cover_analyzer_columns`` fails → add missing
  fields to ``domain/models.py``
- When ``test_activity_model_parses_all_rows`` fails → fix field types or
  the ``convert_nan_values`` validator
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ─── Column groups ────────────────────────────────────────────────────────

CORE_COLUMNS = {
    # Identity (from Strava API, passed through by Analyzer)
    "id",
    "name",
    "type",
    "sport_type",
    "start_date",
    "start_date_local",
    # Core metrics (always computed)
    "distance",
    "moving_time",
    "elapsed_time",
    "total_elevation_gain",
    "average_speed",
    "max_speed",
    # Temporal
    "total_time",
    "elevation_gain",
}

SETTINGS_SNAPSHOT_COLUMNS = {
    # Stamped per-activity by Analyzer's AnalysisService
    "ftp",
    "fthr",
    "lt1_power",
    "lt2_power",
    "lt1_hr",
    "lt2_hr",
    "rider_weight_kg",
    "settings_max_hr",
    "settings_cp",
    "settings_w_prime",
}

TRAINING_LOAD_COLUMNS = {
    # Longitudinal metrics (computed after all activities are processed)
    "chronic_training_load",
    "acute_training_load",
    "training_stress_balance",
    "acwr",
}

CP_MODEL_COLUMNS = {
    "cp",
    "w_prime",
    "cp_r_squared",
    "aei",
}

POWER_COLUMNS = {
    # Present only when activity has power data
    "average_power",
    "normalized_power",
    "intensity_factor",
    "training_stress_score",
    "variability_index",
    "power_per_kg",
    "max_power",
}

POWER_ZONE_COLUMNS = {
    # 7-zone model
    *(f"power_z{i}_percentage" for i in range(1, 8)),
    *(f"power_z{i}_time" for i in range(1, 8)),
}

HR_COLUMNS = {
    # Present only when activity has HR data
    "average_hr",
    "max_hr",
    "hr_training_stress",
}

HR_ZONE_COLUMNS = {
    # 5-zone model
    *(f"hr_z{i}_percentage" for i in range(1, 6)),
    *(f"hr_z{i}_time" for i in range(1, 6)),
}

ZONE_EDGE_COLUMNS = {
    # Boundaries (from ZoneEdgesManager)
    *(f"power_zone_{i}" for i in range(1, 7)),
    *(f"hr_zone_{i}" for i in range(1, 5)),
}

ADVANCED_POWER_COLUMNS = {
    "time_above_90_ftp",
    "time_sweet_spot",
    "estimated_ftp",
    "w_prime_balance_min",
    "match_burn_count",
    "w_prime_depletion",
    "negative_split_index",
    "cardiac_drift",
    "first_half_hr",
    "second_half_hr",
}

CLIMBING_COLUMNS = {
    "vam",
    "climbing_time",
    "climbing_power",
    "climbing_power_per_kg",
}

EFFICIENCY_COLUMNS = {
    "efficiency_factor",
    "power_hr_decoupling",
    "first_half_ef",
    "second_half_ef",
}

FATIGUE_COLUMNS = {
    "fatigue_index",
    "initial_5min_power",
    "final_5min_power",
    "first_half_power",
    "second_half_power",
    "power_drift",
    "half_power_ratio",
    "power_coefficient_variation",
    "power_sustainability_index",
}

TID_COLUMNS = {
    *(f"power_tid_z{i}_percentage" for i in range(1, 4)),
    "power_polarization_index",
    "power_tdr",
    *(f"hr_tid_z{i}_percentage" for i in range(1, 4)),
    "hr_polarization_index",
    "hr_tdr",
    "power_tid_classification",
    "hr_tid_classification",
}

# Fields that exist only for certain activity types / devices, or require
# longitudinal history not present in cold-start fixture runs.
MODEL_ONLY_FIELDS = {
    "device_name",  # Strava API field, not all activities have it
    "normalized_graded_pace",  # Running-specific metric
    # Longitudinal metrics — require previously processed data to compute
    "chronic_training_load",
    "acute_training_load",
    "training_stress_balance",
    "acwr",
    # CP model fitting — requires rolling window of activity history
    "cp",
    "w_prime",
    "cp_r_squared",
    "aei",
}


# ─── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def analyzer_result(tmp_path_factory):
    """Run StravaAnalyzer on test fixture data (once per module)."""

    from strava_analyzer import Pipeline, Settings

    fixtures = Path(__file__).parent / "fixtures" / "analyzer_data"
    output_dir = tmp_path_factory.mktemp("analyzer_output")
    settings = Settings(
        activities_file=str(fixtures / "activities.csv"),
        streams_dir=str(fixtures / "Streams"),
        processed_data_dir=str(output_dir),
        ftp=285,
        max_hr=185,
        rider_weight_kg=77,
    )
    return Pipeline(settings).run()


@pytest.fixture(scope="module")
def analyzer_columns(analyzer_result):
    """Return the set of columns from the Analyzer's raw output."""
    return set(analyzer_result.raw_df.columns)


# ─── Core column-group tests ─────────────────────────────────────────────


class TestCoreColumns:
    """Verify that fundamental column groups always appear."""

    def test_core_columns_present(self, analyzer_columns):
        missing = CORE_COLUMNS - analyzer_columns
        assert not missing, f"Core columns missing from Analyzer output: {missing}"

    def test_settings_snapshot_present(self, analyzer_columns):
        missing = SETTINGS_SNAPSHOT_COLUMNS - analyzer_columns
        assert not missing, (
            f"Settings snapshot columns missing: {missing}"
        )

    def test_training_load_present_when_history_available(self, analyzer_columns):
        """Training load columns appear only with longitudinal history."""
        present = TRAINING_LOAD_COLUMNS & analyzer_columns
        if not present:
            pytest.skip(
                "Training load columns not present (expected on cold-start "
                "fixture runs without longitudinal history)"
            )
        missing = TRAINING_LOAD_COLUMNS - analyzer_columns
        assert not missing, f"Partial training load columns: {missing}"

    def test_cp_model_present_when_history_available(self, analyzer_columns):
        """CP model columns appear only with sufficient activity history."""
        present = CP_MODEL_COLUMNS & analyzer_columns
        if not present:
            pytest.skip(
                "CP model columns not present (expected on cold-start "
                "fixture runs without rolling activity history)"
            )
        missing = CP_MODEL_COLUMNS - analyzer_columns
        assert not missing, f"Partial CP model columns: {missing}"


# ─── Conditional column-group tests ──────────────────────────────────────


class TestConditionalColumns:
    """Verify column groups that depend on activity type / sensors."""

    def test_power_columns_for_cycling(self, analyzer_result):
        df = analyzer_result.raw_df
        rides = df[df["type"] == "Ride"]
        if rides.empty:
            pytest.skip("No cycling activities in fixtures")

        actual = set(df.columns)
        missing = POWER_COLUMNS - actual
        assert not missing, f"Power columns missing for cycling: {missing}"

    def test_power_zone_columns(self, analyzer_columns):
        missing = POWER_ZONE_COLUMNS - analyzer_columns
        assert not missing, f"Power zone columns missing: {missing}"

    def test_hr_columns(self, analyzer_columns):
        missing = HR_COLUMNS - analyzer_columns
        assert not missing, f"HR columns missing: {missing}"

    def test_hr_zone_columns(self, analyzer_columns):
        missing = HR_ZONE_COLUMNS - analyzer_columns
        assert not missing, f"HR zone columns missing: {missing}"

    def test_zone_edge_columns(self, analyzer_columns):
        missing = ZONE_EDGE_COLUMNS - analyzer_columns
        assert not missing, f"Zone edge columns missing: {missing}"

    def test_advanced_power_columns(self, analyzer_columns):
        missing = ADVANCED_POWER_COLUMNS - analyzer_columns
        assert not missing, f"Advanced power columns missing: {missing}"

    def test_climbing_columns(self, analyzer_columns):
        missing = CLIMBING_COLUMNS - analyzer_columns
        assert not missing, f"Climbing columns missing: {missing}"

    def test_efficiency_columns(self, analyzer_columns):
        missing = EFFICIENCY_COLUMNS - analyzer_columns
        assert not missing, f"Efficiency columns missing: {missing}"

    def test_fatigue_columns(self, analyzer_columns):
        missing = FATIGUE_COLUMNS - analyzer_columns
        assert not missing, f"Fatigue columns missing: {missing}"

    def test_tid_columns(self, analyzer_columns):
        missing = TID_COLUMNS - analyzer_columns
        assert not missing, f"TID columns missing: {missing}"


# ─── Model parity tests ──────────────────────────────────────────────────


class TestModelParity:
    """Verify Activity model stays in sync with Analyzer output."""

    def test_activity_model_parses_all_rows(self, analyzer_result):
        """Every row from Analyzer output must parse into an Activity model."""
        from activities_viewer.domain.models import Activity

        errors = []
        for idx, row in analyzer_result.raw_df.iterrows():
            try:
                Activity(**row.to_dict())
            except Exception as e:
                errors.append(f"Row {idx} (id={row.get('id')}): {e}")

        assert not errors, (
            "Activity parse failures:\n" + "\n".join(errors)
        )

    def test_model_fields_cover_analyzer_columns(self, analyzer_columns):
        """Activity model should have fields for all Analyzer output columns.

        This is the key Phase 4 ↔ Phase 5 integration test: it detects
        when the Analyzer adds new columns that the model doesn't have.
        """
        from activities_viewer.domain.models import Activity

        # Build the effective set of names the model accepts (fields + aliases)
        model_names = set(Activity.model_fields.keys())
        for _name, info in Activity.model_fields.items():
            if info.validation_alias:
                model_names.add(str(info.validation_alias))

        uncovered = sorted(analyzer_columns - model_names)
        if uncovered:
            pytest.fail(
                f"Analyzer outputs {len(uncovered)} column(s) not in "
                f"Activity model: {uncovered}\n"
                f"Add these fields to domain/models.py."
            )

    def test_no_unexpected_model_only_fields(self, analyzer_columns):
        """Model-only fields should be in the known allowlist.

        If a model field isn't in the Analyzer output *and* isn't in the
        known MODEL_ONLY_FIELDS allowlist, it may be a typo or stale field.
        """
        from activities_viewer.domain.models import Activity

        model_fields = set(Activity.model_fields.keys())

        # Fields that have aliases are accepted via alias — exclude them
        aliased_fields = set()
        for name, info in Activity.model_fields.items():
            if info.validation_alias and str(info.validation_alias) in analyzer_columns:
                aliased_fields.add(name)

        # Fields in model but not in Analyzer output (minus aliased, minus allowlist)
        model_only = model_fields - analyzer_columns - aliased_fields - MODEL_ONLY_FIELDS
        if model_only:
            pytest.fail(
                f"Model has {len(model_only)} field(s) not in Analyzer "
                f"output and not in allowlist: {sorted(model_only)}\n"
                f"If these are legitimate, add them to MODEL_ONLY_FIELDS."
            )


# ─── Schema consistency ──────────────────────────────────────────────────


class TestSchemaConsistency:
    """Verify raw and moving DataFrames share the same schema."""

    def test_raw_and_moving_same_columns(self, analyzer_result):
        """Raw and moving DataFrames should have identical column sets."""
        raw_cols = set(analyzer_result.raw_df.columns)
        moving_cols = set(analyzer_result.moving_df.columns)

        only_raw = raw_cols - moving_cols
        only_moving = moving_cols - raw_cols

        assert not only_raw and not only_moving, (
            f"Schema mismatch between raw and moving DataFrames.\n"
            f"Only in raw: {sorted(only_raw)}\n"
            f"Only in moving: {sorted(only_moving)}"
        )
