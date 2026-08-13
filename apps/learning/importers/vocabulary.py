import json
import logging
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from apps.learning.data.translations_ru import TRANSLATIONS_RU
from apps.learning.models import Word
from apps.users.models import CEFRLevel

logger = logging.getLogger(__name__)

FREQUENCY_URL = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt"
LOCAL_FREQUENCY = Path(__file__).resolve().parent.parent / "data" / "google-10000-english.txt"

LEVEL_BY_RANK = [
    (500, CEFRLevel.A1),
    (1500, CEFRLevel.A2),
    (3500, CEFRLevel.B1),
    (6000, CEFRLevel.B2),
    (10000, CEFRLevel.C1),
]


def _level_for_rank(rank: int) -> str:
    for threshold, level in LEVEL_BY_RANK:
        if rank <= threshold:
            return level
    return CEFRLevel.C2


def download_frequency_list() -> list[str]:
    if LOCAL_FREQUENCY.exists():
        text = LOCAL_FREQUENCY.read_text(encoding="utf-8")
        return [line.strip().lower() for line in text.splitlines() if line.strip()]

    req = urllib.request.Request(
        FREQUENCY_URL,
        headers={"User-Agent": "EnglishJourneyBot/1.0"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            text = resp.read().decode("utf-8")
        return [line.strip().lower() for line in text.splitlines() if line.strip()]
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as e:
        logger.warning("Could not download frequency list: %s", e)
        return list(TRANSLATIONS_RU.keys())


def import_vocabulary(limit: int = 3000, stdout=None) -> dict:
    words = download_frequency_list()[:limit]
    stats = {"imported": 0, "with_translation": 0, "skipped": 0}

    for rank, english in enumerate(words, 1):
        english = english.strip().lower()
        if not english or len(english) < 2:
            stats["skipped"] += 1
            continue

        russian = TRANSLATIONS_RU.get(english, TRANSLATIONS_RU.get(english.capitalize(), ""))
        level = _level_for_rank(rank)

        _, created = Word.objects.update_or_create(
            english=english,
            defaults={
                "russian": russian or english,
                "transcription": "",
                "level": level,
                "frequency_rank": rank,
                "part_of_speech": "",
                "example_sentence": f"The word is «{english}».",
                "tags": ["frequency", "auto-import"],
            },
        )
        if created:
            stats["imported"] += 1
        if russian:
            stats["with_translation"] += 1

    if stdout:
        stdout.write(
            f"  Vocabulary: {stats['imported']} new, "
            f"{stats['with_translation']} with RU translation, "
            f"total in DB: {Word.objects.count()}\n"
        )

    return stats


def import_core_vocabulary(stdout=None) -> dict:
    """Import curated translations (always has RU)."""
    stats = {"imported": 0}
    for rank, (english, russian) in enumerate(TRANSLATIONS_RU.items(), 1):
        english_clean = english.strip().lower()
        Word.objects.update_or_create(
            english=english_clean,
            defaults={
                "russian": russian,
                "level": _level_for_rank(rank),
                "frequency_rank": rank,
                "tags": ["curated"],
                "example_sentence": f"Example: {english_clean}.",
            },
        )
        stats["imported"] += 1

    if stdout:
        stdout.write(f"  Core vocabulary: {stats['imported']} words\n")
    return stats
