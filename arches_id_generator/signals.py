from django.db.models.signals import pre_save
from django.dispatch import receiver

from arches.app.models.models import CardXNodeXWidget
from arches.app.models.tile import Tile

from arches_id_generator.constants import WIDGET_ID
from arches_id_generator.services.generator import generate_id

@receiver(pre_save, sender=Tile)
def assign_id_to_tile(sender, instance, **kwargs):
    cxnxws = CardXNodeXWidget.objects.filter(
        widget_id=WIDGET_ID,
        node__nodegroup_id=instance.nodegroup_id,
    )
    
    for entry in cxnxws:
        node_id = entry.node_id
        sequence_key = entry.config.get("sequence_key")
        template = entry.config.get("template")
        
        if not sequence_key or not template:
            continue
        
        current = instance.data.get(node_id)
        
        if current:
            continue
        
        new_value = generate_id(sequence_key, template)
        instance.data[node_id] = new_value
        