import logging

from django.conf import settings
from telegram.ext import Application

logger = logging.getLogger(__name__)

_bot_application: Application | None = None


def get_bot_application() -> Application | None:
    global _bot_application
    if _bot_application is not None:
        return _bot_application

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set")
        return None

    _bot_application = Application.builder().token(token).build()
    from .handlers import register_handlers

    register_handlers(_bot_application)
    return _bot_application


async def initialize_bot():
    app = get_bot_application()
    if app and not app.bot._initialized:
        await app.initialize()
    return app
