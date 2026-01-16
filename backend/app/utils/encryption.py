"""Token encryption utilities using Fernet."""

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()

# Initialize Fernet with encryption key
fernet = Fernet(settings.encryption_key.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a token string."""
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string."""
    return fernet.decrypt(encrypted_token.encode()).decode()
