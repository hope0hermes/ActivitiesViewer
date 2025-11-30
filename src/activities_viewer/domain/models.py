"""
Domain models for the ActivitiesViewer application.
These models represent the core business entities and are independent of the data source.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Activity(BaseModel):
    """
    Represents a single physical activity (ride, run, etc.).

    This model captures both raw Strava data and enriched metrics calculated
    by StravaAnalyzer. All metrics have both `raw_` (includes stopped time)
    and `moving_` (excludes stopped time) variants where applicable.
    """
    model_config = ConfigDict(extra="ignore")

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTITY & METADATA
    # ═══════════════════════════════════════════════════════════════════════════
    id: int
    name: str
    type: str
    sport_type: str
    start_date: datetime
    start_date_local: datetime
    workout_type: Optional[float] = Field(
        default=None,
        description="Strava workout type: 10=Race, 11=Long Run, 12=Workout, etc."
    )

    # Equipment & Location
    gear_id: Optional[str] = Field(
        default=None,
        description="Strava gear identifier (e.g., 'b14302691' for a bike)"
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Activity timezone (e.g., '(GMT+01:00) Europe/Berlin')"
    )
    utc_offset: Optional[float] = Field(
        default=None,
        description="UTC offset in seconds"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE TIME & DISTANCE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    distance: float = Field(description="Distance in meters")
    moving_time: float = Field(
        description="Time spent moving in seconds (excludes auto-pause)"
    )
    elapsed_time: float = Field(
        description="Total elapsed time in seconds (wall clock time)"
    )
    total_time: Optional[float] = Field(
        default=None,
        description="Total activity time including gaps (from enriched data)"
    )
    total_elevation_gain: float = Field(description="Elevation gain in meters")
    elevation_gain: Optional[float] = Field(
        default=None,
        description="Enriched elevation gain calculation"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # STRAVA ORIGINAL POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_watts: Optional[float] = Field(
        default=None, description="Strava's average power (watts)"
    )
    max_watts: Optional[float] = Field(
        default=None, description="Strava's max power (watts)"
    )
    weighted_average_watts: Optional[float] = Field(
        default=None, description="Strava's weighted average power (similar to NP)"
    )
    kilojoules: Optional[float] = Field(
        default=None, description="Total work output in kilojoules"
    )
    device_watts: Optional[bool] = Field(
        default=None, description="Whether power comes from a device vs estimated"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # STRAVA ORIGINAL HEART RATE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_heartrate: Optional[float] = Field(
        default=None, description="Strava's average heart rate (bpm)"
    )
    max_heartrate: Optional[float] = Field(
        default=None, description="Strava's max heart rate (bpm)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RAW POWER METRICS (includes stopped time)
    # Use when analyzing total effort including rest periods
    # ═══════════════════════════════════════════════════════════════════════════
    raw_average_power: Optional[float] = Field(
        default=None,
        description="Time-weighted average power including stops. Lower than moving_average_power for activities with rest periods."
    )
    raw_max_power: Optional[float] = Field(
        default=None, description="Maximum power output recorded"
    )
    raw_power_per_kg: Optional[float] = Field(
        default=None, description="Watts per kilogram (raw average)"
    )
    raw_normalized_power: Optional[float] = Field(
        default=None,
        description="Normalized Power (NP) including stops. Represents physiological cost if power had been constant. Uses 30s rolling average raised to 4th power."
    )
    raw_intensity_factor: Optional[float] = Field(
        default=None,
        description="IF = NP / FTP. Values: <0.75 recovery, 0.75-0.85 endurance, 0.85-0.95 tempo, 0.95-1.05 threshold, >1.05 VO2max"
    )
    raw_training_stress_score: Optional[float] = Field(
        default=None,
        description="TSS = (duration × NP × IF) / (FTP × 3600) × 100. Quantifies total training load. 150+ = very hard day."
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MOVING POWER METRICS (excludes stopped time)
    # Primary metrics for analyzing actual riding intensity
    # ═══════════════════════════════════════════════════════════════════════════
    moving_average_power: Optional[float] = Field(
        default=None,
        description="Time-weighted average power excluding stops. Higher than raw_average_power, represents true riding intensity."
    )
    moving_max_power: Optional[float] = Field(
        default=None, description="Maximum power while moving"
    )
    moving_power_per_kg: Optional[float] = Field(
        default=None, description="Watts per kilogram (moving average)"
    )
    moving_normalized_power: Optional[float] = Field(
        default=None,
        description="NP excluding stops. Better represents workout intensity for activities with cafe stops or traffic lights."
    )
    moving_intensity_factor: Optional[float] = Field(
        default=None,
        description="Moving IF = Moving NP / FTP. Typically higher than raw IF for activities with stops."
    )
    moving_training_stress_score: Optional[float] = Field(
        default=None,
        description="Moving TSS. Uses moving time duration. Better for comparing workout intensity across activities."
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # RAW HEART RATE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    raw_average_hr: Optional[float] = Field(
        default=None, description="Average HR including stopped periods"
    )
    raw_max_hr: Optional[float] = Field(
        default=None, description="Maximum HR recorded"
    )
    raw_hr_training_stress: Optional[float] = Field(
        default=None,
        description="hrTSS based on raw time and HR. Useful when power unavailable."
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MOVING HEART RATE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    moving_average_hr: Optional[float] = Field(
        default=None,
        description="Average HR while moving only. Higher than raw for rides with stops."
    )
    moving_max_hr: Optional[float] = Field(
        default=None, description="Maximum HR while moving"
    )
    moving_hr_training_stress: Optional[float] = Field(
        default=None, description="hrTSS based on moving time and HR"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICIENCY & COUPLING METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    raw_efficiency_factor: Optional[float] = Field(
        default=None,
        description="EF = NP / Avg HR (raw). Tracks aerobic fitness - higher is better. Compare over time for similar efforts."
    )
    raw_variability_index: Optional[float] = Field(
        default=None,
        description="VI = NP / Avg Power (raw). 1.0 = perfectly steady (TT), >1.1 = variable (group ride, crits)"
    )
    raw_power_hr_decoupling: Optional[float] = Field(
        default=None,
        description="% change in EF from 1st to 2nd half. Negative = fatigue/dehydration. >5% drift indicates aerobic limiter. Requires 1hr+ effort."
    )
    raw_first_half_ef: Optional[float] = Field(
        default=None, description="Efficiency factor for first half of activity"
    )
    raw_second_half_ef: Optional[float] = Field(
        default=None, description="Efficiency factor for second half of activity"
    )

    moving_efficiency_factor: Optional[float] = Field(
        default=None, description="EF excluding stopped time"
    )
    moving_variability_index: Optional[float] = Field(
        default=None, description="VI excluding stopped time"
    )
    moving_power_hr_decoupling: Optional[float] = Field(
        default=None, description="Decoupling excluding stopped time"
    )
    moving_first_half_ef: Optional[float] = Field(
        default=None, description="First half EF (moving only)"
    )
    moving_second_half_ef: Optional[float] = Field(
        default=None, description="Second half EF (moving only)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # SPEED & PACE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_speed: Optional[float] = Field(
        default=None, description="Average speed from Strava API (m/s)"
    )
    raw_average_speed: Optional[float] = Field(
        default=None, description="Average speed including stops (m/s)"
    )
    raw_max_speed: Optional[float] = Field(
        default=None, description="Maximum speed recorded (m/s)"
    )
    raw_normalized_graded_pace: Optional[float] = Field(
        default=None,
        description="NGP adjusts pace for gradient - uphill counts as harder, downhill as easier. Useful for comparing hilly vs flat routes."
    )
    moving_average_speed: Optional[float] = Field(
        default=None, description="Average speed while moving (m/s)"
    )
    moving_max_speed: Optional[float] = Field(
        default=None, description="Maximum speed while moving (m/s)"
    )
    moving_normalized_graded_pace: Optional[float] = Field(
        default=None, description="NGP while moving only"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CADENCE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_cadence: Optional[float] = Field(
        default=None, description="Average cadence from Strava API (rpm)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # Quantify ability to sustain power over time
    # ═══════════════════════════════════════════════════════════════════════════
    raw_fatigue_index: Optional[float] = Field(
        default=None,
        description="% power decline from initial to final 5min. 0-5%=excellent pacing, 5-15%=good, 15-25%=moderate, >25%=poor pacing"
    )
    raw_initial_5min_power: Optional[float] = Field(
        default=None, description="Average power for first 5 minutes"
    )
    raw_final_5min_power: Optional[float] = Field(
        default=None, description="Average power for last 5 minutes"
    )
    raw_first_half_power: Optional[float] = Field(
        default=None, description="Average power for first half of activity"
    )
    raw_second_half_power: Optional[float] = Field(
        default=None, description="Average power for second half of activity"
    )
    raw_power_drop_percentage: Optional[float] = Field(
        default=None,
        description="% drop from first to second half. <5%=excellent, 5-10%=good, 10-20%=moderate fade"
    )
    raw_half_power_ratio: Optional[float] = Field(
        default=None, description="Ratio of second half to first half power"
    )
    raw_power_coefficient_variation: Optional[float] = Field(
        default=None,
        description="CV = (std/mean) × 100. Lower = more consistent pacing. TT ~5-10%, Group ride 20-40%"
    )
    raw_power_sustainability_index: Optional[float] = Field(
        default=None,
        description="PSI = max(0, 100 - CV). >80=very sustainable, 60-80=good, <40=high variability"
    )

    moving_fatigue_index: Optional[float] = Field(
        default=None, description="Fatigue index excluding stopped time"
    )
    moving_initial_5min_power: Optional[float] = Field(
        default=None, description="Initial 5min power (moving only)"
    )
    moving_final_5min_power: Optional[float] = Field(
        default=None, description="Final 5min power (moving only)"
    )
    moving_first_half_power: Optional[float] = Field(
        default=None, description="First half power (moving only)"
    )
    moving_second_half_power: Optional[float] = Field(
        default=None, description="Second half power (moving only)"
    )
    moving_power_drop_percentage: Optional[float] = Field(
        default=None, description="Power drop % (moving only)"
    )
    moving_half_power_ratio: Optional[float] = Field(
        default=None, description="Half power ratio (moving only)"
    )
    moving_power_coefficient_variation: Optional[float] = Field(
        default=None, description="Power CV (moving only)"
    )
    moving_power_sustainability_index: Optional[float] = Field(
        default=None, description="Sustainability index (moving only)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER ZONES (Coggan 7-Zone Model)
    # Z1: 0-55% FTP (Active Recovery)
    # Z2: 56-75% FTP (Endurance)
    # Z3: 76-90% FTP (Tempo)
    # Z4: 91-105% FTP (Threshold)
    # Z5: 106-120% FTP (VO2max)
    # Z6: 121-150% FTP (Anaerobic)
    # Z7: >150% FTP (Neuromuscular)
    # ═══════════════════════════════════════════════════════════════════════════
    raw_power_z1_percentage: Optional[float] = Field(
        default=None, description="% time in Z1 Active Recovery (0-55% FTP)"
    )
    raw_power_z2_percentage: Optional[float] = Field(
        default=None, description="% time in Z2 Endurance (56-75% FTP)"
    )
    raw_power_z3_percentage: Optional[float] = Field(
        default=None, description="% time in Z3 Tempo (76-90% FTP)"
    )
    raw_power_z4_percentage: Optional[float] = Field(
        default=None, description="% time in Z4 Threshold (91-105% FTP)"
    )
    raw_power_z5_percentage: Optional[float] = Field(
        default=None, description="% time in Z5 VO2max (106-120% FTP)"
    )
    raw_power_z6_percentage: Optional[float] = Field(
        default=None, description="% time in Z6 Anaerobic (121-150% FTP)"
    )
    raw_power_z7_percentage: Optional[float] = Field(
        default=None, description="% time in Z7 Neuromuscular (>150% FTP)"
    )

    moving_power_z1_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z1"
    )
    moving_power_z2_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z2"
    )
    moving_power_z3_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z3"
    )
    moving_power_z4_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z4"
    )
    moving_power_z5_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z5"
    )
    moving_power_z6_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z6"
    )
    moving_power_z7_percentage: Optional[float] = Field(
        default=None, description="% moving time in Z7"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # HEART RATE ZONES (5-Zone Model)
    # Based on % of FTHR (Functional Threshold Heart Rate)
    # ═══════════════════════════════════════════════════════════════════════════
    raw_hr_z1_percentage: Optional[float] = Field(
        default=None, description="% time in HR Z1 (<82% FTHR)"
    )
    raw_hr_z2_percentage: Optional[float] = Field(
        default=None, description="% time in HR Z2 (82-89% FTHR)"
    )
    raw_hr_z3_percentage: Optional[float] = Field(
        default=None, description="% time in HR Z3 (89-94% FTHR)"
    )
    raw_hr_z4_percentage: Optional[float] = Field(
        default=None, description="% time in HR Z4 (94-100% FTHR)"
    )
    raw_hr_z5_percentage: Optional[float] = Field(
        default=None, description="% time in HR Z5 (>100% FTHR)"
    )

    moving_hr_z1_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR Z1"
    )
    moving_hr_z2_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR Z2"
    )
    moving_hr_z3_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR Z3"
    )
    moving_hr_z4_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR Z4"
    )
    moving_hr_z5_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR Z5"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING INTENSITY DISTRIBUTION (TID) - 3-Zone Model
    # Simplified zones for analyzing training polarization
    # Power: Z1 (<76% FTP), Z2 (76-90% FTP), Z3 (>90% FTP)
    # HR: Z1 (<82% FTHR), Z2 (82-94% FTHR), Z3 (>94% FTHR)
    # ═══════════════════════════════════════════════════════════════════════════
    raw_power_tid_z1_percentage: Optional[float] = Field(
        default=None, description="% time in TID Z1 Low (<76% FTP)"
    )
    raw_power_tid_z2_percentage: Optional[float] = Field(
        default=None, description="% time in TID Z2 Moderate (76-90% FTP)"
    )
    raw_power_tid_z3_percentage: Optional[float] = Field(
        default=None, description="% time in TID Z3 High (>90% FTP)"
    )
    raw_power_polarization_index: Optional[float] = Field(
        default=None,
        description="PI = (Z1% + Z3%) / Z2%. Higher = more polarized. >4.0 = highly polarized (ideal for endurance)"
    )
    raw_power_tid_classification: Optional[Union[str, float]] = Field(
        default=None,
        description="Training type: 'polarized' (Z1+Z3 dominant), 'pyramidal' (Z1>Z2>Z3), 'threshold' (Z2 dominant)"
    )
    raw_power_tdr: Optional[float] = Field(
        default=None,
        description="Training Distribution Ratio = Z1% / Z3%. >2.0 = polarized, 1-2 = balanced, <1 = high-intensity focused"
    )

    moving_power_tid_z1_percentage: Optional[float] = Field(
        default=None, description="% moving time in TID Z1"
    )
    moving_power_tid_z2_percentage: Optional[float] = Field(
        default=None, description="% moving time in TID Z2"
    )
    moving_power_tid_z3_percentage: Optional[float] = Field(
        default=None, description="% moving time in TID Z3"
    )
    moving_power_polarization_index: Optional[float] = Field(
        default=None, description="Polarization Index (moving only)"
    )
    moving_power_tid_classification: Optional[Union[str, float]] = Field(
        default=None, description="Training classification (moving only)"
    )
    moving_power_tdr: Optional[float] = Field(
        default=None, description="Training Distribution Ratio (moving only)"
    )

    raw_hr_tid_z1_percentage: Optional[float] = Field(
        default=None, description="% time in HR TID Z1 Low"
    )
    raw_hr_tid_z2_percentage: Optional[float] = Field(
        default=None, description="% time in HR TID Z2 Moderate"
    )
    raw_hr_tid_z3_percentage: Optional[float] = Field(
        default=None, description="% time in HR TID Z3 High"
    )
    raw_hr_polarization_index: Optional[float] = Field(
        default=None, description="HR Polarization Index"
    )
    raw_hr_tid_classification: Optional[Union[str, float]] = Field(
        default=None, description="HR-based training classification"
    )
    raw_hr_tdr: Optional[float] = Field(
        default=None, description="HR Training Distribution Ratio"
    )

    moving_hr_tid_z1_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR TID Z1"
    )
    moving_hr_tid_z2_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR TID Z2"
    )
    moving_hr_tid_z3_percentage: Optional[float] = Field(
        default=None, description="% moving time in HR TID Z3"
    )
    moving_hr_polarization_index: Optional[float] = Field(
        default=None, description="HR Polarization Index (moving only)"
    )
    moving_hr_tid_classification: Optional[Union[str, float]] = Field(
        default=None, description="HR training classification (moving only)"
    )
    moving_hr_tdr: Optional[float] = Field(
        default=None, description="HR TDR (moving only)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER CURVE (Peak Powers at different durations)
    # Maximum Mean Power (MMP) for each duration window
    # Used to create power-duration curves and identify athlete phenotype
    # ═══════════════════════════════════════════════════════════════════════════
    power_curve_5sec: Optional[float] = Field(
        default=None,
        description="Peak 5-second power. Neuromuscular/sprint capacity. World-class sprinters: 1500-2000W"
    )
    power_curve_10sec: Optional[float] = Field(
        default=None, description="Peak 10-second power. Sprint/acceleration capacity"
    )
    power_curve_30sec: Optional[float] = Field(
        default=None, description="Peak 30-second power. Anaerobic capacity"
    )
    power_curve_1min: Optional[float] = Field(
        default=None,
        description="Peak 1-minute power. Anaerobic capacity. Key for short climbs, attacks"
    )
    power_curve_2min: Optional[float] = Field(
        default=None, description="Peak 2-minute power. VO2max-anaerobic transition"
    )
    power_curve_5min: Optional[float] = Field(
        default=None,
        description="Peak 5-minute power. VO2max / MAP capacity. Key indicator of climbing ability"
    )
    power_curve_10min: Optional[float] = Field(
        default=None, description="Peak 10-minute power. Sustained VO2max"
    )
    power_curve_20min: Optional[float] = Field(
        default=None,
        description="Peak 20-minute power. ~95% of FTP. Often used for FTP estimation"
    )
    power_curve_30min: Optional[float] = Field(
        default=None, description="Peak 30-minute power. Near-threshold capacity"
    )
    power_curve_1hr: Optional[float] = Field(
        default=None,
        description="Peak 60-minute power. Closest to true FTP. Time trial capacity"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERVAL DECAY METRICS (5-minute intervals)
    # Analyzes power consistency across equal intervals
    # ═══════════════════════════════════════════════════════════════════════════
    interval_300s_decay_rate: Optional[float] = Field(
        default=None,
        description="Average power decrease per 5-min interval (W/interval). Negative = declining power"
    )
    interval_300s_power_trend: Optional[float] = Field(
        default=None,
        description="Linear regression slope of interval powers. Negative = power decay over time"
    )
    interval_300s_first_power: Optional[float] = Field(
        default=None, description="Average power in first 5-minute interval"
    )
    interval_300s_last_power: Optional[float] = Field(
        default=None, description="Average power in last 5-minute interval"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ADDITIONAL METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    moving_power_stability_index: Optional[float] = Field(
        default=None,
        description="Normalized measure of power consistency. Higher = more stable output"
    )

    @field_validator("*", mode="before")
    @classmethod
    def convert_nan_values(cls, v: Any, info) -> Any:
        """Convert NaN values to None for all fields."""
        import math

        # Skip None values
        if v is None:
            return None

        # Handle NaN floats for numeric fields
        if isinstance(v, float):
            if math.isnan(v):
                return None
            return v

        # Handle NaN strings for string fields
        if isinstance(v, str):
            if v.lower() == "nan" or v.strip() == "":
                # Return None for fields that should be None when empty
                if info.field_name in (
                    "moving_power_tid_classification",
                    "moving_hr_tid_classification",
                ):
                    return None
        return v

    @property
    def date_str(self) -> str:
        return self.start_date_local.strftime("%Y-%m-%d")

    @property
    def duration_str(self) -> str:
        hours = int(self.moving_time // 3600)
        minutes = int((self.moving_time % 3600) // 60)
        return f"{hours}h {minutes}m"


class YearSummary(BaseModel):
    """
    Aggregated statistics for a specific year.
    """
    year: int
    total_distance: float
    total_time: float
    total_elevation: float
    activity_count: int
    avg_power: Optional[float] = None
    total_tss: Optional[float] = None


class Athlete(BaseModel):
    """
    Represents the athlete using the dashboard.
    """
    id: Optional[int] = None
    ftp: float
    weight_kg: float
    max_hr: int
