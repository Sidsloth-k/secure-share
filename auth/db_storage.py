"""Database session storage for production scalability."""
import json
import logging
import datetime
from typing import Optional, Dict

logger = logging.getLogger("SecureShare")


class DatabaseSessionStorage:
    """Stores sessions in database for production scalability."""
    
    def __init__(self, client):
        """
        Initialize database session storage.
        
        Args:
            client: Supabase client instance
        """
        self.client = client
        self._table_name = "user_sessions"
        logger.debug("Database session storage initialized")
    
    def load_session(self, user_id: Optional[str] = None) -> Dict:
        """
        Load session from database.
        
        Args:
            user_id: Optional user ID to load specific session
            
        Returns:
            Session dictionary or empty dict
        """
        try:
            query = self.client.table(self._table_name).select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            else:
                # Load most recent session
                query = query.order("updated_at", desc=True).limit(1)
            
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                session_data = response.data[0].get("session_data")
                if isinstance(session_data, str):
                    session = json.loads(session_data)
                else:
                    session = session_data
                
                logger.debug("Loaded session from database")
                return session
        except Exception as e:
            logger.warning(f"Failed to load session from database: {e}")
        
        return {}
    
    def save_session(self, session: Dict, encrypt: bool = False) -> None:
        """
        Save session to database.
        
        Args:
            session: Session dictionary to save
            encrypt: Whether session is encrypted (for logging only)
        """
        try:
            user_id = session.get("user_id")
            if not user_id:
                logger.warning("Cannot save session: missing user_id")
                return
            
            expires_at = datetime.datetime.fromtimestamp(
                session.get("expires_at", 0)
            ) if session.get("expires_at") else None
            
            # Prepare session data
            session_data = json.dumps(session)
            
            # Upsert session
            self.client.table(self._table_name).upsert({
                "user_id": user_id,
                "session_data": session_data,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": datetime.datetime.now().isoformat(),
                "encrypted": encrypt
            }, on_conflict="user_id").execute()
            
            logger.debug("Saved session to database")
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
            raise
    
    def clear_session(self, user_id: Optional[str] = None) -> None:
        """
        Clear session from database.
        
        Args:
            user_id: Optional user ID to clear specific session
        """
        try:
            query = self.client.table(self._table_name).delete()
            
            if user_id:
                query = query.eq("user_id", user_id)
            else:
                # Clear all expired sessions
                now = datetime.datetime.now().isoformat()
                query = query.lt("expires_at", now)
            
            query.execute()
            logger.debug("Cleared session(s) from database")
        except Exception as e:
            logger.error(f"Failed to clear session from database: {e}")
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from database.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.datetime.now().isoformat()
            response = self.client.table(self._table_name).delete().lt(
                "expires_at", now
            ).execute()
            
            count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {count} expired sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

