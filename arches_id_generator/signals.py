import logging

from django.conf import settings
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.translation import get_language

from arches.app.models.models import CardXNodeXWidget
from arches.app.models.tile import Tile  # noqa: F401
from arches.app.models.tile import TileCardinalityError

logger = logging.getLogger(__name__)

from arches_id_generator.constants import WIDGET_ID
from arches_id_generator.services.generator import generate_id

@receiver(pre_save, sender=Tile)
def assign_id_to_tile(sender, instance, **kwargs):
    cxnxws = CardXNodeXWidget.objects.filter(
        widget_id=WIDGET_ID,
        node__nodegroup_id=instance.nodegroup_id,
    )
    
    for entry in cxnxws:
        node_id = str(entry.node_id)
        sequence_key = entry.config.get("sequence_key")
        template = entry.config.get("template")

        if not sequence_key or not template:
            continue

        current = instance.data.get(node_id)

        if current:
            continue

        new_value = generate_id(sequence_key, template)
        language = get_language() or settings.LANGUAGE_CODE
        instance.data[node_id] = {
            language: {"value": new_value, "direction": "ltr"},
        }
        
@receiver(post_save, sender=Tile)
def auto_populate_widget_tile(sender, instance, **kwargs):
    candidate_bindings = CardXNodeXWidget.objects.filter(
        widget_id=WIDGET_ID,
        node__graph_id=instance.resourceinstance.graph_id,
    )

    for entry in candidate_bindings:
        if entry.config.get("auto_populate") is not True:
            print("skipping because auto_populate is not True or None")
            continue

        nodegroup = entry.node.nodegroup

        if nodegroup.cardinality != "1":
            continue

        if instance.nodegroup_id == nodegroup.nodegroupid:
            continue

        if nodegroup.parentnodegroup_id is not None:
            logger.warning(
                "arches_id_generator: auto_populate is not supported for nodes in child "
                "nodegroups (node=%s, nodegroup=%s). The widget will not auto-populate; "
                "the user must save the widget's card directly to generate an ID.",
                entry.node_id,
                nodegroup.nodegroupid,
            )
            continue
        
        if Tile.objects.filter(
            resourceinstance_id = instance.resourceinstance_id,
            nodegroup_id = nodegroup.nodegroupid,
        ).exists():
            continue
        
        try:
            new_tile = Tile().get_blank_tile_from_nodegroup_id(
                str(nodegroup.nodegroupid),
                resourceid = instance.resourceinstance_id,
                parenttile = None,
            )
            new_tile.save()
        except TileCardinalityError as e:
            pass
        