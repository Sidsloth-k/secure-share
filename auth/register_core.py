"""Core registration flow logic decoupled from Auth class.

This module implements the low-level Supabase sign-up + optional auto-login
behavior and returns a session dictionary when possible. The high-level Auth
class is responsible for persisting the session, setting it on the client,
and creating the profile row in the application `users` table.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger("SecureShare")


def perform_register(
    client: Any,
    email: str,
    password: str,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Any]]:
    """
    Perform Supabase registration flow and optionally auto-login.

    Args:
        client: Supabase client instance (created with anon key)
        email: User email
        password: User password

    Returns:
        Tuple (success, session_dict, user_object)

        - success: True if the auth user was created successfully.
        - session_dict: Populated when a usable session was obtained
          (either from sign_up or follow-up sign_in); None otherwise.
        - user_object: Supabase user object when available, or None.
    """
    try:
        logger.info(f"Registering new user: {email}")
        response = client.auth.sign_up({"email": email, "password": password})

        if not response:
            logger.error("sign_up() returned no response")
            return False, None, None

        user_data = getattr(response, "user", None)
        session_data = getattr(response, "session", None)

        # Some Supabase configurations (or newer behavior) do not return a
        # session on sign_up even when email confirmation is disabled.
        # In that case, immediately sign in to get a session.
        if not session_data:
            logger.info(
                "No session returned from sign_up; attempting sign_in_with_password "
                "to obtain a session after registration"
            )
            try:
                login_resp = client.auth.sign_in_with_password({"email": email, "password": password})
                if login_resp and getattr(login_resp, "session", None):
                    session_data = login_resp.session
                    # Prefer fresh user data from login response if available
                    user_data = getattr(login_resp, "user", user_data)
                    logger.info("Obtained session via sign_in_with_password after sign_up")
                else:
                    logger.warning(
                        "sign_in_with_password after sign_up did not return a session. "
                        "Registration will succeed, but no app session/profile will be created yet "
                        "(likely due to email confirmation requirements)."
                    )
                    # Auth user exists, but we cannot build a local session.
                    return True, None, user_data
            except Exception as login_err:  # pragma: no cover - propagated behavior
                logger.warning(
                    f"Failed to obtain session via sign_in_with_password after sign_up: {login_err}. "
                    "Registration succeeded at auth level, but no app session/profile created."
                )
                return True, None, user_data

        if not user_data or not session_data:
            logger.error("Registration response missing user or session data.")
            return False, None, None

        session = {
            "user_id": user_data.id,
            "email": user_data.email,
            "access_token": session_data.access_token,
            "refresh_token": session_data.refresh_token,
            "expires_at": time.time() + session_data.expires_in,
            "original_lifetime": session_data.expires_in,
        }

        return True, session, user_data

    except Exception as e:  # pragma: no cover - propagated to caller
        logger.error(f"Registration failed: {e}")
        return False, None, None




