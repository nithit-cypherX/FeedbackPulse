"""Behaviour the API and the evaluation step both depend on.

The limits asserted here are the ones recorded in
reports/P02-T03-text-length-cap.md for the pinned revision. If a test fails
after changing the revision, the recorded limit is what needs rechecking.
"""

import pytest

from feedbackpulse.inference import (
    InvalidText,
    ModelNotReady,
    Prediction,
    SentimentClassifier,
    TextTooLong,
)
from feedbackpulse.model_files import ensure_model_files

MODEL_VERSION = "test-only-version"

# From reports/P02-T01-model-provenance.md and P02-T03-text-length-cap.md.
EXPECTED_LABELS = ("negative", "neutral", "positive")
EXPECTED_MAX_CONTENT_TOKENS = 510


@pytest.fixture(scope="module")
def classifier():
    """Load the pinned model once for the whole module, as a process would."""
    return SentimentClassifier.load(ensure_model_files(), MODEL_VERSION)


def test_load_failure_is_distinguishable(tmp_path):
    """P03 needs one error type to turn into a failing /ready and a 503."""
    with pytest.raises(ModelNotReady):
        SentimentClassifier.load(tmp_path / "not-a-model", MODEL_VERSION)


def test_labels_come_from_the_model_config(classifier):
    assert classifier.labels == EXPECTED_LABELS


def test_token_limit_matches_the_recorded_value(classifier):
    assert classifier.max_content_tokens == EXPECTED_MAX_CONTENT_TOKENS


@pytest.mark.parametrize(
    "text",
    [
        "My flight was delayed and nobody helped me.",
        "The staff were helpful.",
        "The flight landed at 6pm.",
    ],
)
def test_prediction_matches_the_api_contract(classifier, text):
    """Shape required by docs/plans/P01-T02-api-contract.md section 3."""
    result = classifier.predict(text)
    assert isinstance(result, Prediction)
    assert result.sentiment in EXPECTED_LABELS
    assert 0.0 <= result.score <= 1.0
    assert result.model_version == MODEL_VERSION


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_blank_text_is_rejected(classifier, text):
    with pytest.raises(InvalidText):
        classifier.predict(text)


def test_text_at_the_limit_is_accepted(classifier):
    text = _text_of_exactly(classifier, classifier.max_content_tokens)
    assert classifier.predict(text).sentiment in EXPECTED_LABELS


def test_text_one_token_over_the_limit_is_rejected_not_truncated(classifier):
    """Rejecting rather than cutting the tail, per P01-T02 section 3."""
    text = _text_of_exactly(classifier, classifier.max_content_tokens + 1)
    with pytest.raises(TextTooLong) as raised:
        classifier.predict(text)
    assert raised.value.token_count == classifier.max_content_tokens + 1
    assert raised.value.limit == classifier.max_content_tokens


def _text_of_exactly(classifier, token_count):
    """Build a text whose content tokenises to exactly `token_count` tokens.

    The count is searched rather than assumed: a repeated word does not map one
    word to one token, because the first piece carries no leading space.
    """
    words = token_count
    while classifier.count_tokens("ok " * words) > token_count:
        words -= 1
    while classifier.count_tokens("ok " * words) < token_count:
        words += 1
    text = "ok " * words
    assert classifier.count_tokens(text) == token_count
    return text
