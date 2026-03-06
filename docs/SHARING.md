# Sharing ActivitiesViewer

How to run ActivitiesViewer with Docker to explore your own Strava cycling data.
No Python installation required — the Docker image ships with everything
(including StravaFetcher and StravaAnalyzer) pre-installed.

## What You Need

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS / Windows) or Docker Engine (Linux)
- A free [Strava API application](https://www.strava.com/settings/api) — you only need the **Client ID** and **Client Secret**

## Quick Start (Full Pipeline)

This is the recommended path. The container will fetch your activities from
Strava, compute all the analytics metrics, and launch the dashboard — all in
one command.

### 1. Pull the image

```bash
docker pull ghcr.io/hope0hermes/activities-viewer:latest
```

### 2. Create a config file

Save the following as `config.yaml` in a new, empty directory. Adjust the
athlete values to match your profile:

```yaml
# Where data is stored inside the container (do not change)
data_dir: "/data"

# Your physiological metrics
athlete:
  ftp: 250.0             # Functional Threshold Power (watts)
  rider_weight_kg: 72.0  # Body weight (kg)
  max_hr: 190            # Maximum heart rate (bpm)

# Strava API credentials — get yours at https://www.strava.com/settings/api
fetcher:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"

# Analysis engine (defaults are fine for most users)
analyzer: {}
  # Optional overrides (uncomment to tune):
  # ctl_days: 28            # Chronic Training Load window (default: 28)
  # atl_days: 7             # Acute Training Load window (default: 7)
  # cp_window_days: 90      # Rolling window for CP/W' estimation (default: 90)

# Dashboard display
viewer:
  page_title: "My Training Dashboard"
  cache_ttl: 3600
```

> **Tip — FTP:** If you don't know your FTP, enter a rough estimate. The
> *Fitness Estimation* page will suggest a value based on your best 20-minute
> power data once your activities are loaded.
>
> **Tip — Max HR:** Use the highest heart rate you have ever recorded. The
> *Fitness Estimation* page will also show your observed max across all rides.

### 3. Run the container

```bash
docker run -d \
  --name activities-viewer \
  -p 8501:8501 \
  -v ./data:/data \
  -v ./config.yaml:/app/config.yaml:ro \
  ghcr.io/hope0hermes/activities-viewer:latest \
  sync --config /app/config.yaml --launch
```

What this does:

| Flag / Volume | Purpose |
|---|---|
| `-p 8501:8501` | Exposes the dashboard on http://localhost:8501 |
| `-v ./data:/data` | Persists fetched & analyzed data between runs |
| `-v ./config.yaml:/app/config.yaml:ro` | Mounts your config (read-only) |
| `sync --config ... --launch` | Runs fetch → analyze → launch dashboard |

### 4. Authenticate with Strava

On the first run the container will need a one-time Strava authorization.
Open http://localhost:8501 and follow the **Strava Connect** prompt in the
sidebar. This stores a token under `./data/` so you won't need to do it again.

### 5. Explore the Dashboard

Once sync completes the dashboard loads automatically. Subsequent runs will
only fetch new activities since your last sync.

### 6. Stop / restart

```bash
docker stop activities-viewer      # stop
docker start activities-viewer     # restart (data is persisted)
docker rm activities-viewer        # remove the container entirely
```

## Docker Compose (Alternative)

If you prefer Docker Compose, create a `docker-compose.yml` next to your
`config.yaml`:

```yaml
services:
  viewer:
    image: ghcr.io/hope0hermes/activities-viewer:latest
    ports:
      - "8501:8501"
    volumes:
      - ./data:/data
      - ./config.yaml:/app/config.yaml:ro
    command: ["sync", "--config", "/app/config.yaml", "--launch"]
```

Then:

```bash
docker compose up -d          # start
docker compose logs -f        # watch logs
docker compose down           # stop
```

## Updating

```bash
docker pull ghcr.io/hope0hermes/activities-viewer:latest
docker stop activities-viewer && docker rm activities-viewer
# Then re-run the `docker run` command above (your data persists in ./data/)
```

## Viewer-Only Mode

If you already have enriched CSV files (e.g. someone shared their dataset),
you can skip the pipeline and just view the data:

```bash
docker run -d \
  --name activities-viewer \
  -p 8501:8501 \
  -v /path/to/data:/data:ro \
  -v /path/to/config.yaml:/app/config.yaml:ro \
  ghcr.io/hope0hermes/activities-viewer:latest
```

For viewer-only mode use a simpler config (no `fetcher`/`analyzer` sections):

```yaml
data_dir: "/data"
ftp: 250.0
rider_weight_kg: 72.0
max_hr: 190
```

## Configuration Tips

### Goal Tracking (Optional)

Add to your config to see W/kg progress on the home page:

```yaml
viewer:
  target_wkg: 4.0
  target_date: "2026-06-01"
  baseline_ftp: 250
  baseline_date: "2025-01-01"
```

### AI Coach (Optional)

Requires a Google Gemini API key (free tier available). Add to your config:

```yaml
viewer:
  google_api_key: "your-gemini-api-key"
```

## Creating a Strava API Application

1. Go to https://www.strava.com/settings/api
2. Fill in the form:
   - **Application Name:** anything (e.g. "My Dashboard")
   - **Category:** choose any
   - **Authorization Callback Domain:** `localhost`
3. After creating, copy the **Client ID** and **Client Secret** into your `config.yaml`

This is free and takes about 2 minutes.

## Troubleshooting

### Container starts but dashboard shows "Waiting for configuration"

The config volume mount may be wrong. Verify:

```bash
docker exec activities-viewer cat /app/config.yaml
```

### Sync fails with authentication error

The Strava token may have expired. Remove the cached token and re-authorize:

```bash
rm ./data/token.json
docker restart activities-viewer
```

Then visit http://localhost:8501 and follow the Strava Connect prompt again.

### "FileNotFoundError" for CSV files

If running in viewer-only mode, check that the data volume is mounted and
contains the expected files:

```bash
docker exec activities-viewer ls /data/
```

### Port conflict

If port 8501 is already in use, map to a different host port:

```bash
docker run -p 8502:8501 ...
```

Then visit http://localhost:8502.

### Permission denied on data files (Linux)

Ensure the data directory is readable:

```bash
chmod -R a+r ./data/
```
