from datetime import date
from unittest.mock import patch

import pytest

pytest.importorskip("django")

from arches_id_generator import template as template_mod
from arches_id_generator.template import render, TemplateError


@pytest.fixture
def patched_allocate():
    with patch.object(template_mod.allocator, "allocate", return_value=42) as p:
        yield p


def test_seq_with_padding(patched_allocate):
    assert render("ID-{seq:05}", scope_key="k") == "ID-00042"


def test_seq_no_padding(patched_allocate):
    assert render("{seq}", scope_key="k") == "42"


def test_seq_requires_scope_key():
    with pytest.raises(TemplateError, match="scope_key"):
        render("{seq}")


def test_calendar_year(patched_allocate):
    out = render("AE/{YYYY}/{seq:03}", scope_key="k", today=date(2026, 6, 1))
    assert out == "AE/2026/00042"


def test_fiscal_year_after_april(patched_allocate):
    out = render(
        "AFC{seq:03}-{fiscal_yy}/{fiscal_yy_next}",
        scope_key="k",
        today=date(2025, 6, 1),
    )
    assert out == "AFC00042-25/26"


def test_fiscal_year_before_april(patched_allocate):
    out = render(
        "AFC{seq:03}-{fiscal_yy}/{fiscal_yy_next}",
        scope_key="k",
        today=date(2026, 2, 15),
    )
    assert out == "AFC00042-25/26"


def test_uuid_token():
    value = render("{uuid}")
    assert len(value) == 36
    assert value.count("-") == 4


def test_rand_token():
    value = render("{rand:6}")
    assert len(value) == 6


def test_rand_requires_length():
    with pytest.raises(TemplateError, match="rand"):
        render("{rand}")


def test_randint_requires_length():
    with pytest.raises(TemplateError, match="randint"):
        render("{randint}")


def test_rand_with_uniqueness_retry():
    seen = {"AAAA"}
    with patch.object(template_mod.generators, "generate_random_string",
                      side_effect=["AAAA", "BBBB"]):
        value = render("{rand:4}", exists_check_fn=lambda v: v in seen)
    assert value == "BBBB"


def test_uniqueness_check_runs_against_full_id():
    # Check must see the rendered template, not just the random fragment.
    seen_full_ids = []
    with patch.object(template_mod.generators, "generate_random_string",
                      return_value="XYZ"):
        render(
            "ART-{rand:3}",
            exists_check_fn=lambda v: seen_full_ids.append(v) or False,
        )
    assert seen_full_ids == ["ART-XYZ"]


def test_seq_skips_uniqueness_check(patched_allocate):
    # {seq} guarantees uniqueness, so the check must not be invoked even if
    # the template also contains a random token.
    calls = []
    with patch.object(template_mod.generators, "generate_random_string",
                      return_value="QQQ"):
        value = render(
            "ART-{seq:04}-{rand:3}",
            scope_key="k",
            exists_check_fn=lambda v: calls.append(v) or True,
        )
    assert value == "ART-0042-QQQ"
    assert calls == []


def test_uuid_skips_uniqueness_check():
    calls = []
    value = render("{uuid}", exists_check_fn=lambda v: calls.append(v) or True)
    assert calls == []
    assert len(value) == 36


def test_full_template_rerolls_on_collision():
    # When the full rendered string is already taken, the whole template
    # is rolled again, not just the random fragment.
    with patch.object(template_mod.generators, "generate_random_string",
                      side_effect=["AAA", "BBB"]):
        value = render(
            "X-{rand:3}",
            exists_check_fn=lambda v: v == "X-AAA",
        )
    assert value == "X-BBB"


def test_context_literal(patched_allocate):
    out = render("{prefix}-{seq}", scope_key="k", context={"prefix": "ART"})
    assert out == "ART-42"


def test_unknown_token_raises():
    with pytest.raises(TemplateError, match="unknown template token"):
        render("{nonsense}")


def test_no_tokens_raises():
    with pytest.raises(TemplateError, match="no tokens"):
        render("plain-string")


# --- next_number (number-widget allocation, shared with {seq}) ---------------

def test_next_number_returns_raw_int(patched_allocate):
    result = template_mod.next_number("k")
    assert result == 42
    assert isinstance(result, int)  # not formatted/stringified
    patched_allocate.assert_called_once_with("k", start_number=None)


def test_next_number_threads_start_number(patched_allocate):
    template_mod.next_number("k", start_number=3000)
    patched_allocate.assert_called_once_with("k", start_number=3000)


def test_next_number_validates_key(patched_allocate):
    with pytest.raises(ValueError):
        template_mod.next_number("Bad Key")
    patched_allocate.assert_not_called()


def test_emit_seq_and_next_number_share_allocation(patched_allocate):
    # {seq} formats the int next_number returns -> single allocation path.
    assert render("{seq:04}", scope_key="shared") == "0042"
    assert template_mod.next_number("shared") == 42
