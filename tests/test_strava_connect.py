"""Tests for Strava OAuth helper functions.

Delegates to StravaFetcher's Client/TokenPersistence — tests mock at
the library boundary rather than raw HTTP calls.
"""

import json
import os
import time
from unittest.mock import MagicMock, patch

from activities_viewer.services.strava_oauth import (
    _build_authorize_url,
    _exchange_code_for_token,
    _get_credentials,
    _is_token_valid,
    _load_token,
    _refresh_token,
    _save_token,
)

# ─── Helpers ──────────────────────────────────────────────────────────────

def _sample_token_dict(
    access="abc123", refresh="def456", expires_at=None
) -> dict:
    """Return a minimal token dict for testing."""
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": expires_at or int(time.time()) + 3600,
    }


def _mock_token(access="new_access", refresh="new_refresh", expires_at=99999):
    """Return a MagicMock that behaves like a StravaFetcher Token."""
    tok = MagicMock()
    tok.access_token.get_secret_value.return_value = access
    tok.refresh_token.get_secret_value.return_value = refresh
    tok.expires_at = expires_at
    return tok


# ─── Token I/O ────────────────────────────────────────────────────────────


class TestTokenHelpers:
    """Tests for token load/save/validate helpers.

    These write real JSON files because TokenPersistence reads the same
    ``{access_token, refresh_token, expires_at}`` format.
    """

    def test_load_token_valid(self, tmp_path):
        """Load a valid token file."""
        token_file = tmp_path / "token.json"
        token_data = _sample_token_dict()
        token_file.write_text(json.dumps(token_data))

        result = _load_token(token_file)
        assert result is not None
        assert result["access_token"] == "abc123"

    def test_load_token_missing(self, tmp_path):
        """Returns None for missing file."""
        result = _load_token(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_token_invalid_json(self, tmp_path):
        """Returns None for invalid JSON."""
        token_file = tmp_path / "token.json"
        token_file.write_text("not json")

        result = _load_token(token_file)
        assert result is None

    def test_save_token(self, tmp_path):
        """Save token creates file and directories."""
        token_file = tmp_path / "subdir" / "token.json"
        token_data = _sample_token_dict(access="abc", refresh="def", expires_at=12345)

        _save_token(token_file, token_data)

        assert token_file.exists()
        saved = json.loads(token_file.read_text())
        assert saved["access_token"] == "abc"

    def test_save_then_load_roundtrip(self, tmp_path):
        """Token survives a save → load round-trip."""
        token_file = tmp_path / "token.json"
        original = _sample_token_dict(access="rt_a", refresh="rt_r", expires_at=55555)

        _save_token(token_file, original)
        loaded = _load_token(token_file)

        assert loaded == original

    def test_is_token_valid(self):
        """Token validity check."""
        # Valid token (expires in 1 hour)
        assert _is_token_valid(_sample_token_dict(expires_at=int(time.time()) + 3600))

        # Expired token
        assert not _is_token_valid(
            _sample_token_dict(expires_at=int(time.time()) - 100)
        )

        # About to expire (within buffer)
        assert not _is_token_valid(
            _sample_token_dict(expires_at=int(time.time()) + 30),
            buffer_seconds=60,
        )


# ─── Authorize URL ────────────────────────────────────────────────────────


class TestBuildAuthorizeUrl:
    """Tests for OAuth URL construction."""

    def test_basic_url(self):
        url = _build_authorize_url("12345", "http://localhost:8501/callback")
        assert "client_id=12345" in url
        assert "redirect_uri=http://localhost:8501/callback" in url
        assert "response_type=code" in url
        assert "scope=profile:read_all,activity:read_all" in url
        assert "approval_prompt=force" in url


# ─── Credentials ──────────────────────────────────────────────────────────


class TestGetCredentials:
    """Tests for credential resolution."""

    def test_from_environment(self):
        with patch.dict(
            os.environ,
            {
                "STRAVA_CLIENT_ID": "99999",
                "STRAVA_CLIENT_SECRET": "secret123",
            },
        ):
            cid, csecret = _get_credentials()
            assert cid == "99999"
            assert csecret == "secret123"

    def test_empty_when_not_configured(self):
        with patch.dict(
            os.environ,
            {
                "STRAVA_CLIENT_ID": "",
                "STRAVA_CLIENT_SECRET": "",
                "ACTIVITIES_VIEWER_UNIFIED_CONFIG": "",
            },
            clear=False,
        ):
            cid, csecret = _get_credentials()
            assert cid == ""
            assert csecret == ""

    def test_from_unified_config(self, tmp_path):
        """Credentials are loaded from fetcher.client_id in unified config."""
        import yaml

        cfg = tmp_path / "unified.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "data_dir": str(tmp_path),
                    "fetcher": {
                        "client_id": "11111",
                        "client_secret": "cfg_secret",
                    },
                }
            )
        )
        with patch.dict(
            os.environ,
            {
                "STRAVA_CLIENT_ID": "",
                "STRAVA_CLIENT_SECRET": "",
                "ACTIVITIES_VIEWER_UNIFIED_CONFIG": str(cfg),
            },
            clear=False,
        ):
            cid, csecret = _get_credentials()
            assert cid == "11111"
            assert csecret == "cfg_secret"


# ─── OAuth exchange / refresh ─────────────────────────────────────────────


class TestExchangeCodeForToken:
    """Tests for token exchange — mocks StravaClient at the library boundary."""

    @patch("strava_fetcher.StravaClient")
    def test_successful_exchange(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.exchange_auth_code_for_token.return_value = _mock_token(
            access="new_access", refresh="new_refresh", expires_at=99999,
        )
        mock_client_cls.return_value = mock_client

        result = _exchange_code_for_token("cid", "csecret", "auth_code")

        assert result["access_token"] == "new_access"
        assert result["refresh_token"] == "new_refresh"
        assert result["expires_at"] == 99999
        mock_client.exchange_auth_code_for_token.assert_called_once_with(
            "auth_code"
        )

    @patch("strava_fetcher.StravaClient")
    def test_successful_refresh(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.refresh_token.return_value = _mock_token(
            access="refreshed_access", refresh="refreshed_refresh", expires_at=88888,
        )
        mock_client_cls.return_value = mock_client

        result = _refresh_token("cid", "csecret", "old_refresh")

        assert result["access_token"] == "refreshed_access"
        assert result["refresh_token"] == "refreshed_refresh"
        assert result["expires_at"] == 88888

        # Verify refresh_token was called with a SecretStr wrapping the value
        call_args = mock_client.refresh_token.call_args
        assert call_args[0][0].get_secret_value() == "old_refresh"
