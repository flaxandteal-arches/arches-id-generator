"""
Unit tests for generate_id with the database mocked.

Verifies the lock-and-increment logic, key validation, and that
the rendered template is returned. Does not exercise concurrency
(that needs a real DB and isn't worth setting up here).
"""
from unittest.mock import patch, MagicMock
import pytest

pytest.importorskip("django")

from arches_id_generator.services import generator


@pytest.fixture
def mock_sequence_row():
    row = MagicMock()
    row.last_issued = 41
    return row


@pytest.fixture
def patched_objects(mock_sequence_row):
    with patch.object(generator.IdSequence, "objects") as objs:
        objs.select_for_update.return_value.get_or_create.return_value = (mock_sequence_row, False)
        yield objs, mock_sequence_row


def test_generate_id_increments_and_renders(patched_objects):
    _, row = patched_objects
    with patch.object(generator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False

        result = generator.generate_id("monument-number", "{seq:05}")

    assert row.last_issued == 42
    row.save.assert_called_once_with(update_fields=["last_issued", "updated_at"])
    assert result == "00042"


def test_generate_id_brand_new_key(patched_objects):
    objs, row = patched_objects
    row.last_issued = 0
    objs.select_for_update.return_value.get_or_create.return_value = (row, True)

    with patch.object(generator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        result = generator.generate_id("brand-new", "{seq}")

    assert row.last_issued == 1
    assert result == "1"


@pytest.mark.parametrize("bad_key", [
    "Uppercase",
    "1leading-digit",
    "has space",
    "has_underscore",
    "has.dot",
    "has/slash",
    "",
    "a" * 129,  # too long
])
def test_generate_id_rejects_bad_keys(bad_key):
    with pytest.raises(ValueError, match="sequence_key must be"):
        generator.generate_id(bad_key, "{seq}")


@pytest.mark.parametrize("good_key", [
    "a",
    "monument-number",
    "abc-123",
    "k" + "a" * 127,  # exactly 128 chars
])
def test_generate_id_accepts_good_keys(good_key, patched_objects):
    with patch.object(generator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        # If validation passes, no ValueError should escape.
        generator.generate_id(good_key, "{seq}")
