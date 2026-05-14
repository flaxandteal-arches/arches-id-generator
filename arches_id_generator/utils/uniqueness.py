"""Retry-on-collision wrapper for non-deterministic generators."""

from typing import Callable


class CollisionError(RuntimeError):
    """Raised when generate_unique exhausts its retries."""


def generate_unique(
    generator_fn: Callable[[], str],
    exists_check_fn: Callable[[str], bool],
    max_retries: int = 10,
) -> str:
    """Call generator_fn until exists_check_fn returns False, or raise."""
    for _ in range(max_retries):
        candidate = generator_fn()
        if not exists_check_fn(candidate):
            return candidate

    raise CollisionError(f"generate_unique exhausted {max_retries} retries")
