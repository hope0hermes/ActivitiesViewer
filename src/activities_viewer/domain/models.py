"""
Domain models for the ActivitiesViewer application.

These models represent the core business entities and are independent of the data source.
Designed for StravaAnalyzer v2.0+ dual-file format (activities_raw.csv, activities_moving.csv).

The file source determines whether metrics are raw (including stopped time) or moving
(excluding stopped time) - no prefixes needed since data is separated by file.
"""

import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Activity(BaseModel):
    """
    Represents a single physical activity (ride, run, etc.).

    This model maps directly to columns in StravaAnalyzer's output CSV files.
    All field names match CSV column names exactly (no prefixes).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # IDENTITY & METADATA
    # ═══════════════════════════════════════════════════════════════════════════
    id: int
    name: str
    type: str
    sport_type: str
    start_date: datetime
    start_date_local: datetime
    workout_type: float | None = Field(
        default=None,
        description="Strava workout type: 10=Race, 11=Long Run, 12=Workout, etc.",
    )

    # Equipment & Location
    gear_id: str | None = Field(default=None, description="Strava gear identifier")
    timezone: str | None = Field(default=None, description="Activity timezone")
    utc_offset: float | None = Field(
        default=None, description="UTC offset in seconds"
    )
    location_city: str | None = Field(default=None)
    location_state: str | None = Field(default=None)
    location_country: str | None = Field(default=None)

    # Strava Metadata
    resource_state: int | None = Field(default=None)
    achievement_count: int | None = Field(default=None)
    kudos_count: int | None = Field(default=None)
    comment_count: int | None = Field(default=None)
    athlete_count: int | None = Field(default=None)
    photo_count: int | None = Field(default=None)
    total_photo_count: int | None = Field(default=None)
    pr_count: int | None = Field(default=None)
    trainer: bool | None = Field(default=None)
    commute: bool | None = Field(default=None)
    manual: bool | None = Field(default=None)
    private: bool | None = Field(default=None)
    visibility: str | None = Field(default=None)
    flagged: bool | None = Field(default=None)
    has_kudoed: bool | None = Field(default=None)
    from_accepted_tag: bool | None = Field(default=None)

    # Device & Upload Info
    device_name: str | None = Field(default=None)
    device_watts: bool | None = Field(
        default=None, description="True if power from device"
    )
    upload_id: int | None = Field(default=None)
    upload_id_str: str | float | int | None = Field(default=None)
    external_id: str | None = Field(default=None)

    # GPS Data
    start_latlng: str | None = Field(default=None)
    end_latlng: str | None = Field(default=None)

    # Map Data (nested from Strava API, flattened in CSV)
    map_id: str | None = Field(default=None, validation_alias="map.id")
    map_summary_polyline: str | None = Field(
        default=None, validation_alias="map.summary_polyline"
    )
    map_resource_state: int | None = Field(
        default=None, validation_alias="map.resource_state"
    )

    # Athlete Reference
    athlete_id: int | None = Field(default=None, validation_alias="athlete.id")
    athlete_resource_state: int | None = Field(
        default=None, validation_alias="athlete.resource_state"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE TIME & DISTANCE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    distance: float = Field(description="Distance in meters")
    moving_time: float = Field(description="Time spent moving in seconds")
    elapsed_time: float = Field(description="Total elapsed time in seconds")
    total_time: float | None = Field(default=None, description="Total activity time")
    total_elevation_gain: float = Field(description="Elevation gain in meters")
    elevation_gain: float | None = Field(
        default=None, description="Enriched elevation gain"
    )
    elev_high: float | None = Field(default=None)
    elev_low: float | None = Field(default=None)

    # ═══════════════════════════════════════════════════════════════════════════
    # SPEED & PACE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_speed: float | None = Field(
        default=None, description="Average speed (m/s)"
    )
    max_speed: float | None = Field(default=None, description="Maximum speed (m/s)")
    normalized_graded_pace: float | None = Field(
        default=None, description="NGP adjusts pace for gradient"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    # Strava Original
    average_watts: float | None = Field(
        default=None, description="Strava average power"
    )
    max_watts: float | None = Field(default=None, description="Strava max power")
    weighted_average_watts: float | None = Field(
        default=None, description="Strava weighted avg power"
    )
    kilojoules: float | None = Field(
        default=None, description="Total work output (kJ)"
    )

    # Enriched Power Metrics
    average_power: float | None = Field(
        default=None, description="Average power (W)"
    )
    max_power: float | None = Field(default=None, description="Maximum power (W)")
    power_per_kg: float | None = Field(
        default=None, description="Power per kilogram (W/kg)"
    )
    normalized_power: float | None = Field(
        default=None,
        description="NP - physiological cost if power had been constant. Uses 30s rolling avg^4.",
    )
    intensity_factor: float | None = Field(
        default=None,
        description="IF = NP/FTP. <0.75 recovery, 0.75-0.85 endurance, 0.85-0.95 tempo, 0.95-1.05 threshold, >1.05 VO2max",
    )
    training_stress_score: float | None = Field(
        default=None,
        description="TSS = (duration × NP × IF) / (FTP × 3600) × 100. Quantifies total training load.",
    )
    variability_index: float | None = Field(
        default=None,
        description="VI = NP/AP. 1.0 = steady (TT), >1.1 = variable (group ride, crits)",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ADVANCED POWER METRICS (NEW)
    # ═══════════════════════════════════════════════════════════════════════════
    time_above_90_ftp: int | None = Field(
        default=None,
        description="Seconds above 90% FTP (VO2max zone). Measures high-intensity training stimulus.",
    )
    time_sweet_spot: int | None = Field(
        default=None,
        description="Seconds in sweet spot (88-94% FTP). Optimal zone for FTP development.",
    )
    w_prime_balance_min: float | None = Field(
        default=None,
        description="Minimum W' balance reached (J). Shows proximity to anaerobic exhaustion.",
    )
    w_prime_depletion: float | None = Field(
        default=None,
        description="W' depletion percentage. Shows how much anaerobic capacity was used.",
    )
    match_burn_count: int | None = Field(
        default=None,
        description="Number of significant W' expenditures (>50% depletion). Quantifies hard efforts.",
    )
    cp_config: float | None = Field(
        default=None,
        description="Configured Critical Power (W) used for W' balance calculations.",
    )
    w_prime_config: float | None = Field(
        default=None,
        description="Configured W' (J) used for W' balance calculations.",
    )
    cp_window_days: int | None = Field(
        default=None,
        description="Rolling window in days used for CP model calculations.",
    )
    negative_split_index: float | None = Field(
        default=None,
        description="NP 2nd half / NP 1st half. <0.95=negative split, 0.95-1.05=even, >1.05=fade.",
    )
    cardiac_drift: float | None = Field(
        default=None,
        description="(HR 2nd - HR 1st)/HR 1st × 100%. HR-only metric. <3%=excellent, >8%=poor/dehydrated.",
    )
    first_half_hr: float | None = Field(
        default=None,
        description="Average heart rate (BPM) during first half of ride.",
    )
    second_half_hr: float | None = Field(
        default=None,
        description="Average heart rate (BPM) during second half of ride.",
    )
    estimated_ftp: float | None = Field(
        default=None,
        description="FTP estimate from best 20-min power (×0.95). Track progression ride-to-ride.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CLIMBING METRICS (NEW)
    # ═══════════════════════════════════════════════════════════════════════════
    vam: float | None = Field(
        default=None,
        description="Velocità Ascensionale Media (m/h). Vertical ascent rate, the gold standard for climbing.",
    )
    climbing_time: int | None = Field(
        default=None,
        description="Seconds spent climbing (positive gradient). Quantifies climbing volume.",
    )
    climbing_power: float | None = Field(
        default=None,
        description="Average power on gradients >4% (W). Shows sustained climbing strength.",
    )
    climbing_power_per_kg: float | None = Field(
        default=None,
        description="Climbing power / weight (W/kg). THE key metric for climbing performance.",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # HEART RATE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    has_heartrate: bool | None = Field(default=None)
    heartrate_opt_out: bool | None = Field(default=None)
    display_hide_heartrate_option: bool | None = Field(default=None)

    # Strava Original
    average_heartrate: float | None = Field(
        default=None, description="Strava avg HR (bpm)"
    )
    max_heartrate: float | None = Field(
        default=None, description="Strava max HR (bpm)"
    )

    # Enriched HR Metrics
    average_hr: float | None = Field(default=None, description="Average HR (bpm)")
    max_hr: float | None = Field(default=None, description="Maximum HR (bpm)")
    hr_training_stress: float | None = Field(
        default=None, description="HR-based TSS (hrTSS)"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CADENCE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    average_cadence: float | None = Field(
        default=None, description="Average cadence (rpm)"
    )
    max_cadence: float | None = Field(
        default=None, description="Maximum cadence (rpm)"
    )
    average_temp: float | None = Field(
        default=None, description="Average temperature"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICIENCY & COUPLING METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    efficiency_factor: float | None = Field(
        default=None,
        description="EF = NP/Avg HR. Higher = better aerobic fitness. Track over time.",
    )
    power_hr_decoupling: float | None = Field(
        default=None,
        description="% change in EF from 1st to 2nd half. >5% = aerobic limiter.",
    )
    first_half_ef: float | None = Field(
        default=None, description="First half efficiency factor"
    )
    second_half_ef: float | None = Field(
        default=None, description="Second half efficiency factor"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    fatigue_index: float | None = Field(
        default=None,
        description="% power decline from initial to final 5min. 0-5%=excellent, 5-15%=good, >25%=poor",
    )
    initial_5min_power: float | None = Field(
        default=None, description="First 5 minutes avg power"
    )
    final_5min_power: float | None = Field(
        default=None, description="Last 5 minutes avg power"
    )
    first_half_power: float | None = Field(
        default=None, description="First half avg power"
    )
    second_half_power: float | None = Field(
        default=None, description="Second half avg power"
    )
    power_drift: float | None = Field(
        default=None,
        description="(Power 2nd - Power 1st)/Power 1st × 100%. Negative = fading. >-5%=excellent, <-15%=poor.",
    )
    half_power_ratio: float | None = Field(
        default=None, description="Ratio of second half to first half power"
    )
    power_coefficient_variation: float | None = Field(
        default=None,
        description="CV = (std/mean) × 100. Lower = more consistent pacing.",
    )
    power_sustainability_index: float | None = Field(
        default=None,
        description="PSI = max(0, 100-CV). >80=sustainable, <40=high variability",
    )

    # Interval Decay Analysis
    interval_300s_decay_rate: float | None = Field(default=None)
    interval_300s_power_trend: float | None = Field(default=None)
    interval_300s_first_power: float | None = Field(default=None)
    interval_300s_last_power: float | None = Field(default=None)

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER ZONES (Coggan 7-Zone Model)
    # ═══════════════════════════════════════════════════════════════════════════
    power_z1_percentage: float | None = Field(
        default=None, description="% time in Z1 (0-55% FTP)"
    )
    power_z2_percentage: float | None = Field(
        default=None, description="% time in Z2 (56-75% FTP)"
    )
    power_z3_percentage: float | None = Field(
        default=None, description="% time in Z3 (76-90% FTP)"
    )
    power_z4_percentage: float | None = Field(
        default=None, description="% time in Z4 (91-105% FTP)"
    )
    power_z5_percentage: float | None = Field(
        default=None, description="% time in Z5 (106-120% FTP)"
    )
    power_z6_percentage: float | None = Field(
        default=None, description="% time in Z6 (121-150% FTP)"
    )
    power_z7_percentage: float | None = Field(
        default=None, description="% time in Z7 (>150% FTP)"
    )

    # Power zone time (seconds)
    power_z1_time: float | None = Field(
        default=None, description="Seconds in Z1 (0-55% FTP)"
    )
    power_z2_time: float | None = Field(
        default=None, description="Seconds in Z2 (56-75% FTP)"
    )
    power_z3_time: float | None = Field(
        default=None, description="Seconds in Z3 (76-90% FTP)"
    )
    power_z4_time: float | None = Field(
        default=None, description="Seconds in Z4 (91-105% FTP)"
    )
    power_z5_time: float | None = Field(
        default=None, description="Seconds in Z5 (106-120% FTP)"
    )
    power_z6_time: float | None = Field(
        default=None, description="Seconds in Z6 (121-150% FTP)"
    )
    power_z7_time: float | None = Field(
        default=None, description="Seconds in Z7 (>150% FTP)"
    )

    # Power zone boundaries (watts)
    power_zone_1: float | None = Field(default=None, description="Z1 upper boundary")
    power_zone_2: float | None = Field(default=None, description="Z2 upper boundary")
    power_zone_3: float | None = Field(default=None, description="Z3 upper boundary")
    power_zone_4: float | None = Field(default=None, description="Z4 upper boundary")
    power_zone_5: float | None = Field(default=None, description="Z5 upper boundary")
    power_zone_6: float | None = Field(default=None, description="Z6 upper boundary")

    # ═══════════════════════════════════════════════════════════════════════════
    # HEART RATE ZONES (5-Zone Model)
    # ═══════════════════════════════════════════════════════════════════════════
    hr_z1_percentage: float | None = Field(
        default=None, description="% time in HR Z1"
    )
    hr_z2_percentage: float | None = Field(
        default=None, description="% time in HR Z2"
    )
    hr_z3_percentage: float | None = Field(
        default=None, description="% time in HR Z3"
    )
    hr_z4_percentage: float | None = Field(
        default=None, description="% time in HR Z4"
    )
    hr_z5_percentage: float | None = Field(
        default=None, description="% time in HR Z5"
    )

    # HR zone time (seconds)
    hr_z1_time: float | None = Field(default=None, description="Seconds in HR Z1")
    hr_z2_time: float | None = Field(default=None, description="Seconds in HR Z2")
    hr_z3_time: float | None = Field(default=None, description="Seconds in HR Z3")
    hr_z4_time: float | None = Field(default=None, description="Seconds in HR Z4")
    hr_z5_time: float | None = Field(default=None, description="Seconds in HR Z5")

    # HR zone boundaries (bpm)
    hr_zone_1: float | None = Field(default=None, description="HR Z1 upper boundary")
    hr_zone_2: float | None = Field(default=None, description="HR Z2 upper boundary")
    hr_zone_3: float | None = Field(default=None, description="HR Z3 upper boundary")
    hr_zone_4: float | None = Field(default=None, description="HR Z4 upper boundary")

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING INTENSITY DISTRIBUTION (TID) - 3-Zone Model
    # ═══════════════════════════════════════════════════════════════════════════
    # Power TID
    power_tid_z1_percentage: float | None = Field(
        default=None, description="% time in TID Z1 Low (<76% FTP)"
    )
    power_tid_z2_percentage: float | None = Field(
        default=None, description="% time in TID Z2 Moderate (76-90% FTP)"
    )
    power_tid_z3_percentage: float | None = Field(
        default=None, description="% time in TID Z3 High (>90% FTP)"
    )
    power_polarization_index: float | None = Field(
        default=None,
        description="PI = (Z1%+Z3%)/Z2%. >4.0=highly polarized, 2-4=moderate, <2=threshold-focused",
    )
    power_tdr: float | None = Field(
        default=None,
        description="Training Distribution Ratio = Z1%/Z3%. >2=polarized, <1=high-intensity",
    )
    power_tid_classification: str | float | None = Field(
        default=None, description="polarized, pyramidal, or threshold"
    )

    # HR TID
    hr_tid_z1_percentage: float | None = Field(
        default=None, description="% time in HR TID Z1"
    )
    hr_tid_z2_percentage: float | None = Field(
        default=None, description="% time in HR TID Z2"
    )
    hr_tid_z3_percentage: float | None = Field(
        default=None, description="% time in HR TID Z3"
    )
    hr_polarization_index: float | None = Field(
        default=None, description="HR Polarization Index"
    )
    hr_tdr: float | None = Field(
        default=None, description="HR Training Distribution Ratio"
    )
    hr_tid_classification: str | float | None = Field(
        default=None, description="HR TID classification"
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING LOAD & FITNESS METRICS (Longitudinal)
    # ═══════════════════════════════════════════════════════════════════════════
    chronic_training_load: float | None = Field(
        default=None,
        description="CTL - 42-day EMA of TSS. Represents fitness/adaptation level.",
    )
    acute_training_load: float | None = Field(
        default=None,
        description="ATL - 7-day EMA of TSS. Represents short-term fatigue.",
    )
    training_stress_balance: float | None = Field(
        default=None,
        description="TSB = CTL - ATL. >20=rested, 0-20=optimal, -10 to 0=productive, <-30=overreached",
    )
    acwr: float | None = Field(
        default=None,
        description="Acute:Chronic Workload Ratio. 0.8-1.3=optimal, >1.5=injury risk",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL POWER MODEL
    # ═══════════════════════════════════════════════════════════════════════════
    cp: float | None = Field(
        default=None, description="Critical Power (W). Max sustainable power for >10min"
    )
    w_prime: float | None = Field(
        default=None, description="W' (J). Anaerobic work capacity above CP"
    )
    cp_r_squared: float | None = Field(
        default=None, description="R² of CP model fit. >0.95=excellent, 0.85-0.95=good"
    )
    aei: float | None = Field(
        default=None,
        description="Anaerobic Energy Index (J/kg). W' normalized to body weight",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ATHLETE THRESHOLDS (from config, stored per activity)
    # ═══════════════════════════════════════════════════════════════════════════
    ftp: float | None = Field(default=None, description="FTP used for this activity")
    fthr: float | None = Field(
        default=None, description="FTHR used for this activity"
    )
    lt1_power: float | None = Field(default=None, description="LT1 power threshold")
    lt2_power: float | None = Field(default=None, description="LT2 power threshold")
    lt1_hr: float | None = Field(default=None, description="LT1 heart rate")
    lt2_hr: float | None = Field(default=None, description="LT2 heart rate")

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER CURVE (Peak Powers at various durations)
    # ═══════════════════════════════════════════════════════════════════════════
    power_curve_1sec: float | None = Field(default=None, description="Peak 1s power")
    power_curve_2sec: float | None = Field(default=None, description="Peak 2s power")
    power_curve_5sec: float | None = Field(default=None, description="Peak 5s power")
    power_curve_10sec: float | None = Field(
        default=None, description="Peak 10s power"
    )
    power_curve_15sec: float | None = Field(
        default=None, description="Peak 15s power"
    )
    power_curve_20sec: float | None = Field(
        default=None, description="Peak 20s power"
    )
    power_curve_30sec: float | None = Field(
        default=None, description="Peak 30s power"
    )
    power_curve_1min: float | None = Field(
        default=None, description="Peak 1min power"
    )
    power_curve_2min: float | None = Field(
        default=None, description="Peak 2min power"
    )
    power_curve_5min: float | None = Field(
        default=None, description="Peak 5min power"
    )
    power_curve_10min: float | None = Field(
        default=None, description="Peak 10min power"
    )
    power_curve_15min: float | None = Field(
        default=None, description="Peak 15min power"
    )
    power_curve_20min: float | None = Field(
        default=None, description="Peak 20min power"
    )
    power_curve_30min: float | None = Field(
        default=None, description="Peak 30min power"
    )
    power_curve_1hr: float | None = Field(default=None, description="Peak 1hr power")

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATORS
    # ═══════════════════════════════════════════════════════════════════════════

    @field_validator("*", mode="before")
    @classmethod
    def convert_nan_values(cls, v: Any, info) -> Any:
        """Convert NaN values to None for all fields."""
        if v is None:
            return None

        if isinstance(v, float):
            if math.isnan(v):
                return None
            return v

        if isinstance(v, str):
            if v.lower() == "nan" or v.strip() == "":
                return None

        return v

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def date_str(self) -> str:
        """Format date as YYYY-MM-DD string."""
        return self.start_date_local.strftime("%Y-%m-%d")

    @property
    def duration_str(self) -> str:
        """Format moving time as human-readable string."""
        hours = int(self.moving_time // 3600)
        minutes = int((self.moving_time % 3600) // 60)
        return f"{hours}h {minutes}m"

    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.distance / 1000

    @property
    def speed_kmh(self) -> float | None:
        """Average speed in km/h."""
        if self.average_speed:
            return self.average_speed * 3.6
        return None


class YearSummary(BaseModel):
    """Aggregated statistics for a specific year."""

    year: int
    total_distance: float
    total_time: float
    total_elevation: float
    activity_count: int
    avg_power: float | None = None
    total_tss: float | None = None


class Athlete(BaseModel):
    """Represents the athlete using the dashboard."""

    id: int | None = None
    ftp: float
    weight_kg: float
    max_hr: int


class TrainingBlock(BaseModel):
    """
    Represents a specific training phase.

    Training blocks are used to organize activities into distinct training periods
    with specific focus areas (e.g., "Base 1", "Build", "Peak").
    """

    name: str = Field(
        description="Name of the training block (e.g., 'Base 1', 'Build')"
    )
    start_date: datetime = Field(description="Start date of the training block")
    end_date: datetime = Field(description="End date of the training block")
    focus_metric: str = Field(
        description="Primary focus of this block (e.g., 'Volume', 'FTP', 'VO2Max')"
    )

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class Goal(BaseModel):
    """
    Defines the athlete's training goal.

    This model encapsulates the target performance metric and timeline,
    enabling the application to provide goal-oriented coaching insights.
    """

    target_wkg: float = Field(
        description="Target power-to-weight ratio in W/kg (e.g., 4.0)", gt=0
    )
    target_date: datetime = Field(
        description="Date by which the goal should be achieved"
    )
    start_wkg: float = Field(description="Starting power-to-weight ratio in W/kg", gt=0)
    start_date: datetime = Field(description="Date when goal tracking began")

    @field_validator("target_date")
    @classmethod
    def validate_target_date(cls, v: datetime, info) -> datetime:
        """Ensure target_date is in the future relative to start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("target_date must be after start_date")
        return v

    @field_validator("target_wkg")
    @classmethod
    def validate_target_wkg(cls, v: float, info) -> float:
        """Ensure target is greater than start (for improvement goals)."""
        if "start_wkg" in info.data and v <= info.data["start_wkg"]:
            raise ValueError(
                "target_wkg must be greater than start_wkg for improvement goals"
            )
        return v

    @property
    def days_remaining(self) -> int:
        """Calculate days remaining until target date."""
        delta = self.target_date - datetime.now()
        return max(0, delta.days)

    @property
    def weeks_remaining(self) -> float:
        """Calculate weeks remaining until target date."""
        return self.days_remaining / 7.0

    @property
    def wkg_improvement_needed(self) -> float:
        """Calculate total W/kg improvement needed."""
        return self.target_wkg - self.start_wkg

    @property
    def required_weekly_gain(self) -> float:
        """Calculate required W/kg gain per week to meet goal."""
        if self.weeks_remaining <= 0:
            return 0.0
        return self.wkg_improvement_needed / self.weeks_remaining


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING PLAN MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class TrainingPhase(BaseModel):
    """Represents a training phase (Base, Build, Specialty, Taper)."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Phase name: base, build, specialty, taper, recovery")
    weeks: int = Field(ge=1, description="Duration in weeks")
    description: str = Field(default="", description="Phase description and focus")
    tid_z1: float = Field(default=75, ge=0, le=100, description="% time in Zone 1")
    tid_z2: float = Field(default=15, ge=0, le=100, description="% time in Zone 2")
    tid_z3: float = Field(default=10, ge=0, le=100, description="% time in Zone 3")
    intensity_factor_target: float = Field(default=0.65, ge=0.4, le=1.0, description="Target avg IF")
    tss_ramp_rate: float = Field(default=5.0, description="Weekly TSS increase %")


class KeyEvent(BaseModel):
    """Represents a key event or race in the training plan."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Event name")
    date: datetime = Field(description="Event date")
    priority: str = Field(default="B", description="Priority: A (peak), B (important), C (training)")
    event_type: str = Field(default="race", description="Type: race, gran_fondo, group_ride, test")
    notes: str = Field(default="", description="Additional notes")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Ensure priority is A, B, or C."""
        if v.upper() not in ["A", "B", "C"]:
            raise ValueError("Priority must be A, B, or C")
        return v.upper()


class WeeklyPlan(BaseModel):
    """Represents a single week's training prescription."""

    model_config = ConfigDict(extra="ignore")

    week_number: int = Field(ge=1, description="Week number in plan")
    start_date: datetime = Field(description="Week start date")
    end_date: datetime = Field(description="Week end date")
    phase: str = Field(description="Training phase: base, build, specialty, taper, recovery")
    phase_week: int = Field(ge=1, description="Week number within the phase")

    # Training Targets
    target_hours: float = Field(ge=0, description="Target training hours")
    target_tss: int = Field(ge=0, description="Target weekly TSS")
    target_ctl: float = Field(default=0, description="Target CTL at week end")

    # Intensity Distribution
    tid_z1: float = Field(default=75, description="% time in Zone 1")
    tid_z2: float = Field(default=15, description="% time in Zone 2")
    tid_z3: float = Field(default=10, description="% time in Zone 3")

    # Key Workouts
    key_workouts: list[str] = Field(default_factory=list, description="Key workout descriptions")
    recovery_notes: str = Field(default="", description="Recovery recommendations")

    # Actual (filled after week completes)
    actual_hours: float | None = Field(default=None, description="Actual training hours")
    actual_tss: int | None = Field(default=None, description="Actual weekly TSS")
    actual_ctl: float | None = Field(default=None, description="Actual CTL at week end")
    adherence_pct: float | None = Field(default=None, description="Plan adherence %")

    # Events
    events: list[str] = Field(default_factory=list, description="Events this week")
    is_recovery_week: bool = Field(default=False, description="Recovery week flag")
    is_taper_week: bool = Field(default=False, description="Taper week flag")


