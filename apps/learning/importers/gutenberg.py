import logging
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from apps.learning.data.gutenberg_catalog import GUTENBERG_CATALOG, GRADED_STORIES
from apps.learning.importers.text_utils import (
    extract_vocabulary_from_text,
    split_into_chapters,
    strip_gutenberg_boilerplate,
)
from apps.learning.models import Exercise, Lesson, ReadingText, SkillCategory, Word
from apps.users.models import CEFRLevel

logger = logging.getLogger(__name__)

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_URL_HTTP = "http://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
LOCAL_BOOKS_DIR = Path(__file__).resolve().parent.parent / "data" / "books"
USER_AGENT = "EnglishJourneyBot/1.0 (language-learning; contact: local)"


def _read_local_book(book_id: str) -> str | None:
    for name in (f"pg{book_id}.txt", f"{book_id}.txt"):
        path = LOCAL_BOOKS_DIR / name
        if path.exists():
            for encoding in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    return path.read_text(encoding=encoding)
                except UnicodeDecodeError:
                    continue
            return path.read_text(encoding="utf-8", errors="replace")
    return None


def download_gutenberg(book_id: str) -> str | None:
    local = _read_local_book(book_id)
    if local:
        return local

    urls = [GUTENBERG_URL.format(id=book_id), GUTENBERG_URL_HTTP.format(id=book_id)]
    ctx = ssl.create_default_context()

    for url in urls:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
                raw = resp.read()
            for encoding in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as e:
            logger.warning("Download failed %s: %s", url, e)

    return None


def import_gutenberg_books(stdout=None, create_lessons=False) -> dict:
    stats = {"books": 0, "chapters": 0, "lessons": 0, "exercises": 0, "errors": 0}

    for book in GUTENBERG_CATALOG:
        if stdout:
            stdout.write(f"  Downloading: {book['title']}...")

        raw = download_gutenberg(book["id"])
        if not raw:
            stats["errors"] += 1
            if stdout:
                stdout.write(" FAILED\n")
            continue

        cleaned = strip_gutenberg_boilerplate(raw)
        chapters = split_into_chapters(cleaned, max_words=700)
        if not chapters:
            stats["errors"] += 1
            if stdout:
                stdout.write(" NO CHAPTERS\n")
            continue

        total_words = sum(c["word_count"] for c in chapters)
        reading, created = ReadingText.objects.update_or_create(
            source=ReadingText.Source.GUTENBERG,
            source_id=book["id"],
            defaults={
                "title": book["title"],
                "title_ru": book.get("title_ru", ""),
                "author": book["author"],
                "level": book["level"],
                "description": book["description"],
                "cover_emoji": book.get("emoji", "📖"),
                "chapters": chapters[:30],
                "total_words": total_words,
                "is_published": True,
            },
        )

        lesson_stats = _create_reading_lessons(reading, chapters[:8]) if create_lessons else {"lessons": 0, "exercises": 0}
        stats["books"] += 1
        stats["chapters"] += len(chapters[:30])
        stats["lessons"] += lesson_stats["lessons"]
        stats["exercises"] += lesson_stats["exercises"]

        if stdout:
            stdout.write(f" OK ({len(chapters)} chapters, {total_words} words)\n")

    return stats


def import_graded_stories(stdout=None, create_lessons=False) -> dict:
    stats = {"books": 0, "chapters": 0, "lessons": 0, "exercises": 0}

    for story in GRADED_STORIES:
        chapters = split_into_chapters(story["text"], max_words=500)
        if not chapters:
            chapters = [{"title": story["title"], "text": story["text"], "word_count": len(story["text"].split())}]

        reading, _ = ReadingText.objects.update_or_create(
            source=ReadingText.Source.GRADED,
            source_id=story["id"],
            defaults={
                "title": story["title"],
                "title_ru": story.get("title_ru", ""),
                "author": story["author"],
                "level": story["level"],
                "description": story["description"],
                "cover_emoji": story.get("emoji", "📖"),
                "chapters": chapters,
                "total_words": sum(c["word_count"] for c in chapters),
                "is_published": True,
            },
        )

        lesson_stats = _create_reading_lessons(reading, chapters) if create_lessons else {"lessons": 0, "exercises": 0}
        stats["books"] += 1
        stats["chapters"] += len(chapters)
        stats["lessons"] += lesson_stats["lessons"]
        stats["exercises"] += lesson_stats["exercises"]

        if stdout:
            stdout.write(f"  Graded: {story['title']} ({len(chapters)} parts)\n")

    return stats


