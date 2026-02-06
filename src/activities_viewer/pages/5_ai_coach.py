"""
AI Coach Page.
Chat interface for analyzing training data with Gemini.
"""

import streamlit as st
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.ai.client import GeminiClient, render_ai_model_selector
from activities_viewer.ai.context import ActivityContextBuilder

st.set_page_config(page_title="AI Coach", page_icon="🤖", layout="wide")


def main():
    st.title("🤖 AI Coach")

    if "activity_service" not in st.session_state:
        st.error(
            "Service not initialized. Please run the app from the main entry point."
        )
        return

    service = st.session_state.activity_service

    # Shared model selector in sidebar
    selected_model = render_ai_model_selector()
    if not selected_model:
        st.error("No AI models available. Please check your GEMINI_API_KEY.")
        return

    # Initialize AI components
    if (
        "ai_client" not in st.session_state
        or st.session_state.get("selected_model") != selected_model
    ):
        try:
            with st.spinner("Initializing AI Coach..."):
                st.session_state.ai_client = GeminiClient(model=selected_model)
                # Pass settings for athlete profile and goal context
                settings = st.session_state.get("settings")
                st.session_state.context_builder = ActivityContextBuilder(service, settings)
                st.session_state.selected_model = selected_model
        except Exception as e:
            st.error(
                f"Failed to initialize AI Coach. Please check your GEMINI_API_KEY.\nError: {e}"
            )
            return

    client = st.session_state.ai_client
    context_builder = st.session_state.context_builder

    # Quick Analysis Prompts
    st.subheader("💡 Quick Analysis")
    col1, col2, col3, col4 = st.columns(4)

    quick_prompts = {
        "📊 Weekly Summary": "Summarize my training from the last 7 days. Include total volume, intensity distribution, and recovery status.",
        "📈 FTP Trend": "Analyze my FTP evolution over the last 6 months. Am I improving? What's the trend?",
        "🎯 Goal Progress": "Based on my current trajectory and training, am I on track to reach my W/kg goal? What adjustments would help?",
        "💪 Training Phase": "What training phase am I in (base, build, peak)? Is my intensity distribution appropriate for this phase?",
        "⚡ Form Check": "Analyze my current form (TSB/CTL/ATL). Am I fresh, fatigued, or at optimal training stress?",
        "🔄 Recovery": "Based on my recent training load and fatigue metrics, do I need more recovery? When should my next hard session be?",
        "📉 EF Trends": "Analyze my Efficiency Factor trends. Is my aerobic fitness improving?",
        "🏆 Year Comparison": "Compare my training this year vs last year. Volume, intensity, FTP progression.",
    }

    # Display prompts in a grid
    prompt_keys = list(quick_prompts.keys())
    with col1:
        if st.button(prompt_keys[0], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[0]]
        if st.button(prompt_keys[4], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[4]]
    with col2:
        if st.button(prompt_keys[1], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[1]]
        if st.button(prompt_keys[5], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[5]]
    with col3:
        if st.button(prompt_keys[2], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[2]]
        if st.button(prompt_keys[6], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[6]]
    with col4:
        if st.button(prompt_keys[3], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[3]]
        if st.button(prompt_keys[7], use_container_width=True):
            st.session_state.quick_prompt = quick_prompts[prompt_keys[7]]

    st.divider()

    # Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI Coach. I can analyze your training data across your full history. Use the quick prompts above or ask me anything!",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle quick prompts or chat input
    prompt = None
    if "quick_prompt" in st.session_state and st.session_state.quick_prompt:
        prompt = st.session_state.quick_prompt
        st.session_state.quick_prompt = None  # Clear after use
    elif user_input := st.chat_input("Ask about your training..."):
        prompt = user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # Build context
            with st.spinner("Analyzing data..."):
                context = context_builder.build_context(prompt)

                # Construct full prompt
                system_prompt = """You are an expert cycling coach and data analyst.
                Analyze the user's activity data provided in the context and answer their question.
                Be encouraging but data-driven. Use the metric system (km, meters).
                If the user asks about specific activities, refer to the ones in the context.
                If you don't have enough data to answer, politely say so and suggest what data might be needed.

                IMPORTANT: The context includes FULL HISTORICAL DATA spanning multiple years.
                - Yearly summaries show all years available
                - Quarterly FTP evolution shows long-term trends
                - Use this data to answer questions about multi-year trends

                STREAM DATA: When analyzing specific activities, you have access to detailed stream data including:
                - Power, heart rate, cadence, speed, altitude
                - GPS coordinates (latitude/longitude) with waypoints and route analysis
                - Segment analysis showing climbs with their GPS locations
                Use this data for route-specific analysis and location-based insights.
                """

                final_prompt = (
                    f"{system_prompt}\n\nContext:\n{context}\n\nUser Question: {prompt}"
                )

                # Get response
                response = client.get_response(final_prompt)

            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        # Rerun to update the chat display
        st.rerun()


if __name__ == "__main__":
    main()
