"""IdSequenceView: seed/read endpoint, the 'refuse edit once used' rule,
and the LoginRequiredMixin gate.

api.py imports real Arches (APIBase / JSON responses), so — like
test_function.py — this collects only where DJANGO_SETTINGS_MODULE is
configured. The view methods are called directly with the ORM and JSON
helpers patched."""
import contextlib
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("django")

from django.contrib.auth.mixins import LoginRequiredMixin

from arches_id_generator.views import api as api_mod


@contextlib.contextmanager
def harness(stored_sequence, payload=None, key_error=None):
    """Patch the ORM + Arches JSON helpers and yield the mock surface.

    JSON responses are turned into inspectable tuples:
      JSONResponse(seq)            -> ("ok", seq)
      JSONErrorResponse(msg, status) -> ("err", msg, status)
    """
    objs = MagicMock()
    objs.filter.return_value.first.return_value = stored_sequence

    deserializer = MagicMock()
    deserializer.return_value.deserialize.return_value = payload or {}

    validate_key = MagicMock(side_effect=key_error)

    with patch.object(api_mod, "IdSequence", MagicMock(objects=objs)) as IdSeq, \
         patch.object(api_mod, "JSONResponse",
                      MagicMock(side_effect=lambda s, **k: ("ok", s))), \
         patch.object(api_mod, "JSONErrorResponse",
                      MagicMock(side_effect=lambda m, status=500: ("err", m, status))), \
         patch.object(api_mod, "JSONDeserializer", deserializer), \
         patch.object(api_mod, "validate_key", validate_key):
        yield MagicMock(
            objs=objs, IdSeq=IdSeq,
            deserializer=deserializer, validate_key=validate_key,
        )


# --- auth gate ----------------------------------------------------------------

def test_view_requires_login():
    # Regression guard: LoginRequiredMixin must stay in the MRO so the
    # endpoint can't silently become anonymous-accessible.
    assert issubclass(api_mod.IdSequenceView, LoginRequiredMixin)


# --- GET ----------------------------------------------------------------------

def test_get_missing_returns_404():
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=None):
        assert view.get(MagicMock(), "k") == (
            "err", "IdSequence not found for the given key.", 404
        )


def test_get_found_returns_sequence():
    seq = MagicMock(name="sequence")
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=seq):
        assert view.get(MagicMock(), "k") == ("ok", seq)


# --- POST ---------------------------------------------------------------------

def test_post_invalid_key_returns_400_before_touching_db():
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=None, key_error=ValueError("bad key")) as h:
        result = view.post(MagicMock(body=b"{}"), "BAD KEY")
    assert result == ("err", "bad key", 400)
    h.deserializer.assert_not_called()  # rejected before reading the body


def test_post_refuses_edit_once_used():
    seq = MagicMock(start_number=1, next_number=7)  # next advanced past start
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=seq, payload={"start_number": 50}):
        result = view.post(MagicMock(body=b"{}"), "k")
    assert result == (
        "err",
        "IdSequence cannot be edited because it has already been used.",
        400,
    )
    seq.save.assert_not_called()


def test_post_edits_unused_sequence():
    seq = MagicMock(start_number=1, next_number=1)  # unused
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=seq, payload={"start_number": 50}):
        result = view.post(MagicMock(body=b"{}"), "k")
    assert seq.start_number == 50
    assert seq.next_number == 50
    seq.save.assert_called_once_with(
        update_fields=["start_number", "next_number", "updated_at"]
    )
    assert result == ("ok", seq)


def test_post_creates_when_absent():
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=None, payload={"start_number": 5}) as h:
        created = h.objs.create.return_value
        result = view.post(MagicMock(body=b"{}"), "new-key")
        h.objs.create.assert_called_once_with(
            pk="new-key", start_number=5, next_number=5
        )
    assert result == ("ok", created)


def test_post_defaults_start_number_to_1_when_omitted():
    view = api_mod.IdSequenceView()
    with harness(stored_sequence=None, payload={}) as h:
        view.post(MagicMock(body=b"{}"), "new-key")
        h.objs.create.assert_called_once_with(
            pk="new-key", start_number=1, next_number=1
        )
