"""Configuration module for FeedbackPulse service.

Separates environment and configuration loading from core inference logic,
per docs/plans/P01-T03-system-structure.md section 4.
"""

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL_VERSION = "sentiment-6e7ff9fbc17c-0110c462"
DEFAULT_ARTIFACT_DIR = Path("artifacts/sentiment-6e7ff9fbc17c/model")
REGISTRY_DIR = Path("reports/registry")


def get_default_model_version() -> str:
    """Read the latest registered model version from reports/registry if available."""
    if REGISTRY_DIR.is_dir():
        entries = sorted(REGISTRY_DIR.glob("sentiment-*.json"))
        if entries:
            return entries[-1].stem
    return DEFAULT_MODEL_VERSION


def get_default_model_dir() -> Path:
    """Resolve the default model directory.

    Prefers the local packaged artifact directory. If not packaged yet,
    falls back to downloading/locating via huggingface snapshot.
    """
    if DEFAULT_ARTIFACT_DIR.is_dir():
        return DEFAULT_ARTIFACT_DIR
    from feedbackpulse.model_files import ensure_model_files

    return ensure_model_files()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration settings."""

    service_token: str
    model_dir: Path
    model_version: str
    host: str = "0.0.0.0"
    port: int = 8000


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Load settings from environment variables or sensible defaults."""
    env = os.environ if environ is None else environ

    service_token = env.get("SERVICE_TOKEN", "test-service-token")

    model_dir_raw = env.get("MODEL_DIR")
    if model_dir_raw:
        model_dir = Path(model_dir_raw)
    else:
        model_dir = get_default_model_dir()

    model_version = env.get("MODEL_VERSION") or get_default_model_version()
    host = env.get("HOST", "0.0.0.0")
    port = int(env.get("PORT", "8000"))

    return Settings(
        service_token=service_token,
        model_dir=model_dir,
        model_version=model_version,
        host=host,
        port=port,
    )
