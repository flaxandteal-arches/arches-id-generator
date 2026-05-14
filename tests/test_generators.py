import re
import pytest

from arches_id_generator import generators


def test_uuid4_shape():
    value = generators.generate_uuid4()
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        value,
    )


def test_uuid7_returns_string():
    assert isinstance(generators.generate_uuid7(), str)


def test_random_int_length():
    for _ in range(20):
        n = generators.generate_random_int(5)
        assert 10000 <= n <= 99999


def test_random_int_length_one_allows_zero():
    values = {generators.generate_random_int(1) for _ in range(100)}
    assert values <= set(range(10))


def test_random_int_rejects_zero_length():
    with pytest.raises(ValueError):
        generators.generate_random_int(0)


def test_random_string_length_and_alphabet():
    s = generators.generate_random_string(20)
    assert len(s) == 20
    assert set(s) <= set(generators.UNAMBIGUOUS_ALPHANUMERIC)


def test_random_string_excludes_ambiguous():
    seen = set()
    for _ in range(200):
        seen.update(generators.generate_random_string(20))
    assert seen.isdisjoint({"0", "O", "1", "I", "L"})


def test_random_string_rejects_zero_length():
    with pytest.raises(ValueError):
        generators.generate_random_string(0)


def test_random_string_rejects_empty_alphabet():
    with pytest.raises(ValueError):
        generators.generate_random_string(5, alphabet="")
