"""Preview, apply or reverse corrections verified from source credits."""

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.editorial.source_credit_repair import (
    apply_credit_repair,
    credit_repair_plan,
    restore_credit_repair,
)
from apps.catalog.models import Book
from apps.common.models import AuditLog
from apps.ingestion.services.source_credits import repairable_credit_names


class Command(BaseCommand):
    help = "Dry-run verified source credit corrections; --apply records reversible changes."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--book", action="append", dest="books")
        parser.add_argument(
            "--restore", help="Restore one repair by audit ID, with --apply."
        )

    def handle(self, *args, **options):
        if options["restore"]:
            return self.restore(options)
        books = (
            Book.objects.filter(
                deleted_at__isnull=True,
                book_contributors__contributor__name__in=repairable_credit_names(),
            )
            .exclude(raw_scrape_payload={})
            .distinct()
        )
        if options["books"]:
            books = books.filter(pk__in=options["books"])
        changed = 0
        for book in books.iterator():
            plan = credit_repair_plan(book)
            if not plan:
                continue
            changed += 1
            self.stdout.write(f"{book.pk}: {len(plan)} credit correction(s)")
            if options["apply"]:
                audit = apply_credit_repair(book.pk)
                if audit:
                    self.stdout.write(f"  audit={audit.pk}")
        self.stdout.write(
            f"{'Applied' if options['apply'] else 'Proposed'} books: {changed}"
        )

    def restore(self, options):
        if not options["apply"]:
            raise CommandError("Restoration requires --apply.")
        try:
            audit = restore_credit_repair(options["restore"])
        except (ValueError, AuditLog.DoesNotExist, Book.DoesNotExist) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(f"Restored book {audit.target_id}; audit={audit.pk}")
