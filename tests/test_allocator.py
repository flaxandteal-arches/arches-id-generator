from unittest.mock import patch, MagicMock

import pytest

pytest.importorskip("django")

from arches_id_generator.utils import allocator


@pytest.fixture
def patched_row():
    row = MagicMock()
    row.next_number = 100
    qs = MagicMock()
    qs.get.return_value = row
    objs = MagicMock()
    objs.select_for_update.return_value = qs
    with patch.object(allocator.IdSequence, "objects", objs), \
         patch.object(allocator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        yield row


def test_allocate_returns_and_increments(patched_row):
    assert allocator.allocate("k") == 100
    assert patched_row.next_number == 101
    patched_row.save.assert_called_once_with(
        update_fields=["next_number", "updated_at"]
    )


def test_allocate_batch(patched_row):
    assert allocator.allocate("k", count=10) == 100
    assert patched_row.next_number == 110


def test_allocate_or_create_uses_get_or_create():
    row = MagicMock()
    row.next_number = 1
    qs = MagicMock()
    qs.get_or_create.return_value = (row, True)
    objs = MagicMock()
    objs.select_for_update.return_value = qs

    with patch.object(allocator.IdSequence, "objects", objs), \
         patch.object(allocator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        assert allocator.allocate_or_create("brand-new") == 1
    assert row.next_number == 2
