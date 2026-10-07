"""Metrics for the evaluation step.

Pure counting and arithmetic: no file access, no model, no configuration. That
keeps the numbers checkable against a hand-computed example in the tests, which
is the independent check the shared evidence protocol asks for when a result
depends on a calculation.

Why not accuracy alone: the evaluation set is 62.7% negative, so always
answering "negative" already
scores 0.627. Macro-F1 weights every class equally, so a model that ignores the
two smaller classes cannot hide behind the majority one.
"""

from collections import Counter


def confusion_counts(pairs, labels) -> dict[tuple[str, str], int]:
    """Count (true label, predicted label) pairs for every label combination."""
    counts = Counter(pairs)
    return {(t, p): counts.get((t, p), 0) for t in labels for p in labels}


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return 0.0 for an empty denominator instead of raising.

    A label with no predictions has undefined precision. Reporting 0.0 keeps the
    macro average defined, and `support` in the per-class output shows when a
    class was too rare to read anything into its score.
    """
    return numerator / denominator if denominator else 0.0


def per_class_metrics(confusion: dict[tuple[str, str], int], labels) -> dict[str, dict]:
    """Precision, recall, F1 and support for each label."""
    result = {}
    for label in labels:
        true_positive = confusion[(label, label)]
        predicted = sum(confusion[(t, label)] for t in labels)
        actual = sum(confusion[(label, p)] for p in labels)
        precision = _safe_ratio(true_positive, predicted)
        recall = _safe_ratio(true_positive, actual)
        result[label] = {
            "precision": precision,
            "recall": recall,
            "f1": _safe_ratio(2 * precision * recall, precision + recall)
            if (precision + recall)
            else 0.0,
            "support": actual,
        }
    return result


def evaluate(pairs, labels) -> dict:
    """Build the full metric set from (true label, predicted label) pairs.

    `pairs` is consumed once, so pass a list rather than a generator if it is
    needed again afterwards.
    """
    pairs = list(pairs)
    if not pairs:
        raise ValueError("no predictions to evaluate")

    confusion = confusion_counts(pairs, labels)
    per_class = per_class_metrics(confusion, labels)
    total = len(pairs)
    correct = sum(confusion[(label, label)] for label in labels)

    return {
        "total": total,
        "correct": correct,
        "accuracy": _safe_ratio(correct, total),
        "macro_f1": sum(per_class[label]["f1"] for label in labels) / len(labels),
        "macro_precision": sum(per_class[label]["precision"] for label in labels)
        / len(labels),
        "macro_recall": sum(per_class[label]["recall"] for label in labels)
        / len(labels),
        "per_class": per_class,
        # Nested dict rather than tuple keys so the result serialises to JSON.
        "confusion": {t: {p: confusion[(t, p)] for p in labels} for t in labels},
    }
