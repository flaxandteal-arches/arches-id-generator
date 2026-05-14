from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest

pytest.importorskip("django")

from arches_id_generator.functions import id_generator_function as fn


def _binding(node_id, **config_overrides):
    config = {
        "sequence_key": "key-a",
        "template": "{seq:03}",
        "generate_on": "tile_save",
    }
    config.update(config_overrides)
    entry = MagicMock()
    entry.node_id = node_id
    entry.config = config
    return entry


@pytest.fixture
def tile():
    return SimpleNamespace(nodegroup_id=uuid4(), data={})


def test_save_stamps_tile_save_binding(tile):
    node_id = uuid4()
    with patch.object(fn, "_bindings_for_nodegroup", return_value=[_binding(node_id)]), \
         patch.object(fn, "generate_id", return_value="042"):
        fn.IdGeneratorFunction().save(tile, request=None)
    assert tile.data[str(node_id)]["en"]["value"] == "042"


def test_save_skips_resource_activation_binding(tile):
    node_id = uuid4()
    with patch.object(fn, "_bindings_for_nodegroup",
                      return_value=[_binding(node_id, generate_on="resource_activation")]), \
         patch.object(fn, "generate_id") as g:
        fn.IdGeneratorFunction().save(tile, request=None)
    g.assert_not_called()
    assert tile.data == {}


def test_save_skips_existing_value(tile):
    node_id = uuid4()
    tile.data[str(node_id)] = {"en": {"value": "USER-TYPED", "direction": "ltr"}}
    with patch.object(fn, "_bindings_for_nodegroup", return_value=[_binding(node_id)]), \
         patch.object(fn, "generate_id") as g:
        fn.IdGeneratorFunction().save(tile, request=None)
    g.assert_not_called()
    assert tile.data[str(node_id)]["en"]["value"] == "USER-TYPED"


def test_save_skips_missing_config(tile):
    node_id = uuid4()
    with patch.object(fn, "_bindings_for_nodegroup",
                      return_value=[_binding(node_id, sequence_key="")]), \
         patch.object(fn, "generate_id") as g:
        fn.IdGeneratorFunction().save(tile, request=None)
    g.assert_not_called()


def test_on_update_lifecycle_skips_when_not_activation():
    resource = SimpleNamespace(pk=uuid4(), graph_id=uuid4())
    new_state = SimpleNamespace(name="draft")
    with patch.object(fn, "_bindings_for_graph") as bindings:
        fn.IdGeneratorFunction().on_update_lifecycle_state(
            resource, current_state=None, new_state=new_state
        )
    bindings.assert_not_called()


def test_on_update_lifecycle_stamps_activation_bindings():
    node_id = uuid4()
    resource = SimpleNamespace(pk=uuid4(), graph_id=uuid4())
    new_state = SimpleNamespace(name="active")

    tile = SimpleNamespace(data={}, save=MagicMock())
    binding = _binding(node_id, generate_on="resource_activation")
    binding.node.nodegroup_id = uuid4()

    tiles_qs = MagicMock()
    tiles_qs.__iter__ = lambda self: iter([tile])

    with patch.object(fn, "_bindings_for_graph", return_value=[binding]), \
         patch.object(fn.Tile, "objects") as tile_objs, \
         patch.object(fn, "generate_id", return_value="001"):
        tile_objs.filter.return_value = tiles_qs
        fn.IdGeneratorFunction().on_update_lifecycle_state(
            resource, current_state=None, new_state=new_state
        )

    assert tile.data[str(node_id)]["en"]["value"] == "001"
    tile.save.assert_called_once()


def test_on_update_lifecycle_respects_user_typed_value():
    node_id = uuid4()
    resource = SimpleNamespace(pk=uuid4(), graph_id=uuid4())
    new_state = SimpleNamespace(name="active")

    tile = SimpleNamespace(
        data={str(node_id): {"en": {"value": "MANUAL", "direction": "ltr"}}},
        save=MagicMock(),
    )
    binding = _binding(node_id, generate_on="resource_activation")
    binding.node.nodegroup_id = uuid4()

    tiles_qs = MagicMock()
    tiles_qs.__iter__ = lambda self: iter([tile])

    with patch.object(fn, "_bindings_for_graph", return_value=[binding]), \
         patch.object(fn.Tile, "objects") as tile_objs, \
         patch.object(fn, "generate_id") as g:
        tile_objs.filter.return_value = tiles_qs
        fn.IdGeneratorFunction().on_update_lifecycle_state(
            resource, current_state=None, new_state=new_state
        )

    g.assert_not_called()
    tile.save.assert_not_called()
    assert tile.data[str(node_id)]["en"]["value"] == "MANUAL"
