from django.db import models
from django.utils import timezone


class CEFRLevel(models.TextChoices):
    PRE_A1 = "PRE_A1", "Pre-A1 (Alphabet)"
    A1 = "A1", "A1 — Beginner"
    A2 = "A2", "A2 — Elementary"
    B1 = "B1", "B1 — Intermediate"
    B2 = "B2", "B2 — Upper Intermediate"
    C1 = "C1", "C1 — Advanced"
    C2 = "C2", "C2 — Proficiency"


class LearnerProfile(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    language_code = models.CharField(max_length=10, default="ru")

    current_level = models.CharField(
        max_length=10, choices=CEFRLevel.choices, default=CEFRLevel.PRE_A1
    )
    total_xp = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    daily_goal_minutes = models.PositiveSmallIntegerField(default=20)
    minutes_today = models.PositiveSmallIntegerField(default=0)
    notifications_enabled = models.BooleanField(default=True)

    skill_listening = models.FloatField(default=0)
    skill_reading = models.FloatField(default=0)
    skill_writing = models.FloatField(default=0)
    skill_speaking = models.FloatField(default=0)
    skill_grammar = models.FloatField(default=0)
    skill_vocabulary = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Learner"
        verbose_name_plural = "Learners"

    def __str__(self):
        return f"{self.first_name or self.username or self.telegram_id}"

    @property
    def display_name(self):
        return self.first_name or self.username or f"User {self.telegram_id}"

    def update_streak(self):
        today = timezone.localdate()
        if self.last_activity_date == today:
            return
        if self.last_activity_date and (today - self.last_activity_date).days == 1:
            self.streak_days += 1
        elif self.last_activity_date != today:
            self.streak_days = 1
        self.longest_streak = max(self.longest_streak, self.streak_days)
        self.last_activity_date = today
        self.save(update_fields=["streak_days", "longest_streak", "last_activity_date", "updated_at"])

    def add_xp(self, amount: int):
        self.total_xp += amount
        self.save(update_fields=["total_xp", "updated_at"])

    def level_progress_percent(self) -> float:
        from apps.learning.models import Lesson, LessonProgress

        total = Lesson.objects.filter(level=self.current_level, is_published=True).count()
        if total == 0:
            return 0.0
        completed = LessonProgress.objects.filter(
            user=self,
            lesson__level=self.current_level,
            lesson__is_published=True,
            status=LessonProgress.Status.COMPLETED,
        ).count()
        return round(completed / total * 100, 1)
