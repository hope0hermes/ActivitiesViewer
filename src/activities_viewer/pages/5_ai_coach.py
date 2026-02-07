"""
AI Coach Page.
Chat interface for analyzing training data with Gemini.
"""

import streamlit as st
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.ai.client import GeminiClient, render_ai_model_selector
from activities_viewer.ai.context import ActivityContextBuilder
from activities_viewer.cache import (
    build_consolidation_prompt,
    build_history_context,
    build_memory_context,
    clear_cache,
    clear_chat_history,
    clear_memory,
    get_cache_size,
    load_chat_history,
    needs_consolidation,
    save_chat_exchange,
    save_memory_summary,
)

st.set_page_config(page_title="AI Coach", page_icon="🤖", layout="wide")


def main():
    st.title("🤖 AI Coach")

    # ── Feature overview (expandable) ─────────────────────────────────
    with st.expander("ℹ️ About AI Coach — capabilities & limitations"):
        st.markdown("""
**What it can do:**
- Analyse your **full training history** (multi-year yearly summaries, quarterly FTP/W·kg evolution)
- Provide insights on **current form** (CTL, ATL, TSB, ACWR) and **training phase** detection
- Review **recent trends**: monthly progression (last 6 months), weekly summaries (last 4 weeks), efficiency factor trends
- Deep-dive into **specific activities**: power, HR, cadence, speed, altitude streams
- **GPS route analysis** with reverse-geocoded street names and waypoints
- Quick-prompt shortcuts for common questions (weekly summary, FTP trend, goal progress, etc.)

**What context is sent to the LLM:**
| Data block | Scope |
|---|---|
| Athlete profile | FTP, weight, W/kg, goal target & date |
| Training status | Latest CTL, ATL, TSB, ACWR |
| Training phase | Auto-detected from 4-week TID (Base → Peak) |
| Yearly summaries | All years in your data |
| FTP evolution | Quarterly FTP & W/kg across full history |
| Monthly trends | Last 6 months of volume, intensity, load |
| Efficiency factor | Aerobic fitness trend |
| Weekly summaries | Last 4 weeks |
| Recent activities | Last 5 activities with detailed metrics |
| Stream data | Power/HR/cadence/speed/altitude for referenced activities |
| GPS & route | Waypoints with reverse-geocoded locations (when available) |

**What it retrieves:**
- A single text response from Google Gemini (selected model in sidebar)
- No data is stored externally — context is built on-the-fly from your local CSV files

**Limitations:**
- Responses depend on the quality and completeness of your enriched activity data
- GPS reverse geocoding is rate-limited (1 req/sec via Nominatim) and may time out
- **Conversation memory**: the last 10 exchanges from previous sessions are injected as context so the LLM can reference earlier advice (stored in `~/.activitiesviewer/chat_history.json`, max 50 exchanges)
- **Long-term memory**: when raw history reaches 50 exchanges, the LLM consolidates them into a structured summary capturing key insights, advice, and progress — these summaries persist indefinitely (up to 20 blocks) and are always included as context
- Cannot modify your data or trigger Strava syncs
- Token limits may truncate context for very large datasets
- Use the **Clear** buttons in the sidebar to reset stored conversations or memory
        """)

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

    # ── Cache management in sidebar ───────────────────────────────────
    with st.sidebar:
        st.divider()
        st.markdown("#### 🗄️ Cache")
        cache_info = get_cache_size()
        for label, value in cache_info.items():
            st.caption(f"{label}: {value}")

        col_clear_chat, col_clear_all = st.columns(2)
        with col_clear_chat:
            if st.button(
                "Clear chat",
                use_container_width=True,
                help="Clears raw conversation exchanges only. Long-term memory summaries are kept.",
            ):
                clear_chat_history()
                st.session_state.messages = []
                st.toast("Chat history cleared")
                st.rerun()
        with col_clear_all:
            if st.button(
                "Clear all",
                type="secondary",
                use_container_width=True,
                help="Wipes the entire ~/.activitiesviewer/ folder including chat history, long-term memory, and geocoding cache.",
            ):
                clear_cache()
                st.session_state.messages = []
                st.toast("All cached data cleared (including long-term memory)")
                st.rerun()
        if st.button(
            "Reset memory only",
            use_container_width=True,
            help="Clears both raw conversation exchanges and consolidated long-term memory summaries. Geocoding cache is kept.",
        ):
            clear_memory()
            st.session_state.messages = []
            st.toast("Conversation history and memory summaries cleared")
            st.rerun()

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

    # Chat Interface — restore from disk on first load
    if "messages" not in st.session_state:
        saved = load_chat_history()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I'm your AI Coach. I can analyze your training "
                    "data across your full history. Use the quick prompts "
                    "above or ask me anything!"
                ),
            }
        ]
        # Replay persisted exchanges so the user sees prior conversation
        for exchange in saved[-10:]:
            st.session_state.messages.append(
                {"role": "user", "content": exchange["user"]}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": exchange["assistant"]}
            )

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

                # Build conversation history context
                history_context = build_history_context(max_exchanges=10)
                memory_context = build_memory_context()

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

                LONG-TERM MEMORY: You may have consolidated memory summaries from earlier
                coaching sessions. These contain key athlete insights, prior advice, and
                progress observations. Use them to provide continuity — build on earlier
                recommendations, check if previous advice was followed, and avoid repeating
                analysis the athlete has already received.

                CONVERSATION HISTORY: You also have recent raw exchanges from the current
                batch of conversations. Use them alongside the long-term memory for full context.
                If the user refers to something "you said before", check both memory and history.
                """

                parts = [system_prompt, f"\nContext:\n{context}"]
                if memory_context:
                    parts.append(f"\n{memory_context}")
                if history_context:
                    parts.append(f"\n{history_context}")
                parts.append(f"\nUser Question: {prompt}")
                final_prompt = "\n".join(parts)

                # Get response
                response = client.get_response(final_prompt)

            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Persist exchange to disk
            save_chat_exchange(prompt, response)

            # Consolidate memory if threshold reached
            if needs_consolidation():
                with st.spinner("Consolidating coaching memory..."):
                    exchanges = load_chat_history()
                    consolidation_prompt = build_consolidation_prompt(exchanges)
                    summary = client.get_response(consolidation_prompt)
                    save_memory_summary(summary, exchanges)
                st.toast(
                    f"💾 Consolidated {len(exchanges)} exchanges into long-term memory"
                )

        # Rerun to update the chat display
        st.rerun()


if __name__ == "__main__":
    main()
