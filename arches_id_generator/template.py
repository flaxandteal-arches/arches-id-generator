"""Render ID templates like `ART-{seq:05}-{rand:4}`. Token reference is in the README."""

import re
from datetime import date as date_cls
from typing import Callable, Optional

from django.conf import settings

from arches_id_generator import generators
from arches_id_generator.utils import allocator
from arches_id_generator.utils.uniqueness import generate_unique
from arches_id_generator.utils.validation import validate_key


TOKEN_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]+))?\}")

# Tokens that guarantee a unique full ID on their own, so wrapping the render
# in a collision-retry loop is redundant (and would produce false positives
# against fragments that happen to appear elsewhere in the column).
DETERMINISTIC_UNIQUE_TOKENS = {"seq", "uuid", "uuid7"}


class TemplateError(ValueError):
    pass


def _fiscal_year_start_month():
    return getattr(settings, "ARCHES_ID_GENERATOR_FISCAL_YEAR_START_MONTH", 4)


def _date_context(today):
    today = today or date_cls.today()
    start_month = _fiscal_year_start_month()
    fiscal_year = today.year if today.month >= start_month else today.year - 1
    return {
        "YYYY": today.year,
        "YY": today.year % 100,
        "fiscal_yy": fiscal_year % 100,
        "fiscal_yy_next": (fiscal_year + 1) % 100,
    }


def next_number(scope_key: str, start_number: Optional[int] = None) -> int:
    """Next integer in `scope_key`. Single allocation path: `{seq}` formats
    this; the number widget stores it raw, so a shared key stays in step.
    `start_number` seeds a new sequence."""
    validate_key(scope_key)
    return allocator.allocate(scope_key, start_number=start_number)


def _emit_seq(spec, scope_key):
    if not scope_key:
        raise TemplateError("template uses {seq} but no scope_key was provided")
    number = next_number(scope_key)
    return format(number, spec) if spec else str(number)


def _emit_rand(spec):
    if not spec or not spec.isdigit():
        raise TemplateError("{rand} requires an integer length, e.g. {rand:6}")
    return generators.generate_random_string(int(spec))


def _emit_randint(spec):
    if not spec or not spec.isdigit():
        raise TemplateError("{randint} requires an integer length, e.g. {randint:5}")
    return str(generators.generate_random_int(int(spec)))


def render(
    template: str,
    scope_key: Optional[str] = None,
    context: Optional[dict] = None,
    exists_check_fn: Optional[Callable[[str], bool]] = None,
    today: Optional[date_cls] = None,
) -> str:
    """Render `template` into a concrete ID string."""
    validate_key(scope_key)
    full_context = _date_context(today)
    if context:
        full_context.update(context)

    token_names = [m.group(1) for m in TOKEN_RE.finditer(template)]
    if not token_names:
        raise TemplateError("template contains no tokens")

    def replace(match):
        name = match.group(1)
        spec = match.group(2)

        if name == "seq":
            return _emit_seq(spec, scope_key)
        if name == "uuid":
            return generators.generate_uuid4()
        if name == "uuid7":
            return generators.generate_uuid7()
        if name == "rand":
            return _emit_rand(spec)
        if name == "randint":
            return _emit_randint(spec)

        if name in full_context:
            value = full_context[name]
            return format(value, spec) if spec else str(value)

        raise TemplateError(f"unknown template token: {{{name}}}")

    roll = lambda: TOKEN_RE.sub(replace, template)

    # Skip the collision-retry when the template already guarantees uniqueness
    # via a deterministic token, or when no uniqueness check was supplied.
    if exists_check_fn is None or any(t in DETERMINISTIC_UNIQUE_TOKENS for t in token_names):
        return roll()
    return generate_unique(roll, exists_check_fn)
