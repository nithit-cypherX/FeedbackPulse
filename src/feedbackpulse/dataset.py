"""Locate and verify the pinned evaluation dataset.

Mirrors `model_files` so both pinned inputs are declared in one place each. The
values are the ones recorded in reports/P02-T02-evaluation-dataset.md; a hash
mismatch means the evaluation set changed and that report no longer applies.
"""

import csv
import hashlib
from pathlib import Path

# Version 4 as required by PROPOSAL.md section 2. kagglehub accepts the version
# in the handle; the kaggle CLI cannot select one.
DATASET_HANDLE = "crowdflower/twitter-airline-sentiment/versions/4"

LOCAL_PATH = Path("data/Tweets.csv")

# sha256 of the exact file the recorded results were produced from.
DATASET_SHA256 = "ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e"

# The whole file is the evaluation set: no sampling and no filtering, so no
# random seed is involved in choosing rows (reports/P02-T02).
TEXT_COLUMN = "text"
LABEL_COLUMN = "airline_sentiment"


class DatasetMismatch(RuntimeError):
    """The local dataset file is missing or is not the pinned one."""


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_dataset(path=LOCAL_PATH) -> Path:
    """Download the pinned version into `path` if it is not already there."""
    import shutil

    import kagglehub

    path = Path(path)
    if not path.exists():
        downloaded = Path(kagglehub.dataset_download(DATASET_HANDLE))
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(downloaded / "Tweets.csv", path)
    return path


def verify(path=LOCAL_PATH) -> str:
    """Return the file's hash, or raise if it is not the pinned dataset."""
    path = Path(path)
    if not path.exists():
        raise DatasetMismatch(f"{path} is missing; run ensure_dataset() first")
    actual = file_sha256(path)
    if actual != DATASET_SHA256:
        raise DatasetMismatch(
            f"{path} has sha256 {actual}, expected {DATASET_SHA256}; "
            "the recorded evaluation results do not apply to this file"
        )
    return actual


def read_rows(path=LOCAL_PATH):
    """Yield (text, true_label) for every row, in file order."""
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row[TEXT_COLUMN], row[LABEL_COLUMN]
