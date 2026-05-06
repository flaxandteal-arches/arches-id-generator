"""
Unit tests for the reset_id_sequence management command.

Skipped if Django isn't actually installed/usable. Uses call_command with
IdSequence.objects mocked so no DB is needed.
"""
from io import StringIO
from unittest.mock import patch, MagicMock
import pytest

pytest.importorskip("django.core.management")

from django.core.management import call_command
from django.core.management.base import CommandError

from arches_id_generator.models import IdSequence


def _row(key="monument-number", last_issued=42):
    row = MagicMock()
    row.key = key
    row.last_issued = last_issued
    row.updated_at = MagicMock()
    row.updated_at.isoformat.return_value = "2026-05-06T10:00:00"
    return row


def _patched_get(row=None, missing=False):
    """Return a context-manager patch that wires up select_for_update().get()."""
    qs = MagicMock()
    if missing:
        qs.get.side_effect = IdSequence.DoesNotExist
    else:
        qs.get.return_value = row
    objs = MagicMock()
    objs.select_for_update.return_value = qs
    return objs


def test_reset_to_zero_happy_path():
    row = _row(last_issued=42)
    out = StringIO()

    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False

        call_command("reset_id_sequence", "monument-number", stdout=out)

    assert row.last_issued == 0
    row.save.assert_called_once_with(update_fields=["last_issued", "updated_at"])
    assert "42 -> 0" in out.getvalue()
    assert "next ID will be 1" in out.getvalue()


def test_skip_forward():
    row = _row(last_issued=10)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        call_command("reset_id_sequence", "monument-number", "--to", "5000")

    assert row.last_issued == 5000


def test_lower_without_force_refused():
    row = _row(last_issued=500)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False

        with pytest.raises(CommandError, match="Refusing to lower"):
            call_command("reset_id_sequence", "monument-number", "--to", "100")

    assert row.last_issued == 500
    row.save.assert_not_called()


def test_lower_with_force_allowed():
    row = _row(last_issued=500)
    with patch.object(IdSequence, "objects", _patched_get(row)), \
         patch("arches_id_generator.management.commands.reset_id_sequence.transaction") as tx:
        tx.atomic.return_value.__enter__.return_value = None
        tx.atomic.return_value.__exit__.return_value = False
        call_command("reset_id_sequence", "monument-number", "--to", "100", "--force")

    assert row.last_issued == 100
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
    rows = [_row("key-a", 1), _row("key-b", 99)]
    out = StringIO()

    objs = MagicMock()
    objs.order_by.return_value = rows
    # Make truthiness work for `if not rows:` against the manager-style mock.
    objs.order_by.return_value.__bool__ = lambda self: True

    with patch.object(IdSequence, "objects", objs):
        call_command("reset_id_sequence", "--list", stdout=out)

    output = out.getvalue()
    assert "key-a" in output
    assert "last_issued=1" in output
    assert "key-b" in output
    assert "last_issued=99" in output


def test_list_empty():
    out = StringIO()
    objs = MagicMock()
    objs.order_by.return_value = []
    with patch.object(IdSequence, "objects", objs):
        call_command("reset_id_sequence", "--list", stdout=out)

    assert "No sequences found." in out.getvalue()
