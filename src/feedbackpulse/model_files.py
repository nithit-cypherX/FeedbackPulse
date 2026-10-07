"""Locate the pinned model files.

Separated from `inference` so the core classifier never downloads anything or
reads configuration itself, per the core / configuration / cloud-adapter split
agreed in docs/plans/P01-T03-system-structure.md section 4.

The revision and file list are the ones already verified against the pinned
model. Changing either invalidates that verification.
"""

from pathlib import Path

MODEL_REPO = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# Commit SHA, not a moving tag: PROPOSAL.md section 2 requires a pinned revision
# and a tag would let the weights change under a recorded evaluation result.
MODEL_REVISION = "3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7"

# tf_model.h5 is TensorFlow weights this project never loads, so it is excluded
# to avoid a ~500 MB download. Offline reuse must pass this same list.
MODEL_FILES = [
    "config.json",
    "pytorch_model.bin",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "README.md",
]


def ensure_model_files(cache_dir: str | None = None) -> Path:
    """Return the local directory holding the pinned revision, downloading it if needed."""
    from huggingface_hub import snapshot_download

    return Path(
        snapshot_download(
            MODEL_REPO,
            revision=MODEL_REVISION,
            allow_patterns=MODEL_FILES,
            cache_dir=cache_dir,
        )
    )
