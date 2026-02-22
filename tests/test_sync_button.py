"""Tests for the sync button component (Phase 4)."""

from unittest.mock import MagicMock, patch

import pytest

from activities_viewer.pages.components.sync_button import (
    _get_last_synced,
    _load_sync_meta,
    _run_sync_pipeline,
    _save_sync_meta,
)


@pytest.fixture(autouse=True)
def _patch_meta_paths(tmp_path, monkeypatch):
    """Redirect sync meta files to a temp directory."""
    meta_dir = tmp_path / ".activitiesviewer"
    meta_file = meta_dir / "sync_meta.json"
    monkeypatch.setattr(
        "activities_viewer.pages.components.sync_button._SYNC_META_DIR", meta_dir
    )
    monkeypatch.setattr(
        "activities_viewer.pages.components.sync_button._SYNC_META_FILE", meta_file
    )


class TestSyncMeta:
    """Tests for sync metadata persistence."""

    def test_save_and_load(self):
        _save_sync_meta({"last_synced_at": "2026-01-15 10:30:00"})
        meta = _load_sync_meta()
        assert meta["last_synced_at"] == "2026-01-15 10:30:00"

    def test_load_empty(self):
        meta = _load_sync_meta()
        assert meta == {}

    def test_get_last_synced_none(self):
        assert _get_last_synced() is None

    def test_get_last_synced_exists(self):
        _save_sync_meta({"last_synced_at": "2026-02-20 15:00:00"})
        assert _get_last_synced() == "2026-02-20 15:00:00"

    def test_corrupt_meta_file(self, tmp_path):
        """Handles corrupted JSON gracefully."""
        meta_dir = tmp_path / ".activitiesviewer"
        meta_dir.mkdir(exist_ok=True)
        (meta_dir / "sync_meta.json").write_text("{bad json")
        meta = _load_sync_meta()
        assert meta == {}


class TestRunSyncPipeline:
    """Tests for _run_sync_pipeline()."""

    def test_no_unified_config_returns_error(self):
        success, output = _run_sync_pipeline(None)
        assert success is False
        assert "No unified config available" in output

    @patch("activities_viewer.pages.components.sync_button.subprocess.run")
    def test_successful_sync(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Sync done", stderr=""
        )
        success, output = _run_sync_pipeline("/path/to/config.yaml")
        assert success is True
        assert "Sync done" in output
        # Should have saved last_synced_at
        assert _get_last_synced() is not None

    @patch("activities_viewer.pages.components.sync_button.subprocess.run")
    def test_failed_sync(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="auth error"
        )
        success, output = _run_sync_pipeline("/path/to/config.yaml")
        assert success is False
        assert "auth error" in output

    @patch("activities_viewer.pages.components.sync_button.subprocess.run")
    def test_full_flag_passed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_sync_pipeline("/path/to/config.yaml", full=True)
        cmd = mock_run.call_args[0][0]
        assert "--full" in cmd

    @patch("activities_viewer.pages.components.sync_button.subprocess.run")
    def test_no_launch_flag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_sync_pipeline("/path/to/config.yaml")
        cmd = mock_run.call_args[0][0]
        assert "--no-launch" in cmd

    @patch(
        "activities_viewer.pages.components.sync_button.subprocess.run",
        side_effect=Exception("boom"),
    )
    def test_exception_handling(self, mock_run):
        success, output = _run_sync_pipeline("/path/to/config.yaml")
        assert success is False
        assert "Failed to run sync" in output
