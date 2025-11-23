"""Token refresh management with concurrency control and retry logic."""
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger("SecureShare")

# Default refresh threshold: refresh when 80% of lifetime has passed
DEFAULT_REFRESH_THRESHOLD = 0.8
# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class TokenManager:
    """Manages token refresh with thread safety and retry logic."""
    
    def __init__(self, client, refresh_threshold: float = DEFAULT_REFRESH_THRESHOLD, metrics=None):
        self.client = client
        self.refresh_threshold = refresh_threshold
        self._refresh_lock = threading.Lock()
        self._refresh_in_progress = False
        self._metrics = metrics  # Optional metrics tracker
    
    def refresh_token(
        self, 
        session: dict, 
        save_callback,
        set_client_callback,
        clear_callback,
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Args:
            session: Current session dictionary
            save_callback: Function to save session (session_dict) -> None
            set_client_callback: Function to set client session (access_token, refresh_token) -> bool
            clear_callback: Function to clear session () -> None
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if refresh successful, False otherwise
        """
        if not session:
            return False
        
        refresh_token = session.get('refresh_token')
        if not refresh_token:
            logger.warning("No refresh token available")
            return False
        
        # Use lock to prevent concurrent refreshes
        with self._refresh_lock:
            if self._refresh_in_progress:
                logger.debug("Token refresh already in progress, waiting...")
                # Wait a bit and check if refresh completed
                time.sleep(0.5)
                return session.get('access_token') is not None
            
            self._refresh_in_progress = True
            
            try:
                return self._do_refresh(
                    session, 
                    refresh_token,
                    save_callback,
                    set_client_callback,
                    clear_callback,
                    max_retries
                )
            finally:
                self._refresh_in_progress = False
    
    def _do_refresh(
        self,
        session: dict,
        refresh_token: str,
        save_callback,
        set_client_callback,
        clear_callback,
        max_retries: int
    ) -> bool:
        """Perform the actual token refresh with retry logic."""
        delay = DEFAULT_RETRY_DELAY
        start_time = time.time()
        error_type = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Refreshing access token (attempt {attempt + 1}/{max_retries})")
                response = self.client.auth.refresh_session(refresh_token)
                
                if response and response.session:
                    session_data = response.session
                    # Preserve original_lifetime if it exists, otherwise use new expires_in
                    original_lifetime = session.get('original_lifetime', session_data.expires_in)
                    
                    session.update({
                        'access_token': session_data.access_token,
                        'refresh_token': session_data.refresh_token,
                        'expires_at': time.time() + session_data.expires_in,
                        'original_lifetime': original_lifetime
                    })
                    
                    save_callback(session)
                    
                    # Set session on client
                    duration_ms = (time.time() - start_time) * 1000
                    if set_client_callback(session_data.access_token, session_data.refresh_token):
                        if self._metrics:
                            self._metrics.record_refresh(True, duration_ms, None, attempt + 1)
                        logger.info("Token refreshed successfully")
                        return True
                    else:
                        logger.warning("Token refreshed but failed to set on client")
                        if self._metrics:
                            self._metrics.record_refresh(True, duration_ms, None, attempt + 1)
                        # Still return True as tokens are valid
                        return True
                        
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__
                duration_ms = (time.time() - start_time) * 1000
                
                # Don't retry on authentication errors (invalid refresh token)
                if any(keyword in error_str for keyword in ['invalid', 'expired', '401', '403', 'unauthorized']):
                    if self._metrics:
                        self._metrics.record_refresh(False, duration_ms, error_type, attempt + 1)
                    logger.error(f"Token refresh failed (non-retryable): {e}")
                    clear_callback()
                    return False
                
                # Retry on network/temporary errors
                if attempt < max_retries - 1:
                    logger.warning(f"Token refresh attempt {attempt + 1} failed: {e}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= DEFAULT_BACKOFF_MULTIPLIER
                else:
                    if self._metrics:
                        self._metrics.record_refresh(False, duration_ms, error_type, attempt + 1)
                    logger.error(f"Token refresh failed after {max_retries} attempts: {e}")
                    clear_callback()
                    return False
        
        # Record final failure if we get here
        duration_ms = (time.time() - start_time) * 1000
        if self._metrics:
            self._metrics.record_refresh(False, duration_ms, error_type or "Unknown", max_retries)
        return False
    
    def ensure_valid_session(
        self,
        session: dict,
        refresh_callback
    ) -> bool:
        """
        Ensure the session is valid, refreshing if necessary.
        
        Args:
            session: Current session dictionary
            refresh_callback: Function to refresh token () -> bool
            
        Returns:
            True if session is valid, False otherwise
        """
        if not session:
            return False
        
        expiry_time = session.get('expires_at', 0)
        current_time = time.time()
        
        # Check if token has expired
        if expiry_time < current_time:
            logger.debug("Token has expired, attempting refresh")
            return refresh_callback()
        
        # Proactive refresh: refresh when threshold of token lifetime has passed
        original_lifetime = session.get('original_lifetime')
        if original_lifetime:
            time_until_expiry = expiry_time - current_time
            elapsed_time = original_lifetime - time_until_expiry
            threshold_time = original_lifetime * self.refresh_threshold
            
            # If threshold or more of the lifetime has elapsed, refresh proactively
            if elapsed_time >= threshold_time:
                logger.debug(
                    f"Token approaching expiration "
                    f"({elapsed_time:.0f}s/{original_lifetime}s elapsed, "
                    f"{elapsed_time/original_lifetime*100:.1f}%), refreshing proactively"
                )
                return refresh_callback()
        else:
            # Fallback: if we don't have original_lifetime, refresh if less than 12 minutes remain
            # (assuming typical 1-hour token lifetime, 12 min = 20% remaining)
            time_until_expiry = expiry_time - current_time
            if time_until_expiry < 720:  # Less than 12 minutes
                logger.debug("Token approaching expiration (estimated), refreshing proactively")
                return refresh_callback()
        
        return True
    
    def get_session_time_remaining(self, session: dict) -> int:
        """
        Returns seconds until session expires.
        
        Args:
            session: Current session dictionary
            
        Returns:
            Seconds until expiration, or 0 if no session or expired
        """
        if not session:
            return 0
        
        expiry_time = session.get('expires_at', 0)
        current_time = time.time()
        remaining = max(0, expiry_time - current_time)
        return int(remaining)

