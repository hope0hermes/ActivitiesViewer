"""Tests for pipeline orchestration — library API integration."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from activities_viewer.pipeline import (
    PipelineOrchestrator,
    is_unified_config,
    load_unified_config,
)

# ─── Fixtures ────────────────────────────────────────────────────────────

MINIMAL_UNIFIED = {
    "data_dir": "/tmp/test-data",
    "athlete": {
        "ftp": 280.0,
        "rider_weight_kg": 75.0,
        "max_hr": 190,
    },
    "fetcher": {
        "client_id": "12345",
        "client_secret": "secret",
    },
    "analyzer": {
        "ctl_days": 28,
        "atl_days": 7,
    },
    "viewer": {
        "page_title": "Test Viewer",
        "cache_ttl": 1800,
    },
}


@pytest.fixture
def orchestrator(tmp_path):
    """Create a PipelineOrchestrator with a minimal unified config."""
    return PipelineOrchestrator(MINIMAL_UNIFIED.copy(), tmp_path)


@pytest.fixture
def unified_yaml(tmp_path):
    """Write a minimal unified config to a temp file and return the path."""
    cfg_path = tmp_path / "unified.yaml"
    cfg_path.write_text(yaml.dump(MINIMAL_UNIFIED))
    return cfg_path


# ─── load_unified_config ─────────────────────────────────────────────────


class TestLoadUnifiedConfig:
    """Tests for load_unified_config()."""

    def test_loads_valid_config(self, unified_yaml):
        config = load_unified_config(unified_yaml)
        assert config["data_dir"] == "/tmp/test-data"
        assert config["athlete"]["ftp"] == 280.0

    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Unified config not found"):
            load_unified_config(tmp_path / "nope.yaml")

    def test_raises_on_missing_data_dir(self, tmp_path):
        cfg = tmp_path / "bad.yaml"
        cfg.write_text(yaml.dump({"athlete": {"ftp": 200}}))
        with pytest.raises(ValueError, match="data_dir"):
            load_unified_config(cfg)

    def test_empty_yaml_raises(self, tmp_path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("")
        with pytest.raises(ValueError, match="data_dir"):
            load_unified_config(cfg)


# ─── is_unified_config ───────────────────────────────────────────────────


class TestIsUnifiedConfig:
    """Tests for is_unified_config()."""

    def test_unified_with_athlete(self):
        assert is_unified_config({"athlete": {}, "data_dir": "x"}) is True

    def test_unified_with_fetcher(self):
        assert is_unified_config({"fetcher": {}, "data_dir": "x"}) is True

    def test_flat_viewer_config(self):
        assert is_unified_config({"data_dir": "x", "ftp": 285}) is False


# ─── _build_fetcher_settings ─────────────────────────────────────────────


class TestBuildFetcherSettings:
    """Tests for PipelineOrchestrator._build_fetcher_settings()."""

    @patch("strava_fetcher.Settings")
    def test_includes_strava_api_credentials(self, mock_settings_cls, orchestrator):
        orchestrator._build_fetcher_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["strava_api"]["client_id"] == "12345"
        assert kw["strava_api"]["client_secret"] == "secret"

    @patch("strava_fetcher.Settings")
    def test_paths_data_dir(self, mock_settings_cls, orchestrator):
        orchestrator._build_fetcher_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["paths"]["data_dir"] == str(orchestrator.data_dir)

    @patch("strava_fetcher.Settings")
    def test_sync_settings_propagation(self, mock_settings_cls, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {
            **config["fetcher"],
            "max_pages": 50,
            "retry_interval_seconds": 300,
            "skip_trainer_activities": True,
        }
        orch = PipelineOrchestrator(config, tmp_path)
        orch._build_fetcher_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["sync"]["max_pages"] == 50
        assert kw["sync"]["retry_interval_seconds"] == 300
        assert kw["sync"]["skip_trainer_activities"] is True

    @patch("strava_fetcher.Settings")
    def test_no_sync_when_empty(self, mock_settings_cls, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {"client_id": "x", "client_secret": "y"}
        orch = PipelineOrchestrator(config, tmp_path)
        orch._build_fetcher_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["sync"] == {}

    @patch("strava_fetcher.Settings")
    def test_no_strava_api_when_empty(self, mock_settings_cls, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {}
        orch = PipelineOrchestrator(config, tmp_path)
        orch._build_fetcher_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["strava_api"] == {}


# ─── _build_analyzer_settings ─────────────────────────────────────────────


class TestBuildAnalyzerSettings:
    """Tests for PipelineOrchestrator._build_analyzer_settings()."""

    @patch("strava_analyzer.Settings")
    def test_path_wiring(self, mock_settings_cls, orchestrator):
        orchestrator._build_analyzer_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["data_dir"] == str(orchestrator.data_dir)
        assert kw["activities_file"] == str(orchestrator.data_dir / "activities.csv")
        assert kw["streams_dir"] == str(orchestrator.data_dir / "Streams")
        assert kw["processed_data_dir"] == str(orchestrator.data_dir)

    @patch("strava_analyzer.Settings")
    def test_athlete_field_mapping(self, mock_settings_cls, orchestrator):
        orchestrator._build_analyzer_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["ftp"] == 280.0
        assert kw["rider_weight_kg"] == 75.0
        assert kw["max_hr"] == 190

    @patch("strava_analyzer.Settings")
    def test_analyzer_overrides(self, mock_settings_cls, orchestrator):
        orchestrator._build_analyzer_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["ctl_days"] == 28
        assert kw["atl_days"] == 7

    @patch("strava_analyzer.Settings")
    def test_full_athlete_fields(self, mock_settings_cls, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["athlete"] = {
            "ftp": 300,
            "fthr": 175,
            "max_hr": 195,
            "rider_weight_kg": 80,
            "cp": 260,
            "w_prime": 25000,
            "lt1_power": 210,
            "lt2_power": 270,
            "lt1_hr": 135,
            "lt2_hr": 160,
        }
        orch = PipelineOrchestrator(config, tmp_path)
        orch._build_analyzer_settings()
        kw = mock_settings_cls.call_args[1]
        assert kw["fthr"] == 175
        assert kw["cp"] == 260
        assert kw["w_prime"] == 25000
        assert kw["lt1_power"] == 210
        assert kw["lt2_power"] == 270
        assert kw["lt1_hr"] == 135
        assert kw["lt2_hr"] == 160


# ─── generate_viewer_settings_dict ────────────────────────────────────────


class TestGenerateViewerSettingsDict:
    """Tests for PipelineOrchestrator.generate_viewer_settings_dict()."""

    def test_data_paths(self, orchestrator):
        cfg = orchestrator.generate_viewer_settings_dict()
        assert cfg["data_dir"] == str(orchestrator.data_dir)
        assert cfg["activities_raw_file"] == "activities_raw.csv"
        assert cfg["activities_moving_file"] == "activities_moving.csv"
        assert cfg["activity_summary_file"] == "activity_summary.json"
        assert cfg["streams_dir"] == "Streams"

    def test_athlete_fields(self, orchestrator):
        cfg = orchestrator.generate_viewer_settings_dict()
        assert cfg["ftp"] == 280.0
        assert cfg["rider_weight_kg"] == 75.0
        assert cfg["max_hr"] == 190

    def test_viewer_overrides(self, orchestrator):
        cfg = orchestrator.generate_viewer_settings_dict()
        assert cfg["page_title"] == "Test Viewer"
        assert cfg["cache_ttl"] == 1800


# ─── data_dir resolution ─────────────────────────────────────────────────


class TestDataDirResolution:
    """Tests for data_dir path resolution in PipelineOrchestrator."""

    def test_absolute_path(self, tmp_path):
        config = {"data_dir": "/opt/strava-data"}
        orch = PipelineOrchestrator(config, tmp_path)
        assert orch.data_dir == Path("/opt/strava-data")

    def test_relative_path_resolved_to_config_dir(self, tmp_path):
        config = {"data_dir": "my-data"}
        orch = PipelineOrchestrator(config, tmp_path)
        assert orch.data_dir == (tmp_path / "my-data").resolve()

    def test_tilde_expansion(self, tmp_path):
        config = {"data_dir": "~/strava-data"}
        orch = PipelineOrchestrator(config, tmp_path)
        assert orch.data_dir == Path.home() / "strava-data"

    def test_default_data_dir(self, tmp_path):
        config = {}  # no data_dir key
        orch = PipelineOrchestrator(config, tmp_path)
        assert orch.data_dir == Path.home() / "strava-data"


# ─── run_fetch ────────────────────────────────────────────────────────────


class TestRunFetch:
    """Tests for PipelineOrchestrator.run_fetch()."""

    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_fetch_basic(self, mock_settings_cls, mock_pipeline_cls, orchestrator):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_fetch()
        mock_pipeline.run.assert_called_once_with(full=False)

    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_fetch_full(self, mock_settings_cls, mock_pipeline_cls, orchestrator):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_fetch(full=True)
        mock_pipeline.run.assert_called_once_with(full=True)

    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_fetch_failure(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.side_effect = RuntimeError("auth error")
        with pytest.raises(RuntimeError, match="auth error"):
            orchestrator.run_fetch()

    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_fetch_creates_data_dir(
        self, mock_settings_cls, mock_pipeline_cls, tmp_path
    ):
        data_dir = tmp_path / "new-data"
        config = {"data_dir": str(data_dir)}
        orch = PipelineOrchestrator(config, tmp_path)
        orch.run_fetch()
        assert data_dir.exists()
        assert (data_dir / "Streams").exists()


# ─── run_analyze ──────────────────────────────────────────────────────────


class TestRunAnalyze:
    """Tests for PipelineOrchestrator.run_analyze()."""

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_run_analyze_basic(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_analyze()
        mock_pipeline.run.assert_called_once_with(recompute_from=None)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_run_analyze_force(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_analyze(force=True)
        # force=True → recompute_from=None (ignores any date)
        mock_pipeline.run.assert_called_once_with(recompute_from=None)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_run_analyze_recompute_from(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_analyze(recompute_from="2024-06-01")
        mock_pipeline.run.assert_called_once_with(recompute_from="2024-06-01")

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_run_analyze_force_supersedes_recompute(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.run_analyze(force=True, recompute_from="2024-06-01")
        # force=True takes precedence → recompute_from=None
        mock_pipeline.run.assert_called_once_with(recompute_from=None)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_run_analyze_failure(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.side_effect = RuntimeError("crash")
        with pytest.raises(RuntimeError, match="crash"):
            orchestrator.run_analyze()


# ─── run_sync ─────────────────────────────────────────────────────────────


class TestRunSync:
    """Tests for PipelineOrchestrator.run_sync() (full pipeline)."""

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_calls_both(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        orchestrator.run_sync()
        mock_f_pipeline_cls.return_value.run.assert_called_once_with(full=False)
        mock_a_pipeline_cls.return_value.run.assert_called_once_with(
            recompute_from=None
        )

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_fetcher_runs_first(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        call_order = []
        mock_f_pipeline_cls.return_value.run.side_effect = (
            lambda **kw: call_order.append("fetcher")
        )
        mock_a_pipeline_cls.return_value.run.side_effect = (
            lambda **kw: call_order.append("analyzer")
        )
        orchestrator.run_sync()
        assert call_order == ["fetcher", "analyzer"]

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_stops_on_fetch_failure(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        mock_f_pipeline_cls.return_value.run.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError, match="fail"):
            orchestrator.run_sync()
        # Analyzer should NOT have been called
        mock_a_pipeline_cls.return_value.run.assert_not_called()

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_forwards_full_flag(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        orchestrator.run_sync(full=True)
        mock_f_pipeline_cls.return_value.run.assert_called_once_with(full=True)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_forwards_force_flag(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        orchestrator.run_sync(force=True)
        mock_a_pipeline_cls.return_value.run.assert_called_once_with(
            recompute_from=None
        )

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_run_sync_forwards_recompute_from(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        orchestrator.run_sync(recompute_from="2024-01-01")
        mock_a_pipeline_cls.return_value.run.assert_called_once_with(
            recompute_from="2024-01-01"
        )


# ─── single activity ─────────────────────────────────────────────────────


class TestSingleActivity:
    """Tests for single activity fetch/process/sync."""

    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_fetch_single_activity(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.fetch_single_activity(123456)
        mock_pipeline.fetch_single_activity.assert_called_once_with(123456)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    def test_process_single_activity(
        self, mock_settings_cls, mock_pipeline_cls, orchestrator
    ):
        mock_pipeline = mock_pipeline_cls.return_value
        orchestrator.process_single_activity(123456)
        mock_pipeline.process_single_activity.assert_called_once_with(123456)

    @patch("strava_analyzer.Pipeline")
    @patch("strava_analyzer.Settings")
    @patch("strava_fetcher.StravaSyncPipeline")
    @patch("strava_fetcher.Settings")
    def test_sync_single_activity(
        self,
        mock_f_settings,
        mock_f_pipeline_cls,
        mock_a_settings,
        mock_a_pipeline_cls,
        orchestrator,
    ):
        orchestrator.sync_single_activity(123456)
        mock_f_pipeline_cls.return_value.fetch_single_activity.assert_called_once_with(
            123456
        )
        mock_a_pipeline_cls.return_value.process_single_activity.assert_called_once_with(
            123456
        )
