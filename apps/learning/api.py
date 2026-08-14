import random

from ninja import NinjaAPI, Schema
from ninja.errors import HttpError

from apps.users.models import LearnerProfile
from apps.users.models import CEFRLevel

from .auth import get_user_from_request
from .models import Exercise, Lesson, LessonProgress, LevelExam, ReadingText, SRSItem, Word
from .services import advance_level_if_ready, get_dashboard_stats, record_exercise_result
from .srs import quality_from_answer, sm2_update

api = NinjaAPI(title="English Bot API", version="1.0")


class DashboardOut(Schema):
    level: str
    level_label: str
    level_progress: float
    total_xp: int
    streak_days: int
    longest_streak: int
    minutes_today: int
    daily_goal: int
    lessons_completed: int
    lessons_total: int
    due_reviews: int
    language_code: str = "ru"
    available_levels: list[str] = []
    skills: dict
    speaking: dict = {}


class LessonOut(Schema):
    id: int
    title: str
    title_ru: str
    description: str
    category: str
    level: str
    estimated_minutes: int
    xp_reward: int
    status: str
    score: float
    order: int
    track: str = "main"
    is_locked: bool = False


class ExerciseOut(Schema):
    id: int
    exercise_type: str
    question: str
    question_ru: str
    data: dict
    points: int
    skill: str
    order: int


class AnswerIn(Schema):
    answer: str


class AnswerOut(Schema):
    is_correct: bool
    correct_answer: str
    explanation: str
    xp_earned: int
    lesson_score: float
    lesson_completed: bool


class ReviewItemOut(Schema):
    id: int
    front: str
    back: str


class ReviewRateIn(Schema):
    quality: int


class ExamOut(Schema):
    level: str
    title: str
    description: str
    pass_score: float
    time_limit_minutes: int
    questions: list


class ExamSubmitIn(Schema):
    answers: dict


class ExamResultOut(Schema):
    score: float
    passed: bool
    new_level: str | None
    skill_scores: dict = {}


class WordOut(Schema):
    id: int
    english: str
    russian: str
    transcription: str
    example_sentence: str


class SettingsIn(Schema):
    language_code: str | None = None
    current_level: str | None = None
    daily_goal_minutes: int | None = None


def _require_user(request):
    user = get_user_from_request(request)
    if not user:
        raise HttpError(401, "Unauthorized")
    return user


@api.post("/settings")
def update_settings(request, payload: SettingsIn):
    user = _require_user(request)
    if payload.language_code:
        if payload.language_code not in {"ru", "en"}:
            raise HttpError(400, "Unsupported interface language")
        user.language_code = payload.language_code
    if payload.current_level:
        valid_levels = {value for value, _ in CEFRLevel.choices}
        if payload.current_level not in valid_levels:
            raise HttpError(400, "Unknown CEFR level")
        if not Lesson.objects.filter(
            level=payload.current_level, is_published=True
        ).exists():
            raise HttpError(400, "This level has no published course yet")
        user.current_level = payload.current_level
    if payload.daily_goal_minutes is not None:
        if not 5 <= payload.daily_goal_minutes <= 120:
            raise HttpError(400, "Daily goal must be between 5 and 120 minutes")
        user.daily_goal_minutes = payload.daily_goal_minutes
    user.save()
    return {
        "ok": True,
        "language_code": user.language_code,
        "current_level": user.current_level,
        "daily_goal_minutes": user.daily_goal_minutes,
    }


@api.get("/dashboard", response=DashboardOut)
def dashboard(request):
    user = _require_user(request)
    return get_dashboard_stats(user)


@api.get("/lessons", response=list[LessonOut])
def lessons(request, level: str | None = None):
    user = _require_user(request)
    level = level or user.current_level
    qs = Lesson.objects.filter(level=level, is_published=True)
    result = []
    for lesson in qs:
        prog = LessonProgress.objects.filter(user=user, lesson=lesson).first()
        result.append(
            LessonOut(
                id=lesson.id,
                title=lesson.title,
                title_ru=lesson.title_ru,
                description=lesson.description,
                category=lesson.category,
                level=lesson.level,
                estimated_minutes=lesson.estimated_minutes,
                xp_reward=lesson.xp_reward,
                status=prog.status if prog else "not_started",
                score=prog.score if prog else 0,
                order=lesson.order,
                track=_lesson_track(lesson),
                is_locked=_lesson_is_locked(user, lesson),
            )
        )
    return result


