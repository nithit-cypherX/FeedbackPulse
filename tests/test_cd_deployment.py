"""Exercise the CD deployment guards offline, without calling Azure."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/cd.yml"
READY_STATE = {
    "state": "Succeeded", "latest": "new-revision", "ready": "new-revision",
    "image": "test.azurecr.io/feedbackpulse:tested-sha",
    "traffic": [{"latestRevision": True, "weight": 100}],
}


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


def run_revision_guard(monkeypatch, states, read_seconds=0):
    """Run the workflow's actual Python with an Azure stub and a virtual clock."""
    clock = SimpleNamespace(seconds=0, calls=[], sleeps=[])

    def read_state(command, **kwargs):
        assert command[:3] == ["az", "containerapp", "show"]
        assert command[command.index("-n") + 1] == "test-app"
        assert command[command.index("-g") + 1] == "test-rg"
        assert kwargs["check"] and kwargs["capture_output"]
        assert 0 < kwargs["timeout"] <= min(30, 300 - clock.seconds)
        state = states[min(len(clock.calls), len(states) - 1)]
        clock.calls.append(kwargs["timeout"])
        clock.seconds += min(read_seconds, kwargs["timeout"])
        if isinstance(state, Exception):
            raise state
        return SimpleNamespace(stdout=json.dumps(state))

    def sleep(seconds):
        assert 0 < seconds <= 10
        clock.sleeps.append(seconds)
        clock.seconds += seconds

    script = step_script("Verify deployed revision").split("python3 - <<'PY'\n", 1)[1]
    script = script.rsplit("\nPY", 1)[0]
    with monkeypatch.context() as patch:
        patch.setenv("EXPECTED_IMAGE", READY_STATE["image"])
        patch.setenv("AZURE_CONTAINER_APP_NAME", "test-app")
        patch.setenv("AZURE_RESOURCE_GROUP", "test-rg")
        patch.setattr(subprocess, "run", read_state)
        patch.setattr(time, "monotonic", lambda: clock.seconds)
        patch.setattr(time, "sleep", sleep)
        try:
            exec(compile(script, str(WORKFLOW), "exec"), {})  # noqa: S102 - Trusted repo code; Azure calls are mocked.
        except SystemExit as error:
            return str(error), clock
    return None, clock


@pytest.mark.parametrize("override,passes", [
    ({}, True),
    ({"state": "Failed"}, False),
    ({"state": "Canceled"}, False),
    ({"state": "Cancelled"}, False),
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
def test_revision_guard_rejects_stale_or_unready_deployment(monkeypatch, capsys, override, passes):
    error, _ = run_revision_guard(monkeypatch, [{**READY_STATE, **override}])
    assert (error is None) == passes, error
    assert ("PASS:" in capsys.readouterr().out) == passes


@pytest.mark.parametrize("pending", [
    {"state": "InProgress", "ready": "old-revision"},
    {"ready": "old-revision"},
    {"latest": "", "ready": ""},
])
def test_revision_waits_for_new_revision_then_succeeds(monkeypatch, capsys, pending):
    error, clock = run_revision_guard(monkeypatch, [
        {**READY_STATE, **pending}, {**READY_STATE, **pending}, READY_STATE,
    ])
    assert error is None
    assert len(clock.calls) == 3 and clock.sleeps == [10, 10]
    output = capsys.readouterr().out
    assert output.count("Waiting for revision:") == 2
    assert output.count("PASS:") == 1


@pytest.mark.parametrize("read_seconds,reads,last_timeout", [(0, 30, 10), (17, 12, 3)])
def test_revision_wait_has_bounded_deadline_including_reads(
    monkeypatch, capsys, read_seconds, reads, last_timeout,
):
    error, clock = run_revision_guard(
        monkeypatch, [{**READY_STATE, "ready": "old-revision"}], read_seconds=read_seconds,
    )
    assert "timed out after 300 seconds" in error
    assert len(clock.calls) == reads and clock.calls[-1] == last_timeout
    assert clock.seconds == 300
    assert "PASS:" not in capsys.readouterr().out


def test_revision_cannot_succeed_at_deadline(monkeypatch, capsys):
    error, clock = run_revision_guard(
        monkeypatch, [{**READY_STATE, "ready": "old-revision"}] * 11 + [READY_STATE], read_seconds=17,
    )
    assert "timed out" in error
    assert len(clock.calls) == 12 and clock.seconds == 300
    assert "PASS:" not in capsys.readouterr().out


@pytest.mark.parametrize("failure", ["Failed", "Canceled", "Cancelled"])
def test_revision_terminal_failure_stops_polling(monkeypatch, failure):
    error, clock = run_revision_guard(monkeypatch, [
        {**READY_STATE, "state": "InProgress"}, {**READY_STATE, "state": failure}, READY_STATE,
    ])
    assert "Azure reported " + failure in error
    assert len(clock.calls) == 2 and clock.sleeps == [10]


@pytest.mark.parametrize("failure", [
    subprocess.CalledProcessError(1, ["az"], stderr="private diagnostic"),
    subprocess.TimeoutExpired(["az"], 30),
])
def test_revision_read_error_fails_closed_without_retry(monkeypatch, failure):
    error, clock = run_revision_guard(monkeypatch, [failure])
    assert error == "Deployment verification failed: could not read Azure state."
    assert len(clock.calls) == 1 and clock.sleeps == []


@pytest.mark.parametrize("read_error", [False, True])
def test_revision_guard_shell_wiring(tmp_path, read_error):
    env = {**fake_cli(tmp_path), "TEST_STATE_JSON": json.dumps(READY_STATE)}
    if read_error:
        env["READ_ERROR"] = "1"
    result = subprocess.run(
        ["bash", "-c", step_script("Verify deployed revision")],
        env=env, capture_output=True, text=True, check=False, timeout=10,
    )
    assert (result.returncode == 0) == (not read_error), result.stdout + result.stderr
    assert ("PASS:" in result.stdout) == (not read_error)


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
