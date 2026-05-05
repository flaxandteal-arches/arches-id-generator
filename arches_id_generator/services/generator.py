from django.db import transaction
from arches_id_generator.models import IdSequence
from arches_id_generator.services.formats import render_format

import re

_VALID_KEY = re.compile(r"^[a-z][a-z0-9-]{0,127}$")

def _validate_key(key):
    if not _VALID_KEY.fullmatch(key):
        raise ValueError(
            "sequence_key must be lowercase letters/digits/hyphens, "
            "start with a letter, max 128 chars"
        )

def generate_id(key, template):
    _validate_key(key)
    with transaction.atomic():
        row, _ = IdSequence.objects.select_for_update().get_or_create(key=key)
        row.last_issued += 1
        row.save(update_fields=["last_issued", "updated_at"])
        return render_format(template, row.last_issued)