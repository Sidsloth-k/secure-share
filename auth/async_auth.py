"""Async/await support for authentication."""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("SecureShare")


class AsyncAuth:
    """Async wrapper for authentication operations."""
    
    def __init__(self, client, auth_instance):
        """
        Initialize async auth wrapper.
        
        Args:
            client: Supabase client
            auth_instance: Synchronous Auth instance
        """
        self.client = client
        self._auth = auth_instance
        logger.debug("AsyncAuth wrapper initialized")
    
    async def login(self, email: str, password: str) -> bool:
        """
        Async login.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            True if successful
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth.login, email, password)
    
    async def register(self, email: str, password: str, display_name: str) -> bool:
        """
        Async register.
        
        Args:
            email: User email
            password: User password
            display_name: Display name
            
        Returns:
            True if successful
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._auth.register, email, password, display_name
        )
    
    async def logout(self) -> None:
        """Async logout."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._auth.logout)
    
    async def is_authenticated(self) -> bool:
        """Async authentication check."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth.is_authenticated)
    
    async def refresh_token(self) -> bool:
        """Async token refresh."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth._refresh_token)
    
    async def ensure_authenticated(self) -> bool:
        """Async authentication check."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth.ensure_authenticated)
    
    async def handle_auth_error(self, error: Exception) -> bool:
        """Async error handling."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth.handle_auth_error, error)
    
    async def get_session_time_remaining(self) -> int:
        """Async get session time remaining."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._auth.get_session_time_remaining)
    
    def get_user_id(self) -> Optional[str]:
        """Get user ID (synchronous, no I/O)."""
        return self._auth.get_user_id()
    
    def get_access_token(self) -> Optional[str]:
        """Get access token (synchronous, no I/O)."""
        return self._auth.get_access_token()

