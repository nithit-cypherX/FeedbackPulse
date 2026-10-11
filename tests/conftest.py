"""Explicit test-only configuration for the API's module-level app."""

import os

# Set before test collection imports feedbackpulse.api; this is not a runtime default.
os.environ.setdefault("SERVICE_TOKEN", "pytest-only-service-token")
