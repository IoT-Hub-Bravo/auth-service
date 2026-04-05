import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Command(BaseCommand):
    help = "Seed development users for the auth-service. Guarded by ALLOW_SETUP_ADMIN."

    def handle(self, *args, **options):
        allow = _env_bool("ALLOW_SETUP_ADMIN", default=False)
        if not (settings.DEBUG or allow):
            raise CommandError(
                "setup_admin is disabled outside development/testing. "
                "Set ALLOW_SETUP_ADMIN=true to override."
            )

        self.stdout.write("Seeding auth-service users...")

        user_model = apps.get_model("users", "User")

        try:
            with transaction.atomic():
                self._create_superuser(user_model)
                self._create_role_users(user_model)
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f"User seeding failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("User seeding completed successfully."))
        self.stdout.write("Seeded users (passwords come from environment variables):")
        self.stdout.write("  - DEV_SUPERUSER_USERNAME  (superuser, role=admin)")
        self.stdout.write("  - DEV_ADMIN_USERNAME      (role=admin)")
        self.stdout.write("  - DEV_CLIENT_USERNAME     (role=client)")

    def _create_superuser(self, user_model):
        username = os.getenv("DEV_SUPERUSER_USERNAME", "superadmin")
        email = os.getenv("DEV_SUPERUSER_EMAIL", "superadmin@example.com")
        password = os.getenv("DEV_SUPERUSER_PASSWORD")

        if not password:
            raise CommandError(
                "DEV_SUPERUSER_PASSWORD is required. "
                "Refusing to create a superuser without an explicit password."
            )

        from django.db import models as django_models

        existing = user_model.objects.filter(
            django_models.Q(username=username) | django_models.Q(email=email)
        ).first()

        if existing:
            self.stdout.write(f"Superuser '{username}' already exists — skipping.")
            return

        user_model.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created superuser: {username}"))

    def _create_role_users(self, user_model):
        role_users = [
            {
                "username_env": "DEV_ADMIN_USERNAME",
                "email_env": "DEV_ADMIN_EMAIL",
                "password_env": "DEV_ADMIN_PASSWORD",
                "default_username": "admin_user",
                "default_email": "admin_user@example.com",
                "role": "admin",
            },
            {
                "username_env": "DEV_CLIENT_USERNAME",
                "email_env": "DEV_CLIENT_EMAIL",
                "password_env": "DEV_CLIENT_PASSWORD",
                "default_username": "client_user",
                "default_email": "client_user@example.com",
                "role": "client",
            },
        ]

        for item in role_users:
            username = os.getenv(item["username_env"], item["default_username"])
            email = os.getenv(item["email_env"], item["default_email"])
            password = os.getenv(item["password_env"])

            if not password:
                self.stdout.write(
                    f"Skipping '{username}': {item['password_env']} is not set."
                )
                continue

            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={"email": email, "role": item["role"]},
            )

            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(
                    self.style.SUCCESS(f"Created user: {username} (role={item['role']})")
                )
            else:
                self.stdout.write(f"User '{username}' already exists — skipping.")
