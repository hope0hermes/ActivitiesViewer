# =============================================================================
# ActivitiesViewer - Multi-stage Docker build
# =============================================================================
# Usage:
#   docker build -t activities-viewer .
#   docker run -p 8501:8501 -v ./data:/data -v ./config.yaml:/app/config.yaml activities-viewer
#
# Publish to GHCR:
#   docker build -t ghcr.io/hope0hermes/activities-viewer:latest .
#   docker push ghcr.io/hope0hermes/activities-viewer:latest
# =============================================================================

FROM python:3.12-slim AS base

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock uv.toml ./

# Install dependencies (without the project itself yet)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy the full source
COPY src/ src/
COPY .streamlit/ .streamlit/
COPY examples/ examples/

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# =============================================================================
# Runtime stage
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the entire venv and app from build stage
COPY --from=base /app /app

# Streamlit configuration for Docker (listen on all interfaces)
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Data volume mount point
VOLUME ["/data"]

EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Default: run the viewer with config at /app/config.yaml
ENTRYPOINT ["uv", "run", "activities-viewer"]
CMD ["run", "--config", "/app/config.yaml"]
