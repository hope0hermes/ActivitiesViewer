"""
Sync button component for the Streamlit sidebar.

Provides a "🔄 Sync Data" button that runs the StravaFetcher → StravaAnalyzer
pipeline as a subprocess. Shows progress via spinner and log output.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)

# Directory for storing sync metadata (last_synced_at, etc.)
_SYNC_META_DIR = Path.home() / ".activitiesviewer"
_SYNC_META_FILE = _SYNC_META_DIR / "sync_meta.json"


def _load_sync_meta() -> dict[str, Any]:
    """Load sync metadata from disk."""
    if _SYNC_META_FILE.exists():
        try:
            return json.loads(_SYNC_META_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_sync_meta(meta: dict[str, Any]) -> None:
    """Save sync metadata to disk."""
    _SYNC_META_DIR.mkdir(parents=True, exist_ok=True)
    _SYNC_META_FILE.write_text(json.dumps(meta, indent=2))


def _get_last_synced() -> str | None:
    """Get the last sync timestamp as a human-readable string."""
    meta = _load_sync_meta()
    return meta.get("last_synced_at")


def _run_sync_pipeline(
    unified_config_path: str | None = None,
    *,
    full: bool = False,
) -> tuple[bool, str]:
    """Run the fetch + analyze pipeline.

    If a unified config path is available (stored in env/session), uses it.
    Otherwise, runs a basic pipeline using the current settings.

    Args:
        unified_config_path: Path to unified config YAML (if available).
        full: Whether to pass --full to force complete re-fetch.

    Returns:
        Tuple of (success: bool, output: str).
    """
    cmd = [sys.executable, "-m", "activities_viewer", "sync"]

    if unified_config_path:
        cmd.extend(["--config", unified_config_path, "--no-launch"])
        if full:
            cmd.append("--full")
    else:
        # If no unified config, we can't run the pipeline
        return False, (
            "No unified config available. The sync button requires a unified "
            "pipeline config. Run with:\n\n"
            "  activities-viewer sync --config unified_config.yaml"
        )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,  # 10 minute timeout
        )

        output = result.stdout or ""
        if result.stderr:
            output += "\n" + result.stderr

        if result.returncode == 0:
            _save_sync_meta({
                "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            return True, output
        else:
            return False, output

    except subprocess.TimeoutExpired:
        return False, "Sync timed out after 10 minutes."
    except Exception as e:
        return False, f"Failed to run sync: {e}"


def render_sync_button() -> None:
    """Render the sync button in the sidebar.

    Shows:
    - Last sync timestamp (if available)
    - "🔄 Sync Data" button
    - Progress spinner during sync
    - Success/failure message after sync
    """
    # Check if unified config is available
    unified_config_path = os.environ.get("ACTIVITIES_VIEWER_UNIFIED_CONFIG")

    with st.expander("🔄 Data Sync", expanded=False):
        # Show last synced timestamp
        last_synced = _get_last_synced()
        if last_synced:
            st.caption(f"Last synced: {last_synced}")
        else:
            st.caption("Never synced from this app")

        if not unified_config_path:
            st.info(
                "💡 To enable in-app sync, launch with a unified config:\n\n"
                "```\n"
                "activities-viewer sync --config unified_config.yaml\n"
                "```"
            )
            return

        # Sync controls
        col1, col2 = st.columns([2, 1])
        with col1:
            sync_clicked = st.button("🔄 Sync Data", use_container_width=True)
        with col2:
            full_sync = st.checkbox("Full", help="Force complete re-fetch")

        if sync_clicked:
            with st.spinner("Syncing data from Strava..."):
                success, output = _run_sync_pipeline(
                    unified_config_path,
                    full=full_sync,
                )

            if success:
                st.success("✅ Sync complete!")
                if output:
                    with st.expander("Sync log", expanded=False):
                        st.code(output, language="text")
                # Trigger a rerun to reload data
                st.rerun()
            else:
                st.error("❌ Sync failed")
                if output:
                    st.code(output, language="text")
