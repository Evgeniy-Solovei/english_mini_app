import logging

from django.core.management.base import BaseCommand

from apps.learning.importers.gutenberg import import_graded_stories, import_gutenberg_books
from apps.learning.importers.vocabulary import import_core_vocabulary, import_vocabulary
from apps.learning.models import Lesson, ReadingText, Word

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import books (Gutenberg), graded stories, and vocabulary into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-gutenberg",
            action="store_true",
            help="Skip downloading from Project Gutenberg (use cached DB data)",
        )
        parser.add_argument(
            "--skip-vocabulary",
            action="store_true",
            help="Skip vocabulary import",
        )
        parser.add_argument(
            "--vocab-limit",
            type=int,
            default=3000,
            help="Max words from frequency list (default: 3000)",
        )
        parser.add_argument(
            "--include-frequency-vocabulary",
            action="store_true",
            help="Also import the noisy frequency list (not recommended for beginners)",
        )
        parser.add_argument(
            "--graded-only",
            action="store_true",
            help="Only import bundled graded stories (no network needed)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Importing learning content...\n"))

        total = {"books": 0, "words": 0, "lessons": 0}

        if not options["skip_vocabulary"]:
            self.stdout.write("📚 Vocabulary:")
            import_core_vocabulary(stdout=self.stdout)
            if options["include_frequency_vocabulary"]:
                import_vocabulary(limit=options["vocab_limit"], stdout=self.stdout)
            total["words"] = Word.objects.count()

        self.stdout.write("\n📖 Graded stories:")
        graded = import_graded_stories(stdout=self.stdout)
        total["books"] += graded["books"]

        if not options["graded_only"] and not options["skip_gutenberg"]:
            self.stdout.write("\n🌐 Project Gutenberg (downloading books):")
            gb = import_gutenberg_books(stdout=self.stdout)
            total["books"] += gb["books"]
            if gb["errors"]:
                self.stdout.write(self.style.WARNING(f"  {gb['errors']} book(s) failed to download"))

        total["lessons"] = Lesson.objects.count()
        readings = ReadingText.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Import complete!\n"
            f"   Words:    {total['words']}\n"
            f"   Books:    {readings}\n"
            f"   Lessons:  {total['lessons']}\n"
        ))
