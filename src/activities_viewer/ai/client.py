"""
Gemini Client wrapper.
"""

import logging
import os
import re

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


def parse_model_version(model_name: str) -> tuple[str, tuple[int, int, int]]:
    """
    Parse a model name and extract the base model and version.

    Handles both standard (gemini-2.5-flash) and preview (gemini-3-flash-preview) formats.
    Preview versions are treated with higher priority.

    Examples:
        "gemini-2.5-flash" -> ("gemini-flash", (2, 5, 0))
        "gemini-3-flash-preview" -> ("gemini-flash", (3, 0, 999))  # preview gets high patch
        "gemini-2.5-flash-001" -> ("gemini-flash", (2, 5, 1))
        "gemini-1.5-pro" -> ("gemini-pro", (1, 5, 0))

    Args:
        model_name: Full model name from Gemini API.

    Returns:
        Tuple of (base_model_type, version_tuple).
    """
    # Extract model type and version: "gemini-X(.Y)-(flash|pro)(-SUFFIX)?"
    # Handles both "gemini-2.5-flash" and "gemini-3-flash-preview"
    match = re.match(r"gemini-(\d+)(?:\.(\d+))?-(flash|pro)(?:-(preview|\d+))?", model_name)
    if not match:
        return (model_name, (0, 0, 0))

    major_str, minor_str, mtype, suffix = match.groups()
    major = int(major_str)
    minor = int(minor_str) if minor_str else 0

    # Handle patch/suffix: preview gets high priority (999), numeric patches are lower
    if suffix == "preview":
        patch = 999  # Preview versions get highest priority
    elif suffix:
        patch = int(suffix)
    else:
        patch = 0

    return (f"gemini-{mtype}", (major, minor, patch))


def get_latest_flash_model(available_models: list[str]) -> str:
    """
    Select the latest flash model from the list using semantic versioning.

    Filters for flash models, parses versions semantically, and returns
    the highest version. Prioritizes stable releases over dev versions.

    Args:
        available_models: List of available model names from Gemini API.

    Returns:
        The latest flash model name, or first available if none found.
    """
    if not available_models:
        return "gemini-2.5-flash"  # Fallback default

    # Filter for flash models
    flash_models = [m for m in available_models if "flash" in m.lower()]

    if not flash_models:
        # No flash models, return first available
        return available_models[0]

    # Parse versions and sort by semantic version (descending)
    parsed = []
    for model in flash_models:
        base, version = parse_model_version(model)
        parsed.append((model, base, version))

    # Sort by version (descending): (major, minor, patch)
    parsed.sort(key=lambda x: x[2], reverse=True)

    # Return the latest version
    return parsed[0][0]


class GeminiClient:
    """Wrapper for Google Gemini API via LangChain."""

    # Cache for available models
    _available_models = None

    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini Client.

        Args:
            model: Model name to use. Defaults to gemini-2.5-flash.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found")
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)

        self.model = model
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
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
            # Return sensible defaults if API fails
            return ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def get_response(self, prompt: str) -> str:
        """Get a response from the LLM."""
        try:
            response = self.llm.invoke(prompt)
            return str(response.content)
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

        # Select the latest flash model as default
        default_model = get_latest_flash_model(available_models)

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
