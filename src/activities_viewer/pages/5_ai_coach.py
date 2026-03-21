"""
AI Coach Page.
Chat interface for analyzing training data with Gemini.
"""

import json
import logging
import os
import re
from pathlib import Path

import streamlit as st

from activities_viewer.ai.client import GeminiClient, render_ai_model_selector
from activities_viewer.ai.context import ActivityContextBuilder
from activities_viewer.app import init_services
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
from activities_viewer.config import Settings
from activities_viewer.services.training_plan_service import TrainingPlanService

logger = logging.getLogger(__name__)

st.set_page_config(page_title="AI Coach", page_icon="🤖", layout="wide")


def _get_training_plan_context() -> str | None:
    """
    Load and serialize the training plan if one exists.

    Returns:
        Serialized plan context string, or None if no plan exists.
    """
    settings = st.session_state.get("settings")
    if not settings:
        return None

    # Get plan file path from settings
    plan_file = getattr(settings, "training_plan_file", None)
    if plan_file:
        plan_path = Path(plan_file)
    else:
        return None

    if not plan_path.exists():
        logger.debug(f"No training plan found at {plan_path}")
        return None

    try:
        plan_service = TrainingPlanService()
        plan = plan_service.load_plan(plan_path)
        if plan:
            logger.info(f"Loaded training plan '{plan.name}' for AI Coach context")
            return plan_service.serialize_plan_for_prompt(plan)
    except Exception as e:
        logger.warning(f"Failed to load training plan: {e}")

    return None


def _parse_plan_modifications(response: str) -> tuple[dict | None, str]:
    """
    Extract a plan_update JSON block from the LLM response.

    The LLM is instructed to embed modifications in a fenced code block:

        ```plan_update
        {"weeks": {...}, "plan": {...}, "summary": "..."}
        ```

    Args:
        response: Raw LLM response text.

    Returns:
        Tuple of (parsed modifications dict or None, display text with block removed).
    """
    pattern = r"```plan_update\s*\n(.*?)\n\s*```"
    match = re.search(pattern, response, re.DOTALL)

    if not match:
        return None, response

    json_str = match.group(1).strip()
    try:
        modifications = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse plan_update JSON: {e}")
        return None, response

    if not isinstance(modifications, dict):
        logger.warning("plan_update block is not a JSON object")
        return None, response

    # Remove the fenced block from the displayed text
    display_text = response[: match.start()] + response[match.end() :]
    display_text = display_text.strip()

    return modifications, display_text


def _response_describes_plan_changes(response: str) -> bool:
    """
    Heuristic check: does the LLM response describe concrete plan modifications?

    Looks for patterns like "Week 5 ... TSS", "reduce volume", "adjust the plan",
    "here is the plan update", etc. Returns True only when multiple signals are
    present to avoid false positives on purely advisory answers.
    """
    response_lower = response.lower()

    # Strong signals that the LLM is presenting concrete changes
    strong_signals = [
        r"here\s+is\s+the\s+plan\s+update",
        r"(?:i(?:'ve|'ll| have| will)\s+)?(?:adjust|modif|updat|chang)\w*\s+(?:the\s+)?(?:plan|week)",
        r"week\s+\d+.*?(?:tss|hours|recovery|taper|workouts?)\s*[=:]",
        r"(?:new|updated|revised|modified)\s+(?:plan|week|target|tss|hours)",
    ]

    # Contextual signals
    contextual_signals = [
        r"reduce\s+(?:volume|tss|hours|load)",
        r"increase\s+(?:volume|tss|hours|load)",
        r"(?:swap|replace|change)\s+(?:the\s+)?workouts?",
        r"recovery\s+week",
        r"maintenance\s+(?:and|&)\s+mobility",
        r"tss\s*(?:=|:|\bto\b)\s*\d+",
        r"hours?\s*(?:=|:|\bto\b)\s*\d+",
    ]

    strong_count = sum(1 for p in strong_signals if re.search(p, response_lower))
    contextual_count = sum(1 for p in contextual_signals if re.search(p, response_lower))

    # Need at least 1 strong signal + 1 contextual, or 3+ contextual
    return (strong_count >= 1 and contextual_count >= 1) or contextual_count >= 3


