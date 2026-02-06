"""
Gemini Client wrapper.
"""

import os
import logging
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API via LangChain."""

    # Cache for available models
    _available_models = None

    def __init__(self, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini Client.

        Args:
            model: Model name to use. Defaults to gemini-2.0-flash.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found")
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)

        self.model = model
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=True,
        )

    @staticmethod
    def get_available_models() -> list:
        """
        Get list of available Gemini models.

        Returns:
            List of model names available for use.
        """
        if GeminiClient._available_models is not None:
            return GeminiClient._available_models

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return []

            genai.configure(api_key=api_key)
            models = genai.list_models()

            # Filter for models that support generateContent
            available = []
            for model in models:
                if "generateContent" in model.supported_generation_methods:
                    available.append(model.name.replace("models/", ""))

            # Cache the result
            GeminiClient._available_models = available
            return available
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            # Return a sensible default if API fails
            return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def get_response(self, prompt: str) -> str:
        """Get a response from the LLM."""
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return f"Error: {str(e)}"


def render_ai_model_selector() -> str | None:
    """
    Render a shared AI model selector in the sidebar.

    Stores the selection in st.session_state.selected_ai_model so it
    persists across pages (AI Coach, Training Plan, etc.).

    Returns:
        The selected model name, or None if no models available.
    """
    import streamlit as st

    with st.sidebar:
        st.divider()
        st.markdown("#### 🤖 AI Model")
        available_models = GeminiClient.get_available_models()

        if not available_models:
            st.error("No AI models available. Check GEMINI_API_KEY.")
            return None

        default_model = "gemini-2.0-flash"
        if default_model not in available_models:
            default_model = available_models[0]

        # Use session state to remember across pages
        current = st.session_state.get("selected_ai_model", default_model)
        if current not in available_models:
            current = default_model

        selected = st.selectbox(
            "Select Model",
            available_models,
            index=available_models.index(current),
            key="ai_model_sidebar",
            label_visibility="collapsed",
        )

        st.session_state.selected_ai_model = selected
        return selected
