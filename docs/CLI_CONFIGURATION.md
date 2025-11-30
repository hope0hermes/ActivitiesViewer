# ActivitiesViewer CLI & Configuration Guide

## Quick Start

### 1. Create a Configuration File

Copy the example configuration and update it with your data paths:

```bash
cp examples/config.yaml config.yaml
```

Edit `config.yaml` with your settings:

```yaml
# Path to your enriched activities data directory
data_dir: "../dev/data_enriched"

# Data files within that directory
activities_enriched_file: "activities_enriched.csv"
activity_summary_file: "activity_summary.json"
streams_dir: "Streams"

# Your athlete profile
ftp: 285.0
weight_kg: 77.0
max_hr: 185
```

### 2. Run the Dashboard

```bash
# Using the CLI with a config file
activities-viewer run --config config.yaml

# Or with UV
uv run activities-viewer run --config config.yaml

# Custom port
activities-viewer run --config config.yaml --port 8502

# Verbose output
activities-viewer run --config config.yaml --verbose
```

### 3. Validate Configuration

Before running the dashboard, validate your setup:

```bash
activities-viewer validate --config config.yaml
```

This will check:
- Configuration file syntax
- All required data files exist
- File counts and basic statistics

## Configuration File Format

The configuration uses YAML format with the following structure:

### Required Sections

```yaml
# Path to data directory (absolute or relative to config file)
data_dir: "../dev/data_enriched"

# File paths within data_dir (relative paths)
activities_enriched_file: "activities_enriched.csv"
activity_summary_file: "activity_summary.json"
streams_dir: "Streams"
```

### Athlete Profile

```yaml
ftp: 285.0              # Functional Threshold Power in watts
weight_kg: 77.0         # Body weight in kilograms
max_hr: 185             # Maximum heart rate in bpm
```

### Optional: Application Settings

```yaml
verbose: false          # Enable debug logging
cache_ttl: 3600         # Cache time-to-live in seconds
page_title: "Activities Viewer"
page_icon: "🚴"
```

### Optional: AI Features (Phase 2)

```yaml
google_api_key: "your-api-key"      # Gemini API key
qdrant_url: "http://localhost:6333"  # Vector DB URL
```

### Optional: Database (Phase 3)

```yaml
database_url: "postgresql://user:pass@localhost:5432/db"
redis_url: "redis://localhost:6379/0"
```

## Environment Variables

Configuration can also be set via environment variables with the `ACTIVITIES_VIEWER_` prefix:

```bash
export ACTIVITIES_VIEWER_DATA_DIR=/path/to/data
export ACTIVITIES_VIEWER_FTP=285
export ACTIVITIES_VIEWER_WEIGHT_KG=77

activities-viewer run --config config.yaml
```

### Variable Naming Convention

- YAML: `ftp`
- Env: `ACTIVITIES_VIEWER_FTP`

- YAML: `weight_kg`
- Env: `ACTIVITIES_VIEWER_WEIGHT_KG`

- YAML: `activities_enriched_file`
- Env: `ACTIVITIES_VIEWER_ACTIVITIES_ENRICHED_FILE`

## CLI Commands

### `run` - Start the Dashboard

Start the Streamlit dashboard with the specified configuration.

```bash
activities-viewer run --config config.yaml [OPTIONS]

Options:
  --config PATH              Path to configuration YAML file (required)
  --port INTEGER             Port to run Streamlit on (default: 8501)
  --verbose/--quiet          Enable verbose output (default: quiet)
  -h, --help                 Show help message
```

**Example:**

```bash
# Start dashboard with config validation
activities-viewer run --config config.yaml --verbose

# Run on custom port
activities-viewer run --config config.yaml --port 8502

# Quiet mode (suppress logs)
activities-viewer run --config config.yaml --quiet
```

### `validate` - Check Configuration

Validate that all configuration and data files are correct.

```bash
activities-viewer validate --config config.yaml

Options:
  --config PATH    Path to configuration YAML file (required)
  -h, --help       Show help message
```