@api.get("/lessons/{lesson_id}", response=dict)
def lesson_detail(request, lesson_id: int):
    user = _require_user(request)
    try:
        lesson = Lesson.objects.get(pk=lesson_id, is_published=True)
    except Lesson.DoesNotExist:
        raise HttpError(404, "Lesson not found")
    if _lesson_is_locked(user, lesson):
        raise HttpError(403, "Complete the previous lesson first")

    prog, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    if prog.status == LessonProgress.Status.NOT_STARTED:
        prog.status = LessonProgress.Status.IN_PROGRESS
        prog.save()

    return {
        "id": lesson.id,
        "title": lesson.title,
        "title_ru": lesson.title_ru,
        "description": lesson.description,
        "content": lesson.content,
        "category": lesson.category,
        "estimated_minutes": lesson.estimated_minutes,
        "status": prog.status,
        "score": prog.score,
    }


def _lesson_track(lesson) -> str:
    return lesson.content.get(
        "track", "it" if lesson.sub_level.startswith("IT") else "main"
    )


def _lesson_is_locked(user, lesson) -> bool:
    level_order = [CEFRLevel.PRE_A1, CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1,
                   CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]
    if level_order.index(lesson.level) > level_order.index(user.current_level):
        return True
    if level_order.index(lesson.level) < level_order.index(user.current_level):
        return False
    track = _lesson_track(lesson)
    candidates = Lesson.objects.filter(
        level=lesson.level, is_published=True, order__lt=lesson.order
    ).order_by("-order")
    previous = next(
        (candidate for candidate in candidates if _lesson_track(candidate) == track),
        None,
    )
    if not previous:
        return False
    return not LessonProgress.objects.filter(
        user=user, lesson=previous, status=LessonProgress.Status.COMPLETED
    ).exists()


@api.get("/lessons/{lesson_id}/exercises", response=list[ExerciseOut])
def lesson_exercises(request, lesson_id: int):
    user = _require_user(request)
    lesson = Lesson.objects.filter(pk=lesson_id, is_published=True).first()
    if not lesson:
        raise HttpError(404, "Lesson not found")
    if _lesson_is_locked(user, lesson):
        raise HttpError(403, "Complete the previous lesson first")
    exercises = list(Exercise.objects.filter(lesson_id=lesson_id).order_by("order"))
    random.SystemRandom().shuffle(exercises)
    return [
        ExerciseOut(
            id=e.id,
            exercise_type=e.exercise_type,
            question=e.question,
            question_ru=e.question_ru,
            data=_public_exercise_data(e.data),
            points=e.points,
            skill=e.skill,
            order=e.order,
        )
        for e in exercises
    ]


def _public_exercise_data(data: dict) -> dict:
    public = {
        key: value for key, value in data.items()
        if key not in {
            "correct_answer", "alternatives", "expected_keywords",
            "srs_front", "srs_back",
        }
    }
    if isinstance(public.get("options"), list):
        public["options"] = list(public["options"])
        random.SystemRandom().shuffle(public["options"])
    return public


