from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or update the configured super admin account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            dest="password",
            help="Password to assign to the seeded super admin.",
        )
        parser.add_argument(
            "--full-name",
            dest="full_name",
            default="R Salehin",
            help="Optional display name for the seeded super admin.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Force overwrite existing super admin details.",
        )

    def handle(self, *args, **options):
        email = settings.SUPER_ADMIN_EMAIL
        password = options.get("password") or settings.SUPER_ADMIN_PASSWORD

        if not password:
            self.stderr.write(
                "No password supplied. Use --password or set SUPER_ADMIN_PASSWORD."
            )
            return

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": options["full_name"],
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            action = "Created"
        else:
            updated = False
            if options["force"]:
                user.full_name = options["full_name"]
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                updated = True
            else:
                if not user.full_name:
                    user.full_name = options["full_name"]
                    updated = True
                if not user.is_staff:
                    user.is_staff = True
                    updated = True
                if not user.is_superuser:
                    user.is_superuser = True
                    updated = True
                if not user.is_active:
                    user.is_active = True
                    updated = True
                if updated:
                    user.save()
            action = "Updated" if updated else "Preserved existing"

        self.stdout.write(f"{action} super admin: {email}")
