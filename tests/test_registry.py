"""The registry entry must stay verifiable after the next evaluation runs.

reports/P02-T05-evaluation-result.json is overwritten by every run. An entry
that only pointed at that path stopped being traceable as soon as anyone
re-ran the evaluation, which would leave a rolled-back version with lineage
nobody could check — exactly what R2 needs to work.
"""

import json

import pytest

from feedbackpulse import registry


def test_entry_keeps_its_own_copy_of_the_evaluation(tmp_path, monkeypatch):
    evaluation = tmp_path / "result.json"
    evaluation.write_text(json.dumps({"macro_f1": 0.5}), encoding="utf-8")
    monkeypatch.setattr(registry, "EVALUATION_RESULT", evaluation)
    monkeypatch.setattr(registry, "LOCKFILE", evaluation)

    lineage = {
        "artifact": {"artifact_id": "sentiment-aaaaaaaaaaaa"},
        "evaluation": {"result_file": "placeholder", "result_sha256": "x"},
    }
    monkeypatch.setattr(registry, "build_lineage", lambda _: lineage)

    registry_dir = tmp_path / "registry"
    path = registry.register(tmp_path / "artifact", registry_dir=registry_dir)
    entry = json.loads(path.read_text(encoding="utf-8"))
    version = entry["model_version"]

    snapshot = registry_dir / f"{version}-evaluation.json"
    assert snapshot.exists()
    assert entry["lineage"]["evaluation"]["result_file"] == snapshot.name

    # Overwriting the shared file must not break the entry.
    evaluation.write_text(json.dumps({"macro_f1": 0.9}), encoding="utf-8")
    assert json.loads(snapshot.read_text(encoding="utf-8"))["macro_f1"] == 0.5


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


def test_lineage_carries_the_run_id(tmp_path, monkeypatch):
    """Without this, model_version could not lead back to the run that measured it."""
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

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifact_id": "sentiment-aaaaaaaaaaaa",
                "loadable_dir": "model",
                "files_sha256": {},
                "source": {
                    "revision": "rev",
                    "licence": "CC BY 4.0",
                    "upstream_file_sha256": {},
                },
            }
        ),
        encoding="utf-8",
    )
    lineage = registry.build_lineage(tmp_path)
    assert lineage["evaluation"]["run_id"] == "run-20260101T000000Z-abcdef"
