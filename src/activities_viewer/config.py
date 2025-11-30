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
    activities_enriched_file: Path = Field(
        default=Path("activities_enriched.csv"),
        description="Filename of enriched activities CSV (relative to data_dir)",
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

        # Resolve activities_enriched_file
        if not self.activities_enriched_file.is_absolute():
            self.activities_enriched_file = self.data_dir / self.activities_enriched_file
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

        Note: Streams directory is optional as it may be populated later.
        """
        errors = []

        if not self.activities_enriched_file.exists():
            errors.append(f"Activities file not found: {self.activities_enriched_file}")

        if not self.activity_summary_file.exists():
            errors.append(f"Summary file not found: {self.activity_summary_file}")

        # Streams directory is optional - may be populated after initial setup
        if not self.streams_dir.exists():
            logger.warning(f"Streams directory not found: {self.streams_dir} (optional)")

        if errors:
            raise FileNotFoundError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
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
            "activity_summary_file": str(self.activity_summary_file),
            "streams_dir": str(self.streams_dir),
            "ftp": self.ftp,
            "weight_kg": self.weight_kg,
            "max_hr": self.max_hr,
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

        logger.debug(f"Loaded YAML configuration: {yaml_data}")
        return Settings(**yaml_data)

    return Settings()
