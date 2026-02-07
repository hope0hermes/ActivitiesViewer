"""Generate actionable training insights from metrics."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass
class Insight:
    """A single training insight/recommendation."""

    type: Literal["success", "warning", "info"]
    title: str
    message: str
    action: str | None = None


def generate_weekly_insights(
    df_week: pd.DataFrame,
    ctl: float,
    atl: float,
    tsb: float,
    acwr: float,
    weekly_tss: float,
) -> list[Insight]:
    """Generate insights for the current week.

    Args:
        df_week: Current week's activities
        ctl: Chronic Training Load
        atl: Acute Training Load
        tsb: Training Stress Balance
        acwr: Acute:Chronic Workload Ratio
        weekly_tss: Total TSS this week

    Returns:
        List of Insight objects
    """
    insights = []

    # ACWR check
    if acwr > 1.5:
        insights.append(
            Insight(
                type="warning",
                title="⚠️ Injury Risk Alert",
                message=f"ACWR is {acwr:.2f} (above 1.5 threshold).",
                action="Reduce training load by 20-30% for the next 3-5 days.",
            )
        )
    elif acwr < 0.8:
        insights.append(
            Insight(
                type="info",
                title="📉 Undertraining",
                message=f"ACWR is {acwr:.2f}. You may be losing fitness.",
                action="Consider gradually increasing training volume.",
            )
        )
    elif 0.8 <= acwr <= 1.3:
        insights.append(
            Insight(
                type="success",
                title="✅ Optimal Load",
                message=f"ACWR is {acwr:.2f} - in the sweet spot for adaptation.",
                action=None,
            )
        )

    # TSB check
    if tsb < -30:
        insights.append(
            Insight(
                type="warning",
                title="😴 Deep Fatigue",
                message=f"TSB is {tsb:.0f}. Significant accumulated fatigue.",
                action="Plan 1-2 recovery days before your next hard session.",
            )
        )
    elif tsb > 25:
        insights.append(
            Insight(
                type="info",
                title="🔋 Very Fresh",
                message=f"TSB is {tsb:.0f}. You're well-rested.",
                action="Good time for a hard workout or test effort.",
            )
        )
    elif 0 <= tsb <= 15:
        insights.append(
            Insight(
                type="success",
                title="🎯 Race Ready",
                message=f"TSB is {tsb:.0f}. Optimal freshness for performance.",
                action=None,
            )
        )

    # Rest days check
    if not df_week.empty:
        rest_days = 7 - len(df_week["start_date_local"].dt.date.unique())
        if rest_days == 0:
            insights.append(
                Insight(
                    type="warning",
                    title="🔴 No Rest Days",
                    message="You trained every day this week.",
                    action="Schedule at least 1 rest day to allow adaptation.",
                )
            )

    return insights


def render_insights(insights: list[Insight]) -> None:
    """Render insights using Streamlit."""
    import streamlit as st

    if not insights:
        return

    st.subheader("💡 Insights & Recommendations")

    for insight in insights:
        message = f"**{insight.title}**: {insight.message}"
        if insight.action:
            message += f"\n\n👉 **Action**: {insight.action}"

        if insight.type == "warning":
            st.warning(message)
        elif insight.type == "success":
            st.success(message)
        else:
            st.info(message)
