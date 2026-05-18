import pytest

from arches_id_generator.utils.validation import validate_key


@pytest.mark.parametrize("good", [
    "a",
    "monument-number",
    "abc-123",
    "k" + "a" * 127,
])
def test_accepts(good):
    validate_key(good)


@pytest.mark.parametrize("bad", [
    "Uppercase",
    "1leading-digit",
    "has space",
    "has_underscore",
    "has.dot",
    "has/slash",
    "",
    None,
    "a" * 129,
])
def test_rejects(bad):
    with pytest.raises(ValueError, match="sequence_key must be"):
        validate_key(bad)
