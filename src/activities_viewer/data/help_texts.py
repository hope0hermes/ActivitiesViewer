"""Centralized help texts for all dashboard metrics.

This module contains all help text strings used in tooltips across the application.
Organized by category for easy maintenance and updates.
"""

HELP_TEXTS = {
    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING LOAD METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "tss": """**Training Stress Score (TSS)**
Quantifies total training load. Weekly targets:
• 300-400: Maintenance
• 400-600: Building
• 600-800: High load
• 800+: Overreaching risk

Annual targets:
• <3000: Light training year
• 3000-6000: Moderate training year
• 6000-10000: Serious amateur
• >10000: Elite/Professional level training

Single activity reference:
• <150: Low
• 150-300: Medium
• 300-450: High
• >450: Very High""",

    "chronic_training_load": """**Chronic Training Load (CTL)**
42-day exponentially weighted average of daily TSS.
Represents overall 'fitness' and training capacity.
• <50: Building/recovery phase
• 50-80: Moderate training
• 80-120: High performance level
• >120: Elite/peak fitness""",

    "ctl": """**Chronic Training Load (CTL)**
42-day exponentially weighted average of daily TSS.
Represents overall 'fitness' and training capacity.
• <50: Building/recovery phase
• 50-80: Moderate training
• 80-120: High performance level
• >120: Elite/peak fitness""",

    "acute_training_load": """**Acute Training Load (ATL)**
7-day exponentially weighted average of daily TSS.
Represents short-term fatigue/stress.
• <50: Fresh
• 50-100: Normal training
• >100: High fatigue

High ATL relative to CTL indicates overtraining risk.""",

    "atl": """**Acute Training Load (ATL)**
7-day exponentially weighted average of daily TSS.
Represents recent training stress ('fatigue').
• Low ATL = well recovered
• High ATL = accumulated fatigue""",

    "training_stress_balance": """**Training Stress Balance (TSB)**
Form indicator (CTL - ATL). Balance between fitness and fatigue.
• TSB > 20: Very fresh (may lose fitness), good for intensity
• TSB 0-20: Optimal zone for racing/productive training
• TSB -10-0: Productive training zone, elevated fatigue
• TSB -50 to -10: Overreached, recovery needed
• TSB < -10: Overreached, recovery needed""",

    "tsb": """**Training Stress Balance (TSB)**
Form indicator (CTL - ATL).
• TSB > 20: Very fresh, might need more load
• TSB 0-20: Optimal zone for racing
• TSB -10-0: Productive training zone
• TSB < -10: Overreached, recovery needed""",

    "acwr": """**Acute:Chronic Workload Ratio (ACWR)**
Injury risk indicator (ATL ÷ CTL). Sweet spot: 0.8-1.3.
• <0.5: Insufficient training stimulus
• <0.8: Undertraining, might lose fitness
• 0.8-1.3: Sweet spot for adaptation
• 1.3-1.5: Caution zone, monitor recovery
• >1.5: High injury/overtraining risk!""",

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "avg_power": "Time-weighted average power. Moving variant excludes stopped time.",

    "normalized_power": """**Normalized Power (NP)**
Represents the power you could have maintained for the same physiological
cost if output had been constant. Uses 30s rolling average raised to 4th power.
More accurate than average power for variable efforts.""",

    "intensity_factor": """**Intensity Factor (IF)**
IF = NP / FTP. Categorizes workout intensity:
• <0.75: Recovery
• 0.75-0.85: Endurance
• 0.85-0.95: Tempo
• 0.95-1.05: Threshold
• >1.05: VO2max""",

    "variability_index": """**Variability Index (VI)**
VI = NP / Avg Power. Indicates power consistency:
• 1.0-1.02: Very steady (time trial)
• 1.02-1.05: Steady (solo ride)
• 1.05-1.15: Variable (group ride)
• >1.15: Highly variable (crits, surges)""",

    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL POWER MODEL
    # ═══════════════════════════════════════════════════════════════════════════

    "cp": """**Critical Power (CP)**
The boundary between steady-state and non-steady-state exercise.
Maximum power sustainable for extended efforts (>3-10 minutes).
Your aerobic ceiling - higher CP = better endurance capacity.

Computed from 90-day rolling power curve.
• <200W: Beginner
• 200-300W: Fit
• 300-400W: Very fit
• >400W: Elite""",

    "w_prime": """**W' (W-prime)**
Anaerobic work capacity above critical power.
The amount of work you can do above CP before exhaustion.
Depletes during intense efforts, recovers during rest.

Computed from 90-day rolling power curve.
• <15kJ: Low anaerobic capacity
• 15-25kJ: Average
• >25kJ: Strong anaerobic capacity""",

    "cp_r_squared": """**R² (R-squared)**
Goodness of fit for CP model (0-1).
How well the mathematical model fits your power-duration data.
• <0.85: Fair (use estimates cautiously)
• 0.85-0.95: Good (reliable)
• >0.95: Excellent (very reliable)""",

    "r_squared": """**R² (R-squared)**
Goodness of fit for CP model.
How well the mathematical model fits your power data.
• <0.90: Fair (use estimates cautiously)
• 0.90-0.95: Good (reliable)
• >0.95: Excellent (very reliable)""",

    "aei": """**Aerobic Endurance Index (AEI)**
W-prime normalized to body weight (J/kg). Indicates athlete profile type.
Higher = greater anaerobic capacity per kg.
• <0.55: Anaerobic profile
• 0.55-0.70: Balanced
• 0.70-0.85: Aerobic profile
• >0.85: Very aerobic profile (endurance specialist)

Compare over time to track phenotype shifts and anaerobic capacity changes.""",

    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICIENCY METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "efficiency_factor": """**Efficiency Factor (EF)**
Power per heartbeat (NP / Avg HR).
Higher is better - more power for same cardiac effort.
Track over time for similar efforts to monitor aerobic fitness gains.
Trending upward = improving aerobic efficiency.""",

    "ef": """**Efficiency Factor (EF)**
Power produced per heartbeat (NP/Avg HR).
Higher EF = better aerobic efficiency. Improves with fitness.
Track over time to monitor aerobic development.""",

    "avg_ef": """**Average Efficiency Factor**
Average Efficiency Factor across all rides.
Higher values indicate better overall aerobic efficiency.
Rising trend = improving aerobic fitness.""",

    "decoupling": """**Decoupling (Cardiac Drift)**
% change in EF from 1st to 2nd half of activity.
Negative = fatigue/dehydration.
>5% drift indicates aerobic system as limiter.

Requires 1hr+ steady effort for meaningful analysis.
• <3%: Excellent aerobic fitness ✅
• 3-5%: Good fitness ✅
• 5-8%: Moderate drift ⚠️
• >8%: Poor fitness or fatigue 🔴""",

    "avg_decoupling": """**Average Cardiac Drift**
Average cardiac drift across all activities.
Lower values indicate better aerobic fitness.
• <5%: Excellent aerobic fitness ✅
• 5-10%: Good aerobic fitness ➡️
• >10%: May need more Z2 base work ⚠️""",

    "cardiac_drift": """**Cardiac Drift**
(EF 1st half - EF 2nd half) / EF 1st half × 100%.
Aerobic fitness indicator:
• <3%: Excellent aerobic fitness ✅
• 3-5%: Good fitness ✅
• 5-8%: Moderate drift ⚠️
• >8%: Poor fitness or fatigue 🔴""",

    # ═══════════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "fatigue_index": """**Fatigue Index**
% power decline from initial to final 5 minutes:
• 0-5%: Excellent pacing
• 5-15%: Good pacing/endurance
• 15-25%: Moderate fatigue
• >25%: Poor pacing or high fatigue

Lower is better - shows ability to maintain power.""",

    "fatigue_trend": """**Fatigue Trend**
Average fatigue index across activities. Lower is better.
High values (>15%) suggest inadequate recovery or pacing issues.""",

    "power_decay": """**Power Decay**
% power decrease from first to second half:
• <5%: Excellent sustainability
• 5-10%: Good
• 10-20%: Moderate fade
• >20%: Significant decay""",

    "hr_fatigue_index": """**HR Fatigue Index**
% HR increase from initial to final 5 minutes:
• 0-5%: Excellent control
• 5-10%: Good
• 10-20%: Moderate drift
• >20%: Significant drift""",

    "hr_decay": """**HR Decay**
% HR increase from first to second half:
• <5%: Excellent control
• 5-10%: Good
• 10-20%: Moderate drift
• >20%: Significant drift""",

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING INTENSITY DISTRIBUTION (TID)
    # ═══════════════════════════════════════════════════════════════════════════

    "tid": """**Training Intensity Distribution (TID)**
How your training is distributed across intensity zones:
• **Zone 1 (Low)**: Below aerobic threshold - recovery and base building
• **Zone 2 (Moderate)**: Between thresholds - tempo/sweetspot work
• **Zone 3 (High)**: Above lactate threshold - hard intervals

**Polarized training** targets 80% Zone 1, minimal Zone 2, 15-20% Zone 3.
Time spent in each intensity zone. Ideal polarized model:
• 75-80% Low intensity (Z1)
• 5-10% Moderate (Z2)
• 15-20% High (Z3)""",

    "weekly_tid": """**Weekly Training Intensity Distribution**
Training Intensity Distribution across the week. Ideal polarized model:
• 75-80% Low intensity (Z1)
• 5-10% Moderate (Z2)
• 15-20% High (Z3)""",

    "polarization_index": """**Polarization Index (PI)**
PI = (Z1% + Z3%) / Z2%. Measures how polarized your training is.
Higher = more polarized (good for endurance).
• >4.0: Highly polarized (ideal for endurance)
• 2-4: Moderately polarized
• 1.5-2.0: Moderately polarized
• <2: Pyramidal or threshold-focused
• <1.5: Threshold-focused (more Zone 2)

Research suggests polarized training is most effective for endurance.""",

    "tdr": """**Training Distribution Ratio (TDR)**
TDR = Z1% / Z3%.
• >2.0: Polarized training
• 1-2: Balanced
• <1: High-intensity focused""",

    "tid_classification": """**TID Classification**
Training type based on intensity distribution:
• Polarized: Z1+Z3 dominant, minimal Z2
• Pyramidal: Z1 > Z2 > Z3
• Threshold: Z2 dominant""",

    # HR-based TID
    "hr_polarization_index": """**HR-based Polarization Index**
HR-based PI = (Z1% + Z3%) / Z2%. Training intensity distribution:
• >4.0: Highly polarized (ideal for endurance)
• 2-4: Moderately polarized
• <2: Pyramidal or threshold-focused""",

    "hr_tid_z1_percentage": """**HR Zone 1 %**
Percentage of activity in Z1 (Zone 1 - Recovery/Endurance).
HR below aerobic threshold (<80% LTHR).
Higher % indicates emphasis on aerobic base building and recovery.""",

    "hr_tid_z2_percentage": """**HR Zone 2 %**
Percentage of activity in Z2 (Tempo/Threshold).
HR at sustained intensity level (80-100% LTHR).
Used to build aerobic capacity while maintaining conversational pace.""",

    "hr_tid_z3_percentage": """**HR Zone 3 %**
Percentage of activity in Z3 (VO2max/Anaerobic).
HR at high intensity (>100% LTHR).
Short high-intensity efforts for aerobic power and capacity building.""",

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER CURVE & PRs
    # ═══════════════════════════════════════════════════════════════════════════

    "power_curve": """**Power Curve PRs**
Best power outputs for various durations throughout the year.
These represent your peak performance capabilities:
• **5s-30s**: Neuromuscular power (sprints)
• **1-5min**: Anaerobic capacity (VO2max efforts)
• **20min-1hr**: Threshold/FTP power (sustained efforts)""",

    # ═══════════════════════════════════════════════════════════════════════════
    # RECOVERY & READINESS
    # ═══════════════════════════════════════════════════════════════════════════

    "rest_days": """**Rest Days**
Days with no activity or TSS < 20.
Adequate recovery time prevents overtraining and allows adaptation.
• 2+: ✅ Good recovery
• 1: ⚠️ May need more rest
• 0: 🔴 High overtraining risk""",

    "monotony": """**Monotony Index**
Mean daily TSS divided by standard deviation.
Measures training variety. Lower values indicate better variation.
• <1.5: ✅ Good variety
• 1.5-2.0: ⚠️ Moderate risk
• >2.0: 🔴 Too repetitive""",

    "strain": """**Training Strain**
Weekly TSS × Monotony Index.
Combines training load with variation. Higher values = greater stress.
• <3000: ✅ Manageable
• 3000-6000: ⚠️ Moderate
• >6000: 🔴 High strain""",

    # ═══════════════════════════════════════════════════════════════════════════
    # PROGRESSIVE OVERLOAD
    # ═══════════════════════════════════════════════════════════════════════════

    "this_week_tss": """**This Week TSS**
Total Training Stress Score for the current week.
Quantifies overall training load across all activities.""",

    "four_week_avg_tss": """**4-Week Average TSS**
Average weekly TSS over the previous 4 weeks.
Provides baseline for comparing current week's load.""",

    "progression": """**Weekly Progression**
Week-over-week TSS change as percentage.
Optimal progression: 3-10% increase per week.
• +3 to +10%: ✅ Optimal
• +10 to +20%: ⚠️ Monitor recovery
• >+20%: 🔴 High risk
• <-10%: 💤 Recovery week""",

    # ═══════════════════════════════════════════════════════════════════════════
    # INTENSITY-SPECIFIC VOLUME
    # ═══════════════════════════════════════════════════════════════════════════

    "z2_volume": """**Z2 Volume**
Time spent in Zone 2 (56-75% FTP).
Aerobic base building, mitochondrial adaptation.
Target: 60-80% of weekly volume for base phase.""",

    "sweet_spot_time": """**Sweet Spot Time**
Time at 88-94% FTP (Sweet Spot range).
Highly effective for FTP improvement.
Target: 10-20% of weekly volume during build phase.""",

    "vo2max_time": """**VO2max Time**
Time above 90% FTP (VO2max and above).
High intensity training for maximal aerobic power.
Target: 5-10% of weekly volume.""",

    "time_above_90_ftp": """**Time Above 90% FTP**
Seconds above 90% FTP (VO2max zone). High-intensity training stimulus:
• 0-5 min: Easy/recovery
• 5-15 min: Moderate stimulus
• 15-30 min: Significant workout
• >30 min: Hard VO2max session""",

    # ═══════════════════════════════════════════════════════════════════════════
    # FTP & FITNESS EVOLUTION
    # ═══════════════════════════════════════════════════════════════════════════

    "ftp_trajectory": """**FTP Evolution**
Track estimated FTP changes throughout the year.
Upward trend indicates improving fitness.
Monthly averages smooth out daily fluctuations.""",

    "ftp_start": """**FTP Start**
Estimated FTP at the beginning of the month.
Based on power duration curve analysis from recent activities.""",

    "ftp_end": """**FTP End**
Estimated FTP at the end of the month.
Based on power duration curve analysis from recent activities.""",

    "ftp_change": """**FTP Change**
Change in estimated FTP over the month.
• Positive: Fitness improvement ✅
• Negative: May need recovery or training adjustment ⚠️
• Stable (±2W): Maintenance phase ➡️""",

    "peak_metrics": """**Peak Performance Metrics**
Highest values achieved during the year.
Peak FTP, CTL, and W/kg indicate best fitness state.""",

    "estimated_ftp": """**Estimated FTP**
FTP estimate from best 20-min power × 0.95. Track progression:
• Compare to configured FTP
• Rising estimates = improving fitness
• Requires rides >20 minutes with sustained effort""",

    # ═══════════════════════════════════════════════════════════════════════════
    # PERIODIZATION & TRAINING PHASES
    # ═══════════════════════════════════════════════════════════════════════════

    "season_phases": """**Season Phase Detection**
Automatic classification based on CTL trends and intensity:
• OFF-SEASON: Low volume recovery period
• BASE: Building aerobic foundation (low IF)
• BUILD: Increasing intensity and volume
• PEAK/RACE: Tapering for peak performance
• RECOVERY: Active recovery after hard blocks
• TRANSITION: Between defined phases""",

    "volume_vs_avg": """**Volume vs Average**
Monthly training volume compared to 3-month rolling average.
• +10% or more: High volume block 📈
• -10% or less: Recovery/taper block 📉
• ±10%: Maintenance ➡️""",

    "intensity_vs_avg": """**Intensity vs Average**
Average ride intensity (IF) compared to 3-month rolling average.
• Higher: BUILD/PEAK phase (harder efforts) ⚡
• Lower: BASE phase (endurance focus) 🏗️
• Similar: Maintenance ➡️""",

    "long_rides": """**Long Rides**
Number of rides longer than 3 hours.
Critical for endurance development and aerobic capacity.
Target: 1-2 per week during base phase.""",

    # ═══════════════════════════════════════════════════════════════════════════
    # AEROBIC DEVELOPMENT
    # ═══════════════════════════════════════════════════════════════════════════

    "ef_trend": """**EF Trend**
Weekly rate of change in Efficiency Factor.
Positive trend = improving aerobic efficiency ✅
• >0.02/week: Significant improvement
• 0-0.02/week: Gradual improvement
• <0: May need more Z2 volume or recovery""",

    "decoupling_trend": """**Decoupling Trend**
Weekly rate of change in cardiac drift.
Negative trend (decreasing drift) = improving aerobic fitness ✅
• <-0.2%/week: Significant improvement
• -0.2 to 0: Gradual improvement
• >0: Increasing fatigue or deconditioning""",

    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING CONSISTENCY
    # ═══════════════════════════════════════════════════════════════════════════

    "training_days": """**Training Days**
Number of days with at least one activity.
Higher consistency = better adaptation and fitness gains.
• 70%+: Excellent consistency ✅
• 50-70%: Good consistency ➡️
• <50%: Consider improving consistency ⚠️""",

    "longest_streak": """**Longest Streak**
Longest run of consecutive training days.
Very long streaks (>14 days) may indicate need for rest days.""",

    "longest_gap": """**Longest Gap**
Longest period without training.
• 1-3 days: Normal recovery ✅
• 4-7 days: Planned rest week ➡️
• >7 days: Extended break (illness, vacation, etc.) ⚠️""",

    # ═══════════════════════════════════════════════════════════════════════════
    # YEAR-OVER-YEAR & STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    "yoy_comparison": """**Year-over-Year Progress**
Compare key metrics against previous year.
Positive trends indicate consistent improvement.""",

    "total_hours": """**Total Training Hours**
Total training time for the year.
• Elite cyclists: 500-800h/year
• Serious amateurs: 300-500h/year
• Recreational: <300h/year""",

    "biggest_week": """**Biggest Week**
Week with highest training volume.
Useful for tracking peak training blocks.""",

    "highest_np": """**Highest NP**
Highest normalized power for any single activity.
Indicates peak sustained power output capability.""",

    # ═══════════════════════════════════════════════════════════════════════════
    # RISK ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    "high_acwr_weeks": """**High ACWR Weeks**
Weeks with Acute:Chronic Workload Ratio > 1.5.
High ACWR increases injury risk.
Target: Keep ACWR between 0.8-1.3""",

    "longest_break": """**Longest Break**
Longest consecutive period without training.
• 1-3 days: Normal recovery
• 4-7 days: Planned rest week
• >7 days: Extended break (illness, vacation, etc.)""",

    # ═══════════════════════════════════════════════════════════════════════════
    # GEAR & EQUIPMENT
    # ═══════════════════════════════════════════════════════════════════════════

    "gear_usage": """**Gear Usage Statistics**
Breakdown of distance, time, and elevation by equipment.
Helps track:
• Equipment wear and maintenance needs
• Training distribution across bikes
• Preferred equipment for different activities""",

    # ═══════════════════════════════════════════════════════════════════════════
    # ADVANCED POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "negative_split_index": """**Negative Split Index**
NP 2nd half / NP 1st half. Pacing analysis:
• >1.05: Negative split (building power) ✅
• 0.95-1.05: Even pacing ✅
• 0.85-0.95: Slight fade ⚠️
• <0.85: Significant fade 🔴""",

    "match_burn_count": """**Match Burn Count**
Number of significant W' expenditures (>50% depletion).
Quantifies hard efforts/attacks:
• 0-2: Steady ride
• 3-5: Typical interval workout
• 6-10: Dynamic group ride
• >10: Criterium racing""",

    # ═══════════════════════════════════════════════════════════════════════════
    # CLIMBING METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "vam": """**VAM (Velocità Ascensionale Media)**
Vertical ascent rate (m/h):
• <800 m/h: Recreational
• 800-1000 m/h: Strong amateur
• 1000-1200 m/h: Cat 2-3 racer
• 1200-1400 m/h: Cat 1/Pro domestic
• >1600 m/h: World Tour climber""",

    "climbing_time": """**Climbing Time**
Seconds spent on positive gradients.
Shows climbing volume in the ride.""",

    "climbing_power": """**Climbing Power**
Average power on gradients >4%.
Shows sustained climbing strength.""",

    "climbing_power_per_kg": """**Climbing W/kg**
Climbing power / weight (W/kg). THE key metric for climbing:
• <3.0 W/kg: Recreational
• 3.0-3.5 W/kg: Strong amateur
• 3.5-4.0 W/kg: Cat 2-3 racer
• 4.0-4.5 W/kg: Cat 1/Pro domestic
• >5.5 W/kg: World Tour climber""",

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERVAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    "interval_300s_decay_rate": """**300s Interval Decay Rate**
% power decline across 300s intervals during the ride.
Indicator of power sustainability:
• <5%: Excellent power maintenance
• 5-15%: Good power sustainability
• 15-25%: Moderate power drop
• >25%: Significant fatigue/power loss""",

    "interval_300s_power_trend": """**300s Interval Power Trend**
Average change in power per 300s interval (W/interval).
Trend direction:
• Positive: Building power across workout
• Negative: Declining power (fatigue accumulating)
• Near zero: Stable power throughout""",

    # ═══════════════════════════════════════════════════════════════════════════
    # BASIC METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    "average_hr": "Time-weighted average heart rate during activity.",
    "max_hr": "Maximum heart rate recorded during the activity.",
    "average_cadence": "Average pedal cadence (RPM). Indicates pedaling efficiency and style.",
    "kilojoules": "Total energy expended during activity. Based on power and duration.",
    "moving_time": "Total time the bike was in motion (excludes stopped time).",
    "elapsed_time": "Total time from activity start to finish (includes stops).",
}


def get_help_text(key: str, fallback: str = "") -> str:
    """Get help text by key with optional fallback.

    Args:
        key: The metric key to look up
        fallback: Default text to return if key not found

    Returns:
        Help text string for the metric, or fallback if not found
    """
    return HELP_TEXTS.get(key, fallback)
