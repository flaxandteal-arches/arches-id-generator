from datetime import date
import pytest
from arches_id_generator.services.formats import render_format


def test_simple_padding():
    assert render_format("3{seq:05}", 1) == "300001"
    assert render_format("3{seq:05}", 47) == "300047"

def test_no_padding():
    assert render_format("{seq}", 7) == "7"

def test_calendar_year():
    assert render_format("AE/{YYYY}/{seq:03}", 7, today=date(2026, 6, 1)) == "AE/2026/007"
    assert render_format("AE/{YY}/{seq:03}", 7, today=date(2026, 6, 1)) == "AE/26/007"

def test_fiscal_year_after_april():
    # June 2025 → fiscal 2025/26
    out = render_format("AFC{seq:03}-{fiscal_yy}/{fiscal_yy_next}", 1, today=date(2025, 6, 1))
    assert out == "AFC001-25/26"

def test_fiscal_year_before_april():
    # Feb 2026 → still fiscal 2025/26
    out = render_format("AFC{seq:03}-{fiscal_yy}/{fiscal_yy_next}", 1, today=date(2026, 2, 15))
    assert out == "AFC001-25/26"

def test_unknown_token_raises():
    with pytest.raises(ValueError, match="Invalid placeholder in template"):
        render_format("{nonsense}", 1)