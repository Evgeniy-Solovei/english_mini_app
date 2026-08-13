from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.learning.models import Lesson


class Command(BaseCommand):
    help = "Load the bundled learning fixture into an empty PostgreSQL database"

    def handle(self, *args, **options):
        if Lesson.objects.exists():
            self.stdout.write("Learning content already exists; fixture import skipped.")
            return

        fixture = Path(settings.BASE_DIR) / "dumps" / "english_bot_curriculum_v3_2026-08-12.json.gz"
        if not fixture.exists():
            raise CommandError(f"Initial content fixture not found: {fixture}")

        call_command("loaddata", str(fixture))
        self.stdout.write(self.style.SUCCESS("Initial learning content loaded into PostgreSQL."))
