from django.utils import timezone

from apps.users.models import CEFRLevel, LearnerProfile

from .models import DailySession, ExerciseAttempt, LessonProgress


LEVEL_ORDER = [
    CEFRLevel.PRE_A1,
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
    CEFRLevel.C2,
]

SKILL_MAP = {
    "alphabet": "skill_reading",
    "vocabulary": "skill_vocabulary",
    "grammar": "skill_grammar",
    "reading": "skill_reading",
    "listening": "skill_listening",
    "speaking": "skill_speaking",
    "writing": "skill_writing",
    "dialogue": "skill_speaking",
}


def calculate_level_score(user: LearnerProfile, level: str) -> float:
    from .models import Lesson

    lessons = Lesson.objects.filter(level=level, is_published=True)
    total = lessons.count()
    if total == 0:
        return 0.0
    weighted = sum(
        LessonProgress.objects.filter(user=user, lesson=lesson)
        .values_list("score", flat=True)
        .first()
        or 0
        for lesson in lessons
    )
    return round(weighted / total, 1)


def update_skill(user: LearnerProfile, skill: str, delta: float):
    field = SKILL_MAP.get(skill)
    if not field:
        return
    current = getattr(user, field, 0)
    new_val = min(100.0, max(0.0, current + delta))
    setattr(user, field, round(new_val, 1))
    user.save(update_fields=[field, "updated_at"])


def record_exercise_result(user, exercise, answer: str, is_correct: bool) -> int:
    already_passed = ExerciseAttempt.objects.filter(
        user=user, exercise=exercise, is_correct=True
    ).exists()

    score = exercise.points if is_correct else 0
    ExerciseAttempt.objects.create(
        user=user,
        exercise=exercise,
        answer=answer,
        is_correct=is_correct,
        score=score,
    )

    xp_earned = 0
    if is_correct:
        if not already_passed:
            user.add_xp(exercise.points)
            xp_earned += exercise.points
        update_skill(user, exercise.skill, 1.5)
    else:
        update_skill(user, exercise.skill, -0.5)

    progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=exercise.lesson)
    progress.attempts += 1
    if progress.status == LessonProgress.Status.NOT_STARTED:
        progress.status = LessonProgress.Status.IN_PROGRESS

    lesson_exercises = exercise.lesson.exercises.count()
    correct_count = ExerciseAttempt.objects.filter(
        user=user, exercise__lesson=exercise.lesson, is_correct=True
    ).values("exercise_id").distinct().count()

    progress.score = round(correct_count / max(lesson_exercises, 1) * 100, 1)

    was_completed = progress.status == LessonProgress.Status.COMPLETED
    if progress.score >= 100 and not was_completed:
        progress.status = LessonProgress.Status.COMPLETED
        progress.completed_at = timezone.now()
        user.add_xp(exercise.lesson.xp_reward)
        xp_earned += exercise.lesson.xp_reward
        daily_lesson_completed = True
    else:
        daily_lesson_completed = False

    progress.save()
    _update_daily_session(user, xp_earned, daily_lesson_completed)
    user.update_streak()
    return xp_earned


def _update_daily_session(user, xp: int, lesson_completed: bool = False):
    today = timezone.localdate()
    session, _ = DailySession.objects.get_or_create(user=user, date=today)
    session.xp_earned += xp
    session.exercises_done += 1
    if lesson_completed:
        session.lessons_completed += 1
    session.minutes_spent = min(session.minutes_spent + 2, 120)
    session.save()
    user.minutes_today = session.minutes_spent
    user.save(update_fields=["minutes_today", "updated_at"])


def advance_level_if_ready(user: LearnerProfile) -> str | None:
    current_idx = LEVEL_ORDER.index(user.current_level)
    if current_idx >= len(LEVEL_ORDER) - 1:
        return None

    from .models import Lesson

    next_level = LEVEL_ORDER[current_idx + 1]
    if not Lesson.objects.filter(level=next_level, is_published=True).exists():
        return None

    score = calculate_level_score(user, user.current_level)
    if score < 85:
        return None

    from .models import ExamAttempt, LevelExam

    try:
        exam = LevelExam.objects.get(level=user.current_level)
    except LevelExam.DoesNotExist:
        exam = None

    if exam:
        passed = ExamAttempt.objects.filter(user=user, exam=exam, passed=True).exists()
        if not passed:
            return None

    user.current_level = next_level
    user.save(update_fields=["current_level", "updated_at"])
    return user.current_level


def get_dashboard_stats(user: LearnerProfile) -> dict:
    from .models import Lesson, SRSItem

    today = timezone.localdate()
    due_reviews = SRSItem.objects.filter(user=user, next_review__lte=today).count()
    total_lessons = Lesson.objects.filter(level=user.current_level, is_published=True).count()
    published_levels = set(
        Lesson.objects.filter(is_published=True).values_list("level", flat=True)
    )
    completed = LessonProgress.objects.filter(
        user=user,
        lesson__level=user.current_level,
        status=LessonProgress.Status.COMPLETED,
    ).count()

    return {
        "level": user.current_level,
        "level_label": user.get_current_level_display(),
        "level_progress": user.level_progress_percent(),
        "total_xp": user.total_xp,
        "streak_days": user.streak_days,
        "longest_streak": user.longest_streak,
        "minutes_today": user.minutes_today,
        "daily_goal": user.daily_goal_minutes,
        "lessons_completed": completed,
        "lessons_total": total_lessons,
        "due_reviews": due_reviews,
        "language_code": user.language_code,
        "available_levels": [level for level in LEVEL_ORDER if level in published_levels],
        "skills": {
            "listening": user.skill_listening,
            "reading": user.skill_reading,
            "writing": user.skill_writing,
            "speaking": user.skill_speaking,
            "grammar": user.skill_grammar,
            "vocabulary": user.skill_vocabulary,
        },
        "speaking": _speak_stats(user),
    }


def _speak_stats(user: LearnerProfile) -> dict:
    try:
        from apps.learning.speaking_services import speak_dashboard

        return speak_dashboard(user)
    except Exception:
        return {
            "speak_minutes_today": 0,
            "speak_goal": 10,
            "phrases_today": 0,
            "dialogues_today": 0,
            "avg_pronunciation": 0,
            "speak_streak_ok": False,
        }
