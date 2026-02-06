"""Centralized help texts for all dashboard metrics.

This module provides:
- METRICS_METADATA: Structured metadata with thresholds (SINGLE SOURCE OF TRUTH)
- BASE_DESCRIPTIONS: Pure prose descriptions (imported from metric_descriptions)
- HELP_TEXTS: Legacy help texts (retained for non-metric features)
- get_help_text(): Generates dynamic help text combining description + thresholds

ARCHITECTURE:
- Thresholds are ONLY defined in METRICS_METADATA (structured data)
- Descriptions are pure prose in BASE_DESCRIPTIONS (no threshold bullets)
- get_help_text() generates complete help text dynamically
"""

from .metric_descriptions import BASE_DESCRIPTIONS, FEATURE_DESCRIPTIONS


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY HELP_TEXTS - Retained for backwards compatibility
# Most of these will be phased out as metrics migrate to BASE_DESCRIPTIONS
# ═══════════════════════════════════════════════════════════════════════════

HELP_TEXTS = {
    # ═══════════════════════════════════════════════════════════════════════════
    # TRAINING LOAD METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    "tss": """**Training Stress Score (TSS)**
Quantifies training load based on duration and intensity.
TSS = (Duration × NP × IF) / (FTP × 3600) × 100

**Single activity interpretation:**
• <50: Recovery/easy ride
• 50-100: Moderate workout (typical 1hr quality session)
• 100-150: Hard workout (extended threshold work)
• 150-250: Very hard (long race or intense session)
• >250: Epic effort (gran fondo, multi-hour race)

**Weekly targets:**
• 300-400: Maintenance
• 400-600: Building
• 600-800: High load
• >800: Overreaching risk

**Reference**: 1hr at FTP (IF=1.0) = TSS 100""",
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
Represents short-term fatigue/stress.
• <50: Fresh
• 50-100: Normal training
• >100: High fatigue

High ATL relative to CTL indicates overtraining risk.""",
    "training_stress_balance": """**Training Stress Balance (TSB)**
Form indicator (CTL - ATL). Balance between fitness and fatigue.
• TSB > 25: Very fresh (may lose fitness)
• TSB 10-25: Fresh, ready for hard work or racing
• TSB 0-10: Optimal for productive training
• TSB -10 to 0: Productive training, moderate fatigue
• TSB -30 to -10: Overreached, need recovery
• TSB < -30: Severely overreached, rest required""",
    "tsb": """**Training Stress Balance (TSB)**
Form indicator (CTL - ATL). Balance between fitness and fatigue.
• TSB > 25: Very fresh (may lose fitness)
• TSB 10-25: Fresh, ready for hard work or racing
• TSB 0-10: Optimal for productive training
• TSB -10 to 0: Productive training, moderate fatigue
• TSB -30 to -10: Overreached, need recovery
• TSB < -30: Severely overreached, rest required""",
    "acwr": """**Acute:Chronic Workload Ratio (ACWR)**
Injury risk indicator (ATL ÷ CTL). Sweet spot: 0.8-1.3.
• <0.5: Insufficient training stimulus
• <0.8: Undertraining, might lose fitness
• 0.8-1.3: Sweet spot for adaptation
• 1.3-1.5: Caution zone, monitor recovery
• >1.5: High injury/overtraining risk!""",
    # Recovery & Overtraining Metrics (NEW - Phase 5.5)
    "monotony_index": """**Monotony Index**
Daily TSS variability measure (mean TSS ÷ standard deviation).
Indicates training variety/repetitiveness:
• <1.5: ✅ Safe - Good training variety
• 1.5-2.0: ⚠️ Monitor - Moderate overtraining risk
• >2.0: 🔴 High risk - Training too repetitive

High monotony combined with high volume increases injury/burnout risk.

**Source**: Foster (1998), Monitoring training in athletes with reference to overtraining syndrome.""",
    "strain_index": """**Strain Index**
Weekly TSS × Monotony Index. Combines total load with training variety.
Quantifies overall training stress risk:
• <3000: ✅ Manageable load
• 3000-6000: ⚠️ Moderate strain - Monitor recovery
• >6000: 🔴 High strain - Prioritize recovery

Lower strain allows for better adaptation and reduced injury risk.

**Source**: Foster (1998), Monitoring training in athletes with reference to overtraining syndrome.""",
    "rest_days": """**Rest Days**
Number of days with TSS < 20 (minimal training stress).
Adequate recovery is essential for adaptation:
• 2+ days/week: ✅ Adequate for most athletes
• 1 day/week: ⚠️ May need more depending on intensity
• 0 days/week: 🔴 Critical - Recovery day needed immediately

Elite athletes may need fewer rest days but require careful monitoring.""",
    # Workout Classification & Periodization (NEW - Phase 5.6)
    "workout_type": """**Workout Type**
Strava's classification of the activity based on metadata and tags:
• Race: Competitive events (highest intensity)
• Workout: Structured training sessions
• Long Run/Ride: Extended endurance efforts
• Intervals: High-intensity interval training
• Recovery: Easy regeneration sessions

Tracking workout type distribution helps ensure training variety.""",
    "training_phase": """**Training Phase**
Periodization block classification based on volume and intensity trends:
• **Base Building**: Volume increasing, intensity moderate (Z2 focus)
• **Build Phase**: High volume + increasing intensity (threshold work)
• **Peak/Race Prep**: Volume stable/high, intensity at maximum
• **Taper/Recovery**: Volume decreasing, intensity maintained/reduced
• **Transition**: Low volume and intensity (off-season)

Proper periodization cycles stress → adaptation → rest for optimal gains.

**Source**: Periodization principles from Bompa & Haff (2009).""",
    "periodization_check": """**Periodization Check**
Automated training phase detection using volume and intensity metrics.
Compares current period to previous period to identify phase:
• Volume up + Intensity stable = Base Building
• Volume stable + Intensity up = Build/Intensity
• Volume down = Taper/Recovery

Helps ensure your training follows sound periodization principles.""",
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

Note: Absolute watts vary by body weight. W/kg is more
useful for comparing climbing/racing ability.
• <3.0 W/kg: Recreational
• 3.0-3.5 W/kg: Fit amateur
• 3.5-4.0 W/kg: Strong amateur
• 4.0-5.0 W/kg: Cat 1-3 racer
• >5.0 W/kg: Elite/Pro""",
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
    "aei": """**Anaerobic Energy Index (AEI)**
W' (anaerobic capacity) normalized to body weight (kJ/kg).
Higher = greater anaerobic capacity per kg of body weight.
• <0.15: Very low anaerobic capacity
• 0.15-0.25: Low to moderate
• 0.25-0.35: Moderate to high
• >0.35: High anaerobic capacity

Track over time to monitor changes in anaerobic work capacity.
Higher values indicate greater ability to perform high-intensity efforts.""",
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
    "decoupling": """**Power:HR Decoupling**
Percent change in Efficiency Factor (power/HR ratio) from 1st to 2nd half.
Formula: (EF 2nd half - EF 1st half) / EF 1st half × 100%

Negative values = EF decreasing (power dropping relative to HR - normal fatigue).
Positive values = EF improving (rare, indicates warm-up effect).

This is different from cardiac drift which only tracks HR changes.
Requires 1hr+ steady effort for meaningful analysis.
• > -3%: Excellent aerobic fitness ✅
• -3% to -5%: Good fitness ✅
• -5% to -8%: Moderate drift ⚠️
• < -8%: Poor fitness or fatigue 🔴""",
    # Alias for power_hr_decoupling field name
    "power_hr_decoupling": """**Power:HR Decoupling**
Percent change in Efficiency Factor (power/HR ratio) from 1st to 2nd half.
Formula: (EF 2nd half - EF 1st half) / EF 1st half × 100%

Negative values = EF decreasing (power dropping relative to HR - normal fatigue).
Positive values = EF improving (rare, indicates warm-up effect).

This is different from cardiac drift which only tracks HR changes.
Requires 1hr+ steady effort for meaningful analysis.
• > -3%: Excellent aerobic fitness ✅
• -3% to -5%: Good fitness ✅
• -5% to -8%: Moderate drift ⚠️
• < -8%: Poor fitness or fatigue 🔴""",
    "avg_decoupling": """**Average Power:HR Decoupling**
Average decoupling across all activities.
Values closer to 0% (less negative) indicate better aerobic fitness.
Most values will be negative due to natural fatigue accumulation during efforts.
• > -5%: Excellent aerobic fitness ✅
• -5% to -10%: Good aerobic fitness ➡️
• < -10%: May need more Z2 base work ⚠️""",
    "cardiac_drift": """**Cardiac Drift**
Percent increase in heart rate from 1st to 2nd half (HR-only metric).
Formula: (HR 2nd half - HR 1st half) / HR 1st half × 100%

Positive values = HR increasing (cardiovascular strain/dehydration - normal).
Negative values = HR decreasing (rare, warm-up effect).

This is different from decoupling which tracks power/HR ratio changes.
• < 3%: Excellent aerobic fitness ✅
• 3-5%: Good fitness ✅
• 5-8%: Moderate drift ⚠️
• > 8%: Poor fitness or dehydration/heat stress 🔴""",
    "first_half_hr": """**First Half Heart Rate**
Average heart rate (BPM) during the first half of the ride.
Used to calculate cardiac drift by comparing with second half HR.""",
    "second_half_hr": """**Second Half Heart Rate**
Average heart rate (BPM) during the second half of the ride.
Used to calculate cardiac drift by comparing with first half HR.""",
    # ═══════════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    "fatigue_index": """**Fatigue Index**
Power decline from first half to second half (magnitude of power loss).
Formula: (Power 1st half - Power 2nd half) / Power 1st half × 100%

This is the absolute value of power drift, showing magnitude of power fade:
• 0-5%: Excellent pacing ✅
• 5-15%: Good pacing/endurance ✅
• 15-25%: Moderate fatigue ⚠️
• >25%: Poor pacing or high fatigue 🔴

Lower is better - shows ability to maintain power.""",
    "fatigue_trend": """**Fatigue Trend**
Average fatigue index across activities. Lower is better.
High values (>15%) suggest inadequate recovery or pacing issues.""",
    "power_drift": """**Power Drift**
Percent change in power from 1st to 2nd half (power-only metric).
Formula: (Power 2nd half - Power 1st half) / Power 1st half × 100%

Negative values = power decreasing (normal fatigue).
Positive values = negative split (building power throughout ride).

• >-5%: Excellent sustainability ✅
• -5% to -10%: Good pacing ✅
• -10% to -15%: Moderate fade ⚠️
• <-15%: Significant fade 🔴""",
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
• 2.0-4.0: Moderately polarized
• 1.5-2.0: Slightly polarized / pyramidal
• <1.5: Threshold-focused (heavy Zone 2)

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
Harder effort - breathing is labored, conversation difficult.""",
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
    "average_power": "Time-weighted average power output (watts) during the activity.",
    "average_speed": "Average speed during the activity (km/h or mph).",
    "distance": "Total distance covered during the activity.",
    "total_elevation_gain": "Total meters climbed during the activity.",
    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICIENCY HALF METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    "first_half_ef": """**First Half Efficiency Factor**
Efficiency Factor (NP/HR) during the first half of the ride.
Used to calculate decoupling by comparing with second half EF.
Higher values indicate better power output per heartbeat.""",
    "second_half_ef": """**Second Half Efficiency Factor**
Efficiency Factor (NP/HR) during the second half of the ride.
Used to calculate decoupling by comparing with first half EF.
Lower than first half indicates normal fatigue/drift.""",
    # ═══════════════════════════════════════════════════════════════════════════
    # HR-BASED TRAINING STRESS
    # ═══════════════════════════════════════════════════════════════════════════
    "hr_training_stress": """**HR Training Stress (hrTSS)**
Heart rate-based training stress score.
Uses heart rate zones when power data is unavailable.
Comparable to TSS but derived from HR instead of power.""",
    "training_stress_score": """**Training Stress Score (TSS)**
Quantifies training load for this activity.
TSS = (Duration × NP × IF) / (FTP × 3600) × 100

• <50: Recovery/easy ride
• 50-100: Moderate workout (typical 1hr quality session)
• 100-150: Hard workout
• 150-250: Very hard effort
• >250: Epic effort

**Reference**: 1hr at FTP (IF=1.0) = TSS 100""",
    # ═══════════════════════════════════════════════════════════════════════════
    # W' BALANCE METRICS
    # ═══════════════════════════════════════════════════════════════════════════
    "w_prime_balance_min": """**W' Balance Minimum**
Lowest W' balance reached during the ride (kJ).
Shows how deeply you dipped into anaerobic reserves.
Lower values = harder efforts above CP.""",
    "w_prime_depletion": """**W' Depletion**
Maximum percentage of W' used during the ride.
• <50%: Conservative effort above CP
• 50-75%: Moderate anaerobic work
• 75-90%: Hard effort, significant W' use
• >90%: Near-maximal effort, full depletion""",
    "power_decay": """**Power Decay Rate**
Rate of power decline during sustained efforts.
Lower values indicate better power sustainability.
• <5%: Excellent sustainability
• 5-10%: Good sustainability
• >10%: Significant decay""",
}