**Output:**

```
Configuration Validation Summary
============================================================
  data_dir: /path/to/data_enriched
  activities_enriched_file: /path/to/data_enriched/activities_enriched.csv
  activity_summary_file: /path/to/data_enriched/activity_summary.json
  streams_dir: /path/to/data_enriched/Streams
  ftp: 285.0
  weight_kg: 77.0
  max_hr: 185
  cache_ttl: 3600

  Activities loaded: 1812 records
  Columns: 140
  Summary data: 25 keys
  Stream files: 1812 found

============================================================
✅ All validations passed!
============================================================
```

### `version` - Show Version

Display the installed version of ActivitiesViewer.

```bash
activities-viewer version
```

## Configuration Loading Order

Settings are loaded with the following precedence (highest to lowest):

1. **Environment Variables** (e.g., `ACTIVITIES_VIEWER_FTP=290`)
2. **YAML Configuration File** (passed via `--config` option)
3. **Default Values** (built-in defaults)

Example with precedence:

```bash
# File has ftp: 285, env has ACTIVITIES_VIEWER_FTP=290
# Result: ftp = 290 (env wins)
export ACTIVITIES_VIEWER_FTP=290
activities-viewer run --config config.yaml
```

## Data Directory Structure

ActivitiesViewer expects the following directory structure:

```
data_enriched/
├── activities_enriched.csv      # Main enriched activities file
├── activity_summary.json        # Summary statistics
└── Streams/                     # Activity stream files
    ├── stream_1001301785.csv
    ├── stream_10017325050.csv
    ├── stream_10017325928.csv
    └── ... (one per activity)
```

### File Specifications

**activities_enriched.csv:**
- CSV file with enriched activity metrics
- Generated by StravaAnalyzer
- Expected columns: start_date, distance, normalized_power, etc.

**activity_summary.json:**
- JSON file with aggregate statistics
- Contains per-athlete performance data
- Updated after running StravaAnalyzer

**Streams/stream_*.csv:**
- Individual activity stream files
- Naming format: `stream_{activity_id}.csv`
- Contains time-series data: power, HR, GPS, etc.

## Troubleshooting

### "Configuration file not found"

```
FileNotFoundError: Configuration file not found: config.yaml
```

**Solution:** Make sure the config file exists in the current directory or provide the full path:

```bash
activities-viewer run --config /full/path/to/config.yaml
```

### "Activities file not found"

```
Configuration validation failed:
  - Activities file not found: /path/to/activities_enriched.csv
```

**Solution:** Check that `data_dir` in your config points to the correct directory with all required files:

```bash
ls -la /path/to/data_enriched/
```

### "Streams directory not found"

**Solution:** Ensure the `Streams` subdirectory exists and contains stream files:

```bash
ls -la /path/to/data_enriched/Streams/ | head
```

### Port Already in Use

```
Address already in use
```

**Solution:** Use a different port:

```bash
activities-viewer run --config config.yaml --port 8502
```

### Validation Passes But Dashboard Won't Start

- Check internet connection (for Streamlit initialization)
- Verify all dependencies are installed: `uv sync`
- Try with `--verbose` flag for more information:

```bash
activities-viewer run --config config.yaml --verbose
```

## Integration with StravaAnalyzer

ActivitiesViewer is designed to work with data from [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer).

### Workflow

1. **Generate enriched data:**
   ```bash
   cd ../StravaAnalyzer
   strava-analyzer run --config config.yaml
   ```

2. **Create ActivitiesViewer config:**
   ```bash
   cd ../ActivitiesViewer
   cp examples/config.yaml config.yaml
   # Edit config.yaml to point to StravaAnalyzer's output
   ```

3. **Run dashboard:**
   ```bash
   activities-viewer run --config config.yaml
   ```

## Next Steps

- See [README.md](../README.md) for general information
- Check [SETUP.md](../docs/SETUP.md) for detailed setup instructions
- Review the [Implementation Plan](../DASHBOARD_IMPLEMENTATION_PLAN.md) for features and roadmap
