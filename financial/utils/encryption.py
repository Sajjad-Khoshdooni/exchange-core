from cryptography.fernet import Fernet
from decouple import config

# to generate new encryption_key run Fernet.generate_key().decode()
ENCRYPTION_KEY = config('ENCRYPTION_KEY')


def encrypt(text: str) -> str:
    fernet = Fernet(ENCRYPTION_KEY.encode())
    return fernet.encrypt(text.encode()).decode()


def decrypt(encrypted: str) -> str:
    fernet = Fernet(ENCRYPTION_KEY.encode())
    return fernet.decrypt(encrypted.encode()).decode()
