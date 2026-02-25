"""
Pipeline orchestrator for running the full fetch → analyze → view workflow.

Constructs library Settings objects from a unified config and calls
StravaFetcher / StravaAnalyzer Python APIs directly (no subprocesses).
"""

import importlib.util
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ── Library availability guards ──────────────────────────────────────────
# These flags enable graceful degradation when the upstream libraries
# are not installed (e.g. dashboard-only usage).

HAS_FETCHER = importlib.util.find_spec("strava_fetcher") is not None
HAS_ANALYZER = importlib.util.find_spec("strava_analyzer") is not None


class PipelineOrchestrator:
    """Orchestrate fetch → analyze → view using library APIs.

    Reads a unified config dict and constructs library Settings objects for
    StravaFetcher and StravaAnalyzer directly — no subprocesses or temp files.

    Args:
        unified_config: Parsed unified YAML dict.
        config_dir: Directory containing the unified config (for relative path resolution).
    """

    def __init__(self, unified_config: dict[str, Any], config_dir: Path) -> None:
        self.config = unified_config
        self.config_dir = config_dir.resolve()

        # Resolve the shared data directory.
        # Default matches StravaFetcher's own default so the cached token at
        # ~/.strava_fetcher/data/token.json is found without re-authorization.
        raw_data_dir = self.config.get("data_dir", "~/.strava_fetcher/data")
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

    # ─── Settings construction ────────────────────────────────────────────

    def _build_fetcher_settings(self) -> Any:
        """Construct a StravaFetcher ``Settings`` object from unified config.

        The ``paths.data_dir`` is taken from the top-level ``data_dir`` key
        (defaulting to ``~/.strava_fetcher/data`` — StravaFetcher's own
        default).  An explicit ``fetcher.token_file`` override is forwarded
        so users who keep the token outside ``data_dir`` don't have to
        re-authorize on every launch.

        Returns:
            A ``strava_fetcher.Settings`` instance.

        Raises:
            ImportError: If ``strava-fetcher`` is not installed.
        """
        from strava_fetcher import Settings as FetcherSettings

        strava_api: dict[str, Any] = {}
        if "client_id" in self.fetcher:
            strava_api["client_id"] = str(self.fetcher["client_id"])
        if "client_secret" in self.fetcher:
            strava_api["client_secret"] = str(self.fetcher["client_secret"])

        sync_keys = ("max_pages", "retry_interval_seconds", "skip_trainer_activities")
        sync_dict = {k: self.fetcher[k] for k in sync_keys if k in self.fetcher}

        # Build paths dict, forwarding an explicit token_file if provided so
        # the pipeline finds an already-authorized token rather than prompting
        # for a new authorization code every time.
        paths: dict[str, Any] = {"data_dir": str(self.data_dir)}
        if "token_file" in self.fetcher:
            paths["token_file"] = str(
                Path(str(self.fetcher["token_file"])).expanduser()
            )

        return FetcherSettings(
            strava_api=strava_api,
            paths=paths,
            sync=sync_dict,
        )

    def _build_analyzer_settings(self) -> Any:
        """Construct a StravaAnalyzer ``Settings`` object from unified config.

        Passes ``athlete:`` fields directly to StravaAnalyzer's Settings — both
        use the same field names (e.g. ``rider_weight_kg``, ``ftp``).

        Returns:
            A ``strava_analyzer.Settings`` instance.

        Raises:
            ImportError: If ``strava-analyzer`` is not installed.
        """
        from strava_analyzer import Settings as AnalyzerSettings

        cfg: dict[str, Any] = {
            "data_dir": str(self.data_dir),
            "activities_file": str(self.data_dir / "activities.csv"),
            "streams_dir": str(self.data_dir / "Streams"),
            "processed_data_dir": str(self.data_dir),
        }

        # Athlete fields pass through directly — names are aligned with Analyzer
        cfg.update(self.athlete)

        # Merge analyzer-specific overrides (ctl_days, atl_days, etc.)
        for key, value in self.analyzer.items():
            cfg[key] = value

        return AnalyzerSettings(**cfg)

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

        # Athlete fields → viewer (names are aligned, pass through directly)
        for key in ("ftp", "max_hr", "rider_weight_kg", "cp", "w_prime"):
            if key in self.athlete:
                viewer_cfg[key] = self.athlete[key]

        # Viewer-specific settings
        for key, value in self.viewer.items():
            viewer_cfg[key] = value

        return viewer_cfg

    # ─── Internal helpers ─────────────────────────────────────────────────

    def _ensure_data_dir(self) -> None:
        """Create the shared data directory and Streams sub-directory if needed."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "Streams").mkdir(parents=True, exist_ok=True)

    # ─── Public methods ───────────────────────────────────────────────────

    def run_fetch(self, *, full: bool = False) -> None:
        """Fetch activities via the StravaFetcher Python API.

        Args:
            full: Force a complete re-fetch of all activities.

        Raises:
            ImportError: If ``strava-fetcher`` is not installed.
        """
        from strava_fetcher import StravaSyncPipeline

        self._ensure_data_dir()
        settings = self._build_fetcher_settings()
        pipeline = StravaSyncPipeline(settings)

        logger.info("Running StravaFetcher (library mode)...")
        pipeline.run(full=full)
        logger.info("Fetch complete")

    def run_analyze(
        self,
        *,
        force: bool = False,
        recompute_from: str | None = None,
    ) -> None:
        """Analyze activities via the StravaAnalyzer Python API.

        Args:
            force: Force full re-analysis of all activities.
            recompute_from: ISO date to selectively recompute from.

        Raises:
            ImportError: If ``strava-analyzer`` is not installed.
        """
        from strava_analyzer import Pipeline as AnalyzerPipeline

        settings = self._build_analyzer_settings()
        pipeline = AnalyzerPipeline(settings)

        effective_recompute = None if force else recompute_from
        logger.info("Running StravaAnalyzer (library mode)...")
        pipeline.run(recompute_from=effective_recompute)
        logger.info("Analysis complete")

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
        logger.info("Starting pipeline sync (library mode)")
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

    def fetch_single_activity(self, activity_id: int) -> None:
        """Fetch a single activity via the StravaFetcher Python API.

        Args:
            activity_id: Strava activity ID.

        Raises:
            ImportError: If ``strava-fetcher`` is not installed.
        """
        from strava_fetcher import StravaSyncPipeline

        self._ensure_data_dir()
        settings = self._build_fetcher_settings()
        pipeline = StravaSyncPipeline(settings)
        pipeline.fetch_single_activity(activity_id)

    def process_single_activity(self, activity_id: int) -> None:
        """Process a single activity via the StravaAnalyzer Python API.

        Args:
            activity_id: Strava activity ID.

        Raises:
            ImportError: If ``strava-analyzer`` is not installed.
        """
        from strava_analyzer import Pipeline as AnalyzerPipeline

        settings = self._build_analyzer_settings()
        pipeline = AnalyzerPipeline(settings)
        pipeline.process_single_activity(activity_id)

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
