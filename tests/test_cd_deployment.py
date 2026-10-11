"""Exercise the CD deployment guards offline, without calling Azure."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/cd.yml"


def step_script(name):
    workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    script = next(s["run"] for s in workflow["jobs"]["deploy"]["steps"] if s["name"] == name)
    return script.replace("${{ github.event.workflow_run.head_sha || github.sha }}", "tested-sha")


def fake_cli(tmp_path):
    executable = tmp_path / "az"
    executable.write_text(f"#!{sys.executable}\n" + '''
import os, sys
args = sys.argv[1:]
assert args[:2] in [["containerapp", "show"], ["containerapp", "update"]]
if os.environ.get("READ_ERROR") and args[1] == "show":
    raise SystemExit(1)
if args[1] == "update":
    with open(os.environ["CALL_LOG"], "a") as stream:
        stream.write("update\\n")
elif "--query" in args:
    print(os.environ["TEST_STATE_JSON"])
''')
    executable.chmod(0o755)
    return {
        **os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin",
        "AZURE_CONTAINER_APP_NAME": "test-app", "AZURE_RESOURCE_GROUP": "test-rg",
        "AZURE_REGISTRY_SERVER": "test.azurecr.io", "CALL_LOG": str(tmp_path / "calls"),
    }


@pytest.mark.parametrize("override,passes", [
    ({}, True),
    ({"state": "Failed"}, False),
    ({"state": "InProgress"}, False),
    ({"latest": "", "ready": ""}, False),
    ({"ready": "old-revision"}, False),
    ({"image": "test.azurecr.io/feedbackpulse:old-sha"}, False),
    ({"traffic": []}, False),
    ({"traffic": [{"revisionName": "old-revision", "weight": 100}]}, False),
    ({"traffic": [{"latestRevision": True, "weight": 50},
                  {"revisionName": "old-revision", "weight": 50}]}, False),
    ({"traffic": [{"revisionName": "new-revision", "weight": 100}]}, True),
])
def test_revision_guard_rejects_stale_or_unready_deployment(tmp_path, override, passes):
    state = {
        "state": "Succeeded", "latest": "new-revision", "ready": "new-revision",
        "image": "test.azurecr.io/feedbackpulse:tested-sha",
        "traffic": [{"latestRevision": True, "weight": 100}], **override,
    }
    result = subprocess.run(
        ["bash", "-c", step_script("Verify deployed revision")],
        env={**fake_cli(tmp_path), "TEST_STATE_JSON": json.dumps(state)},
        capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == passes, result.stdout + result.stderr
    assert ("PASS:" in result.stdout) == passes


@pytest.mark.parametrize("read_error", [False, True])
def test_cd_updates_only_an_existing_readable_app(tmp_path, read_error):
    env = fake_cli(tmp_path)
    if read_error:
        env["READ_ERROR"] = "1"
    result = subprocess.run(
        ["bash", "-c", step_script("Deploy revision to Azure Container Apps")],
        env=env, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (not read_error)
    calls = tmp_path / "calls"
    if read_error:
        assert not calls.exists()
    else:
        assert calls.read_text() == "update\n"
