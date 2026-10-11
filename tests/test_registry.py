"""The registry entry must stay verifiable after the next evaluation runs.

reports/P02-T05-evaluation-result.json is overwritten by every run. An entry
that only pointed at that path stopped being traceable as soon as anyone
re-ran the evaluation, which would leave a rolled-back version with lineage
nobody could check — exactly what R2 needs to work.
"""

import hashlib
import json

import pytest

from feedbackpulse import registry


def test_entry_keeps_its_own_copy_of_the_evaluation(tmp_path, monkeypatch):
    evaluation = tmp_path / "result.json"
    evaluation.write_text(json.dumps({"macro_f1": 0.5}), encoding="utf-8")
    monkeypatch.setattr(registry, "EVALUATION_RESULT", evaluation)
    monkeypatch.setattr(registry, "LOCKFILE", evaluation)

    snapshot_name = "run-20260101T000000Z-abcdef-evaluation.json"
    lineage = {
        "artifact": {"artifact_id": "sentiment-aaaaaaaaaaaa"},
        "evaluation": {"result_file": snapshot_name, "result_sha256": "x"},
    }
    monkeypatch.setattr(registry, "build_lineage", lambda _: lineage)

    registry_dir = tmp_path / "registry"
    path = registry.register(tmp_path / "artifact", registry_dir=registry_dir)
    entry = json.loads(path.read_text(encoding="utf-8"))

    snapshot = registry_dir / snapshot_name
    assert snapshot.exists()
    assert entry["lineage"]["evaluation"]["result_file"] == snapshot_name

    # Overwriting the shared file must not break the entry.
    evaluation.write_text(json.dumps({"macro_f1": 0.9}), encoding="utf-8")
    assert json.loads(snapshot.read_text(encoding="utf-8"))["macro_f1"] == 0.5


def test_entry_can_verify_its_own_version(tmp_path, monkeypatch):
    """The first link of the traceability chain.

    The version is a digest over the lineage, so the lineage that gets stored
    must be the one that was hashed. Filling a field in afterwards broke this
    once and the entry could no longer prove its own version.
    """
    evaluation = tmp_path / "result.json"
    evaluation.write_text(json.dumps({"macro_f1": 0.5}), encoding="utf-8")
    monkeypatch.setattr(registry, "EVALUATION_RESULT", evaluation)

    lineage = {
        "artifact": {"artifact_id": "sentiment-aaaaaaaaaaaa"},
        "evaluation": {"result_file": "run-20260101T000000Z-abcdef-evaluation.json"},
    }
    monkeypatch.setattr(registry, "build_lineage", lambda _: lineage)

    registry_dir = tmp_path / "registry"
    path = registry.register(tmp_path / "artifact", registry_dir=registry_dir)
    entry = json.loads(path.read_text(encoding="utf-8"))

    recomputed = registry.model_version_for(
        entry["lineage"]["artifact"]["artifact_id"], entry["lineage"]
    )
    assert recomputed == entry["model_version"]


def test_missing_entry_is_reported(tmp_path):
    with pytest.raises(registry.CannotRegister):
        registry.load("sentiment-nope", registry_dir=tmp_path)


def test_run_ids_differ_for_runs_started_in_the_same_second():
    """R1 asks for a run ID, and nothing else here can serve as one.

    The pipeline is deterministic, so predictions_sha256 repeats across runs over
    the same inputs; the timestamp alone collides for runs started in the same
    second.
    """
    from feedbackpulse.evaluate import new_run_id

    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(value.startswith("run-") for value in ids)


