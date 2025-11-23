"""Main authentication module - thin wrapper around modular components."""
import os
import logging
import datetime
from typing import Optional

from auth.storage import load_session, save_session, clear_session, SESSION_FILE, set_encryption, set_db_storage
from auth.client_manager import ClientManager
from auth.token_manager import TokenManager
from auth.session_validator import SessionValidator
from auth.error_handler import AuthErrorHandler
from auth.encryption import SessionEncryption
from auth.metrics import TokenRefreshMetrics
from auth.db_storage import DatabaseSessionStorage

logger = logging.getLogger("SecureShare")

# Export session file path and functions for backward compatibility
__all__ = ['Auth', 'load_session', 'save_session', 'clear_session', 'SESSION_FILE']


class Auth:
    """Handles user authentication using Supabase."""
    
    # Refresh token when 80% of lifetime has passed (proactive refresh)
    REFRESH_THRESHOLD = 0.8
    
    def __init__(self, client, enable_encryption: bool = None, enable_metrics: bool = None, use_database: bool = None, use_async: bool = None):
        """
        Initialize Auth module.
        
        Args:
            client: Supabase client instance
            enable_encryption: Whether to encrypt session storage (None = auto-detect from env)
            enable_metrics: Whether to track token refresh metrics (None = auto-detect from env)
            use_database: Whether to use database storage (None = auto-detect from env)
            use_async: Whether to use async mode (None = auto-detect from env)
        """
        self.client = client
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        # Auto-detect from environment if not specified
        if enable_encryption is None:
            enable_encryption = os.getenv("ENABLE_SESSION_ENCRYPTION", "false").lower() == "true"
        if enable_metrics is None:
            enable_metrics = os.getenv("ENABLE_REFRESH_METRICS", "false").lower() == "true"
        if use_database is None:
            # Production uses database, development uses file
            use_database = environment == "production"
        if use_async is None:
            use_async = os.getenv("USE_ASYNC_AUTH", "false").lower() == "true"
        
        self._enable_encryption = enable_encryption
        self._use_database = use_database
        self._use_async = use_async
        
        # Initialize encryption if enabled
        if enable_encryption:
            encryption_key = os.getenv("SESSION_ENCRYPTION_KEY")
            if encryption_key:
                import base64
                try:
                    key_bytes = base64.urlsafe_b64decode(encryption_key.encode())
                    self._encryption = SessionEncryption(key=key_bytes)
                except Exception as e:
                    logger.warning(f"Failed to load encryption key from env: {e}, using default")
                    self._encryption = SessionEncryption()
            else:
                self._encryption = SessionEncryption()
            set_encryption(self._encryption)
        else:
            self._encryption = None
        
        # Initialize metrics if enabled
        self._metrics = TokenRefreshMetrics() if enable_metrics else None
        
        # Initialize database storage if in production mode
        if use_database:
            self._db_storage = DatabaseSessionStorage(client)
            set_db_storage(self._db_storage)
            logger.info("Using database session storage (production mode)")
        else:
            self._db_storage = None
            logger.debug("Using file-based session storage (development mode)")
        
        # Load session (will use database or file based on mode)
        self.session = load_session()
        
        # Initialize modular components
        self._client_manager = ClientManager(client)
        self._token_manager = TokenManager(
            client, 
            refresh_threshold=self.REFRESH_THRESHOLD,
            metrics=self._metrics
        )
        self._session_validator = SessionValidator(client)
        self._error_handler = AuthErrorHandler(self._refresh_token)
        
        # Set session on client if we have a saved session
        if self.session:
            self._set_client_session()
        
        logger.debug(
            f"Auth module initialized "
            f"(encryption: {enable_encryption}, metrics: {enable_metrics}, "
            f"database: {use_database}, async: {use_async})"
        )
    
    def _set_client_session(self) -> None:
        """Set the session on the Supabase client."""
        access_token = self.session.get('access_token')
        refresh_token = self.session.get('refresh_token')
        self._client_manager.set_session(access_token, refresh_token)
    
    def _refresh_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        return self._token_manager.refresh_token(
            session=self.session,
            save_callback=self._save_session,
            set_client_callback=self._client_manager.set_session,
            clear_callback=self._clear_session_internal
        )
    
    def _save_session(self, session: dict) -> None:
        """Save session and update internal state."""
        save_session(session, encrypt=self._enable_encryption)
        self.session = session
    
    def _clear_session_internal(self) -> None:
        """Clear session internally."""
        user_id = self.session.get('user_id') if self.session else None
        clear_session(user_id=user_id)
        self.session = {}
    
    def _ensure_valid_session(self) -> bool:
        """Ensure the session is valid, refreshing if necessary."""
        return self._token_manager.ensure_valid_session(
            session=self.session,
            refresh_callback=self._refresh_token
        )
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated, refreshing token if needed."""
        return self._session_validator.is_authenticated(
            session=self.session,
            ensure_valid_callback=self._ensure_valid_session,
            refresh_callback=self._refresh_token
        )
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure user is authenticated before making API calls.
        This method should be called before any protected operations.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.is_authenticated()
    
    def handle_auth_error(self, error: Exception) -> bool:
        """
        Handle authentication errors from API calls.
        Attempts to refresh token if error is auth-related.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if error was handled (token refreshed), False otherwise
        """
        return self._error_handler.handle_auth_error(error)
    
    def login(self, email: str, password: str) -> bool:
        """
        Login user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info(f"Attempting login for user: {email}")
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            
            if response:
                user_data = response.user
                session_data = response.session
                
                import time
                self.session = {
                    'user_id': user_data.id,
                    'email': user_data.email,
                    'access_token': session_data.access_token,
                    'refresh_token': session_data.refresh_token,
                    'expires_at': time.time() + session_data.expires_in,
                    'original_lifetime': session_data.expires_in
                }
                
                self._save_session(self.session)
                self._set_client_session()
                logger.info("Login successful")
                
                # Optionally, fetch and store profile
                self._fetch_user_profile()
                return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
        return False
    
    def register(self, email: str, password: str, display_name: str) -> bool:
        """
        Register a new user.
        
        Args:
            email: User email
            password: User password
            display_name: User display name
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            logger.info(f"Registering new user: {email}")
            response = self.client.auth.sign_up({"email": email, "password": password})
            
            if response:
                user_data = response.user
                session_data = response.session
                
                if not session_data:
                    logger.info("Registration successful. Email verification required.")
                    return True
                
                import time
                self.session = {
                    'user_id': user_data.id,
                    'email': user_data.email,
                    'access_token': session_data.access_token,
                    'refresh_token': session_data.refresh_token,
                    'expires_at': time.time() + session_data.expires_in,
                    'original_lifetime': session_data.expires_in
                }
                
                self._save_session(self.session)
                self._set_client_session()
                
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
        """Logout user and clear session."""
        try:
            if self.session:
                logger.info("Logging out")
                self.client.auth.sign_out()
                self._clear_session_internal()
            else:
                logger.debug("No active session to log out from")
        except Exception as e:
            logger.error(f"Logout failed: {e}")
    
    def get_user_id(self) -> Optional[str]:
        """Get current user ID."""
        return self.session.get('user_id') if self.session else None
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token."""
        return self.session.get('access_token') if self.session else None
    
    def get_session_time_remaining(self) -> int:
        """
        Get seconds until session expires.
        
        Returns:
            Seconds until expiration, or 0 if no session
        """
        return self._token_manager.get_session_time_remaining(self.session)
    
    def get_refresh_metrics(self, window_seconds: int = 3600) -> dict:
        """
        Get token refresh metrics.
        
        Args:
            window_seconds: Time window in seconds (default 1 hour)
            
        Returns:
            Dictionary with refresh statistics, or empty dict if metrics disabled
        """
        if self._metrics:
            return self._metrics.get_stats(window_seconds)
        return {}
    
    def get_async_auth(self):
        """
        Get async auth wrapper if async mode is enabled.
        
        Returns:
            AsyncAuth instance if async enabled, None otherwise
        """
        if self._use_async:
            from auth.async_auth import AsyncAuth
            return AsyncAuth(self.client, self)
        return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (database mode only).
        
        Returns:
            Number of sessions cleaned up
        """
        if self._db_storage:
            return self._db_storage.cleanup_expired_sessions()
        return 0
    
    def _fetch_user_profile(self) -> None:
        """Fetch and store user profile."""
        try:
            user_id = self.get_user_id()
            if not user_id:
                return
            
            response = self.client.table('users').select('*').eq('id', user_id).execute()
            if response.data:
                self.session['profile'] = response.data[0]
                self._save_session(self.session)
                logger.debug("User profile fetched and saved")
        except Exception as e:
            logger.warning(f"Failed to fetch user profile: {e}")
