import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update

from .bot_app import get_bot_application

logger = logging.getLogger(__name__)


@csrf_exempt
async def telegram_webhook(request):
    if request.method != "POST":
        return HttpResponse("OK")

    secret = settings.TELEGRAM_WEBHOOK_SECRET
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return JsonResponse({"error": "Invalid webhook secret"}, status=403)

    app = get_bot_application()
    if not app:
        return JsonResponse({"error": "Bot not configured"}, status=503)

    try:
        data = json.loads(request.body)
        update = Update.de_json(data, app.bot)
        if not app.bot._initialized:
            await app.initialize()
        await app.process_update(update)
    except Exception as e:
        logger.exception("Webhook error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"ok": True})
