from django.db import transaction

from arches_id_generator.models import IdSequence


def allocate(key, count=1, start_number=None):
    """Atomically allocate `count` numbers; returns the first (caller owns
    [n, n+count-1]). Sequence auto-created on first use. `start_number` only
    applies at creation; an existing sequence is never re-based."""
    defaults = (
        {} if start_number is None
        else {"start_number": start_number, "next_number": start_number}
    )
    with transaction.atomic():
        sequence, _ = IdSequence.objects.select_for_update().get_or_create(
            pk=key, defaults=defaults
        )

        allocated_number = sequence.next_number
        sequence.next_number = allocated_number + count
        sequence.save(update_fields=["next_number", "updated_at"])

        return allocated_number
