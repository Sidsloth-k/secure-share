"""Supabase client session management."""
import logging

logger = logging.getLogger("SecureShare")


class ClientManager:
    """Manages Supabase client session configuration."""
    
    def __init__(self, client):
        self.client = client
    
    def set_session(self, access_token: str, refresh_token: str) -> bool:
        """
        Set the session on the Supabase client.
        
        Args:
            access_token: The access token
            refresh_token: The refresh token
            
        Returns:
            True if successful, False otherwise
        """
        if not access_token or not refresh_token:
            logger.warning("Cannot set session: missing tokens")
            return False
        
        try:
            # Validate tokens are not empty strings
            if not isinstance(access_token, str) or not isinstance(refresh_token, str):
                logger.warning("Invalid token types")
                return False
            
            # Check if tokens look valid (basic validation)
            if len(access_token) < 10 or len(refresh_token) < 10:
                logger.warning("Tokens appear to be invalid (too short)")
                return False
            
            self.client.auth.set_session(access_token, refresh_token)
            logger.debug("Session set on Supabase client")
            return True
        except (IndexError, ValueError, AttributeError) as e:
            # Handle cases where tokens are invalid or client setup is incomplete
            logger.warning(f"Failed to set session on client: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error setting session: {e}")
            return False

