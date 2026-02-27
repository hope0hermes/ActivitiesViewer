"""
Settings Editor — edit athlete & analyzer configuration from the UI.

Reads the current YAML configuration file, presents editable fields for
athlete parameters (FTP, weight, max HR, CP, W', goals, training plan),
and writes changes back to the same YAML file so they persist across
sessions and sync runs.
"""

import os
from pathlib import Path

import streamlit as st
import yaml

from activities_viewer.config import Settings

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="centered")


# ─── Helpers ──────────────────────────────────────────────────────────────


def _resolve_config_path() -> Path | None:
    """Return the path to the active YAML config file, or *None*."""
    # 1. Unified config (CLI-launched mode)
    unified = os.environ.get("ACTIVITIES_VIEWER_UNIFIED_CONFIG")
    if unified and Path(unified).exists():
        return Path(unified)

    # 2. Stored during app startup
    stored = st.session_state.get("config_file_path")
    if stored and Path(stored).exists():
        return Path(stored)

    # 3. Fallback: config.yaml in current directory
    fallback = Path("config.yaml")
    if fallback.exists():
        return fallback.resolve()

    return None


def _load_yaml(path: Path) -> dict:
    """Load raw YAML dict from *path*."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _save_yaml(path: Path, data: dict) -> None:
    """Write *data* back to *path* preserving readable formatting."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ─── Main ─────────────────────────────────────────────────────────────────


