"""Metric arithmetic checked against a hand-computed example.

The expected numbers below were derived by hand from the definitions of
precision, recall and F1, not by running `evaluate` and copying its output. That
is what makes them an independent check rather than a restatement of the code.

Worked example, 10 predictions over three labels:

    true negative -> negative x3, neutral x1      (support 4)
    true neutral  -> neutral x2,  positive x1     (support 3)
    true positive -> positive x1, negative x2     (support 3)

    predicted totals: negative 5, neutral 3, positive 2
    correct 6 of 10 -> accuracy 0.6

    negative: precision 3/5 = 0.6,  recall 3/4 = 0.75,  F1 = 2/3
    neutral:  precision 2/3,        recall 2/3,          F1 = 2/3
    positive: precision 1/2 = 0.5,  recall 1/3,          F1 = 0.4
"""

import pytest

from feedbackpulse.evaluation import confusion_counts, evaluate

LABELS = ("negative", "neutral", "positive")

PAIRS = (
    [("negative", "negative")] * 3
    + [("negative", "neutral")] * 1
    + [("neutral", "neutral")] * 2
    + [("neutral", "positive")] * 1
    + [("positive", "positive")] * 1
    + [("positive", "negative")] * 2
)

TWO_THIRDS = 2 / 3


def test_accuracy_matches_hand_count():
    assert evaluate(PAIRS, LABELS)["accuracy"] == pytest.approx(0.6)
    assert evaluate(PAIRS, LABELS)["correct"] == 6
    assert evaluate(PAIRS, LABELS)["total"] == 10


@pytest.mark.parametrize(
    ("label", "precision", "recall", "f1", "support"),
    [
        ("negative", 0.6, 0.75, TWO_THIRDS, 4),
        ("neutral", TWO_THIRDS, TWO_THIRDS, TWO_THIRDS, 3),
        ("positive", 0.5, 1 / 3, 0.4, 3),
    ],
)
def test_per_class_matches_hand_computation(label, precision, recall, f1, support):
    got = evaluate(PAIRS, LABELS)["per_class"][label]
    assert got["precision"] == pytest.approx(precision)
    assert got["recall"] == pytest.approx(recall)
    assert got["f1"] == pytest.approx(f1)
    assert got["support"] == support


def test_macro_averages_match_hand_computation():
    result = evaluate(PAIRS, LABELS)
    assert result["macro_f1"] == pytest.approx((TWO_THIRDS + TWO_THIRDS + 0.4) / 3)
    assert result["macro_precision"] == pytest.approx((0.6 + TWO_THIRDS + 0.5) / 3)
    assert result["macro_recall"] == pytest.approx((0.75 + TWO_THIRDS + 1 / 3) / 3)


def test_macro_f1_punishes_always_guessing_the_majority_class():
    """The reason macro-F1 is the headline metric rather than accuracy.

    With the class balance of the real evaluation set, a constant "negative"
    answer scores high on accuracy and poorly on macro-F1.
    """
    pairs = (
        [("negative", "negative")] * 627
        + [("neutral", "negative")] * 212
        + [("positive", "negative")] * 161
    )
    result = evaluate(pairs, LABELS)
    assert result["accuracy"] == pytest.approx(0.627)
    # Only the negative class scores at all: precision 627/1000, recall 627/627.
    # The other two labels have no true positives, so their F1 is 0.
    negative_f1 = 2 * 0.627 * 1.0 / (0.627 + 1.0)
    assert result["per_class"]["negative"]["f1"] == pytest.approx(negative_f1)
    assert result["per_class"]["neutral"]["f1"] == 0.0
    assert result["per_class"]["positive"]["f1"] == 0.0
    assert result["macro_f1"] == pytest.approx(negative_f1 / 3)
    assert result["macro_f1"] < result["accuracy"] / 2


def test_confusion_counts_cover_every_combination_and_sum_to_total():
    confusion = confusion_counts(PAIRS, LABELS)
    assert len(confusion) == len(LABELS) ** 2
    assert sum(confusion.values()) == len(PAIRS)


def test_label_never_predicted_gets_zero_instead_of_an_error():
    pairs = [("negative", "negative"), ("neutral", "negative")]
    got = evaluate(pairs, LABELS)["per_class"]["positive"]
    assert got == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        evaluate([], LABELS)


def test_aggregate_metrics_alone_cannot_detect_swapped_rows():
    """Why the evaluation records a per-row fingerprint as well.

    These two runs disagree on every row involved, yet every aggregate number
    matches, because the errors cancel. Comparing metrics across runs would call
    this reproducible; comparing predictions row by row would not.
    """
    first = [("negative", "neutral"), ("neutral", "negative")]
    second = [("negative", "negative"), ("neutral", "neutral")]
    assert first != second

    swapped = evaluate(first, LABELS)
    matched = evaluate(second, LABELS)
    assert swapped["accuracy"] != matched["accuracy"]

    # The case the fingerprint is really for: same counts, different rows.
    run_a = [("negative", "neutral"), ("neutral", "negative")]
    run_b = [("neutral", "negative"), ("negative", "neutral")]
    assert evaluate(run_a, LABELS)["confusion"] == evaluate(run_b, LABELS)["confusion"]
