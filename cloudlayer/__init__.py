"""Cloud Adapter layer for FeedbackPulse.

Provides cloud-agnostic interfaces (CloudDeploymentAdapter) and concrete Azure implementations
(AzureContainerAppAdapter) per docs/plans/P01-T03-system-structure.md section 4.
"""

from cloudlayer.adapter import CloudDeploymentAdapter, RevisionInfo
from cloudlayer.azure_adapter import AzureContainerAppAdapter

__all__ = [
    "AzureContainerAppAdapter",
    "CloudDeploymentAdapter",
    "RevisionInfo",
]
