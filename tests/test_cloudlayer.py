"""Tests for Cloud Adapter and Azure Container Apps Configuration (Phase P04-T01).

Validates:
1. CloudDeploymentAdapter protocol conformance.
2. AzureContainerAppAdapter operations (service url, revision listing, traffic splitting, rollback).
3. Declarative Container App template structure and constraint policies.
"""

import json
import subprocess

import pytest

from cloudlayer.adapter import CloudDeploymentAdapter
from cloudlayer.azure_adapter import AzureContainerAppAdapter
from cloudlayer.render_config import (
    TEMPLATE_PATH,
    render_containerapp_yaml,
    validate_config_structure,
)

DUMMY_ENV = {
    "MANAGED_ENV_ID": "/subscriptions/0000/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env",
    "SERVICE_TOKEN": "test-service-token-secret-12345",
    "REGISTRY_SERVER": "itcs3556688166.azurecr.io",
    "REGISTRY_USERNAME": "itcs3556688166",
    "REGISTRY_PASSWORD": "dummy-registry-password",
    "IMAGE_TAG": "itcs3556688166.azurecr.io/feedbackpulse:test-tag",
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
    assert "${REGISTRY_PASSWORD}" in content
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
    assert secret_map["acr-password"] == DUMMY_ENV["REGISTRY_PASSWORD"]


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


def test_infra_missing_required_env_raises():
    incomplete_env = dict(DUMMY_ENV)
    del incomplete_env["SERVICE_TOKEN"]

    with pytest.raises(ValueError, match="Missing required environment variables"):
        render_containerapp_yaml(incomplete_env)


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
