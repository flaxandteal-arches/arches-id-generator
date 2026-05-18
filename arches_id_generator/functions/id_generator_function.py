import logging

from django.conf import settings
from django.utils.translation import get_language

from arches.app.functions.base import BaseFunction
from arches.app.models.models import CardXNodeXWidget
from arches.app.models.tile import Tile, TileCardinalityError

from arches_id_generator.constants import FUNCTION_ID, NUMBER_WIDGET_ID, WIDGET_IDS
from arches_id_generator.template import next_number, render


logger = logging.getLogger(__name__)


GENERATE_ON_TILE_SAVE = "tile_save"
GENERATE_ON_RESOURCE_ACTIVATION = "resource_activation"


details = {
    "functionid": FUNCTION_ID,
    "name": "ID Generator",
    "type": "lifecyclehandler",
    "description": (
        "Generates IDs for nodes configured with the id-generator widget, "
        "either at tile save or on resource lifecycle activation."
    ),
    "defaultconfig": {},
    "component": "",
    "modulename": "id_generator_function.py",
    "classname": "IdGeneratorFunction",
}


def _activation_state_names():
    return getattr(
        settings,
        "ARCHES_ID_GENERATOR_ACTIVATION_STATE_NAMES",
        ["active", "published"],
    )


def _existing_values_for_node(node_id):
    def check(candidate):
        return Tile.objects.filter(
            **{f"data__{node_id}__contains": candidate}
        ).exists()

    return check


def _stamp(tile, node_id, sequence_key, template_string):
    new_value = render(
        template_string,
        scope_key=sequence_key,
        exists_check_fn=_existing_values_for_node(node_id),
    )
    language = get_language() or settings.LANGUAGE_CODE
    tile.data[node_id] = {
        language: {"value": new_value, "direction": "ltr"},
    }


def _coerce_start_number(raw):
    """Widget config can yield None / "" / a string / 0; sequences are
    1-based, so anything invalid or < 1 falls back to 1."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 1
    return n if n >= 1 else 1


def _stamp_number(tile, node_id, sequence_key, start_number):
    """Number variant: store a bare int (no i18n wrapper, no template)."""
    tile.data[node_id] = next_number(
        sequence_key, start_number=_coerce_start_number(start_number)
    )


def _is_number_binding(entry):
    return str(entry.widget_id) == NUMBER_WIDGET_ID


def _binding_value_present(tile, node_id, is_number):
    value = tile.data.get(node_id)
    # A number node legitimately stores 0 (falsy), so test for presence,
    # not truthiness, in the numeric case.
    return value is not None if is_number else bool(value)


def _apply_binding(tile, entry):
    """Stamp the binding into `tile` if empty (string=templated,
    number=int). Returns True iff a value was stamped."""
    node_id = str(entry.node_id)
    sequence_key = entry.config.get("sequence_key")
    if not sequence_key:
        return False
    is_number = _is_number_binding(entry)
    if _binding_value_present(tile, node_id, is_number):
        return False
    if is_number:
        _stamp_number(tile, node_id, sequence_key, entry.config.get("start_number"))
        return True
    template_string = entry.config.get("template")
    if not template_string:
        return False
    _stamp(tile, node_id, sequence_key, template_string)
    return True


def _bindings_for_nodegroup(nodegroup_id):
    return CardXNodeXWidget.objects.filter(
        widget_id__in=WIDGET_IDS,
        node__nodegroup_id=nodegroup_id,
    )


def _bindings_for_graph(graph_id):
    return CardXNodeXWidget.objects.filter(
        widget_id__in=WIDGET_IDS,
        node__graph_id=graph_id,
    )


class IdGeneratorFunction(BaseFunction):
    def save(self, tile, request, context=None):
        """Pre-tile-save: stamp values for tile_save-mode bindings."""
        for entry in _bindings_for_nodegroup(tile.nodegroup_id):
            generate_on = entry.config.get("generate_on", GENERATE_ON_TILE_SAVE)
            if generate_on != GENERATE_ON_TILE_SAVE:
                continue
            _apply_binding(tile, entry)

    def post_save(self, tile, request, context=None):
        """auto_populate: create a blank cardinality-1 tile if none exists.

        new_tile.save() re-enters this method; it terminates because the
        nodegroup-self skip and the exists() guard each retire a nodegroup
        permanently. Removing either reintroduces recursion/duplicates.
        """
        bindings = _bindings_for_graph(tile.resourceinstance.graph_id)

        for entry in bindings:
            if entry.config.get("auto_populate") is not True:
                continue
            # Contradicts resource_activation (lifecycle handler creates the
            # tile itself); UI blocks it, ignore raw/legacy config defensively.
            if entry.config.get("generate_on") == GENERATE_ON_RESOURCE_ACTIVATION:
                continue

            nodegroup = entry.node.nodegroup

            if nodegroup.cardinality != "1":
                continue
            if tile.nodegroup_id == nodegroup.nodegroupid:
                continue
            if nodegroup.parentnodegroup_id is not None:
                logger.warning(
                    "auto_populate not supported for child nodegroups (node=%s).",
                    entry.node_id,
                )
                continue
            if Tile.objects.filter(
                resourceinstance_id=tile.resourceinstance_id,
                nodegroup_id=nodegroup.nodegroupid,
            ).exists():
                continue

            try:
                new_tile = Tile().get_blank_tile_from_nodegroup_id(
                    str(nodegroup.nodegroupid),
                    resourceid=tile.resourceinstance_id,
                    parenttile=None,
                )
                # Re-enters post_save; terminates per the docstring.
                new_tile.save()
            except TileCardinalityError:
                pass

    def on_update_lifecycle_state(
        self, resource_instance, current_state, new_state, request=None, context=None
    ):
        """Stamp resource_activation-mode bindings when the resource enters
        an 'active' lifecycle state.
        """
        if not new_state:
            return
        if new_state.name.lower() not in {n.lower() for n in _activation_state_names()}:
            return

        for entry in _bindings_for_graph(resource_instance.graph_id):
            if entry.config.get("generate_on") != GENERATE_ON_RESOURCE_ACTIVATION:
                continue

            sequence_key = entry.config.get("sequence_key")
            if not sequence_key:
                continue
            # String variant needs a template; number variant doesn't.
            if not _is_number_binding(entry) and not entry.config.get("template"):
                continue

            nodegroup = entry.node.nodegroup
            tiles = list(
                Tile.objects.filter(
                    resourceinstance_id=resource_instance.pk,
                    nodegroup_id=nodegroup.nodegroupid,
                )
            )

            # No tile was ever saved for this nodegroup (e.g. the resource was
            # published without the ID card being filled in). Create a blank
            # top-level tile so the ID can still be stamped, mirroring the
            # constraints used by the auto_populate path in post_save.
            if not tiles:
                if nodegroup.cardinality != "1":
                    logger.warning(
                        "Cannot auto-create ID tile for cardinality-n "
                        "nodegroup on activation (node=%s).",
                        entry.node_id,
                    )
                    continue
                if nodegroup.parentnodegroup_id is not None:
                    logger.warning(
                        "Cannot auto-create ID tile for child nodegroup on "
                        "activation (node=%s).",
                        entry.node_id,
                    )
                    continue
                try:
                    new_tile = Tile().get_blank_tile_from_nodegroup_id(
                        str(nodegroup.nodegroupid),
                        resourceid=resource_instance.pk,
                        parenttile=None,
                    )
                except TileCardinalityError:
                    continue
                tiles = [new_tile]

            for tile in tiles:
                if _apply_binding(tile, entry):
                    # Re-enters post_save; terminates via its exists() guard.
                    tile.save()
