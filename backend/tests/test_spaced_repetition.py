import pytest

from backend.app.services.spaced_repetition import schedule_review


def test_first_successful_review_sets_interval_to_one_day():
    review = schedule_review(score=4)
    assert review.interval_days == 1
    assert review.repetitions == 1


def test_second_successful_review_sets_interval_to_six_days():
    review = schedule_review(score=4, interval_days=1, ease_factor=2.5, repetitions=1)
    assert review.interval_days == 6
    assert review.repetitions == 2


def test_third_successful_review_multiplies_interval_by_ease_factor():
    review = schedule_review(score=4, interval_days=6, ease_factor=2.5, repetitions=2)
    assert review.interval_days == round(6 * 2.5)
    assert review.repetitions == 3


def test_failing_score_resets_repetitions_and_interval():
    review = schedule_review(score=1, interval_days=20, ease_factor=2.8, repetitions=5)
    assert review.repetitions == 0
    assert review.interval_days == 1


def test_ease_factor_has_a_floor_of_1_3():
    review = schedule_review(score=0, interval_days=1, ease_factor=1.3, repetitions=0)
    assert review.ease_factor == pytest.approx(1.3)


@pytest.mark.parametrize("score", [-1, 6])
def test_invalid_score_raises_value_error(score):
    with pytest.raises(ValueError):
        schedule_review(score=score)
