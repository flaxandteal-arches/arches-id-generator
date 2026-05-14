from datetime import date
from unittest.mock import patch

import pytest

pytest.importorskip("django")

from arches_id_generator import template as template_mod
from arches_id_generator.template import render, TemplateError


@pytest.fixture
def patched_allocate():
    with patch.object(template_mod.allocator, "allocate_or_create", return_value=42) as p:
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
