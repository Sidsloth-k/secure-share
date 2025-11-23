"""Authentication error handling."""
import logging

logger = logging.getLogger("SecureShare")


class AuthErrorHandler:
    """Handles authentication errors from API calls."""
    
    def __init__(self, refresh_callback):
        """
        Initialize error handler.
        
        Args:
            refresh_callback: Function to refresh token () -> bool
        """
        self.refresh_callback = refresh_callback
    
    def handle_auth_error(self, error: Exception) -> bool:
        """
        Handle authentication errors from API calls.
        Attempts to refresh token if error is auth-related.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if error was handled (token refreshed), False otherwise
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check for authentication/authorization errors
        auth_keywords = [
            '401', 'unauthorized', 'forbidden', '403', 
            'expired', 'invalid token', 'authentication',
            'jwt', 'token', 'signature'
        ]
        
        is_auth_error = (
            any(keyword in error_str for keyword in auth_keywords) or 
            'auth' in error_type
        )
        
        if is_auth_error:
            logger.debug(f"Authentication error detected: {error}, attempting token refresh")
            if self.refresh_callback():
                logger.info("Token refreshed successfully after auth error")
                return True
            else:
                logger.warning("Token refresh failed after auth error")
                return False
        
        return False

