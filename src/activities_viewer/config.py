"""
Configuration management for ActivitiesViewer.

Settings are loaded from YAML configuration files and environment variables.
Based on the pydantic-settings pattern from StravaAnalyzer.
"""

import logging
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings for ActivitiesViewer.

    Settings are loaded in the following order of precedence (highest to lowest):
    1. Environment variables (e.g., ACTIVITIES_VIEWER_DATA_DIR)
    2. .env file (if found)
    3. YAML configuration file (if provided)
    4. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="ACTIVITIES_VIEWER_",
        env_file=".env",
        extra="ignore",
    )

    # --- File Paths ---
    data_dir: Path = Field(
        default=Path("data"),
        description="Path to data directory containing activities CSV and streams",
    )
    # New dual-file format (StravaAnalyzer output)
    activities_raw_file: Path = Field(
        default=Path("activities_raw.csv"),
        description="Filename of raw activities CSV (all data points, relative to data_dir)",
    )
    activities_moving_file: Path = Field(
        default=Path("activities_moving.csv"),
        description="Filename of moving activities CSV (movement only, relative to data_dir)",
    )
    # Backward compatibility: single enriched file
    activities_enriched_file: Path = Field(
        default=Path("activities_enriched.csv"),
        description="Filename of enriched activities CSV (legacy, relative to data_dir)",
    )
    activity_summary_file: Path = Field(
        default=Path("activity_summary.json"),
        description="Filename of activity summary JSON (relative to data_dir)",
    )
    streams_dir: Path = Field(
        default=Path("Streams"),
        description="Directory containing activity stream files (relative to data_dir)",
    )

    # --- Athlete Settings ---
    ftp: float = Field(
        default=285.0,
        gt=0,
        description="Functional Threshold Power in watts",
    )
    cp: float = Field(
        default=0.0,
        ge=0,
        description="Critical Power in watts (0 = disabled). Typically 85-90% of FTP",
    )
    w_prime: float = Field(
        default=0.0,
        ge=0,
        description="W-prime (anaerobic capacity) in joules (0 = disabled). Typical: 15,000-30,000 J",
    )
    weight_kg: float = Field(
        default=77.0,
        gt=0,
        description="Athlete weight in kilograms",
    )
    max_hr: int = Field(
        default=185,
        gt=0,
        description="Maximum heart rate in bpm",
    )

    # --- Goal Tracking (Optional) ---
    target_wkg: float | None = Field(
        default=None,
        gt=0,
        description="Target W/kg goal (e.g., 4.0)",
    )
    target_date: str | None = Field(
        default=None,
        description="Target date for goal in YYYY-MM-DD format (e.g., '2025-08-01')",
    )
    baseline_ftp: float | None = Field(
        default=None,
        gt=0,
        description="FTP when goal was set (for tracking progress from baseline)",
    )
    baseline_date: str | None = Field(
        default=None,
        description="Date when goal tracking began in YYYY-MM-DD format (e.g., '2024-12-01')",
    )

    # --- Training Plan Settings (Optional) ---
    weekly_hours_available: float = Field(
        default=10.0,
        gt=0,
        description="Available training hours per week",
    )
    training_plan_start: str | None = Field(
        default=None,
        description="Training plan start date in YYYY-MM-DD format",
    )
    training_phase: str = Field(
        default="base",
        description="Current training phase: base, build, specialty, taper",
    )
    key_events: list[dict] = Field(
        default_factory=list,
        description="List of key events: [{name, date, priority (A/B/C)}]",
    )
    training_plan_file: str | None = Field(
        default="training_plan.json",
        description="Path to save/load training plan (relative to config or absolute)",
    )

    # --- Application Settings ---
    data_source_type: str = Field(
        default="csv",
        description="Type of data source: 'csv' or 'sql'",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache time-to-live in seconds",
    )

    # --- Streamlit Settings ---
    page_title: str = Field(
        default="Activities Viewer",
        description="Page title for Streamlit app",
    )
    page_icon: str = Field(
        default="🚴",
        description="Page icon for Streamlit app",
    )

    # --- Gear Mapping ---
    gear_names: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of Strava gear IDs to human-readable names",
    )

    # --- Workout Type Mapping ---
    workout_type_names: dict[int, str] = Field(
        default_factory=lambda: {
            0: "Default",
            10: "Race",
            11: "Long Run",
            12: "Workout",
        },
        description="Mapping of Strava workout type IDs to names",
    )

    # --- Optional: AI Features (Phase 2) ---
    google_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key for AI features",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
    )

    # --- Optional: Database (Phase 3) ---
    database_url: str | None = Field(
        default=None,
        description="PostgreSQL database URL",
    )
    redis_url: str | None = Field(
        default=None,
        description="Redis cache URL",
    )

    def __init__(self, **data):
        """Initialize settings and resolve paths."""
        super().__init__(**data)
        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """Resolve all file paths to absolute paths."""
        # Make data_dir absolute
        if not self.data_dir.is_absolute():
            self.data_dir = self.data_dir.resolve()

        # Resolve activities_raw_file (new format)
        if not self.activities_raw_file.is_absolute():
            self.activities_raw_file = self.data_dir / self.activities_raw_file
        else:
            self.activities_raw_file = self.activities_raw_file.resolve()

        # Resolve activities_moving_file (new format)
        if not self.activities_moving_file.is_absolute():
            self.activities_moving_file = self.data_dir / self.activities_moving_file
        else:
            self.activities_moving_file = self.activities_moving_file.resolve()

        # Resolve activities_enriched_file (legacy format)
        if not self.activities_enriched_file.is_absolute():
            self.activities_enriched_file = (
                self.data_dir / self.activities_enriched_file
            )
        else:
            self.activities_enriched_file = self.activities_enriched_file.resolve()

        # Resolve activity_summary_file
        if not self.activity_summary_file.is_absolute():
            self.activity_summary_file = self.data_dir / self.activity_summary_file
        else:
            self.activity_summary_file = self.activity_summary_file.resolve()

        # Resolve streams_dir
        if not self.streams_dir.is_absolute():
            self.streams_dir = self.data_dir / self.streams_dir
        else:
            self.streams_dir = self.streams_dir.resolve()

    @field_validator("data_dir", mode="before")
    @classmethod
    def expand_user_path(cls, v: str | Path) -> Path:
        """Expand ~ and environment variables in paths."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v.expanduser()

    def validate_files(self) -> None:
        """Validate that all required data files exist.

        Supports both new dual-file format (activities_raw.csv, activities_moving.csv)
        and legacy single-file format (activities_enriched.csv).
        Note: Streams directory is optional as it may be populated later.
        """
        errors = []

        # Check for new dual-file format
        has_raw = self.activities_raw_file.exists()
        has_moving = self.activities_moving_file.exists()
        has_enriched = (
            self.activities_enriched_file.exists()
            if self.activities_enriched_file
            else False
        )

        # Require at least raw file (moving file is optional, will use raw as fallback)
        if not has_raw and not has_enriched:
            errors.append(
                f"Activities files not found. Need either:\n"
                f"    - {self.activities_raw_file} (new format), or\n"
                f"    - {self.activities_enriched_file} (legacy format)"
            )
        elif has_raw and not has_moving:
            logger.warning(
                f"Moving activities file not found: {self.activities_moving_file} "
                f"(will use raw data for both views)"
            )

        if not self.activity_summary_file.exists():
            errors.append(f"Summary file not found: {self.activity_summary_file}")

        # Streams directory is optional - may be populated after initial setup
        if not self.streams_dir.exists():
            logger.warning(
                f"Streams directory not found: {self.streams_dir} (optional)"
            )

        if errors:
            raise FileNotFoundError(
                "Configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def get_stream_path(self, activity_id: int) -> Path:
        """Get the path to a specific activity stream file.

        Args:
            activity_id: The Strava activity ID

        Returns:
            Path to the stream CSV file
        """
        return self.streams_dir / f"stream_{activity_id}.csv"

    def to_dict_for_display(self) -> dict:
        """Return a safe dictionary for display (without sensitive data)."""
        return {
            "data_dir": str(self.data_dir),
            "activities_enriched_file": str(self.activities_enriched_file),
            "activity_summary_file": str(self.activity_summary_file),
            "streams_dir": str(self.streams_dir),
            "ftp": self.ftp,
            "weight_kg": self.weight_kg,
            "max_hr": self.max_hr,
            "cache_ttl": self.cache_ttl,
        }

    def to_json_dict(self) -> dict:
        """Return a JSON-serializable dictionary for passing between processes."""
        return {
            "data_dir": str(self.data_dir),
            "activities_enriched_file": str(self.activities_enriched_file),
            "activities_raw_file": str(self.activities_raw_file),
            "activities_moving_file": str(self.activities_moving_file),
            "activity_summary_file": str(self.activity_summary_file),
            "streams_dir": str(self.streams_dir),
            "ftp": self.ftp,
            "weight_kg": self.weight_kg,
            "max_hr": self.max_hr,
            "target_wkg": self.target_wkg,
            "target_date": self.target_date,
            "baseline_ftp": self.baseline_ftp,
            "baseline_date": self.baseline_date,
            "cache_ttl": self.cache_ttl,
            "page_title": self.page_title,
            "page_icon": self.page_icon,
        }


def load_settings(config_file: Path | None = None) -> Settings:
    """Load settings from a YAML file, environment variables, and defaults.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Settings instance

    Raises:
        FileNotFoundError: If config_file doesn't exist
        ValueError: If configuration is invalid
    """
    if config_file:
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        logger.info(f"Loading configuration from {config_file}")
        with open(config_file, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if yaml_data is None:
            yaml_data = {}

        # Resolve data_dir relative to config file if not absolute
        if "data_dir" in yaml_data:
            data_dir_path = Path(yaml_data["data_dir"]).expanduser()
            if not data_dir_path.is_absolute():
                data_dir_path = config_file.parent / data_dir_path
            yaml_data["data_dir"] = str(data_dir_path.resolve())

        # Resolve training_plan_file relative to config file if not absolute
        if "training_plan_file" in yaml_data:
            plan_path = Path(yaml_data["training_plan_file"]).expanduser()
            if not plan_path.is_absolute():
                plan_path = config_file.parent / plan_path
            yaml_data["training_plan_file"] = str(plan_path.resolve())
        else:
            # Default to training_plan.json in config file directory
            yaml_data["training_plan_file"] = str((config_file.parent / "training_plan.json").resolve())

        logger.debug(f"Loaded YAML configuration: {yaml_data}")
        return Settings(**yaml_data)

    return Settings()
