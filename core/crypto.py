"""Passphrase key-derivation and verification helpers.

Seshat never stores the passphrase. We derive:
  * the SQLCipher key (when the encrypted backend is available), and
  * a separate verifier hash (so the unlock screen can reject a wrong
    passphrase cleanly even on the unencrypted fallback backend).

All cryptography here is local and standard-library based (PBKDF2-HMAC-SHA256).
"""

from __future__ import annotations

import hashlib
import hmac
import os

# PBKDF2 work factor. High enough to be costly to brute force, low enough
# that a single unlock is imperceptible.
_PBKDF2_ROUNDS = 240_000
_SALT_BYTES = 16
_KEY_BYTES = 32


def new_salt() -> str:
    """Return a fresh random salt as a hex string."""
    return os.urandom(_SALT_BYTES).hex()


def _pbkdf2(passphrase: str, salt_hex: str, *, rounds: int = _PBKDF2_ROUNDS) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        bytes.fromhex(salt_hex),
        rounds,
        dklen=_KEY_BYTES,
    )


def derive_verifier(passphrase: str, salt_hex: str) -> str:
    """Hash used to confirm the passphrase matches a stored value."""
    return _pbkdf2(passphrase, salt_hex).hex()


def verify(passphrase: str, salt_hex: str, expected_hex: str) -> bool:
    """Constant-time check of a passphrase against a stored verifier."""
    candidate = derive_verifier(passphrase, salt_hex)
    return hmac.compare_digest(candidate, expected_hex)


def derive_sqlcipher_key(passphrase: str, salt_hex: str) -> str:
    """Derive a raw hex key for SQLCipher's ``PRAGMA key = "x'...'"`` form.

    Using a raw key (rather than handing SQLCipher the passphrase directly)
    keeps the KDF parameters under our control and consistent across files.
    """
    return _pbkdf2(passphrase, salt_hex).hex()
