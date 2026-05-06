import pytest

from arches_id_generator.services.formats import render_format


def test_attribute_access_rejected():
    with pytest.raises(ValueError, match="Attribute/index access not allowed"):
        render_format("{seq.__class__}", 1)


def test_index_access_rejected():
    with pytest.raises(ValueError, match="Attribute/index access not allowed"):
        render_format("{seq[0]}", 1)


def test_repr_conversion_rejected():
    with pytest.raises(ValueError, match="Conversion '!r' not allowed"):
        render_format("{seq!r}", 1)


def test_str_conversion_rejected():
    with pytest.raises(ValueError, match="Conversion '!s' not allowed"):
        render_format("{seq!s}", 1)


def test_unknown_token_rejected_at_validation():
    with pytest.raises(ValueError, match="Unknown token"):
        render_format("{evil}", 1)


def test_empty_template():
    assert render_format("", 1) == ""


def test_literal_only_template():
    assert render_format("static-id", 5) == "static-id"


def test_mixed_literal_and_token():
    assert render_format("foo-{seq:02}-bar", 7) == "foo-07-bar"
