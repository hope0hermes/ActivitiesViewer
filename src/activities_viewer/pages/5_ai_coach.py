"""
AI Coach Page.
Chat interface for analyzing training data with Gemini.
"""

import streamlit as st
from activities_viewer.services.activity_service import ActivityService
from activities_viewer.ai.client import GeminiClient
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

    # Sidebar for model selection
    with st.sidebar:
        st.header("⚙️ Settings")

        # Get available models
        with st.spinner("Loading available models..."):
            available_models = GeminiClient.get_available_models()

        if not available_models:
            st.error("Could not fetch available models. Please check your API key.")
            return

        # Model selector
        default_model = "gemini-2.0-flash"
        if default_model not in available_models:
            default_model = available_models[0]

        selected_model = st.selectbox(
            "Select Model",
            available_models,
            index=available_models.index(default_model)
            if default_model in available_models
            else 0,
            help="Choose which Gemini model to use for analysis",
        )

    # Initialize AI components
    if "ai_client" not in st.session_state or st.session_state.get(
        "selected_model"
    ) != selected_model:
        try:
            with st.spinner("Initializing AI Coach..."):
                st.session_state.ai_client = GeminiClient(model=selected_model)
                st.session_state.context_builder = ActivityContextBuilder(service)
                st.session_state.selected_model = selected_model
        except Exception as e:
            st.error(
                f"Failed to initialize AI Coach. Please check your GEMINI_API_KEY.\nError: {e}"
            )
            return

    client = st.session_state.ai_client
    context_builder = st.session_state.context_builder

    # Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI Coach. I can analyze your recent activities and answer questions about your training. How can I help you today?",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about your training..."):
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
                """

                final_prompt = (
                    f"{system_prompt}\n\nContext:\n{context}\n\nUser Question: {prompt}"
                )

                # Get response
                response = client.get_response(final_prompt)

            message_placeholder.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )

if __name__ == "__main__":
    main()