@pytest.fixture
def registration_inputs(tmp_path, monkeypatch):
    """Small local files: check registration without downloading a model."""
    evaluation = tmp_path / "result.json"
    evaluation.write_text(
        json.dumps(
            {
                "total": 1,
                "accuracy": 0.5,
                "macro_f1": 0.5,
                "predictions_sha256": "x",
                "run": {"run_id": "run-20260101T000000Z-abcdef", "finished_utc": "t"},
                "inputs": {
                    "code": {"commit": "0" * 40, "dirty": False},
                    "model_revision": "rev",
                    "dataset_sha256": "ds",
                    "versions": {"python": "3.13.11"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(registry, "EVALUATION_RESULT", evaluation)
    monkeypatch.setattr(registry, "LOCKFILE", evaluation)
    monkeypatch.setattr(
        registry.gitinfo,
        "code_version",
        lambda: {"commit": "0" * 40, "dirty": False, "uncommitted": []},
    )
    monkeypatch.setattr(registry.gitinfo, "behaviour_changed_between", lambda _c: [])
    monkeypatch.setattr(registry.dataset, "DATASET_SHA256", "ds")

    artifact = tmp_path / "artifact"
    (artifact / "model").mkdir(parents=True)
    contents = {
        "model/config.json": b'{"model_type": "roberta"}',
        "model/model.safetensors": b"test weights, not a loadable model",
        "upstream-model-card.md": b"test model card",
    }
    for name, content in contents.items():
        (artifact / name).write_bytes(content)

    manifest = artifact / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifact_id": "sentiment-aaaaaaaaaaaa",
                "loadable_dir": "model",
                "files_sha256": {
                    name: hashlib.sha256(content).hexdigest()
                    for name, content in contents.items()
                },
                "source": {
                    "revision": "rev",
                    "licence": "CC BY 4.0",
                    "upstream_file_sha256": {},
                },
            }
        ),
        encoding="utf-8",
    )
    return artifact


def test_lineage_carries_the_run_id(registration_inputs):
    """Without this, model_version could not lead back to its evaluation run."""
    lineage = registry.build_lineage(registration_inputs)
    assert lineage["evaluation"]["run_id"] == "run-20260101T000000Z-abcdef"


def test_register_accepts_matching_files(registration_inputs, tmp_path):
    path = registry.register(registration_inputs, registry_dir=tmp_path / "registry")
    entry = json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads((registration_inputs / "manifest.json").read_text())
    assert entry["lineage"]["artifact"]["files_sha256"] == manifest["files_sha256"]
    assert (path.parent / entry["lineage"]["evaluation"]["result_file"]).is_file()


@pytest.mark.parametrize(
    "name",
    ["model/config.json", "model/model.safetensors", "upstream-model-card.md"],
)
@pytest.mark.parametrize("change", ["missing", "changed"])
def test_register_rejects_missing_or_changed_files(
    registration_inputs, tmp_path, name, change
):
    file = registration_inputs / name
    if change == "missing":
        file.unlink()
    else:
        file.write_bytes(b"changed after packaging")
    registry_dir = tmp_path / "registry"

    with pytest.raises(registry.CannotRegister) as raised:
        registry.register(registration_inputs, registry_dir=registry_dir)

    assert name in str(raised.value)
    assert not registry_dir.exists(), "Rejected artifacts must not create an entry"


def test_register_rejects_a_directory_in_place_of_a_file(registration_inputs, tmp_path):
    file = registration_inputs / "model/model.safetensors"
    file.unlink()
    file.mkdir()
    with pytest.raises(registry.CannotRegister, match="model/model.safetensors"):
        registry.register(registration_inputs, registry_dir=tmp_path / "registry")


def test_register_rejects_empty_file_hashes(registration_inputs, tmp_path):
    path = registration_inputs / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files_sha256"] = {}
    path.write_text(json.dumps(manifest))
    with pytest.raises(registry.CannotRegister, match="file hashes"):
        registry.register(registration_inputs, registry_dir=tmp_path / "registry")


def test_register_rejects_paths_outside_artifact(registration_inputs, tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside the artifact")
    path = registration_inputs / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files_sha256"]["../outside.bin"] = hashlib.sha256(
        outside.read_bytes()
    ).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(registry.CannotRegister, match="outside"):
        registry.register(registration_inputs, registry_dir=tmp_path / "registry")
