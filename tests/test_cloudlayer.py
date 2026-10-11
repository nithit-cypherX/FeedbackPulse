"""Tests for Cloud Adapter and Azure Container Apps Configuration (Phase P04-T01).

Validates:
1. CloudDeploymentAdapter protocol conformance.
2. AzureContainerAppAdapter operations (service url, revision listing, traffic splitting, rollback).
3. Declarative Container App template structure and constraint policies.
"""

import json
import os
import subprocess
import sys

import pytest

from cloudlayer.adapter import CloudDeploymentAdapter
from cloudlayer.azure_adapter import AzureContainerAppAdapter
from cloudlayer.render_config import (
    REQUIRED_VARS,
    TEMPLATE_PATH,
    render_containerapp_yaml,
    validate_config_structure,
)

DUMMY_ENV = {
    "MANAGED_ENV_ID": "/subscriptions/0000/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env",
    "SERVICE_TOKEN": "renderer-test-token-not-for-deployment",
    "REGISTRY_SERVER": "example.azurecr.io",
    "REGISTRY_IDENTITY_ID": "/subscriptions/0000/resourceGroups/rg/providers/"
    "Microsoft.ManagedIdentity/userAssignedIdentities/pull-identity",
    "IMAGE_TAG": "example.azurecr.io/feedbackpulse:test-tag",
}


# ==============================================================================
# 1. Cloud Adapter Tests
# ==============================================================================


def test_azure_adapter_conforms_to_protocol():
    adapter = AzureContainerAppAdapter(resource_group="test-rg", app_name="test-app")
    assert isinstance(adapter, CloudDeploymentAdapter)


def test_azure_adapter_get_service_url():
    def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        assert "show" in cmd
        assert "--query" in cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="feedbackpulse-api.politeglacier-123.southeastasia.azurecontainerapps.io\n",
            stderr="",
        )

    adapter = AzureContainerAppAdapter(
        resource_group="test-rg", app_name="test-app", command_runner=mock_runner
    )
    url = adapter.get_service_url()
    assert (
        url
        == "https://feedbackpulse-api.politeglacier-123.southeastasia.azurecontainerapps.io"
    )


def test_azure_adapter_list_revisions_and_active():
    revisions_json = json.dumps(
        [
            {
                "name": "feedbackpulse-api--rev1",
                "properties": {"active": True, "createdTime": "2026-10-08T10:00:00Z"},
            },
            {
                "name": "feedbackpulse-api--rev2",
                "properties": {"active": True, "createdTime": "2026-10-08T11:00:00Z"},
            },
        ]
    )
    traffic_json = json.dumps(
        [
            {"revisionName": "feedbackpulse-api--rev2", "weight": 100},
            {"revisionName": "feedbackpulse-api--rev1", "weight": 0},
        ]
    )

    def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if "revision" in cmd and "list" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=revisions_json, stderr="")
        if "show" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=traffic_json, stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unknown")

    adapter = AzureContainerAppAdapter(
        resource_group="test-rg", app_name="test-app", command_runner=mock_runner
    )
    revs = adapter.list_revisions()
    assert len(revs) == 2
    assert revs[1].name == "feedbackpulse-api--rev2"
    assert revs[1].traffic_weight == 100

    active_rev = adapter.get_active_revision()
    assert active_rev == "feedbackpulse-api--rev2"


def test_azure_adapter_traffic_weights_and_rollback():
    captured_commands: list[list[str]] = []

    def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        captured_commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    adapter = AzureContainerAppAdapter(
        resource_group="test-rg", app_name="test-app", command_runner=mock_runner
    )

    # Valid weights: 50 / 50
    ok = adapter.set_traffic_weights(
        {"feedbackpulse-api--rev1": 50, "feedbackpulse-api--rev2": 50}
    )
    assert ok is True
    assert "--revision-weight" in captured_commands[0]

    # Rollback to rev1 (shifts 100% to rev1)
    rollback_ok = adapter.rollback_to_revision("feedbackpulse-api--rev1")
    assert rollback_ok is True
    assert "feedbackpulse-api--rev1=100" in captured_commands[1]

    # Invalid weights (sum != 100) must raise ValueError
    with pytest.raises(ValueError, match="must equal 100"):
        adapter.set_traffic_weights({"feedbackpulse-api--rev1": 70})


# ==============================================================================
# 2. Template Structure & Sizing Policy Tests
# ==============================================================================


def test_template_file_exists():
    assert TEMPLATE_PATH.is_file(), "cloudlayer/containerapp.template.yaml must exist"


def test_template_no_plaintext_secrets_hardcoded():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "${SERVICE_TOKEN}" in content
    assert "${REGISTRY_IDENTITY_ID}" in content
    assert "REGISTRY_PASSWORD" not in content
    assert "passwordSecretRef" not in content
    assert "acr-password" not in content
    # Ensure no accidentally hardcoded credentials
    assert "ghp_" not in content
    assert "eyJ" not in content


def test_render_containerapp_yaml_valid():
    _rendered, parsed = render_containerapp_yaml(DUMMY_ENV)
    assert isinstance(parsed, dict)
    assert parsed["properties"]["managedEnvironmentId"] == DUMMY_ENV["MANAGED_ENV_ID"]
    assert parsed["properties"]["configuration"]["activeRevisionsMode"] == "Multiple"

    # Verify secrets mapping
    secrets = parsed["properties"]["configuration"]["secrets"]
    secret_map = {s["name"]: s["value"] for s in secrets}
    assert secret_map["service-token"] == DUMMY_ENV["SERVICE_TOKEN"]
    assert set(secret_map) == {"service-token"}
    assert parsed["identity"] == {
        "type": "UserAssigned",
        "userAssignedIdentities": {DUMMY_ENV["REGISTRY_IDENTITY_ID"]: {}},
    }
    assert parsed["properties"]["configuration"]["registries"] == [{
        "server": DUMMY_ENV["REGISTRY_SERVER"],
        "identity": DUMMY_ENV["REGISTRY_IDENTITY_ID"],
    }]


