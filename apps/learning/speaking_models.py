from django.db import models

from apps.users.models import CEFRLevel, LearnerProfile


class PhrasePack(models.Model):
    """Collection of phrases for shadowing / pronunciation."""

    class PackType(models.TextChoices):
        SHADOWING = "shadow", "Shadowing"
        SURVIVAL = "survival", "Survival Phrases"
        PHONETICS = "phonetics", "Phonetics"
        SMALL_TALK = "smalltalk", "Small Talk"

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    pack_type = models.CharField(max_length=20, choices=PackType.choices)
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, default=CEFRLevel.A1)
    emoji = models.CharField(max_length=10, default="🎤")
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


class ShadowPhrase(models.Model):
    pack = models.ForeignKey(PhrasePack, on_delete=models.CASCADE, related_name="phrases")
    order = models.PositiveSmallIntegerField(default=0)
    english = models.CharField(max_length=500)
    russian = models.CharField(max_length=500, blank=True)
    phonetic = models.CharField(max_length=200, blank=True)
    tip = models.TextField(blank=True, help_text="Pronunciation tip for RU speakers")
    slow_first = models.BooleanField(default=True)

    class Meta:
        ordering = ["pack", "order"]

    def __str__(self):
        return self.english[:60]


class DialogueScenario(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, default=CEFRLevel.A1)
    emoji = models.CharField(max_length=10, default="💬")
    setting = models.CharField(max_length=200, blank=True, help_text="e.g. At a cafe")
    # turns: [{role: bot|user, text, hint_ru, keywords: [], accept: []}]
    turns = models.JSONField(default=list)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "order"]

    def __str__(self):
        return self.title


class DialogueProgress(models.Model):
    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="dialogues")
    scenario = models.ForeignKey(DialogueScenario, on_delete=models.CASCADE)
    current_turn = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)
    best_score = models.FloatField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_played = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "scenario"]]


class SpeakSession(models.Model):
    """Daily speaking practice log."""

    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="speak_sessions")
    date = models.DateField()
    minutes = models.PositiveSmallIntegerField(default=0)
    phrases_practiced = models.PositiveSmallIntegerField(default=0)
    dialogues_done = models.PositiveSmallIntegerField(default=0)
    avg_pronunciation = models.FloatField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [["user", "date"]]
        ordering = ["-date"]


class PronunciationAttempt(models.Model):
    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="pronunciation_attempts")
    expected = models.CharField(max_length=500)
    spoken = models.CharField(max_length=500, blank=True)
    score = models.FloatField(default=0)
    grade = models.CharField(max_length=5, blank=True)
    source = models.CharField(max_length=30, blank=True)  # shadow / dialogue / free
    phrase = models.ForeignKey(ShadowPhrase, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
