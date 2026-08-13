import math
from datetime import timedelta

from django.utils import timezone

from .models import SRSItem


def sm2_update(item: SRSItem, quality: int) -> SRSItem:
    """
    SM-2 algorithm update.
    quality: 0-5 (0=complete blackout, 5=perfect)
    """
    if quality < 3:
        item.repetitions = 0
        item.interval_days = 1
    else:
        if item.repetitions == 0:
            item.interval_days = 1
        elif item.repetitions == 1:
            item.interval_days = 6
        else:
            item.interval_days = math.ceil(item.interval_days * item.ease_factor)
        item.repetitions += 1

    item.ease_factor = max(
        1.3,
        item.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    item.last_review = timezone.localdate()
    item.next_review = item.last_review + timedelta(days=item.interval_days)
    item.save()
    return item


def quality_from_answer(is_correct: bool, hints_used: int = 0) -> int:
    if not is_correct:
        return 1 if hints_used == 0 else 0
    if hints_used == 0:
        return 5
    if hints_used == 1:
        return 4
    return 3
