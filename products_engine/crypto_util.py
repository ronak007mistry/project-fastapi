import base64
import json
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_salt = b"testing_salt_for_encryption"


def _fernet() -> Fernet:
    secret = os.getenv("AES_SECRET", "dev-only-change-in-production-secret-key!!")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))
    return Fernet(key)


def encrypt_payload(data: Any) -> dict[str, str]:
    raw = json.dumps(data, default=str).encode("utf-8")
    token = _fernet().encrypt(raw)
    return {
        "algorithm": "fernet-aes",
        "ciphertext": token.decode("ascii"),
    }
