"""Session storage management with file-based (dev) and database (prod) support."""
import os
import json
import logging

logger = logging.getLogger("SecureShare")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".secure_share")
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")
ENCRYPTED_SESSION_FILE = os.path.join(CONFIG_DIR, "session.enc")

# Global encryption instance (optional)
_encryption = None
# Global database storage instance (optional, for production)
_db_storage = None


def set_encryption(encryption_instance):
    """Set encryption instance for session storage."""
    global _encryption
    _encryption = encryption_instance


def set_db_storage(db_storage_instance):
    """Set database storage instance for production."""
    global _db_storage
    _db_storage = db_storage_instance


def load_session(user_id: str = None) -> dict:
    """
    Load the user session from database (production) or file (development).
    
    Args:
        user_id: Optional user ID for database lookup
        
    Returns:
        Session dictionary or empty dict
    """
    # Use database storage if available (production mode)
    if _db_storage:
        return _db_storage.load_session(user_id)
    
    # File-based storage (development mode)
    # Try encrypted first, then plain
    if os.path.exists(ENCRYPTED_SESSION_FILE):
        try:
            if _encryption:
                with open(ENCRYPTED_SESSION_FILE, 'r') as f:
                    encrypted_data = f.read()
                    session = _encryption.decrypt_session(encrypted_data)
                    logger.debug("Loaded encrypted session from file")
                    return session
            else:
                logger.warning("Encrypted session file exists but no encryption instance set")
        except Exception as e:
            logger.warning(f"Failed to load encrypted session: {e}")
    
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session = json.load(f)
                logger.debug("Loaded session from file")
                return session
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
    return {}


def save_session(session: dict, encrypt: bool = False) -> None:
    """
    Save user session to database (production) or file (development).
    
    Args:
        session: Session dictionary to save
        encrypt: Whether to encrypt the session
    """
    # Use database storage if available (production mode)
    if _db_storage:
        try:
            _db_storage.save_session(session, encrypt=encrypt)
            return
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
            raise
    
    # File-based storage (development mode)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        if encrypt and _encryption:
            # Save encrypted
            encrypted_data = _encryption.encrypt_session(session)
            with open(ENCRYPTED_SESSION_FILE, 'w') as f:
                f.write(encrypted_data)
            # Remove plain file if exists
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            logger.debug("Saved encrypted session to file")
        else:
            # Save plain
            with open(SESSION_FILE, 'w') as f:
                json.dump(session, f)
            # Remove encrypted file if exists
            if os.path.exists(ENCRYPTED_SESSION_FILE):
                os.remove(ENCRYPTED_SESSION_FILE)
            logger.debug("Saved session to file")
    except Exception as e:
        logger.error(f"Failed to save session: {e}")


def clear_session(user_id: str = None) -> None:
    """
    Clear user session from database (production) or file (development).
    
    Args:
        user_id: Optional user ID for database cleanup
    """
    # Use database storage if available (production mode)
    if _db_storage:
        try:
            _db_storage.clear_session(user_id)
            return
        except Exception as e:
            logger.error(f"Failed to clear session from database: {e}")
            return
    
    # File-based storage (development mode)
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        if os.path.exists(ENCRYPTED_SESSION_FILE):
            os.remove(ENCRYPTED_SESSION_FILE)
        logger.debug("Cleared session")
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")

