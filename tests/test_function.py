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
         patch.object(fn, "render", return_value="042"):
        fn.IdGeneratorFunction().save(tile, request=None)
    assert tile.data[str(node_id)]["en"]["value"] == "042"


def test_save_skips_resource_activation_binding(tile):
    node_id = uuid4()
    with patch.object(fn, "_bindings_for_nodegroup",
                      return_value=[_binding(node_id, generate_on="resource_activation")]), \
         patch.object(fn, "render") as g:
        fn.IdGeneratorFunction().save(tile, request=None)
    g.assert_not_called()
    assert tile.data == {}


def test_save_skips_existing_value(tile):
    node_id = uuid4()
    tile.data[str(node_id)] = {"en": {"value": "USER-TYPED", "direction": "ltr"}}
    with patch.object(fn, "_bindings_for_nodegroup", return_value=[_binding(node_id)]), \
         patch.object(fn, "render") as g:
        fn.IdGeneratorFunction().save(tile, request=None)
    g.assert_not_called()
    assert tile.data[str(node_id)]["en"]["value"] == "USER-TYPED"


def test_save_skips_missing_config(tile):
    node_id = uuid4()
    with patch.object(fn, "_bindings_for_nodegroup",
                      return_value=[_binding(node_id, sequence_key="")]), \
         patch.object(fn, "render") as g:
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
         patch.object(fn, "render", return_value="001"):
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
         patch.object(fn, "render") as g:
        tile_objs.filter.return_value = tiles_qs
        fn.IdGeneratorFunction().on_update_lifecycle_state(
            resource, current_state=None, new_state=new_state
        )

    g.assert_not_called()
    tile.save.assert_not_called()
    assert tile.data[str(node_id)]["en"]["value"] == "MANUAL"


# --- post_save re-entrancy / auto_populate -----------------------------------

def _auto_binding(nodegroup_id):
    """Binding that auto-populates a top-level cardinality-1 nodegroup."""
    entry = MagicMock()
    entry.node_id = uuid4()
    entry.config = {"auto_populate": True}
    entry.node.nodegroup = SimpleNamespace(
        nodegroupid=nodegroup_id,
        cardinality="1",
        parentnodegroup_id=None,
    )
    return entry


def test_post_save_creates_one_tile_per_auto_populate_nodegroup_under_reentrancy():
    """Multiple auto_populate bindings on one graph: post_save must create
    exactly one tile per nodegroup, and the new_tile.save() re-entrancy must
    terminate (not loop, not duplicate)."""
    graph_id = uuid4()
    resource_id = uuid4()
    ng1, ng2 = uuid4(), uuid4()
    bindings = [_auto_binding(ng1), _auto_binding(ng2)]

    # (resourceinstance_id, nodegroup_id) pairs that "exist" in the DB.
    store: set[tuple] = set()
    created: list = []
    SAVE_CAP = 50  # guard: if termination is broken, fail loud not hang

    func = fn.IdGeneratorFunction()

    def make_new_tile(nodegroup_id):
        t = SimpleNamespace(
            nodegroup_id=nodegroup_id,
            resourceinstance_id=resource_id,
            resourceinstance=SimpleNamespace(graph_id=graph_id),
            data={},
        )

        def save():
            assert len(created) < SAVE_CAP, "post_save re-entrancy did not terminate"
            # Arches persists the row *before* re-running node functions —
            # the termination argument depends on this ordering.
            store.add((resource_id, nodegroup_id))
            created.append(nodegroup_id)
            func.post_save(t, request=None)

        t.save = save
        return t

    class FakeTileObjects:
        def filter(self, **kw):
            present = (kw["resourceinstance_id"], kw["nodegroup_id"]) in store
            return SimpleNamespace(exists=lambda: present)

    class FakeTile:
        objects = FakeTileObjects()

        def get_blank_tile_from_nodegroup_id(self, ngid, resourceid=None, parenttile=None):
            return make_new_tile(ngid)

    trigger = SimpleNamespace(
        nodegroup_id=uuid4(),  # some other nodegroup, not ng1/ng2
        resourceinstance_id=resource_id,
        resourceinstance=SimpleNamespace(graph_id=graph_id),
        data={},
    )

    with patch.object(fn, "_bindings_for_graph", return_value=bindings), \
         patch.object(fn, "Tile", FakeTile):
        func.post_save(trigger, request=None)

    # Exactly one tile per distinct auto_populate nodegroup; no duplicates.
    assert sorted(created) == sorted([ng1, ng2])

    # Idempotent: a second pass (tiles now exist) creates nothing.
    created.clear()
    with patch.object(fn, "_bindings_for_graph", return_value=bindings), \
         patch.object(fn, "Tile", FakeTile):
        func.post_save(trigger, request=None)
    assert created == []


