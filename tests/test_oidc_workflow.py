"""Local workflow checks; never log in to Azure or run a GitHub workflow."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def load_workflow(name):
    # BaseLoader preserves the GitHub key `on` instead of YAML 1.1's boolean True.
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


def test_login_workflow_is_manual_main_only_and_has_no_deploy_job():
    workflow = load_workflow("oidc-check.yml")
    assert workflow["on"] == {"workflow_dispatch": ""}
    assert workflow["permissions"] == {}
    assert set(workflow["jobs"]) == {"login"}
    job = workflow["jobs"]["login"]
    assert job["if"] == "${{ github.ref == 'refs/heads/main' }}"
    assert job["environment"] == "production"
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == "5"
    assert job["permissions"] == {"id-token": "write"}
    assert job["env"] == {
        "AZURE_CLIENT_ID": "${{ secrets.AZURE_CLIENT_ID }}",
        "AZURE_TENANT_ID": "${{ secrets.AZURE_TENANT_ID }}",
        "AZURE_CORE_OUTPUT": "none",
    }
    assert len(job["steps"]) == 3
    settings, login, identity = job["steps"]
    assert settings["id"] == "settings" and settings["shell"] == "bash"
    assert login["uses"] == "azure/login@v2"
    assert login["with"] == {
        "client-id": "${{ secrets.AZURE_CLIENT_ID }}",
        "tenant-id": "${{ secrets.AZURE_TENANT_ID }}",
        "allow-no-subscriptions": "true",
    }
    assert identity["id"] == "identity" and identity["shell"] == "python"


def test_cd_switch_guards_both_automatic_and_manual_paths():
    workflow = load_workflow("cd.yml")
    assert set(workflow["jobs"]) == {"deploy"}
    # Check the entire grouping: workflow_dispatch must not bypass the switch.
    expected = """${{ vars.FEEDBACKPULSE_CD_ENABLED == 'true' &&
        github.ref == 'refs/heads/main' &&
        ((github.event_name == 'workflow_run' &&
          github.event.workflow_run.head_branch == 'main' &&
          github.event.workflow_run.conclusion == 'success') ||
         github.event_name == 'workflow_dispatch') }}"""
    assert workflow["jobs"]["deploy"]["if"].split() == expected.split()


@pytest.mark.parametrize("client,tenant,code", [
    ("test-client", "test-tenant", 0),
    ("", "test-tenant", 1),
    ("test-client", "", 1),
    ("", "", 1),
])
def test_missing_settings_fail_before_login(client, tenant, code):
    script = load_workflow("oidc-check.yml")["jobs"]["login"]["steps"][0]["run"]
    result = subprocess.run(
        ["bash", "-c", script],
        env={"AZURE_CLIENT_ID": client, "AZURE_TENANT_ID": tenant},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == code
    assert "test-client" not in result.stdout
    assert "test-tenant" not in result.stdout


@pytest.mark.parametrize("account,passes", [
    ({"tenantId": "tenant-a", "user": {"name": "client-a", "type": "servicePrincipal"}}, True),
    ({"tenantId": "TENANT-A", "user": {"name": "CLIENT-A", "type": "servicePrincipal"}}, True),
    ({"tenantId": "wrong", "user": {"name": "client-a", "type": "servicePrincipal"}}, False),
    ({"tenantId": "tenant-a", "user": {"name": "wrong", "type": "servicePrincipal"}}, False),
    ({"tenantId": "tenant-a", "user": {"name": "client-a", "type": "user"}}, False),
    ({}, False),
])
def test_identity_check_uses_only_read_only_account_data(account, passes):
    # Isolated Python process with a stubbed CLI response and no executables on PATH.
    stub = """
import os
import subprocess

def fake_account_output(command, *, text):
    assert command == ["az", "account", "show", "--output", "json"]
    assert text is True
    return os.environ["TEST_ACCOUNT"]

subprocess.check_output = fake_account_output
"""
    script = load_workflow("oidc-check.yml")["jobs"]["login"]["steps"][2]["run"]
    result = subprocess.run(
        [sys.executable, "-c", stub + script],
        env={
            "PATH": "",
            "AZURE_CLIENT_ID": "client-a",
            "AZURE_TENANT_ID": "tenant-a",
            "TEST_ACCOUNT": json.dumps(account),
        },
        capture_output=True, text=True, check=False, timeout=5,
    )
    if passes:
        assert result.returncode == 0, result.stderr
        assert "PASS: OIDC login matches" in result.stdout
        assert "deployment permissions were not tested" in result.stdout
    else:
        assert result.returncode != 0
        assert "does not match" in result.stderr
        assert "PASS:" not in result.stdout
    assert "client-a" not in result.stdout + result.stderr
    assert "tenant-a" not in result.stdout + result.stderr
