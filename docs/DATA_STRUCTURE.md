# Data Structure

ActivitiesViewer reads enriched cycling data produced by [StravaAnalyzer](https://github.com/hope0hermes/StravaAnalyzer).

## Data Directory Layout

```
data_dir/
├── activities_raw.csv          # Required: all metrics (elapsed time base)
├── activities_moving.csv       # Recommended: metrics (moving time base)
├── activity_summary.json       # Optional: summary statistics
├── token.json                  # Auto-created by Strava OAuth
└── Streams/                    # Optional: per-activity stream data
    ├── stream_12345678.csv
    ├── stream_12345679.csv
    └── ...
```

## Activity CSV Files

### Dual-File Format (Default)

StravaAnalyzer v2.0+ produces two CSV files:

| File | Time base | Use case |
|------|-----------|----------|
| `activities_raw.csv` | Total elapsed time | Includes rest stops, wait time |
| `activities_moving.csv` | Moving time only | More accurate training metrics |

Both files share the same columns. The viewer uses `activities_raw.csv` as primary and falls back to `activities_moving.csv` for moving-time metrics.

### Legacy Format

If you only have a single `activities_enriched.csv`, set this in your config:

```yaml
activities_enriched_file: "activities_enriched.csv"
```

### Key Columns

These columns are used by the dashboard. Missing columns are handled gracefully — features that depend on them are simply hidden.

#### Identity & Metadata

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Strava activity ID |
| `name` | str | Activity name |
| `type` | str | Activity type (Ride, Run, VirtualRide, etc.) |
| `start_date_local` | datetime | Local start time |
| `device_name` | str | Recording device (e.g., "Garmin Edge 530") |

#### Duration & Distance

| Column | Type | Description |
|--------|------|-------------|
| `moving_time` | float | Moving time in seconds |
| `elapsed_time` | float | Total elapsed time in seconds |
| `distance` | float | Distance in meters |
| `total_elevation_gain` | float | Elevation gain in meters |

#### Power Metrics

| Column | Type | Description |
|--------|------|-------------|
| `average_watts` | float | Average power (W) |
| `weighted_average_watts` | float | Normalized Power (W) |
| `max_watts` | float | Peak power (W) |
| `best_20min_power` | float | Best 20-min average power (W) |
| `intensity_factor` | float | IF = NP / FTP |
| `training_stress_score` | float | TSS |

#### Heart Rate

| Column | Type | Description |
|--------|------|-------------|
| `average_heartrate` | float | Average HR (bpm) |
| `max_heartrate` | float | Maximum HR (bpm) |

#### Physiology (Computed by StravaAnalyzer)

| Column | Type | Description |
|--------|------|-------------|
| `efficiency_factor` | float | NP / average HR |
| `pw_hr_decoupling` | float | Power:HR drift (%) |
| `variability_index` | float | NP / average power |

#### Training Load (Computed by StravaAnalyzer)

| Column | Type | Description |
|--------|------|-------------|
| `ctl` | float | Chronic Training Load (fitness) |
| `atl` | float | Acute Training Load (fatigue) |
| `tsb` | float | Training Stress Balance (form) |

#### Critical Power Model

| Column | Type | Description |
|--------|------|-------------|
| `cp` | float | Critical Power (W) |
| `w_prime` | float | W' anaerobic capacity (J) |
| `cp_r_squared` | float | Model fit quality (0–1) |

## Stream Files

Individual activity streams are stored as CSV files in the `Streams/` directory, named `stream_{activity_id}.csv`.

### Stream Columns

| Column | Type | Description |
|--------|------|-------------|
| `time` | int | Elapsed seconds from start |
| `watts` | float | Instantaneous power (W) |
| `heartrate` | float | Heart rate (bpm) |
| `cadence` | float | Cadence (rpm) |
| `altitude` | float | Altitude (m) |
| `distance` | float | Cumulative distance (m) |
| `velocity_smooth` | float | Smoothed speed (m/s) |
| `latlng` | str | GPS coordinates (lat, lng) |
| `grade_smooth` | float | Road gradient (%) |
| `temp` | float | Temperature (°C) |

Not all columns are present in every stream — it depends on the sensors available during the activity.

## Validation

Run the config validator to check your data:

```bash
activities-viewer validate --config config.yaml
```

This verifies:
- Config file syntax and required fields
- Data directory exists and is readable
- CSV files can be loaded
- Key columns are present
