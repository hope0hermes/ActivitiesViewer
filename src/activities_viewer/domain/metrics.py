"""
Centralized metric definitions and registry for ActivitiesViewer.

This module provides a single source of truth for all metrics displayed
in the application, ensuring consistency across the UI.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Any
from enum import Enum
import pandas as pd
from datetime import datetime


class MetricCategory(str, Enum):
    """Categories for organizing metrics in the UI."""

    HERO = "hero"  # Top-level metrics (FTP, W/kg, TSS)
    LOAD = "load"  # Volume and training load metrics
    INTENSITY = "intensity"  # Intensity-based metrics (IF, TID, zones)
    PHYSIOLOGY = "physiology"  # Efficiency, HR, decoupling
    POWER = "power"  # Power-specific metrics (curves, peaks)
    STATUS = "status"  # Training status (CTL, ATL, TSB)
    GENERAL = "general"  # Basic metrics (distance, time, speed)
    EQUIPMENT = "equipment"  # Gear-related metrics
    METADATA = "metadata"  # Activity metadata (name, date, type)


@dataclass
class MetricDefinition:
    """
    Defines properties of a single metric.

    Attributes:
        id: Column name in the CSV file
        label: Human-readable display name
        unit: Unit of measurement (e.g., "W", "km", "%")
        help_text: Tooltip/explanation for the metric
        format_func: Function to format the value for display
        category: Metric category for UI organization
    """

    id: str
    label: str
    unit: str
    help_text: str
    format_func: Callable[[Any], str]
    category: MetricCategory


# ═══════════════════════════════════════════════════════════════════════════
# FORMATTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def _format_none_safe(value: Any, formatter: Callable[[Any], str]) -> str:
    """Wrapper to handle None/NaN values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    return formatter(value)


def _fmt_int(value: Any) -> str:
    """Format as integer."""
    return _format_none_safe(value, lambda v: f"{int(v)}")


def _fmt_float_1(value: Any) -> str:
    """Format float with 1 decimal."""
    return _format_none_safe(value, lambda v: f"{float(v):.1f}")


def _fmt_float_2(value: Any) -> str:
    """Format float with 2 decimals."""
    return _format_none_safe(value, lambda v: f"{float(v):.2f}")


def _fmt_watts(value: Any) -> str:
    """Format power in watts."""
    return _format_none_safe(value, lambda v: f"{int(v)} W")


def _fmt_wkg(value: Any) -> str:
    """Format power per kilogram."""
    return _format_none_safe(value, lambda v: f"{float(v):.2f} W/kg")


def _fmt_duration_hm(value: Any) -> str:
    """Format duration in seconds as h:mm."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}"
    return f"{minutes}m"


def _fmt_duration_hours(value: Any) -> str:
    """Format duration in seconds as decimal hours."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    return f"{value / 3600:.1f}h"


def _fmt_distance_km(value: Any) -> str:
    """Format distance in meters as kilometers."""
    return _format_none_safe(value, lambda v: f"{v / 1000:.1f} km")


def _fmt_distance_m(value: Any) -> str:
    """Format distance in meters."""
    return _format_none_safe(value, lambda v: f"{int(v)} m")


def _fmt_speed_kph(value: Any) -> str:
    """Format speed in m/s as km/h."""
    return _format_none_safe(value, lambda v: f"{v * 3.6:.1f} km/h")


def _fmt_percentage(value: Any) -> str:
    """Format as percentage."""
    return _format_none_safe(value, lambda v: f"{float(v):.1f}%")


def _fmt_percentage_2(value: Any) -> str:
    """Format as percentage with 2 decimals."""
    return _format_none_safe(value, lambda v: f"{float(v):.2f}%")


def _fmt_bpm(value: Any) -> str:
    """Format heart rate in BPM."""
    return _format_none_safe(value, lambda v: f"{int(v)} bpm")


def _fmt_cadence(value: Any) -> str:
    """Format cadence in RPM."""
    return _format_none_safe(value, lambda v: f"{int(v)} rpm")


def _fmt_temperature(value: Any) -> str:
    """Format temperature in Celsius."""
    return _format_none_safe(value, lambda v: f"{int(v)}°C")


def _fmt_date(value: Any) -> str:
    """Format date."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value
    return "-"


def _fmt_datetime(value: Any) -> str:
    """Format datetime."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, str):
        return value
    return "-"


