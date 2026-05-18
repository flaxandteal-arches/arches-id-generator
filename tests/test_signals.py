"""signals.ensure_function_attached_to_graph: early-exit guards, the
Function.DoesNotExist branch, and the happy-path auto-attach.

signals.py imports real Arches models, so this collects only where
DJANGO_SETTINGS_MODULE is configured."""
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("django")

from arches_id_generator import signals
from arches_id_generator.constants import FUNCTION_ID, WIDGET_ID


class _DoesNotExist(Exception):
    pass


def _instance(widget_id=WIDGET_ID, node_id="node-1", graph_id="graph-1"):
    inst = MagicMock()
    inst.widget_id = widget_id
    inst.node_id = node_id
    inst.node.graph_id = graph_id
    return inst


def _patched(get_side_effect=None, function=None):
    Function = MagicMock()
    Function.DoesNotExist = _DoesNotExist
    if get_side_effect is not None:
        Function.objects.get.side_effect = get_side_effect
    else:
        Function.objects.get.return_value = function or MagicMock(name="function")
    FunctionXGraph = MagicMock()
    return Function, FunctionXGraph


def test_ignores_non_idgenerator_widget():
    Function, FXG = _patched()
    with patch.object(signals, "Function", Function), \
         patch.object(signals, "FunctionXGraph", FXG):
        signals.ensure_function_attached_to_graph(
            None, _instance(widget_id="some-other-widget-id")
        )
    Function.objects.get.assert_not_called()
    FXG.objects.get_or_create.assert_not_called()


def test_ignores_instance_without_node():
    Function, FXG = _patched()
    with patch.object(signals, "Function", Function), \
         patch.object(signals, "FunctionXGraph", FXG):
        signals.ensure_function_attached_to_graph(None, _instance(node_id=None))
    Function.objects.get.assert_not_called()
    FXG.objects.get_or_create.assert_not_called()


def test_function_not_registered_warns_and_returns():
    Function, FXG = _patched(get_side_effect=_DoesNotExist)
    with patch.object(signals, "Function", Function), \
         patch.object(signals, "FunctionXGraph", FXG), \
         patch.object(signals, "logger") as log:
        signals.ensure_function_attached_to_graph(None, _instance())
    log.warning.assert_called_once()
    FXG.objects.get_or_create.assert_not_called()


def test_happy_path_attaches_function_to_graph():
    fn = MagicMock(name="function")
    Function, FXG = _patched(function=fn)
    with patch.object(signals, "Function", Function), \
         patch.object(signals, "FunctionXGraph", FXG):
        signals.ensure_function_attached_to_graph(
            None, _instance(graph_id="graph-42")
        )
    Function.objects.get.assert_called_once_with(pk=FUNCTION_ID)
    FXG.objects.get_or_create.assert_called_once_with(
        function=fn, graph_id="graph-42", defaults={"config": {}}
    )


def test_widget_id_compared_as_string():
    # instance.widget_id is typically a UUID; the guard str()s it, so a
    # UUID-typed value equal to WIDGET_ID must still match.
    import uuid

    fn = MagicMock()
    Function, FXG = _patched(function=fn)
    with patch.object(signals, "Function", Function), \
         patch.object(signals, "FunctionXGraph", FXG):
        signals.ensure_function_attached_to_graph(
            None, _instance(widget_id=uuid.UUID(WIDGET_ID))
        )
    FXG.objects.get_or_create.assert_called_once()
