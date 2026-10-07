"""Register a packaged artifact and mint the model_version the API returns.

P01-T02 section 3 requires model_version to name the artifact actually in use
and to lead back to its lineage, and calls the "sentiment-v1" in that document
an illustration rather than a value to ship. This module decides the real one.

Run with:  PYTHONPATH=src uv run python -m feedbackpulse.registry
"""

import hashlib
import json
import shutil
from pathlib import Path

from feedbackpulse import dataset, gitinfo, model_files

REGISTRY_DIR = Path("reports/registry")
EVALUATION_RESULT = Path("reports/P02-T05-evaluation-result.json")
LOCKFILE = Path("uv.lock")


class CannotRegister(RuntimeError):
    """The lineage does not hold together, so no version may be minted."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(payload: dict) -> bytes:
    """Stable bytes for hashing: key order and spacing must not shift the digest."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def lineage_digest(lineage: dict) -> str:
    """Hash every recorded input, so any change produces a different version."""
    return hashlib.sha256(_canonical(lineage)).hexdigest()


def model_version_for(artifact_id: str, lineage: dict) -> str:
    """Build the string the API returns.

    Three parts, each earning its place:

      sentiment-6e7ff9fbc17c-4f2a9c1b
      |         |             |
      |         |             lineage digest: code, environment, dataset and
      |         |             evaluation result. Changing any of them changes
      |         |             this, which is what makes the version mean
      |         |             "these exact inputs" rather than "these weights".
      |         artifact id from P02-T06, so two releases of the same weights
      |         are visibly the same weights during a rollback.
      model family, readable in a log or a response body.

    Content-addressed rather than a counter: no central registry has to hand out
    the next number, which matters while the storage service is still undecided.
    """
    return f"{artifact_id}-{lineage_digest(lineage)[:8]}"


def build_lineage(artifact_dir: Path) -> dict:
    """Collect everything model_version must lead back to, or refuse."""
    code = gitinfo.code_version()
    if code["commit"] is None:
        raise CannotRegister("git is unavailable, so provenance cannot be claimed")
    if code["dirty"]:
        raise CannotRegister(
            "uncommitted inputs, so this version could not be rebuilt from its "
            f"commit: {', '.join(code['uncommitted'])}"
        )

    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        raise CannotRegister(f"{manifest_path} is missing; package the artifact first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not EVALUATION_RESULT.exists():
        raise CannotRegister(
            f"{EVALUATION_RESULT} is missing; run the evaluation step first"
        )
    evaluation = json.loads(EVALUATION_RESULT.read_text(encoding="utf-8"))

    eval_code = evaluation["inputs"]["code"]
    if eval_code.get("dirty"):
        raise CannotRegister("the evaluation ran on uncommitted code; re-run it")

    # An evaluation describes a release only while the files that decide a
    # prediction have not moved since it ran.
    moved = gitinfo.behaviour_changed_between(eval_code["commit"])
    if moved:
        raise CannotRegister(
            "these files changed since the evaluation ran, so its numbers no "
            f"longer describe this code: {', '.join(moved)}. Re-run the evaluation."
        )

    if evaluation["inputs"]["model_revision"] != manifest["source"]["revision"]:
        raise CannotRegister("the evaluation used a different model revision")
    if evaluation["inputs"]["dataset_sha256"] != dataset.DATASET_SHA256:
        raise CannotRegister("the evaluation used a different dataset file")

    return {
        "artifact": {
            "artifact_id": manifest["artifact_id"],
            "manifest_sha256": _sha256_file(manifest_path),
            "loadable_dir": manifest["loadable_dir"],
            "files_sha256": manifest["files_sha256"],
        },
        "source_model": {
            "repo": model_files.MODEL_REPO,
            "revision": model_files.MODEL_REVISION,
            "licence": manifest["source"]["licence"],
            "upstream_file_sha256": manifest["source"]["upstream_file_sha256"],
        },
        "evaluation_data": {
            "handle": dataset.DATASET_HANDLE,
            "sha256": dataset.DATASET_SHA256,
            "rows": evaluation["total"],
        },
        "code": {"commit": code["commit"]},
        "environment": {
            "python": evaluation["inputs"]["versions"]["python"],
            "lockfile_sha256": _sha256_file(LOCKFILE),
            "packages": evaluation["inputs"]["versions"],
        },
        "evaluation": {
            # Named after the run rather than the version, so it is known before
            # the digest is computed. Naming it after the version meant filling
            # it in afterwards, which left the stored lineage different from the
            # one that was hashed, and an entry that could not verify its own
            # version. Relative to the entry because the shared path below is
            # overwritten by the next run.
            "result_file": f"{evaluation['run']['run_id']}-evaluation.json",
            "produced_from": str(EVALUATION_RESULT),
            "result_sha256": _sha256_file(EVALUATION_RESULT),
            "run_id": evaluation["run"]["run_id"],
            "run_finished_utc": evaluation["run"]["finished_utc"],
            "accuracy": evaluation["accuracy"],
            "macro_f1": evaluation["macro_f1"],
        },
    }


def register(artifact_dir: Path, registry_dir: Path = REGISTRY_DIR) -> Path:
    """Write the registry entry and return its path."""
    lineage = build_lineage(artifact_dir)
    version = model_version_for(lineage["artifact"]["artifact_id"], lineage)

    registry_dir.mkdir(parents=True, exist_ok=True)

    # The entry keeps its own copy of the evaluation it was built from, so it
    # stays verifiable after the next run overwrites the shared result file.
    # The name comes from the lineage, which is not touched after hashing.
    shutil.copyfile(
        EVALUATION_RESULT, registry_dir / lineage["evaluation"]["result_file"]
    )

    entry = {"model_version": version, "lineage": lineage}
    path = registry_dir / f"{version}.json"
    path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    return path


def load(version: str, registry_dir: Path = REGISTRY_DIR) -> dict:
    """Read one entry back, which is how a deployed version is traced."""
    path = registry_dir / f"{version}.json"
    if not path.exists():
        raise CannotRegister(f"no registry entry for {version}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    import sys

    artifacts = sorted(Path("artifacts").glob("sentiment-*"))
    if not artifacts:
        print("no packaged artifact found; run package_artifact first", file=sys.stderr)
        raise SystemExit(1)
    if len(artifacts) > 1:
        # ponytail: register whichever single artifact is present; ceiling:
        # cannot hold two live versions at once; revisit when: P04 needs a
        # rollback target alongside the current release; upgrade: take the
        # artifact id as an argument and keep every entry side by side.
        print(
            f"several artifacts present, refusing to guess: {artifacts}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    path = register(artifacts[0])
    entry = json.loads(path.read_text(encoding="utf-8"))
    print(f"model_version : {entry['model_version']}")
    print(f"entry         : {path}")
    for section, value in entry["lineage"].items():
        print(f"  {section}")
        for key, inner in value.items():
            if isinstance(inner, dict):
                print(f"    {key}: {len(inner)} entries")
            else:
                print(f"    {key}: {inner}")


if __name__ == "__main__":
    main()
