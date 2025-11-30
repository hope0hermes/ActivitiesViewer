# ActivitiesViewer - Quick Reference

## Installation & Setup

```bash
# Clone the repository
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer

# Create virtual environment and install
uv sync

# Install with dev dependencies
uv pip install -e ".[dev]"
```

## Configuration

```bash
# Create config from example
cp examples/config.yaml config.yaml

# Edit config with your paths and settings
nano config.yaml
```

**Minimal config.yaml:**

```yaml
data_dir: "../dev/data_enriched"
activities_enriched_file: "activities_enriched.csv"
activity_summary_file: "activity_summary.json"
streams_dir: "Streams"

ftp: 285.0
weight_kg: 77.0
max_hr: 185
```

## Running the Dashboard

```bash
# Validate configuration first
activities-viewer validate --config config.yaml

# Start the dashboard
activities-viewer run --config config.yaml

# Custom port
activities-viewer run --config config.yaml --port 8502

# Verbose output
activities-viewer run --config config.yaml --verbose
```

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/activities_viewer

# Format code
uv run black src/ tests/
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/activities_viewer
```

## Environment Variables

```bash
export ACTIVITIES_VIEWER_DATA_DIR=/path/to/data
export ACTIVITIES_VIEWER_FTP=285
export ACTIVITIES_VIEWER_WEIGHT_KG=77
export ACTIVITIES_VIEWER_MAX_HR=185

activities-viewer run --config config.yaml
```

## Required Data Files

```
data_enriched/
├── activities_enriched.csv     # from StravaAnalyzer
├── activity_summary.json       # from StravaAnalyzer
└── Streams/
    └── stream_*.csv            # activity streams
```

## Useful Commands

```bash
# Show help
activities-viewer --help
activities-viewer run --help
activities-viewer validate --help

# Show version
activities-viewer version

# Run tests
uv run pytest tests/ -v

# Check for issues
uv run mypy src/
uv run ruff check src/
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Port 8501 in use | Use `--port 8502` flag |
| Files not found | Check `data_dir` path in config |
| Import errors | Run `uv sync` to install dependencies |
| Type errors | Run `uv run mypy src/` to check |

## Documentation

- [CLI & Configuration Guide](CLI_CONFIGURATION.md) - Detailed CLI reference
- [Setup Guide](SETUP.md) - Installation and environment setup
- [Implementation Plan](../DASHBOARD_IMPLEMENTATION_PLAN.md) - Features and roadmap
- [README](../README.md) - General information

## Project Structure

```
ActivitiesViewer/
├── src/activities_viewer/
│   ├── app.py          # Main Streamlit app
│   ├── cli.py          # CLI commands
│   ├── config.py       # Configuration & Settings
│   ├── pages/          # Streamlit pages
│   ├── components/     # Reusable components
│   ├── data/           # Data loading
│   ├── analytics/      # Business logic
│   └── viz/            # Visualizations
├── tests/              # Test suite
├── examples/           # Example configs
├── docs/               # Documentation
└── pyproject.toml      # Dependencies
```

## Next Steps

1. Copy `examples/config.yaml` to `config.yaml`
2. Update paths to your data directory
3. Run `activities-viewer validate --config config.yaml`
4. Run `activities-viewer run --config config.yaml`
5. Open browser at `http://localhost:8501`

## Integration with StravaAnalyzer

```bash
# Generate enriched data
cd ../StravaAnalyzer
strava-analyzer run --config config.yaml

# Then run ActivitiesViewer with the output
cd ../ActivitiesViewer
activities-viewer run --config config.yaml
```
