"""
Analysis Service - The aggregation engine for metrics across time ranges.

This service implements the aggregation logic defined in Section 6 of the
refactoring plan, handling the proper aggregation of metrics across different
time scales (activity, week, month, year).
"""

from typing import List, Optional
import pandas as pd
import numpy as np
from datetime import datetime


class AnalysisService:
    """
    Service for aggregating and analyzing activity metrics.

    Most metrics are pre-calculated in activities_moving.csv. This service
    primarily handles **aggregation** over time ranges according to the
    metric-specific rules defined in the refactoring plan.
    """

    def __init__(self):
        """Initialize the AnalysisService."""
        pass

    # ========================================================================
    # LOAD METRICS - Summation
    # ========================================================================

    def aggregate_load(self, activities_df: pd.DataFrame) -> dict:
        """
        Aggregate load metrics (TSS, Volume, Work) over the given activities.

        Aggregation Logic: SUMMATION
        - TSS: Sum
        - Volume (hours): Sum
        - Work (kJ): Sum
        - Distance: Sum
        - Elevation: Sum

        Args:
            activities_df: DataFrame of activities to aggregate

        Returns:
            Dictionary with aggregated load metrics
        """
        if activities_df.empty:
            return {
                "total_tss": 0.0,
                "total_hours": 0.0,
                "total_kj": 0.0,
                "total_distance_km": 0.0,
                "total_elevation_m": 0.0,
                "activity_count": 0,
            }

        # Calculate totals (sum)
        total_tss = activities_df["training_stress_score"].fillna(0).sum()
        total_moving_time = activities_df["moving_time"].fillna(0).sum()
        total_kj = activities_df["kilojoules"].fillna(0).sum()
        total_distance = activities_df["distance"].fillna(0).sum()
        total_elevation = activities_df["total_elevation_gain"].fillna(0).sum()

        return {
            "total_tss": total_tss,
            "total_hours": total_moving_time / 3600,  # Convert seconds to hours
            "total_kj": total_kj,
            "total_distance_km": total_distance / 1000,  # Convert meters to km
            "total_elevation_m": total_elevation,
            "activity_count": len(activities_df),
            "avg_tss_per_activity": total_tss / len(activities_df)
            if len(activities_df) > 0
            else 0,
            "avg_hours_per_activity": (total_moving_time / 3600) / len(activities_df)
            if len(activities_df) > 0
            else 0,
        }

    # ========================================================================
    # INTENSITY METRICS - Time-Weighted Average
    # ========================================================================

    def aggregate_intensity(self, activities_df: pd.DataFrame) -> dict:
        """
        Aggregate intensity metrics (IF, Normalized Power) over activities.

        Aggregation Logic: TIME-WEIGHTED AVERAGE
        - Intensity Factor (IF): Weighted by moving time
        - Normalized Power: Weighted by moving time

        Args:
            activities_df: DataFrame of activities to aggregate

        Returns:
            Dictionary with aggregated intensity metrics
        """
        if activities_df.empty:
            return {
                "avg_intensity_factor": 0.0,
                "avg_normalized_power": 0.0,
                "avg_power": 0.0,
            }

        # Filter out rows with NaN in key columns
        valid_if = activities_df[
            activities_df["intensity_factor"].notna()
            & activities_df["moving_time"].notna()
        ]

        valid_np = activities_df[
            activities_df["normalized_power"].notna()
            & activities_df["moving_time"].notna()
        ]

        valid_power = activities_df[
            activities_df["average_watts"].notna()
            & activities_df["moving_time"].notna()
        ]

        # Calculate time-weighted averages
        if not valid_if.empty:
            total_time_if = valid_if["moving_time"].sum()
            avg_if = (
                valid_if["intensity_factor"] * valid_if["moving_time"]
            ).sum() / total_time_if
        else:
            avg_if = 0.0

        if not valid_np.empty:
            total_time_np = valid_np["moving_time"].sum()
            avg_np = (
                valid_np["normalized_power"] * valid_np["moving_time"]
            ).sum() / total_time_np
        else:
            avg_np = 0.0

        if not valid_power.empty:
            total_time_power = valid_power["moving_time"].sum()
            avg_power = (
                valid_power["average_watts"] * valid_power["moving_time"]
            ).sum() / total_time_power
        else:
            avg_power = 0.0

        return {
            "avg_intensity_factor": avg_if,
            "avg_normalized_power": avg_np,
            "avg_power": avg_power,
        }

    # ========================================================================
    # TRAINING INTENSITY DISTRIBUTION (TID)
    # ========================================================================

    def aggregate_tid(self, activities_df: pd.DataFrame) -> dict:
        """
        Aggregate Training Intensity Distribution across activities.

        Aggregation Logic: Sum zone times, recalculate percentages
        - Sum time in each zone across all activities
        - Recalculate percentages based on total time

        Args:
            activities_df: DataFrame of activities to aggregate

        Returns:
            Dictionary with TID percentages for Z1, Z2, Z3
        """
        if activities_df.empty:
            return {
                "tid_z1_percentage": 0.0,
                "tid_z2_percentage": 0.0,
                "tid_z3_percentage": 0.0,
            }

        # Sum time in each TID zone weighted by moving time
        valid_data = activities_df[
            activities_df["power_tid_z1_percentage"].notna()
            & activities_df["power_tid_z2_percentage"].notna()
            & activities_df["power_tid_z3_percentage"].notna()
            & activities_df["moving_time"].notna()
        ]

        if valid_data.empty:
            return {
                "tid_z1_percentage": 0.0,
                "tid_z2_percentage": 0.0,
                "tid_z3_percentage": 0.0,
            }

        # Calculate actual time in each zone (percentage * moving_time)
        z1_time = (
            valid_data["power_tid_z1_percentage"] * valid_data["moving_time"] / 100
        ).sum()
        z2_time = (
            valid_data["power_tid_z2_percentage"] * valid_data["moving_time"] / 100
        ).sum()
        z3_time = (
            valid_data["power_tid_z3_percentage"] * valid_data["moving_time"] / 100
        ).sum()

        total_time = z1_time + z2_time + z3_time

        if total_time > 0:
            return {
                "tid_z1_percentage": (z1_time / total_time) * 100,
                "tid_z2_percentage": (z2_time / total_time) * 100,
                "tid_z3_percentage": (z3_time / total_time) * 100,
            }
        else:
            return {
                "tid_z1_percentage": 0.0,
                "tid_z2_percentage": 0.0,
                "tid_z3_percentage": 0.0,
            }

    # ========================================================================
    # PHYSIOLOGY METRICS - Filtered Average for Z2 Rides
    # ========================================================================

    def aggregate_physiology(
        self, activities_df: pd.DataFrame, filter_steady_state: bool = True
    ) -> dict:
        """
        Aggregate physiology metrics (EF, Decoupling) with smart filtering.

        Aggregation Logic: FILTER then AVERAGE
        - Filter for Z2/Steady rides (IF < 0.75, exclude races/intervals)
        - Average Efficiency Factor
        - Average Power:HR Decoupling

        Args:
            activities_df: DataFrame of activities to aggregate
            filter_steady_state: If True, filter out non-steady-state rides

        Returns:
            Dictionary with aggregated physiology metrics
        """
        if activities_df.empty:
            return {
                "avg_efficiency_factor": 0.0,
                "avg_decoupling": 0.0,
                "filtered_activity_count": 0,
            }

        df = activities_df.copy()

        # Smart filtering for steady-state rides (critical for EF trends)
        if filter_steady_state:
            # Filter criteria:
            # 1. Intensity < 0.75 (Z2 or easier)
            # 2. Not a race (workout_type != 10)
            # 3. Has valid EF and decoupling data
            df = df[
                (df["intensity_factor"].notna())
                & (df["intensity_factor"] < 0.75)
                & ((df["workout_type"].isna()) | (df["workout_type"] != 10))
                & (df["efficiency_factor"].notna())
                & (df["power_hr_decoupling"].notna())
            ]

        if df.empty:
            return {
                "avg_efficiency_factor": 0.0,
                "avg_decoupling": 0.0,
                "filtered_activity_count": 0,
            }

        # Simple average for these metrics
        avg_ef = df["efficiency_factor"].mean()
        avg_decoupling = df["power_hr_decoupling"].mean()

        return {
            "avg_efficiency_factor": avg_ef,
            "avg_decoupling": avg_decoupling,
            "filtered_activity_count": len(df),
        }

    # ========================================================================
    # POWER CURVE - Max of Max
    # ========================================================================

    def get_power_curve_max(self, activities_df: pd.DataFrame) -> dict:
        """
        Calculate the best power curve across all activities.

        Aggregation Logic: MAX of MAX
        - For each duration (1s, 5s, 1min, etc.), take the maximum value

        Args:
            activities_df: DataFrame of activities

        Returns:
            Dictionary with best power for each duration
        """
        power_curve_columns = [
            "power_curve_1sec",
            "power_curve_2sec",
            "power_curve_5sec",
            "power_curve_10sec",
            "power_curve_15sec",
            "power_curve_20sec",
            "power_curve_30sec",
            "power_curve_1min",
            "power_curve_2min",
            "power_curve_5min",
            "power_curve_10min",
            "power_curve_15min",
            "power_curve_20min",
            "power_curve_30min",
            "power_curve_1hr",
        ]

        result = {}

        for col in power_curve_columns:
            if col in activities_df.columns:
                max_val = activities_df[col].max()
                result[col] = max_val if pd.notna(max_val) else 0.0
            else:
                result[col] = 0.0

        return result

    # ========================================================================
    # PERFORMANCE MANAGEMENT CHART (PMC) DATA
    # ========================================================================

    def get_pmc_data(self, activities_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract Performance Management Chart time-series data.

        Returns CTL (Fitness), ATL (Fatigue), TSB (Form) over time.

        Args:
            activities_df: DataFrame of activities with PMC columns

        Returns:
            DataFrame with date, ctl, atl, tsb columns
        """
        if activities_df.empty:
            return pd.DataFrame(columns=["date", "ctl", "atl", "tsb"])

        required_cols = [
            "start_date_local",
            "chronic_training_load",
            "acute_training_load",
            "training_stress_balance",
        ]

        if not all(col in activities_df.columns for col in required_cols):
            return pd.DataFrame(columns=["date", "ctl", "atl", "tsb"])

        pmc_df = activities_df[required_cols].copy()
        pmc_df = pmc_df.rename(
            columns={
                "start_date_local": "date",
                "chronic_training_load": "ctl",
                "acute_training_load": "atl",
                "training_stress_balance": "tsb",
            }
        )

        # Sort by date
        pmc_df = pmc_df.sort_values("date")

        return pmc_df

    # ========================================================================
    # EFFICIENCY TRENDS
    # ========================================================================

    def get_efficiency_trends(
        self, activities_df: pd.DataFrame, filter_steady_state: bool = True
    ) -> pd.DataFrame:
        """
        Get time-series data for efficiency metrics.

        Args:
            activities_df: DataFrame of activities
            filter_steady_state: If True, filter for Z2 rides only

        Returns:
            DataFrame with date, efficiency_factor, decoupling columns
        """
        if activities_df.empty:
            return pd.DataFrame(columns=["date", "efficiency_factor", "decoupling"])

        df = activities_df.copy()

        # Apply the same smart filtering as aggregate_physiology
        if filter_steady_state:
            df = df[
                (df["efficiency_factor"].notna())
                & (df["efficiency_factor"] > 0)
                & (df["intensity_factor"].notna())
                & (df["intensity_factor"] < 0.75)
                & ((df["workout_type"].isna()) | (df["workout_type"] != 10))
            ]
        else:
            # Always exclude NaN or zero efficiency_factor (no power meter or no data)
            df = df[(df["efficiency_factor"].notna()) & (df["efficiency_factor"] > 0)]

        if df.empty:
            return pd.DataFrame(columns=["date", "efficiency_factor", "decoupling", "cardiac_drift"])

        # Select relevant columns
        result = df[
            ["start_date_local", "efficiency_factor", "power_hr_decoupling", "cardiac_drift"]
        ].copy()
        result = result.rename(
            columns={"start_date_local": "date", "power_hr_decoupling": "decoupling"}
        )

        # Sort by date
        result = result.sort_values("date")

        return result

    # ========================================================================
    # COMPREHENSIVE PERIOD ANALYSIS
    # ========================================================================

    def analyze_period(self, activities_df: pd.DataFrame) -> dict:
        """
        Perform comprehensive analysis of a time period.

        This is the main aggregation method that combines all the above
        to provide a complete picture of the training period.

        Args:
            activities_df: DataFrame of activities in the period

        Returns:
            Dictionary with all aggregated metrics
        """
        load = self.aggregate_load(activities_df)
        intensity = self.aggregate_intensity(activities_df)
        tid = self.aggregate_tid(activities_df)
        physiology = self.aggregate_physiology(activities_df)
        power_curve = self.get_power_curve_max(activities_df)

        return {
            "load": load,
            "intensity": intensity,
            "tid": tid,
            "physiology": physiology,
            "power_curve": power_curve,
        }

    # ========================================================================
    # RECOVERY METRICS - Monotony, Strain, Rest Days
    # ========================================================================

    def get_recovery_metrics(
        self, activities_df: pd.DataFrame, period_days: int = 7
    ) -> dict:
        """
        Calculate recovery metrics: Monotony Index, Strain Index, Rest Days.

        These metrics help identify overtraining risk:
        - Monotony: High values (>2.0) indicate repetitive training (injury risk)
        - Strain: High values (>6000) indicate excessive load (burnout risk)
        - Rest Days: Count of days with TSS < 20

        Args:
            activities_df: DataFrame of activities
            period_days: Number of days in the period (default: 7 for weekly)

        Returns:
            Dictionary with recovery metrics
        """
        if activities_df.empty or "training_stress_score" not in activities_df.columns:
            return {
                "monotony_index": 0.0,
                "strain_index": 0.0,
                "rest_days": 0,
                "weekly_tss": 0.0,
                "daily_tss_values": [],
            }

        # Ensure datetime column
        df = activities_df.copy()
        if "start_date_local" in df.columns:
            df["start_date_local"] = pd.to_datetime(df["start_date_local"])
            if df["start_date_local"].dt.tz is not None:
                df["start_date_local"] = df["start_date_local"].dt.tz_localize(None)
        else:
            return {
                "monotony_index": 0.0,
                "strain_index": 0.0,
                "rest_days": 0,
                "weekly_tss": 0.0,
                "daily_tss_values": [],
            }

        # Get date range
        start_date = df["start_date_local"].min()
        end_date = df["start_date_local"].max()

        # Create complete period with all days
        date_range = pd.date_range(
            start=start_date.normalize(), end=end_date.normalize(), freq="D"
        )

        # Group activities by date and sum TSS
        df["date_local"] = df["start_date_local"].dt.date
        daily_tss = df.groupby("date_local")["training_stress_score"].sum()

        # Create full period with 0 for days without activities
        daily_tss_full = pd.Series(0.0, index=date_range.date)
        daily_tss_full.update(daily_tss)
        daily_tss_values = daily_tss_full.values

        # Calculate Monotony Index (mean / std)
        if len(daily_tss_values) > 1 and daily_tss_values.std() > 0:
            monotony = daily_tss_values.mean() / daily_tss_values.std()
        else:
            monotony = 0.0

        # Calculate Strain Index (total TSS × monotony)
        weekly_tss = daily_tss_values.sum()
        strain = weekly_tss * monotony

        # Calculate Rest Days (TSS < 20)
        rest_days = int((daily_tss_values < 20).sum())

        return {
            "monotony_index": monotony,
            "strain_index": strain,
            "rest_days": rest_days,
            "weekly_tss": weekly_tss,
            "daily_tss_values": daily_tss_values.tolist(),
            "avg_daily_tss": daily_tss_values.mean(),
            "max_daily_tss": daily_tss_values.max(),
        }

    def classify_training_phase(
        self,
        activities_df: pd.DataFrame,
        previous_period_df: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Classify the training phase based on volume and intensity trends.

        Phases:
        - Base: Volume increasing, intensity stable or low
        - Build: Volume stable/high, intensity increasing
        - Peak: Both volume and intensity high
        - Recovery/Taper: Volume decreasing
        - Transition: Low volume and intensity

        Args:
            activities_df: Current period activities
            previous_period_df: Previous period for comparison (optional)

        Returns:
            Dictionary with phase classification and metrics
        """
        if activities_df.empty:
            return {
                "phase": "Unknown",
                "confidence": 0.0,
                "volume_trend": 0.0,
                "intensity_trend": 0.0,
                "description": "No data available",
            }

        # Calculate current metrics
        current_load = self.aggregate_load(activities_df)
        current_intensity = self.aggregate_intensity(activities_df)

        current_volume = current_load["total_hours"]
        current_if = current_intensity["avg_intensity_factor"]

        # If no previous period, classify based on absolute values
        if previous_period_df is None or previous_period_df.empty:
            if current_if > 0.80:
                phase = "Build/Peak"
                confidence = 0.6
                description = "High intensity training detected"
            elif current_volume > 10:  # >10 hours/week
                phase = "Base Building"
                confidence = 0.6
                description = "High volume training detected"
            elif current_volume < 5:
                phase = "Recovery/Transition"
                confidence = 0.6
                description = "Low volume period"
            else:
                phase = "General Training"
                confidence = 0.5
                description = "Moderate volume and intensity"

            return {
                "phase": phase,
                "confidence": confidence,
                "volume_trend": 0.0,
                "intensity_trend": 0.0,
                "description": description,
                "current_volume_hours": current_volume,
                "current_avg_if": current_if,
            }

        # Calculate previous metrics for comparison
        prev_load = self.aggregate_load(previous_period_df)
        prev_intensity = self.aggregate_intensity(previous_period_df)

        prev_volume = prev_load["total_hours"]
        prev_if = prev_intensity["avg_intensity_factor"]

        # Calculate trends (% change)
        volume_trend = (
            ((current_volume - prev_volume) / prev_volume * 100)
            if prev_volume > 0
            else 0
        )
        intensity_trend = ((current_if - prev_if) / prev_if * 100) if prev_if > 0 else 0

        # Classify phase based on trends
        if volume_trend > 10 and abs(intensity_trend) < 10:
            phase = "Base Building"
            confidence = 0.8
            description = f"Volume up {volume_trend:.0f}%, intensity stable"
        elif volume_trend > 10 and intensity_trend > 10:
            phase = "Overload (Risky)"
            confidence = 0.9
            description = f"⚠️ Both volume (+{volume_trend:.0f}%) and intensity (+{intensity_trend:.0f}%) increasing"
        elif abs(volume_trend) < 10 and intensity_trend > 10:
            phase = "Build/Intensification"
            confidence = 0.8
            description = f"Volume stable, intensity up {intensity_trend:.0f}%"
        elif volume_trend < -20:
            phase = "Taper/Recovery"
            confidence = 0.9
            description = f"Volume down {abs(volume_trend):.0f}%"
        elif current_if > 0.85 and current_volume > 8:
            phase = "Peak/Race Prep"
            confidence = 0.7
            description = "High intensity and volume maintained"
        elif current_volume < 5 and current_if < 0.70:
            phase = "Transition/Off-Season"
            confidence = 0.8
            description = "Low volume and intensity"
        else:
            phase = "Maintenance"
            confidence = 0.6
            description = "Stable training load"

        return {
            "phase": phase,
            "confidence": confidence,
            "volume_trend": volume_trend,
            "intensity_trend": intensity_trend,
            "description": description,
            "current_volume_hours": current_volume,
            "current_avg_if": current_if,
            "previous_volume_hours": prev_volume,
            "previous_avg_if": prev_if,
        }