def _extract_modifications_via_llm(
    client: GeminiClient,
    coaching_response: str,
    plan_context: str,
) -> dict | None:
    """
    Second-pass LLM call: extract structured plan modifications from a
    conversational coaching response that describes changes but didn't
    include the structured block.

    Args:
        client: The GeminiClient to use.
        coaching_response: The LLM's conversational response describing changes.
        plan_context: Serialized current training plan.

    Returns:
        Parsed modifications dict, or None on failure.
    """
    extraction_prompt = f"""You are a JSON extraction assistant. Your ONLY job is to read the
coaching response below and produce a single JSON object that captures
the concrete training plan modifications described in it.

=== CURRENT TRAINING PLAN ===
{plan_context}

=== COACHING RESPONSE (describes the desired changes) ===
{coaching_response}

=== YOUR TASK ===
Output ONLY a valid JSON object (no markdown, no explanation, no extra text)
with this exact structure:

{{
  "weeks": {{
    "<week_number>": {{
      "target_tss": <int or omit>,
      "target_hours": <float or omit>,
      "tid_z1": <float or omit>,
      "tid_z2": <float or omit>,
      "tid_z3": <float or omit>,
      "key_workouts": [<list of strings> or omit],
      "recovery_notes": "<string or omit>",
      "is_recovery_week": <bool or omit>,
      "is_taper_week": <bool or omit>
    }}
  }},
  "plan": {{
    "name": "<string or omit>",
    "goal": "<string or omit>",
    "target_ftp": <float or omit>
  }},
  "summary": "<one-line description of all changes>"
}}

Rules:
- Only include fields that are being changed (omit unchanged fields).
- Week numbers are 1-based integers used as string keys.
- "plan" and "weeks" keys are optional — only include what's changing.
- "summary" is always required.
- Output ONLY the JSON object, nothing else."""

    try:
        raw = client.get_response(extraction_prompt)
    except Exception as e:
        logger.warning(f"Extraction LLM call failed: {e}")
        return None

    # Strip any markdown fencing the LLM might have wrapped around it
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        modifications = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse extraction response as JSON: {e}\nRaw: {cleaned[:500]}")
        return None

    if not isinstance(modifications, dict):
        return None

    # Sanity: must have at least "weeks" or "plan" key
    if "weeks" not in modifications and "plan" not in modifications:
        logger.warning("Extraction produced JSON with neither 'weeks' nor 'plan' keys")
        return None

    return modifications


def _apply_and_save_plan_modifications(modifications: dict) -> list[str] | None:
    """
    Load the current plan, apply modifications, and save back to disk.

    Args:
        modifications: Parsed modification dict from the LLM.

    Returns:
        List of change descriptions, or None on failure.
    """
    settings = st.session_state.get("settings")
    if not settings:
        logger.warning("No settings in session — cannot modify plan")
        return None

    plan_file = getattr(settings, "training_plan_file", None)
    if not plan_file:
        logger.warning("No training_plan_file configured")
        return None

    plan_path = Path(plan_file)
    plan_service = TrainingPlanService()
    plan = plan_service.load_plan(plan_path)

    if plan is None:
        logger.warning(f"No training plan found at {plan_path}")
        return None

    plan, changes = plan_service.apply_modifications(plan, modifications)
    plan_service.save_plan(plan, plan_path)
    logger.info(f"Saved modified training plan to {plan_path}")

    # Update session state so the Training Plan page picks up changes
    # without needing a full session restart.
    st.session_state.training_plan = plan
    st.session_state.pop("plan_load_attempted", None)

    return changes


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
- **Modify your training plan** when asked (e.g. swap workouts, adjust TSS targets, mark recovery weeks)
- Quick-prompt shortcuts for common questions (weekly summary, FTP trend, goal progress, etc.)

