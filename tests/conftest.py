"""
Stub the bits of `arches.app.models` that signals.py imports at module-load
time, so the signal tests don't require a configured Arches environment.
Real Django *is* required for the rest (transaction, ORM, management command);
those tests use pytest.importorskip("django") at the top of their files.
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
    from arches.app.models.models import CardXNodeXWidget  # noqa: F401
except Exception:
    _stub("arches")
    _stub("arches.app")
    _stub("arches.app.models")

    tile_mod = _stub("arches.app.models.tile")
    tile_mod.Tile = type("Tile", (), {})

    models_mod = _stub("arches.app.models.models")

    class CardXNodeXWidget:
        objects = None

    models_mod.CardXNodeXWidget = CardXNodeXWidget
