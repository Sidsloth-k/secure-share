"""Session encryption for secure storage."""
import os
import json
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("SecureShare")


class SessionEncryption:
    """Encrypts and decrypts session data."""
    
    def __init__(self, key: bytes = None):
        """
        Initialize encryption with optional key.
        
        Args:
            key: Encryption key (32 bytes). If None, generates from OS keyring or password.
        """
        if key is None:
            key = self._get_or_create_key()
        
        self.cipher = Fernet(key)
        logger.debug("Session encryption initialized")
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from OS keyring or generate new one."""
        # First try environment variable
        key_env = os.getenv("SESSION_ENCRYPTION_KEY")
        if key_env:
            try:
                # Try to decode as base64
                key_bytes = base64.urlsafe_b64decode(key_env.encode())
                if len(key_bytes) == 32:
                    return key_bytes
                else:
                    logger.warning(f"Invalid key length from env: {len(key_bytes)}, expected 32")
            except Exception as e:
                logger.warning(f"Failed to decode key from env: {e}")
        
        # Try OS keyring
        try:
            import keyring
            key_str = keyring.get_password("secure_share", "session_key")
            
            if key_str:
                try:
                    key_bytes = base64.urlsafe_b64decode(key_str.encode())
                    if len(key_bytes) == 32:
                        return key_bytes
                except Exception as e:
                    logger.warning(f"Failed to decode key from keyring: {e}")
            
            # Generate new key and store in keyring
            key = Fernet.generate_key()
            try:
                keyring.set_password("secure_share", "session_key", base64.urlsafe_b64encode(key).decode())
            except Exception as e:
                logger.warning(f"Failed to save key to keyring: {e}")
            return key
        except ImportError:
            logger.debug("keyring not available")
        
        # Last resort: generate from machine-specific data
        logger.warning("keyring not available, using machine-specific key (less secure)")
        try:
            machine_id = os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "default"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'secure_share_salt',
                iterations=100000,
            )
            # Derive raw bytes and encode to Fernet-compatible format
            raw_key = kdf.derive(machine_id.encode())
            key = base64.urlsafe_b64encode(raw_key)
            return key
        except Exception as e:
            logger.error(f"Failed to generate machine-specific key: {e}")
            # Ultimate fallback: generate random key (won't persist across restarts)
            logger.warning("Using temporary random key (will not persist)")
            return Fernet.generate_key()
    
    def encrypt_session(self, session: dict) -> str:
        """
        Encrypt session data.
        
        Args:
            session: Session dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            session_json = json.dumps(session)
            encrypted = self.cipher.encrypt(session_json.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt session: {e}")
            raise
    
    def decrypt_session(self, encrypted_data: str) -> dict:
        """
        Decrypt session data.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted session dictionary
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt session: {e}")
            raise

