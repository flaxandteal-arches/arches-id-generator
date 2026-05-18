from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

pytest.importorskip("django.core.management")

from django.core.management import call_command
from django.core.management.base import CommandError

from arches_id_generator.models import IdSequence


def _row(key="monument-number", start_number=1, next_number=42):
    row = MagicMock()
    row.key = key
    row.start_number = start_number
    row.next_number = next_number
    row.updated_at = MagicMock()
    row.updated_at.isoformat.return_value = "2026-05-08T10:00:00"
    return row


def _patched_get(row=None, missing=False):
    qs = MagicMock()
    if missing:
        qs.get.side_effect = IdSequence.DoesNotExist
    else:
        qs.get.return_value = row
    objs = MagicMock()
    objs.select_for_update.return_value = qs
    return objs


def test_reset_to_one_happy_path():
    row = _row(next_number=42)
    out = StringIO()
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        call_command("reset_id_sequence", "monument-number", stdout=out)

    assert row.next_number == 1
    row.save.assert_called_once_with(update_fields=["next_number", "updated_at"])
    assert "42 -> 1" in out.getvalue()


def test_skip_forward():
    row = _row(next_number=10)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        call_command("reset_id_sequence", "monument-number", "--to", "5000")
    assert row.next_number == 5000


def test_lower_without_force_refused():
    row = _row(next_number=500)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        with pytest.raises(CommandError, match="Refusing to lower"):
            call_command("reset_id_sequence", "monument-number", "--to", "100")
    assert row.next_number == 500
    row.save.assert_not_called()


def test_lower_with_force_allowed():
    row = _row(next_number=500)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        call_command("reset_id_sequence", "monument-number", "--to", "100", "--force")
    assert row.next_number == 100
    row.save.assert_called_once()


def test_unknown_key_raises():
    with patch.object(IdSequence, "objects", _patched_get(missing=True)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        with pytest.raises(CommandError, match="No sequence with key"):
            call_command("reset_id_sequence", "does-not-exist")


def test_missing_key_without_list_raises():
    with pytest.raises(CommandError, match="Missing sequence key"):
        call_command("reset_id_sequence")


def test_list_prints_rows():
    rows = [_row("key-a", 1, 1), _row("key-b", 1, 99)]
    out = StringIO()
    objs = MagicMock()
    objs.order_by.return_value = rows
    objs.order_by.return_value.__bool__ = lambda self: True
    with patch.object(IdSequence, "objects", objs):
        call_command("reset_id_sequence", "--list", stdout=out)
    output = out.getvalue()
    assert "key-a" in output
    assert "next=1" in output
    assert "key-b" in output
    assert "next=99" in output


def test_list_empty():
    out = StringIO()
    objs = MagicMock()
    objs.order_by.return_value = []
    with patch.object(IdSequence, "objects", objs):
        call_command("reset_id_sequence", "--list", stdout=out)
    assert "No sequences found." in out.getvalue()
