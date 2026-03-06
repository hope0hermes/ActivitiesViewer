# Setup Guide

Detailed setup instructions for ActivitiesViewer.

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Runtime |
| [UV](https://github.com/astral-sh/uv) | Latest | Package manager |
| Git | Any | Clone the repo |
| Activity data | — | Enriched CSVs from [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer) |

### Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify: `uv --version`

## Step 1: Clone and Install

```bash
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer
uv sync
```

This creates a `.venv/` virtual environment and installs all dependencies including the upstream `strava-fetcher` and `strava-analyzer` packages.

## Step 2: Prepare Your Data

ActivitiesViewer reads enriched activity data produced by [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer). You need:

| File | Required | Description |
|------|----------|-------------|
| `activities_raw.csv` | Yes | Activities with metrics over total elapsed time |
| `activities_moving.csv` | Recommended | Activities with metrics over moving time only |
| `Streams/` directory | Optional | Per-activity stream CSVs for detailed analysis |

If you only have the legacy single-file format (`activities_enriched.csv`), that also works. See [DATA_STRUCTURE.md](DATA_STRUCTURE.md) for column details.

### Generate Data with StravaAnalyzer

```bash
cd ../StravaAnalyzer
strava-analyzer run --config config.yaml
```

This creates the CSV files and `Streams/` directory in your configured `data_dir`.

## Step 3: Configure

```bash
cp examples/config.yaml config.yaml
```

Edit `config.yaml`:

```yaml
# Point to your data directory
data_dir: "/path/to/your/data"

# Dual-file format (default from StravaAnalyzer v2.0+)
activities_raw_file: "activities_raw.csv"
activities_moving_file: "activities_moving.csv"
streams_dir: "Streams"

# Your athlete profile
ftp: 285.0              # Functional Threshold Power (watts)
rider_weight_kg: 77.0   # Weight in kg
max_hr: 185             # Maximum heart rate (bpm)
```

For the full list of options, see [CLI_CONFIGURATION.md](CLI_CONFIGURATION.md) or the annotated [`examples/config.yaml`](../examples/config.yaml).

## Step 4: Validate and Run

```bash
# Check config is valid
activities-viewer validate --config config.yaml

# Launch the dashboard
activities-viewer run --config config.yaml
```

Open http://localhost:8501.

## Step 5 (Optional): Full Pipeline

To fetch from Strava, analyze, and view in one command:

```bash
cp examples/unified_config.yaml config.yaml
# Add your Strava API credentials (client_id, client_secret)

activities-viewer sync --config config.yaml
```

See [`examples/unified_config.yaml`](../examples/unified_config.yaml) for the full pipeline config format.

## Optional Extras

### AI Coach (Google Gemini)

```bash
uv sync --extra ai
```

Add to `config.yaml`:

```yaml
google_api_key: "your-gemini-api-key"
```

### Development Tools

```bash
uv sync --extra dev
```

## Troubleshooting

### "No module named 'strava_fetcher'" or similar

The upstream packages (`strava-fetcher`, `strava-analyzer`) are hosted on a private Devpi index. Ensure your `uv.toml` includes the index URL, or install from the correct source.

### "FileNotFoundError: activities_raw.csv"

Check that `data_dir` in your config points to the directory containing the CSV files. Paths can be absolute or relative to the config file location.

### Port Already in Use

```bash
activities-viewer run --config config.yaml --port 8502
```

### Dashboard Shows No Data

1. Verify CSV files exist: `ls /path/to/data/*.csv`
2. Check that the files have the expected columns: `head -1 /path/to/data/activities_raw.csv`
3. Run `activities-viewer validate --config config.yaml` for diagnostics

### Permission Errors on Data Files

Ensure your user has read access: `chmod -R u+r /path/to/data/`
