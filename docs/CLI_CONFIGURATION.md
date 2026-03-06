# CLI & Configuration Reference

## CLI Commands

### `activities-viewer run`

Launch the Streamlit dashboard.

```bash
activities-viewer run --config config.yaml [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config` | Required | Path to YAML config file |
| `--port` | 8501 | Streamlit server port |
| `--verbose` | false | Enable debug logging |

### `activities-viewer sync`

Run the full pipeline: fetch from Strava → analyze → launch dashboard.

```bash
activities-viewer sync --config unified_config.yaml [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config` | Required | Path to unified YAML config |
| `--port` | 8501 | Streamlit server port |
| `--skip-fetch` | false | Skip Strava API fetch step |
| `--skip-analyze` | false | Skip analysis step |
| `--verbose` | false | Enable debug logging |

Requires the unified config format with `fetcher`, `analyzer`, and `athlete` sections. See [`examples/unified_config.yaml`](../examples/unified_config.yaml).

### `activities-viewer validate`

Check that a config file is valid and data files are accessible.

```bash
activities-viewer validate --config config.yaml
```

### `activities-viewer version`

Print the installed version.

```bash
activities-viewer version
```

## Configuration File

ActivitiesViewer uses YAML configuration with [Pydantic](https://docs.pydantic.dev/) validation.

### Viewer-Only Config (`config.yaml`)

For use with `activities-viewer run`. Requires pre-generated data from StravaAnalyzer.

```yaml
# ── Data Paths (required) ──
data_dir: "/path/to/your/data"
activities_raw_file: "activities_raw.csv"       # Elapsed-time metrics
activities_moving_file: "activities_moving.csv"  # Moving-time metrics
streams_dir: "Streams"                           # Per-activity streams

# Legacy single-file (if you don't have the dual-file format)
# activities_enriched_file: "activities_enriched.csv"

# ── Athlete Profile (required) ──
ftp: 285.0              # Functional Threshold Power (watts)
rider_weight_kg: 77.0   # Weight (kg)
max_hr: 185             # Maximum heart rate (bpm)

# ── Optional: Critical Power ──
# Typically computed from data; set manually if you have lab values
# cp: 260               # Critical Power (watts)
# w_prime: 25000         # W' anaerobic capacity (joules)

# ── Optional: Goal Tracking ──
# target_wkg: 4.0
# target_date: "2026-06-01"
# baseline_ftp: 285
# baseline_date: "2025-12-01"

# ── Optional: AI Coach ──
# google_api_key: "your-gemini-api-key"

# ── App Settings ──
verbose: false
cache_ttl: 3600         # Cache TTL in seconds
page_title: "Activities Viewer"
page_icon: "🚴"
```

### Unified Pipeline Config (`unified_config.yaml`)

For use with `activities-viewer sync`. Includes Strava API credentials.

```yaml
data_dir: "~/.strava_fetcher/data"

athlete:
  ftp: 285.0
  rider_weight_kg: 77.0
  max_hr: 185

fetcher:
  client_id: "your_client_id"
  client_secret: "your_client_secret"

analyzer:
  # ctl_days: 42
  # atl_days: 7

viewer:
  page_title: "Activities Viewer"
  cache_ttl: 3600
```

See [`examples/unified_config.yaml`](../examples/unified_config.yaml) for the fully annotated version.

### Environment Variables

Any config field can be overridden via environment variable with the `ACTIVITIES_VIEWER_` prefix:

```bash
export ACTIVITIES_VIEWER_FTP=290
export ACTIVITIES_VIEWER_DATA_DIR=/data/strava
export ACTIVITIES_VIEWER_GOOGLE_API_KEY=your-key
```

Environment variables take precedence over the config file.

## Data Directory Structure

The `data_dir` should contain the output from StravaAnalyzer:

```
data_dir/
├── activities_raw.csv
├── activities_moving.csv
├── activity_summary.json    # optional
├── token.json               # auto-created by Strava OAuth
└── Streams/
    ├── stream_12345678.csv
    └── ...
```

See [DATA_STRUCTURE.md](DATA_STRUCTURE.md) for column details.

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Home** | Goal tracking, PMC, recent activities |
| **Analysis** | Fluid explorer with Overview / Physiology / Power Profile / Recovery modes |
| **Activity Detail** | Single activity deep dive with route map |
| **AI Coach** | Natural language training queries (requires Gemini API key) |
| **Training Plan** | AI-generated periodized plans with TSS tracking |
| **Fitness Estimation** | Auto-estimate FTP and max HR from your data |
| **Strava Connect** | Browser-based OAuth (for Docker deployments) |
| **Settings** | Edit athlete profile and config from the UI |
