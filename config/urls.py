from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.bot.views import telegram_webhook
from apps.learning.api import api as learning_api
from apps.voice import views as voice_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", learning_api.urls),
    path("bot/webhook/", telegram_webhook, name="telegram_webhook"),
    path("voice/tts/", voice_views.tts_view, name="voice_tts"),
    path("voice/stt/", voice_views.stt_view, name="voice_stt"),
    path("voice/check/", voice_views.pronunciation_check, name="voice_check"),
    path("miniapp/", include("apps.learning.miniapp_urls")),
    path("", RedirectView.as_view(url="/miniapp/", permanent=False)),
]
