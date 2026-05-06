from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from arches_id_generator.models import IdSequence


class Command(BaseCommand):
    help = (
        "Reset or set the counter for an ID sequence. "
        "The next generated ID will be (--to) + 1."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "key",
            nargs="?",
            help="The sequence_key whose counter should be updated.",
        )
        parser.add_argument(
            "--to",
            type=int,
            default=0,
            help="Value to set last_issued to. Default: 0.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Allow lowering the counter below its current value. "
                "Without this, the command refuses to lower the counter "
                "because it can cause duplicate IDs."
            ),
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all sequences and exit. Ignores other arguments.",
        )

    def handle(self, *args, **opts):
        if opts["list"]:
            rows = IdSequence.objects.order_by("key")
            if not rows:
                self.stdout.write("No sequences found.")
                return
            width = max(len(r.key) for r in rows)
            for row in rows:
                self.stdout.write(
                    f"{row.key.ljust(width)}  last_issued={row.last_issued}  "
                    f"updated_at={row.updated_at.isoformat()}"
                )
            return

        key = opts["key"]
        target = opts["to"]

        if not key:
            raise CommandError("Missing sequence key. Pass a key, or use --list.")

        with transaction.atomic():
            try:
                row = IdSequence.objects.select_for_update().get(key=key)
            except IdSequence.DoesNotExist:
                raise CommandError(f"No sequence with key={key!r}")

            if target < row.last_issued and not opts["force"]:
                raise CommandError(
                    f"Refusing to lower {key} from {row.last_issued} to {target} "
                    f"without --force (risk of duplicate IDs against existing tiles)."
                )

            old = row.last_issued
            row.last_issued = target
            row.save(update_fields=["last_issued", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{key}: {old} -> {target} (next ID will be {target + 1})"
            )
        )
