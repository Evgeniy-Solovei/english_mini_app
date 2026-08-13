from django.contrib import admin

from .models import (
    DailySession,
    ExamAttempt,
    Exercise,
    ExerciseAttempt,
    Lesson,
    LessonProgress,
    LevelExam,
    ReadingText,
    SRSItem,
    Word,
)
from .speaking_models import (
    DialogueScenario,
    PhrasePack,
    PronunciationAttempt,
    ShadowPhrase,
    SpeakSession,
)


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0


class PhraseInline(admin.TabularInline):
    model = ShadowPhrase
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "category", "order", "is_published")
    list_filter = ("level", "category", "is_published")
    search_fields = ("title", "title_ru")
    inlines = [ExerciseInline]


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ("english", "russian", "level", "frequency_rank")
    list_filter = ("level",)
    search_fields = ("english", "russian")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "score")
    list_filter = ("status",)


@admin.register(LevelExam)
class LevelExamAdmin(admin.ModelAdmin):
    list_display = ("level", "title", "pass_score")


@admin.register(ReadingText)
class ReadingTextAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "level", "source", "total_words", "is_published")
    list_filter = ("level", "source", "is_published")
    search_fields = ("title", "author")


@admin.register(PhrasePack)
class PhrasePackAdmin(admin.ModelAdmin):
    list_display = ("title", "pack_type", "level", "order", "is_published")
    list_filter = ("pack_type", "level")
    inlines = [PhraseInline]


@admin.register(DialogueScenario)
class DialogueScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "setting", "is_published")
    list_filter = ("level",)


admin.site.register(Exercise)
admin.site.register(ExerciseAttempt)
admin.site.register(SRSItem)
admin.site.register(ExamAttempt)
admin.site.register(DailySession)
admin.site.register(SpeakSession)
admin.site.register(PronunciationAttempt)
