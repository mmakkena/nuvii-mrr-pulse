from cryptography.fernet import Fernet

from app.config import settings


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    if not settings.fernet_key:
        raise ValueError("FERNET_KEY not configured")
    return Fernet(settings.fernet_key.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage."""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_token.encode()).decode()
