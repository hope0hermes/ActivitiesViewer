FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/hope0hermes/ActivitiesViewer"
LABEL org.opencontainers.image.description="Strava Activities Viewer — fetch, analyze, and visualize your cycling data"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# System deps for potential native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install all three tools from PyPI (or private index)
# To use a private index, uncomment and set --index-url:
# ARG PIP_INDEX_URL=https://pypi.org/simple/
RUN pip install --no-cache-dir \
    strava-fetcher \
    strava-analyzer \
    activities-viewer

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Data volume mount point
VOLUME /data

# Streamlit port
EXPOSE 8501

# Streamlit config: disable CORS/XSRF for container networking
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