def _fmt_string(value: Any) -> str:
    """Format as string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    return str(value)


def _fmt_boolean(value: Any) -> str:
    """Format boolean value."""
    if value is None:
        return "-"
    return "Yes" if value else "No"


def _fmt_kj(value: Any) -> str:
    """Format kilojoules."""
    return _format_none_safe(value, lambda v: f"{int(v)} kJ")


def _fmt_vam(value: Any) -> str:
    """Format VAM (Vertical Ascent in Meters per hour)."""
    return _format_none_safe(value, lambda v: f"{int(v)} m/h")


def _fmt_index(value: Any) -> str:
    """Format unitless index values."""
    return _format_none_safe(value, lambda v: f"{float(v):.2f}")


# ═══════════════════════════════════════════════════════════════════════════
# METRIC REGISTRY
# ═══════════════════════════════════════════════════════════════════════════


class MetricRegistry:
    """
    Centralized catalog of all metric definitions.

    This registry provides a single source of truth for all metrics
    used throughout the application.
    """

    # Hero Metrics (Top-level importance)
    ESTIMATED_FTP = MetricDefinition(
        id="estimated_ftp",
        label="Estimated FTP",
        unit="W",
        help_text="Estimated Functional Threshold Power",
        format_func=_fmt_watts,
        category=MetricCategory.HERO,
    )

    POWER_PER_KG = MetricDefinition(
        id="power_per_kg",
        label="Power/kg",
        unit="W/kg",
        help_text="Average power per kilogram of body weight",
        format_func=_fmt_wkg,
        category=MetricCategory.HERO,
    )

    TRAINING_STRESS_SCORE = MetricDefinition(
        id="training_stress_score",
        label="TSS",
        unit="TSS",
        help_text="Training Stress Score - measure of training load",
        format_func=_fmt_int,
        category=MetricCategory.HERO,
    )

    NORMALIZED_POWER = MetricDefinition(
        id="normalized_power",
        label="Normalized Power",
        unit="W",
        help_text="Power normalized for variability (similar to average perceived effort)",
        format_func=_fmt_watts,
        category=MetricCategory.HERO,
    )

    INTENSITY_FACTOR = MetricDefinition(
        id="intensity_factor",
        label="Intensity Factor",
        unit="IF",
        help_text="Ratio of Normalized Power to FTP (training intensity)",
        format_func=_fmt_float_2,
        category=MetricCategory.HERO,
    )

    # Load Metrics
    MOVING_TIME = MetricDefinition(
        id="moving_time",
        label="Moving Time",
        unit="h:mm",
        help_text="Time spent moving (excludes stops)",
        format_func=_fmt_duration_hm,
        category=MetricCategory.LOAD,
    )

    ELAPSED_TIME = MetricDefinition(
        id="elapsed_time",
        label="Elapsed Time",
        unit="h:mm",
        help_text="Total elapsed time including stops",
        format_func=_fmt_duration_hm,
        category=MetricCategory.LOAD,
    )

    DISTANCE = MetricDefinition(
        id="distance",
        label="Distance",
        unit="km",
        help_text="Total distance covered",
        format_func=_fmt_distance_km,
        category=MetricCategory.LOAD,
    )

    TOTAL_ELEVATION_GAIN = MetricDefinition(
        id="total_elevation_gain",
        label="Elevation Gain",
        unit="m",
        help_text="Total elevation gained during the activity",
        format_func=_fmt_distance_m,
        category=MetricCategory.LOAD,
    )

    KILOJOULES = MetricDefinition(
        id="kilojoules",
        label="Work",
        unit="kJ",
        help_text="Total mechanical work performed",
        format_func=_fmt_kj,
        category=MetricCategory.LOAD,
    )

    HR_TRAINING_STRESS = MetricDefinition(
        id="hr_training_stress",
        label="HRSS",
        unit="HRSS",
        help_text="Heart Rate-based Training Stress Score",
        format_func=_fmt_int,
        category=MetricCategory.LOAD,
    )

    # Intensity Metrics
    AVERAGE_WATTS = MetricDefinition(
        id="average_watts",
        label="Avg Power",
        unit="W",
        help_text="Average power output",
        format_func=_fmt_watts,
        category=MetricCategory.INTENSITY,
    )

    MAX_WATTS = MetricDefinition(
        id="max_watts",
        label="Max Power",
        unit="W",
        help_text="Maximum power output",
        format_func=_fmt_watts,
        category=MetricCategory.INTENSITY,
    )

    WEIGHTED_AVERAGE_WATTS = MetricDefinition(
        id="weighted_average_watts",
        label="Weighted Avg Power",
        unit="W",
        help_text="Power weighted by intensity (from Strava)",
        format_func=_fmt_watts,
        category=MetricCategory.INTENSITY,
    )

    VARIABILITY_INDEX = MetricDefinition(
        id="variability_index",
        label="VI",
        unit="VI",
        help_text="Normalized Power / Average Power (measures pacing consistency)",
        format_func=_fmt_float_2,
        category=MetricCategory.INTENSITY,
    )

    TIME_ABOVE_90_FTP = MetricDefinition(
        id="time_above_90_ftp",
        label="Time >90% FTP",
        unit="s",
        help_text="Time spent above 90% of FTP",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    TIME_SWEET_SPOT = MetricDefinition(
        id="time_sweet_spot",
        label="Sweet Spot Time",
        unit="s",
        help_text="Time in sweet spot range (88-93% FTP)",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    # Training Intensity Distribution (TID) - Power
    POWER_TID_Z1_PERCENTAGE = MetricDefinition(
        id="power_tid_z1_percentage",
        label="TID Z1 (Power)",
        unit="%",
        help_text="Percentage of time in Zone 1 (<55% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_TID_Z2_PERCENTAGE = MetricDefinition(
        id="power_tid_z2_percentage",
        label="TID Z2 (Power)",
        unit="%",
        help_text="Percentage of time in Zone 2 (55-90% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_TID_Z3_PERCENTAGE = MetricDefinition(
        id="power_tid_z3_percentage",
        label="TID Z3 (Power)",
        unit="%",
        help_text="Percentage of time in Zone 3 (>90% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_POLARIZATION_INDEX = MetricDefinition(
        id="power_polarization_index",
        label="Polarization Index",
        unit="PI",
        help_text="Measure of training polarization (high = more polarized)",
        format_func=_fmt_float_2,
        category=MetricCategory.INTENSITY,
    )

    POWER_TDR = MetricDefinition(
        id="power_tdr",
        label="TDR (Power)",
        unit="TDR",
        help_text="Threshold Duration Ratio",
        format_func=_fmt_float_2,
        category=MetricCategory.INTENSITY,
    )

    # Power Zones (7-zone model)
    POWER_Z1_PERCENTAGE = MetricDefinition(
        id="power_z1_percentage",
        label="Z1 %",
        unit="%",
        help_text="Active Recovery (<55% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z2_PERCENTAGE = MetricDefinition(
        id="power_z2_percentage",
        label="Z2 %",
        unit="%",
        help_text="Endurance (55-75% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z3_PERCENTAGE = MetricDefinition(
        id="power_z3_percentage",
        label="Z3 %",
        unit="%",
        help_text="Tempo (75-90% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z4_PERCENTAGE = MetricDefinition(
        id="power_z4_percentage",
        label="Z4 %",
        unit="%",
        help_text="Lactate Threshold (90-105% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z5_PERCENTAGE = MetricDefinition(
        id="power_z5_percentage",
        label="Z5 %",
        unit="%",
        help_text="VO2 Max (105-120% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z6_PERCENTAGE = MetricDefinition(
        id="power_z6_percentage",
        label="Z6 %",
        unit="%",
        help_text="Anaerobic Capacity (>120% FTP)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    POWER_Z7_PERCENTAGE = MetricDefinition(
        id="power_z7_percentage",
        label="Z7 %",
        unit="%",
        help_text="Neuromuscular Power (Sprint)",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    # Heart Rate Zones
    HR_Z1_PERCENTAGE = MetricDefinition(
        id="hr_z1_percentage",
        label="HR Z1 %",
        unit="%",
        help_text="Heart Rate Zone 1 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_Z2_PERCENTAGE = MetricDefinition(
        id="hr_z2_percentage",
        label="HR Z2 %",
        unit="%",
        help_text="Heart Rate Zone 2 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_Z3_PERCENTAGE = MetricDefinition(
        id="hr_z3_percentage",
        label="HR Z3 %",
        unit="%",
        help_text="Heart Rate Zone 3 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_Z4_PERCENTAGE = MetricDefinition(
        id="hr_z4_percentage",
        label="HR Z4 %",
        unit="%",
        help_text="Heart Rate Zone 4 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_Z5_PERCENTAGE = MetricDefinition(
        id="hr_z5_percentage",
        label="HR Z5 %",
        unit="%",
        help_text="Heart Rate Zone 5 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    # Physiology Metrics
    EFFICIENCY_FACTOR = MetricDefinition(
        id="efficiency_factor",
        label="Efficiency Factor",
        unit="EF",
        help_text="Normalized Power / Average HR (higher = more efficient)",
        format_func=_fmt_float_2,
        category=MetricCategory.PHYSIOLOGY,
    )

    POWER_HR_DECOUPLING = MetricDefinition(
        id="power_hr_decoupling",
        label="Pw:HR Decoupling",
        unit="%",
        help_text="Power/HR drift between first and second half (< 5% = good endurance)",
        format_func=_fmt_percentage,
        category=MetricCategory.PHYSIOLOGY,
    )

    CARDIAC_DRIFT = MetricDefinition(
        id="cardiac_drift",
        label="Cardiac Drift",
        unit="%",
        help_text="Heart rate drift during steady effort",
        format_func=_fmt_percentage,
        category=MetricCategory.PHYSIOLOGY,
    )

    AVERAGE_HEARTRATE = MetricDefinition(
        id="average_heartrate",
        label="Avg HR",
        unit="bpm",
        help_text="Average heart rate",
        format_func=_fmt_bpm,
        category=MetricCategory.PHYSIOLOGY,
    )

    MAX_HEARTRATE = MetricDefinition(
        id="max_heartrate",
        label="Max HR",
        unit="bpm",
        help_text="Maximum heart rate",
        format_func=_fmt_bpm,
        category=MetricCategory.PHYSIOLOGY,
    )

    AVERAGE_HR = MetricDefinition(
        id="average_hr",
        label="Avg HR",
        unit="bpm",
        help_text="Average heart rate (enriched)",
        format_func=_fmt_bpm,
        category=MetricCategory.PHYSIOLOGY,
    )

    MAX_HR = MetricDefinition(
        id="max_hr",
        label="Max HR",
        unit="bpm",
        help_text="Maximum heart rate (enriched)",
        format_func=_fmt_bpm,
        category=MetricCategory.PHYSIOLOGY,
    )

    FIRST_HALF_EF = MetricDefinition(
        id="first_half_ef",
        label="1st Half EF",
        unit="EF",
        help_text="Efficiency factor in first half",
        format_func=_fmt_float_2,
        category=MetricCategory.PHYSIOLOGY,
    )

    SECOND_HALF_EF = MetricDefinition(
        id="second_half_ef",
        label="2nd Half EF",
        unit="EF",
        help_text="Efficiency factor in second half",
        format_func=_fmt_float_2,
        category=MetricCategory.PHYSIOLOGY,
    )

    # Power Profile & Curves
    POWER_CURVE_1SEC = MetricDefinition(
        id="power_curve_1sec",
        label="1s Peak",
        unit="W",
        help_text="Maximum 1-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_2SEC = MetricDefinition(
        id="power_curve_2sec",
        label="2s Peak",
        unit="W",
        help_text="Maximum 2-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_5SEC = MetricDefinition(
        id="power_curve_5sec",
        label="5s Peak",
        unit="W",
        help_text="Maximum 5-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_10SEC = MetricDefinition(
        id="power_curve_10sec",
        label="10s Peak",
        unit="W",
        help_text="Maximum 10-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_15SEC = MetricDefinition(
        id="power_curve_15sec",
        label="15s Peak",
        unit="W",
        help_text="Maximum 15-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_20SEC = MetricDefinition(
        id="power_curve_20sec",
        label="20s Peak",
        unit="W",
        help_text="Maximum 20-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_30SEC = MetricDefinition(
        id="power_curve_30sec",
        label="30s Peak",
        unit="W",
        help_text="Maximum 30-second power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_1MIN = MetricDefinition(
        id="power_curve_1min",
        label="1min Peak",
        unit="W",
        help_text="Maximum 1-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_2MIN = MetricDefinition(
        id="power_curve_2min",
        label="2min Peak",
        unit="W",
        help_text="Maximum 2-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_5MIN = MetricDefinition(
        id="power_curve_5min",
        label="5min Peak",
        unit="W",
        help_text="Maximum 5-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_10MIN = MetricDefinition(
        id="power_curve_10min",
        label="10min Peak",
        unit="W",
        help_text="Maximum 10-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_15MIN = MetricDefinition(
        id="power_curve_15min",
        label="15min Peak",
        unit="W",
        help_text="Maximum 15-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_20MIN = MetricDefinition(
        id="power_curve_20min",
        label="20min Peak",
        unit="W",
        help_text="Maximum 20-minute power (FTP estimate base)",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_30MIN = MetricDefinition(
        id="power_curve_30min",
        label="30min Peak",
        unit="W",
        help_text="Maximum 30-minute power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_CURVE_1HR = MetricDefinition(
        id="power_curve_1hr",
        label="1hr Peak",
        unit="W",
        help_text="Maximum 1-hour power",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    W_PRIME_BALANCE_MIN = MetricDefinition(
        id="w_prime_balance_min",
        label="W' Balance Min",
        unit="kJ",
        help_text="Minimum W' (anaerobic capacity) balance",
        format_func=_fmt_kj,
        category=MetricCategory.POWER,
    )

    MATCH_BURN_COUNT = MetricDefinition(
        id="match_burn_count",
        label="Matches Burned",
        unit="count",
        help_text="Number of hard efforts (matches) burned",
        format_func=_fmt_int,
        category=MetricCategory.POWER,
    )

    FATIGUE_INDEX = MetricDefinition(
        id="fatigue_index",
        label="Fatigue Index",
        unit="%",
        help_text="Power drop-off during the activity",
        format_func=_fmt_percentage,
        category=MetricCategory.POWER,
    )

    POWER_SUSTAINABILITY_INDEX = MetricDefinition(
        id="power_sustainability_index",
        label="Sustainability Index",
        unit="PSI",
        help_text="How well power was sustained",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    # Climbing Metrics
    VAM = MetricDefinition(
        id="vam",
        label="VAM",
        unit="m/h",
        help_text="Vertical Ascent in Meters per hour",
        format_func=_fmt_vam,
        category=MetricCategory.POWER,
    )

    CLIMBING_TIME = MetricDefinition(
        id="climbing_time",
        label="Climbing Time",
        unit="s",
        help_text="Time spent climbing",
        format_func=_fmt_duration_hm,
        category=MetricCategory.POWER,
    )

    CLIMBING_POWER = MetricDefinition(
        id="climbing_power",
        label="Climbing Power",
        unit="W",
        help_text="Average power while climbing",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    CLIMBING_POWER_PER_KG = MetricDefinition(
        id="climbing_power_per_kg",
        label="Climbing W/kg",
        unit="W/kg",
        help_text="Power per kg while climbing",
        format_func=_fmt_wkg,
        category=MetricCategory.POWER,
    )

    # Training Status (PMC)
    CHRONIC_TRAINING_LOAD = MetricDefinition(
        id="chronic_training_load",
        label="CTL (Fitness)",
        unit="TSS",
        help_text="Chronic Training Load - 42-day weighted average (Fitness)",
        format_func=_fmt_int,
        category=MetricCategory.STATUS,
    )

    ACUTE_TRAINING_LOAD = MetricDefinition(
        id="acute_training_load",
        label="ATL (Fatigue)",
        unit="TSS",
        help_text="Acute Training Load - 7-day weighted average (Fatigue)",
        format_func=_fmt_int,
        category=MetricCategory.STATUS,
    )

    TRAINING_STRESS_BALANCE = MetricDefinition(
        id="training_stress_balance",
        label="TSB (Form)",
        unit="TSS",
        help_text="Training Stress Balance - CTL minus ATL (Form)",
        format_func=_fmt_int,
        category=MetricCategory.STATUS,
    )

    ACWR = MetricDefinition(
        id="acwr",
        label="ACWR",
        unit="ratio",
        help_text="Acute:Chronic Workload Ratio (injury risk indicator)",
        format_func=_fmt_float_2,
        category=MetricCategory.STATUS,
    )

    # Critical Power Model
    CP = MetricDefinition(
        id="cp",
        label="Critical Power",
        unit="W",
        help_text="Critical Power (theoretical sustainable power)",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    W_PRIME = MetricDefinition(
        id="w_prime",
        label="W'",
        unit="kJ",
        help_text="Anaerobic Work Capacity (W prime)",
        format_func=_fmt_kj,
        category=MetricCategory.POWER,
    )

    CP_R_SQUARED = MetricDefinition(
        id="cp_r_squared",
        label="CP R²",
        unit="R²",
        help_text="Critical Power model fit quality",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    AEI = MetricDefinition(
        id="aei",
        label="AEI",
        unit="AEI",
        help_text="Aerobic Endurance Index",
        format_func=_fmt_float_2,
        category=MetricCategory.PHYSIOLOGY,
    )

    # General Metrics
    AVERAGE_SPEED = MetricDefinition(
        id="average_speed",
        label="Avg Speed",
        unit="km/h",
        help_text="Average speed",
        format_func=_fmt_speed_kph,
        category=MetricCategory.GENERAL,
    )

    MAX_SPEED = MetricDefinition(
        id="max_speed",
        label="Max Speed",
        unit="km/h",
        help_text="Maximum speed",
        format_func=_fmt_speed_kph,
        category=MetricCategory.GENERAL,
    )

    AVERAGE_CADENCE = MetricDefinition(
        id="average_cadence",
        label="Avg Cadence",
        unit="rpm",
        help_text="Average cadence",
        format_func=_fmt_cadence,
        category=MetricCategory.GENERAL,
    )

    MAX_CADENCE = MetricDefinition(
        id="max_cadence",
        label="Max Cadence",
        unit="rpm",
        help_text="Maximum cadence",
        format_func=_fmt_cadence,
        category=MetricCategory.GENERAL,
    )

    AVERAGE_TEMP = MetricDefinition(
        id="average_temp",
        label="Avg Temp",
        unit="°C",
        help_text="Average temperature",
        format_func=_fmt_temperature,
        category=MetricCategory.GENERAL,
    )

    # Metadata
    NAME = MetricDefinition(
        id="name",
        label="Activity Name",
        unit="",
        help_text="Activity name",
        format_func=_fmt_string,
        category=MetricCategory.METADATA,
    )

    TYPE = MetricDefinition(
        id="type",
        label="Type",
        unit="",
        help_text="Activity type (Ride, Run, etc.)",
        format_func=_fmt_string,
        category=MetricCategory.METADATA,
    )

    SPORT_TYPE = MetricDefinition(
        id="sport_type",
        label="Sport Type",
        unit="",
        help_text="Detailed sport type",
        format_func=_fmt_string,
        category=MetricCategory.METADATA,
    )

    START_DATE = MetricDefinition(
        id="start_date",
        label="Date",
        unit="",
        help_text="Activity start date",
        format_func=_fmt_date,
        category=MetricCategory.METADATA,
    )

    START_DATE_LOCAL = MetricDefinition(
        id="start_date_local",
        label="Local Time",
        unit="",
        help_text="Activity start time (local)",
        format_func=_fmt_datetime,
        category=MetricCategory.METADATA,
    )

    WORKOUT_TYPE = MetricDefinition(
        id="workout_type",
        label="Workout Type",
        unit="",
        help_text="Strava workout type",
        format_func=_fmt_int,
        category=MetricCategory.METADATA,
    )

    # Equipment
    GEAR_ID = MetricDefinition(
        id="gear_id",
        label="Gear",
        unit="",
        help_text="Equipment used",
        format_func=_fmt_string,
        category=MetricCategory.EQUIPMENT,
    )

    TRAINER = MetricDefinition(
        id="trainer",
        label="Trainer",
        unit="",
        help_text="Indoor trainer activity",
        format_func=_fmt_boolean,
        category=MetricCategory.EQUIPMENT,
    )

    DEVICE_NAME = MetricDefinition(
        id="device_name",
        label="Device",
        unit="",
        help_text="Recording device",
        format_func=_fmt_string,
        category=MetricCategory.EQUIPMENT,
    )

    DEVICE_WATTS = MetricDefinition(
        id="device_watts",
        label="Device Power",
        unit="",
        help_text="Power from device (vs estimated)",
        format_func=_fmt_boolean,
        category=MetricCategory.EQUIPMENT,
    )

    # FTP & Threshold Settings (from enriched data)
    FTP = MetricDefinition(
        id="ftp",
        label="FTP",
        unit="W",
        help_text="Functional Threshold Power (configured)",
        format_func=_fmt_watts,
        category=MetricCategory.STATUS,
    )

    FTHR = MetricDefinition(
        id="fthr",
        label="FTHR",
        unit="bpm",
        help_text="Functional Threshold Heart Rate (configured)",
        format_func=_fmt_bpm,
        category=MetricCategory.STATUS,
    )

    LT1_POWER = MetricDefinition(
        id="lt1_power",
        label="LT1 Power",
        unit="W",
        help_text="Lactate Threshold 1 power",
        format_func=_fmt_watts,
        category=MetricCategory.STATUS,
    )

    LT2_POWER = MetricDefinition(
        id="lt2_power",
        label="LT2 Power",
        unit="W",
        help_text="Lactate Threshold 2 power",
        format_func=_fmt_watts,
        category=MetricCategory.STATUS,
    )

    LT1_HR = MetricDefinition(
        id="lt1_hr",
        label="LT1 HR",
        unit="bpm",
        help_text="Lactate Threshold 1 heart rate",
        format_func=_fmt_bpm,
        category=MetricCategory.STATUS,
    )

    LT2_HR = MetricDefinition(
        id="lt2_hr",
        label="LT2 HR",
        unit="bpm",
        help_text="Lactate Threshold 2 heart rate",
        format_func=_fmt_bpm,
        category=MetricCategory.STATUS,
    )

    # Interval Analysis
    NEGATIVE_SPLIT_INDEX = MetricDefinition(
        id="negative_split_index",
        label="Negative Split",
        unit="index",
        help_text="Negative split indicator (>1 = stronger finish)",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    INITIAL_5MIN_POWER = MetricDefinition(
        id="initial_5min_power",
        label="First 5min Power",
        unit="W",
        help_text="Average power in first 5 minutes",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    FINAL_5MIN_POWER = MetricDefinition(
        id="final_5min_power",
        label="Final 5min Power",
        unit="W",
        help_text="Average power in final 5 minutes",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    FIRST_HALF_POWER = MetricDefinition(
        id="first_half_power",
        label="1st Half Power",
        unit="W",
        help_text="Average power in first half",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    SECOND_HALF_POWER = MetricDefinition(
        id="second_half_power",
        label="2nd Half Power",
        unit="W",
        help_text="Average power in second half",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    POWER_DROP_PERCENTAGE = MetricDefinition(
        id="power_drop_percentage",
        label="Power Drop",
        unit="%",
        help_text="Power drop from first to second half",
        format_func=_fmt_percentage,
        category=MetricCategory.POWER,
    )

    HALF_POWER_RATIO = MetricDefinition(
        id="half_power_ratio",
        label="Half Power Ratio",
        unit="ratio",
        help_text="Ratio of second half to first half power",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    POWER_COEFFICIENT_VARIATION = MetricDefinition(
        id="power_coefficient_variation",
        label="Power CV",
        unit="%",
        help_text="Coefficient of variation of power (consistency)",
        format_func=_fmt_percentage,
        category=MetricCategory.POWER,
    )

    INTERVAL_300S_DECAY_RATE = MetricDefinition(
        id="interval_300s_decay_rate",
        label="5min Decay Rate",
        unit="W/min",
        help_text="Power decay rate over 5-minute intervals",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    INTERVAL_300S_POWER_TREND = MetricDefinition(
        id="interval_300s_power_trend",
        label="5min Power Trend",
        unit="W",
        help_text="Power trend over 5-minute intervals",
        format_func=_fmt_float_2,
        category=MetricCategory.POWER,
    )

    INTERVAL_300S_FIRST_POWER = MetricDefinition(
        id="interval_300s_first_power",
        label="First 5min Interval",
        unit="W",
        help_text="Power in first 5-minute interval",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    INTERVAL_300S_LAST_POWER = MetricDefinition(
        id="interval_300s_last_power",
        label="Last 5min Interval",
        unit="W",
        help_text="Power in last 5-minute interval",
        format_func=_fmt_watts,
        category=MetricCategory.POWER,
    )

    # Power Zone Time (seconds, not percentage)
    POWER_ZONE_1 = MetricDefinition(
        id="power_zone_1",
        label="Z1 Time",
        unit="s",
        help_text="Time in Power Zone 1",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    POWER_ZONE_2 = MetricDefinition(
        id="power_zone_2",
        label="Z2 Time",
        unit="s",
        help_text="Time in Power Zone 2",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    POWER_ZONE_3 = MetricDefinition(
        id="power_zone_3",
        label="Z3 Time",
        unit="s",
        help_text="Time in Power Zone 3",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    POWER_ZONE_4 = MetricDefinition(
        id="power_zone_4",
        label="Z4 Time",
        unit="s",
        help_text="Time in Power Zone 4",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    POWER_ZONE_5 = MetricDefinition(
        id="power_zone_5",
        label="Z5 Time",
        unit="s",
        help_text="Time in Power Zone 5",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    POWER_ZONE_6 = MetricDefinition(
        id="power_zone_6",
        label="Z6 Time",
        unit="s",
        help_text="Time in Power Zone 6",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    # Heart Rate Zone Time
    HR_ZONE_1 = MetricDefinition(
        id="hr_zone_1",
        label="HR Z1 Time",
        unit="s",
        help_text="Time in HR Zone 1",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    HR_ZONE_2 = MetricDefinition(
        id="hr_zone_2",
        label="HR Z2 Time",
        unit="s",
        help_text="Time in HR Zone 2",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    HR_ZONE_3 = MetricDefinition(
        id="hr_zone_3",
        label="HR Z3 Time",
        unit="s",
        help_text="Time in HR Zone 3",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    HR_ZONE_4 = MetricDefinition(
        id="hr_zone_4",
        label="HR Z4 Time",
        unit="s",
        help_text="Time in HR Zone 4",
        format_func=_fmt_duration_hm,
        category=MetricCategory.INTENSITY,
    )

    # Training Classification
    POWER_TID_CLASSIFICATION = MetricDefinition(
        id="power_tid_classification",
        label="TID Classification",
        unit="",
        help_text="Training intensity distribution classification",
        format_func=_fmt_string,
        category=MetricCategory.INTENSITY,
    )

    HR_TID_CLASSIFICATION = MetricDefinition(
        id="hr_tid_classification",
        label="HR TID Classification",
        unit="",
        help_text="Heart rate TID classification",
        format_func=_fmt_string,
        category=MetricCategory.INTENSITY,
    )

    # HR TID
    HR_TID_Z1_PERCENTAGE = MetricDefinition(
        id="hr_tid_z1_percentage",
        label="HR TID Z1 %",
        unit="%",
        help_text="Heart rate TID Zone 1 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_TID_Z2_PERCENTAGE = MetricDefinition(
        id="hr_tid_z2_percentage",
        label="HR TID Z2 %",
        unit="%",
        help_text="Heart rate TID Zone 2 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_TID_Z3_PERCENTAGE = MetricDefinition(
        id="hr_tid_z3_percentage",
        label="HR TID Z3 %",
        unit="%",
        help_text="Heart rate TID Zone 3 percentage",
        format_func=_fmt_percentage,
        category=MetricCategory.INTENSITY,
    )

    HR_POLARIZATION_INDEX = MetricDefinition(
        id="hr_polarization_index",
        label="HR Polarization",
        unit="PI",
        help_text="Heart rate polarization index",
        format_func=_fmt_float_2,
        category=MetricCategory.INTENSITY,
    )

    HR_TDR = MetricDefinition(
        id="hr_tdr",
        label="HR TDR",
        unit="TDR",
        help_text="Heart rate threshold duration ratio",
        format_func=_fmt_float_2,
        category=MetricCategory.INTENSITY,
    )

    # Additional fields
    NORMALIZED_GRADED_PACE = MetricDefinition(
        id="normalized_graded_pace",
        label="NGP",
        unit="min/km",
        help_text="Normalized Graded Pace (running)",
        format_func=_fmt_string,
        category=MetricCategory.GENERAL,
    )

    # Other power metrics
    AVERAGE_POWER = MetricDefinition(
        id="average_power",
        label="Avg Power",
        unit="W",
        help_text="Average power (enriched)",
        format_func=_fmt_watts,
        category=MetricCategory.INTENSITY,
    )

    MAX_POWER = MetricDefinition(
        id="max_power",
        label="Max Power",
        unit="W",
        help_text="Maximum power (enriched)",
        format_func=_fmt_watts,
        category=MetricCategory.INTENSITY,
    )

    TOTAL_TIME = MetricDefinition(
        id="total_time",
        label="Total Time",
        unit="h:mm",
        help_text="Total activity time",
        format_func=_fmt_duration_hm,
        category=MetricCategory.LOAD,
    )

    ELEVATION_GAIN = MetricDefinition(
        id="elevation_gain",
        label="Elevation",
        unit="m",
        help_text="Elevation gain (enriched)",
        format_func=_fmt_distance_m,
        category=MetricCategory.LOAD,
    )

    @classmethod
    def get_all_metrics(cls) -> dict[str, MetricDefinition]:
        """Get all registered metrics as a dictionary keyed by metric ID."""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if isinstance(getattr(cls, name), MetricDefinition)
        }

    @classmethod
    def get_by_id(cls, metric_id: str) -> Optional[MetricDefinition]:
        """Get a metric definition by its ID."""
        all_metrics = cls.get_all_metrics()
        return all_metrics.get(metric_id.upper().replace(".", "_"))

    @classmethod
    def get_by_category(cls, category: MetricCategory) -> list[MetricDefinition]:
        """Get all metrics in a specific category."""
        return [
            metric
            for metric in cls.get_all_metrics().values()
            if metric.category == category
        ]

    @classmethod
    def get_hero_metrics(cls) -> list[MetricDefinition]:
        """Get hero (top-level) metrics."""
        return cls.get_by_category(MetricCategory.HERO)

    @classmethod
    def get_load_metrics(cls) -> list[MetricDefinition]:
        """Get load metrics."""
        return cls.get_by_category(MetricCategory.LOAD)

    @classmethod
    def get_intensity_metrics(cls) -> list[MetricDefinition]:
        """Get intensity metrics."""
        return cls.get_by_category(MetricCategory.INTENSITY)

    @classmethod
    def get_physiology_metrics(cls) -> list[MetricDefinition]:
        """Get physiology metrics."""
        return cls.get_by_category(MetricCategory.PHYSIOLOGY)

    @classmethod
    def get_power_metrics(cls) -> list[MetricDefinition]:
        """Get power metrics."""
        return cls.get_by_category(MetricCategory.POWER)

    @classmethod
    def get_status_metrics(cls) -> list[MetricDefinition]:
        """Get status metrics."""
        return cls.get_by_category(MetricCategory.STATUS)
