import pytest

from arches_id_generator.utils.uniqueness import generate_unique, CollisionError


def test_returns_first_unique():
    candidates = iter(["a", "b", "c"])
    seen = {"a", "b"}
    assert generate_unique(lambda: next(candidates), lambda v: v in seen) == "c"


def test_raises_on_exhaustion():
    with pytest.raises(CollisionError):
        generate_unique(lambda: "x", lambda v: True, max_retries=3)


def test_first_try_wins():
    calls = []
    def gen():
        calls.append(1)
        return "x"
    generate_unique(gen, lambda v: False)
    assert len(calls) == 1
