"""
Context builder for AI queries.

Provides multi-scale temporal context for long-term goal tracking:
- Full historical data summary (all years available)
- Quarterly/monthly aggregations for trend analysis
- FTP evolution over entire history
- Recent detailed activities
- Stream data for referenced activities (power, HR, cadence analysis)
- GPS route analysis with street names via reverse geocoding
"""

import logging
import re
import time
from datetime import datetime, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from activities_viewer.services.activity_service import ActivityService

# Optional geocoding support
try:
    from geopy.exc import GeocoderServiceError, GeocoderTimedOut
    from geopy.geocoders import Nominatim
    GEOCODING_AVAILABLE = True
except ImportError:
    GEOCODING_AVAILABLE = False

logger = logging.getLogger(__name__)


# Global geocoder instance (reused across calls)
_geocoder = None


def get_geocoder():
    """Get or create a Nominatim geocoder instance."""
    global _geocoder
    if _geocoder is None and GEOCODING_AVAILABLE:
        _geocoder = Nominatim(user_agent="activities_viewer_ai_coach/1.0")
    return _geocoder


@lru_cache(maxsize=100)
def reverse_geocode_cached(lat: float, lng: float) -> str | None:
    """
    Reverse geocode coordinates to get street/location name.

    Uses LRU cache to avoid repeated lookups for the same location.
    Rate-limited to respect Nominatim's 1 request/second policy.
    """
    geocoder = get_geocoder()
    if geocoder is None:
        return None

    try:
        # Nominatim requires 1 second between requests
        time.sleep(1.1)

        location = geocoder.reverse((lat, lng), exactly_one=True, language="en")
        if location:
            address = location.raw.get("address", {})
            # Build a useful location string
            parts = []

            # Street name
            road = address.get("road") or address.get("street")
            if road:
                parts.append(road)

            # Neighborhood/suburb
            suburb = address.get("suburb") or address.get("neighbourhood") or address.get("quarter")
            if suburb and suburb not in parts:
                parts.append(suburb)

            # City/town
            city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
            if city and city not in parts:
                parts.append(city)

            return ", ".join(parts) if parts else None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding error for ({lat}, {lng}): {e}")
    except Exception as e:
        logger.warning(f"Unexpected geocoding error: {e}")

    return None


