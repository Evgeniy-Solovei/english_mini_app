from django.core.management.base import BaseCommand
from django.conf import settings

from apps.bot.bot_app import get_bot_application


class Command(BaseCommand):
    help = "Set Telegram webhook URL"

    def add_arguments(self, parser):
        parser.add_argument("url", type=str, help="Webhook URL")
        parser.add_argument("--drop", action="store_true", help="Remove webhook")

    def handle(self, *args, **options):
        import asyncio

        app = get_bot_application()
        if not app:
            self.stderr.write("Bot token not configured")
            return

        async def run():
            if options["drop"]:
                await app.bot.delete_webhook()
                self.stdout.write("Webhook removed")
            else:
                url = options["url"]
                kwargs = {"url": url, "drop_pending_updates": True}
                if settings.TELEGRAM_WEBHOOK_SECRET:
                    kwargs["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
                await app.bot.set_webhook(**kwargs)
                self.stdout.write(self.style.SUCCESS(f"Webhook set: {url}"))

        asyncio.run(run())
