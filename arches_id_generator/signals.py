"""Auto-attach the id-generator Function to any graph that uses the widget."""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from arches.app.models.models import (
    CardXNodeXWidget,
    Function,
    FunctionXGraph,
)

from arches_id_generator.constants import FUNCTION_ID, WIDGET_IDS


logger = logging.getLogger(__name__)


@receiver(post_save, sender=CardXNodeXWidget)
def ensure_function_attached_to_graph(sender, instance, **kwargs):
    if str(instance.widget_id) not in WIDGET_IDS:
        return
    if not instance.node_id:
        return

    graph_id = instance.node.graph_id

    try:
        function = Function.objects.get(pk=FUNCTION_ID)
    except Function.DoesNotExist:
        logger.warning(
            "id-generator Function (%s) not registered; "
            "run migrations to enable resource_activation mode.",
            FUNCTION_ID,
        )
        return

    def attach():
        FunctionXGraph.objects.get_or_create(
            function=function,
            graph_id=graph_id,
            defaults={"config": {}},
        )

    transaction.on_commit(attach)
