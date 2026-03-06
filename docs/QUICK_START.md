# Quick Start

Get up and running in 5 minutes.

## 1. Install

```bash
git clone https://github.com/hope0hermes/ActivitiesViewer.git
cd ActivitiesViewer

# Install UV if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## 2. Configure

```bash
cp examples/config.yaml config.yaml
```

Edit `config.yaml` with your settings:

```yaml
# Data paths (point to your StravaAnalyzer output)
data_dir: "/path/to/your/data"
activities_raw_file: "activities_raw.csv"
activities_moving_file: "activities_moving.csv"
streams_dir: "Streams"

# Athlete profile
ftp: 285.0
rider_weight_kg: 77.0
max_hr: 185
```

## 3. Run

```bash
# Validate config first
activities-viewer validate --config config.yaml

# Launch dashboard
activities-viewer run --config config.yaml
```

Open http://localhost:8501 in your browser.

## Full Pipeline (Optional)

To fetch from Strava + analyze + view in one step:

```bash
cp examples/unified_config.yaml config.yaml
# Edit with your Strava API credentials + athlete settings

activities-viewer sync --config config.yaml
```

## CLI Commands

```bash
activities-viewer run      --config config.yaml   # Launch dashboard
activities-viewer sync     --config config.yaml   # Full pipeline
activities-viewer validate --config config.yaml   # Check config
activities-viewer version                          # Show version
activities-viewer --help                           # All options
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Port 8501 in use | `activities-viewer run --config config.yaml --port 8502` |
| Files not found | Check `data_dir` path in `config.yaml` |
| Import errors | Run `uv sync` to reinstall dependencies |
| No activities shown | Ensure `activities_raw_file` points to a valid CSV |

## What's Next

- [SETUP.md](SETUP.md) — Detailed setup with prerequisites
- [DATA_STRUCTURE.md](DATA_STRUCTURE.md) — Expected data format
- [CLI_CONFIGURATION.md](CLI_CONFIGURATION.md) — Full configuration reference
- [SHARING.md](SHARING.md) — Share with friends via Docker