# ═══════════════════════════════════════════════════════════════════════════
# METRICS METADATA - Comprehensive structured data for all metrics
# ═══════════════════════════════════════════════════════════════════════════

METRICS_METADATA = {
    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING LOAD METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "tss": {
        "name": "Training Stress Score",
        "short_name": "TSS",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("tss", ""),
        "thresholds": {
            "single_activity": [
                (50, "🟢", "Recovery/Easy"),
                (100, "🟡", "Moderate"),
                (150, "🟠", "Hard"),
                (250, "🔴", "Very Hard"),
                (float('inf'), "🔴", "Epic"),
            ],
            "weekly": [
                (400, "🟡", "Maintenance"),
                (600, "🟢", "Building"),
                (800, "🟠", "High Load"),
                (float('inf'), "🔴", "Overreaching"),
            ],
            "annual": [
                (3000, "🟡", "Light"),
                (6000, "🟢", "Moderate"),
                (10000, "🟠", "Serious"),
                (float('inf'), "🔴", "Elite/Pro"),
            ],
        },
        "format": "{:.0f}",
        "higher_is_better": None,  # Context-dependent
    },

    "ctl": {
        "name": "Chronic Training Load",
        "short_name": "CTL",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("ctl", ""),
        "thresholds": [
            (50, "🟡", "Building/Recovery"),
            (80, "🟢", "Moderate"),
            (120, "🟠", "High Performance"),
            (float('inf'), "🔴", "Elite/Peak"),
        ],
        "format": "{:.1f}",
        "higher_is_better": True,
    },

    "atl": {
        "name": "Acute Training Load",
        "short_name": "ATL",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("atl", ""),
        "thresholds": [
            (50, "🟢", "Fresh"),
            (100, "🟡", "Normal"),
            (float('inf'), "🔴", "High Fatigue"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "tsb": {
        "name": "Training Stress Balance",
        "short_name": "TSB",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("tsb", ""),
        "thresholds": [
            (-50, "🔴", "Critical"),
            (-10, "🟠", "Overreached"),
            (0, "🟡", "Productive"),
            (20, "🟢", "Optimal"),
            (float('inf'), "🔵", "Very Fresh"),
        ],
        "format": "{:.0f}",
        "higher_is_better": None,  # Sweet spot is 0-20
    },

    "acwr": {
        "name": "Acute:Chronic Workload Ratio",
        "short_name": "ACWR",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("acwr", ""),
        "thresholds": [
            (0.5, "🔴", "Too Low"),
            (0.8, "🟠", "Undertraining"),
            (1.3, "🟢", "Sweet Spot"),
            (1.5, "🟡", "Caution"),
            (float('inf'), "🔴", "High Risk"),
        ],
        "format": "{:.2f}",
        "higher_is_better": None,  # Sweet spot is 0.8-1.3
    },

    "monotony_index": {
        "name": "Monotony Index",
        "short_name": "Monotony",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("monotony_index", ""),
        "thresholds": [
            (1.5, "🟢", "Safe"),
            (2.0, "🟡", "Monitor"),
            (float('inf'), "🔴", "High Risk"),
        ],
        "format": "{:.2f}",
        "higher_is_better": False,
    },

    "strain_index": {
        "name": "Strain Index",
        "short_name": "Strain",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("strain_index", ""),
        "thresholds": [
            (3000, "🟢", "Manageable"),
            (6000, "🟡", "Moderate"),
            (float('inf'), "🔴", "High Strain"),
        ],
        "format": "{:.0f}",
        "higher_is_better": False,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # POWER METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "normalized_power": {
        "name": "Normalized Power",
        "short_name": "NP",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("normalized_power", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "intensity_factor": {
        "name": "Intensity Factor",
        "short_name": "IF",
        "unit": None,
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("intensity_factor", ""),
        "thresholds": [
            (0.75, "🟢", "Recovery"),
            (0.85, "🟡", "Endurance"),
            (0.95, "🟠", "Tempo"),
            (1.05, "🔴", "Threshold"),
            (float('inf'), "🔴", "VO2max"),
        ],
        "format": "{:.2f}",
        "higher_is_better": None,  # Context-dependent
    },

    "variability_index": {
        "name": "Variability Index",
        "short_name": "VI",
        "unit": None,
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("variability_index", ""),
        "thresholds": [
            (1.02, "🟢", "Very Steady"),
            (1.05, "🟢", "Steady"),
            (1.15, "🟡", "Variable"),
            (float('inf'), "🟠", "Highly Variable"),
        ],
        "format": "{:.2f}",
        "higher_is_better": False,
    },

    "cp": {
        "name": "Critical Power",
        "short_name": "CP",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("cp", ""),
        "thresholds": None,  # Absolute watts vary by body weight - use W/kg instead
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "w_prime": {
        "name": "W-prime",
        "short_name": "W'",
        "unit": "J",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("w_prime", ""),
        "thresholds": [
            (15000, "🟡", "Low"),
            (25000, "🟢", "Average"),
            (float('inf'), "🟠", "Strong"),
        ],
        "format": "{:,.0f}",
        "higher_is_better": True,
    },

    "w_prime_depletion": {
        "name": "W' Depletion",
        "short_name": "W' Depletion",
        "unit": "%",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("w_prime_depletion", ""),
        "thresholds": [
            (50, "🟢", "Conservative"),
            (75, "🟡", "Moderate"),
            (90, "🟠", "Hard"),
            (float('inf'), "🔴", "Near-maximal"),
        ],
        "format": "{:.0f}",
        "higher_is_better": False,
    },

    "cp_r_squared": {
        "name": "R-squared",
        "short_name": "R²",
        "unit": None,
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("cp_r_squared", ""),
        "thresholds": [
            (0.85, "🟡", "Fair"),
            (0.95, "🟢", "Good"),
            (float('inf'), "🟠", "Excellent"),
        ],
        "format": "{:.3f}",
        "higher_is_better": True,
    },

    "aei": {
        "name": "Anaerobic Energy Index",
        "short_name": "AEI",
        "unit": "kJ/kg",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("aei", ""),
        "thresholds": [
            (0.15, "🟡", "Low"),
            (0.25, "🟢", "Moderate"),
            (0.35, "🟠", "High"),
            (float('inf'), "🔴", "Very High"),
        ],
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CARDIAC METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "ef": {
        "name": "Efficiency Factor",
        "short_name": "EF",
        "unit": "W/bpm",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("ef", ""),
        "thresholds": None,  # Relative to individual baseline
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    "decoupling": {
        "name": "Power:HR Decoupling",
        "short_name": "Decoupling",
        "unit": "%",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("decoupling", ""),
        "thresholds": [
            (-3, "🟢", "Excellent"),        # value >= -3: Excellent
            (-5, "🟡", "Good"),              # -5 <= value < -3: Good
            (-8, "🟠", "Moderate"),          # -8 <= value < -5: Moderate
            (-float('inf'), "🔴", "Poor/Fatigued"),  # value < -8: Poor
        ],
        "format": "{:.1f}",
        "higher_is_better": True,  # Less negative is better
    },

    "cardiac_drift": {
        "name": "Cardiac Drift",
        "short_name": "Drift",
        "unit": "%",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("cardiac_drift", ""),
        "thresholds": [
            (3, "🟢", "Excellent"),        # value < 3: Excellent
            (5, "🟡", "Good"),              # 3 <= value < 5: Good
            (8, "🟠", "Moderate"),          # 5 <= value < 8: Moderate
            (float('inf'), "🔴", "Poor/Dehydrated"),  # value >= 8: Poor
        ],
        "format": "{:.1f}",
        "higher_is_better": False,  # Lower drift is better (less HR increase)
    },

    "first_half_hr": {
        "name": "First Half HR",
        "short_name": "1st HR",
        "unit": "BPM",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("first_half_hr", ""),
        "format": "{:.0f}",
    },

    "second_half_hr": {
        "name": "Second Half HR",
        "short_name": "2nd HR",
        "unit": "BPM",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("second_half_hr", ""),
        "format": "{:.0f}",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FATIGUE & DURABILITY METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "fatigue_index": {
        "name": "Fatigue Index",
        "short_name": "Fatigue",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("fatigue_index", ""),
        "thresholds": [
            (5, "🟢", "Excellent"),
            (15, "🟡", "Good"),
            (25, "🟠", "Moderate"),
            (float('inf'), "🔴", "Poor"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "power_decay": {
        "name": "Power Decay",
        "short_name": "Decay",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("power_decay", ""),
        "thresholds": [
            (5, "🟢", "Excellent"),
            (10, "🟡", "Good"),
            (20, "🟠", "Moderate"),
            (float('inf'), "🔴", "Significant"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "power_drift": {
        "name": "Power Drift",
        "short_name": "Power Drift",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("power_drift", ""),
        "thresholds": [
            (-5, "🟢", "Excellent"),        # value >= -5: Excellent
            (-10, "🟡", "Good"),             # -10 <= value < -5: Good
            (-15, "🟠", "Moderate"),        # -15 <= value < -10: Moderate
            (-float('inf'), "🔴", "Poor/Fading"),  # value < -15: Poor
        ],
        "format": "{:.1f}",
        "higher_is_better": True,  # Less negative is better
    },

    "hr_fatigue_index": {
        "name": "HR Fatigue Index",
        "short_name": "HR Fatigue",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("hr_fatigue_index", ""),
        "thresholds": [
            (5, "🟢", "Excellent"),
            (10, "🟡", "Good"),
            (20, "🟠", "Moderate"),
            (float('inf'), "🔴", "Significant"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "hr_decay": {
        "name": "HR Decay",
        "short_name": "HR Decay",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("hr_decay", ""),
        "thresholds": [
            (5, "🟢", "Excellent"),
            (10, "🟡", "Good"),
            (20, "🟠", "Moderate"),
            (float('inf'), "🔴", "Significant"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # TRAINING INTENSITY DISTRIBUTION
    # ═══════════════════════════════════════════════════════════════════════

    "polarization_index": {
        "name": "Polarization Index",
        "short_name": "PI",
        "unit": None,
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("polarization_index", ""),
        "thresholds": [
            (1.5, "🟡", "Threshold-focused"),
            (2.0, "🟠", "Pyramidal"),
            (4.0, "🟢", "Moderately Polarized"),
            (float('inf'), "🟢", "Highly Polarized"),
        ],
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    "tdr": {
        "name": "Training Distribution Ratio",
        "short_name": "TDR",
        "unit": None,
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("tdr", ""),
        "thresholds": [
            (1, "🟡", "High-intensity"),
            (2, "🟢", "Balanced"),
            (float('inf'), "🟠", "Polarized"),
        ],
        "format": "{:.2f}",
        "higher_is_better": None,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PACING METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "negative_split_index": {
        "name": "Negative Split Index",
        "short_name": "NSI",
        "unit": None,
        "category": "pacing",
        "base_description": BASE_DESCRIPTIONS.get("negative_split_index", ""),
        "thresholds": [
            (0.85, "🔴", "Significant Fade"),
            (0.95, "🟠", "Slight Fade"),
            (1.05, "🟢", "Even Pacing"),
            (float('inf'), "🟢", "Negative Split"),
        ],
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CLIMBING METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "vam": {
        "name": "VAM",
        "short_name": "VAM",
        "unit": "m/h",
        "category": "climbing",
        "base_description": BASE_DESCRIPTIONS.get("vam", ""),
        "thresholds": [
            (800, "🟡", "Recreational"),
            (1000, "🟢", "Strong Amateur"),
            (1200, "🟠", "Cat 2-3"),
            (1400, "🔴", "Cat 1/Pro"),
            (1600, "🔴", "World Tour"),
        ],
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "climbing_power_per_kg": {
        "name": "Climbing W/kg",
        "short_name": "Climb W/kg",
        "unit": "W/kg",
        "category": "climbing",
        "base_description": BASE_DESCRIPTIONS.get("climbing_power_per_kg", ""),
        "thresholds": [
            (3.0, "🟡", "Recreational"),
            (3.5, "🟢", "Strong Amateur"),
            (4.0, "🟠", "Cat 2-3"),
            (4.5, "🔴", "Cat 1/Pro"),
            (5.5, "🔴", "World Tour"),
        ],
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # RECOVERY METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "rest_days": {
        "name": "Rest Days",
        "short_name": "Rest",
        "unit": "days",
        "category": "recovery",
        "base_description": BASE_DESCRIPTIONS.get("rest_days", ""),
        "thresholds": [
            (0, "🔴", "No Rest"),
            (1, "🟡", "May Need More"),
            (float('inf'), "🟢", "Good Recovery"),
        ],
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PROGRESSION METRICS
    # ═══════════════════════════════════════════════════════════════════════

    "progression": {
        "name": "Weekly Progression",
        "short_name": "Progression",
        "unit": "%",
        "category": "progression",
        "base_description": BASE_DESCRIPTIONS.get("progression", ""),
        "thresholds": [
            (-10, "🔵", "Recovery Week"),
            (3, "🟡", "Low"),
            (10, "🟢", "Optimal"),
            (20, "🟡", "Monitor"),
            (float('inf'), "🔴", "High Risk"),
        ],
        "format": "{:+.0f}",
        "higher_is_better": None,  # Sweet spot 3-10%
    },

    # ═══════════════════════════════════════════════════════════════════════
    # BASIC METRICS (no thresholds)
    # ═══════════════════════════════════════════════════════════════════════

    "average_power": {
        "name": "Average Power",
        "short_name": "Avg Power",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("avg_power", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "average_hr": {
        "name": "Average Heart Rate",
        "short_name": "Avg HR",
        "unit": "bpm",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("average_hr", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "max_hr": {
        "name": "Maximum Heart Rate",
        "short_name": "Max HR",
        "unit": "bpm",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("max_hr", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "average_cadence": {
        "name": "Average Cadence",
        "short_name": "Avg Cadence",
        "unit": "rpm",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("average_cadence", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "kilojoules": {
        "name": "Energy Expended",
        "short_name": "kJ",
        "unit": "kJ",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("kilojoules", ""),
        "thresholds": None,
        "format": "{:,.0f}",
        "higher_is_better": None,
    },

    "moving_time": {
        "name": "Moving Time",
        "short_name": "Moving",
        "unit": "seconds",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("moving_time", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "elapsed_time": {
        "name": "Elapsed Time",
        "short_name": "Elapsed",
        "unit": "seconds",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("elapsed_time", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CLIMBING METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "climbing_power": {
        "name": "Climbing Power",
        "short_name": "Climb Pwr",
        "unit": "W",
        "category": "climbing",
        "base_description": BASE_DESCRIPTIONS.get("climbing_power", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "climbing_time": {
        "name": "Climbing Time",
        "short_name": "Climb Time",
        "unit": "seconds",
        "category": "climbing",
        "base_description": BASE_DESCRIPTIONS.get("climbing_time", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FTP & PROGRESSION METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "estimated_ftp": {
        "name": "Estimated FTP",
        "short_name": "Est FTP",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("estimated_ftp", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "ftp_start": {
        "name": "FTP Start",
        "short_name": "FTP Start",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("ftp_start", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "ftp_end": {
        "name": "FTP End",
        "short_name": "FTP End",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("ftp_end", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "ftp_change": {
        "name": "FTP Change",
        "short_name": "FTP Δ",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("ftp_change", ""),
        "thresholds": None,
        "format": "{:+.0f}",
        "higher_is_better": True,
    },

    "ftp_trajectory": {
        "name": "FTP Evolution",
        "short_name": "FTP Trend",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("ftp_trajectory", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # TID & INTENSITY METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "time_above_90_ftp": {
        "name": "Time Above 90% FTP",
        "short_name": "T>90%",
        "unit": "seconds",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("time_above_90_ftp", ""),
        "thresholds": [
            (300, "🟢", "Easy/Recovery"),
            (900, "🟡", "Moderate Stimulus"),
            (1800, "🟠", "Significant Workout"),
            (float('inf'), "🔴", "Hard VO2max Session"),
        ],
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "sweet_spot_time": {
        "name": "Sweet Spot Time",
        "short_name": "SS Time",
        "unit": "seconds",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("sweet_spot_time", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "vo2max_time": {
        "name": "VO2max Time",
        "short_name": "VO2 Time",
        "unit": "seconds",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("vo2max_time", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "z2_volume": {
        "name": "Zone 2 Volume",
        "short_name": "Z2 Vol",
        "unit": "seconds",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("z2_volume", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "hr_polarization_index": {
        "name": "HR Polarization Index",
        "short_name": "HR PI",
        "unit": None,
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("hr_polarization_index", ""),
        "thresholds": [
            (1.5, "🟡", "Threshold-focused"),
            (2.0, "🟠", "Pyramidal"),
            (4.0, "🟢", "Moderately Polarized"),
            (float('inf'), "🟢", "Highly Polarized"),
        ],
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    "hr_tid_z1_percentage": {
        "name": "HR Zone 1 %",
        "short_name": "HR Z1%",
        "unit": "%",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("hr_tid_z1_percentage", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": None,
    },

    "hr_tid_z2_percentage": {
        "name": "HR Zone 2 %",
        "short_name": "HR Z2%",
        "unit": "%",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("hr_tid_z2_percentage", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": None,
    },

    "hr_tid_z3_percentage": {
        "name": "HR Zone 3 %",
        "short_name": "HR Z3%",
        "unit": "%",
        "category": "tid",
        "base_description": BASE_DESCRIPTIONS.get("hr_tid_z3_percentage", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": None,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # INTERVAL & PACING METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "interval_300s_decay_rate": {
        "name": "300s Interval Decay Rate",
        "short_name": "Int Decay",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("interval_300s_decay_rate", ""),
        "thresholds": [
            (5, "🟢", "Excellent"),
            (15, "🟡", "Good"),
            (25, "🟠", "Moderate"),
            (float('inf'), "🔴", "Significant"),
        ],
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "interval_300s_power_trend": {
        "name": "300s Interval Power Trend",
        "short_name": "Int Trend",
        "unit": "W/interval",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("interval_300s_power_trend", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": True,
    },

    "match_burn_count": {
        "name": "Match Burn Count",
        "short_name": "Matches",
        "unit": None,
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("match_burn_count", ""),
        "thresholds": [
            (2, "🟢", "Steady Ride"),
            (5, "🟡", "Typical Workout"),
            (10, "🟠", "Dynamic Ride"),
            (float('inf'), "🔴", "Criterium"),
        ],
        "format": "{:.0f}",
        "higher_is_better": False,  # Lower match burns = steadier ride = better
    },

    # ═══════════════════════════════════════════════════════════════════════
    # WEEKLY/AGGREGATE METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "this_week_tss": {
        "name": "This Week TSS",
        "short_name": "Week TSS",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("this_week_tss", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "four_week_avg_tss": {
        "name": "4-Week Average TSS",
        "short_name": "4W Avg TSS",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("four_week_avg_tss", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "high_acwr_weeks": {
        "name": "High ACWR Weeks",
        "short_name": "High ACWR",
        "unit": "weeks",
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("high_acwr_weeks", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": False,
    },

    "long_rides": {
        "name": "Long Rides",
        "short_name": "Long Rides",
        "unit": None,
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("long_rides", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "total_hours": {
        "name": "Total Training Hours",
        "short_name": "Total Hrs",
        "unit": "hours",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("total_hours", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": None,
    },

    "biggest_week": {
        "name": "Biggest Week",
        "short_name": "Max Week",
        "unit": "TSS",
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("biggest_week", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "highest_np": {
        "name": "Highest NP",
        "short_name": "Peak NP",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("highest_np", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # TREND METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "avg_ef": {
        "name": "Average Efficiency Factor",
        "short_name": "Avg EF",
        "unit": "W/bpm",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("avg_ef", ""),
        "thresholds": None,
        "format": "{:.2f}",
        "higher_is_better": True,
    },

    "avg_decoupling": {
        "name": "Average Decoupling",
        "short_name": "Avg Decoup",
        "unit": "%",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("avg_decoupling", ""),
        "thresholds": [
            (-5, "🟢", "Excellent"),
            (-10, "🟡", "Good"),
            (float('inf'), "🟠", "Needs Work"),
        ],
        "format": "{:.1f}",
        "higher_is_better": True,
    },

    "fatigue_trend": {
        "name": "Fatigue Trend",
        "short_name": "Fat Trend",
        "unit": "%",
        "category": "fatigue",
        "base_description": BASE_DESCRIPTIONS.get("fatigue_trend", ""),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": False,
    },

    "ef_trend": {
        "name": "EF Trend",
        "short_name": "EF Trend",
        "unit": "W/bpm/week",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("ef_trend", ""),
        "thresholds": None,
        "format": "{:.3f}",
        "higher_is_better": True,
    },

    "decoupling_trend": {
        "name": "Decoupling Trend",
        "short_name": "Decoup Trend",
        "unit": "%/week",
        "category": "cardiac",
        "base_description": BASE_DESCRIPTIONS.get("decoupling_trend", ""),
        "thresholds": None,
        "format": "{:.2f}",
        "higher_is_better": False,
    },

    # ═══════════════════════════════════════════════════════════════════════
    # BASIC METRICS (added in migration)
    # ═══════════════════════════════════════════════════════════════════════

    "max_power": {
        "name": "Maximum Power",
        "short_name": "Max Pwr",
        "unit": "W",
        "category": "power",
        "base_description": BASE_DESCRIPTIONS.get("max_power", "Peak 1-second power recorded during activity."),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": True,
    },

    "distance": {
        "name": "Distance",
        "short_name": "Dist",
        "unit": "km",
        "category": "basic",
        "base_description": BASE_DESCRIPTIONS.get("distance", "Total distance covered in this activity."),
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": None,
    },

    "total_elevation_gain": {
        "name": "Total Elevation Gain",
        "short_name": "Elevation",
        "unit": "m",
        "category": "climbing",
        "description": "Total vertical meters climbed during the activity.",
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },

    "average_speed": {
        "name": "Average Speed",
        "short_name": "Avg Speed",
        "unit": "km/h",
        "category": "basic",
        "description": "Average speed during the activity.",
        "thresholds": None,
        "format": "{:.1f}",
        "higher_is_better": True,
    },

    "training_stress_score": {
        "name": "Training Stress Score",
        "short_name": "TSS",
        "unit": None,
        "category": "training_load",
        "base_description": BASE_DESCRIPTIONS.get("tss", ""),
        "thresholds": None,
        "format": "{:.0f}",
        "higher_is_better": None,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE_HELP - Non-metric UI concepts and feature explanations
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_HELP = {
    "workout_type": """**Workout Type**
Strava's classification of the activity based on metadata and tags:
• Race: Competitive events (highest intensity)
• Workout: Structured training sessions
• Long Run/Ride: Extended endurance efforts
• Intervals: High-intensity interval training
• Recovery: Easy regeneration sessions

Tracking workout type distribution helps ensure training variety.""",

    "training_phase": """**Training Phase**
Periodization block classification based on volume and intensity trends:
• **Base Building**: Volume increasing, intensity moderate (Z2 focus)
• **Build Phase**: High volume + increasing intensity (threshold work)
• **Peak/Race Prep**: Volume stable/high, intensity at maximum
• **Taper/Recovery**: Volume decreasing, intensity maintained/reduced
• **Transition**: Low volume and intensity (off-season)

Proper periodization cycles stress → adaptation → rest for optimal gains.""",

    "periodization_check": """**Periodization Check**
Automated training phase detection using volume and intensity metrics.
Compares current period to previous period to identify phase:
• Volume up + Intensity stable = Base Building
• Volume stable + Intensity up = Build/Intensity
• Volume down = Taper/Recovery

Helps ensure your training follows sound periodization principles.""",

    "season_phases": """**Season Phase Detection**
Automatic classification based on CTL trends and intensity:
• OFF-SEASON: Low volume recovery period
• BASE: Building aerobic foundation (low IF)
• BUILD: Increasing intensity and volume
• PEAK/RACE: Tapering for peak performance
• RECOVERY: Active recovery after hard blocks
• TRANSITION: Between defined phases""",

    "power_curve": """**Power Curve PRs**
Best power outputs for various durations throughout the year.
These represent your peak performance capabilities:
• **5s-30s**: Neuromuscular power (sprints)
• **1-5min**: Anaerobic capacity (VO2max efforts)
• **20min-1hr**: Threshold/FTP power (sustained efforts)""",

    "gear_usage": """**Gear Usage Statistics**
Breakdown of distance, time, and elevation by equipment.
Helps track:
• Equipment wear and maintenance needs
• Training distribution across bikes
• Preferred equipment for different activities""",

    "yoy_comparison": """**Year-over-Year Progress**
Compare key metrics against previous year.
Positive trends indicate consistent improvement.""",

    "tid_classification": """**TID Classification**
Training type based on intensity distribution:
• Polarized: Z1+Z3 dominant, minimal Z2
• Pyramidal: Z1 > Z2 > Z3
• Threshold: Z2 dominant""",

    "tid": """**Training Intensity Distribution (TID)**
How your training is distributed across intensity zones:
• **Zone 1 (Low)**: Below aerobic threshold - recovery and base building
• **Zone 2 (Moderate)**: Between thresholds - tempo/sweetspot work
• **Zone 3 (High)**: Above lactate threshold - hard intervals

**Polarized training** targets 80% Zone 1, minimal Zone 2, 15-20% Zone 3.""",

    "weekly_tid": """**Weekly Training Intensity Distribution**
Training Intensity Distribution across the week. Ideal polarized model:
• 75-80% Low intensity (Z1)
• 5-10% Moderate (Z2)
• 15-20% High (Z3)""",

    "longest_streak": """**Longest Streak**
Longest run of consecutive training days.
Very long streaks (>14 days) may indicate need for rest days.""",

    "longest_gap": """**Longest Gap**
Longest period without training.
• 1-3 days: Normal recovery ✅
• 4-7 days: Planned rest week ➡️
• >7 days: Extended break (illness, vacation, etc.) ⚠️""",

    "longest_break": """**Longest Break**
Longest consecutive period without training.
• 1-3 days: Normal recovery
• 4-7 days: Planned rest week
• >7 days: Extended break (illness, vacation, etc.)""",

    "training_days": """**Training Days**
Number of days with at least one activity.
Higher consistency = better adaptation and fitness gains.
• 70%+: Excellent consistency ✅
• 50-70%: Good consistency ➡️
• <50%: Consider improving consistency ⚠️""",

    "peak_metrics": """**Peak Performance Metrics**
Highest values achieved during the year.
Peak FTP, CTL, and W/kg indicate best fitness state.""",

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
}


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY THRESHOLD STRUCTURE - For backwards compatibility
# ═══════════════════════════════════════════════════════════════════════════

METRIC_THRESHOLDS = {
    key: meta["thresholds"]
    for key, meta in METRICS_METADATA.items()
    if meta.get("thresholds") is not None and not isinstance(meta["thresholds"], dict)
}


def _format_thresholds_as_text(thresholds: list, higher_is_better: bool | None) -> str:
    """Convert structured thresholds to readable bullet points.

    Args:
        thresholds: List of (value, emoji, label) tuples
        higher_is_better: Direction indicator for threshold interpretation

    Returns:
        Formatted string with bullet points for each threshold
    """
    if not thresholds:
        return ""

    lines = []
    prev_val = None

    for i, (threshold, emoji, label) in enumerate(thresholds):
        if threshold == float('inf') or threshold == -float('inf'):
            # Last threshold - show "greater than previous"
            if prev_val is not None:
                if higher_is_better is False:
                    lines.append(f"• ≥{prev_val}: {emoji} {label}")
                else:
                    lines.append(f"• >{prev_val}: {emoji} {label}")
        else:
            if i == 0:
                # First threshold
                lines.append(f"• <{threshold}: {emoji} {label}")
            else:
                # Middle thresholds - show range
                lines.append(f"• {prev_val}-{threshold}: {emoji} {label}")
            prev_val = threshold

    return "\n".join(lines)


def generate_help_text_from_metadata(key: str) -> str:
    """Generate help text dynamically from METRICS_METADATA.

    This is the SINGLE SOURCE OF TRUTH - it combines:
    - base_description (pure prose from BASE_DESCRIPTIONS)
    - thresholds (structured data, auto-formatted as bullets)

    Args:
        key: The metric key

    Returns:
        Generated help text with title, description, and thresholds
    """
    metadata = METRICS_METADATA.get(key)
    if not metadata:
        return ""

    name = metadata.get("name", key.replace("_", " ").title())
    short_name = metadata.get("short_name", "")
    unit = metadata.get("unit", "")

    # Build title
    if short_name and short_name != name:
        title = f"**{name} ({short_name})**"
    else:
        title = f"**{name}**"

    if unit:
        title += f" [{unit}]"

    parts = [title]

    # Add base description (pure prose, no thresholds)
    desc = metadata.get("base_description", "")
    if desc:
        # Strip any existing title if duplicated
        if desc.startswith("**"):
            title_end = desc.find("\n")
            if title_end > 0:
                desc = desc[title_end+1:].strip()
        parts.append(desc)

    # Add thresholds (auto-generated from structured data)
    thresholds = metadata.get("thresholds")
    if thresholds:
        higher_is_better = metadata.get("higher_is_better")

        if isinstance(thresholds, dict):
            # Multi-context thresholds (e.g., TSS has single_activity, weekly, annual)
            for context_name, context_thresholds in thresholds.items():
                context_label = context_name.replace("_", " ").title()
                threshold_text = _format_thresholds_as_text(context_thresholds, higher_is_better)
                if threshold_text:
                    parts.append(f"\n**{context_label}:**\n{threshold_text}")
        else:
            threshold_text = _format_thresholds_as_text(thresholds, higher_is_better)
            if threshold_text:
                parts.append(f"\n**Interpretation:**\n{threshold_text}")

    return "\n".join(parts)


def get_help_text(key: str, fallback: str | dict = "") -> str:
    """Get help text by key, using METRICS_METADATA as SINGLE SOURCE OF TRUTH.

    Priority:
    1. If key exists in METRICS_METADATA → generate_help_text_from_metadata()
       (combines base_description + auto-formatted thresholds)
    2. Fall back to FEATURE_HELP for UI features/concepts
    3. Fall back to HELP_TEXTS for legacy help
    4. Return fallback if not found

    Args:
        key: The metric key to look up
        fallback: Default text to return if key not found.
                  If a dict is passed (legacy pattern), it's ignored.

    Returns:
        Help text string for the metric, or fallback if not found
    """
    # Handle legacy pattern where help_texts dict was passed as second arg
    if isinstance(fallback, dict):
        fallback = ""

    # Check METRICS_METADATA first (source of truth for metrics)
    if key in METRICS_METADATA:
        # Generate dynamically - thresholds always in sync!
        return generate_help_text_from_metadata(key)

    # Check FEATURE_HELP for UI features/concepts
    if key in FEATURE_HELP:
        return FEATURE_HELP[key]

    # Fall back to HELP_TEXTS for legacy non-metric help
    return HELP_TEXTS.get(key, fallback)


def get_metric_status(metric_key: str, value: float) -> dict[str, str]:
    """Get status interpretation for a metric value based on thresholds.

    Args:
        metric_key: The metric identifier (e.g., 'cardiac_drift', 'tsb')
        value: The metric value to interpret

    Returns:
        Dictionary with 'emoji' and 'label' keys, or empty dict if no thresholds defined

    Examples:
        >>> get_metric_status('cardiac_drift', 4.2)
        {'emoji': '🟡', 'label': 'Good'}
        >>> get_metric_status('tsb', -15)
        {'emoji': '🟠', 'label': 'Overreached'}
    """
    # Try to get from METRICS_METADATA first
    metadata = METRICS_METADATA.get(metric_key)
    if metadata:
        thresholds = metadata.get("thresholds")
        if isinstance(thresholds, dict):
            # Handle multi-context thresholds (e.g., TSS has single_activity, weekly, annual)
            # Default to first context if no specific context provided
            thresholds = next(iter(thresholds.values()))

        if thresholds:
            # Use higher_is_better to determine comparison logic
            # If higher_is_better=False: thresholds are ascending, use < operator
            # If higher_is_better=True: thresholds are descending, use >= operator
            higher_is_better = metadata.get("higher_is_better", True)

            for threshold, emoji, label in thresholds:
                if higher_is_better:
                    # For metrics where higher is better (descending thresholds)
                    if value >= threshold:
                        return {"emoji": emoji, "label": label}
                else:
                    # For metrics where lower is better (ascending thresholds)
                    if value < threshold:
                        return {"emoji": emoji, "label": label}
            # Fallback to last threshold if no match
            return {"emoji": thresholds[-1][1], "label": thresholds[-1][2]}

    # Fallback to legacy METRIC_THRESHOLDS for backwards compatibility
    thresholds = METRIC_THRESHOLDS.get(metric_key)
    if thresholds:
        # For legacy thresholds, detect direction from threshold values
        is_ascending = thresholds[0][0] < thresholds[-1][0]
        for threshold, emoji, label in thresholds:
            if is_ascending:
                if value < threshold:
                    return {"emoji": emoji, "label": label}
            else:
                if value >= threshold:
                    return {"emoji": emoji, "label": label}
        return {"emoji": thresholds[-1][1], "label": thresholds[-1][2]}

    return {}


def get_metric_metadata(metric_key: str) -> dict:
    """Get complete metadata for a metric.

    Args:
        metric_key: The metric identifier

    Returns:
        Dictionary with metadata (name, unit, category, thresholds, etc.)
        Returns empty dict if metric not found

    Examples:
        >>> meta = get_metric_metadata('cp')
        >>> meta['name']
        'Critical Power'
        >>> meta['unit']
        'W'
    """
    return METRICS_METADATA.get(metric_key, {})


def format_metric_value(metric_key: str, value: float) -> str:
    """Format a metric value according to its metadata.

    Args:
        metric_key: The metric identifier
        value: The value to format

    Returns:
        Formatted string representation of the value

    Examples:
        >>> format_metric_value('cp', 294.5)
        '294'
        >>> format_metric_value('w_prime', 13334)
        '13,334'
    """
    metadata = METRICS_METADATA.get(metric_key)
    if metadata and metadata.get("format"):
        try:
            formatted = metadata["format"].format(value)
            # Add unit if specified
            if metadata.get("unit"):
                return f"{formatted} {metadata['unit']}"
            return formatted
        except (ValueError, KeyError):
            pass

    # Fallback to simple formatting
    return f"{value:.1f}"


def get_metrics_by_category(category: str) -> list[str]:
    """Get all metric keys belonging to a specific category.

    Args:
        category: Category name (e.g., 'power', 'cardiac', 'training_load')

    Returns:
        List of metric keys in that category

    Examples:
        >>> get_metrics_by_category('power')
        ['normalized_power', 'intensity_factor', 'cp', 'w_prime', ...]
    """
    return [
        key for key, meta in METRICS_METADATA.items()
        if meta.get("category") == category
    ]
