from django.db import transaction

from arches_id_generator.models import IdSequence


def allocate(key, count=1):
    """Atomically allocate `count` numbers; returns the first (caller owns [n, n+count-1])."""
    with transaction.atomic():
        sequence = IdSequence.objects.select_for_update().get(pk=key)

        allocated_number = sequence.next_number
        sequence.next_number = allocated_number + count
        sequence.save(update_fields=["next_number", "updated_at"])

        return allocated_number


def allocate_or_create(key, count=1):
    """Like allocate but auto-creates the sequence at start_number=1 if absent."""
    with transaction.atomic():
        sequence, _ = IdSequence.objects.select_for_update().get_or_create(pk=key)

        allocated_number = sequence.next_number
        sequence.next_number = allocated_number + count
        sequence.save(update_fields=["next_number", "updated_at"])

        return allocated_number
