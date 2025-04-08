import os
import time
import secrets
import base64
import math
from collections import Counter
from pathlib import Path
import datetime
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("SecureShare")

def generate_key(password: str, salt: bytes = None) -> (bytes, bytes):
    """Generate an encryption key from a password, optionally with a given salt."""
    if not salt:
        salt = secrets.token_bytes(16)
    logger.debug("Generating encryption key")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return key, salt

def encrypt_file(file_path: str, key: bytes) -> (bytes, bytes):
    """Encrypt file data using AES-GCM with a unique nonce and associated timestamp data."""
    logger.info(f"Encrypting file: {file_path}")
    nonce = secrets.token_bytes(12)  # Recommended 96 bits
    aesgcm = AESGCM(key)
    with open(file_path, 'rb') as f:
        file_data = f.read()
    timestamp = str(int(time.time())).encode()  # Associated data (could be used for replay protection)
    encrypted_data = aesgcm.encrypt(nonce, file_data, timestamp)
    logger.debug(f"Encrypted data size: {len(encrypted_data)} bytes")
    return encrypted_data, nonce

def decrypt_file(encrypted_data: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decrypt file data using AES-GCM."""
    logger.info("Decrypting file data")
    aesgcm = AESGCM(key)
    try:
        decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
        logger.debug(f"Decrypted data size: {len(decrypted_data)} bytes")
        return decrypted_data
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise

def calculate_entropy(data: bytes) -> float:
    """Calculate the Shannon entropy of data."""
    freq = Counter(data)
    entropy = 0
    for count in freq.values():
        prob = count / len(data)
        entropy -= prob * math.log2(prob)
    return entropy
