#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────────────────────
# Activities Viewer — Docker entrypoint
#
# Modes:
#   (default)  — sync on first run, then launch Streamlit viewer
#   sync       — fetch + analyze only (no viewer)
#   viewer     — launch Streamlit only (no sync)
#   shell      — drop to bash (for debugging)
# ─────────────────────────────────────────────────────────────────────────

DATA_DIR="/data"
CONFIG="/data/unified_config.yaml"

# Generate unified config from environment variables
generate_config() {
    echo ">>> Generating unified config from environment variables..."

    cat > "$CONFIG" <<EOF
# Auto-generated unified config — do not edit manually.
# To change settings, update your .env file and restart the container.

data_dir: ${DATA_DIR}

athlete:
  ftp: ${FTP:-250}
  weight_kg: ${WEIGHT_KG:-75.0}
EOF

    # Optional athlete fields
    [ -n "$FTHR" ]       && echo "  fthr: $FTHR"          >> "$CONFIG"
    [ -n "$MAX_HR" ]     && echo "  max_hr: $MAX_HR"      >> "$CONFIG"
    [ -n "$LT1_HR" ]     && echo "  lt1_hr: $LT1_HR"      >> "$CONFIG"
    [ -n "$LT2_HR" ]     && echo "  lt2_hr: $LT2_HR"      >> "$CONFIG"
    [ -n "$CP" ]         && echo "  cp: $CP"               >> "$CONFIG"
    [ -n "$W_PRIME" ]    && echo "  w_prime: $W_PRIME"     >> "$CONFIG"

    # Fetcher section (Strava API credentials)
    cat >> "$CONFIG" <<EOF

fetcher:
  strava:
    client_id: "${STRAVA_CLIENT_ID:-}"
    client_secret: "${STRAVA_CLIENT_SECRET:-}"
  paths:
    data_dir: ${DATA_DIR}/fetcher
  sync:
    per_page: ${FETCH_PER_PAGE:-100}
EOF

    # Analyzer section
    cat >> "$CONFIG" <<EOF

analyzer:
  ctl_days: ${CTL_DAYS:-42}
  atl_days: ${ATL_DAYS:-7}
EOF
    [ -n "$ANALYZER_EXTRA" ] && echo "$ANALYZER_EXTRA" >> "$CONFIG"

    # Viewer section
    cat >> "$CONFIG" <<EOF

viewer:
  page_title: "${PAGE_TITLE:-Activities Viewer}"
  cache_ttl: ${CACHE_TTL:-300}
EOF

    # Goals (optional)
    if [ -n "$TARGET_WKG" ] || [ -n "$TARGET_DATE" ]; then
        echo "  goals:" >> "$CONFIG"
        [ -n "$TARGET_WKG" ]  && echo "    target_wkg: $TARGET_WKG"    >> "$CONFIG"
        [ -n "$TARGET_DATE" ] && echo "    target_date: \"$TARGET_DATE\"" >> "$CONFIG"
        [ -n "$BASELINE_FTP" ] && echo "    baseline_ftp: $BASELINE_FTP"  >> "$CONFIG"
    fi

    # AI (optional)
    if [ -n "$GEMINI_API_KEY" ]; then
        cat >> "$CONFIG" <<EOF
  ai:
    gemini_api_key: "${GEMINI_API_KEY}"
    model: "${GEMINI_MODEL:-gemini-2.0-flash}"
EOF
    fi

    echo ">>> Config written to $CONFIG"
}

# ─── Mode: sync ───
if [ "$1" = "sync" ]; then
    generate_config
    echo "=== Syncing from Strava API ==="
    activities-viewer sync --config "$CONFIG" --no-launch ${SYNC_FULL:+--full}
    echo "=== Sync complete ==="
    exit 0
fi

# ─── Mode: viewer only ───
if [ "$1" = "viewer" ]; then
    generate_config
    echo "=== Starting Activities Viewer (no sync) ==="
    activities-viewer sync --config "$CONFIG" --no-launch --skip-fetch --skip-analyze 2>/dev/null || true
    activities-viewer run --config "$CONFIG" --port 8501
    exit 0
fi

# ─── Mode: shell (debug) ───
if [ "$1" = "shell" ]; then
    exec /bin/bash
fi

# ─── Default mode: sync on first run, then launch viewer ───
generate_config

# First-run sync (if no enriched data exists yet)
if [ ! -f "$DATA_DIR/activities_raw.csv" ]; then
    echo "=== First run: fetching and analyzing all activities ==="
    activities-viewer sync --config "$CONFIG" --no-launch --full || {
        echo "WARNING: Initial sync failed. Launching viewer anyway..."
    }
fi

echo "=== Starting Activities Viewer ==="
activities-viewer sync --config "$CONFIG" --launch --port 8501
