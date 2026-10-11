"""Local workflow checks; never log in to Azure or run a GitHub workflow."""

import json
import os
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


def test_cd_checkout_matches_image_and_deployment_sha():
    steps = load_workflow("cd.yml")["jobs"]["deploy"]["steps"]
    checkout = next(step for step in steps if step.get("uses") == "actions/checkout@v4")
    # Automatic CD uses the triggering CI commit; manual CD uses its own event SHA.
    expected_ref = "${{ github.event.workflow_run.head_sha || github.sha }}"
    assert checkout.get("with", {}).get("ref") == expected_ref
    for name in ("Build and push container image", "Render Container App configuration"):
        step = next(step for step in steps if step["name"] == name)
        assert f'DEPLOY_SHA="{expected_ref}"' in step["run"]


CD_SETTINGS = [
    "AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID",
    "AZURE_RESOURCE_GROUP", "AZURE_CONTAINER_APP_ENV", "AZURE_CONTAINER_APP_NAME",
    "AZURE_REGISTRY_NAME", "AZURE_REGISTRY_SERVER", "AZURE_REGISTRY_IDENTITY_ID", "SERVICE_TOKEN",
]


def test_cd_requires_explicit_settings_before_any_other_steps():
    workflow = load_workflow("cd.yml")
    assert workflow["env"] == {
        name: "${{ vars." + name + " }}" for name in CD_SETTINGS[3:-1]
    }
    job = workflow["jobs"]["deploy"]
    assert job["env"] == {
        name: "${{ secrets." + name + " }}" for name in CD_SETTINGS[:3]
    }
    assert job["steps"][0]["id"] == "settings"
    assert job["steps"][0]["env"] == {"SERVICE_TOKEN": "${{ secrets.SERVICE_TOKEN }}"}
    logins = [step for step in job["steps"] if step.get("uses") == "azure/login@v2"]
    assert len(logins) == 1
    assert logins[0]["with"] == {
        "client-id": "${{ env.AZURE_CLIENT_ID }}",
        "tenant-id": "${{ env.AZURE_TENANT_ID }}",
        "subscription-id": "${{ env.AZURE_SUBSCRIPTION_ID }}",
    }


