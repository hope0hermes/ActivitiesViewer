"""
Strava OAuth page for Docker users.

Provides a browser-based OAuth flow so users don't need to use the CLI
for initial token authorization. Captures the authorization code from
Strava's redirect and exchanges it for an access token.
"""

import time

import requests
import streamlit as st

from activities_viewer.services.strava_oauth import (
    _build_authorize_url,
    _exchange_code_for_token,
    _get_credentials,
    _get_token_path,
    _is_token_valid,
    _load_token,
    _refresh_token,
    _save_token,
)

st.set_page_config(page_title="Strava Connect", page_icon="🔗", layout="centered")


# ─── Main page ───────────────────────────────────────────────────────────


def main():
    """OAuth connection page."""
    settings = st.session_state.get("settings")

    st.title("🔗 Strava Connect")

    token_path = _get_token_path(settings)
    client_id, client_secret = _get_credentials()

    # ── Handle OAuth callback (code in query params) ──────────────────
    query_params = st.query_params
    code = query_params.get("code")

    if code:
        if not client_id or not client_secret:
            st.error(
                "Cannot exchange authorization code: Strava credentials "
                "not configured. Set `STRAVA_CLIENT_ID` and "
                "`STRAVA_CLIENT_SECRET` environment variables."
            )
        else:
            with st.spinner("Exchanging authorization code for token..."):
                try:
                    token_data = _exchange_code_for_token(
                        client_id, client_secret, code
                    )
                    _save_token(token_path, token_data)
                    st.success(
                        "✅ Successfully connected to Strava! "
                        "Your token has been saved."
                    )
                    # Clear the code from URL
                    st.query_params.clear()
                    st.rerun()
                except requests.HTTPError as e:
                    st.error(
                        f"Failed to exchange code: {e.response.status_code} "
                        f"— {e.response.text}"
                    )
                except Exception as e:
                    st.error(f"Token exchange failed: {e}")
        return

    # ── Show current status ───────────────────────────────────────────
    token = _load_token(token_path)

    if token:
        is_valid = _is_token_valid(token)

        # Auto-refresh expired tokens silently on page load
        if not is_valid and client_id and client_secret:
            try:
                token = _refresh_token(
                    client_id, client_secret, token["refresh_token"]
                )
                _save_token(token_path, token)
                is_valid = True
            except Exception:
                pass  # Fall through to manual refresh UI below

        if is_valid:
            expires_at = token.get("expires_at", 0)
            remaining = int(expires_at - time.time())
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60

            st.success("✅ Connected to Strava")
            st.markdown(f"Token expires in **{hours}h {minutes}m**")
            st.caption(f"Token file: `{token_path}`")

            # Offer refresh
            if st.button("🔄 Refresh Token Now"):
                if client_id and client_secret:
                    try:
                        new_token = _refresh_token(
                            client_id,
                            client_secret,
                            token["refresh_token"],
                        )
                        _save_token(token_path, new_token)
                        st.success("Token refreshed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Refresh failed: {e}")
                else:
                    st.warning("Credentials not configured for refresh.")

        else:
            st.warning("⚠️ Token expired")

            if client_id and client_secret:
                if st.button("🔄 Refresh Expired Token"):
                    try:
                        new_token = _refresh_token(
                            client_id,
                            client_secret,
                            token["refresh_token"],
                        )
                        _save_token(token_path, new_token)
                        st.success("Token refreshed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Refresh failed: {e}. Try re-authorizing below.")
            else:
                st.info("Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET to auto-refresh.")

    else:
        st.info("No Strava token found. Authorize below to connect.")

    st.divider()

    # ── Authorization flow ────────────────────────────────────────────
    st.header("Authorize with Strava")

    if not client_id:
        st.warning(
            "**Strava API credentials not configured.**\n\n"
            "1. Go to [Strava API Settings](https://www.strava.com/settings/api)\n"
            "2. Register an app (set callback domain to `localhost`)\n"
            "3. Set `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` "
            "in your `.env` file or environment\n"
            "4. Restart the container"
        )
        return

    # Build redirect URI — must match Streamlit's page path (lowercase,
    # numeric prefix stripped).  File 8_strava_connect.py → /strava_connect
    redirect_uri = "http://localhost:8501/strava_connect"

    auth_url = _build_authorize_url(client_id, redirect_uri)

    st.markdown(
        """
        Click the button below to authorize this app with Strava.
        You'll be redirected to Strava to grant permission, then
        sent back here automatically.
        """
    )

    st.link_button(
        "🔶 Connect with Strava",
        auth_url,
        use_container_width=True,
    )

    st.caption(
        "This grants read-only access to your profile and activities. "
        "You can revoke access at any time from "
        "[Strava Settings](https://www.strava.com/settings/apps)."
    )

    # Manual code entry fallback
    with st.expander("Manual code entry (if redirect doesn't work)"):
        st.markdown(
            f"1. Open this URL in your browser:\n\n"
            f"```\n{auth_url}\n```\n\n"
            f"2. Authorize the app\n"
            f"3. Copy the `code` parameter from the redirect URL\n"
            f"4. Paste it below:"
        )
        manual_code = st.text_input("Authorization code:")
        if st.button("Submit Code") and manual_code:
            try:
                token_data = _exchange_code_for_token(
                    client_id, client_secret, manual_code.strip()
                )
                _save_token(token_path, token_data)
                st.success("✅ Connected! Token saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")


if __name__ == "__main__":
    main()
else:
    main()
