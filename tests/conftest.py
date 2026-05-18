"""Stub the bits of `arches.app.models` that signals/function modules import
at module-load time so unit tests don't need a configured Arches environment.
Real Django is still required for ORM-level tests; those use pytest.importorskip.
"""
import sys
import types


def _stub(name):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return mod


try:
    from arches.app.models.tile import Tile  # noqa: F401
    from arches.app.models.models import (  # noqa: F401
        CardXNodeXWidget,
        Function,
        FunctionXGraph,
        ResourceInstance,
        ResourceInstanceLifecycleState,
    )
    from arches.app.functions.base import BaseFunction  # noqa: F401
except Exception:
    _stub("arches")
    _stub("arches.app")
    _stub("arches.app.models")
    _stub("arches.app.functions")

    tile_mod = _stub("arches.app.models.tile")
    tile_mod.Tile = type("Tile", (), {})
    tile_mod.TileCardinalityError = type("TileCardinalityError", (Exception,), {})

    models_mod = _stub("arches.app.models.models")
    for cls_name in (
        "CardXNodeXWidget",
        "Function",
        "FunctionXGraph",
        "ResourceInstance",
        "ResourceInstanceLifecycleState",
    ):
        setattr(models_mod, cls_name, type(cls_name, (), {"objects": None}))

    base_mod = _stub("arches.app.functions.base")
    base_mod.BaseFunction = type("BaseFunction", (), {
        "__init__": lambda self, config=None, nodegroup_id=None: None,
    })
