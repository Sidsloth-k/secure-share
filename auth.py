import os
import sys
import json
import time
import logging
import datetime
import getpass

from supabase import create_client
from dotenv import load_dotenv

logger = logging.getLogger("SecureShare")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".secure_share")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")

def load_session() -> dict:
    """Load the user session from file."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session = json.load(f)
                logger.debug("Loaded session from file")
                return session
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
    return {}

def save_session(session: dict) -> None:
    """Save user session to file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f)
        logger.debug("Saved session to file")
    except Exception as e:
        logger.error(f"Failed to save session: {e}")

def clear_session() -> None:
    """Clear user session."""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    logger.debug("Cleared session")

class Auth:
    """Handles user authentication using Supabase."""
    
    def __init__(self, client):
        self.client = client
        self.session = load_session()
        logger.debug("Auth module initialized")
    
    def is_authenticated(self) -> bool:
        if not self.session:
            return False
        try:
            expiry_time = self.session.get('expires_at', 0)
            if expiry_time < time.time():
                logger.debug("Session has expired")
                return False
            user = self.client.auth.get_user(self.session.get('access_token', ''))
            logger.debug("Session is valid")
            return True
        except Exception as e:
            logger.warning(f"Session verification failed: {e}")
            return False
    
    def login(self, email: str, password: str) -> bool:
        try:
            logger.info(f"Attempting login for user: {email}")
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response:
                user_data = response.user
                session_data = response.session
                self.session = {
                    'user_id': user_data.id,
                    'email': user_data.email,
                    'access_token': session_data.access_token,
                    'refresh_token': session_data.refresh_token,
                    'expires_at': time.time() + session_data.expires_in
                }
                save_session(self.session)
                logger.info("Login successful")
                # Optionally, fetch and store profile
                self._fetch_user_profile()
                return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
        return False
    
    def register(self, email: str, password: str, display_name: str) -> bool:
        try:
            logger.info(f"Registering new user: {email}")
            response = self.client.auth.sign_up({"email": email, "password": password})
            if response:
                user_data = response.user
                session_data = response.session
                if not session_data:
                    logger.info("Registration successful. Email verification required.")
                    return True
                self.session = {
                    'user_id': user_data.id,
                    'email': user_data.email,
                    'access_token': session_data.access_token,
                    'refresh_token': session_data.refresh_token,
                    'expires_at': time.time() + session_data.expires_in
                }
                save_session(self.session)
                # Create user profile in the database
                self.client.table('users').insert({
                    'id': user_data.id,
                    'email': email,
                    'display_name': display_name,
                    'created_at': datetime.datetime.now().isoformat(),
                    'cloud_connected': False
                }).execute()
                logger.info("Registration and profile creation successful")
                return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
        return False
    
    def logout(self) -> None:
        try:
            if self.session:
                logger.info("Logging out")
                self.client.auth.sign_out()
                clear_session()
                self.session = {}
            else:
                logger.debug("No active session to log out from")
        except Exception as e:
            logger.error(f"Logout failed: {e}")
    
    def get_user_id(self) -> str:
        return self.session.get('user_id')
    
    def get_access_token(self) -> str:
        return self.session.get('access_token')
    
    def _fetch_user_profile(self) -> None:
        try:
            user_id = self.get_user_id()
            if not user_id:
                return
            response = self.client.table('users').select('*').eq('id', user_id).execute()
            if response.data:
                self.session['profile'] = response.data[0]
                save_session(self.session)
                logger.debug("User profile fetched and saved")
        except Exception as e:
            logger.warning(f"Failed to fetch user profile: {e}")
