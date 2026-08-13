from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Download Gutenberg book files into apps/learning/data/books/"

    def handle(self, *args, **options):
        from apps.learning.data.download_books import IDS, download

        self.stdout.write("Downloading Gutenberg books...")
        ok = 0
        for book_id in IDS:
            if download(book_id):
                ok += 1
        self.stdout.write(self.style.SUCCESS(f"Done: {ok}/{len(IDS)} books saved"))
