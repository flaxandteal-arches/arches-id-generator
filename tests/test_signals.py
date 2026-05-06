"""
Unit tests for the assign_id_to_tile pre_save signal.

CardXNodeXWidget queries and the generator are mocked so no DB is needed.
A SimpleNamespace stands in for the Tile instance — the signal only reads
.nodegroup_id and .data on it.
"""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from uuid import UUID, uuid4
import pytest

pytest.importorskip("django")

from arches_id_generator import signals


def _entry(node_id, sequence_key="key-a", template="{seq:03}"):
    e = MagicMock()
    e.node_id = node_id
    e.config = {"sequence_key": sequence_key, "template": template}
    return e


@pytest.fixture
def fake_tile():
    return SimpleNamespace(nodegroup_id=uuid4(), data={})


def test_empty_node_gets_id_in_i18n_shape(fake_tile):
    node_id = uuid4()
    entries = [_entry(node_id)]

    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id", return_value="042") as gen:
        objs.filter.return_value = entries
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    gen.assert_called_once_with("key-a", "{seq:03}")
    assert fake_tile.data[str(node_id)] == {"en": {"value": "042", "direction": "ltr"}}


def test_existing_value_is_not_overwritten(fake_tile):
    node_id = uuid4()
    fake_tile.data[str(node_id)] = {"en": {"value": "ABC-001", "direction": "ltr"}}
    entries = [_entry(node_id)]

    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id") as gen:
        objs.filter.return_value = entries
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    gen.assert_not_called()
    assert fake_tile.data[str(node_id)] == {"en": {"value": "ABC-001", "direction": "ltr"}}


def test_node_id_is_stored_as_string_not_uuid(fake_tile):
    node_id = uuid4()
    entries = [_entry(node_id)]

    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id", return_value="X"):
        objs.filter.return_value = entries
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    keys = list(fake_tile.data.keys())
    assert all(isinstance(k, str) for k in keys), "Tile.data keys must be str (JSON requirement)"
    assert not any(isinstance(k, UUID) for k in keys)


def test_missing_sequence_key_skipped(fake_tile):
    node_id = uuid4()
    entry = MagicMock()
    entry.node_id = node_id
    entry.config = {"sequence_key": "", "template": "{seq}"}

    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id") as gen:
        objs.filter.return_value = [entry]
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    gen.assert_not_called()
    assert fake_tile.data == {}


def test_missing_template_skipped(fake_tile):
    node_id = uuid4()
    entry = MagicMock()
    entry.node_id = node_id
    entry.config = {"sequence_key": "key-a", "template": ""}

    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id") as gen:
        objs.filter.return_value = [entry]
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    gen.assert_not_called()


def test_multiple_nodes_get_separate_ids(fake_tile):
    node_a, node_b = uuid4(), uuid4()
    entries = [_entry(node_a, "k1", "A-{seq}"), _entry(node_b, "k2", "B-{seq}")]

    issued = iter(["1", "1"])
    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id", side_effect=lambda k, t: next(issued)):
        objs.filter.return_value = entries
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    assert fake_tile.data[str(node_a)]["en"]["value"] == "1"
    assert fake_tile.data[str(node_b)]["en"]["value"] == "1"


def test_no_generator_widgets_in_nodegroup_is_noop(fake_tile):
    with patch.object(signals.CardXNodeXWidget, "objects") as objs, \
         patch.object(signals, "generate_id") as gen:
        objs.filter.return_value = []
        signals.assign_id_to_tile(sender=None, instance=fake_tile)

    gen.assert_not_called()
    assert fake_tile.data == {}