def main():
    settings: Settings | None = st.session_state.get("settings")
    if settings is None:
        st.error("Settings not loaded. Please start ActivitiesViewer with a config file.")
        st.stop()

    st.title("⚙️ Settings")

    config_path = _resolve_config_path()
    if config_path is None:
        st.error(
            "Cannot locate the YAML configuration file. "
            "Make sure you launched ActivitiesViewer with `--config`."
        )
        st.stop()

    st.caption(f"Configuration file: `{config_path}`")

    # Load the raw YAML so we can update individual keys without losing
    # comments structure (we do lose comments with yaml.dump, but keys stay).
    raw = _load_yaml(config_path)

    # Detect whether this is a unified config (has top-level 'athlete:' key)
    is_unified = "athlete" in raw
    athlete_section = raw.get("athlete", {}) if is_unified else raw

    # ── Athlete Parameters ────────────────────────────────────────────
    st.header("🏋️ Athlete Parameters")

    col1, col2 = st.columns(2)

    with col1:
        ftp = st.number_input(
            "FTP (watts)",
            min_value=50.0,
            max_value=600.0,
            value=float(athlete_section.get("ftp", settings.ftp)),
            step=1.0,
            help="Functional Threshold Power — your best sustainable 1-hour power.",
        )

        rider_weight_kg = st.number_input(
            "Weight (kg)",
            min_value=30.0,
            max_value=200.0,
            value=float(athlete_section.get("rider_weight_kg", athlete_section.get("weight_kg", settings.rider_weight_kg))),
            step=0.1,
            format="%.1f",
            help="Athlete body weight in kilograms.",
        )

        max_hr = st.number_input(
            "Max HR (bpm)",
            min_value=100,
            max_value=230,
            value=int(athlete_section.get("max_hr", settings.max_hr)),
            step=1,
            help="Maximum heart rate in beats per minute.",
        )

    with col2:
        cp = st.number_input(
            "Critical Power (watts)",
            min_value=0.0,
            max_value=600.0,
            value=float(athlete_section.get("cp", settings.cp)),
            step=1.0,
            help="Critical Power — typically 85–90% of FTP. Set to 0 to disable.",
        )

        w_prime = st.number_input(
            "W' (joules)",
            min_value=0.0,
            max_value=50000.0,
            value=float(athlete_section.get("w_prime", settings.w_prime)),
            step=100.0,
            help="W-prime (anaerobic capacity above CP). Typical range: 15,000–30,000 J. Set 0 to disable.",
        )

    st.markdown("---")

    # ── Goal Tracking ─────────────────────────────────────────────────
    st.header("🎯 Goal Tracking")

    col1, col2 = st.columns(2)

    with col1:
        target_wkg = st.number_input(
            "Target W/kg",
            min_value=0.0,
            max_value=10.0,
            value=float(athlete_section.get("target_wkg", settings.target_wkg or 0.0)),
            step=0.1,
            format="%.1f",
            help="Your target watts-per-kilogram goal. Set 0 to disable.",
        )

        baseline_ftp = st.number_input(
            "Baseline FTP (watts)",
            min_value=0.0,
            max_value=600.0,
            value=float(athlete_section.get("baseline_ftp", settings.baseline_ftp or 0.0)),
            step=1.0,
            help="Your FTP when you set the goal (for progress tracking). Set 0 to disable.",
        )

    with col2:
        target_date = st.text_input(
            "Target Date (YYYY-MM-DD)",
            value=str(athlete_section.get("target_date", settings.target_date or "")),
            help="Date by which you want to reach your target W/kg.",
        )

        baseline_date = st.text_input(
            "Baseline Date (YYYY-MM-DD)",
            value=str(athlete_section.get("baseline_date", settings.baseline_date or "")),
            help="Date when you started tracking toward your goal.",
        )

    st.markdown("---")

    # ── Training Plan Settings ────────────────────────────────────────
    st.header("📅 Training Plan")

    col1, col2 = st.columns(2)

    with col1:
        weekly_hours = st.number_input(
            "Weekly Hours Available",
            min_value=1.0,
            max_value=40.0,
            value=float(athlete_section.get("weekly_hours_available", settings.weekly_hours_available)),
            step=0.5,
            help="How many hours per week you have available for training.",
        )

    with col2:
        training_phase = st.selectbox(
            "Current Training Phase",
            ["base", "build", "specialty", "taper"],
            index=["base", "build", "specialty", "taper"].index(
                athlete_section.get("training_phase", settings.training_phase)
            ),
            help="Your current training phase.",
        )

    st.markdown("---")

    # ── Analyzer Settings (if unified config) ─────────────────────────
    analyzer_section = raw.get("analyzer", {}) if is_unified else {}

    if is_unified:
        st.header("📊 Analyzer Settings")
        st.caption("These settings control the StravaAnalyzer enrichment pipeline.")

        col1, col2 = st.columns(2)
        with col1:
            ctl_days = st.number_input(
                "CTL Time Constant (days)",
                min_value=7,
                max_value=120,
                value=int(analyzer_section.get("ctl_days", 42)),
                step=1,
                help="Chronic Training Load exponential decay constant (default 42).",
            )
            atl_days = st.number_input(
                "ATL Time Constant (days)",
                min_value=3,
                max_value=30,
                value=int(analyzer_section.get("atl_days", 7)),
                step=1,
                help="Acute Training Load exponential decay constant (default 7).",
            )
        with col2:
            cp_window_days = st.number_input(
                "CP Window (days)",
                min_value=30,
                max_value=365,
                value=int(analyzer_section.get("cp_window_days", 90)),
                step=1,
                help="Rolling window (in days) for Critical Power model fitting.",
            )

        st.markdown("---")

    # ── Save Button ───────────────────────────────────────────────────
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        # Build updated values
        athlete_updates: dict = {
            "ftp": ftp,
            "rider_weight_kg": rider_weight_kg,
            "max_hr": max_hr,
            "cp": cp,
            "w_prime": w_prime,
            "weekly_hours_available": weekly_hours,
            "training_phase": training_phase,
        }

        # Goal tracking — only write non-empty / non-zero values
        if target_wkg and target_wkg > 0:
            athlete_updates["target_wkg"] = target_wkg
        else:
            athlete_updates.pop("target_wkg", None)
            # Also remove from yaml if previously set
            if is_unified:
                raw.get("athlete", {}).pop("target_wkg", None)
            else:
                raw.pop("target_wkg", None)

        if target_date and target_date.strip():
            athlete_updates["target_date"] = target_date.strip()
        else:
            if is_unified:
                raw.get("athlete", {}).pop("target_date", None)
            else:
                raw.pop("target_date", None)

        if baseline_ftp and baseline_ftp > 0:
            athlete_updates["baseline_ftp"] = baseline_ftp
        else:
            if is_unified:
                raw.get("athlete", {}).pop("baseline_ftp", None)
            else:
                raw.pop("baseline_ftp", None)

        if baseline_date and baseline_date.strip():
            athlete_updates["baseline_date"] = baseline_date.strip()
        else:
            if is_unified:
                raw.get("athlete", {}).pop("baseline_date", None)
            else:
                raw.pop("baseline_date", None)

        # Write to YAML
        if is_unified:
            if "athlete" not in raw:
                raw["athlete"] = {}
            raw["athlete"].update(athlete_updates)
            # Analyzer settings
            if "analyzer" not in raw:
                raw["analyzer"] = {}
            raw["analyzer"]["ctl_days"] = ctl_days
            raw["analyzer"]["atl_days"] = atl_days
            raw["analyzer"]["cp_window_days"] = cp_window_days
        else:
            raw.update(athlete_updates)

        try:
            _save_yaml(config_path, raw)

            # Update in-memory Settings so changes take effect immediately
            settings.ftp = ftp
            settings.rider_weight_kg = rider_weight_kg
            settings.max_hr = max_hr
            settings.cp = cp
            settings.w_prime = w_prime
            settings.weekly_hours_available = weekly_hours
            settings.training_phase = training_phase
            if target_wkg and target_wkg > 0:
                settings.target_wkg = target_wkg
            else:
                settings.target_wkg = None
            settings.target_date = target_date.strip() if target_date and target_date.strip() else None
            settings.baseline_ftp = baseline_ftp if baseline_ftp and baseline_ftp > 0 else None
            settings.baseline_date = baseline_date.strip() if baseline_date and baseline_date.strip() else None

            st.session_state.settings = settings

            st.success(f"✅ Settings saved to {config_path.name}")
            st.info(
                "ℹ️ Athlete parameters (FTP, weight, max HR) will be used on the next "
                "sync/analyze run. The dashboard already reflects the updated values."
            )
        except Exception as e:
            st.error(f"Failed to save settings: {e}")

    # ── Current Settings Summary ──────────────────────────────────────
    with st.expander("📋 Current Settings (read-only)"):
        st.json(settings.to_dict_for_display())


if __name__ == "__main__":
    main()
else:
    main()
