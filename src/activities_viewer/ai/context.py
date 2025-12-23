"""
Context builder for AI queries.
"""

import pandas as pd
from activities_viewer.services.activity_service import ActivityService


class ActivityContextBuilder:
    def __init__(self, service: ActivityService):
        self.service = service

    def build_context(self, query: str) -> str:
        """
        Build context for the LLM based on the user query.

        Args:
            query: The user's question.

        Returns:
            A string containing relevant context with all activities.
        """
        # Get all activities for comprehensive context
        activities = self.service.get_all_activities()

        context = "User's Complete Activity History:\n"
        if not activities.empty:
            # Sort by date descending for chronological order
            activities = activities.sort_values("start_date_local", ascending=False)

            for _, row in activities.iterrows():
                date_str = row["start_date_local"].strftime("%Y-%m-%d")
                dist_km = row["distance"] / 1000
                elev_m = row["total_elevation_gain"]
                time_h = row["moving_time"] / 3600

                context += f"- {date_str}: {row['name']} ({row['sport_type']})\n"
                context += f"  Distance: {dist_km:.1f}km, Elev: {elev_m:.0f}m, Time: {time_h:.1f}h\n"
                if "average_heartrate" in row and pd.notna(row["average_heartrate"]):
                    context += f"  Avg HR: {row['average_heartrate']:.0f} bpm\n"
                if "moving_normalized_power" in row and pd.notna(
                    row["moving_normalized_power"]
                ):
                    context += f"  NP: {row['moving_normalized_power']:.0f} W\n"
                if "moving_training_stress_score" in row and pd.notna(
                    row["moving_training_stress_score"]
                ):
                    context += f"  TSS: {row['moving_training_stress_score']:.0f}\n"
                context += "\n"
        else:
            context += "No activities found.\n"

        return context
