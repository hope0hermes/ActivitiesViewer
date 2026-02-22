"""
Pipeline orchestrator for running the full fetch → analyze → view workflow.

Generates tool-specific configs from a unified config and runs StravaFetcher
and StravaAnalyzer as subprocesses, keeping the packages decoupled.
"""

import importlib.util
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ── Library availability guards ──────────────────────────────────────────
# Phase 1: These flags enable graceful degradation when the upstream
# libraries are not installed (e.g. dashboard-only usage).
# Phase 2 will use these to switch from subprocess to library API calls.
#
# Available imports when HAS_FETCHER is True:
#   from strava_fetcher import (
#       StravaSyncPipeline, StravaClient, TokenPersistence,
#       PathSettings, SyncSettings, StravaAPISettings, load_settings,
#   )
#
# Available imports when HAS_ANALYZER is True:
#   from strava_analyzer import (
#       Pipeline, AnalysisService, Settings, load_settings,
#       DualAnalysisResult, AnalysisResult,
#   )

HAS_FETCHER = importlib.util.find_spec("strava_fetcher") is not None
HAS_ANALYZER = importlib.util.find_spec("strava_analyzer") is not None


class PipelineOrchestrator:
    """Orchestrate the StravaFetcher → StravaAnalyzer → ActivitiesViewer pipeline.

    Reads a unified YAML config with ``athlete:``, ``fetcher:``, ``analyzer:``,
    and ``viewer:`` sections and generates tool-specific temp configs for each
    subprocess invocation.

    Args:
        unified_config: Parsed unified YAML dict.
        config_dir: Directory containing the unified config (for relative path resolution).
    """

    def __init__(self, unified_config: dict[str, Any], config_dir: Path) -> None:
        self.config = unified_config
        self.config_dir = config_dir.resolve()

        # Resolve the shared data directory
        raw_data_dir = self.config.get("data_dir", "~/strava-data")
        self.data_dir = Path(raw_data_dir).expanduser()
        if not self.data_dir.is_absolute():
            self.data_dir = (self.config_dir / self.data_dir).resolve()
        else:
            self.data_dir = self.data_dir.resolve()

        # Sub-sections (default to empty dicts)
        self.athlete = self.config.get("athlete", {})
        self.fetcher = self.config.get("fetcher", {})
        self.analyzer = self.config.get("analyzer", {})
        self.viewer = self.config.get("viewer", {})

    # ─── Config generators ────────────────────────────────────────────────

    def generate_fetcher_config(self) -> dict[str, Any]:
        """Build the YAML dict that StravaFetcher ``Settings.from_yaml`` expects.

        Returns:
            dict suitable for ``yaml.dump`` → temp file → ``strava-fetcher sync --config-file``.
        """
        fetcher_cfg: dict[str, Any] = {}

        # strava_api section
        strava_api: dict[str, str] = {}
        if "client_id" in self.fetcher:
            strava_api["client_id"] = str(self.fetcher["client_id"])
        if "client_secret" in self.fetcher:
            strava_api["client_secret"] = str(self.fetcher["client_secret"])
        if strava_api:
            fetcher_cfg["strava_api"] = strava_api

        # paths section — all tools share self.data_dir
        fetcher_cfg["paths"] = {
            "data_dir": str(self.data_dir),
        }

        # sync section
        sync: dict[str, Any] = {}
        for key in ("max_pages", "retry_interval_seconds", "skip_trainer_activities"):
            if key in self.fetcher:
                sync[key] = self.fetcher[key]
        if sync:
            fetcher_cfg["sync"] = sync

        return fetcher_cfg

    def generate_analyzer_config(self) -> dict[str, Any]:
        """Build the YAML dict that StravaAnalyzer ``load_settings`` expects.

        Maps unified athlete fields → analyzer field names and merges any
        analyzer-specific overrides.

        Returns:
            dict suitable for ``yaml.dump`` → temp file → ``strava-analyzer run --config``.
        """
        analyzer_cfg: dict[str, Any] = {}

        # Path wiring — analyzer reads from the shared data_dir and writes back to it
        analyzer_cfg["data_dir"] = str(self.data_dir)
        analyzer_cfg["activities_file"] = "activities.csv"
        analyzer_cfg["streams_dir"] = "Streams"
        analyzer_cfg["processed_data_dir"] = str(self.data_dir)

        # Athlete fields → analyzer field names
        field_map = {
            "ftp": "ftp",
            "fthr": "fthr",
            "max_hr": "max_hr",
            "weight_kg": "rider_weight_kg",
            "cp": "cp",
            "w_prime": "w_prime",
            "lt1_power": "lt1_power",
            "lt2_power": "lt2_power",
            "lt1_hr": "lt1_hr",
            "lt2_hr": "lt2_hr",
            "ftpace": "ftpace",
        }
        for src, dst in field_map.items():
            if src in self.athlete:
                analyzer_cfg[dst] = self.athlete[src]

        # Merge any analyzer-specific overrides (e.g. ctl_days, atl_days)
        for key, value in self.analyzer.items():
            analyzer_cfg[key] = value

        return analyzer_cfg

    def generate_viewer_settings_dict(self) -> dict[str, Any]:
        """Build a flat dict suitable for ``Settings(**data)`` in ActivitiesViewer.

        Maps unified athlete fields + viewer overrides into the Viewer's Settings
        field names so it can be used directly.

        Returns:
            dict for ``Settings(**result)``.
        """
        viewer_cfg: dict[str, Any] = {}

        # Data paths — viewer reads from the shared data_dir
        viewer_cfg["data_dir"] = str(self.data_dir)
        viewer_cfg["activities_raw_file"] = "activities_raw.csv"
        viewer_cfg["activities_moving_file"] = "activities_moving.csv"
        viewer_cfg["activity_summary_file"] = "activity_summary.json"
        viewer_cfg["streams_dir"] = "Streams"

        # Athlete fields → viewer field names (same names for most)
        for key in ("ftp", "max_hr", "weight_kg", "cp", "w_prime"):
            if key in self.athlete:
                viewer_cfg[key] = self.athlete[key]

        # Viewer-specific settings
        for key, value in self.viewer.items():
            viewer_cfg[key] = value

        return viewer_cfg

    # ─── Subprocess execution ─────────────────────────────────────────────

    def _ensure_data_dir(self) -> None:
        """Create the shared data directory and Streams sub-directory if needed."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "Streams").mkdir(parents=True, exist_ok=True)

    def _write_temp_config(self, config_dict: dict[str, Any], prefix: str) -> Path:
        """Write a config dict to a temp YAML file.

        Returns:
            Path to the temporary config file (caller should clean up).
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            prefix=f"{prefix}_",
            delete=False,
        )
        yaml.dump(config_dict, tmp, default_flow_style=False)
        tmp.close()
        return Path(tmp.name)

    def _run_tool(
        self,
        cmd: list[str],
        tool_name: str,
        *,
        capture: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a CLI tool as a subprocess.

        Args:
            cmd: Command list (e.g. ["strava-fetcher", "sync", ...]).
            tool_name: Human-readable name for logging.
            capture: Whether to capture stdout/stderr (False streams to console).

        Returns:
            CompletedProcess result.

        Raises:
            RuntimeError: If the subprocess exits with a non-zero code.
        """
        logger.info(f"Running {tool_name}: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr or "(no stderr)"
            msg = f"{tool_name} failed (exit {result.returncode}): {stderr}"
            logger.error(msg)
            raise RuntimeError(msg)

        if capture and result.stdout:
            logger.info(f"{tool_name} output:\n{result.stdout}")

        return result

    # ─── CLI tool resolution ─────────────────────────────────────────────

    @staticmethod
    def _resolve_cli(tool_name: str) -> str:
        """Find a CLI entry-point on PATH.

        Args:
            tool_name: CLI command name (e.g. ``strava-fetcher``).

        Returns:
            Absolute path to the executable.

        Raises:
            RuntimeError: If the tool is not found on PATH.
        """
        path = shutil.which(tool_name)
        if path is None:
            raise RuntimeError(
                f"'{tool_name}' not found on PATH. "
                f"Make sure the package is installed and the entry-point is "
                f"available (e.g. activate its virtualenv or install globally)."
            )
        return path

    # ─── Public methods ───────────────────────────────────────────────────

    def run_fetch(self, *, full: bool = False) -> subprocess.CompletedProcess[str]:
        """Run ``strava-fetcher sync``.

        Args:
            full: Pass ``--full`` to force a complete re-fetch.

        Returns:
            CompletedProcess result.
        """
        self._ensure_data_dir()
        fetcher_cfg = self.generate_fetcher_config()
        tmp_path = self._write_temp_config(fetcher_cfg, "fetcher")

        try:
            cmd = [
                self._resolve_cli("strava-fetcher"),
                "sync",
                "--config-file", str(tmp_path),
            ]
            if full:
                cmd.append("--full")
            return self._run_tool(cmd, "StravaFetcher")
        finally:
            tmp_path.unlink(missing_ok=True)

    def run_analyze(
        self,
        *,
        force: bool = False,
        recompute_from: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run ``strava-analyzer run``.

        Args:
            force: Pass ``--force`` to reprocess all activities.
            recompute_from: ISO date to selectively recompute from.

        Returns:
            CompletedProcess result.
        """
        analyzer_cfg = self.generate_analyzer_config()
        tmp_path = self._write_temp_config(analyzer_cfg, "analyzer")

        try:
            cmd = [
                self._resolve_cli("strava-analyzer"),
                "run",
                "--config", str(tmp_path),
            ]
            if force:
                cmd.append("--force")
            elif recompute_from:
                cmd.extend(["--recompute-from", recompute_from])
            return self._run_tool(cmd, "StravaAnalyzer")
        finally:
            tmp_path.unlink(missing_ok=True)

    def run_sync(
        self,
        *,
        full: bool = False,
        force: bool = False,
        recompute_from: str | None = None,
    ) -> None:
        """Run the full fetch → analyze pipeline.

        Args:
            full: Force full activity re-fetch from Strava API.
            force: Force full re-analysis of all activities.
            recompute_from: ISO date for selective recomputation.
        """
        logger.info("=" * 60)
        logger.info("Starting pipeline sync")
        logger.info("=" * 60)

        logger.info("Step 1/2: Fetching activities from Strava...")
        self.run_fetch(full=full)
        logger.info("✅ Fetch complete")

        logger.info("Step 2/2: Analyzing activities...")
        self.run_analyze(force=force, recompute_from=recompute_from)
        logger.info("✅ Analysis complete")

        logger.info("=" * 60)
        logger.info("Pipeline sync finished successfully")
        logger.info("=" * 60)

    def fetch_single_activity(self, activity_id: int) -> subprocess.CompletedProcess[str]:
        """Run ``strava-fetcher fetch-activity <ID>``.

        Args:
            activity_id: Strava activity ID.

        Returns:
            CompletedProcess result.
        """
        self._ensure_data_dir()
        fetcher_cfg = self.generate_fetcher_config()
        tmp_path = self._write_temp_config(fetcher_cfg, "fetcher")

        try:
            cmd = [
                self._resolve_cli("strava-fetcher"),
                "fetch-activity", str(activity_id),
                "--config-file", str(tmp_path),
            ]
            return self._run_tool(cmd, "StravaFetcher (single)")
        finally:
            tmp_path.unlink(missing_ok=True)

    def process_single_activity(self, activity_id: int) -> subprocess.CompletedProcess[str]:
        """Run ``strava-analyzer process-activity <ID>``.

        Args:
            activity_id: Strava activity ID.

        Returns:
            CompletedProcess result.
        """
        analyzer_cfg = self.generate_analyzer_config()
        tmp_path = self._write_temp_config(analyzer_cfg, "analyzer")

        try:
            cmd = [
                self._resolve_cli("strava-analyzer"),
                "process-activity", str(activity_id),
                "--config", str(tmp_path),
            ]
            return self._run_tool(cmd, "StravaAnalyzer (single)")
        finally:
            tmp_path.unlink(missing_ok=True)

    def sync_single_activity(self, activity_id: int) -> None:
        """Fetch and process a single activity end-to-end.

        Args:
            activity_id: Strava activity ID.
        """
        logger.info(f"Syncing single activity {activity_id}")
        self.fetch_single_activity(activity_id)
        self.process_single_activity(activity_id)
        logger.info(f"Single activity {activity_id} sync complete")


def load_unified_config(config_path: Path) -> dict[str, Any]:
    """Load and validate a unified pipeline config YAML.

    Args:
        config_path: Path to the unified YAML config file.

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the config is missing required sections.
    """
    config_path = config_path.expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Unified config not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Validate minimum required structure
    if "data_dir" not in config:
        raise ValueError(
            "Unified config must have a top-level 'data_dir' key. "
            "See examples/unified_config.yaml for the expected format."
        )

    return config


def is_unified_config(config: dict[str, Any]) -> bool:
    """Check whether a parsed YAML dict looks like a unified pipeline config.

    Returns True if it has ``athlete:`` or ``fetcher:`` top-level keys, which
    distinguish it from the flat viewer-only config format.
    """
    return "athlete" in config or "fetcher" in config