def test_post_save_ignores_auto_populate_when_generate_on_activation():
    """auto_populate + generate_on=resource_activation is contradictory; the
    lifecycle handler creates the tile, so post_save must not."""
    binding = _auto_binding(uuid4())
    binding.config["generate_on"] = "resource_activation"

    trigger = SimpleNamespace(
        nodegroup_id=uuid4(),
        resourceinstance_id=uuid4(),
        resourceinstance=SimpleNamespace(graph_id=uuid4()),
        data={},
    )

    with patch.object(fn, "_bindings_for_graph", return_value=[binding]), \
         patch.object(fn, "Tile") as TileCls:
        fn.IdGeneratorFunction().post_save(trigger, request=None)

    TileCls.assert_not_called()
    TileCls.objects.filter.assert_not_called()


# --- number-datatype variant -------------------------------------------------

from arches_id_generator.constants import NUMBER_WIDGET_ID, WIDGET_ID  # noqa: E402


def _num_binding(node_id, **cfg):
    entry = MagicMock()
    entry.node_id = node_id
    entry.widget_id = NUMBER_WIDGET_ID
    config = {"sequence_key": "k", "start_number": 1}
    config.update(cfg)
    entry.config = config
    return entry


def test_is_number_binding_discriminates_by_widget_id():
    assert fn._is_number_binding(_num_binding(uuid4())) is True
    str_entry = MagicMock(widget_id=WIDGET_ID)
    assert fn._is_number_binding(str_entry) is False


@pytest.mark.parametrize(
    "raw,expected",
    [(None, 1), ("", 1), ("abc", 1), (0, 1), (-5, 1), (1, 1),
     (3000, 3000), ("3000", 3000)],
)
def test_coerce_start_number(raw, expected):
    assert fn._coerce_start_number(raw) == expected


def test_apply_binding_number_writes_bare_int():
    node_id = uuid4()
    tile = SimpleNamespace(data={})
    entry = _num_binding(node_id, start_number=3000)
    with patch.object(fn, "next_number", return_value=3000) as nn:
        assert fn._apply_binding(tile, entry) is True
    nn.assert_called_once_with("k", start_number=3000)
    # bare int, not the string datatype's i18n dict
    assert tile.data[str(node_id)] == 3000


def test_apply_binding_number_skips_when_value_present_including_zero():
    node_id = uuid4()
    tile = SimpleNamespace(data={str(node_id): 0})  # 0 is a real value
    with patch.object(fn, "next_number") as nn:
        assert fn._apply_binding(tile, _num_binding(node_id)) is False
    nn.assert_not_called()


def test_apply_binding_number_requires_sequence_key():
    tile = SimpleNamespace(data={})
    entry = _num_binding(uuid4(), sequence_key="")
    with patch.object(fn, "next_number") as nn:
        assert fn._apply_binding(tile, entry) is False
    nn.assert_not_called()


def test_apply_binding_string_path_unaffected():
    node_id = uuid4()
    tile = SimpleNamespace(data={})
    entry = _binding(node_id)  # string binding (template set)
    with patch.object(fn, "_stamp") as stamp:
        assert fn._apply_binding(tile, entry) is True
    stamp.assert_called_once()
