"""Stateless ID generators backed by `secrets`. No DB, no uniqueness checks."""

import secrets
import uuid

try:
    from uuid_extensions import uuid7  # type: ignore
except ImportError:
    uuid7 = None


UNAMBIGUOUS_DIGITS = "23456789"
UNAMBIGUOUS_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
UNAMBIGUOUS_ALPHANUMERIC = UNAMBIGUOUS_DIGITS + UNAMBIGUOUS_LETTERS


def generate_uuid4() -> str:
    return str(uuid.uuid4())


def generate_uuid7() -> str:
    """Time-ordered UUID; falls back to uuid4 if uuid_extensions isn't installed."""
    if uuid7 is None:
        return generate_uuid4()
    return str(uuid7())


def generate_random_int(length: int) -> int:
    """Random integer with exactly `length` digits (no leading zeros)."""
    if length < 1:
        raise ValueError("length must be >= 1")
    lower = 10 ** (length - 1) if length > 1 else 0
    upper = 10**length
    return lower + secrets.randbelow(upper - lower)


def generate_random_string(length: int, alphabet: str = UNAMBIGUOUS_ALPHANUMERIC) -> str:
    """Random string from `alphabet`; default excludes 0, O, 1, I, L."""
    if length < 1:
        raise ValueError("length must be >= 1")
    if not alphabet:
        raise ValueError("alphabet must be non-empty")
    return "".join(secrets.choice(alphabet) for _ in range(length))
