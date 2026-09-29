"""AES-256-GCM envelope encryption for third-party tokens (NFR-SEC-01, Tech Bible 9.1).

A random 256-bit data key encrypts the token; the data key is wrapped with the key-encryption
key (KEK) from TOKEN_KEK_B64 (a local stand-in for a cloud KMS). Output is a compact string:
``v1.<kek_id>.<b64 wrapped_key>.<b64 nonce>.<b64 ciphertext>``.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VERSION = "v1"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class TokenCipher:
    def __init__(self, kek: bytes, kek_id: str) -> None:
        if len(kek) != 32:
            raise ValueError("KEK must be 32 bytes")
        if "." in kek_id:
            raise ValueError("kek_id must not contain '.'")
        self._kek = AESGCM(kek)
        self.kek_id = kek_id

    @classmethod
    def from_env(cls) -> "TokenCipher":
        kek = base64.b64decode(os.environ["TOKEN_KEK_B64"])
        return cls(kek, os.environ.get("TOKEN_KEK_ID", "local-1"))

    def encrypt(self, plaintext: str, aad: str = "") -> str:
        data_key = AESGCM.generate_key(bit_length=256)
        wrap_nonce = os.urandom(12)
        wrapped = wrap_nonce + self._kek.encrypt(wrap_nonce, data_key, self.kek_id.encode())
        nonce = os.urandom(12)
        ct = AESGCM(data_key).encrypt(nonce, plaintext.encode(), aad.encode())
        return ".".join([_VERSION, self.kek_id, _b64e(wrapped), _b64e(nonce), _b64e(ct)])

    def decrypt(self, token: str, aad: str = "") -> str:
        version, kek_id, wrapped_s, nonce_s, ct_s = token.split(".")
        if version != _VERSION or kek_id != self.kek_id:
            raise ValueError("unknown token envelope version or key id")
        wrapped = _b64d(wrapped_s)
        data_key = self._kek.decrypt(wrapped[:12], wrapped[12:], kek_id.encode())
        return AESGCM(data_key).decrypt(_b64d(nonce_s), _b64d(ct_s), aad.encode()).decode()
