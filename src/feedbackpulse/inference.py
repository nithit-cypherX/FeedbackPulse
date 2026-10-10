"""The single preprocess -> predict -> label path.

Both the evaluation step and the API must call this module, so a prediction made
while measuring quality is produced the same way as one served to a caller
(docs/plans/P01-T03-system-structure.md section 4).

This module is core logic: it reads no environment variables, opens no network
connection, and talks to no cloud service. The model directory and the version
string are supplied by the caller.
"""

from dataclasses import dataclass

# Number of RoBERTa position slots reserved because of padding_idx, so the usable
# sequence length is max_position_embeddings - 2. Verified by experiment:
# total length 512 runs, 513 raises.
_POSITION_OFFSET = 2


class ModelNotReady(RuntimeError):
    """The model could not be loaded, so no prediction can be made.

    P03 maps this to a failing /ready check and a 503 from /predict rather than
    returning a made-up sentiment (docs/plans/P01-T02-api-contract.md section 4).
    """


class InvalidText(ValueError):
    """The caller's text cannot be classified. P03 maps this to 422."""


class TextTooLong(InvalidText):
    """The text exceeds the model's token limit.

    Raised instead of truncating, because P01-T02 section 3 forbids silently
    dropping the tail of a message.
    """

    def __init__(self, token_count: int, limit: int) -> None:
        super().__init__(f"text is {token_count} tokens, limit is {limit}")
        self.token_count = token_count
        self.limit = limit


@dataclass(frozen=True)
class Prediction:
    """One classification result, shaped like the success response in P01-T02 section 3."""

    sentiment: str
    score: float
    model_version: str


class SentimentClassifier:
    """Holds a loaded model and classifies one text at a time.

    Construct it once when the process starts and reuse it across requests; the
    weights are never reloaded per call (P01-T03 section 3).
    """

    def __init__(self, model, tokenizer, model_version: str | None = None) -> None:
        self._model = model
        self._tokenizer = tokenizer
        self._model_version = model_version or ""

        # Read the label names from the loaded config instead of hardcoding the
        # order, so a different revision cannot silently shift the mapping.
        self._id2label = {
            int(i): str(name) for i, name in model.config.id2label.items()
        }

        max_total = model.config.max_position_embeddings - _POSITION_OFFSET
        self._special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
        self._max_content_tokens = max_total - self._special_tokens

        # The upstream repo ships no tokenizer_config.json, so this attribute
        # arrives as a sentinel of ~1e30.
        # Anything comparing a length against it would conclude nothing is ever
        # too long. Setting it keeps a tokenizer taken from this object honest,
        # while the single source of the number stays the config above.
        tokenizer.model_max_length = max_total

    @classmethod
    def load(cls, model_dir, model_version: str | None = None) -> "SentimentClassifier":
        """Load the model from a local directory, or raise ModelNotReady."""
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
            model.eval()
            torch.set_grad_enabled(False)
        except Exception as exc:
            raise ModelNotReady(f"could not load the model from {model_dir}") from exc
        return cls(model, tokenizer, model_version)

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def max_content_tokens(self) -> int:
        """Longest accepted text in tokens, excluding the special tokens."""
        return self._max_content_tokens

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(self._id2label[i] for i in sorted(self._id2label))

    def count_tokens(self, text: str) -> int:
        """Content tokens in `text`, excluding the special tokens the model adds."""
        # No truncation: the real length is needed to reject, not to cut down.
        return len(self._tokenizer(text, add_special_tokens=False)["input_ids"])

    # ponytail: one text per call; ceiling: throughput of a single forward
    # pass per text, measured at 51ms for a short text and 184ms at the token
    # limit; revisit when: a caller needs
    # more throughput than that, such as an evaluation run outgrowing a
    # tolerable wall time; upgrade: add a batched method here rather than
    # tokenising anywhere else, so the single prediction path stays single.
    def predict(self, text: str) -> Prediction:
        """Classify one text.

        Raises InvalidText for blank input, TextTooLong past the token limit.
        """
        if not isinstance(text, str) or not text.strip():
            raise InvalidText("text must be a non-empty string")

        token_count = self.count_tokens(text)
        if token_count > self._max_content_tokens:
            # Checked before the forward pass: reaching the model with an
            # over-long sequence raises a RuntimeError that P03 could only
            # report as a 500, where P01-T02 section 4 requires a 422.
            raise TextTooLong(token_count, self._max_content_tokens)

        import torch

        encoded = self._tokenizer(text, return_tensors="pt")
        logits = self._model(**encoded).logits[0]
        probs = torch.softmax(logits, dim=-1)
        index = int(probs.argmax())
        return Prediction(
            sentiment=self._id2label[index],
            score=float(probs[index]),
            model_version=self._model_version,
        )
