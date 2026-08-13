from django.utils import timezone

from apps.learning.speaking_models import PronunciationAttempt, SpeakSession
from apps.users.models import LearnerProfile
from apps.voice.services import compare_pronunciation, evaluate_free_speech


SPEAK_DAILY_GOAL_MINUTES = 10


def get_or_create_speak_session(user: LearnerProfile) -> SpeakSession:
    today = timezone.localdate()
    session, _ = SpeakSession.objects.get_or_create(user=user, date=today)
    return session


def record_pronunciation(
    user: LearnerProfile,
    expected: str,
    spoken: str,
    source: str = "shadow",
    phrase=None,
    acoustic_result: dict | None = None,
) -> dict:
    result = acoustic_result or compare_pronunciation(spoken, expected)
    PronunciationAttempt.objects.create(
        user=user,
        expected=expected,
        spoken=spoken,
        score=result["score"],
        grade=result.get("grade", ""),
        source=source,
        phrase=phrase,
    )

    session = get_or_create_speak_session(user)
    n = session.phrases_practiced
    session.avg_pronunciation = round(
        (session.avg_pronunciation * n + result["score"]) / (n + 1), 1
    )
    session.phrases_practiced = n + 1
    session.minutes = min(120, session.minutes + 1)
    xp = 8 if result["passed"] else 2
    if result["score"] >= 95:
        xp = 15
    session.xp_earned += xp
    session.save()

    user.add_xp(xp)
    user.update_streak()
    # bump speaking skill
    delta = 2.0 if result["passed"] else 0.3
    user.skill_speaking = min(100.0, round(user.skill_speaking + delta, 1))
    user.skill_listening = min(100.0, round(user.skill_listening + 0.5, 1))
    user.minutes_today = max(user.minutes_today, session.minutes)
    user.save(update_fields=["skill_speaking", "skill_listening", "minutes_today", "updated_at"])

    result["xp_earned"] = xp
    result["speak_minutes_today"] = session.minutes
    result["speak_goal"] = SPEAK_DAILY_GOAL_MINUTES
    result["phrases_today"] = session.phrases_practiced
    return result


def record_dialogue_reply(
    user: LearnerProfile,
    spoken: str,
    expected_keywords: list[str] | None = None,
    accept_phrases: list[str] | None = None,
) -> dict:
    # If accept phrases provided, score against best match
    if accept_phrases:
        best = None
        for phrase in accept_phrases:
            r = compare_pronunciation(spoken, phrase)
            if best is None or r["score"] > best["score"]:
                best = r
                best["matched_phrase"] = phrase
        result = best
        result["english_ok"] = True
    else:
        result = evaluate_free_speech(spoken, expected_keywords)

    session = get_or_create_speak_session(user)
    session.minutes = min(120, session.minutes + 1)
    xp = 10 if result.get("passed") else 3
    session.xp_earned += xp
    session.save()
    user.add_xp(xp)
    user.update_streak()
    if result.get("passed"):
        user.skill_speaking = min(100.0, round(user.skill_speaking + 1.5, 1))
        user.save(update_fields=["skill_speaking", "updated_at"])

    result["xp_earned"] = xp
    result["speak_minutes_today"] = session.minutes
    result["speak_goal"] = SPEAK_DAILY_GOAL_MINUTES
    return result


def complete_dialogue(user: LearnerProfile, scenario, score: float):
    from apps.learning.speaking_models import DialogueProgress

    prog, _ = DialogueProgress.objects.get_or_create(user=user, scenario=scenario)
    was_completed = prog.completed
    prog.completed = True
    prog.attempts += 1
    prog.best_score = max(prog.best_score, score)
    prog.current_turn = 0
    prog.save()

    if not was_completed:
        session = get_or_create_speak_session(user)
        session.dialogues_done += 1
        session.xp_earned += 40
        session.minutes = min(120, session.minutes + 3)
        session.save()
        user.add_xp(40)
        user.skill_speaking = min(100.0, round(user.skill_speaking + 3, 1))
        user.save(update_fields=["skill_speaking", "updated_at"])


def speak_dashboard(user: LearnerProfile) -> dict:
    session = get_or_create_speak_session(user)
    from apps.learning.speaking_models import DialogueProgress, PhrasePack

    return {
        "speak_minutes_today": session.minutes,
        "speak_goal": SPEAK_DAILY_GOAL_MINUTES,
        "phrases_today": session.phrases_practiced,
        "dialogues_today": session.dialogues_done,
        "avg_pronunciation": session.avg_pronunciation,
        "speak_streak_ok": session.minutes >= SPEAK_DAILY_GOAL_MINUTES,
        "packs_count": PhrasePack.objects.filter(is_published=True).count(),
        "dialogues_completed": DialogueProgress.objects.filter(user=user, completed=True).count(),
        "skill_speaking": user.skill_speaking,
    }


def next_bot_reply(turn: dict) -> dict:
    """Return bot line for a dialogue turn."""
    return {
        "role": "bot",
        "text": turn.get("text", ""),
        "hint_ru": turn.get("hint_ru", ""),
    }
