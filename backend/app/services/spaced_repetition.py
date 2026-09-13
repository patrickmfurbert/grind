from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Review:
    next_review: datetime
    interval_days: int
    ease_factor: float
    repetitions: int


def schedule_review(score: int, interval_days: int = 1, ease_factor: float = 2.5, repetitions: int = 0) -> Review:
    if not 0 <= score <= 5:
        raise ValueError("score must be between 0 and 5")
    if score < 3:
        repetitions, interval_days = 0, 1
    else:
        repetitions += 1
        interval_days = 1 if repetitions == 1 else 6 if repetitions == 2 else round(interval_days * ease_factor)
    ease_factor = max(1.3, ease_factor + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)))
    return Review(datetime.now(UTC) + timedelta(days=interval_days), interval_days, ease_factor, repetitions)