@pytest.mark.parametrize("missing", [None, *CD_SETTINGS])
@pytest.mark.parametrize("value", ["", " \t"])
def test_cd_preflight_fails_closed_without_printing_values(missing, value):
    script = load_workflow("cd.yml")["jobs"]["deploy"]["steps"][0]["run"]
    env = {name: "private-value-" + name for name in CD_SETTINGS}
    if missing:
        env[missing] = value
    result = subprocess.run(
        ["/bin/bash", "-c", script], env={**env, "PATH": ""},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == (1 if missing else 0)
    if missing:
        assert missing in result.stdout
    assert "private-value-" not in result.stdout + result.stderr


def test_cd_rejects_old_example_service_token():
    script = load_workflow("cd.yml")["jobs"]["deploy"]["steps"][0]["run"]
    result = subprocess.run(
        ["/bin/bash", "-c", script],
        env={**dict.fromkeys(CD_SETTINGS, "configured"),
             "SERVICE_TOKEN": "test-service-token-secret-12345", "PATH": ""},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert "old example value" in result.stdout
    assert "test-service-token-secret-12345" not in result.stdout + result.stderr


def test_cd_render_and_smoke_use_secret_environment_not_script_interpolation():
    steps = load_workflow("cd.yml")["jobs"]["deploy"]["steps"]
    render = next(step for step in steps if step["name"] == "Render Container App configuration")
    smoke = next(step for step in steps if step["name"] == "Live Smoke Test with Three Known Payloads")
    assert render["env"] == smoke["env"] == {"SERVICE_TOKEN": "${{ secrets.SERVICE_TOKEN }}"}
    assert 'REGISTRY_IDENTITY_ID="$AZURE_REGISTRY_IDENTITY_ID"' in render["run"]
    for step in steps:
        script = step.get("run", "")
        assert "secrets.SERVICE_TOKEN" not in script
        assert "az acr credential" not in script
        assert "REGISTRY_PASSWORD" not in script
        assert "REGISTRY_USERNAME" not in script


def test_cd_shell_scripts_have_valid_bash_syntax():
    for step in load_workflow("cd.yml")["jobs"]["deploy"]["steps"]:
        if "run" in step:
            result = subprocess.run(
                ["bash", "-n"], input=step["run"], capture_output=True, text=True, check=False,
            )
            assert result.returncode == 0, (step["name"], result.stderr)


@pytest.mark.parametrize("entrypoint", ["cd-render", "make-deploy"])
def test_deployment_callers_pass_identity_without_acr_password(tmp_path, entrypoint):
    """Exercise real renderer/caller scripts with a fake Azure CLI, never the cloud."""
    root = WORKFLOWS.parents[1]
    (tmp_path / "cloudlayer").mkdir()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_az = fake_bin / "az"
    fake_az.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
args = sys.argv[1:]
if args[:3] == ["containerapp", "env", "show"]:
    print(os.environ["TEST_ENV_ID"])
elif args[:2] == ["containerapp", "show"]:
    print("test-app")
elif args[:2] == ["containerapp", "update"]:
    import yaml
    with open(args[args.index("--yaml") + 1]) as stream:
        config = yaml.safe_load(stream)
    with open("captured-config.json", "w") as stream:
        json.dump(config, stream)
else:
    raise SystemExit("Unexpected Azure command in offline test")
''')
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(f"#!{sys.executable}\n" + '''
import os, sys
assert sys.argv[1:4] == ["run", "python", "cloudlayer/render_config.py"]
os.execv(sys.executable, [sys.executable, os.environ["TEST_RENDERER"], *sys.argv[4:]])
''')
    fake_az.chmod(0o755)
    fake_uv.chmod(0o755)
    identity = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/pull"
    env = {
        **os.environ, **dict.fromkeys(CD_SETTINGS, "test-setting"),
        "PATH": f"{fake_bin}:/usr/bin:/bin", "HOME": str(tmp_path),
        "UV": str(fake_uv), "AZURE_REGISTRY_IDENTITY_ID": identity,
        "AZURE_REGISTRY_SERVER": "example.azurecr.io", "IMAGE_TAG": "example.azurecr.io/feedbackpulse:test",
        "SERVICE_TOKEN": 'test-only-"quoted"-token',
        "TEST_ENV_ID": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env",
        "TEST_RENDERER": str(root / "cloudlayer/render_config.py"),
    }
    if entrypoint == "cd-render":
        steps = load_workflow("cd.yml")["jobs"]["deploy"]["steps"]
        script = next(s["run"] for s in steps if s["name"] == "Render Container App configuration")
        script = script.replace("${{ github.event.workflow_run.head_sha || github.sha }}", "test-sha")
        command = ["/bin/bash", "-c", script]
    else:
        command = ["/usr/bin/make", "-f", str(root / "Makefile"), "deploy",
                   f"UV={fake_uv}", f"PATH={env['PATH']}"]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    if entrypoint == "cd-render":
        config = yaml.safe_load((tmp_path / "rendered_containerapp.yaml").read_text())
    else:
        config = json.loads((tmp_path / "captured-config.json").read_text())
        assert not list((tmp_path / "cloudlayer").glob("containerapp.render.*.yaml"))
    assert config["identity"]["userAssignedIdentities"] == {identity: {}}
    settings = config["properties"]["configuration"]
    assert settings["registries"] == [{"server": "example.azurecr.io", "identity": identity}]
    assert settings["secrets"] == [{"name": "service-token", "value": env["SERVICE_TOKEN"]}]
    assert env["SERVICE_TOKEN"] not in result.stdout + result.stderr


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
