"""Base descriptions for metrics - prose only, no threshold values.

This is the SINGLE SOURCE OF TRUTH for metric descriptions.
Threshold values are defined separately in METRICS_METADATA.
The get_help_text() function combines these to generate full help text.
"""

# ═══════════════════════════════════════════════════════════════════════════
# BASE DESCRIPTIONS - Pure prose, NO threshold values
# ═══════════════════════════════════════════════════════════════════════════

BASE_DESCRIPTIONS = {
    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING LOAD METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "tss": """Quantifies training load based on duration and intensity.
TSS = (Duration × NP × IF) / (FTP × 3600) × 100

**Reference**: 1hr at FTP (IF=1.0) = TSS 100""",

    "ctl": """42-day exponentially weighted average of daily TSS.
Represents overall 'fitness' and training capacity.
Higher CTL = greater ability to handle training load.""",

    "atl": """7-day exponentially weighted average of daily TSS.
Represents short-term fatigue/stress.
High ATL relative to CTL indicates overtraining risk.""",

    "tsb": """Form indicator calculated as CTL - ATL.
Represents the balance between fitness (CTL) and fatigue (ATL).
Used to time peak performance for races.""",

    "acwr": """Injury risk indicator calculated as ATL ÷ CTL.
Monitors training load progression relative to fitness.
Too rapid increases indicate elevated injury risk.""",

    "monotony_index": """Training variety measure: mean daily TSS ÷ standard deviation.
Lower values = more training variety (good).
High monotony combined with high volume increases injury/burnout risk.

**Source**: Foster (1998)""",

    "strain_index": """Weekly TSS × Monotony Index.
Combines total load with training variety to quantify stress risk.
Lower strain allows for better adaptation.

**Source**: Foster (1998)""",

    # ═══════════════════════════════════════════════════════════════════════
    # POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "normalized_power": """Represents the power you could have maintained for the same
physiological cost if output had been constant.
Uses 30s rolling average raised to 4th power.
More accurate than average power for variable efforts.""",

    "intensity_factor": """Ratio of Normalized Power to FTP (IF = NP / FTP).
Categorizes workout intensity relative to your threshold.""",

    "variability_index": """Ratio of Normalized Power to Average Power (VI = NP / Avg).
Indicates how steady or variable your power output was.""",

    # ═══════════════════════════════════════════════════════════════════════
    # CRITICAL POWER MODEL
    # ═══════════════════════════════════════════════════════════════════════
    "cp": """The boundary between steady-state and non-steady-state exercise.
Maximum power sustainable for extended efforts (>3-10 minutes).
Your aerobic ceiling - higher CP = better endurance capacity.

Computed from 90-day rolling power curve.
Note: Absolute watts vary by body weight; W/kg is more useful for comparison.""",

    "w_prime": """Anaerobic work capacity above critical power.
The amount of work (in kJ) you can do above CP before exhaustion.
Depletes during intense efforts, recovers during rest.

Computed from 90-day rolling power curve.""",

    "cp_r_squared": """Goodness of fit for the Critical Power model (0-1).
Indicates how well the mathematical model fits your power-duration data.
Higher R² = more reliable CP and W' estimates.""",

    "aei": """W' (anaerobic capacity) normalized to body weight (kJ/kg).
Higher AEI = greater anaerobic capacity per kg of body weight.
Track over time to monitor changes in anaerobic work capacity.""",

    "w_prime_depletion": """Maximum percentage of W' used during the ride.
Shows how deeply you dipped into anaerobic reserves.""",

    "w_prime_balance_min": """Lowest W' balance reached during the ride (kJ).
Shows how deeply you dipped into anaerobic reserves.
Lower values = harder efforts above CP.""",

    # ═══════════════════════════════════════════════════════════════════════
    # EFFICIENCY & CARDIAC METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "ef": """Power per heartbeat (NP / Avg HR).
Higher is better - more power for same cardiac effort.
Track over time for similar efforts to monitor aerobic fitness gains.""",

    "decoupling": """Percent change in Efficiency Factor from 1st to 2nd half.
Formula: (EF 2nd half - EF 1st half) / EF 1st half × 100%

Negative values = EF decreasing (normal fatigue pattern).
Requires 1hr+ steady effort for meaningful analysis.""",

    "cardiac_drift": """Percent increase in heart rate from 1st to 2nd half.
Formula: (HR 2nd half - HR 1st half) / HR 1st half × 100%

Positive values = HR increasing (normal cardiovascular response).
Lower drift indicates better aerobic fitness.""",

    "first_half_hr": """Average heart rate (BPM) during the first half of the ride.
Used to calculate cardiac drift by comparing with second half HR.""",

    "second_half_hr": """Average heart rate (BPM) during the second half of the ride.
Used to calculate cardiac drift by comparing with first half HR.""",

    # ═══════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "fatigue_index": """Power decline from first half to second half.
Formula: (Power 1st - Power 2nd) / Power 1st × 100%

This is the magnitude of power fade.
Lower is better - shows ability to maintain power.""",

    "power_drift": """Percent change in power from 1st to 2nd half.
Formula: (Power 2nd - Power 1st) / Power 1st × 100%

Negative = power decreasing (normal fatigue).
Positive = negative split (building power).""",

    "power_decay": """Rate of power decline during sustained efforts.
Lower values indicate better power sustainability.""",

    "hr_fatigue_index": """Percent HR increase from initial to final 5 minutes.
Lower values indicate better cardiovascular control.""",

    "hr_decay": """Percent HR increase from first to second half.
Lower values indicate better cardiovascular stability.""",

    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING INTENSITY DISTRIBUTION
    # ═══════════════════════════════════════════════════════════════════════
    "polarization_index": """PI = (Z1% + Z3%) / Z2%.
Measures how polarized your training intensity distribution is.
Higher = more polarized (research suggests this is effective for endurance).""",

    "tdr": """Training Distribution Ratio: Z1% / Z3%.
Measures balance between low and high intensity training.""",

    # ═══════════════════════════════════════════════════════════════════════
    # CLIMBING METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "vam": """Velocità Ascensionale Media - vertical ascent rate in meters per hour.
Key metric for comparing climbing performance across different climbs.""",

    "climbing_power": """Average power on gradients >4%.
Shows sustained climbing strength.""",

    "climbing_power_per_kg": """Climbing power divided by body weight (W/kg).
THE key metric for climbing performance.
Allows comparison across athletes of different weights.""",

    # ═══════════════════════════════════════════════════════════════════════
    # ADVANCED POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════
    "negative_split_index": """Ratio of NP 2nd half to NP 1st half.
Values >1.0 indicate building power (negative split).
Values <1.0 indicate fading power.""",

    "match_burn_count": """Number of significant W' expenditures (>50% depletion).
Quantifies hard efforts/attacks during the ride.""",
}


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE DESCRIPTIONS - Non-metric UI concepts
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_DESCRIPTIONS = {
    "workout_type": """Strava's classification of the activity based on metadata:
• Race: Competitive events
• Workout: Structured training sessions
• Long Run/Ride: Extended endurance efforts
• Intervals: High-intensity interval training
• Recovery: Easy regeneration sessions""",

    "training_phase": """Periodization block classification based on volume and intensity trends:
• Base Building: Volume increasing, intensity moderate
• Build Phase: High volume + increasing intensity
• Peak/Race Prep: Volume stable, intensity at maximum
• Taper/Recovery: Volume decreasing
• Transition: Off-season

**Source**: Periodization principles from Bompa & Haff (2009)""",

    "tid": """Training Intensity Distribution - how training is spread across zones:
• Zone 1 (Low): Below aerobic threshold - base building
• Zone 2 (Moderate): Between thresholds - tempo work
• Zone 3 (High): Above lactate threshold - hard intervals

Polarized training targets 80% Z1, minimal Z2, 15-20% Z3.""",

    "tid_classification": """Training type based on intensity distribution:
• Polarized: Z1+Z3 dominant, minimal Z2
• Pyramidal: Z1 > Z2 > Z3
• Threshold: Z2 dominant""",

    "power_curve": """Best power outputs for various durations.
• 5s-30s: Neuromuscular power (sprints)
• 1-5min: Anaerobic capacity (VO2max efforts)
• 20min-1hr: Threshold/FTP power""",

    "gear_usage": """Breakdown of distance, time, and elevation by equipment.
Helps track equipment wear and training distribution across bikes.""",

    "season_phases": """Automatic classification based on CTL trends:
• OFF-SEASON: Low volume recovery
• BASE: Building aerobic foundation
• BUILD: Increasing intensity and volume
• PEAK/RACE: Tapering for performance
• RECOVERY: After hard blocks""",

    "yoy_comparison": """Year-over-year progress comparison.
Compare key metrics against previous year to track long-term trends.""",
}
