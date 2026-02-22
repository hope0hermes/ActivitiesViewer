"""
Sync button component for the Streamlit sidebar.

Provides a "🔄 Sync Data" button that calls the PipelineOrchestrator
directly via StravaFetcher/StravaAnalyzer Python APIs. Shows progress
via spinner and log output.
"""

import json
import logging
import os
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
    """Run the fetch + analyze pipeline via direct library calls.

    Args:
        unified_config_path: Path to unified config YAML (if available).
        full: Whether to force a complete re-fetch.

    Returns:
        Tuple of (success: bool, output: str).
    """
    if not unified_config_path:
        return False, (
            "No unified config available. The sync button requires a unified "
            "pipeline config. Run with:\n\n"
            "  activities-viewer sync --config unified_config.yaml"
        )

    try:
        from activities_viewer.pipeline import PipelineOrchestrator, load_unified_config

        config_path = Path(unified_config_path)
        unified = load_unified_config(config_path)
        orchestrator = PipelineOrchestrator(unified, config_path.parent)

        orchestrator.run_sync(full=full)

        _save_sync_meta(
            {
                "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return True, "Pipeline sync completed successfully."

    except FileNotFoundError as e:
        return False, f"Config not found: {e}"
    except ImportError as e:
        return False, f"Missing dependency: {e}"
    except Exception as e:
        return False, f"Sync failed: {e}"


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
