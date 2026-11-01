"""Symmetric encryption for sensitive data (e.g. BYO provider API keys).

Implements AES-128-CBC / HMAC-SHA256 authenticated encryption using Fernet,
supporting zero-downtime key rotation via primary and secondary (old) keys.
"""
from typing import Optional, Tuple
import logging
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger("praxis.crypto")


class CryptoError(Exception):
    """Base exception for cryptographic operations."""


class MissingKeyError(CryptoError):
    """Raised when an operation requires an encryption key that is missing or not configured."""


class DecryptionError(CryptoError):
    """Raised when ciphertext cannot be decrypted or authentication tag verification fails."""


def generate_fernet_key() -> str:
    """Generate a fresh URL-safe base64-encoded 32-byte key."""
    return Fernet.generate_key().decode("utf-8")


class FernetManager:
    """Manages symmetric encryption, decryption, and key rotation."""

    def __init__(self, primary_key: Optional[str] = None, old_key: Optional[str] = None):
        self._primary_key = (primary_key or "").strip()
        self._old_key = (old_key or "").strip()
        self._fernet_primary: Optional[Fernet] = None
        self._multi_fernet: Optional[MultiFernet] = None

        fernets = []
        if self._primary_key:
            try:
                self._fernet_primary = Fernet(self._primary_key.encode("utf-8"))
                fernets.append(self._fernet_primary)
            except Exception as e:
                raise CryptoError(f"Invalid primary FERNET_KEY: {e}") from e

        if self._old_key:
            try:
                fernets.append(Fernet(self._old_key.encode("utf-8")))
            except Exception as e:
                raise CryptoError(f"Invalid FERNET_KEY_OLD: {e}") from e

        if fernets:
            self._multi_fernet = MultiFernet(fernets)

    @property
    def is_configured(self) -> bool:
        return self._fernet_primary is not None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string using the primary key."""
        if not self._fernet_primary:
            raise MissingKeyError("Cannot encrypt: FERNET_KEY is not configured.")
        if not isinstance(plaintext, str):
            raise ValueError("Plaintext must be a string.")
        
        token = self._fernet_primary.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext using MultiFernet (trying primary then old key)."""
        if not self._multi_fernet:
            raise MissingKeyError("Cannot decrypt: no Fernet keys are configured.")
        if not isinstance(ciphertext, str) or not ciphertext.strip():
            raise ValueError("Ciphertext must be a non-empty string.")

        try:
            decrypted_bytes = self._multi_fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken as e:
            raise DecryptionError("Decryption failed: corrupted ciphertext or key mismatch.") from e
        except Exception as e:
            raise DecryptionError(f"Decryption error: {e}") from e

    def rotate(self, ciphertext: str) -> Tuple[str, bool]:
        """Re-encrypt ciphertext with the primary key if it was encrypted with an older key.

        Returns:
            Tuple[str, bool]: (new_or_same_ciphertext, was_rotated)
        """
        if not self._multi_fernet or not self._fernet_primary:
            raise MissingKeyError("Cannot rotate: FERNET_KEY is not configured.")

        try:
            # MultiFernet.rotate re-encrypts the token with the first Fernet in the list.
            rotated_bytes = self._multi_fernet.rotate(ciphertext.encode("utf-8"))
            rotated_str = rotated_bytes.decode("utf-8")
            was_rotated = rotated_str != ciphertext
            return rotated_str, was_rotated
        except InvalidToken as e:
            raise DecryptionError("Rotation failed: token could not be decrypted by any known key.") from e


_cached_manager: Optional[FernetManager] = None


def get_fernet_manager() -> FernetManager:
    """Retrieve or initialize the singleton FernetManager from application settings."""
    global _cached_manager
    if _cached_manager is None:
        from packages.config.settings import settings
        _cached_manager = FernetManager(
            primary_key=settings.FERNET_KEY,
            old_key=settings.FERNET_KEY_OLD,
        )
    return _cached_manager
