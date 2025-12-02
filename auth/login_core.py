"""Core login flow logic decoupled from Auth class.

This module contains the low-level implementation of the login flow that talks
to Supabase and builds the session dictionary. The high-level Auth class is
responsible for persisting the session, setting it on the client, and fetching
the profile.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional


logger = logging.getLogger("SecureShare")


def perform_login(client: Any, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Perform Supabase email/password login and build a session dictionary.

    Args:
        client: Supabase client instance (created with anon key)
        email: User email
        password: User password

    Returns:
        Session dictionary on success, or None on failure.
    """
    try:
        logger.info(f"Attempting login for user: {email}")
        response = client.auth.sign_in_with_password({"email": email, "password": password})

        # Defensive checks in case the SDK changes shape
        if not response or not getattr(response, "session", None) or not getattr(response, "user", None):
            logger.error("Login failed: missing user or session in response")
            return None

        user_data = response.user
        session_data = response.session

        session = {
            "user_id": user_data.id,
            "email": user_data.email,
            "access_token": session_data.access_token,
            "refresh_token": session_data.refresh_token,
            "expires_at": time.time() + session_data.expires_in,
            "original_lifetime": session_data.expires_in,
        }

        logger.info("Login successful")
        return session

    except Exception as e:  # pragma: no cover - propagated to caller for tests
        logger.error(f"Login failed: {e}")
        return None


