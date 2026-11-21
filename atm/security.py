"""Password hashing, constant-time verification, and PIN input utilities."""
import getpass
import hashlib
import hmac
import os

ITERATIONS = 210_000


def hash_pin(pin: str) -> str:
    if not (pin.isascii() and pin.isdigit() and 4 <= len(pin) <= 8):
        raise ValueError('PIN must contain 4-8 ASCII digits')
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_pin(pin: str, encoded: str) -> bool:
    try:
        scheme, count, salt_hex, digest_hex = encoded.split('$')
        if scheme != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(salt_hex), int(count))
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def read_pin(prompt: str) -> str:
    return getpass.getpass(prompt + ' ')