class ActivityContextBuilder:
    def __init__(self, service: ActivityService, settings=None):
        self.service = service
        self.settings = settings

    def build_context(self, query: str) -> str:
        """
        Build comprehensive context for the LLM based on the user query.

        Provides multi-scale temporal context:
        - Data range and athlete profile
        - Current training status
        - Training phase detection
        - FULL HISTORY: Yearly summaries
        - FULL HISTORY: Quarterly FTP/W/kg evolution
        - Recent monthly trends (last 6 months)
        - Efficiency Factor trends
        - Last 4 weeks summary
        - Last 5 activities with details
        - Stream data for referenced activities (if detected in query)

        Args:
            query: The user's question.

        Returns:
            A string containing relevant context.
        """
        activities = self.service.get_all_activities()

        context = ""

        if activities.empty:
            context += "No activities found.\n"
            return context

        # Sort by date descending
        activities = activities.sort_values("start_date_local", ascending=False)

        # Handle timezone-aware datetimes for all filtering
        if activities["start_date_local"].dt.tz is not None:
            activities = activities.copy()
            activities["start_date_local"] = activities["start_date_local"].dt.tz_localize(None)

        # ═══════════════════════════════════════════════════════════════════════
        # DETECT REFERENCED ACTIVITIES & LOAD STREAM DATA
        # ═══════════════════════════════════════════════════════════════════════
        referenced_activities = self._detect_referenced_activities(query, activities)
        if referenced_activities:
            context += "=== REFERENCED ACTIVITY STREAM DATA ===\n"
            context += self._build_stream_context(referenced_activities)
            context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # STREAMS DIRECTORY OVERVIEW (fleet analytics across ALL stream files)
        # ═══════════════════════════════════════════════════════════════════════
        context += self._build_streams_overview_context(activities)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # DATA RANGE & ATHLETE PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        oldest_date = activities["start_date_local"].min()
        newest_date = activities["start_date_local"].max()
        total_activities = len(activities)
        years_of_data = (newest_date - oldest_date).days / 365.25

        context += "=== DATA RANGE & ATHLETE PROFILE ===\n"
        context += f"Data spans: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')}\n"
        context += f"Total history: {years_of_data:.1f} years ({total_activities} activities)\n"

        if self.settings:
            ftp = getattr(self.settings, 'ftp', None)
            weight = getattr(self.settings, 'rider_weight_kg', None)
            if ftp and weight:
                context += f"Current FTP: {ftp:.0f}W, Weight: {weight:.1f}kg, W/kg: {ftp/weight:.2f}\n"
            target_wkg = getattr(self.settings, 'target_wkg', None)
            target_date = getattr(self.settings, 'target_date', None)
            if target_wkg and target_date:
                context += f"GOAL: {target_wkg:.1f} W/kg by {target_date}\n"
                if ftp and weight:
                    gap = target_wkg - (ftp/weight)
                    context += f"Gap to Goal: {gap:.2f} W/kg ({gap * weight:.0f}W)\n"
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # CURRENT TRAINING STATUS
        # ═══════════════════════════════════════════════════════════════════════
        latest = activities.iloc[0]
        context += "=== CURRENT TRAINING STATUS ===\n"
        self._add_training_status(context, latest)
        context += self._format_training_status(latest)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # TRAINING PHASE DETECTION
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== CURRENT TRAINING PHASE ===\n"
        context += self._detect_training_phase(activities)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # FULL HISTORY: YEARLY SUMMARIES
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== YEARLY TRAINING SUMMARIES (Full History) ===\n"
        context += self._build_yearly_summaries(activities)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # FULL HISTORY: QUARTERLY FTP EVOLUTION
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== FTP/W/KG EVOLUTION BY QUARTER (Full History) ===\n"
        context += self._build_quarterly_ftp_evolution(activities)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # RECENT MONTHLY TRENDS (Last 6 months)
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== RECENT MONTHLY TRENDS (Last 6 Months) ===\n"
        context += self._build_monthly_progression(activities, months=6)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # EFFICIENCY FACTOR TRENDS
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== EFFICIENCY FACTOR TRENDS (Aerobic Fitness) ===\n"
        context += self._build_ef_trends(activities)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # LAST 4 WEEKS SUMMARY
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== LAST 4 WEEKS SUMMARY ===\n"
        context += self._build_weekly_summaries(activities, weeks=4)
        context += "\n"

        # ═══════════════════════════════════════════════════════════════════════
        # LAST 5 ACTIVITIES (Detailed)
        # ═══════════════════════════════════════════════════════════════════════
        context += "=== LAST 5 ACTIVITIES (Detailed) ===\n"
        for _, row in activities.head(5).iterrows():
            context += self._format_activity_detail(row)

        return context

    def build_training_plan_context(self, plan=None) -> str:
        """
        Build focused context for AI-assisted training plan generation/refinement.

        Provides the macro-level athlete profile that the LLM needs to tailor
        a periodized plan:
        - Athlete profile & goals
        - Current training status (CTL/ATL/TSB/ACWR)
        - Training phase auto-detection
        - Full yearly summaries (volume, FTP peaks, peak CTL)
        - Quarterly FTP/W/kg evolution (long-term trajectory)
        - 6-month monthly trends (recent load & intensity)
        - Efficiency Factor trends (aerobic fitness arc)
        - Last 4 weeks summary (current training pattern)

        Excludes stream data and GPS — not needed for plan-level decisions.

        Args:
            plan: Optional TrainingPlan. When provided, the plan's FTP/W/kg
                  targets are used instead of config-level goals, so the LLM
                  sees the correct targets for THIS plan.

        Returns:
            A string with the athlete's comprehensive training history context.
        """
        activities = self.service.get_all_activities()
        context = ""

        if activities.empty:
            context += "No historical activities found.\n"
            return context

        activities = activities.sort_values("start_date_local", ascending=False)

        # Handle timezone-aware datetimes
        if activities["start_date_local"].dt.tz is not None:
            activities = activities.copy()
            activities["start_date_local"] = activities["start_date_local"].dt.tz_localize(None)

        # ─── DATA RANGE & ATHLETE PROFILE ────────────────────────────────
        oldest_date = activities["start_date_local"].min()
        newest_date = activities["start_date_local"].max()
        total_activities = len(activities)
        years_of_data = (newest_date - oldest_date).days / 365.25

        context += "=== ATHLETE PROFILE & HISTORY ===\n"
        context += f"Data spans: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')}\n"
        context += f"Total history: {years_of_data:.1f} years ({total_activities} activities)\n"

        if self.settings:
            ftp = getattr(self.settings, 'ftp', None)
            weight = getattr(self.settings, 'rider_weight_kg', None)
            if ftp and weight:
                context += f"Current FTP: {ftp:.0f}W, Weight: {weight:.1f}kg, W/kg: {ftp/weight:.2f}\n"

            # Use plan targets if provided, otherwise fall back to config goals
            if plan is not None:
                plan_target_wkg = plan.target_ftp / plan.weight_kg
                plan_start_wkg = plan.start_ftp / plan.weight_kg
                context += (
                    f"THIS PLAN'S GOAL: {plan.start_ftp:.0f}W ({plan_start_wkg:.2f} W/kg) "
                    f"→ {plan.target_ftp:.0f}W ({plan_target_wkg:.2f} W/kg) "
                    f"by {plan.end_date.strftime('%Y-%m-%d')}\n"
                )
                if ftp and weight:
                    gap = plan_target_wkg - (ftp / weight)
                    context += f"Gap to Plan Goal: {gap:.2f} W/kg ({gap * weight:.0f}W)\n"
            else:
                target_wkg = getattr(self.settings, 'target_wkg', None)
                target_date = getattr(self.settings, 'target_date', None)
                if target_wkg and target_date:
                    context += f"GOAL: {target_wkg:.1f} W/kg by {target_date}\n"
                    if ftp and weight:
                        gap = target_wkg - (ftp / weight)
                        context += f"Gap to Goal: {gap:.2f} W/kg ({gap * weight:.0f}W)\n"
        context += "\n"

        # ─── CURRENT TRAINING STATUS ─────────────────────────────────────
        latest = activities.iloc[0]
        context += "=== CURRENT TRAINING STATUS ===\n"
        context += self._format_training_status(latest)
        context += "\n"

        # ─── TRAINING PHASE DETECTION ────────────────────────────────────
        context += "=== DETECTED TRAINING PHASE ===\n"
        context += self._detect_training_phase(activities)
        context += "\n"

        # ─── YEARLY SUMMARIES ────────────────────────────────────────────
        context += "=== YEARLY TRAINING SUMMARIES (Full History) ===\n"
        context += self._build_yearly_summaries(activities)
        context += "\n"

        # ─── QUARTERLY FTP EVOLUTION ─────────────────────────────────────
        context += "=== FTP/W/KG EVOLUTION BY QUARTER (Full History) ===\n"
        context += self._build_quarterly_ftp_evolution(activities)
        context += "\n"

        # ─── MONTHLY TRENDS (6 months) ──────────────────────────────────
        context += "=== RECENT MONTHLY TRENDS (Last 6 Months) ===\n"
        context += self._build_monthly_progression(activities, months=6)
        context += "\n"

        # ─── EFFICIENCY FACTOR TRENDS ────────────────────────────────────
        context += "=== EFFICIENCY FACTOR TRENDS (Aerobic Fitness) ===\n"
        context += self._build_ef_trends(activities)
        context += "\n"

        # ─── LAST 4 WEEKS ───────────────────────────────────────────────
        context += "=== LAST 4 WEEKS SUMMARY ===\n"
        context += self._build_weekly_summaries(activities, weeks=4)
        context += "\n"

        # ─── TRAINING LOAD PATTERNS ─────────────────────────────────────
        context += "=== TRAINING LOAD PATTERNS ===\n"
        context += self._build_load_patterns(activities)
        context += "\n"

        return context

    def _build_load_patterns(self, activities: pd.DataFrame) -> str:
        """Build patterns about athlete's typical training to inform plan design."""
        output = ""
        now = datetime.now()

        # Average weekly hours over last 3 months
        three_months_ago = now - timedelta(days=90)
        recent = activities[activities["start_date_local"] >= three_months_ago]

        if recent.empty:
            return "Insufficient recent data for load patterns.\n"

        total_hours = recent["moving_time"].sum() / 3600
        weeks_span = max(1, (now - three_months_ago).days / 7)
        avg_weekly_hours = total_hours / weeks_span
        avg_weekly_rides = len(recent) / weeks_span

        output += f"Recent 3-month average: {avg_weekly_hours:.1f}h/week, {avg_weekly_rides:.1f} rides/week\n"

        # Typical ride duration
        avg_ride_duration = recent["moving_time"].mean() / 3600
        max_ride_duration = recent["moving_time"].max() / 3600
        output += f"Typical ride: {avg_ride_duration:.1f}h, Longest recent: {max_ride_duration:.1f}h\n"

        # Training intensity distribution over last 3 months
        if "power_tid_z1_percentage" in recent.columns:
            avg_z1 = recent["power_tid_z1_percentage"].mean()
            avg_z2 = recent["power_tid_z2_percentage"].mean() if "power_tid_z2_percentage" in recent.columns else 0
            avg_z3 = recent["power_tid_z3_percentage"].mean() if "power_tid_z3_percentage" in recent.columns else 0
            if pd.notna(avg_z1):
                output += f"3-month TID: Z1={avg_z1:.0f}% Z2={avg_z2:.0f}% Z3={avg_z3:.0f}%\n"

        # Average TSS
        tss_col = "moving_training_stress_score" if "moving_training_stress_score" in recent.columns else "training_stress_score"
        if tss_col in recent.columns:
            total_tss = recent[tss_col].sum()
            avg_weekly_tss = total_tss / weeks_span
            output += f"Avg weekly TSS: {avg_weekly_tss:.0f}\n"

        # Long ride frequency (rides > 2.5h)
        long_rides = recent[recent["moving_time"] > 9000]  # 2.5h in seconds
        if not long_rides.empty:
            long_ride_freq = len(long_rides) / weeks_span
            output += f"Long rides (>2.5h): {long_ride_freq:.1f}/week\n"

        # Intensity distribution: what kind of workouts they actually do
        if "intensity_factor" in recent.columns:
            easy_rides = recent[recent["intensity_factor"] < 0.70]
            tempo_rides = recent[(recent["intensity_factor"] >= 0.70) & (recent["intensity_factor"] < 0.85)]
            hard_rides = recent[recent["intensity_factor"] >= 0.85]
            output += f"Ride types: {len(easy_rides)} easy, {len(tempo_rides)} tempo, {len(hard_rides)} hard (last 3 months)\n"

        return output

    def _format_training_status(self, latest: pd.Series) -> str:
        """Format current training status from latest activity."""
        output = ""
        if pd.notna(latest.get("chronic_training_load")):
            ctl = latest['chronic_training_load']
            level = "Elite" if ctl > 100 else "Strong" if ctl > 70 else "Good" if ctl > 50 else "Building"
            output += f"CTL (Fitness): {ctl:.1f} ({level})\n"
        if pd.notna(latest.get("acute_training_load")):
            output += f"ATL (Fatigue): {latest['acute_training_load']:.1f}\n"
        if pd.notna(latest.get("training_stress_balance")):
            tsb = latest["training_stress_balance"]
            if tsb > 15:
                status = "Fresh"
            elif tsb > 0:
                status = "Rested"
            elif tsb > -15:
                status = "Optimal"
            elif tsb > -30:
                status = "Fatigued"
            else:
                status = "Overreached"
            output += f"TSB (Form): {tsb:.1f} ({status})\n"
        if pd.notna(latest.get("acwr")):
            acwr = latest["acwr"]
            risk = "HIGH RISK" if acwr > 1.5 else "Elevated" if acwr > 1.3 else "Undertraining" if acwr < 0.8 else "Optimal"
            output += f"ACWR: {acwr:.2f} ({risk})\n"
        return output

    def _add_training_status(self, context: str, latest: pd.Series) -> None:
        """Helper for backwards compatibility."""
        pass

    def _detect_training_phase(self, activities: pd.DataFrame) -> str:
        """Detect current training phase based on recent TID."""
        output = ""
        four_weeks_ago = datetime.now() - timedelta(days=28)
        recent = activities[activities["start_date_local"] >= four_weeks_ago]

        if recent.empty:
            return "Unable to detect phase - insufficient recent data.\n"

        avg_z1 = recent["power_tid_z1_percentage"].mean() if "power_tid_z1_percentage" in recent.columns else 0
        avg_z2 = recent["power_tid_z2_percentage"].mean() if "power_tid_z2_percentage" in recent.columns else 0
        avg_z3 = recent["power_tid_z3_percentage"].mean() if "power_tid_z3_percentage" in recent.columns else 0
        avg_if = recent["intensity_factor"].mean() if "intensity_factor" in recent.columns else 0

        if pd.notna(avg_z1) and pd.notna(avg_z3):
            if avg_z1 > 75 and avg_z3 < 10:
                phase = "BASE BUILDING"
                note = "⚠️ FTP estimates will appear LOWER than actual capability. Use EF trend instead."
            elif avg_z1 > 60 and avg_z3 < 20:
                phase = "EARLY BUILD"
                note = "FTP estimates may underestimate capability."
            elif avg_z3 > 20 and avg_z3 < 35:
                phase = "BUILD"
                note = "FTP estimates should be representative."
            elif avg_z3 > 35:
                phase = "PEAK/RACE"
                note = "FTP estimates most accurate."
            else:
                phase = "MIXED"
                note = ""
        else:
            phase = "UNKNOWN"
            note = ""

        output += f"Phase: {phase}\n"
        output += f"Recent 4-Week TID: Z1={avg_z1:.0f}% Z2={avg_z2:.0f}% Z3={avg_z3:.0f}%\n"
        if pd.notna(avg_if):
            output += f"Avg IF: {avg_if:.2f}\n"
        if note:
            output += f"{note}\n"

        return output

    def _build_yearly_summaries(self, activities: pd.DataFrame) -> str:
        """Build yearly summaries for full historical context."""
        output = ""

        # Get all years in the data
        activities = activities.copy()
        activities["year"] = activities["start_date_local"].dt.year
        years = sorted(activities["year"].unique(), reverse=True)

        weight = getattr(self.settings, 'rider_weight_kg', 75.0) if self.settings else 75.0

        for year in years:
            year_data = activities[activities["year"] == year]

            total_activities = len(year_data)
            total_hours = year_data["moving_time"].sum() / 3600
            total_distance = year_data["distance"].sum() / 1000
            total_elevation = year_data["total_elevation_gain"].sum()

            tss_col = "moving_training_stress_score" if "moving_training_stress_score" in year_data.columns else "training_stress_score"
            total_tss = year_data[tss_col].sum() if tss_col in year_data.columns else 0

            # Best FTP of the year
            best_ftp = None
            if "estimated_ftp" in year_data.columns:
                ftp_vals = pd.to_numeric(year_data["estimated_ftp"], errors="coerce")
                best_ftp = ftp_vals.max() if ftp_vals.notna().any() else None
            elif "power_curve_20min" in year_data.columns:
                p20_vals = pd.to_numeric(year_data["power_curve_20min"], errors="coerce")
                best_ftp = float(p20_vals.max()) * 0.95 if p20_vals.notna().any() else None

            # Peak CTL
            peak_ctl = year_data["chronic_training_load"].max() if "chronic_training_load" in year_data.columns else None

            output += f"{year}: {total_activities} rides, {total_hours:.0f}h, {total_distance:.0f}km, {total_elevation:.0f}m elev, TSS={total_tss:.0f}"
            if best_ftp is not None and best_ftp > 0:
                output += f", Best FTP={best_ftp:.0f}W ({best_ftp/weight:.2f} W/kg)"
            if peak_ctl is not None and peak_ctl > 0:
                output += f", Peak CTL={peak_ctl:.0f}"
            output += "\n"

        return output

    def _build_quarterly_ftp_evolution(self, activities: pd.DataFrame) -> str:
        """Build quarterly FTP evolution for multi-year trend analysis."""
        output = ""

        # Get FTP estimates
        activities = activities.copy()
        if "estimated_ftp" in activities.columns:
            activities["ftp_est"] = pd.to_numeric(activities["estimated_ftp"], errors="coerce")
        elif "power_curve_20min" in activities.columns:
            activities["ftp_est"] = pd.to_numeric(activities["power_curve_20min"], errors="coerce") * 0.95
        else:
            return "No FTP estimation data available.\n"

        # Filter valid
        ftp_data = activities[activities["ftp_est"].notna() & (activities["ftp_est"] > 0)].copy()
        if ftp_data.empty:
            return "No valid FTP estimates.\n"

        weight = getattr(self.settings, 'rider_weight_kg', 75.0) if self.settings else 75.0

        # Create quarter column
        ftp_data["quarter"] = ftp_data["start_date_local"].dt.to_period("Q")
        quarters = sorted(ftp_data["quarter"].unique(), reverse=True)

        for q in quarters[:16]:  # Last 4 years (16 quarters)
            q_data = ftp_data[ftp_data["quarter"] == q]
            if q_data.empty:
                continue

            best_ftp = q_data["ftp_est"].max()
            avg_ftp = q_data["ftp_est"].mean()
            best_wkg = best_ftp / weight

            output += f"{q}: Best={best_ftp:.0f}W ({best_wkg:.2f} W/kg), Avg={avg_ftp:.0f}W\n"

        # Calculate year-over-year trend
        one_year_ago = datetime.now() - relativedelta(years=1)
        old_data = ftp_data[ftp_data["start_date_local"] <= one_year_ago]
        recent_data = ftp_data[ftp_data["start_date_local"] >= datetime.now() - relativedelta(months=3)]

        if not old_data.empty and not recent_data.empty:
            old_best = old_data["ftp_est"].max()
            recent_best = recent_data["ftp_est"].max()
            if pd.notna(old_best) and pd.notna(recent_best):
                ftp_change = recent_best - old_best
                wkg_change = ftp_change / weight
                output += f"\n1-Year Trend: {ftp_change:+.0f}W ({wkg_change:+.2f} W/kg)\n"

        return output

    def _build_monthly_progression(self, activities: pd.DataFrame, months: int = 6) -> str:
        """Build monthly training summaries."""
        output = ""
        now = datetime.now()

        for i in range(months):
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)

            month_data = activities[
                (activities["start_date_local"] >= month_start) &
                (activities["start_date_local"] <= month_end)
            ]

            month_name = month_start.strftime("%b %Y")

            if month_data.empty:
                output += f"{month_name}: No activities\n"
                continue

            total_activities = len(month_data)
            total_hours = month_data["moving_time"].sum() / 3600

            tss_col = "moving_training_stress_score" if "moving_training_stress_score" in month_data.columns else "training_stress_score"
            total_tss = month_data[tss_col].sum() if tss_col in month_data.columns else 0

            end_ctl = month_data.iloc[0].get("chronic_training_load", 0)
            avg_if = month_data["intensity_factor"].mean() if "intensity_factor" in month_data.columns else 0

            output += f"{month_name}: {total_activities} rides, {total_hours:.0f}h, TSS={total_tss:.0f}"
            if pd.notna(end_ctl) and end_ctl > 0:
                output += f", CTL={end_ctl:.0f}"
            if pd.notna(avg_if) and avg_if > 0:
                output += f", IF={avg_if:.2f}"
            output += "\n"

        return output

    def _build_ef_trends(self, activities: pd.DataFrame) -> str:
        """Build Efficiency Factor trends - crucial for base building."""
        output = ""

        if "efficiency_factor" not in activities.columns:
            return "No EF data available.\n"

        output += "EF = NP/HR. Rising EF = improving aerobic fitness.\n"

        now = datetime.now()
        for i in range(6):
            month_start = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)

            month_data = activities[
                (activities["start_date_local"] >= month_start) &
                (activities["start_date_local"] <= month_end)
            ]

            month_name = month_start.strftime("%b %Y")

            ef_data = month_data[
                (month_data["efficiency_factor"].notna()) &
                (month_data["efficiency_factor"] > 0.5) &
                (month_data["efficiency_factor"] < 3.0)
            ]

            if ef_data.empty:
                continue

            avg_ef = ef_data["efficiency_factor"].mean()
            max_ef = ef_data["efficiency_factor"].max()
            output += f"{month_name}: Avg EF={avg_ef:.2f}, Best={max_ef:.2f}\n"

        return output

    def _build_weekly_summaries(self, activities: pd.DataFrame, weeks: int = 4) -> str:
        """Build weekly summaries for recent patterns."""
        output = ""
        now = datetime.now()

        for i in range(weeks):
            week_end = now - timedelta(days=i * 7)
            week_start = week_end - timedelta(days=7)

            week_data = activities[
                (activities["start_date_local"] >= week_start) &
                (activities["start_date_local"] < week_end)
            ]

            week_label = f"Week {i+1}" if i > 0 else "This Week"

            if week_data.empty:
                output += f"{week_label}: Rest / No activities\n"
                continue

            total_activities = len(week_data)
            total_hours = week_data["moving_time"].sum() / 3600
            tss_col = "moving_training_stress_score" if "moving_training_stress_score" in week_data.columns else "training_stress_score"
            total_tss = week_data[tss_col].sum() if tss_col in week_data.columns else 0

            output += f"{week_label}: {total_activities} rides, {total_hours:.1f}h, TSS={total_tss:.0f}\n"

        return output

    def _format_activity_detail(self, row: pd.Series) -> str:
        """Format a single activity with details."""
        output = ""
        date_str = row["start_date_local"].strftime("%Y-%m-%d")
        dist_km = row["distance"] / 1000
        time_h = row["moving_time"] / 3600

        output += f"\n- {date_str}: {row['name']} ({row['sport_type']})\n"
        output += f"  {dist_km:.1f}km, {time_h:.1f}h"

        np_val = row.get("moving_normalized_power") or row.get("normalized_power")
        if pd.notna(np_val):
            output += f", NP={np_val:.0f}W"
        if pd.notna(row.get("intensity_factor")):
            output += f", IF={row['intensity_factor']:.2f}"

        tss_val = row.get("moving_training_stress_score") or row.get("training_stress_score")
        if pd.notna(tss_val):
            output += f", TSS={tss_val:.0f}"

        ftp_est = row.get("estimated_ftp")
        if pd.notna(ftp_est) and ftp_est > 0:
            weight = getattr(self.settings, 'rider_weight_kg', 75.0) if self.settings else 75.0
            output += f", Est.FTP={ftp_est:.0f}W ({ftp_est/weight:.2f} W/kg)"

        output += "\n"
        return output

    def _detect_referenced_activities(self, query: str, activities: pd.DataFrame) -> list:
        """
        Detect activities referenced in the user's query.

        Detection methods:
        1. Activity ID (e.g., "activity 12345", "ID 12345")
        2. Activity name (exact or partial match)
        3. Date reference (e.g., "yesterday", "January 15", "2026-01-15")
        4. Keywords like "last ride", "last activity", "today's ride"

        Returns:
            List of (activity_id, activity_row) tuples for matched activities.
        """
        matched = []
        query_lower = query.lower()

        # 1. Detect activity ID references
        id_patterns = [
            r'activity\s*[#]?(\d+)',
            r'id\s*[#:]?\s*(\d+)',
            r'#(\d{8,})',  # Activity IDs are typically long numbers
        ]
        for pattern in id_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                activity_id = int(match)
                if "id" in activities.columns:
                    row = activities[activities["id"] == activity_id]
                    if not row.empty:
                        matched.append((activity_id, row.iloc[0]))

        # 2. Detect "last ride/activity" references
        if any(phrase in query_lower for phrase in ["last ride", "last activity", "latest ride", "latest activity", "most recent"]):
            if not activities.empty:
                latest = activities.iloc[0]
                matched.append((latest.get("id"), latest))

        # 3. Detect "today/yesterday" references
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        if "today" in query_lower:
            today_activities = activities[activities["start_date_local"].dt.date == today]
            for _, row in today_activities.iterrows():
                matched.append((row.get("id"), row))

        if "yesterday" in query_lower:
            yesterday_activities = activities[activities["start_date_local"].dt.date == yesterday]
            for _, row in yesterday_activities.iterrows():
                matched.append((row.get("id"), row))

        # 4. Detect date patterns (YYYY-MM-DD or Month Day)
        date_patterns = [
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            (r'(\d{1,2}/\d{1,2}/\d{4})', '%m/%d/%Y'),
            (r'(\d{1,2}/\d{1,2}/\d{2})', '%m/%d/%y'),
        ]
        for pattern, date_format in date_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                try:
                    target_date = datetime.strptime(match, date_format).date()
                    date_activities = activities[activities["start_date_local"].dt.date == target_date]
                    for _, row in date_activities.iterrows():
                        matched.append((row.get("id"), row))
                except ValueError:
                    pass

        # 5. Detect activity names (fuzzy match)
        # Look for quoted strings or known activity names
        quoted_matches = re.findall(r'"([^"]+)"', query)
        quoted_matches += re.findall(r"'([^']+)'", query)
        for quoted in quoted_matches:
            name_matches = activities[
                activities["name"].str.lower().str.contains(quoted.lower(), na=False)
            ]
            for _, row in name_matches.head(3).iterrows():  # Limit to 3 matches
                matched.append((row.get("id"), row))

        # 6. Physiological / stream keyword fallback
        # When the query clearly asks about stream-level data (HR, power zones,
        # cadence, etc.) but doesn't reference any specific activity, auto-attach
        # the most recent activity so the AI has real data rather than claiming
        # it has "no access to stream data".
        if not matched:
            stream_keywords = (
                "heart rate", "heartrate", " hr ", "bpm", " hr,", "hr.",
                "power zone", "power distribution", "watt zone",
                "cadence", "cardiac drift", "aerobic decoupling",
                "vo2", "interval", "effort", "segment",
                "altitude", "elevation", "climb",
                "zone distribution", "training zone",
            )
            if any(kw in query_lower for kw in stream_keywords):
                if not activities.empty:
                    latest = activities.iloc[0]
                    matched.append((latest.get("id"), latest))

        # Deduplicate by activity ID
        seen_ids = set()
        unique_matched = []
        for activity_id, row in matched:
            if activity_id not in seen_ids and activity_id is not None:
                seen_ids.add(activity_id)
                unique_matched.append((activity_id, row))

        return unique_matched[:3]  # Limit to 3 activities max

    def _build_stream_context(self, referenced_activities: list) -> str:
        """
        Build detailed stream analysis for referenced activities.

        Includes:
        - Power distribution and zones
        - Heart rate patterns
        - Cadence analysis
        - Interval detection
        - Best efforts
        """
        output = ""

        for activity_id, activity_row in referenced_activities:
            name = activity_row.get("name", "Unknown")
            date_str = activity_row["start_date_local"].strftime("%Y-%m-%d")

            output += f"\n📊 Stream Analysis: {name} ({date_str})\n"
            output += f"   Activity ID: {activity_id}\n"

            # Load stream data
            try:
                stream = self.service.get_activity_stream(activity_id)
                output += f"   Stream loaded: {len(stream)} data points, columns: {list(stream.columns)}\n"
            except Exception as e:
                output += f"   ⚠️ Could not load stream: {e}\n"
                continue

            if stream.empty:
                output += "   ⚠️ No stream data available for this activity.\n"
                continue

            # Analyze stream data
            output += self._analyze_stream(stream, activity_row)

        return output

    def _build_streams_overview_context(self, activities: pd.DataFrame) -> str:
        """
        Compute cross-activity stream analytics by scanning the full streams directory.

        Instead of pre-processing a single activity's stream, iterates all
        available stream files and computes fleet-level physiological metrics:
        - Best sustained HR per duration window (rolling avg, 1–60 min)
        - HR distribution histogram (best 30-min avg per activity)
        - Best sustained power per duration window (power curve)
        - Data coverage and recency

        Results are cached per-instance keyed on stream file count to avoid
        re-scanning 1000+ files on every query.
        """
        from pathlib import Path

        streams_dir = self.service.get_streams_dir()
        if streams_dir is None:
            return ""

        streams_dir = Path(streams_dir)
        if not streams_dir.exists():
            return ""

        stream_files = sorted(streams_dir.glob("stream_*.csv"))
        if not stream_files:
            return ""

        # Instance-level cache keyed on file count (cheap staleness check)
        cache_key = len(stream_files)
        if getattr(self, "_streams_overview_cache_key", None) == cache_key:
            cached: str = getattr(self, "_streams_overview_cache", "")
            if cached:
                return cached

        # Build activity id → (date, name) lookup from the pre-loaded DataFrame
        id_to_meta: dict[str, tuple] = {}
        if not activities.empty and "id" in activities.columns:
            for _, row in activities.iterrows():
                try:
                    id_to_meta[str(int(row["id"]))] = (
                        row["start_date_local"],
                        row.get("name", "Unknown"),
                    )
                except (ValueError, TypeError):
                    pass

        WINDOWS: dict[str, int] = {
            "1 min":  60,
            "5 min":  300,
            "10 min": 600,
            "20 min": 1200,
            "30 min": 1800,
            "45 min": 2700,
            "60 min": 3600,
        }

        hr_results:  list[dict] = []
        pwr_results: list[dict] = []

        for sf in stream_files:
            act_id = sf.stem.replace("stream_", "")
            try:
                df = pd.read_csv(sf, sep=";")
            except Exception:
                continue

            pwr_col = (
                "watts" if "watts" in df.columns
                else "power" if "power" in df.columns
                else None
            )

            # Heart rate
            if "heartrate" in df.columns:
                hr = pd.to_numeric(df["heartrate"], errors="coerce").dropna()
                if len(hr) >= 60:
                    hr_s = pd.Series(hr.values)
                    row_hr: dict = {"id": act_id}
                    for label, w in WINDOWS.items():
                        if len(hr_s) >= w:
                            row_hr[label] = round(float(hr_s.rolling(w).mean().max()), 1)
                    hr_results.append(row_hr)

            # Power
            if pwr_col:
                pwr = pd.to_numeric(df[pwr_col], errors="coerce").dropna()
                if len(pwr) >= 60:
                    pwr_s = pd.Series(pwr.values)
                    row_pwr: dict = {"id": act_id}
                    for label, w in WINDOWS.items():
                        if len(pwr_s) >= w:
                            row_pwr[label] = round(float(pwr_s.rolling(w).mean().max()), 1)
                    pwr_results.append(row_pwr)

        output = "=== STREAMS DIRECTORY OVERVIEW ===\n"
        output += (
            f"Scanned {len(stream_files)} stream files: "
            f"{len(hr_results)} with HR data, {len(pwr_results)} with power data.\n"
        )

        def _best(results: list[dict], label: str) -> tuple:
            best_val: float | None = None
            best_date = ""
            best_name = ""
            for r in results:
                v = r.get(label)
                if v is not None and (best_val is None or v > best_val):
                    best_val = v
                    meta = id_to_meta.get(r["id"])
                    if meta:
                        dt = meta[0]
                        best_date = (
                            dt.strftime("%Y-%m-%d")
                            if hasattr(dt, "strftime")
                            else str(dt)[:10]
                        )
                        best_name = str(meta[1])
            return best_val, best_date, best_name

        # ── Best sustained HR per window ──────────────────────────────────────
        if hr_results:
            output += "\nBEST SUSTAINED HEART RATE (rolling-window best across all activities):\n"
            for label in WINDOWS:
                val, d, name = _best(hr_results, label)
                if val is not None:
                    output += f"  {label:8s}: {val:.1f} bpm   [{d}  {name}]\n"

            # HR distribution histogram over best 30-min average per activity
            vals_30 = [r["30 min"] for r in hr_results if r.get("30 min") is not None]
            if vals_30:
                bins = [0, 130, 140, 150, 155, 160, 165, 170, 175, 180, 185, 300]
                hist_labels = [
                    "<130", "130-139", "140-149", "150-154", "155-159",
                    "160-164", "165-169", "170-174", "175-179", "180-184", "185+",
                ]
                hist, _ = np.histogram(vals_30, bins=bins)
                output += "\nHR DISTRIBUTION — best 30-min rolling average per activity:\n"
                for lbl, cnt in zip(hist_labels, hist, strict=True):
                    bar = "█" * min(cnt, 40)
                    output += f"  {lbl:>8s}: {cnt:4d}  {bar}\n"

        # ── Best sustained power per window ───────────────────────────────────
        if pwr_results:
            ftp = getattr(self.settings, "ftp", 285.0) if self.settings else 285.0
            weight = getattr(self.settings, "rider_weight_kg", 77.0) if self.settings else 77.0
            output += (
                f"\nBEST SUSTAINED POWER (power curve, FTP={ftp:.0f}W, "
                f"{ftp/weight:.2f} W/kg):\n"
            )
            for label in WINDOWS:
                val, d, name = _best(pwr_results, label)
                if val is not None:
                    wkg = val / weight
                    pct = val / ftp * 100
                    output += (
                        f"  {label:8s}: {val:.0f}W  ({wkg:.2f} W/kg, {pct:.0f}% FTP)"
                        f"   [{d}  {name}]\n"
                    )

        # Cache result
        self._streams_overview_cache_key = cache_key
        self._streams_overview_cache = output
        return output

    def _analyze_stream(self, stream: pd.DataFrame, activity_row: pd.Series) -> str:
        """Analyze stream data and return formatted analysis."""
        output = ""
        ftp = getattr(self.settings, 'ftp', 285.0) if self.settings else 285.0
        weight = getattr(self.settings, 'rider_weight_kg', 77.0) if self.settings else 77.0

        # Available columns
        has_power = "watts" in stream.columns or "power" in stream.columns
        has_hr = "heartrate" in stream.columns or "heart_rate" in stream.columns
        has_cadence = "cadence" in stream.columns
        has_altitude = "altitude" in stream.columns
        has_velocity = "velocity_smooth" in stream.columns or "speed" in stream.columns

        power_col = "watts" if "watts" in stream.columns else "power" if "power" in stream.columns else None
        hr_col = "heartrate" if "heartrate" in stream.columns else "heart_rate" if "heart_rate" in stream.columns else None
        velocity_col = "velocity_smooth" if "velocity_smooth" in stream.columns else "speed" if "speed" in stream.columns else None

        output += f"   Stream length: {len(stream)} data points\n"

        # === POWER ANALYSIS ===
        if has_power and power_col:
            power = pd.to_numeric(stream[power_col], errors="coerce").dropna()
            if len(power) > 0:
                output += "\n   ⚡ POWER ANALYSIS:\n"

                # Basic stats
                avg_power = power.mean()
                max_power = power.max()
                output += f"      Avg: {avg_power:.0f}W, Max: {max_power:.0f}W\n"

                # Power zones (using 7-zone model)
                z1 = (power < ftp * 0.55).sum() / len(power) * 100
                z2 = ((power >= ftp * 0.55) & (power < ftp * 0.75)).sum() / len(power) * 100
                z3 = ((power >= ftp * 0.75) & (power < ftp * 0.90)).sum() / len(power) * 100
                z4 = ((power >= ftp * 0.90) & (power < ftp * 1.05)).sum() / len(power) * 100
                z5 = ((power >= ftp * 1.05) & (power < ftp * 1.20)).sum() / len(power) * 100
                z6 = ((power >= ftp * 1.20) & (power < ftp * 1.50)).sum() / len(power) * 100
                z7 = (power >= ftp * 1.50).sum() / len(power) * 100

                output += f"      Zone Distribution (FTP={ftp:.0f}W):\n"
                output += f"        Z1 (Recovery): {z1:.1f}%\n"
                output += f"        Z2 (Endurance): {z2:.1f}%\n"
                output += f"        Z3 (Tempo): {z3:.1f}%\n"
                output += f"        Z4 (Threshold): {z4:.1f}%\n"
                output += f"        Z5 (VO2max): {z5:.1f}%\n"
                output += f"        Z6 (Anaerobic): {z6:.1f}%\n"
                output += f"        Z7 (Neuromuscular): {z7:.1f}%\n"

                # Best efforts (rolling averages)
                output += "      Best Efforts:\n"
                for duration_name, seconds in [("5s", 5), ("30s", 30), ("1min", 60), ("5min", 300), ("20min", 1200)]:
                    if len(power) >= seconds:
                        rolling = power.rolling(window=seconds, min_periods=seconds).mean()
                        best = rolling.max()
                        if pd.notna(best):
                            wkg = best / weight
                            output += f"        {duration_name}: {best:.0f}W ({wkg:.2f} W/kg)\n"

                # Variability Index
                if avg_power > 0:
                    np_val = activity_row.get("moving_normalized_power") or activity_row.get("normalized_power")
                    if pd.notna(np_val) and np_val > 0:
                        vi = np_val / avg_power
                        output += f"      Variability Index: {vi:.2f}\n"

                # Detect intervals (power > 90% FTP for > 30 seconds)
                threshold = ftp * 0.90
                intervals = self._detect_intervals(power, threshold, min_duration=30)
                if intervals:
                    output += f"      Detected {len(intervals)} hard interval(s):\n"
                    for i, (start, end, avg_pwr) in enumerate(intervals[:5], 1):  # Show max 5
                        duration = end - start
                        output += f"        #{i}: {duration}s @ {avg_pwr:.0f}W avg\n"

        # === HEART RATE ANALYSIS ===
        if has_hr and hr_col:
            hr = pd.to_numeric(stream[hr_col], errors="coerce").dropna()
            if len(hr) > 0:
                output += "\n   ❤️ HEART RATE ANALYSIS:\n"
                max_hr = getattr(self.settings, 'max_hr', 185) if self.settings else 185

                avg_hr = hr.mean()
                max_hr_actual = hr.max()
                min_hr = hr.min()

                output += f"      Avg: {avg_hr:.0f} bpm, Max: {max_hr_actual:.0f} bpm, Min: {min_hr:.0f} bpm\n"

                # HR zones (5-zone model)
                z1_hr = (hr < max_hr * 0.60).sum() / len(hr) * 100
                z2_hr = ((hr >= max_hr * 0.60) & (hr < max_hr * 0.70)).sum() / len(hr) * 100
                z3_hr = ((hr >= max_hr * 0.70) & (hr < max_hr * 0.80)).sum() / len(hr) * 100
                z4_hr = ((hr >= max_hr * 0.80) & (hr < max_hr * 0.90)).sum() / len(hr) * 100
                z5_hr = (hr >= max_hr * 0.90).sum() / len(hr) * 100

                output += f"      HR Zone Distribution (Max HR={max_hr}):\n"
                output += f"        Z1 (<60%): {z1_hr:.1f}%\n"
                output += f"        Z2 (60-70%): {z2_hr:.1f}%\n"
                output += f"        Z3 (70-80%): {z3_hr:.1f}%\n"
                output += f"        Z4 (80-90%): {z4_hr:.1f}%\n"
                output += f"        Z5 (>90%): {z5_hr:.1f}%\n"

                # Cardiac drift (compare first half vs second half)
                if len(hr) > 100:
                    first_half = hr.iloc[:len(hr)//2].mean()
                    second_half = hr.iloc[len(hr)//2:].mean()
                    drift = ((second_half - first_half) / first_half) * 100
                    output += f"      Cardiac Drift: {drift:+.1f}%\n"

        # === CADENCE ANALYSIS ===
        if has_cadence:
            cadence = pd.to_numeric(stream["cadence"], errors="coerce").dropna()
            cadence_non_zero = cadence[cadence > 0]
            if len(cadence_non_zero) > 0:
                output += "\n   🔄 CADENCE ANALYSIS:\n"
                avg_cad = cadence_non_zero.mean()
                max_cad = cadence_non_zero.max()
                output += f"      Avg: {avg_cad:.0f} rpm, Max: {max_cad:.0f} rpm\n"

                # Cadence distribution
                low_cad = (cadence_non_zero < 80).sum() / len(cadence_non_zero) * 100
                mid_cad = ((cadence_non_zero >= 80) & (cadence_non_zero < 95)).sum() / len(cadence_non_zero) * 100
                high_cad = (cadence_non_zero >= 95).sum() / len(cadence_non_zero) * 100
                output += f"      Distribution: Low(<80rpm)={low_cad:.0f}%, Mid(80-95)={mid_cad:.0f}%, High(>95)={high_cad:.0f}%\n"

        # === ELEVATION/CLIMBING ANALYSIS ===
        if has_altitude:
            altitude = pd.to_numeric(stream["altitude"], errors="coerce").dropna()
            if len(altitude) > 1:
                output += "\n   ⛰️ ELEVATION ANALYSIS:\n"
                min_alt = altitude.min()
                max_alt = altitude.max()
                output += f"      Range: {min_alt:.0f}m - {max_alt:.0f}m ({max_alt - min_alt:.0f}m)\n"

                # Calculate total ascent/descent
                diff = altitude.diff()
                total_ascent = diff[diff > 0].sum()
                total_descent = abs(diff[diff < 0].sum())
                output += f"      Total Ascent: {total_ascent:.0f}m, Descent: {total_descent:.0f}m\n"

        # === SPEED ANALYSIS ===
        if has_velocity and velocity_col:
            velocity = pd.to_numeric(stream[velocity_col], errors="coerce").dropna()
            velocity_kmh = velocity * 3.6  # Convert m/s to km/h
            if len(velocity_kmh) > 0:
                output += "\n   🚀 SPEED ANALYSIS:\n"
                avg_speed = velocity_kmh.mean()
                max_speed = velocity_kmh.max()
                output += f"      Avg: {avg_speed:.1f} km/h, Max: {max_speed:.1f} km/h\n"

        # === GPS/ROUTE ANALYSIS ===
        has_gps = "latlng" in stream.columns
        if has_gps:
            output += self._analyze_gps_data(stream, activity_row)

        # ═══════════════════════════════════════════════════════════════════════
        # RAW STREAM DATA (sampled for visualizations/correlations)
        # ═══════════════════════════════════════════════════════════════════════
        output += self._format_raw_stream_data(stream, power_col, hr_col, velocity_col)

        return output

    def _format_raw_stream_data(self, stream: pd.DataFrame, power_col: str | None,
                                 hr_col: str | None, velocity_col: str | None) -> str:
        """
        Format raw stream data for AI analysis and visualization.

        Samples data to keep context size reasonable while preserving
        the ability to create scatter plots and correlations.
        """
        output = "\n   📈 RAW STREAM DATA (for visualization/correlation):\n"

        # Determine sample rate - aim for ~200-300 data points max
        n_points = len(stream)
        if n_points <= 300:
            sample_rate = 1
        elif n_points <= 1500:
            sample_rate = 5
        elif n_points <= 3000:
            sample_rate = 10
        else:
            sample_rate = max(1, n_points // 300)

        sampled = stream.iloc[::sample_rate].copy()
        output += f"      (Sampled every {sample_rate}s, {len(sampled)} points from {n_points} total)\n\n"

        # Build data table header
        cols_available = []
        col_headers = []

        if "time" in stream.columns:
            cols_available.append("time")
            col_headers.append("time_s")
        elif "elapsed_time" in stream.columns:
            cols_available.append("elapsed_time")
            col_headers.append("time_s")

        if power_col and power_col in stream.columns:
            cols_available.append(power_col)
            col_headers.append("power_w")

        if hr_col and hr_col in stream.columns:
            cols_available.append(hr_col)
            col_headers.append("hr_bpm")

        if "cadence" in stream.columns:
            cols_available.append("cadence")
            col_headers.append("cad_rpm")

        if velocity_col and velocity_col in stream.columns:
            cols_available.append(velocity_col)
            col_headers.append("speed_ms")

        if "altitude" in stream.columns:
            cols_available.append("altitude")
            col_headers.append("alt_m")

        if not cols_available:
            return "      No usable stream columns found.\n"

        # Output as CSV-like format for easy parsing
        output += "      " + ",".join(col_headers) + "\n"

        for _idx, row in sampled.iterrows():
            values = []
            for col in cols_available:
                val = row.get(col)
                if pd.isna(val):
                    values.append("")
                elif isinstance(val, float):
                    values.append(f"{val:.1f}")
                else:
                    values.append(str(val))
            output += "      " + ",".join(values) + "\n"

        output += "\n      Use this data for scatter plots, correlations, or trend analysis.\n"
        output += "      Columns: " + ", ".join(f"{h}={c}" for h, c in zip(col_headers, cols_available, strict=False)) + "\n"

        return output

    def _analyze_gps_data(self, stream: pd.DataFrame, activity_row: pd.Series) -> str:
        """
        Analyze GPS/route data from the stream.

        Provides:
        - Route bounding box (geographic extent)
        - Start/end coordinates with street names
        - Key waypoints with street names (via reverse geocoding)
        - Segment analysis with GPS coordinates
        """
        output = "\n   📍 GPS/ROUTE ANALYSIS:\n"

        try:
            # Parse latlng column - it may be stored as string "[lat, lng]" or list
            latlng = stream["latlng"].dropna()
            if len(latlng) == 0:
                return "      ⚠️ No GPS data available.\n"

            # Parse coordinates
            coords = []
            for val in latlng:
                if isinstance(val, str):
                    # Parse string like "[48.147227, 11.541671]"
                    val = val.strip("[]")
                    parts = val.split(",")
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0].strip())
                            lng = float(parts[1].strip())
                            coords.append((lat, lng))
                        except ValueError:
                            continue
                elif isinstance(val, (list, tuple)) and len(val) == 2:
                    coords.append((float(val[0]), float(val[1])))

            if len(coords) < 2:
                return "      ⚠️ Insufficient GPS data points.\n"

            # Extract lat/lng arrays
            lats = [c[0] for c in coords]
            lngs = [c[1] for c in coords]

            # Bounding box
            min_lat, max_lat = min(lats), max(lats)
            min_lng, max_lng = min(lngs), max(lngs)

            output += f"      Bounding Box: [{min_lat:.5f}, {min_lng:.5f}] to [{max_lat:.5f}, {max_lng:.5f}]\n"

            # Start and end points with reverse geocoding
            start_lat, start_lng = coords[0]
            end_lat, end_lng = coords[-1]

            # Geocode start location
            if GEOCODING_AVAILABLE:
                start_name = reverse_geocode_cached(round(start_lat, 4), round(start_lng, 4))
                end_name = reverse_geocode_cached(round(end_lat, 4), round(end_lng, 4))

                if start_name:
                    output += f"      Start: {start_name}\n"
                    output += f"              [{start_lat:.5f}, {start_lng:.5f}]\n"
                else:
                    output += f"      Start: [{start_lat:.5f}, {start_lng:.5f}]\n"

                if end_name:
                    output += f"      End: {end_name}\n"
                    output += f"           [{end_lat:.5f}, {end_lng:.5f}]\n"
                else:
                    output += f"      End: [{end_lat:.5f}, {end_lng:.5f}]\n"
            else:
                output += f"      Start: [{start_lat:.5f}, {start_lng:.5f}]\n"
                output += f"      End: [{end_lat:.5f}, {end_lng:.5f}]\n"

            # Check if it's a loop (start ~= end)
            from math import sqrt
            dist_start_end = sqrt((end_lat - start_lat)**2 + (end_lng - start_lng)**2)
            is_loop = dist_start_end < 0.001  # ~100m threshold
            output += f"      Route type: {'Loop (returns to start)' if is_loop else 'Point-to-point'}\n"

            # Sample key waypoints with street names (limit geocoding to save time)
            output += "\n      Key Waypoints with Street Names:\n"
            # Sample 5 waypoints (to limit geocoding calls - each takes 1+ second)
            sample_indices = [int(i * len(coords) / 5) for i in range(1, 5)]
            sample_indices = sorted(set(sample_indices))

            for idx in sample_indices[:4]:  # Max 4 waypoints (besides start/end)
                lat, lng = coords[idx]
                pct = idx / len(coords) * 100

                if GEOCODING_AVAILABLE:
                    location_name = reverse_geocode_cached(round(lat, 4), round(lng, 4))
                    if location_name:
                        output += f"        {pct:5.1f}%: {location_name}\n"
                    else:
                        output += f"        {pct:5.1f}%: [{lat:.5f}, {lng:.5f}]\n"
                else:
                    output += f"        {pct:5.1f}%: [{lat:.5f}, {lng:.5f}]\n"

            # Add segment analysis if altitude is available
            if "altitude" in stream.columns and "grade_smooth" in stream.columns:
                output += "\n      Significant Climbs/Descents:\n"
                output += self._analyze_segments_with_gps(stream, coords)

        except Exception as e:
            output += f"      ⚠️ Error analyzing GPS data: {e}\n"

        return output

    def _analyze_segments_with_gps(self, stream: pd.DataFrame, coords: list) -> str:
        """Analyze climbing/descending segments with GPS coordinates and street names."""
        output = ""

        try:
            altitude = pd.to_numeric(stream["altitude"], errors="coerce")
            grade = pd.to_numeric(stream["grade_smooth"], errors="coerce")

            # Find significant climbs (grade > 3% for > 60 seconds)
            in_climb = False
            climb_start = 0
            climbs = []

            for i in range(len(grade)):
                if pd.notna(grade.iloc[i]) and grade.iloc[i] > 3:
                    if not in_climb:
                        in_climb = True
                        climb_start = i
                else:
                    if in_climb and (i - climb_start) >= 60:
                        start_alt = altitude.iloc[climb_start] if pd.notna(altitude.iloc[climb_start]) else 0
                        end_alt = altitude.iloc[i-1] if pd.notna(altitude.iloc[i-1]) else 0
                        elevation_gain = end_alt - start_alt
                        if elevation_gain > 20:  # Only significant climbs
                            avg_grade = grade.iloc[climb_start:i].mean()
                            # Get GPS coords if available
                            if climb_start < len(coords):
                                start_coord = coords[climb_start]
                            else:
                                start_coord = coords[-1]
                            climbs.append({
                                "start_idx": climb_start,
                                "end_idx": i,
                                "duration_s": i - climb_start,
                                "elevation_m": elevation_gain,
                                "avg_grade": avg_grade,
                                "start_coord": start_coord
                            })
                    in_climb = False

            if climbs:
                output += f"        Found {len(climbs)} significant climb(s):\n"
                for j, climb in enumerate(climbs[:3], 1):  # Show max 3 (to limit geocoding)
                    lat, lng = climb["start_coord"]

                    # Try to get street name for the climb
                    location_name = None
                    if GEOCODING_AVAILABLE:
                        location_name = reverse_geocode_cached(round(lat, 4), round(lng, 4))

                    if location_name:
                        output += (f"          #{j}: {location_name}\n"
                                  f"              {climb['duration_s']}s, +{climb['elevation_m']:.0f}m @ {climb['avg_grade']:.1f}%\n")
                    else:
                        output += (f"          #{j}: {climb['duration_s']}s, "
                                  f"+{climb['elevation_m']:.0f}m @ {climb['avg_grade']:.1f}% "
                                  f"(starts at [{lat:.5f}, {lng:.5f}])\n")
            else:
                output += "        No significant climbs detected.\n"

            # Also detect significant descents
            in_descent = False
            descent_start = 0
            descents = []

            for i in range(len(grade)):
                if pd.notna(grade.iloc[i]) and grade.iloc[i] < -3:
                    if not in_descent:
                        in_descent = True
                        descent_start = i
                else:
                    if in_descent and (i - descent_start) >= 60:
                        start_alt = altitude.iloc[descent_start] if pd.notna(altitude.iloc[descent_start]) else 0
                        end_alt = altitude.iloc[i-1] if pd.notna(altitude.iloc[i-1]) else 0
                        elevation_loss = start_alt - end_alt
                        if elevation_loss > 20:
                            avg_grade = grade.iloc[descent_start:i].mean()
                            if descent_start < len(coords):
                                start_coord = coords[descent_start]
                            else:
                                start_coord = coords[-1]
                            descents.append({
                                "start_idx": descent_start,
                                "end_idx": i,
                                "duration_s": i - descent_start,
                                "elevation_m": elevation_loss,
                                "avg_grade": avg_grade,
                                "start_coord": start_coord
                            })
                    in_descent = False

            if descents:
                output += f"\n        Found {len(descents)} significant descent(s):\n"
                for j, descent in enumerate(descents[:3], 1):  # Show max 3
                    lat, lng = descent["start_coord"]

                    location_name = None
                    if GEOCODING_AVAILABLE:
                        location_name = reverse_geocode_cached(round(lat, 4), round(lng, 4))

                    if location_name:
                        output += (f"          #{j}: {location_name}\n"
                                  f"              {descent['duration_s']}s, -{descent['elevation_m']:.0f}m @ {descent['avg_grade']:.1f}%\n")
                    else:
                        output += (f"          #{j}: {descent['duration_s']}s, "
                                  f"-{descent['elevation_m']:.0f}m @ {descent['avg_grade']:.1f}% "
                                  f"(starts at [{lat:.5f}, {lng:.5f}])\n")

        except Exception as e:
            output += f"        ⚠️ Error in segment analysis: {e}\n"

        return output

    def _detect_intervals(self, power: pd.Series, threshold: float, min_duration: int = 30) -> list:
        """
        Detect intervals where power exceeds threshold for at least min_duration seconds.

        Returns list of (start_idx, end_idx, avg_power) tuples.
        """
        intervals = []
        in_interval = False
        interval_start = 0

        for i, p in enumerate(power):
            if p >= threshold:
                if not in_interval:
                    in_interval = True
                    interval_start = i
            else:
                if in_interval:
                    interval_end = i
                    duration = interval_end - interval_start
                    if duration >= min_duration:
                        avg_pwr = power.iloc[interval_start:interval_end].mean()
                        intervals.append((interval_start, interval_end, avg_pwr))
                    in_interval = False

        # Handle case where ride ends in an interval
        if in_interval:
            interval_end = len(power)
            duration = interval_end - interval_start
            if duration >= min_duration:
                avg_pwr = power.iloc[interval_start:interval_end].mean()
                intervals.append((interval_start, interval_end, avg_pwr))

        return intervals
