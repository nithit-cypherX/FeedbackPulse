"""Configuration renderer and validator for Azure Container Apps.

Reads cloudlayer/containerapp.template.yaml and substitutes environment variables
while strictly validating required parameters, resource boundaries, and probe paths.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

TEMPLATE_PATH = Path(__file__).parent / "containerapp.template.yaml"

REQUIRED_VARS = [
    "MANAGED_ENV_ID",
    "SERVICE_TOKEN",
    "REGISTRY_SERVER",
    "REGISTRY_IDENTITY_ID",
    "IMAGE_TAG",
]


def validate_config_structure(config: dict[str, Any]) -> None:
    """Validate that the parsed YAML strictly follows FeedbackPulse constraints."""
    properties = config.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("Missing 'properties' root block in YAML config")

    configuration = properties.get("configuration")
    if not isinstance(configuration, dict):
        raise TypeError("Missing 'properties.configuration' block")

    identity = config.get("identity", {})
    assigned = identity.get("userAssignedIdentities", {})
    registries = configuration.get("registries", [])
    if identity.get("type") != "UserAssigned" or not assigned:
        raise ValueError("A user-assigned registry identity must be attached to the app")
    if not registries or any(
        registry.get("identity") not in assigned
        or "username" in registry
        or "passwordSecretRef" in registry
        for registry in registries
    ):
        raise ValueError("Registry authentication must use the attached managed identity")

    # Ingress checks
    ingress = configuration.get("ingress", {})
    if ingress.get("targetPort") != 8000:
        raise ValueError(f"Expected ingress targetPort=8000, got {ingress.get('targetPort')}")
    if not ingress.get("external"):
        raise ValueError("Ingress must be external")

    # Template and container checks
    template = properties.get("template")
    if not isinstance(template, dict):
        raise TypeError("Missing 'properties.template' block")

    containers = template.get("containers", [])
    if not containers or not isinstance(containers, list):
        raise ValueError("Template must contain at least one container")

    app_container = containers[0]
    resources = app_container.get("resources", {})
    if resources.get("cpu") != 1.0:
        raise ValueError(f"CPU resource must be 1.0 vCPU, got {resources.get('cpu')}")
    if resources.get("memory") != "2.0Gi":
        raise ValueError(f"Memory resource must be 2.0Gi, got {resources.get('memory')}")

    # Probes checks
    probes = app_container.get("probes", [])
    probe_map = {p.get("type"): p.get("httpGet", {}) for p in probes if isinstance(p, dict)}

    if "Liveness" not in probe_map or probe_map["Liveness"].get("path") != "/health":
        raise ValueError("Missing or invalid Liveness probe (must target /health on port 8000)")
    if "Readiness" not in probe_map or probe_map["Readiness"].get("path") != "/ready":
        raise ValueError("Missing or invalid Readiness probe (must target /ready on port 8000)")

    # Scale checks
    scale = template.get("scale", {})
    if scale.get("minReplicas") != 0:
        raise ValueError(f"Scale minReplicas must be 0 for scale-to-zero, got {scale.get('minReplicas')}")
    if scale.get("maxReplicas", 999) > 3:
        raise ValueError(f"Scale maxReplicas must not exceed 3, got {scale.get('maxReplicas')}")


def render_containerapp_yaml(
    env_vars: dict[str, str],
    template_path: Path = TEMPLATE_PATH,
    allow_placeholders: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Substitute template placeholders with env_vars and validate."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found at {template_path}")

    env = dict(env_vars)
    if "REGISTRY_SERVER" not in env and "AZURE_REGISTRY_SERVER" in env:
        env["REGISTRY_SERVER"] = env["AZURE_REGISTRY_SERVER"]
    if "REGISTRY_IDENTITY_ID" not in env and "AZURE_REGISTRY_IDENTITY_ID" in env:
        env["REGISTRY_IDENTITY_ID"] = env["AZURE_REGISTRY_IDENTITY_ID"]

    raw_template = template_path.read_text(encoding="utf-8")

    # Check for missing variables unless placeholders are explicitly allowed
    missing = [var for var in REQUIRED_VARS if not env.get(var, "").strip()]
    if missing and not allow_placeholders:
        raise ValueError(f"Missing required environment variables for rendering: {', '.join(missing)}")

    if env.get("SERVICE_TOKEN") == "test-service-token-secret-12345":
        raise ValueError("SERVICE_TOKEN must not use the old example value")
    registry_identity = env.get("REGISTRY_IDENTITY_ID", "")
    if registry_identity and not re.fullmatch(
        r"/subscriptions/[^/\s]+/resourceGroups/[^/\s]+/providers/"
        r"Microsoft\.ManagedIdentity/userAssignedIdentities/[^/\s]+",
        registry_identity,
        flags=re.IGNORECASE,
    ):
        raise ValueError("REGISTRY_IDENTITY_ID must be a user-assigned identity resource ID")

    # Replace quoted YAML scalars once: quotes/newlines in a token remain data,
    # and a token containing another placeholder is not substituted a second time.
    pattern = r'"\$\{(' + "|".join(REQUIRED_VARS) + r')\}"'
    rendered = re.sub(
        pattern,
        lambda match: json.dumps(env.get(match[1], f"${{{match[1]}}}")),
        raw_template,
    )

    parsed = yaml.safe_load(rendered)
    validate_config_structure(parsed)

    return rendered, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Render and validate Azure Container Apps YAML")
    parser.add_argument("--output", "-o", type=Path, help="Output rendered YAML path")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate template structure with dummy values without writing",
    )
    args = parser.parse_args()

    env_vars = dict(os.environ)

    if args.validate_only:
        dummy_vars = {
            "MANAGED_ENV_ID": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/env",
            "SERVICE_TOKEN": "dummy-token-for-validation",
            "REGISTRY_SERVER": "example.azurecr.io",
            "REGISTRY_IDENTITY_ID": "/subscriptions/sub/resourceGroups/rg/providers/"
            "Microsoft.ManagedIdentity/userAssignedIdentities/pull-identity",
            "IMAGE_TAG": "example.azurecr.io/feedbackpulse:test",
        }
        try:
            render_containerapp_yaml(dummy_vars)
            print("Template structure and constraint validation: PASSED")
            return 0
        except (ValueError, TypeError, FileNotFoundError) as exc:
            print(f"Validation FAILED: {exc}", file=sys.stderr)
            return 1

    try:
        rendered_content, _ = render_containerapp_yaml(env_vars)
    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered_content, encoding="utf-8")
        print(f"Rendered configuration written to {args.output}")
    else:
        # Mask secrets before printing to stdout
        masked = yaml.safe_load(rendered_content)
        for secret in masked["properties"]["configuration"].get("secrets", []):
            if "value" in secret:
                secret["value"] = "***MASKED***"
        print(yaml.safe_dump(masked, sort_keys=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
