from datetime import date
import string

_FISCAL_YEAR_START_MONTH = 4
_ALLOWED_FIELDS = {"seq", "YYYY", "YY", "fiscal_yy", "fiscal_yy_next"}

def _validate_template(template):
    for literal_text, field_name, format_spec, conversion in string.Formatter().parse(template):
        if field_name is None:
            continue                                  # plain text between/around tokens
        if conversion is not None:                    # blocks `{seq!r}`, `{seq!s}` etc.
            raise ValueError(f"Conversion '!{conversion}' not allowed")
        if "." in field_name or "[" in field_name:    # blocks `{seq.__class__...}` and `{seq[0]}`
            raise ValueError(f"Attribute/index access not allowed: {field_name!r}")
        if field_name not in _ALLOWED_FIELDS:
            raise ValueError(f"Unknown token: {field_name!r}")

def _build_context(seq, today=None):
    today = today or date.today()
    if today.month >= _FISCAL_YEAR_START_MONTH:
        fiscal_year = today.year
    else:
        fiscal_year = today.year - 1
    return {
        "seq": seq,
        "YYYY": today.year,
        "YY": today.year % 100,
        "fiscal_yy": fiscal_year % 100,
        "fiscal_yy_next": (fiscal_year + 1) % 100
    }
        
def render_format(template, seq, today=None):
    _validate_template(template)
    try:
        return template.format(**_build_context(seq, today))
    except KeyError as e:
        raise ValueError(f"Invalid placeholder in template: {e}")