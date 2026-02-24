"""
Strava OAuth helper functions.

Delegates token I/O and OAuth exchange to StravaFetcher's library API.
Pure functions for token management and OAuth flow, separated from
the Streamlit page for testability.

All functions maintain the same dict-based public API so callers
(pages/8_strava_connect.py) require zero changes.
"""

import os
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────────────────

STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
SCOPES = "profile:read_all,activity:read_all"


# ─── Internal helpers ─────────────────────────────────────────────────────


def _build_api_settings(client_id: str, client_secret: str):
    """Construct a ``StravaAPISettings`` for the StravaFetcher client.

    Uses lazy import so the module loads even if strava-fetcher is not installed.
    """
    from strava_fetcher import StravaAPISettings

    return StravaAPISettings(client_id=client_id, client_secret=client_secret)


def _token_to_dict(token) -> dict:
    """Convert a StravaFetcher ``Token`` model to a plain dict."""
    return {
        "access_token": token.access_token.get_secret_value(),
        "refresh_token": token.refresh_token.get_secret_value(),
        "expires_at": token.expires_at,
    }


def _dict_to_token(token_data: dict):
    """Convert a plain dict to a StravaFetcher ``Token`` model."""
    from pydantic import SecretStr
    from strava_fetcher import Token

    return Token(
        access_token=SecretStr(token_data["access_token"]),
        refresh_token=SecretStr(token_data["refresh_token"]),
        expires_at=token_data.get("expires_at", 0),
    )


# ─── Token path resolution (Viewer-specific) ─────────────────────────────


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


# ─── Token I/O (delegates to StravaFetcher TokenPersistence) ──────────────


def _load_token(token_path: Path) -> dict | None:
    """Load token from disk using StravaFetcher's ``TokenPersistence``.

    Returns:
        Token data dict, or None if file missing/invalid.
    """
    from strava_fetcher import TokenPersistence

    tp = TokenPersistence(token_path)
    token = tp.read()
    if token is None:
        return None
    return _token_to_dict(token)


def _save_token(token_path: Path, token_data: dict) -> None:
    """Save token to disk using StravaFetcher's ``TokenPersistence``."""
    from strava_fetcher import TokenPersistence

    token = _dict_to_token(token_data)
    tp = TokenPersistence(token_path)
    tp.write(token)


# ─── Token validation (delegates to Token.is_expired) ─────────────────────


def _is_token_valid(token: dict, buffer_seconds: int = 60) -> bool:
    """Check if token is still valid (not expired).

    Uses StravaFetcher's ``Token.is_expired()`` for consistent logic.
    """
    t = _dict_to_token(token)
    return not t.is_expired(buffer_seconds=buffer_seconds)


# ─── OAuth exchange (delegates to StravaClient) ──────────────────────────


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
        strava_fetcher.exceptions.APIError: If token exchange fails.
    """
    from strava_fetcher import StravaClient

    api_settings = _build_api_settings(client_id, client_secret)
    client = StravaClient(api_settings)
    token = client.exchange_auth_code_for_token(code)
    return _token_to_dict(token)


def _refresh_token(
    client_id: str, client_secret: str, refresh_token: str
) -> dict:
    """Refresh an expired access token.

    Args:
        client_id: Strava API client ID.
        client_secret: Strava API client secret.
        refresh_token: Current refresh token string.

    Returns:
        New token data dict.

    Raises:
        strava_fetcher.exceptions.APIError: If token refresh fails.
    """
    from pydantic import SecretStr
    from strava_fetcher import StravaClient

    api_settings = _build_api_settings(client_id, client_secret)
    client = StravaClient(api_settings)
    token = client.refresh_token(SecretStr(refresh_token))
    return _token_to_dict(token)


# ─── Credentials (Viewer-specific, unchanged) ────────────────────────────


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
                client_id = client_id or str(fetcher.get("client_id", ""))
                client_secret = client_secret or str(
                    fetcher.get("client_secret", "")
                )
            except Exception:
                pass

    return client_id, client_secret


# ─── Authorize URL (Viewer-specific, unchanged) ──────────────────────────


def _build_authorize_url(client_id: str, redirect_uri: str) -> str:
    """Build the Strava authorization URL.

    Note: StravaClient.get_authorization_url() exists but hardcodes
    ``redirect_uri=http://localhost``. We build the URL manually to
    support Streamlit's custom redirect URI.
    """
    return (
        f"{STRAVA_AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt=force"
        f"&scope={SCOPES}"
    )
