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

        Provides comprehensive training data including:
        - Basic activity info (name, distance, elevation, time)
        - Power metrics (NP, IF, TSS)
        - Heart rate metrics
        - Training Intensity Distribution (TID)
        - Efficiency Factor
        - Fatigue metrics (fatigue_index, cardiac_drift)
        - Performance Management (CTL, ATL, TSB, ACWR)

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

            # Add current training status from the most recent activity
            latest = activities.iloc[0]
            context += "\n=== CURRENT TRAINING STATUS ===\n"
            if pd.notna(latest.get("chronic_training_load")):
                context += f"CTL (Fitness): {latest['chronic_training_load']:.1f}\n"
            if pd.notna(latest.get("acute_training_load")):
                context += f"ATL (Fatigue): {latest['acute_training_load']:.1f}\n"
            if pd.notna(latest.get("training_stress_balance")):
                tsb = latest["training_stress_balance"]
                status = "Fresh" if tsb > 0 else "Fatigued"
                context += f"TSB (Form): {tsb:.1f} ({status})\n"
            if pd.notna(latest.get("acwr")):
                acwr = latest["acwr"]
                if acwr > 1.5:
                    risk = "HIGH INJURY RISK"
                elif acwr < 0.8:
                    risk = "Undertraining"
                else:
                    risk = "Optimal"
                context += f"ACWR: {acwr:.2f} ({risk})\n"
            context += "\n"

            context += "=== ACTIVITY HISTORY ===\n"
            for _, row in activities.iterrows():
                date_str = row["start_date_local"].strftime("%Y-%m-%d")
                dist_km = row["distance"] / 1000
                elev_m = row["total_elevation_gain"]
                time_h = row["moving_time"] / 3600

                context += f"\n- {date_str}: {row['name']} ({row['sport_type']})\n"
                context += f"  Distance: {dist_km:.1f}km, Elev: {elev_m:.0f}m, Time: {time_h:.1f}h\n"

                # Heart rate metrics
                if pd.notna(row.get("average_heartrate")):
                    context += f"  Avg HR: {row['average_heartrate']:.0f} bpm\n"

                # Power metrics
                if pd.notna(row.get("moving_normalized_power")):
                    context += f"  NP: {row['moving_normalized_power']:.0f} W"
                    if pd.notna(row.get("intensity_factor")):
                        context += f", IF: {row['intensity_factor']:.2f}"
                    context += "\n"
                if pd.notna(row.get("moving_training_stress_score")):
                    context += f"  TSS: {row['moving_training_stress_score']:.0f}\n"

                # Training Intensity Distribution (TID)
                tid_z1 = row.get("power_tid_z1_percentage")
                tid_z2 = row.get("power_tid_z2_percentage")
                tid_z3 = row.get("power_tid_z3_percentage")
                if pd.notna(tid_z1) and pd.notna(tid_z2) and pd.notna(tid_z3):
                    context += f"  TID: Z1={tid_z1:.0f}% Z2={tid_z2:.0f}% Z3={tid_z3:.0f}%\n"

                # Efficiency Factor
                if pd.notna(row.get("efficiency_factor")):
                    context += f"  Efficiency Factor: {row['efficiency_factor']:.2f}\n"

                # Fatigue metrics
                fatigue_idx = row.get("fatigue_index")
                cardiac_drift = row.get("cardiac_drift")
                if pd.notna(fatigue_idx) or pd.notna(cardiac_drift):
                    context += "  Fatigue:"
                    if pd.notna(fatigue_idx):
                        context += f" Index={fatigue_idx:.1f}%"
                    if pd.notna(cardiac_drift):
                        context += f" CardiacDrift={cardiac_drift:.1f}%"
                    context += "\n"

                # PMC snapshot for this activity
                ctl = row.get("chronic_training_load")
                atl = row.get("acute_training_load")
                tsb = row.get("training_stress_balance")
                if pd.notna(ctl) and pd.notna(atl) and pd.notna(tsb):
                    context += f"  PMC: CTL={ctl:.1f} ATL={atl:.1f} TSB={tsb:.1f}\n"

        else:
            context += "No activities found.\n"

        return context