def _create_reading_lessons(reading: ReadingText, chapters: list[dict]) -> dict:
    stats = {"lessons": 0, "exercises": 0}
    base_order = _next_lesson_order(reading.level)

    for i, chapter in enumerate(chapters[:6]):
        lesson_title = f"Reading: {reading.title} — {chapter['title'][:60]}"
        lesson, _ = Lesson.objects.update_or_create(
            level=reading.level,
            title=lesson_title,
            defaults={
                "title_ru": f"Чтение: {reading.title_ru or reading.title}",
                "description": reading.description,
                "category": SkillCategory.READING,
                "content": {
                    "blocks": [
                        {"type": "text", "title": chapter["title"], "body": f"📖 {reading.author}"},
                        {"type": "reading", "title": "Text", "body": chapter["text"][:4000]},
                    ],
                    "reading_id": reading.id,
                    "chapter_index": i,
                },
                "estimated_minutes": max(10, chapter["word_count"] // 50),
                "xp_reward": 30,
                "order": base_order + i,
                "is_published": True,
            },
        )

        if i == 0:
            reading.lesson = lesson
            reading.save(update_fields=["lesson"])

        ex_count = _generate_reading_exercises(lesson, chapter["text"])
        stats["lessons"] += 1
        stats["exercises"] += ex_count

    return stats


def _next_lesson_order(level: str) -> int:
    last = Lesson.objects.filter(level=level).order_by("-order").first()
    return (last.order + 10) if last else 100


def _generate_reading_exercises(lesson: Lesson, text: str) -> int:
    Exercise.objects.filter(lesson=lesson).delete()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 5]
    count = 0

    if sentences:
        first = sentences[0]
        words = first.split()
        if len(words) > 4:
            blank_word = words[3].strip(".,!?;:'\"")
            masked = words.copy()
            masked[3] = "______"
            Exercise.objects.create(
                lesson=lesson,
                order=1,
                exercise_type=Exercise.ExerciseType.FILL_BLANK,
                question=f"Fill in the blank: {' '.join(masked[:12])}",
                question_ru="Заполните пропуск в предложении из текста",
                data={"correct_answer": blank_word.lower(), "alternatives": [blank_word, blank_word.capitalize()]},
                points=5,
                skill=SkillCategory.READING,
            )
            count += 1

    vocab = extract_vocabulary_from_text(text, limit=5)
    for j, word in enumerate(vocab[:3], start=2):
        Exercise.objects.create(
            lesson=lesson,
            order=j,
            exercise_type=Exercise.ExerciseType.TRANSLATE,
            question=f"What does the word «{word}» mean in context?",
            question_ru=f"Что означает слово «{word}»?",
            data={
                "correct_answer": word,
                "alternatives": [word.capitalize()],
                "explanation": f"The word «{word}» appears in this text.",
                "srs_front": word,
                "srs_back": "",
            },
            points=5,
            skill=SkillCategory.VOCABULARY,
        )
        count += 1

    if len(sentences) >= 2:
        Exercise.objects.create(
            lesson=lesson,
            order=count + 1,
            exercise_type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            question="What is this text mainly about?",
            question_ru="О чём в основном этот текст?",
            data={
                "options": [
                    sentences[0][:80],
                    "Something completely different",
                    "A scientific report",
                    "A cooking recipe",
                ],
                "correct_answer": sentences[0][:80],
            },
            points=10,
            skill=SkillCategory.READING,
        )
        count += 1

    return count
