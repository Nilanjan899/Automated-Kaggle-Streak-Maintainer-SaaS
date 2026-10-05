from cryptography.fernet import Fernet

def encrypt_key(plain_key: str, master_key: str) -> str:
    """Encrypts a user's API key before saving to Firebase."""
    f = Fernet(master_key.encode('utf-8'))
    return f.encrypt(plain_key.encode('utf-8')).decode('utf-8')

def decrypt_key(encrypted_key: str, master_key: str) -> str:
    """Decrypts a user's API key in memory just before making the Gemini call."""
    f = Fernet(master_key.encode('utf-8'))
    return f.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')