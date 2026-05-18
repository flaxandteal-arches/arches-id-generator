import re

_VALID_KEY = re.compile(r"^[a-z][a-z0-9-]{0,127}$")


def validate_key(key):
    """Lowercase slug, starts with a letter, max 128 chars."""
    if not _VALID_KEY.fullmatch(key or ""):
        raise ValueError(
            "sequence_key must be lowercase letters/digits/hyphens, "
            "start with a letter, max 128 chars"
        )
