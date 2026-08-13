from django.core.management.base import BaseCommand

from apps.bot.bot_app import get_bot_application
from apps.bot.handlers import register_handlers


class Command(BaseCommand):
    help = "Run Telegram bot in polling mode (for local development)"

    def handle(self, *args, **options):
        app = get_bot_application()
        if not app:
            self.stderr.write(self.style.ERROR("Set TELEGRAM_BOT_TOKEN in .env"))
            return

        register_handlers(app)
        self.stdout.write(self.style.SUCCESS("Starting bot in polling mode..."))
        app.run_polling(drop_pending_updates=True)
