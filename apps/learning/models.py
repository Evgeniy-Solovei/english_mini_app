from django.db import models

from apps.users.models import CEFRLevel, LearnerProfile


class SkillCategory(models.TextChoices):
    ALPHABET = "alphabet", "Alphabet & Phonetics"
    VOCABULARY = "vocabulary", "Vocabulary"
    GRAMMAR = "grammar", "Grammar"
    READING = "reading", "Reading"
    LISTENING = "listening", "Listening"
    SPEAKING = "speaking", "Speaking"
    WRITING = "writing", "Writing"
    DIALOGUE = "dialogue", "Dialogues"


class Lesson(models.Model):
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, db_index=True)
    sub_level = models.CharField(max_length=10, blank=True, help_text="e.g. A1.1")
    order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=SkillCategory.choices)
    content = models.JSONField(default=dict, help_text="Structured lesson blocks")
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    xp_reward = models.PositiveSmallIntegerField(default=20)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "order"]
        unique_together = [["level", "order"]]

    def __str__(self):
        return f"[{self.level}] {self.title}"


class Word(models.Model):
    english = models.CharField(max_length=200, db_index=True)
    russian = models.CharField(max_length=200)
    transcription = models.CharField(max_length=200, blank=True)
    part_of_speech = models.CharField(max_length=50, blank=True)
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, default=CEFRLevel.A1)
    example_sentence = models.TextField(blank=True)
    example_translation = models.TextField(blank=True)
    audio_url = models.CharField(max_length=500, blank=True)
    frequency_rank = models.PositiveIntegerField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["frequency_rank", "english"]

    def __str__(self):
        return self.english


class Exercise(models.Model):
    class ExerciseType(models.TextChoices):
        MULTIPLE_CHOICE = "mc", "Multiple Choice"
        FILL_BLANK = "fill", "Fill in the Blank"
        TRANSLATE = "translate", "Translation"
        MATCH = "match", "Matching"
        LISTEN = "listen", "Listening"
        SPEAK = "speak", "Speaking"
        READ = "read", "Reading Comprehension"
        ORDER = "order", "Word Order"
        WRITE = "write", "Guided Writing"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="exercises")
    order = models.PositiveSmallIntegerField(default=0)
    exercise_type = models.CharField(max_length=10, choices=ExerciseType.choices)
    question = models.TextField()
    question_ru = models.TextField(blank=True)
    data = models.JSONField(default=dict, help_text="options, correct_answer, hints, audio_text")
    points = models.PositiveSmallIntegerField(default=5)
    skill = models.CharField(max_length=20, choices=SkillCategory.choices, default=SkillCategory.VOCABULARY)

    class Meta:
        ordering = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} — Q{self.order}"


class LessonProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        REVIEW = "review", "Needs Review"

    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    score = models.FloatField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "lesson"]]

    def __str__(self):
        return f"{self.user} — {self.lesson}"


class ExerciseAttempt(models.Model):
    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="attempts")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SRSItem(models.Model):
    """Spaced repetition item (SM-2 algorithm)."""

    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="srs_items")
    word = models.ForeignKey(Word, on_delete=models.CASCADE, null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    front = models.CharField(max_length=500)
    back = models.CharField(max_length=500)

    ease_factor = models.FloatField(default=2.5)
    interval_days = models.PositiveIntegerField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    next_review = models.DateField(null=True, blank=True)
    last_review = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [["user", "front"]]

    def __str__(self):
        return f"{self.front} → {self.back}"


class LevelExam(models.Model):
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_score = models.FloatField(default=70.0)
    time_limit_minutes = models.PositiveSmallIntegerField(default=30)
    questions = models.JSONField(default=list, help_text="List of exam question objects")

    def __str__(self):
        return f"Exam {self.level}"


class ExamAttempt(models.Model):
    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="exam_attempts")
    exam = models.ForeignKey(LevelExam, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class DailySession(models.Model):
    user = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField()
    minutes_spent = models.PositiveSmallIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)
    lessons_completed = models.PositiveSmallIntegerField(default=0)
    exercises_done = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [["user", "date"]]
        ordering = ["-date"]


class ReadingText(models.Model):
    class Source(models.TextChoices):
        GUTENBERG = "gutenberg", "Project Gutenberg"
        VOA = "voa", "VOA Learning English"
        MANUAL = "manual", "Manual"
        GRADED = "graded", "Graded Reader"
        ENGLISH_JOURNEY_ORIGINAL = "english_journey_original", "English Journey Original"

    title = models.CharField(max_length=300)
    title_ru = models.CharField(max_length=300, blank=True)
    author = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUAL)
    source_id = models.CharField(max_length=50, blank=True, db_index=True)
    level = models.CharField(max_length=10, choices=CEFRLevel.choices, db_index=True)
    description = models.TextField(blank=True)
    cover_emoji = models.CharField(max_length=10, default="📖")
    chapters = models.JSONField(default=list, help_text="[{title, text, word_count}]")
    total_words = models.PositiveIntegerField(default=0)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="reading_texts")
    is_published = models.BooleanField(default=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level", "title"]
        unique_together = [["source", "source_id"]]

    def __str__(self):
        return f"{self.title} ({self.level})"


# Speaking / conversation models
from apps.learning.speaking_models import (  # noqa: E402,F401
    DialogueProgress,
    DialogueScenario,
    PhrasePack,
    PronunciationAttempt,
    ShadowPhrase,
    SpeakSession,
)