class TrainingPlan(BaseModel):
    """Complete training plan with all weeks."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Plan name")
    goal: str = Field(description="Goal description (e.g., 'Reach 4.5 W/kg')")
    created_at: datetime = Field(default_factory=datetime.now)

    # Athlete Profile
    start_ftp: float = Field(gt=0, description="FTP at plan start")
    target_ftp: float = Field(gt=0, description="Target FTP at plan end")
    weight_kg: float = Field(gt=0, description="Athlete weight")
    hours_per_week: float = Field(gt=0, description="Available hours per week")

    # Plan Duration
    start_date: datetime = Field(description="Plan start date")
    end_date: datetime = Field(description="Plan end date")
    total_weeks: int = Field(ge=1, description="Total weeks in plan")

    # Phases
    phases: list[TrainingPhase] = Field(default_factory=list, description="Training phases")

    # Weekly Plans
    weeks: list[WeeklyPlan] = Field(default_factory=list, description="Weekly plans")

    # Key Events
    key_events: list[KeyEvent] = Field(default_factory=list, description="Key events/races")

    @property
    def current_week(self) -> int:
        """Get current week number (1-based)."""
        now = datetime.now()
        if now < self.start_date:
            return 0
        if now > self.end_date:
            return self.total_weeks
        delta = now - self.start_date
        return min(self.total_weeks, delta.days // 7 + 1)

    @property
    def progress_pct(self) -> float:
        """Get plan progress as percentage."""
        return (self.current_week / self.total_weeks) * 100 if self.total_weeks > 0 else 0

    @property
    def ftp_improvement_pct(self) -> float:
        """Calculate expected FTP improvement."""
        return ((self.target_ftp - self.start_ftp) / self.start_ftp) * 100
