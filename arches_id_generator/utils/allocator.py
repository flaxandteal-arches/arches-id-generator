from django.db import transaction

from arches_id_generator.models import IdSequence


def allocate(key, count=1):
    """Atomically allocate `count` numbers; returns the first (caller owns
    [n, n+count-1]). The sequence is auto-created at start_number=1 on first
    use, so callers never need to pre-create the row."""
    with transaction.atomic():
        sequence, _ = IdSequence.objects.select_for_update().get_or_create(pk=key)

        allocated_number = sequence.next_number
        sequence.next_number = allocated_number + count
        sequence.save(update_fields=["next_number", "updated_at"])

        return allocated_number
