"""Cloud Adapter interface protocol for FeedbackPulse.

Per docs/plans/P01-T03-system-structure.md section 4:
Core application logic in src/ must remain strictly cloud-agnostic.
All cloud-specific interactions (deployment, revision management, traffic routing)
are isolated in this adapter layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RevisionInfo:
    """Metadata for a deployed container revision."""

    name: str
    active: bool
    traffic_weight: int
    created_time: str | None = None


@runtime_checkable
class CloudDeploymentAdapter(Protocol):
    """Abstract interface for cloud container deployment and revision management."""

    def get_service_url(self) -> str | None:
        """Return the public FQDN URL for the service, or None if not deployed."""
        ...

    def get_active_revision(self) -> str | None:
        """Return the name of the revision currently receiving 100% traffic."""
        ...

    def list_revisions(self) -> list[RevisionInfo]:
        """List all revisions and their current traffic allocations."""
        ...

    def set_traffic_weights(self, weights: dict[str, int]) -> bool:
        """Route traffic according to the specified revision weights (must sum to 100)."""
        ...

    def rollback_to_revision(self, revision_name: str) -> bool:
        """Shift 100% of traffic back to the specified revision."""
        ...
