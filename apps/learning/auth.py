import hashlib
import json
import hmac
import time
from urllib.parse import parse_qsl

from django.conf import settings
from django.http import HttpRequest


def validate_telegram_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData and return parsed user data."""
    if not init_data or not settings.TELEGRAM_BOT_TOKEN:
        if settings.DEBUG:
            return {"id": 0, "first_name": "Dev", "username": "devuser"}
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(
        b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Telegram recommends rejecting stale init data. This also limits replay attacks.
    auth_date = parsed.get("auth_date")
    max_age = getattr(settings, "TELEGRAM_INIT_DATA_MAX_AGE", 86400)
    if auth_date:
        try:
            if abs(time.time() - int(auth_date)) > max_age:
                return None
        except (TypeError, ValueError):
            return None

    user_data = parsed.get("user")
    if user_data:
        try:
            return json.loads(user_data)
        except (TypeError, json.JSONDecodeError):
            return None
    return None


def get_user_from_request(request: HttpRequest):
    from apps.users.models import LearnerProfile

    init_data = request.headers.get("X-Telegram-Init-Data") or request.GET.get("initData", "")
    tg_user = validate_telegram_init_data(init_data)

    if not tg_user:
        return None

    telegram_id = tg_user.get("id")
    if telegram_id is None:
        return None

    user, _ = LearnerProfile.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": tg_user.get("username", ""),
            "first_name": tg_user.get("first_name", ""),
            "last_name": tg_user.get("last_name", ""),
            "language_code": tg_user.get("language_code", "ru"),
        },
    )
    return user
