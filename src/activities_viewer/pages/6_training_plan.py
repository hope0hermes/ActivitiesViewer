"""
Training Plan Page.

Generate and track periodized training plans based on goals.
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from activities_viewer.services.activity_service import ActivityService
from activities_viewer.services.training_plan_service import TrainingPlanService
from activities_viewer.services.analysis_service import AnalysisService
from activities_viewer.domain.models import TrainingPlan, WeeklyPlan
from activities_viewer.config import Settings
from activities_viewer.ai.client import GeminiClient

st.set_page_config(page_title="Training Plan", page_icon="📋", layout="wide")


def get_plan_file_path(settings: Settings) -> Path:
    """Get the path to the training plan file."""
    plan_file = getattr(settings, "training_plan_file", None)
    if plan_file:
        return Path(plan_file)
    # Fallback to current working directory
    return Path.cwd() / "training_plan.json"


def init_services(settings: Settings) -> ActivityService:
    """Initialize activity service for plan tracking."""
    from pathlib import Path
    from activities_viewer.repository.csv_repo import CSVActivityRepository

    raw_file = (
        settings.activities_raw_file
        if hasattr(settings, "activities_raw_file")
        else settings.activities_enriched_file
    )
    moving_file = (
        settings.activities_moving_file
        if hasattr(settings, "activities_moving_file")
        else None
    )
    repo = CSVActivityRepository(raw_file, moving_file, settings.streams_dir)
    return ActivityService(repo)


def render_plan_generator(settings: Settings) -> TrainingPlan | None:
    """Render the plan generation form."""
    st.subheader("📝 Create New Training Plan")

    with st.form("plan_generator"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Goal Settings")
            plan_name = st.text_input("Plan Name", value="FTP Improvement Plan")

            current_ftp = st.number_input(
                "Current FTP (watts)",
                min_value=100,
                max_value=500,
                value=int(settings.ftp) if settings.ftp else 250,
            )

            target_ftp = st.number_input(
                "Target FTP (watts)",
                min_value=100,
                max_value=600,
                value=int(settings.ftp * 1.15) if settings.ftp else 290,
                help="Typical improvement: 10-20% over 6 months",
            )

            weight = st.number_input(
                "Weight (kg)",
                min_value=40.0,
                max_value=150.0,
                value=settings.weight_kg if settings.weight_kg else 75.0,
                step=0.5,
            )

            # Calculate W/kg
            current_wkg = current_ftp / weight
            target_wkg = target_ftp / weight
            st.info(
                f"W/kg: {current_wkg:.2f} → {target_wkg:.2f} "
                f"(+{((target_wkg - current_wkg) / current_wkg * 100):.1f}%)"
            )

        with col2:
            st.markdown("#### Time & Schedule")

            start_date = st.date_input(
                "Plan Start Date",
                value=datetime.now().date(),
            )

            plan_duration = st.selectbox(
                "Plan Duration",
                options=[8, 12, 16, 20, 24],
                index=2,
                format_func=lambda x: f"{x} weeks ({x // 4} months)",
            )

            end_date = start_date + timedelta(weeks=plan_duration)
            st.write(f"**End Date:** {end_date.strftime('%Y-%m-%d')}")

            hours_per_week = st.slider(
                "Hours Available per Week",
                min_value=4.0,
                max_value=20.0,
                value=settings.weekly_hours_available if hasattr(settings, "weekly_hours_available") else 10.0,
                step=0.5,
            )

            current_ctl = st.number_input(
                "Current CTL (Fitness)",
                min_value=0,
                max_value=200,
                value=50,
                help="Your current Chronic Training Load",
            )

        st.markdown("#### Key Events (Optional)")
        st.caption("Add A-races (peak events), B-races (important), or C-races (training)")

        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            event_name = st.text_input("Event Name", key="event_name")
        with col2:
            event_date = st.date_input("Event Date", key="event_date", value=end_date)
        with col3:
            event_priority = st.selectbox("Priority", ["A", "B", "C"], key="event_priority")
        with col4:
            add_event = st.form_submit_button("Add Event")

        # Store events in session state
        if "plan_events" not in st.session_state:
            st.session_state.plan_events = []

        if add_event and event_name:
            st.session_state.plan_events.append({
                "name": event_name,
                "date": event_date.strftime("%Y-%m-%d"),
                "priority": event_priority,
            })

        # Show added events
        if st.session_state.plan_events:
            st.write("**Added Events:**")
            for i, event in enumerate(st.session_state.plan_events):
                st.write(f"  {i + 1}. {event['name']} ({event['priority']}) - {event['date']}")

        submitted = st.form_submit_button("🚀 Generate Plan", type="primary")

        if submitted:
            service = TrainingPlanService()
            plan = service.generate_plan(
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time()),
                start_ftp=float(current_ftp),
                target_ftp=float(target_ftp),
                weight_kg=weight,
                hours_per_week=hours_per_week,
                key_events=st.session_state.plan_events,
                current_ctl=float(current_ctl),
                plan_name=plan_name,
            )
            return plan

    return None


def render_plan_overview(plan: TrainingPlan):
    """Render plan overview metrics."""
    st.subheader(f"📋 {plan.name}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Duration",
            f"{plan.total_weeks} weeks",
            f"{plan.total_weeks // 4} months",
        )
    with col2:
        st.metric(
            "FTP Goal",
            f"{plan.target_ftp:.0f}W",
            f"+{plan.ftp_improvement_pct:.1f}%",
        )
    with col3:
        target_wkg = plan.target_ftp / plan.weight_kg
        st.metric(
            "W/kg Goal",
            f"{target_wkg:.2f}",
            f"+{target_wkg - plan.start_ftp / plan.weight_kg:.2f}",
        )
    with col4:
        st.metric(
            "Progress",
            f"{plan.progress_pct:.0f}%",
            f"Week {plan.current_week}",
        )

    # Phase breakdown
    st.markdown("#### Training Phases")
    phase_data = []
    for phase in plan.phases:
        phase_data.append({
            "Phase": phase.name,
            "Weeks": phase.weeks,
            "Focus": phase.description,
            "Z1/Z2/Z3": f"{phase.tid_z1:.0f}%/{phase.tid_z2:.0f}%/{phase.tid_z3:.0f}%",
        })
    st.dataframe(
        pd.DataFrame(phase_data),
        use_container_width=True,
        hide_index=True,
    )


def render_plan_chart(plan: TrainingPlan):
    """Render visual plan chart with TSS and CTL progression."""
    st.subheader("📊 Plan Visualization")

    # Prepare data
    weeks = plan.weeks
    week_nums = [w.week_number for w in weeks]
    target_tss = [w.target_tss for w in weeks]
    target_ctl = [w.target_ctl for w in weeks]
    actual_tss = [w.actual_tss if w.actual_tss else 0 for w in weeks]
    phases = [w.phase for w in weeks]

    # Create figure
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Weekly TSS (Planned vs Actual)", "CTL Progression"),
        row_heights=[0.6, 0.4],
    )

    # Phase colors
    phase_colors = {
        "Base": "rgba(100, 149, 237, 0.3)",  # Cornflower blue
        "Build": "rgba(255, 165, 0, 0.3)",  # Orange
        "Specialty": "rgba(255, 99, 71, 0.3)",  # Tomato
        "Taper": "rgba(144, 238, 144, 0.3)",  # Light green
        "Recovery": "rgba(200, 200, 200, 0.3)",  # Gray
        "Maintenance": "rgba(186, 85, 211, 0.3)",  # Medium orchid
    }

    # Add phase backgrounds
    current_phase = None
    phase_start = 0
    for i, phase in enumerate(phases + [None]):
        if phase != current_phase:
            if current_phase is not None:
                color = phase_colors.get(current_phase, "rgba(200, 200, 200, 0.2)")
                for row in [1, 2]:
                    fig.add_vrect(
                        x0=phase_start + 0.5,
                        x1=i + 0.5,
                        fillcolor=color,
                        layer="below",
                        line_width=0,
                        row=row,
                        col=1,
                    )
            current_phase = phase
            phase_start = i

    # Target TSS bars
    fig.add_trace(
        go.Bar(
            x=week_nums,
            y=target_tss,
            name="Target TSS",
            marker_color="rgba(55, 128, 191, 0.6)",
            marker_line_color="rgba(55, 128, 191, 1)",
            marker_line_width=1,
        ),
        row=1,
        col=1,
    )

    # Actual TSS bars
    fig.add_trace(
        go.Bar(
            x=week_nums,
            y=actual_tss,
            name="Actual TSS",
            marker_color="rgba(50, 171, 96, 0.8)",
            marker_line_color="rgba(50, 171, 96, 1)",
            marker_line_width=1,
        ),
        row=1,
        col=1,
    )

    # Target CTL line
    fig.add_trace(
        go.Scatter(
            x=week_nums,
            y=target_ctl,
            name="Target CTL",
            mode="lines+markers",
            line=dict(color="rgba(219, 64, 82, 0.9)", width=2),
            marker=dict(size=6),
        ),
        row=2,
        col=1,
    )

    # Actual CTL (if available)
    actual_ctl = [w.actual_ctl for w in weeks if w.actual_ctl is not None]
    if actual_ctl:
        ctl_weeks = [w.week_number for w in weeks if w.actual_ctl is not None]
        fig.add_trace(
            go.Scatter(
                x=ctl_weeks,
                y=actual_ctl,
                name="Actual CTL",
                mode="lines+markers",
                line=dict(color="rgba(50, 171, 96, 0.9)", width=2, dash="dot"),
                marker=dict(size=6),
            ),
            row=2,
            col=1,
        )

    # Mark current week
    current_week = plan.current_week
    if 1 <= current_week <= plan.total_weeks:
        for row in [1, 2]:
            fig.add_vline(
                x=current_week,
                line_dash="dash",
                line_color="red",
                annotation_text="Now",
                row=row,
                col=1,
            )

    # Mark events
    for event in plan.key_events:
        event_week = (event.date - plan.start_date).days // 7 + 1
        if 1 <= event_week <= plan.total_weeks:
            symbol = "🏆" if event.priority == "A" else "🎯" if event.priority == "B" else "🚴"
            fig.add_annotation(
                x=event_week,
                y=max(target_tss) * 1.1,
                text=f"{symbol} {event.name}",
                showarrow=True,
                arrowhead=2,
                row=1,
                col=1,
            )

    # Update layout
    fig.update_layout(
        height=500,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )

    fig.update_xaxes(title_text="Week", row=2, col=1)
    fig.update_yaxes(title_text="TSS", row=1, col=1)
    fig.update_yaxes(title_text="CTL", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)


def render_weekly_details(plan: TrainingPlan):
    """Render detailed weekly breakdown."""
    st.subheader("📅 Weekly Breakdown")

    # Create tabs for each phase
    phase_names = list(dict.fromkeys([w.phase for w in plan.weeks]))
    tabs = st.tabs(phase_names)

    for tab, phase_name in zip(tabs, phase_names):
        with tab:
            phase_weeks = [w for w in plan.weeks if w.phase == phase_name]

            for week in phase_weeks:
                is_current = week.week_number == plan.current_week

                with st.expander(
                    f"Week {week.week_number} ({week.start_date.strftime('%b %d')} - {week.end_date.strftime('%b %d')})"
                    + (" 👈 Current" if is_current else ""),
                    expanded=is_current,
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**Targets**")
                        st.write(f"Hours: {week.target_hours}h")
                        st.write(f"TSS: {week.target_tss}")
                        st.write(f"Target CTL: {week.target_ctl}")

                    with col2:
                        st.markdown("**Actuals**")
                        if week.actual_hours is not None:
                            st.write(f"Hours: {week.actual_hours}h")
                            st.write(f"TSS: {week.actual_tss}")
                            if week.actual_ctl:
                                st.write(f"Actual CTL: {week.actual_ctl}")
                            adherence = week.adherence_pct or 0
                            color = "green" if adherence >= 90 else "orange" if adherence >= 70 else "red"
                            st.markdown(f"Adherence: :{color}[{adherence:.0f}%]")
                        else:
                            st.write("Not yet completed")

                    with col3:
                        st.markdown("**Intensity Distribution**")
                        st.write(f"Z1: {week.tid_z1}%")
                        st.write(f"Z2: {week.tid_z2}%")
                        st.write(f"Z3: {week.tid_z3}%")

                    if week.key_workouts:
                        st.markdown("**Key Workouts:**")
                        for workout in week.key_workouts:
                            st.write(f"  • {workout}")

                    if week.events:
                        st.markdown("**Events:**")
                        for event in week.events:
                            st.write(f"  🏆 {event}")

                    if week.recovery_notes:
                        st.caption(f"💡 {week.recovery_notes}")


def render_adherence_summary(plan: TrainingPlan):
    """Render adherence tracking summary."""
    st.subheader("📈 Adherence Summary")

    completed_weeks = [w for w in plan.weeks if w.actual_tss is not None]

    if not completed_weeks:
        st.info("No completed weeks yet. Complete training to see adherence data.")
        return

    # Calculate overall adherence
    total_target_tss = sum(w.target_tss for w in completed_weeks)
    total_actual_tss = sum(w.actual_tss or 0 for w in completed_weeks)
    overall_adherence = (total_actual_tss / total_target_tss * 100) if total_target_tss > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Overall Adherence",
            f"{overall_adherence:.0f}%",
            "On Track" if overall_adherence >= 85 else "Need Focus",
        )

    with col2:
        weeks_hit = sum(1 for w in completed_weeks if (w.adherence_pct or 0) >= 90)
        st.metric(
            "Weeks Hit (>90%)",
            f"{weeks_hit}/{len(completed_weeks)}",
        )

    with col3:
        total_hours = sum(w.actual_hours or 0 for w in completed_weeks)
        st.metric(
            "Total Hours Trained",
            f"{total_hours:.1f}h",
        )


def render_ai_recommendations(
    plan: TrainingPlan,
    plan_service: TrainingPlanService,
    activities_df: pd.DataFrame,
):
    """Render AI-powered plan adjustment recommendations."""
    st.subheader("🤖 AI Plan Advisor")

    # Model selection in expander (similar to AI Coach)
    with st.expander("⚙️ AI Settings", expanded=False):
        with st.spinner("Loading available models..."):
            available_models = GeminiClient.get_available_models()

        if not available_models:
            st.error("Could not fetch available models. Please check your GEMINI_API_KEY environment variable.")
            return

        # Model selector
        default_model = "gemini-2.0-flash"
        if default_model not in available_models:
            default_model = available_models[0]

        selected_model = st.selectbox(
            "Select Model",
            available_models,
            index=available_models.index(default_model) if default_model in available_models else 0,
            help="Choose which Gemini model to use for plan analysis",
            key="training_plan_ai_model",
        )

    # Get current metrics for AI context
    current_tsb = 0.0
    current_acwr = 1.0
    ef_trend = "stable"

    if not activities_df.empty:
        # Get latest TSB
        if "training_stress_balance" in activities_df.columns:
            latest = activities_df.sort_values("start_date_local", ascending=False).iloc[0]
            current_tsb = latest.get("training_stress_balance", 0.0)
            if pd.isna(current_tsb):
                current_tsb = 0.0

        # Get ACWR
        if "acwr" in activities_df.columns:
            current_acwr = latest.get("acwr", 1.0)
            if pd.isna(current_acwr):
                current_acwr = 1.0

        # Determine EF trend from recent activities
        if "efficiency_factor" in activities_df.columns:
            recent = activities_df.sort_values("start_date_local", ascending=False).head(10)
            ef_values = recent["efficiency_factor"].dropna()
            if len(ef_values) >= 3:
                first_half = ef_values.iloc[len(ef_values)//2:].mean()
                second_half = ef_values.iloc[:len(ef_values)//2].mean()
                if second_half > first_half * 1.02:
                    ef_trend = "improving"
                elif second_half < first_half * 0.98:
                    ef_trend = "declining"

    # Show current status
    col1, col2, col3 = st.columns(3)
    with col1:
        tsb_color = "green" if current_tsb > 0 else "orange" if current_tsb > -20 else "red"
        st.metric(
            "Current Form (TSB)",
            f"{current_tsb:.1f}",
            "Fresh" if current_tsb > 0 else "Fatigued",
        )
    with col2:
        acwr_status = "Optimal" if current_acwr < 1.3 else "Elevated" if current_acwr < 1.5 else "HIGH RISK"
        st.metric(
            "Workload Ratio (ACWR)",
            f"{current_acwr:.2f}",
            acwr_status,
        )
    with col3:
        st.metric(
            "Efficiency Trend",
            ef_trend.capitalize(),
            "↗️" if ef_trend == "improving" else "➡️" if ef_trend == "stable" else "↘️",
        )

    # Generate recommendations button
    if st.button("🧠 Get AI Recommendations", type="primary"):
        with st.spinner("Analyzing your training plan..."):
            try:
                # Generate the prompt
                prompt = plan_service.get_ai_adjustment_prompt(
                    plan=plan,
                    current_tsb=current_tsb,
                    current_acwr=current_acwr,
                    ef_trend=ef_trend,
                )

                # Add adherence context
                completed_weeks = [w for w in plan.weeks if w.actual_tss is not None]
                if completed_weeks:
                    total_target = sum(w.target_tss for w in completed_weeks)
                    total_actual = sum(w.actual_tss or 0 for w in completed_weeks)
                    adherence = (total_actual / total_target * 100) if total_target > 0 else 100
                    prompt += f"\n\n## Adherence Summary\n- Overall Adherence: {adherence:.0f}%\n"
                    prompt += f"- Weeks Completed: {len(completed_weeks)}\n"

                    # Recent week details
                    recent_weeks = completed_weeks[-3:]
                    prompt += "\n## Recent Weeks:\n"
                    for w in recent_weeks:
                        prompt += f"- Week {w.week_number}: {w.actual_tss}/{w.target_tss} TSS ({w.adherence_pct:.0f}% adherence)\n"

                # Get AI response
                client = GeminiClient(model=selected_model)
                response = client.get_response(prompt)

                # Display recommendations
                st.markdown("### 💡 AI Recommendations")
                st.markdown(response)

                # Store in session state for reference
                st.session_state.ai_recommendations = {
                    "timestamp": datetime.now().isoformat(),
                    "response": response,
                }

            except Exception as e:
                st.error(f"Failed to get AI recommendations: {e}")

    # Show previous recommendations if available
    if "ai_recommendations" in st.session_state:
        rec = st.session_state.ai_recommendations
        with st.expander(f"📝 Previous Recommendations ({rec['timestamp'][:10]})"):
            st.markdown(rec["response"])


def main():
    st.title("📋 Training Plan")

    # Check for services
    if "activity_service" not in st.session_state:
        # Try to initialize from settings
        if "settings" in st.session_state:
            settings = st.session_state.settings
            try:
                st.session_state.activity_service = init_services(settings)
            except Exception as e:
                st.error(f"Failed to initialize services: {e}")
                st.stop()
        else:
            st.error("Service not initialized. Please run the app from the main entry point.")
            st.stop()

    settings = st.session_state.get("settings")
    if not settings:
        st.error("Settings not found. Please configure the application.")
        st.stop()

    # Initialize training plan service
    plan_service = TrainingPlanService(st.session_state.activity_service)
    plan_file_path = get_plan_file_path(settings)

    # Try to load saved plan on startup (only once per session)
    if "training_plan" not in st.session_state and "plan_load_attempted" not in st.session_state:
        st.session_state.plan_load_attempted = True
        loaded_plan = plan_service.load_plan(plan_file_path)
        if loaded_plan:
            st.session_state.training_plan = loaded_plan
            st.toast(f"📂 Loaded training plan from {plan_file_path.name}")
            st.rerun()  # Rerun to show the loaded plan immediately

    # Sidebar navigation
    with st.sidebar:
        st.header("📋 Training Plan")
        action = st.radio(
            "Action",
            ["View Current Plan", "Create New Plan"],
            label_visibility="collapsed",
        )
        
        # Show plan file location
        st.caption(f"📁 Plan file: `{plan_file_path.name}`")

    if action == "Create New Plan":
        plan = render_plan_generator(settings)
        if plan:
            st.session_state.training_plan = plan
            # Auto-save the new plan
            try:
                plan_service.save_plan(plan, plan_file_path)
                st.success(f"✅ Plan generated and saved to {plan_file_path.name}!")
            except Exception as e:
                st.warning(f"Plan generated but failed to save: {e}")
            st.rerun()

    else:
        # View current plan
        if "training_plan" not in st.session_state:
            st.info(
                "No training plan created yet. Use the sidebar to create a new plan."
            )

            # Offer quick plan based on config
            if settings.target_wkg and settings.target_date:
                st.markdown("---")
                st.markdown("### 🎯 Quick Plan from Config")
                st.write(
                    f"Your config shows a goal of **{settings.target_wkg} W/kg** "
                    f"by **{settings.target_date}**"
                )

                if st.button("Generate Plan from Config"):
                    try:
                        target_date = datetime.strptime(settings.target_date, "%Y-%m-%d")
                        target_ftp = settings.target_wkg * settings.weight_kg

                        plan = plan_service.generate_plan(
                            start_date=datetime.now(),
                            end_date=target_date,
                            start_ftp=settings.ftp,
                            target_ftp=target_ftp,
                            weight_kg=settings.weight_kg,
                            hours_per_week=getattr(settings, "weekly_hours_available", 10.0),
                            key_events=getattr(settings, "key_events", []),
                            current_ctl=50.0,
                            plan_name=f"Path to {settings.target_wkg} W/kg",
                        )
                        st.session_state.training_plan = plan
                        # Auto-save
                        try:
                            plan_service.save_plan(plan, plan_file_path)
                            st.success(f"✅ Plan generated and saved!")
                        except Exception as save_e:
                            st.warning(f"Plan generated but save failed: {save_e}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate plan: {e}")
        else:
            plan = st.session_state.training_plan

            # Update with actual data
            activities_df = st.session_state.activity_service.get_all_activities()
            plan = plan_service.update_actuals(plan, activities_df)
            st.session_state.training_plan = plan

            # Render plan views
            render_plan_overview(plan)
            render_plan_chart(plan)
            render_adherence_summary(plan)

            # AI Recommendations section
            st.markdown("---")
            render_ai_recommendations(plan, plan_service, activities_df)

            # Weekly details
            st.markdown("---")
            render_weekly_details(plan)

            # Export/Clear buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄 Refresh Actuals"):
                    st.rerun()
            with col2:
                if st.button("💾 Save Plan"):
                    try:
                        plan_service.save_plan(plan, plan_file_path)
                        st.success(f"✅ Saved to {plan_file_path.name}")
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
            with col3:
                if st.button("🗑️ Clear Plan", type="secondary"):
                    del st.session_state.training_plan
                    if "plan_events" in st.session_state:
                        del st.session_state.plan_events
                    # Optionally delete the file
                    if plan_file_path.exists():
                        plan_file_path.unlink()
                    st.rerun()


if __name__ == "__main__":
    main()
