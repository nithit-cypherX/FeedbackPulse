"""Assemble the model file set that the service loads.

The packaged set is self-contained: `SentimentClassifier.load` must work against
`<artifact>/model` without reaching the Hugging Face cache or the network.

Deliberately says nothing about where the artifact is stored or how it reaches a
container. Those remain open in docs/plans/P01-T03-system-structure.md section
12, and the layout here must not close either option.

Run with:  PYTHONPATH=src uv run python -m feedbackpulse.package_artifact
"""

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from feedbackpulse import model_files

ARTIFACT_ROOT = Path("artifacts")

# Copied byte for byte from the pinned revision so their hashes still match the
# upstream ones recorded in reports/P02-T01-model-provenance.md. Only the
# weights are transformed; see WEIGHTS_FILE below.
VERBATIM_FILES = (
    "config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
)

WEIGHTS_FILE = "model.safetensors"

# The upstream model card travels with the artifact to satisfy the CC BY 4.0
# attribution requirement, but stays out of model/ so the loadable directory
# holds nothing the loader does not read.
MODEL_CARD_FILE = "upstream-model-card.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_id(model_dir: Path) -> str:
    """Derive a content-addressed id from the loadable files.

    Content addressing rather than a counter: the same inputs always produce the
    same id, so two people packaging independently can tell they built the same
    thing. Only files under model/ take part, which keeps the manifest free to
    record the id without hashing itself.
    """
    lines = sorted(f"{p.name}:{_sha256(p)}" for p in model_dir.iterdir() if p.is_file())
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    return f"sentiment-{digest[:12]}"


def _code_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build(snapshot_dir: Path, root: Path = ARTIFACT_ROOT) -> Path:
    """Build one artifact directory and return its path."""
    import safetensors.torch
    import torch
    import transformers
    from transformers import AutoModelForSequenceClassification

    staging = root / ".build"
    if staging.exists():
        shutil.rmtree(staging)
    model_dir = staging / "model"
    model_dir.mkdir(parents=True)

    for name in VERBATIM_FILES:
        shutil.copyfile(snapshot_dir / name, model_dir / name)

    model = AutoModelForSequenceClassification.from_pretrained(str(snapshot_dir))
    model.eval()
    # save_model handles shared storage; this checkpoint has none, but relying on
    # it means a future revision with tied weights does not fail silently.
    safetensors.torch.save_model(model, str(model_dir / WEIGHTS_FILE))

    shutil.copyfile(snapshot_dir / "README.md", staging / MODEL_CARD_FILE)

    identifier = artifact_id(model_dir)
    upstream = {
        name: _sha256(snapshot_dir / name)
        for name in (*VERBATIM_FILES, "pytorch_model.bin", "README.md")
    }
    files = {
        f"model/{p.name}": _sha256(p)
        for p in sorted(model_dir.iterdir())
        if p.is_file()
    }
    files[MODEL_CARD_FILE] = _sha256(staging / MODEL_CARD_FILE)

    manifest = {
        "artifact_id": identifier,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "loadable_dir": "model",
        "source": {
            "repo": model_files.MODEL_REPO,
            "revision": model_files.MODEL_REVISION,
            "licence": "CC BY 4.0",
            "upstream_file_sha256": upstream,
        },
        "weights": {
            "format": "safetensors",
            "converted_from": "pytorch_model.bin",
            "reason": (
                "loading the artifact must not unpickle a file, since P05 "
                "deliberately tampers with it and a pickle executes on load"
            ),
            # Recorded because the converted file is not a copy: three entries
            # the classification head never reads are absent.
            "tensors_written": len(model.state_dict()),
            "tensors_dropped": [
                "roberta.embeddings.position_ids",
                "roberta.pooler.dense.weight",
                "roberta.pooler.dense.bias",
            ],
        },
        "model": {
            "labels": [model.config.id2label[i] for i in sorted(model.config.id2label)],
            "max_content_tokens": model.config.max_position_embeddings
            - 2
            - 2,  # position offset, then the two special tokens
        },
        "built_with": {
            "code_commit": _code_commit(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "safetensors": safetensors.__version__,
        },
        "files_sha256": files,
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    destination = root / identifier
    if destination.exists():
        shutil.rmtree(destination)
    staging.rename(destination)
    return destination


def main() -> None:
    artifact = build(model_files.ensure_model_files())
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    print(f"artifact_id : {manifest['artifact_id']}")
    print(f"path        : {artifact}")
    print(f"labels      : {', '.join(manifest['model']['labels'])}")
    print(f"max tokens  : {manifest['model']['max_content_tokens']}")
    for name, digest in manifest["files_sha256"].items():
        size = (artifact / name).stat().st_size
        print(f"  {name:<32} {size:>12,} bytes  {digest[:16]}...")


if __name__ == "__main__":
    main()