**What context is sent to the LLM:**
| Data block | Scope |
|---|---|
| Athlete profile | FTP, weight, W/kg, goal target & date |
| Training status | Latest CTL, ATL, TSB, ACWR |
| Training phase | Auto-detected from 4-week TID (Base → Peak) |
| **Training plan** | Full periodized plan (if generated) with phases, weekly targets, key events |
| Yearly summaries | All years in your data |
| FTP evolution | Quarterly FTP & W/kg across full history |
| Monthly trends | Last 6 months of volume, intensity, load |
| Efficiency factor | Aerobic fitness trend |
| Weekly summaries | Last 4 weeks |
| Recent activities | Last 5 activities with detailed metrics |
| **Streams overview** | Best sustained HR & power per duration (1–60 min) + HR histogram, from **all** stream files |
| Stream deep-dive | Full second-by-second power/HR/cadence/altitude for specifically referenced activities |
| GPS & route | Waypoints with reverse-geocoded locations (when available) |

**What it retrieves:**
- A single text response from Google Gemini (selected model in sidebar)
- No data is stored externally — context is built on-the-fly from your local CSV files

**Limitations:**
- Responses depend on the quality and completeness of your enriched activity data
- GPS reverse geocoding is rate-limited (1 req/sec via Nominatim) and may time out
- **Conversation memory**: the last 10 exchanges from previous sessions are injected as context so the LLM can reference earlier advice (stored in `~/.activitiesviewer/chat_history.json`, max 50 exchanges)
- **Long-term memory**: when raw history reaches 50 exchanges, the LLM consolidates them into a structured summary capturing key insights, advice, and progress — these summaries persist indefinitely (up to 20 blocks) and are always included as context
- Cannot trigger Strava syncs or modify activity data
- Token limits may truncate context for very large datasets
- Use the **Clear** buttons in the sidebar to reset stored conversations or memory
        """)

    if "activity_service" not in st.session_state:
        # Try to initialize from settings / env config
        if "settings" not in st.session_state:
            config_json = os.environ.get("ACTIVITIES_VIEWER_CONFIG")
            if config_json:
                try:
                    config_data = json.loads(config_json)
                    st.session_state.settings = Settings(**config_data)
                except Exception:
                    pass
        if "settings" in st.session_state:
            try:
                st.session_state.activity_service = init_services(
                    st.session_state.settings
                )
            except Exception:
                pass

        if "activity_service" not in st.session_state:
            st.info("⏳ Waiting for data services... Please navigate from the main page.")
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
            # Show plan modification notification inline after the message
            notification = message.get("plan_notification")
            if notification:
                if notification["type"] == "success":
                    st.success(notification["text"], icon="📝")
                else:
                    st.warning(notification["text"])

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

                TRAINING PLAN: If a training plan is included in the context, use it to:
                - Answer questions about upcoming workouts and weekly targets
                - Compare actual training vs planned targets (TSS, hours, intensity distribution)
                - Provide guidance on current training phase and periodization
                - Reference key events and taper periods
                If no plan is present, suggest the user generate one on the Training Plan page.

                TRAINING PLAN MODIFICATIONS: You can modify the training plan when the user
                asks you to. Examples: "make week 5 a recovery week", "increase TSS for the
                build phase", "swap workouts in week 3", "reduce hours next week", etc.

                When you modify the plan, you MUST:
                1. Explain the changes conversationally in your response.
                2. Include a ```plan_update``` fenced code block with a JSON object describing
                   the exact changes. This block will be parsed and applied automatically.

                The JSON format is:
                ```plan_update
                {
                  "weeks": {
                    "<week_number>": {
                      "target_tss": <int>,
                      "target_hours": <float>,
                      "tid_z1": <float>, "tid_z2": <float>, "tid_z3": <float>,
                      "key_workouts": ["workout 1", "workout 2"],
                      "recovery_notes": "notes",
                      "is_recovery_week": <bool>,
                      "is_taper_week": <bool>
                    }
                  },
                  "plan": {
                    "name": "...", "goal": "...", "target_ftp": <float>
                  },
                  "summary": "Brief description of all changes made"
                }
                ```

                Rules for the plan_update block:
                - Only include fields you are actually changing (omit unchanged fields).
                - Week numbers are 1-based integers (use as string keys in the JSON).
                - "plan" key is optional — only include it for plan-level changes.
                - "weeks" key is optional — only include it for week-level changes.
                - tid_z1 + tid_z2 + tid_z3 should equal 100 when you change intensity distribution.
                - Always include "summary" with a brief description.
                - Do NOT modify the plan unless the user explicitly asks for a change.
                - When suggesting changes, first explain your reasoning, then include the block.

                STREAM DATA: You have TWO levels of stream access:

                1. STREAMS DIRECTORY OVERVIEW (always present in every context):
                   Fleet-level analytics computed from ALL activities with stream files:
                   best sustained HR and power per duration window (1–60 min rolling
                   averages) and HR distribution histogram. ALWAYS check the
                   "STREAMS DIRECTORY OVERVIEW" section in the context before making
                   any claims about physiological capacity. Use it to answer questions
                   like "can I sustain 180 bpm for 30 min?", "what is my peak 20-min
                   power?", "show my HR distribution", or any cross-activity comparison.

                2. INDIVIDUAL STREAM DEEP-DIVE (included when an activity is referenced):
                   Full second-by-second power, HR, cadence, speed, altitude and GPS
                   when the user names a specific activity, date, "last ride", activity
                   ID, OR asks a general physiological question (auto-attaches the most
                   recent activity). USE this data — do not claim you cannot see it.
                   - GPS coordinates with waypoints and reverse-geocoded street names
                   - Segment analysis showing climbs and their GPS locations
                   Use this for single-activity deep-dives and route analysis.

                LONG-TERM MEMORY: You may have consolidated memory summaries from earlier
                coaching sessions. These contain key athlete insights, prior advice, and
                progress observations. Use them to provide continuity — build on earlier
                recommendations, check if previous advice was followed, and avoid repeating
                analysis the athlete has already received.

                CONVERSATION HISTORY: You also have recent raw exchanges from the current
                batch of conversations. Use them alongside the long-term memory for full context.
                If the user refers to something "you said before", check both memory and history.
                """

                # Build context parts
                parts = [system_prompt, f"\nContext:\n{context}"]

                # Add training plan if available
                plan_context = _get_training_plan_context()
                if plan_context:
                    parts.append(f"\n=== CURRENT TRAINING PLAN ===\n{plan_context}")
                else:
                    parts.append("\n[No training plan currently set. User can generate one on the Training Plan page.]")
                if memory_context:
                    parts.append(f"\n{memory_context}")
                if history_context:
                    parts.append(f"\n{history_context}")
                parts.append(f"\nUser Question: {prompt}")
                final_prompt = "\n".join(parts)

                # Get response
                response = client.get_response(final_prompt)

            # Check for plan modifications in the response
            modifications, display_text = _parse_plan_modifications(response)

            # Fallback: if no structured block but the response describes
            # plan changes, do a focused extraction call
            if modifications is None and _response_describes_plan_changes(response):
                plan_ctx = _get_training_plan_context()
                if plan_ctx:
                    with st.spinner("Applying plan modifications..."):
                        modifications = _extract_modifications_via_llm(
                            client, response, plan_ctx,
                        )
                    # display_text is unchanged (the full conversational response)

            plan_notification = None
            if modifications:
                changes = _apply_and_save_plan_modifications(modifications)
                if changes:
                    message_placeholder.markdown(display_text)
                    change_list = "\n".join(f"- {c}" for c in changes)
                    notification_text = f"✅ Training plan updated!\n\n{change_list}"
                    st.success(notification_text, icon="📝")
                    plan_notification = {"type": "success", "text": notification_text}
                else:
                    message_placeholder.markdown(display_text)
                    notification_text = (
                        "⚠️ Plan modification was suggested but could not be applied. "
                        "Make sure you have an active training plan."
                    )
                    st.warning(notification_text)
                    plan_notification = {"type": "warning", "text": notification_text}
            else:
                message_placeholder.markdown(display_text)

            msg = {"role": "assistant", "content": display_text}
            if plan_notification:
                msg["plan_notification"] = plan_notification
            st.session_state.messages.append(msg)

            # Persist exchange to disk
            save_chat_exchange(prompt, display_text)

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
