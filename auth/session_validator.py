"""Session validation and authentication checking."""
import logging

logger = logging.getLogger("SecureShare")


class SessionValidator:
    """Validates session tokens and authentication status."""
    
    def __init__(self, client):
        self.client = client
    
    def is_authenticated(
        self,
        session: dict,
        ensure_valid_callback,
        refresh_callback
    ) -> bool:
        """
        Check if user is authenticated, refreshing token if needed.
        
        Args:
            session: Current session dictionary
            ensure_valid_callback: Function to ensure valid session () -> bool
            refresh_callback: Function to refresh token () -> bool
            
        Returns:
            True if authenticated, False otherwise
        """
        if not session:
            return False
        
        # Ensure session is valid (refresh if needed)
        if not ensure_valid_callback():
            return False
        
        try:
            # Verify the token is still valid by getting user info
            access_token = session.get('access_token', '')
            if not access_token:
                return False
            
            user = self.client.auth.get_user(access_token)
            logger.debug("Session is valid")
            return True
        except Exception as e:
            # If get_user fails, try refreshing the token
            error_str = str(e).lower()
            auth_keywords = ['401', 'unauthorized', 'expired', 'invalid', '403', 'forbidden']
            
            if any(keyword in error_str for keyword in auth_keywords):
                logger.debug("Token validation failed, attempting refresh")
                if refresh_callback():
                    # Retry after refresh
                    try:
                        access_token = session.get('access_token', '')
                        if access_token:
                            user = self.client.auth.get_user(access_token)
                            logger.debug("Session verified after refresh")
                            return True
                    except Exception as retry_error:
                        logger.warning(f"Session verification failed after refresh: {retry_error}")
                        return False
            
            logger.warning(f"Session verification failed: {e}")
            return False

