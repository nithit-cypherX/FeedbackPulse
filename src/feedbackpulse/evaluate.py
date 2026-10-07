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

import hashlib
import json
import secrets
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from feedbackpulse import dataset, gitinfo, model_files
from feedbackpulse.evaluation import evaluate
from feedbackpulse.inference import SentimentClassifier

RESULT_PATH = Path("reports/P02-T05-evaluation-result.json")


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


def new_run_id() -> str:
    """Identify one execution.

    R1 lists a run ID among the evidence to keep, and nothing else here can
    serve as one: the pipeline is deterministic, so predictions_sha256 is the
    same for every run over the same inputs and identifies the output rather
    than the execution. The random suffix keeps two runs started in the same
    second apart.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"run-{stamp}-{secrets.token_hex(3)}"


def run(classifier: SentimentClassifier, dataset_path=dataset.LOCAL_PATH) -> dict:
    """Predict every row and return the metrics plus the inputs they came from."""
    run_id = new_run_id()
    dataset_hash = dataset.verify(dataset_path)

    pairs = []
    skipped = []
    # Fingerprint of every prediction in row order. Aggregate metrics can match
    # across two runs while individual rows differ, if the differences cancel
    # out; this catches that, which is what reproducibility actually claims.
    # repr() of the score so the comparison is over the float's exact bits.
    fingerprint = hashlib.sha256()
    started = time.perf_counter()
    for index, (text, true_label) in enumerate(dataset.read_rows(dataset_path)):
        try:
            prediction = classifier.predict(text)
        except ValueError as exc:
            # Recorded, not silently dropped: a skipped row changes the totals.
            skipped.append({"row": index, "reason": str(exc)})
            fingerprint.update(f"{index}\tskipped\n".encode())
            continue
        pairs.append((true_label, prediction.sentiment))
        fingerprint.update(
            f"{index}\t{prediction.sentiment}\t{prediction.score!r}\n".encode()
        )
    elapsed = time.perf_counter() - started

    result = evaluate(pairs, classifier.labels)
    result["skipped"] = skipped
    result["predictions_sha256"] = fingerprint.hexdigest()
    result["inputs"] = {
        "model_repo": model_files.MODEL_REPO,
        "model_revision": model_files.MODEL_REVISION,
        "labels_from_model_config": list(classifier.labels),
        "max_content_tokens": classifier.max_content_tokens,
        "dataset_handle": dataset.DATASET_HANDLE,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_hash,
        "code": gitinfo.code_version(),
        "versions": _package_versions(),
    }
    result["run"] = {
        "run_id": run_id,
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

    print(f"run_id         : {result['run']['run_id']}")
    print(f"rows evaluated : {result['total']:,}")
    print(f"rows skipped   : {len(result['skipped'])}")
    print(f"predictions    : {result['predictions_sha256'][:16]}...")
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