@api.post("/exercises/{exercise_id}/answer", response=AnswerOut)
def submit_answer(request, exercise_id: int, payload: AnswerIn):
    user = _require_user(request)
    try:
        exercise = Exercise.objects.select_related("lesson").get(pk=exercise_id)
    except Exercise.DoesNotExist:
        raise HttpError(404, "Exercise not found")
    if _lesson_is_locked(user, exercise.lesson):
        raise HttpError(403, "Complete the previous lesson first")

    correct = exercise.data.get("correct_answer", "")
    user_answer = _normalize_answer(payload.answer)
    correct_norm = _normalize_answer(str(correct))

    if exercise.exercise_type == "mc":
        is_correct = user_answer == correct_norm
    elif exercise.exercise_type in ("fill", "translate", "order"):
        alternatives = exercise.data.get("alternatives", [])
        all_valid = [correct_norm] + [_normalize_answer(str(a)) for a in alternatives]
        is_correct = user_answer in all_valid
    elif exercise.exercise_type == "speak":
        alternatives = exercise.data.get("alternatives", [])
        phrase_matches = any(
            _fuzzy_match(user_answer, _normalize_answer(str(candidate)))
            for candidate in [correct, *alternatives]
        )
        keyword_matches = _keyword_match(
            user_answer, exercise.data.get("expected_keywords", [])
        )
        is_correct = phrase_matches or keyword_matches
    elif exercise.exercise_type == "write":
        is_correct = _writing_match(
            user_answer,
            exercise.data.get("expected_keywords", []),
            exercise.data.get("min_words", 4),
        )
    else:
        is_correct = user_answer == correct_norm

    xp_earned = record_exercise_result(user, exercise, payload.answer, is_correct)

    prog = LessonProgress.objects.get(user=user, lesson=exercise.lesson)
    explanation = exercise.data.get("explanation", "")
    if exercise.exercise_type == "write" and not is_correct:
        explanation = _writing_feedback(
            user_answer,
            exercise.data.get("expected_keywords", []),
            exercise.data.get("min_words", 4),
        )

    if is_correct and exercise.data.get("srs_front"):
        SRSItem.objects.update_or_create(
            user=user,
            front=exercise.data["srs_front"],
            defaults={
                "back": exercise.data.get("srs_back", correct),
                "next_review": None,
            },
        )
    elif not is_correct and correct:
        SRSItem.objects.update_or_create(
            user=user,
            front=exercise.question[:500],
            defaults={
                "back": str(correct)[:500],
                "lesson": exercise.lesson,
                "next_review": None,
            },
        )

    return AnswerOut(
        is_correct=is_correct,
        correct_answer=str(correct),
        explanation=explanation,
        xp_earned=xp_earned,
        lesson_score=prog.score,
        lesson_completed=prog.status == LessonProgress.Status.COMPLETED,
    )


def _fuzzy_match(spoken: str, expected: str) -> bool:
    if spoken == expected:
        return True
    spoken_words = set(spoken.split())
    expected_words = set(expected.split())
    if not expected_words:
        return False
    overlap = len(spoken_words & expected_words) / len(expected_words)
    return overlap >= 0.7


