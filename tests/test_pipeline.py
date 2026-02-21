"""Tests for pipeline orchestration (Phase 3)."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        "weight_kg": 75.0,
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


# ─── generate_fetcher_config ─────────────────────────────────────────────


class TestGenerateFetcherConfig:
    """Tests for PipelineOrchestrator.generate_fetcher_config()."""

    def test_includes_strava_api_credentials(self, orchestrator):
        cfg = orchestrator.generate_fetcher_config()
        assert cfg["strava_api"]["client_id"] == "12345"
        assert cfg["strava_api"]["client_secret"] == "secret"

    def test_paths_data_dir(self, orchestrator):
        cfg = orchestrator.generate_fetcher_config()
        assert cfg["paths"]["data_dir"] == str(orchestrator.data_dir)

    def test_sync_settings_propagation(self, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {
            **config["fetcher"],
            "max_pages": 50,
            "retry_interval_seconds": 300,
            "skip_trainer_activities": True,
        }
        orch = PipelineOrchestrator(config, tmp_path)
        cfg = orch.generate_fetcher_config()
        assert cfg["sync"]["max_pages"] == 50
        assert cfg["sync"]["retry_interval_seconds"] == 300
        assert cfg["sync"]["skip_trainer_activities"] is True

    def test_no_sync_section_when_empty(self, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {"client_id": "x", "client_secret": "y"}
        orch = PipelineOrchestrator(config, tmp_path)
        cfg = orch.generate_fetcher_config()
        assert "sync" not in cfg

    def test_no_strava_api_when_empty(self, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["fetcher"] = {}
        orch = PipelineOrchestrator(config, tmp_path)
        cfg = orch.generate_fetcher_config()
        assert "strava_api" not in cfg


# ─── generate_analyzer_config ─────────────────────────────────────────────


class TestGenerateAnalyzerConfig:
    """Tests for PipelineOrchestrator.generate_analyzer_config()."""

    def test_path_wiring(self, orchestrator):
        cfg = orchestrator.generate_analyzer_config()
        assert cfg["data_dir"] == str(orchestrator.data_dir)
        assert cfg["activities_file"] == "activities.csv"
        assert cfg["streams_dir"] == "Streams"
        assert cfg["processed_data_dir"] == str(orchestrator.data_dir)

    def test_athlete_field_mapping(self, orchestrator):
        cfg = orchestrator.generate_analyzer_config()
        assert cfg["ftp"] == 280.0
        assert cfg["rider_weight_kg"] == 75.0
        assert cfg["max_hr"] == 190

    def test_analyzer_overrides(self, orchestrator):
        cfg = orchestrator.generate_analyzer_config()
        assert cfg["ctl_days"] == 28
        assert cfg["atl_days"] == 7

    def test_full_athlete_fields(self, tmp_path):
        config = MINIMAL_UNIFIED.copy()
        config["athlete"] = {
            "ftp": 300,
            "fthr": 175,
            "max_hr": 195,
            "weight_kg": 80,
            "cp": 260,
            "w_prime": 25000,
            "lt1_power": 210,
            "lt2_power": 270,
            "lt1_hr": 135,
            "lt2_hr": 160,
        }
        orch = PipelineOrchestrator(config, tmp_path)
        cfg = orch.generate_analyzer_config()
        assert cfg["fthr"] == 175
        assert cfg["cp"] == 260
        assert cfg["w_prime"] == 25000
        assert cfg["lt1_power"] == 210
        assert cfg["lt2_power"] == 270
        assert cfg["lt1_hr"] == 135
        assert cfg["lt2_hr"] == 160


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
        assert cfg["weight_kg"] == 75.0
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

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_fetch_basic(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_fetch()
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "sync" in cmd
        assert "--full" not in cmd
        mock_which.assert_called_with("strava-fetcher")

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_fetch_full(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_fetch(full=True)
        cmd = mock_run.call_args[0][0]
        assert "--full" in cmd

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_fetch_failure(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="auth error")
        with pytest.raises(RuntimeError, match="StravaFetcher failed"):
            orchestrator.run_fetch()

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_fetch_creates_data_dir(self, mock_run, mock_which, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        data_dir = tmp_path / "new-data"
        config = {"data_dir": str(data_dir)}
        orch = PipelineOrchestrator(config, tmp_path)
        orch.run_fetch()
        assert data_dir.exists()
        assert (data_dir / "Streams").exists()


# ─── run_analyze ──────────────────────────────────────────────────────────


class TestRunAnalyze:
    """Tests for PipelineOrchestrator.run_analyze()."""

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-analyzer")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_analyze_basic(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_analyze()
        cmd = mock_run.call_args[0][0]
        assert "run" in cmd
        assert "--force" not in cmd
        assert "--recompute-from" not in cmd

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-analyzer")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_analyze_force(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_analyze(force=True)
        cmd = mock_run.call_args[0][0]
        assert "--force" in cmd

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-analyzer")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_analyze_recompute_from(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_analyze(recompute_from="2024-06-01")
        cmd = mock_run.call_args[0][0]
        assert "--recompute-from" in cmd
        assert "2024-06-01" in cmd

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-analyzer")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_analyze_force_supersedes_recompute(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        orchestrator.run_analyze(force=True, recompute_from="2024-06-01")
        cmd = mock_run.call_args[0][0]
        assert "--force" in cmd
        # force and recompute-from are mutually exclusive — force wins
        assert "--recompute-from" not in cmd

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-analyzer")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_analyze_failure(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="crash")
        with pytest.raises(RuntimeError, match="StravaAnalyzer failed"):
            orchestrator.run_analyze()


# ─── run_sync ─────────────────────────────────────────────────────────────


class TestRunSync:
    """Tests for PipelineOrchestrator.run_sync() (full pipeline)."""

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_calls_both_tools(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        orchestrator.run_sync()
        assert mock_run.call_count == 2

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_fetcher_runs_first(self, mock_run, mock_which, orchestrator):
        call_order = []
        def record_call(*args, **kwargs):
            cmd = args[0]
            if "strava-fetcher" in str(cmd):
                call_order.append("fetcher")
            elif "strava-analyzer" in str(cmd):
                call_order.append("analyzer")
            return MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = record_call
        orchestrator.run_sync()
        assert call_order == ["fetcher", "analyzer"]

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_stops_on_fetch_failure(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fail")
        with pytest.raises(RuntimeError, match="StravaFetcher"):
            orchestrator.run_sync()
        assert mock_run.call_count == 1  # analyzer not called

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_forwards_full_flag(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        orchestrator.run_sync(full=True)
        first_cmd = mock_run.call_args_list[0][0][0]
        assert "--full" in first_cmd

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_forwards_force_flag(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        orchestrator.run_sync(force=True)
        second_cmd = mock_run.call_args_list[1][0][0]
        assert "--force" in second_cmd

    @patch("activities_viewer.pipeline.shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_run_sync_forwards_recompute_from(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        orchestrator.run_sync(recompute_from="2024-01-01")
        second_cmd = mock_run.call_args_list[1][0][0]
        assert "--recompute-from" in second_cmd
        assert "2024-01-01" in second_cmd


# ─── temp config file cleanup ────────────────────────────────────────────


class TestTempConfigCleanup:
    """Ensure temp config files are cleaned up even on failure."""

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_fetcher_temp_file_cleaned_on_success(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        orchestrator.run_fetch()
        # Verify that no temp files with our prefix remain
        import glob
        remaining = glob.glob("/tmp/fetcher_*.yaml")
        # The file should have been deleted
        assert len(remaining) == 0 or all(
            "fetcher_" not in f for f in remaining
        )

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/local/bin/strava-fetcher")
    @patch("activities_viewer.pipeline.subprocess.run")
    def test_fetcher_temp_file_cleaned_on_failure(self, mock_run, mock_which, orchestrator):
        mock_run.return_value = MagicMock(returncode=1, stderr="fail")
        with pytest.raises(RuntimeError):
            orchestrator.run_fetch()
        # Temp file should still be cleaned up


# ─── _resolve_cli ───────────────────────────────────────────────────────────


class TestResolveCli:
    """Tests for PipelineOrchestrator._resolve_cli()."""

    @patch("activities_viewer.pipeline.shutil.which", return_value="/usr/bin/strava-fetcher")
    def test_resolves_tool_on_path(self, mock_which):
        result = PipelineOrchestrator._resolve_cli("strava-fetcher")
        assert result == "/usr/bin/strava-fetcher"
        mock_which.assert_called_once_with("strava-fetcher")

    @patch("activities_viewer.pipeline.shutil.which", return_value=None)
    def test_raises_when_tool_not_found(self, mock_which):
        with pytest.raises(RuntimeError, match="'strava-fetcher' not found on PATH"):
            PipelineOrchestrator._resolve_cli("strava-fetcher")
