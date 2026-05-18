from unittest.mock import patch, MagicMock

import pytest

pytest.importorskip("django")

from arches_id_generator.utils import allocator


def _patched(next_number, created):
    """Mock IdSequence.objects + transaction so allocate() runs without a DB.
    Returns the mock row so the test can assert on next_number/save."""
    row = MagicMock()
    row.next_number = next_number
    qs = MagicMock()
    qs.get_or_create.return_value = (row, created)
    objs = MagicMock()
    objs.select_for_update.return_value = qs
    return row, objs


@pytest.fixture
def patched_row():
    row, objs = _patched(100, created=False)
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


def test_allocate_auto_creates_absent_sequence():
    # get_or_create returns (row, created=True) for a brand-new key; allocate
    # must not raise — the sequence is created lazily on first use.
    row, objs = _patched(1, created=True)
    with patch.object(allocator.IdSequence, "objects", objs), \
         patch.object(allocator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        assert allocator.allocate("brand-new") == 1
    assert row.next_number == 2
    objs.select_for_update.return_value.get_or_create.assert_called_once_with(
        pk="brand-new", defaults={}
    )


def test_allocate_seeds_start_number_on_create():
    # start_number is passed as get_or_create defaults so a brand-new
    # sequence begins there instead of the model default.
    row, objs = _patched(3000, created=True)
    with patch.object(allocator.IdSequence, "objects", objs), \
         patch.object(allocator, "transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        assert allocator.allocate("seeded", start_number=3000) == 3000
    assert row.next_number == 3001
    objs.select_for_update.return_value.get_or_create.assert_called_once_with(
        pk="seeded", defaults={"start_number": 3000, "next_number": 3000}
    )
