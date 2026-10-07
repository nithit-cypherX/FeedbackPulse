"""Run the evaluation step: predict every row, then report the metrics.

Deliberately calls `SentimentClassifier.predict` one text at a time rather than
tokenising here, so the numbers come from the same path the API will serve
(docs/plans/P01-T03-system-structure.md section 4).

Run with:  PYTHONPATH=src uv run python -m feedbackpulse.evaluate

`src/` is not an installed package, so the path is supplied the same way the
container does it (PYTHONPATH=/app/src), per the interface decision recorded in
reports/P02-T04-inference-interface.md. The pytest `pythonpath` setting only
covers the test run, not this module.
"""

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from feedbackpulse import dataset, model_files
from feedbackpulse.evaluation import evaluate
from feedbackpulse.inference import SentimentClassifier

RESULT_PATH = Path("reports/P02-T05-evaluation-result.json")


# Everything this project writes as a result rather than reads as an input.
# Changes here must not mark a run dirty: the question the flag answers is
# whether the code and configuration behind the numbers were committed, and a
# previous result file sitting uncommitted says nothing about that.
_OUTPUT_PREFIXES = ("reports/",)


def uncommitted_inputs(porcelain_status: str) -> list[str]:
    """Paths from `git status --porcelain` that count as uncommitted inputs."""
    paths = []
    for line in porcelain_status.splitlines():
        if not line.strip():
            continue
        # Porcelain v1: two status characters, a space, then the path. A rename
        # reads "old -> new", and either side changing is a real change.
        candidates = [part.strip().strip('"') for part in line[3:].split(" -> ")]
        if any(not path.startswith(_OUTPUT_PREFIXES) for path in candidates if path):
            paths.append(line[3:])
    return paths


def _code_version() -> dict:
    """Record the commit and whether the inputs behind this run were committed.

    A dirty tree means the run cannot be reproduced from the commit alone, so it
    is recorded rather than hidden.
    """
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None, "uncommitted": None}
    dirty_paths = uncommitted_inputs(status)
    return {"commit": commit, "dirty": bool(dirty_paths), "uncommitted": dirty_paths}


def _package_versions() -> dict:
    import numpy
    import tokenizers
    import torch
    import transformers

    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "numpy": numpy.__version__,
        "tokenizers": tokenizers.__version__,
    }


def run(classifier: SentimentClassifier, dataset_path=dataset.LOCAL_PATH) -> dict:
    """Predict every row and return the metrics plus the inputs they came from."""
    dataset_hash = dataset.verify(dataset_path)

    pairs = []
    skipped = []
    started = time.perf_counter()
    for index, (text, true_label) in enumerate(dataset.read_rows(dataset_path)):
        try:
            prediction = classifier.predict(text)
        except ValueError as exc:
            # Recorded, not silently dropped: a skipped row changes the totals.
            skipped.append({"row": index, "reason": str(exc)})
            continue
        pairs.append((true_label, prediction.sentiment))
    elapsed = time.perf_counter() - started

    result = evaluate(pairs, classifier.labels)
    result["skipped"] = skipped
    result["inputs"] = {
        "model_repo": model_files.MODEL_REPO,
        "model_revision": model_files.MODEL_REVISION,
        "labels_from_model_config": list(classifier.labels),
        "max_content_tokens": classifier.max_content_tokens,
        "dataset_handle": dataset.DATASET_HANDLE,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_hash,
        "code": _code_version(),
        "versions": _package_versions(),
    }
    result["run"] = {
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "seconds": round(elapsed, 1),
    }
    return result


def main() -> None:
    dataset.ensure_dataset()
    classifier = SentimentClassifier.load(
        model_files.ensure_model_files(),
        # Placeholder: the real scheme is decided in P02-T07. Recorded so the
        # result file never implies a version it was not produced with.
        model_version=f"unversioned-{model_files.MODEL_REVISION[:12]}",
    )
    result = run(classifier)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"rows evaluated : {result['total']:,}")
    print(f"rows skipped   : {len(result['skipped'])}")
    print(f"accuracy       : {result['accuracy']:.4f}")
    print(f"macro F1       : {result['macro_f1']:.4f}")
    for label in classifier.labels:
        scores = result["per_class"][label]
        print(
            f"  {label:<9} P={scores['precision']:.4f} "
            f"R={scores['recall']:.4f} F1={scores['f1']:.4f} n={scores['support']:,}"
        )
    print(f"written        : {RESULT_PATH}")


if __name__ == "__main__":
    main()
