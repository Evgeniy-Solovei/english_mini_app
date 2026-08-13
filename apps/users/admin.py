from django.contrib import admin

from .models import LearnerProfile


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "display_name", "current_level", "total_xp", "streak_days")
    search_fields = ("telegram_id", "username", "first_name")
    list_filter = ("current_level",)
