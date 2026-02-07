"""
Command-line interface for ActivitiesViewer.

Provides commands to run the dashboard and validate configuration.
"""

import json
import logging
from pathlib import Path

import click
import pandas as pd

from .config import load_settings


# Custom command class to show full help text
class CustomGroup(click.Group):
    """Custom Click group that shows full command help without truncation."""

    def format_commands(self, ctx, formatter):
        """Format commands with full descriptions."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            help_text = cmd.get_short_help_str(limit=999)
            commands.append((subcommand, help_text))

        if commands:
            with formatter.section("Commands"):
                formatter.write_dl(commands)


def configure_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level.

    Args:
        verbose: Enable debug logging
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@click.group(cls=CustomGroup, context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """ActivitiesViewer - Streamlit dashboard for cycling activities analysis.

    Quick start: activities-viewer run --config config.yaml
    """


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to configuration YAML file",
)
@click.option(
    "--verbose/--quiet",
    default=False,
    help="Enable verbose output",
)
@click.option(
    "--port",
    type=int,
    default=8501,
    help="Port to run Streamlit on",
)
def run(config: Path, verbose: bool, port: int) -> None:
    """Start the ActivitiesViewer Streamlit dashboard.

    Loads configuration from the specified YAML file and starts the
    interactive dashboard for analyzing cycling activities.
    """
    configure_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Loading configuration from {config}")
        settings = load_settings(config)

        logger.info("Validating data files...")
        settings.validate_files()
        logger.info("✅ All data files found")

        # Import streamlit here to avoid startup delay if not needed
        import json
        import os
        import subprocess
        import sys
        import tempfile

        app_path = Path(__file__).parent / "app.py"
        logger.info(f"Starting Streamlit dashboard on port {port}...")
        logger.info(f"Open browser at http://localhost:{port}")

        # Create a temporary environment file with settings serialized as JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(settings.to_dict_for_display(), f)
            settings_file = f.name

        try:
            env = os.environ.copy()
            env["ACTIVITIES_VIEWER_CONFIG"] = json.dumps(settings.to_json_dict())

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(app_path),
                    "--server.port",
                    str(port),
                    "--logger.level=error",  # Suppress streamlit's verbose logging
                ],
                env=env,
                check=False,
            )
        finally:
            # Clean up temporary file
            import os

            if os.path.exists(settings_file):
                os.remove(settings_file)

    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise click.Abort() from e


@main.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to configuration YAML file",
)
def validate(config: Path) -> None:
    """Validate configuration and data files.

    Checks that the configuration file is valid and all required
    data files exist and are readable.
    """
    logger = logging.getLogger(__name__)
    configure_logging(verbose=True)

    try:
        logger.info(f"Loading configuration from {config}")
        settings = load_settings(config)

        logger.info("Validating data files...")
        settings.validate_files()

        # Load and display summary statistics
        logger.info("\n" + "=" * 60)
        logger.info("Configuration Validation Summary")
        logger.info("=" * 60)

        for key, value in settings.to_dict_for_display().items():
            logger.info(f"  {key}: {value}")

        # Check activities file (support both dual-file and legacy single-file formats)
        try:
            if settings.activities_raw_file.exists():
                activities_df = pd.read_csv(
                    settings.activities_raw_file, sep=";", low_memory=False
                )
                source_file = settings.activities_raw_file.name
            elif (
                settings.activities_enriched_file
                and settings.activities_enriched_file.exists()
            ):
                activities_df = pd.read_csv(
                    settings.activities_enriched_file, sep=";", low_memory=False
                )
                source_file = settings.activities_enriched_file.name
            else:
                raise FileNotFoundError("No activities file found")
        except UnicodeDecodeError:
            if settings.activities_raw_file.exists():
                activities_df = pd.read_csv(
                    settings.activities_raw_file,
                    sep=";",
                    encoding="latin-1",
                    low_memory=False,
                )
            else:
                activities_df = pd.read_csv(
                    settings.activities_enriched_file,
                    sep=";",
                    encoding="latin-1",
                    low_memory=False,
                )
        logger.info(
            f"\n  Activities loaded: {len(activities_df)} records from {source_file}"
        )
        logger.info(f"  Columns: {len(activities_df.columns)}")

        # Check summary file
        with open(settings.activity_summary_file, encoding="utf-8") as f:
            summary = json.load(f)
        logger.info(f"  Summary data: {len(summary)} keys")

        # Check streams
        stream_files = list(settings.streams_dir.glob("stream_*.csv"))
        logger.info(f"  Stream files: {len(stream_files)} found")

        logger.info("\n" + "=" * 60)
        logger.info("✅ All validations passed!")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        raise click.Abort() from e


@main.command()
def version() -> None:
    """Show version information."""
    from . import __version__

    click.echo(f"ActivitiesViewer {__version__}")


if __name__ == "__main__":
    main()
