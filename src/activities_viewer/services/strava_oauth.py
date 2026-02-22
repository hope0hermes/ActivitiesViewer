"""
Strava OAuth helper functions.

Pure functions for token management and OAuth flow, separated from
the Streamlit page for testability.
"""

import json
import os
import time
from pathlib import Path

import requests

# ─── Constants ────────────────────────────────────────────────────────────

STRAVA_OAUTH_URL = "https://www.strava.com/oauth"
STRAVA_AUTHORIZE_URL = f"{STRAVA_OAUTH_URL}/authorize"
STRAVA_TOKEN_URL = f"{STRAVA_OAUTH_URL}/token"
SCOPES = "profile:read_all,activity:read_all"


# ─── Token helpers ────────────────────────────────────────────────────────


def _get_token_path(settings=None) -> Path:
    """Determine the token file path.

    Checks (in order):
    1. STRAVA_TOKEN_FILE env var
    2. Settings data_dir / token.json
    3. /data/fetcher/token.json (Docker default)
    4. ~/.strava_fetcher/data/token.json (local default)
    """
    env_path = os.environ.get("STRAVA_TOKEN_FILE")
    if env_path:
        return Path(env_path)

    if settings and hasattr(settings, "data_dir"):
        fetcher_dir = settings.data_dir / "fetcher"
        if fetcher_dir.exists():
            return fetcher_dir / "token.json"
        return settings.data_dir / "token.json"

    docker_path = Path("/data/fetcher/token.json")
    if docker_path.parent.exists():
        return docker_path

    return Path.home() / ".strava_fetcher" / "data" / "token.json"


def _load_token(token_path: Path) -> dict | None:
    """Load token from disk. Returns None if missing or invalid."""
    if not token_path.exists():
        return None
    try:
        with open(token_path) as f:
            data = json.load(f)
        if "access_token" in data and "refresh_token" in data:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _save_token(token_path: Path, token_data: dict) -> None:
    """Save token to disk."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w") as f:
        json.dump(token_data, f, indent=4)


def _is_token_valid(token: dict, buffer_seconds: int = 60) -> bool:
    """Check if token is still valid (not expired)."""
    expires_at = token.get("expires_at", 0)
    return time.time() < (expires_at - buffer_seconds)


def _exchange_code_for_token(
    client_id: str, client_secret: str, code: str
) -> dict:
    """Exchange authorization code for access token.

    Args:
        client_id: Strava API client ID.
        client_secret: Strava API client secret.
        code: Authorization code from Strava redirect.

    Returns:
        Token data dict with access_token, refresh_token, expires_at.

    Raises:
        requests.HTTPError: If token exchange fails.
    """
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": data["expires_at"],
    }


def _refresh_token(
    client_id: str, client_secret: str, refresh_token: str
) -> dict:
    """Refresh an expired access token.

    Returns:
        New token data dict.
    """
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": data["expires_at"],
    }


def _get_credentials() -> tuple[str, str]:
    """Get Strava client ID and secret from environment or unified config.

    Checks (in order):
    1. ``STRAVA_CLIENT_ID`` / ``STRAVA_CLIENT_SECRET`` env vars
    2. Unified config at ``ACTIVITIES_VIEWER_UNIFIED_CONFIG`` →
       ``fetcher.client_id`` / ``fetcher.client_secret``

    Returns:
        (client_id, client_secret) tuple.
    """
    client_id = os.environ.get("STRAVA_CLIENT_ID", "")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "")

    # Try unified config
    if not client_id or not client_secret:
        config_path = os.environ.get("ACTIVITIES_VIEWER_UNIFIED_CONFIG")
        if config_path and Path(config_path).exists():
            try:
                import yaml

                with open(config_path) as f:
                    config = yaml.safe_load(f)
                fetcher = config.get("fetcher", {})
                # Credentials live directly under fetcher: in the unified config
                client_id = client_id or str(fetcher.get("client_id", ""))
                client_secret = client_secret or str(
                    fetcher.get("client_secret", "")
                )
            except Exception:
                pass

    return client_id, client_secret


def _build_authorize_url(client_id: str, redirect_uri: str) -> str:
    """Build the Strava authorization URL."""
    return (
        f"{STRAVA_AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt=force"
        f"&scope={SCOPES}"
    )
