"""
Goal Service - The "brain" of the goal-driven approach.

This service calculates progress toward training goals and provides
status indicators to guide the user's training journey.
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from activities_viewer.domain.models import Goal


class GoalStatus(str, Enum):
    """
    Training goal status indicators.

    These statuses help the user understand if they're on track
    to achieve their goal on time.
    """

    AHEAD = "ahead"  # Current progress is ahead of expected curve
    ON_TRACK = "on_track"  # Current progress matches expected curve
    BEHIND = "behind"  # Current progress is behind but recoverable
    CRITICAL = "critical"  # Significantly behind, goal at risk


class GoalService:
    """
    Service for calculating goal progress and status.

    This service implements the logic to track progress toward a target
    power-to-weight ratio (e.g., 4.0 W/kg) and provides actionable insights.
    """

    def __init__(self):
        """Initialize the GoalService."""
        pass

    def calculate_progress(
        self, current_ftp: float, weight_kg: float, goal: Goal
    ) -> dict:
        """
        Calculate current progress toward goal.

        Args:
            current_ftp: Current Functional Threshold Power in watts
            weight_kg: Current body weight in kilograms
            goal: Goal object with target and timeline

        Returns:
            Dictionary containing:
                - current_wkg: Current power-to-weight ratio
                - target_wkg: Target power-to-weight ratio
                - progress_percentage: Percentage of goal achieved (0-100+)
                - wkg_remaining: W/kg improvement still needed
                - days_remaining: Days until target date
                - weeks_remaining: Weeks until target date
        """
        if weight_kg <= 0:
            raise ValueError("weight_kg must be positive")

        current_wkg = current_ftp / weight_kg
        total_improvement = goal.target_wkg - goal.start_wkg
        achieved_improvement = current_wkg - goal.start_wkg

        # Calculate progress percentage (can exceed 100% if ahead)
        if total_improvement > 0:
            progress_percentage = (achieved_improvement / total_improvement) * 100
        else:
            progress_percentage = 0.0

        return {
            "current_wkg": current_wkg,
            "target_wkg": goal.target_wkg,
            "progress_percentage": progress_percentage,
            "wkg_remaining": goal.target_wkg - current_wkg,
            "days_remaining": goal.days_remaining,
            "weeks_remaining": goal.weeks_remaining,
        }

    def get_required_ramp_rate(self, goal: Goal, current_wkg: float) -> float:
        """
        Calculate required W/kg gain per week to hit target on time.

        Args:
            goal: Goal object with target and timeline
            current_wkg: Current power-to-weight ratio

        Returns:
            Required weekly gain in W/kg. Returns 0 if goal date has passed.
        """
        if goal.weeks_remaining <= 0:
            return 0.0

        wkg_remaining = goal.target_wkg - current_wkg
        return wkg_remaining / goal.weeks_remaining

    def get_on_track_status(
        self,
        current_ftp: float,
        weight_kg: float,
        goal: Goal,
        tolerance_percentage: float = 10.0,
    ) -> GoalStatus:
        """
        Determine if the user is on track to meet their goal.

        The algorithm calculates the expected W/kg at the current point
        in time based on linear progression from start to target. It then
        compares actual progress to expected progress.

        Args:
            current_ftp: Current FTP in watts
            weight_kg: Current body weight in kg
            goal: Goal object with target and timeline
            tolerance_percentage: Acceptable deviation percentage (default 10%)

        Returns:
            GoalStatus enum indicating training status
        """
        if weight_kg <= 0:
            raise ValueError("weight_kg must be positive")

        current_wkg = current_ftp / weight_kg

        # Calculate how far through the goal timeline we are
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (datetime.now() - goal.start_date).days

        if total_days <= 0:
            # Goal timeline is invalid
            return GoalStatus.CRITICAL

        # Calculate expected W/kg at this point (linear progression)
        time_progress = elapsed_days / total_days
        total_improvement = goal.target_wkg - goal.start_wkg
        expected_wkg = goal.start_wkg + (total_improvement * time_progress)

        # Calculate deviation from expected
        deviation = current_wkg - expected_wkg
        deviation_percentage = (
            (deviation / total_improvement) * 100 if total_improvement > 0 else 0
        )

        # Determine status based on deviation
        if deviation_percentage > tolerance_percentage:
            return GoalStatus.AHEAD
        elif deviation_percentage >= -tolerance_percentage:
            return GoalStatus.ON_TRACK
        elif deviation_percentage >= -(tolerance_percentage * 2):
            return GoalStatus.BEHIND
        else:
            return GoalStatus.CRITICAL

    def get_expected_wkg_at_date(self, goal: Goal, target_date: datetime) -> float:
        """
        Calculate expected W/kg at a specific date based on linear progression.

        Args:
            goal: Goal object
            target_date: Date to calculate expected W/kg for

        Returns:
            Expected W/kg at the target date
        """
        total_days = (goal.target_date - goal.start_date).days
        elapsed_days = (target_date - goal.start_date).days

        if total_days <= 0:
            return goal.start_wkg

        # Linear interpolation
        time_progress = min(max(elapsed_days / total_days, 0), 1)  # Clamp 0-1
        total_improvement = goal.target_wkg - goal.start_wkg

        return goal.start_wkg + (total_improvement * time_progress)

    def get_goal_summary(
        self, current_ftp: float, weight_kg: float, goal: Goal
    ) -> dict:
        """
        Get a comprehensive summary of goal status.

        Args:
            current_ftp: Current FTP in watts
            weight_kg: Current body weight in kg
            goal: Goal object

        Returns:
            Dictionary with comprehensive goal metrics
        """
        progress = self.calculate_progress(current_ftp, weight_kg, goal)
        current_wkg = progress["current_wkg"]
        status = self.get_on_track_status(current_ftp, weight_kg, goal)
        required_rate = self.get_required_ramp_rate(goal, current_wkg)
        expected_wkg = self.get_expected_wkg_at_date(goal, datetime.now())

        return {
            **progress,
            "status": status,
            "status_label": status.value.replace("_", " ").title(),
            "required_weekly_gain": required_rate,
            "expected_wkg_now": expected_wkg,
            "ahead_behind_wkg": current_wkg - expected_wkg,
            "on_pace": status in [GoalStatus.AHEAD, GoalStatus.ON_TRACK],
        }