def test_infra_sizing_constraints():
    _, parsed = render_containerapp_yaml(DUMMY_ENV)
    container = parsed["properties"]["template"]["containers"][0]
    resources = container["resources"]
    assert resources["cpu"] == 1.0, "Must be 1.0 vCPU"
    assert resources["memory"] == "2.0Gi", "Must be 2.0Gi memory"

    scale = parsed["properties"]["template"]["scale"]
    assert scale["minReplicas"] == 0, "Must scale to zero when idle"
    assert scale["maxReplicas"] <= 3, "Max replicas capped for budget protection"


def test_infra_probe_endpoints():
    _, parsed = render_containerapp_yaml(DUMMY_ENV)
    container = parsed["properties"]["template"]["containers"][0]
    probes = container["probes"]
    probe_map = {p["type"]: p for p in probes}

    assert "Liveness" in probe_map
    assert probe_map["Liveness"]["httpGet"]["path"] == "/health"
    assert probe_map["Liveness"]["httpGet"]["port"] == 8000

    assert "Readiness" in probe_map
    assert probe_map["Readiness"]["httpGet"]["path"] == "/ready"
    assert probe_map["Readiness"]["httpGet"]["port"] == 8000


@pytest.mark.parametrize("setting", REQUIRED_VARS)
@pytest.mark.parametrize("value", [None, "", " \t"])
def test_infra_missing_required_env_raises(setting, value):
    incomplete_env = dict(DUMMY_ENV)
    if value is None:
        del incomplete_env[setting]
    else:
        incomplete_env[setting] = value

    with pytest.raises(ValueError, match="Missing required environment variables"):
        render_containerapp_yaml(incomplete_env)


def test_renderer_rejects_old_example_token():
    with pytest.raises(ValueError, match="old example value"):
        render_containerapp_yaml({**DUMMY_ENV, "SERVICE_TOKEN": "test-service-token-secret-12345"})


@pytest.mark.parametrize("identity", ["client-id", "system", "/subscriptions/sub/resourceGroups/rg"])
def test_renderer_rejects_invalid_identity_resource_id(identity):
    with pytest.raises(ValueError, match="user-assigned identity resource ID"):
        render_containerapp_yaml({**DUMMY_ENV, "REGISTRY_IDENTITY_ID": identity})


def test_renderer_accepts_azure_registry_variable_names():
    env = dict(DUMMY_ENV)
    env["AZURE_REGISTRY_SERVER"] = env.pop("REGISTRY_SERVER")
    env["AZURE_REGISTRY_IDENTITY_ID"] = env.pop("REGISTRY_IDENTITY_ID")
    _, parsed = render_containerapp_yaml(env)
    assert parsed["properties"]["configuration"]["registries"][0]["identity"] == (
        DUMMY_ENV["REGISTRY_IDENTITY_ID"]
    )


@pytest.mark.parametrize("token", ['token-"quoted"', r"token-\backslash", "token\nsecond-line",
                                   "literal-${IMAGE_TAG}-token", "$(do-not-execute)"])
def test_renderer_preserves_token_as_data(token):
    _, parsed = render_containerapp_yaml({**DUMMY_ENV, "SERVICE_TOKEN": token})
    assert parsed["properties"]["configuration"]["secrets"] == [
        {"name": "service-token", "value": token}
    ]


@pytest.mark.parametrize("change", ["missing-attachment", "different-identity", "password"])
def test_validation_rejects_invalid_registry_authentication(change):
    _, parsed = render_containerapp_yaml(DUMMY_ENV)
    registry = parsed["properties"]["configuration"]["registries"][0]
    if change == "missing-attachment":
        parsed.pop("identity")
    elif change == "different-identity":
        registry["identity"] = DUMMY_ENV["REGISTRY_IDENTITY_ID"] + "-other"
    else:
        registry["passwordSecretRef"] = "acr-password"
    with pytest.raises(ValueError, match="identity"):
        validate_config_structure(parsed)


def test_renderer_cli_masks_token_in_stdout():
    token = 'sensitive-"quoted"-tail-${IMAGE_TAG}'
    result = subprocess.run(
        [sys.executable, str(TEMPLATE_PATH.with_name("render_config.py"))],
        env={**os.environ, **DUMMY_ENV, "SERVICE_TOKEN": token},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "***MASKED***" in result.stdout
    assert "sensitive-" not in result.stdout + result.stderr
    assert "quoted" not in result.stdout + result.stderr


def test_renderer_validation_only_needs_no_azure_settings():
    result = subprocess.run(
        [sys.executable, str(TEMPLATE_PATH.with_name("render_config.py")), "--validate-only"],
        env={}, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASSED" in result.stdout


def test_validation_rejects_invalid_sizing():
    _, parsed = render_containerapp_yaml(DUMMY_ENV)
    parsed["properties"]["template"]["containers"][0]["resources"]["cpu"] = 4.0
    with pytest.raises(ValueError, match="CPU resource must be 1.0 vCPU"):
        validate_config_structure(parsed)


def test_validation_rejects_missing_probes():
    _, parsed = render_containerapp_yaml(DUMMY_ENV)
    parsed["properties"]["template"]["containers"][0]["probes"] = []
    with pytest.raises(ValueError, match="Missing or invalid Liveness probe"):
        validate_config_structure(parsed)
