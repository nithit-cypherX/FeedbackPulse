"""Azure Container Apps implementation of CloudDeploymentAdapter.

Handles Azure-specific CLI commands, revision inspections, and traffic shifting
for safe releases and rollbacks (P04-T01, P04-T03, P04-T05).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from cloudlayer.adapter import CloudDeploymentAdapter, RevisionInfo

logger = logging.getLogger("feedbackpulse.cloudlayer.azure")


class AzureContainerAppAdapter(CloudDeploymentAdapter):
    """Adapter for managing Azure Container Apps revisions and deployments."""

    def __init__(
        self,
        resource_group: str = "itcs355-6688166",
        app_name: str = "feedbackpulse-api",
        command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.resource_group = resource_group
        self.app_name = app_name
        self._runner = command_runner or self._default_runner

    def _default_runner(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        az_bin = shutil.which("az") or "/opt/homebrew/bin/az"
        full_cmd = [az_bin, *cmd]
        return subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

    def get_service_url(self) -> str | None:
        """Fetch the public HTTPS FQDN of the container app."""
        cmd = [
            "containerapp",
            "show",
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "--query",
            "properties.configuration.ingress.fqdn",
            "-o",
            "tsv",
        ]
        proc = self._runner(cmd)
        if proc.returncode == 0 and proc.stdout.strip():
            fqdn = proc.stdout.strip()
            return f"https://{fqdn}"
        return None

    def list_revisions(self) -> list[RevisionInfo]:
        """Query Azure Container Apps for all revisions and their traffic share."""
        # 1. Fetch traffic split rules from ingress
        ingress_cmd = [
            "containerapp",
            "show",
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "--query",
            "properties.configuration.ingress.traffic",
            "-o",
            "json",
        ]
        ingress_proc = self._runner(ingress_cmd)
        traffic_map: dict[str, int] = {}
        if ingress_proc.returncode == 0 and ingress_proc.stdout.strip():
            try:
                traffic_list = json.loads(ingress_proc.stdout)
                for entry in traffic_list:
                    rev = entry.get("revisionName")
                    weight = entry.get("weight", 0)
                    if rev:
                        traffic_map[rev] = weight
            except json.JSONDecodeError:
                logger.warning("Failed to parse ingress traffic JSON")

        # 2. Fetch revision list
        rev_cmd = [
            "containerapp",
            "revision",
            "list",
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "-o",
            "json",
        ]
        rev_proc = self._runner(rev_cmd)
        if rev_proc.returncode != 0:
            logger.error("Failed to list revisions: %s", rev_proc.stderr)
            return []

        results: list[RevisionInfo] = []
        try:
            revisions_data = json.loads(rev_proc.stdout)
            for item in revisions_data:
                name = item.get("name", "")
                active = item.get("properties", {}).get("active", False)
                created = item.get("properties", {}).get("createdTime")
                weight = traffic_map.get(name, 0)
                results.append(
                    RevisionInfo(
                        name=name,
                        active=active,
                        traffic_weight=weight,
                        created_time=created,
                    )
                )
        except json.JSONDecodeError:
            logger.error("Invalid JSON from az containerapp revision list")

        return results

    def get_active_revision(self) -> str | None:
        """Find the revision that currently receives 100% traffic."""
        revisions = self.list_revisions()
        for rev in revisions:
            if rev.traffic_weight == 100:
                return rev.name
        # Fallback: if no 100% split, return first active revision with non-zero traffic
        for rev in revisions:
            if rev.traffic_weight > 0:
                return rev.name
        return None

    def set_traffic_weights(self, weights: dict[str, int]) -> bool:
        """Set traffic allocation across revisions (weights must sum to 100)."""
        total = sum(weights.values())
        if total != 100:
            raise ValueError(f"Total revision traffic weights must equal 100, got {total}")

        weight_args = [f"{rev}={weight}" for rev, weight in weights.items()]
        cmd = [
            "containerapp",
            "ingress",
            "traffic",
            "set",
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "--revision-weight",
            *weight_args,
        ]
        proc = self._runner(cmd)
        if proc.returncode != 0:
            logger.error("Failed to set traffic weights: %s", proc.stderr)
            return False
        return True

    def rollback_to_revision(self, revision_name: str) -> bool:
        """Shift 100% traffic to the specified target revision."""
        logger.info("Initiating rollback to revision '%s'...", revision_name)
        return self.set_traffic_weights({revision_name: 100})

    def deploy_config(self, yaml_path: Path | str) -> bool:
        """Deploy or update Container App using rendered YAML configuration."""
        path = str(yaml_path)
        # Check if app exists
        check_cmd = [
            "containerapp",
            "show",
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "--query",
            "name",
            "-o",
            "tsv",
        ]
        exists = self._runner(check_cmd).returncode == 0

        action = "update" if exists else "create"
        cmd = [
            "containerapp",
            action,
            "-n",
            self.app_name,
            "-g",
            self.resource_group,
            "--yaml",
            path,
        ]
        proc = self._runner(cmd)
        if proc.returncode != 0:
            logger.error("Deployment failed: %s", proc.stderr)
            return False
        return True