def _keyword_match(spoken: str, expected_keywords: list[str]) -> bool:
    """Accept a meaningful beginner reply without requiring memorised wording."""
    if not expected_keywords:
        return False
    spoken_words = set(spoken.split())
    keywords = {_normalize_answer(str(word)) for word in expected_keywords}
    matched = len(spoken_words & keywords)
    required = max(1, (len(keywords) + 1) // 2)
    return len(spoken_words) >= 2 and matched >= required


def _writing_match(answer: str, expected_keywords: list[str], min_words: int) -> bool:
    words = answer.split()
    if len(words) < min_words:
        return False
    return _keyword_match(answer, expected_keywords) if expected_keywords else True


def _writing_feedback(answer: str, expected_keywords: list[str], min_words: int) -> str:
    words = answer.split()
    if len(words) < min_words:
        return f"Нужно минимум {min_words} английских слов; сейчас {len(words)}."
    missing = [word for word in expected_keywords if _normalize_answer(word) not in set(words)]
    if missing:
        return "Добавьте ключевую информацию: " + ", ".join(missing[:4]) + "."
    return "Проверьте порядок слов и попробуйте ещё раз."


def _normalize_answer(value: str) -> str:
    """Make beginner free-text answers tolerant to punctuation and extra spaces."""
    import re

    value = value.casefold().strip()
    value = re.sub(r"[^\w\s']", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value)


@api.get("/reviews", response=list[ReviewItemOut])
@api.get("/srs/due", response=list[ReviewItemOut])
@api.get("/srs/items", response=list[ReviewItemOut])
def due_reviews(request):
    from django.utils import timezone

    user = _require_user(request)
    today = timezone.localdate()
    items = SRSItem.objects.filter(user=user).filter(
        models_Q_next_review_lte(today)
    ).order_by("next_review", "ease_factor", "repetitions")[:20]
    return [ReviewItemOut(id=i.id, front=i.front, back=i.back) for i in items]


def models_Q_next_review_lte(today):
    from django.db.models import Q

    return Q(next_review__lte=today) | Q(next_review__isnull=True)


@api.post("/reviews/{item_id}/rate")
@api.post("/srs/{item_id}/rate")
def rate_review(request, item_id: int, payload: ReviewRateIn):
    user = _require_user(request)
    try:
        item = SRSItem.objects.get(pk=item_id, user=user)
    except SRSItem.DoesNotExist:
        raise HttpError(404, "Review item not found")
    sm2_update(item, max(0, min(5, payload.quality)))
    return {"ok": True}


@api.get("/exam/{level}", response=ExamOut)
def get_exam(request, level: str):
    _require_user(request)
    try:
        exam = LevelExam.objects.get(level=level)
    except LevelExam.DoesNotExist:
        raise HttpError(404, "Exam not found")
    questions = []
    for q in exam.questions:
        safe_q = {
            k: v for k, v in q.items()
            if k not in {"correct_answer", "alternatives", "expected_keywords"}
        }
        questions.append(safe_q)
    return ExamOut(
        level=exam.level,
        title=exam.title,
        description=exam.description,
        pass_score=exam.pass_score,
        time_limit_minutes=exam.time_limit_minutes,
        questions=questions,
    )


@api.post("/exam/{level}/submit", response=ExamResultOut)
def submit_exam(request, level: str, payload: ExamSubmitIn):
    from django.utils import timezone

    from .models import ExamAttempt

    user = _require_user(request)
    try:
        exam = LevelExam.objects.get(level=level)
    except LevelExam.DoesNotExist:
        raise HttpError(404, "Exam not found")

    total = len(exam.questions)
    correct = 0
    skill_totals = {}
    skill_correct = {}
    for i, q in enumerate(exam.questions):
        user_ans = _normalize_answer(str(payload.answers.get(str(i), "")))
        valid = [q.get("correct_answer", ""), *q.get("alternatives", [])]
        question_type = q.get("type")
        if question_type == "writing":
            answer_ok = _writing_match(
                user_ans, q.get("expected_keywords", []), q.get("min_words", 4)
            )
        elif question_type == "speaking":
            answer_ok = any(
                _fuzzy_match(user_ans, _normalize_answer(str(answer))) for answer in valid
            ) or _keyword_match(user_ans, q.get("expected_keywords", []))
        else:
            answer_ok = user_ans in {_normalize_answer(str(answer)) for answer in valid}
        skill = q.get("skill", "general")
        skill_totals[skill] = skill_totals.get(skill, 0) + 1
        if answer_ok:
            correct += 1
            skill_correct[skill] = skill_correct.get(skill, 0) + 1

    score = round(correct / max(total, 1) * 100, 1)
    passed = score >= exam.pass_score
    previously_passed = ExamAttempt.objects.filter(user=user, exam=exam, passed=True).exists()

    ExamAttempt.objects.create(
        user=user,
        exam=exam,
        score=score,
        passed=passed,
        answers=payload.answers,
        finished_at=timezone.now(),
    )

    new_level = None
    if passed:
        if not previously_passed:
            user.add_xp(100)
        new_level = advance_level_if_ready(user)

    skill_scores = {
        skill: round(skill_correct.get(skill, 0) / count * 100, 1)
        for skill, count in skill_totals.items()
    }
    return ExamResultOut(
        score=score, passed=passed, new_level=new_level, skill_scores=skill_scores
    )


@api.get("/words", response=list[WordOut])
def word_list(request, level: str | None = None, limit: int = 50, offset: int = 0):
    user = _require_user(request)
    level = level or user.current_level
    words = Word.objects.filter(level=level)[offset : offset + limit]
    return [
        WordOut(
            id=w.id,
            english=w.english,
            russian=w.russian,
            transcription=w.transcription,
            example_sentence=w.example_sentence,
        )
        for w in words
    ]


class ReadingOut(Schema):
    id: int
    title: str
    title_ru: str
    author: str
    level: str
    description: str
    cover_emoji: str
    total_words: int
    chapter_count: int
    source: str
    lesson_id: int | None


class ReadingDetailOut(ReadingOut):
    chapters: list


@api.get("/library", response=list[ReadingOut])
@api.get("/reading/texts", response=list[ReadingOut])
def library_list(request, level: str | None = None):
    _require_user(request)
    qs = ReadingText.objects.filter(is_published=True)
    if level:
        qs = qs.filter(level=level)
    return [
        ReadingOut(
            id=r.id,
            title=r.title,
            title_ru=r.title_ru,
            author=r.author,
            level=r.level,
            description=r.description,
            cover_emoji=r.cover_emoji,
            total_words=r.total_words,
            chapter_count=len(r.chapters),
            source=r.source,
            lesson_id=r.lesson_id,
        )
        for r in qs
    ]


@api.get("/library/{book_id}", response=ReadingDetailOut)
@api.get("/reading/texts/{book_id}", response=ReadingDetailOut)
def library_detail(request, book_id: int):
    _require_user(request)
    try:
        book = ReadingText.objects.get(pk=book_id, is_published=True)
    except ReadingText.DoesNotExist:
        raise HttpError(404, "Book not found")
    return ReadingDetailOut(
        id=book.id,
        title=book.title,
        title_ru=book.title_ru,
        author=book.author,
        level=book.level,
        description=book.description,
        cover_emoji=book.cover_emoji,
        total_words=book.total_words,
        chapter_count=len(book.chapters),
        source=book.source,
        lesson_id=book.lesson_id,
        chapters=[
            {"title": c.get("title", f"Chapter {i + 1}"), "word_count": c.get("word_count", 0), "index": i}
            for i, c in enumerate(book.chapters)
        ],
    )


@api.get("/library/{book_id}/chapter/{index}", response=dict)
def library_chapter(request, book_id: int, index: int):
    _require_user(request)
    try:
        book = ReadingText.objects.get(pk=book_id, is_published=True)
    except ReadingText.DoesNotExist:
        raise HttpError(404, "Book not found")
    if index < 0 or index >= len(book.chapters):
        raise HttpError(404, "Chapter not found")
    chapter = book.chapters[index]
    return {
        "book_id": book.id,
        "book_title": book.title,
        "chapter_index": index,
        "title": chapter.get("title", f"Chapter {index + 1}"),
        "text": chapter.get("text", ""),
        "text_ru": chapter.get("text_ru", ""),
        "word_count": chapter.get("word_count", 0),
    }


@api.get("/stats/content", response=dict)
def content_stats(request):
    _require_user(request)
    return {
        "words": Word.objects.count(),
        "lessons": Lesson.objects.filter(is_published=True).count(),
        "books": ReadingText.objects.filter(is_published=True).count(),
        "exercises": Exercise.objects.count(),
    }


# ─── Speaking / Shadowing / Talk ───────────────────────────────────────────

class PackOut(Schema):
    id: int
    slug: str
    title: str
    title_ru: str
    pack_type: str
    level: str
    emoji: str
    phrase_count: int


class PhraseOut(Schema):
    id: int
    order: int
    english: str
    russian: str
    phonetic: str
    tip: str


class ScenarioOut(Schema):
    id: int
    slug: str
    title: str
    title_ru: str
    description: str
    level: str
    emoji: str
    setting: str
    turn_count: int
    completed: bool
    best_score: float


@api.get("/speak/dashboard", response=dict)
def speak_dash(request):
    from apps.learning.speaking_services import speak_dashboard

    user = _require_user(request)
    return speak_dashboard(user)


@api.get("/speak/packs", response=list[PackOut])
@api.get("/shadowing/packs", response=list[PackOut])
def speak_packs(request, pack_type: str | None = None):
    from apps.learning.speaking_models import PhrasePack

    _require_user(request)
    qs = PhrasePack.objects.filter(is_published=True)
    if pack_type:
        qs = qs.filter(pack_type=pack_type)
    return [
        PackOut(
            id=p.id,
            slug=p.slug,
            title=p.title,
            title_ru=p.title_ru,
            pack_type=p.pack_type,
            level=p.level,
            emoji=p.emoji,
            phrase_count=p.phrases.count(),
        )
        for p in qs
    ]


@api.get("/speak/packs/{pack_id}/phrases", response=list[PhraseOut])
def speak_phrases(request, pack_id: int):
    from apps.learning.speaking_models import PhrasePack, ShadowPhrase

    _require_user(request)
    try:
        PhrasePack.objects.get(pk=pack_id, is_published=True)
    except PhrasePack.DoesNotExist:
        raise HttpError(404, "Pack not found")
    return [
        PhraseOut(
            id=ph.id,
            order=ph.order,
            english=ph.english,
            russian=ph.russian,
            phonetic=ph.phonetic,
            tip=ph.tip,
        )
        for ph in ShadowPhrase.objects.filter(pack_id=pack_id)
    ]


@api.post("/speak/pronounce")
def speak_pronounce(request):
    """Accept JSON {expected, spoken, phrase_id?} or multipart with audio."""
    from apps.learning.speaking_models import ShadowPhrase
    from apps.learning.speaking_services import record_pronunciation
    from apps.voice.services import assess_pronunciation, speech_to_text

    user = _require_user(request)
    acoustic_result = None

    if request.content_type and "multipart" in request.content_type:
        expected = request.POST.get("expected", "")
        spoken = request.POST.get("spoken", "")
        phrase_id = request.POST.get("phrase_id")
        if request.FILES.get("audio"):
            audio_bytes = request.FILES["audio"].read()
            acoustic_result = assess_pronunciation(audio_bytes, expected)
            if acoustic_result:
                spoken = acoustic_result.get("spoken", spoken)
            elif not spoken:
                spoken = speech_to_text(audio_bytes)
    else:
        import json

        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            body = {}
        expected = body.get("expected", "")
        spoken = body.get("spoken", "")
        phrase_id = body.get("phrase_id")

    if not expected:
        raise HttpError(400, "expected phrase required")

    phrase = None
    if phrase_id:
        phrase = ShadowPhrase.objects.filter(pk=phrase_id).first()

    return record_pronunciation(
        user, expected, spoken, source="shadow", phrase=phrase,
        acoustic_result=acoustic_result,
    )


@api.post("/speak/transcribe")
def speak_transcribe(request):
    """Authenticated transcription for open dialogue and exam answers."""
    from apps.voice.services import speech_to_text

    _require_user(request)
    audio = request.FILES.get("audio")
    if not audio:
        raise HttpError(400, "audio file required")
    return {"text": speech_to_text(audio.read())}


@api.get("/speak/dialogues", response=list[ScenarioOut])
def speak_dialogues(request):
    from apps.learning.speaking_models import DialogueProgress, DialogueScenario

    user = _require_user(request)
    result = []
    for s in DialogueScenario.objects.filter(is_published=True):
        prog = DialogueProgress.objects.filter(user=user, scenario=s).first()
        result.append(
            ScenarioOut(
                id=s.id,
                slug=s.slug,
                title=s.title,
                title_ru=s.title_ru,
                description=s.description,
                level=s.level,
                emoji=s.emoji,
                setting=s.setting,
                turn_count=len(s.turns),
                completed=prog.completed if prog else False,
                best_score=prog.best_score if prog else 0,
            )
        )
    return result


@api.get("/speak/dialogues/{scenario_id}", response=dict)
def speak_dialogue_detail(request, scenario_id: int):
    from apps.learning.speaking_models import DialogueProgress, DialogueScenario

    user = _require_user(request)
    try:
        s = DialogueScenario.objects.get(pk=scenario_id, is_published=True)
    except DialogueScenario.DoesNotExist:
        raise HttpError(404, "Scenario not found")

    prog, _ = DialogueProgress.objects.get_or_create(user=user, scenario=s)
    # Return turns without revealing accept answers fully — keep hints
    safe_turns = []
    for t in s.turns:
        safe_turns.append({
            "role": t.get("role"),
            "text": t.get("text", ""),
            "hint_ru": t.get("hint_ru", ""),
        })
    return {
        "id": s.id,
        "title": s.title,
        "title_ru": s.title_ru,
        "description": s.description,
        "emoji": s.emoji,
        "setting": s.setting,
        "level": s.level,
        "turns": safe_turns,
        "current_turn": prog.current_turn,
        "completed": prog.completed,
    }


@api.post("/speak/dialogues/{scenario_id}/reply")
def speak_dialogue_reply(request, scenario_id: int):
    import json

    from apps.learning.speaking_models import DialogueProgress, DialogueScenario
    from apps.learning.speaking_services import complete_dialogue, record_dialogue_reply
    from apps.voice.services import speech_to_text

    user = _require_user(request)
    try:
        s = DialogueScenario.objects.get(pk=scenario_id, is_published=True)
    except DialogueScenario.DoesNotExist:
        raise HttpError(404, "Scenario not found")

    if request.content_type and "multipart" in request.content_type:
        spoken = request.POST.get("spoken", "")
        turn_index = int(request.POST.get("turn_index", 0))
        if not spoken and request.FILES.get("audio"):
            spoken = speech_to_text(request.FILES["audio"].read())
    else:
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            body = {}
        spoken = body.get("spoken", "")
        turn_index = int(body.get("turn_index", 0))

    turns = s.turns
    # Find the user turn at/after turn_index
    user_turn = None
    user_turn_idx = None
    for i in range(turn_index, len(turns)):
        if turns[i].get("role") == "user":
            user_turn = turns[i]
            user_turn_idx = i
            break

    if user_turn is None:
        raise HttpError(400, "No user turn expected")

    result = record_dialogue_reply(
        user,
        spoken,
        expected_keywords=user_turn.get("keywords"),
        accept_phrases=user_turn.get("accept"),
    )

    prog, _ = DialogueProgress.objects.get_or_create(user=user, scenario=s)
    next_idx = user_turn_idx + 1
    bot_next = None
    finished = False

    if result.get("passed"):
        while next_idx < len(turns) and turns[next_idx].get("role") == "bot":
            bot_next = {
                "text": turns[next_idx].get("text", ""),
                "hint_ru": turns[next_idx].get("hint_ru", ""),
                "index": next_idx,
            }
            next_idx += 1
            break
        # peek if more user turns
        has_more_user = any(t.get("role") == "user" for t in turns[next_idx:])
        if not has_more_user:
            finished = True
            # include last bot lines
            remaining_bots = [t for t in turns[next_idx:] if t.get("role") == "bot"]
            if remaining_bots and not bot_next:
                bot_next = {
                    "text": remaining_bots[0].get("text", ""),
                    "hint_ru": remaining_bots[0].get("hint_ru", ""),
                    "index": next_idx,
                }
            complete_dialogue(user, s, result.get("score", 0))
            prog.completed = True
        prog.current_turn = next_idx
        prog.save()
    else:
        # stay on same turn
        prog.current_turn = user_turn_idx
        prog.save()
        bot_next = {
            "text": user_turn.get("retry_bot", "Please try again."),
            "hint_ru": user_turn.get("hint_ru", ""),
            "index": user_turn_idx,
        }

    return {
        **result,
        "next_bot": bot_next,
        "next_turn_index": prog.current_turn,
        "finished": finished,
        "hint_ru": user_turn.get("hint_ru", "") if not result.get("passed") else "",
    }
