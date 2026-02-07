"""
Training Plan Service.

Generates periodized training plans based on athlete goals, available time,
and key events. Supports classic periodization with Base, Build, Specialty,
and Taper phases.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from activities_viewer.domain.models import (
    KeyEvent,
    TrainingPhase,
    TrainingPlan,
    WeeklyPlan,
)
from activities_viewer.services.activity_service import ActivityService

# Standard phase templates
PHASE_TEMPLATES = {
    "base": TrainingPhase(
        name="Base",
        weeks=8,
        description="Build aerobic foundation with high volume, low intensity",
        tid_z1=80,
        tid_z2=12,
        tid_z3=8,
        intensity_factor_target=0.65,
        tss_ramp_rate=5.0,
    ),
    "build": TrainingPhase(
        name="Build",
        weeks=6,
        description="Increase intensity, introduce threshold work",
        tid_z1=70,
        tid_z2=15,
        tid_z3=15,
        intensity_factor_target=0.72,
        tss_ramp_rate=7.0,
    ),
    "specialty": TrainingPhase(
        name="Specialty",
        weeks=4,
        description="Event-specific preparation, peak intensity",
        tid_z1=60,
        tid_z2=15,
        tid_z3=25,
        intensity_factor_target=0.78,
        tss_ramp_rate=3.0,
    ),
    "taper": TrainingPhase(
        name="Taper",
        weeks=2,
        description="Reduce volume, maintain intensity, peak freshness",
        tid_z1=65,
        tid_z2=15,
        tid_z3=20,
        intensity_factor_target=0.70,
        tss_ramp_rate=-30.0,  # Negative = reduction
    ),
    "recovery": TrainingPhase(
        name="Recovery",
        weeks=1,
        description="Active recovery week with reduced load",
        tid_z1=90,
        tid_z2=8,
        tid_z3=2,
        intensity_factor_target=0.55,
        tss_ramp_rate=-40.0,
    ),
}

# Key workout templates by phase
WORKOUT_TEMPLATES = {
    "base": [
        "Long endurance ride (Z1-Z2, 3-4h)",
        "Sweet spot intervals (2x20min @ 88-93% FTP)",
        "Recovery spin (Z1, 1h)",
        "Endurance with cadence drills",
    ],
    "build": [
        "Threshold intervals (4x10min @ FTP)",
        "VO2max intervals (5x4min @ 110-120% FTP)",
        "Long endurance ride with tempo blocks",
        "Sweet spot over/unders",
    ],
    "specialty": [
        "Race simulation workout",
        "VO2max intervals (6x3min @ 115-125% FTP)",
        "Threshold + sprint combo",
        "Event-specific terrain practice",
    ],
    "taper": [
        "Short opener workout (race pace efforts)",
        "Easy spin with 2-3 race pace openers",
        "Complete rest or very easy spin",
    ],
    "recovery": [
        "Easy spin (Z1 only, 45-60min)",
        "Active recovery or complete rest",
        "Yoga/stretching session",
    ],
}


class TrainingPlanService:
    """
    Service for generating and managing training plans.

    Generates periodized plans based on:
    - Current fitness (CTL) and FTP
    - Target goal (W/kg or FTP)
    - Available training hours
    - Key events/races
    """

    def __init__(self, activity_service: ActivityService | None = None):
        """
        Initialize the training plan service.

        Args:
            activity_service: Service for accessing activity data (for actuals)
        """
        self.activity_service = activity_service

    def generate_plan(
        self,
        start_date: datetime,
        end_date: datetime,
        start_ftp: float,
        target_ftp: float,
        weight_kg: float,
        hours_per_week: float,
        key_events: list[dict] | None = None,
        current_ctl: float = 50.0,
        plan_name: str = "Training Plan",
    ) -> TrainingPlan:
        """
        Generate a periodized training plan.

        Args:
            start_date: Plan start date
            end_date: Plan end date (typically the A-race date)
            start_ftp: Current FTP in watts
            target_ftp: Target FTP in watts
            weight_kg: Athlete weight in kg
            hours_per_week: Available training hours per week
            key_events: List of key events [{name, date, priority}]
            current_ctl: Current CTL (fitness) for progressive loading
            plan_name: Name for the plan

        Returns:
            Complete TrainingPlan with weekly prescriptions
        """
        total_days = (end_date - start_date).days
        total_weeks = max(1, total_days // 7)

        # Parse key events
        parsed_events = self._parse_key_events(key_events or [])

        # Determine phases based on available weeks
        phases = self._calculate_phases(total_weeks, parsed_events)

        # Generate weekly plans
        weeks = self._generate_weekly_plans(
            start_date=start_date,
            phases=phases,
            hours_per_week=hours_per_week,
            start_ftp=start_ftp,
            current_ctl=current_ctl,
            parsed_events=parsed_events,
        )

        # Calculate goal
        start_wkg = start_ftp / weight_kg
        target_wkg = target_ftp / weight_kg
        goal = f"Improve from {start_wkg:.2f} to {target_wkg:.2f} W/kg (+{(target_wkg - start_wkg):.2f})"

        return TrainingPlan(
            name=plan_name,
            goal=goal,
            start_ftp=start_ftp,
            target_ftp=target_ftp,
            weight_kg=weight_kg,
            hours_per_week=hours_per_week,
            start_date=start_date,
            end_date=end_date,
            total_weeks=total_weeks,
            phases=phases,
            weeks=weeks,
            key_events=parsed_events,
        )

    def _parse_key_events(self, events: list[dict]) -> list[KeyEvent]:
        """Parse raw event dictionaries into KeyEvent objects."""
        parsed = []
        for event in events:
            try:
                date = event.get("date")
                if isinstance(date, str):
                    date = datetime.strptime(date, "%Y-%m-%d")

                if not isinstance(date, datetime):
                    continue

                parsed.append(
                    KeyEvent(
                        name=event.get("name", "Event"),
                        date=date,
                        priority=event.get("priority", "B"),
                        event_type=event.get("type", "race"),
                        notes=event.get("notes", ""),
                    )
                )
            except (ValueError, TypeError):
                continue

        return sorted(parsed, key=lambda e: e.date)

    def _calculate_phases(
        self, total_weeks: int, events: list[KeyEvent]
    ) -> list[TrainingPhase]:
        """
        Calculate training phases based on available weeks.

        Uses classic periodization:
        - Base: ~40% of available time
        - Build: ~30% of available time
        - Specialty: ~20% of available time
        - Taper: ~10% of available time (min 1 week before A-race)
        """
        phases = []

        if total_weeks <= 4:
            # Very short plan - just maintenance
            phases.append(
                TrainingPhase(
                    name="Maintenance",
                    weeks=total_weeks,
                    description="Maintain fitness with balanced training",
                    tid_z1=70,
                    tid_z2=15,
                    tid_z3=15,
                    intensity_factor_target=0.70,
                    tss_ramp_rate=0,
                )
            )
        elif total_weeks <= 8:
            # Short plan - abbreviated phases
            build_weeks = total_weeks - 1
            taper_weeks = 1
            phases.append(PHASE_TEMPLATES["build"].model_copy(update={"weeks": build_weeks}))
            phases.append(PHASE_TEMPLATES["taper"].model_copy(update={"weeks": taper_weeks}))
        elif total_weeks <= 12:
            # Medium plan
            base_weeks = total_weeks // 2
            build_weeks = total_weeks - base_weeks - 2
            taper_weeks = 2
            phases.append(PHASE_TEMPLATES["base"].model_copy(update={"weeks": base_weeks}))
            phases.append(PHASE_TEMPLATES["build"].model_copy(update={"weeks": build_weeks}))
            phases.append(PHASE_TEMPLATES["taper"].model_copy(update={"weeks": taper_weeks}))
        else:
            # Full periodization
            base_weeks = int(total_weeks * 0.40)
            build_weeks = int(total_weeks * 0.30)
            specialty_weeks = int(total_weeks * 0.20)
            taper_weeks = total_weeks - base_weeks - build_weeks - specialty_weeks

            # Ensure minimum taper
            if taper_weeks < 1:
                taper_weeks = 1
                specialty_weeks -= 1

            phases.append(PHASE_TEMPLATES["base"].model_copy(update={"weeks": base_weeks}))
            phases.append(PHASE_TEMPLATES["build"].model_copy(update={"weeks": build_weeks}))
            phases.append(PHASE_TEMPLATES["specialty"].model_copy(update={"weeks": specialty_weeks}))
            phases.append(PHASE_TEMPLATES["taper"].model_copy(update={"weeks": taper_weeks}))

        return phases

    def _generate_weekly_plans(
        self,
        start_date: datetime,
        phases: list[TrainingPhase],
        hours_per_week: float,
        start_ftp: float,
        current_ctl: float,
        parsed_events: list[KeyEvent],
    ) -> list[WeeklyPlan]:
        """Generate weekly training prescriptions."""
        weeks = []
        current_date = start_date
        week_number = 1
        running_ctl = current_ctl
        running_tss = int(current_ctl * 7)  # Approximate weekly TSS from CTL

        # Create event lookup by week
        event_lookup: dict[int, list[str]] = {}
        for event in parsed_events:
            event_week = (event.date - start_date).days // 7 + 1
            if event_week not in event_lookup:
                event_lookup[event_week] = []
            event_lookup[event_week].append(event.name)

        for phase in phases:
            phase_name = phase.name.lower()
            phase_workouts = WORKOUT_TEMPLATES.get(phase_name, [])

            for phase_week in range(1, phase.weeks + 1):
                week_start = current_date
                week_end = current_date + timedelta(days=6)

                # Check if this is a recovery week (every 4th week in base/build)
                is_recovery = False
                if phase_name in ["base", "build"] and phase_week % 4 == 0:
                    is_recovery = True

                # Calculate target TSS with progressive overload
                if is_recovery:
                    target_tss = int(running_tss * 0.6)  # 40% reduction
                    target_hours = hours_per_week * 0.6
                elif phase.tss_ramp_rate < 0:
                    # Taper - reduce
                    reduction = 1 + (phase.tss_ramp_rate / 100)
                    target_tss = int(running_tss * reduction)
                    target_hours = hours_per_week * reduction
                else:
                    # Progressive overload
                    ramp = 1 + (phase.tss_ramp_rate / 100)
                    target_tss = int(running_tss * ramp)
                    target_hours = hours_per_week

                # Cap TSS to reasonable levels
                max_weekly_tss = hours_per_week * 80  # ~80 TSS/hour max
                target_tss = min(target_tss, int(max_weekly_tss))

                # Update running values for next week
                if not is_recovery:
                    running_tss = target_tss

                # Estimate CTL progression
                target_ctl = running_ctl + (target_tss - running_ctl * 7) / 42
                running_ctl = target_ctl

                # Get events this week
                week_events = event_lookup.get(week_number, [])

                # Select key workouts
                key_workouts = []
                if is_recovery:
                    key_workouts = WORKOUT_TEMPLATES.get("recovery", [])[:2]
                else:
                    # Rotate through phase workouts
                    for i in range(min(3, len(phase_workouts))):
                        idx = (phase_week - 1 + i) % len(phase_workouts)
                        key_workouts.append(phase_workouts[idx])

                # Recovery notes
                if is_recovery:
                    recovery_notes = "Recovery week - prioritize rest, sleep, and easy spinning"
                elif phase_name == "taper":
                    recovery_notes = "Taper week - reduce volume, keep legs fresh"
                else:
                    recovery_notes = "Focus on quality sleep and nutrition"

                week_plan = WeeklyPlan(
                    week_number=week_number,
                    start_date=week_start,
                    end_date=week_end,
                    phase=phase.name,
                    phase_week=phase_week,
                    target_hours=round(target_hours, 1),
                    target_tss=target_tss,
                    target_ctl=round(target_ctl, 1),
                    tid_z1=phase.tid_z1,
                    tid_z2=phase.tid_z2,
                    tid_z3=phase.tid_z3,
                    key_workouts=key_workouts,
                    recovery_notes=recovery_notes,
                    events=week_events,
                    is_recovery_week=is_recovery,
                    is_taper_week=phase_name == "taper",
                )

                weeks.append(week_plan)
                week_number += 1
                current_date = week_end + timedelta(days=1)

        return weeks

    def update_actuals(
        self,
        plan: TrainingPlan,
        activities_df: pd.DataFrame,
    ) -> TrainingPlan:
        """
        Update the plan with actual training data.

        Args:
            plan: The training plan to update
            activities_df: DataFrame with activity data

        Returns:
            Updated training plan with actuals filled in
        """
        if activities_df.empty:
            return plan

        # Ensure datetime column
        if not pd.api.types.is_datetime64_any_dtype(activities_df["start_date_local"]):
            activities_df["start_date_local"] = pd.to_datetime(activities_df["start_date_local"])

        # Handle timezone
        if activities_df["start_date_local"].dt.tz is not None:
            activities_df = activities_df.copy()
            activities_df["start_date_local"] = activities_df["start_date_local"].dt.tz_localize(None)

        for week in plan.weeks:
            week_start = week.start_date
            week_end = week.end_date

            # Make sure week dates are timezone-naive
            if hasattr(week_start, "tzinfo") and week_start.tzinfo is not None:
                week_start = week_start.replace(tzinfo=None)
            if hasattr(week_end, "tzinfo") and week_end.tzinfo is not None:
                week_end = week_end.replace(tzinfo=None)

            # Filter activities for this week
            week_activities = activities_df[
                (activities_df["start_date_local"] >= week_start)
                & (activities_df["start_date_local"] <= week_end)
            ]

            if not week_activities.empty:
                # Calculate actuals
                actual_hours = week_activities["moving_time"].sum() / 3600

                tss_col = (
                    "moving_training_stress_score"
                    if "moving_training_stress_score" in week_activities.columns
                    else "training_stress_score"
                )
                actual_tss = int(week_activities[tss_col].sum()) if tss_col in week_activities.columns else 0

                # Get CTL from last activity of the week
                week_sorted = week_activities.sort_values("start_date_local", ascending=False)
                actual_ctl = week_sorted.iloc[0].get("chronic_training_load", 0)

                # Calculate adherence
                if week.target_tss > 0:
                    adherence = (actual_tss / week.target_tss) * 100
                else:
                    adherence = 100.0

                # Update week
                week.actual_hours = round(actual_hours, 1)
                week.actual_tss = actual_tss
                week.actual_ctl = round(actual_ctl, 1) if pd.notna(actual_ctl) else None
                week.adherence_pct = round(adherence, 1)

        return plan

    def get_current_week_plan(self, plan: TrainingPlan) -> WeeklyPlan | None:
        """Get the current week's plan."""
        current_week = plan.current_week
        if 1 <= current_week <= len(plan.weeks):
            return plan.weeks[current_week - 1]
        return None

    def get_week_summary(self, week: WeeklyPlan) -> dict:
        """Get a summary of a week's plan vs actuals."""
        summary = {
            "week": week.week_number,
            "phase": week.phase,
            "target_hours": week.target_hours,
            "target_tss": week.target_tss,
            "actual_hours": week.actual_hours,
            "actual_tss": week.actual_tss,
            "adherence": week.adherence_pct,
            "status": "Not Started",
        }

        if week.actual_tss is not None and week.adherence_pct is not None:
            if week.adherence_pct >= 90:
                summary["status"] = "✅ Complete"
            elif week.adherence_pct >= 70:
                summary["status"] = "⚠️ Partial"
            else:
                summary["status"] = "❌ Missed"

        return summary

    def get_ai_adjustment_prompt(
        self,
        plan: TrainingPlan,
        current_tsb: float,
        current_acwr: float,
        ef_trend: str = "stable",
    ) -> str:
        """
        Generate a prompt for AI-based plan adjustment.

        Args:
            plan: Current training plan
            current_tsb: Current Training Stress Balance (form)
            current_acwr: Current Acute:Chronic Workload Ratio
            ef_trend: Efficiency Factor trend (improving/stable/declining)

        Returns:
            Prompt for AI analysis
        """
        current_week = self.get_current_week_plan(plan)

        prompt = f"""
        Analyze my training plan adherence and recommend adjustments:

        ## Current Status
        - Plan Week: {plan.current_week} of {plan.total_weeks}
        - Current Phase: {current_week.phase if current_week else 'N/A'}
        - TSB (Form): {current_tsb:.1f} {'(Fresh)' if current_tsb > 0 else '(Fatigued)'}
        - ACWR: {current_acwr:.2f} {'(HIGH RISK)' if current_acwr > 1.5 else '(Optimal)' if current_acwr < 1.3 else '(Elevated)'}
        - EF Trend: {ef_trend}

        ## Plan Goals
        - Start FTP: {plan.start_ftp:.0f}W
        - Target FTP: {plan.target_ftp:.0f}W
        - Progress: {plan.progress_pct:.0f}%

        ## This Week's Target
        - Hours: {current_week.target_hours if current_week else 'N/A'}
        - TSS: {current_week.target_tss if current_week else 'N/A'}
        - Key Workouts: {', '.join(current_week.key_workouts) if current_week else 'N/A'}

        Please provide:
        1. Assessment of current fatigue level
        2. Recommended adjustments to this week's plan
        3. Specific workout modifications if needed
        4. Recovery recommendations
        """

        return prompt
    def save_plan(self, plan: TrainingPlan, file_path: Path | str) -> None:
        """
        Save training plan to a JSON file.

        Args:
            plan: The training plan to save
            file_path: Path to save the plan to
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "name": plan.name,
            "goal": plan.goal,
            "created_at": plan.created_at.isoformat(),
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "start_ftp": plan.start_ftp,
            "target_ftp": plan.target_ftp,
            "weight_kg": plan.weight_kg,
            "hours_per_week": plan.hours_per_week,
            "total_weeks": plan.total_weeks,
            "phases": [
                {
                    "name": p.name,
                    "weeks": p.weeks,
                    "description": p.description,
                    "tid_z1": p.tid_z1,
                    "tid_z2": p.tid_z2,
                    "tid_z3": p.tid_z3,
                    "intensity_factor_target": p.intensity_factor_target,
                    "tss_ramp_rate": p.tss_ramp_rate,
                }
                for p in plan.phases
            ],
            "weeks": [
                {
                    "week_number": w.week_number,
                    "phase": w.phase,
                    "phase_week": w.phase_week,
                    "start_date": w.start_date.isoformat(),
                    "end_date": w.end_date.isoformat(),
                    "target_hours": w.target_hours,
                    "target_tss": w.target_tss,
                    "target_ctl": w.target_ctl,
                    "tid_z1": w.tid_z1,
                    "tid_z2": w.tid_z2,
                    "tid_z3": w.tid_z3,
                    "key_workouts": w.key_workouts,
                    "events": w.events,
                    "recovery_notes": w.recovery_notes,
                    "is_recovery_week": w.is_recovery_week,
                    "is_taper_week": w.is_taper_week,
                    "actual_hours": w.actual_hours,
                    "actual_tss": w.actual_tss,
                    "actual_ctl": w.actual_ctl,
                    "adherence_pct": w.adherence_pct,
                }
                for w in plan.weeks
            ],
            "key_events": [
                {
                    "name": e.name,
                    "date": e.date.isoformat(),
                    "priority": e.priority,
                    "event_type": e.event_type,
                }
                for e in plan.key_events
            ],
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_plan(self, file_path: Path | str) -> TrainingPlan | None:
        """
        Load training plan from a JSON file.

        Args:
            file_path: Path to load the plan from

        Returns:
            TrainingPlan if file exists and is valid, None otherwise
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            # Parse phases
            phases = [
                TrainingPhase(
                    name=p["name"],
                    weeks=p["weeks"],
                    description=p["description"],
                    tid_z1=p["tid_z1"],
                    tid_z2=p["tid_z2"],
                    tid_z3=p["tid_z3"],
                    intensity_factor_target=p["intensity_factor_target"],
                    tss_ramp_rate=p["tss_ramp_rate"],
                )
                for p in data["phases"]
            ]

            # Parse weeks
            weeks = [
                WeeklyPlan(
                    week_number=w["week_number"],
                    phase=w["phase"],
                    phase_week=w.get("phase_week", 1),
                    start_date=datetime.fromisoformat(w["start_date"]),
                    end_date=datetime.fromisoformat(w["end_date"]),
                    target_hours=w["target_hours"],
                    target_tss=w["target_tss"],
                    target_ctl=w["target_ctl"],
                    tid_z1=w["tid_z1"],
                    tid_z2=w["tid_z2"],
                    tid_z3=w["tid_z3"],
                    key_workouts=w["key_workouts"],
                    events=w.get("events", []),
                    recovery_notes=w.get("recovery_notes"),
                    is_recovery_week=w.get("is_recovery_week", False),
                    is_taper_week=w.get("is_taper_week", False),
                    actual_hours=w.get("actual_hours"),
                    actual_tss=w.get("actual_tss"),
                    actual_ctl=w.get("actual_ctl"),
                    adherence_pct=w.get("adherence_pct"),
                )
                for w in data["weeks"]
            ]

            # Parse key events
            key_events = [
                KeyEvent(
                    name=e["name"],
                    date=datetime.fromisoformat(e["date"]),
                    priority=e["priority"],
                    event_type=e.get("event_type", "race"),
                )
                for e in data.get("key_events", [])
            ]

            return TrainingPlan(
                name=data["name"],
                goal=data.get("goal", ""),
                created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
                start_date=datetime.fromisoformat(data["start_date"]),
                end_date=datetime.fromisoformat(data["end_date"]),
                start_ftp=data["start_ftp"],
                target_ftp=data["target_ftp"],
                weight_kg=data["weight_kg"],
                hours_per_week=data.get("hours_per_week", 10.0),
                total_weeks=data.get("total_weeks", len(weeks)),
                phases=phases,
                weeks=weeks,
                key_events=key_events,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to load training plan: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    # AI-ASSISTED PLAN REFINEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def build_plan_refinement_prompt(
        self,
        plan: TrainingPlan,
        athlete_context: str,
    ) -> str:
        """
        Build a prompt that asks the LLM to refine a static training plan
        using comprehensive athlete history.

        Args:
            plan: The template-generated plan to refine.
            athlete_context: Output of ActivityContextBuilder.build_training_plan_context().

        Returns:
            Full prompt string for the LLM.
        """
        # Serialize the static plan into a readable format
        plan_summary = self.serialize_plan_for_prompt(plan)

        system_prompt = """You are an elite cycling coach creating a personalised training plan.

You have been given:
1. The athlete's COMPLETE training history (years of data, FTP evolution, load patterns, etc.)
2. A TEMPLATE plan generated from standard periodisation rules.

Your task: REFINE the template plan to fit THIS athlete based on their actual history.

REFINEMENT GUIDELINES:
- Adjust weekly TSS targets based on what the athlete actually sustains (don't prescribe 800 TSS/week if they average 400)
- Tailor workout suggestions to their strengths/weaknesses visible in the data
- If their FTP has been plateauing, emphasise variety and VO2max work in the Build phase
- If their EF is declining, prioritise aerobic base even if the template says Build
- If they rarely do long rides, ramp long ride duration gradually rather than jumping to 4h
- Account for their actual weekly ride frequency and typical ride duration
- If they're already in a detectable training phase, align the plan start accordingly
- Set realistic FTP targets based on their quarterly progression trajectory

RESPONSE FORMAT — you MUST respond with EXACTLY this structure:

## AI Coach Analysis
(2-3 paragraphs: what you observe about the athlete's history, current fitness trajectory,
strengths, limiters, and how that shapes your plan adjustments)

## Phase Adjustments
For each phase, state what you'd change and why. If no change is needed, say "No changes".
Format:
- **Phase Name** (X weeks): adjustment description

## Weekly Refinements
For EACH week number, provide refined values in this EXACT format (one per line):
WEEK <number>: TSS=<value>, HOURS=<value>, Z1=<pct>, Z2=<pct>, Z3=<pct>
WORKOUTS: <comma-separated list of 2-3 key workout descriptions>
NOTES: <one-line recovery/focus note>

Important:
- Include ALL weeks (don't skip any)
- TSS values must be integers
- HOURS can have one decimal
- Z1+Z2+Z3 must equal 100
- Be specific with workout descriptions (include power targets relative to FTP)

## Key Recommendations
(3-5 bullet points with the most important things for this athlete)
"""

        return f"{system_prompt}\n\n## Athlete Training History\n{athlete_context}\n\n## Template Plan to Refine\n{plan_summary}"

    def serialize_plan_for_prompt(self, plan: TrainingPlan) -> str:
        """Serialize a TrainingPlan into a readable prompt section."""
        lines = []
        lines.append(f"Plan: {plan.name}")
        lines.append(f"Goal: {plan.goal}")
        lines.append(f"Duration: {plan.total_weeks} weeks ({plan.start_date.strftime('%Y-%m-%d')} to {plan.end_date.strftime('%Y-%m-%d')})")
        lines.append(f"Start FTP: {plan.start_ftp:.0f}W → Target FTP: {plan.target_ftp:.0f}W")
        lines.append(f"Weight: {plan.weight_kg:.1f}kg")
        lines.append(f"Available hours/week: {plan.hours_per_week}")
        lines.append("")

        # Phases
        lines.append("### Phases")
        for phase in plan.phases:
            lines.append(
                f"- {phase.name} ({phase.weeks} weeks): {phase.description} "
                f"[TID: Z1={phase.tid_z1:.0f}% Z2={phase.tid_z2:.0f}% Z3={phase.tid_z3:.0f}%, "
                f"IF target={phase.intensity_factor_target:.2f}]"
            )
        lines.append("")

        # Events
        if plan.key_events:
            lines.append("### Key Events")
            for event in plan.key_events:
                lines.append(f"- {event.name} ({event.priority}) on {event.date.strftime('%Y-%m-%d')}")
            lines.append("")

        # Weekly breakdown
        lines.append("### Weekly Breakdown")
        for week in plan.weeks:
            marker = " [RECOVERY]" if week.is_recovery_week else " [TAPER]" if week.is_taper_week else ""
            lines.append(
                f"Week {week.week_number} ({week.phase}, wk {week.phase_week}){marker}: "
                f"TSS={week.target_tss}, Hours={week.target_hours}, CTL={week.target_ctl:.0f}, "
                f"TID: Z1={week.tid_z1:.0f}/Z2={week.tid_z2:.0f}/Z3={week.tid_z3:.0f}"
            )
            if week.key_workouts:
                lines.append(f"  Workouts: {', '.join(week.key_workouts)}")
            if week.events:
                lines.append(f"  Events: {', '.join(week.events)}")

        return "\n".join(lines)

    def apply_ai_plan_refinements(
        self,
        plan: TrainingPlan,
        ai_response: str,
    ) -> tuple[TrainingPlan, str]:
        """
        Parse structured LLM output and apply refinements to the plan.

        Extracts WEEK lines from the response and updates the corresponding
        WeeklyPlan objects. Returns both the refined plan and the full AI
        analysis text (for display).

        Args:
            plan: The original template plan.
            ai_response: Raw LLM response text.

        Returns:
            Tuple of (refined_plan, analysis_text).
        """
        import logging
        import re
        log = logging.getLogger(__name__)

        refined_count = 0

        for week in plan.weeks:
            wn = week.week_number

            # Match: WEEK <n>: TSS=<v>, HOURS=<v>, Z1=<v>, Z2=<v>, Z3=<v>
            pattern = (
                rf"WEEK\s+{wn}\s*:\s*"
                rf"TSS\s*=\s*(\d+)\s*,\s*"
                rf"HOURS\s*=\s*([\d.]+)\s*,\s*"
                rf"Z1\s*=\s*(\d+)\s*,\s*"
                rf"Z2\s*=\s*(\d+)\s*,\s*"
                rf"Z3\s*=\s*(\d+)"
            )
            match = re.search(pattern, ai_response, re.IGNORECASE)

            if match:
                new_tss = int(match.group(1))
                new_hours = float(match.group(2))
                new_z1 = int(match.group(3))
                new_z2 = int(match.group(4))
                new_z3 = int(match.group(5))

                # Sanity checks
                if new_tss > 0 and new_hours > 0 and (new_z1 + new_z2 + new_z3) == 100:
                    week.target_tss = new_tss
                    week.target_hours = round(new_hours, 1)
                    week.tid_z1 = new_z1
                    week.tid_z2 = new_z2
                    week.tid_z3 = new_z3
                    refined_count += 1
                else:
                    log.warning(
                        f"Week {wn}: AI values failed sanity check "
                        f"(TSS={new_tss}, Hours={new_hours}, Z={new_z1}+{new_z2}+{new_z3})"
                    )

            # Match workouts for this week: WORKOUTS: <text> (on next line after WEEK N)
            workout_pattern = (
                rf"WEEK\s+{wn}\s*:.*?\n"
                rf"WORKOUTS\s*:\s*(.+)"
            )
            workout_match = re.search(workout_pattern, ai_response, re.IGNORECASE)
            if workout_match:
                workouts_text = workout_match.group(1).strip()
                new_workouts = [w.strip() for w in workouts_text.split(",") if w.strip()]
                if new_workouts:
                    week.key_workouts = new_workouts

            # Match notes
            notes_pattern = (
                rf"WEEK\s+{wn}\s*:.*?\n"
                rf"(?:WORKOUTS\s*:.*?\n)?"
                rf"NOTES\s*:\s*(.+)"
            )
            notes_match = re.search(notes_pattern, ai_response, re.IGNORECASE)
            if notes_match:
                new_notes = notes_match.group(1).strip()
                if new_notes:
                    week.recovery_notes = new_notes

        # Recalculate CTL progression after TSS changes
        if refined_count > 0:
            self._recalculate_ctl_progression(plan)
            log.info(f"AI refinement applied to {refined_count}/{plan.total_weeks} weeks")

        # Extract analysis text (everything before "## Weekly Refinements")
        analysis = ai_response
        split_marker = "## Weekly Refinements"
        if split_marker in ai_response:
            analysis = ai_response.split(split_marker)[0].strip()
            # Also append Key Recommendations if present
            key_rec_marker = "## Key Recommendations"
            if key_rec_marker in ai_response:
                analysis += "\n\n" + ai_response.split(key_rec_marker)[1]
                analysis = analysis.strip()
                analysis = f"{ai_response.split(split_marker)[0].strip()}\n\n## Key Recommendations{ai_response.split(key_rec_marker)[1]}"

        return plan, analysis

    def _recalculate_ctl_progression(self, plan: TrainingPlan) -> None:
        """Recalculate target CTL after AI-adjusted TSS values."""
        # Start from whatever the first week's CTL is
        running_ctl = plan.weeks[0].target_ctl if plan.weeks else 50.0

        for week in plan.weeks:
            # CTL ≈ exponentially weighted avg of daily TSS with 42-day constant
            daily_tss = week.target_tss / 7
            running_ctl = running_ctl + (daily_tss - running_ctl) / 42 * 7
            week.target_ctl = round(running_ctl, 1)
