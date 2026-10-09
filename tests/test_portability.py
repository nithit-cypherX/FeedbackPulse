"""Automated Portability Audit (docs/plans/P01-T03-system-structure.md §10).

Verifies that the core application (src/) maintains strict portability:
1. Core application code must never import cloudlayer or any cloud SDK (azure, boto3, google.cloud).
2. Cloudlayer isolates all cloud provider code and adapters.
3. Core configuration in config.py only reads environment variables without cloud SDK dependencies.
"""

import ast
from pathlib import Path

FORBIDDEN_CORE_IMPORTS = {
    "cloudlayer",
    "azure",
    "azure.mgmt",
    "azure.identity",
    "boto3",
    "botocore",
    "google.cloud",
}

SRC_DIR = Path(__file__).parent.parent / "src"
CLOUDLAYER_DIR = Path(__file__).parent.parent / "cloudlayer"


def _extract_imported_modules(py_file: Path) -> set[str]:
    """Parse a python file into an AST and extract all top-level imported module names."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    return modules


def test_core_code_does_not_import_cloudlayer_or_cloud_sdks():
    """Verify that no python module in src/ imports cloudlayer or external cloud SDKs."""
    src_files = list(SRC_DIR.glob("**/*.py"))
    assert src_files, f"No python files found in {SRC_DIR}"

    violations: list[str] = []
    for py_file in src_files:
        imports = _extract_imported_modules(py_file)
        for imp in imports:
            root_module = imp.split(".")[0]
            if root_module in FORBIDDEN_CORE_IMPORTS or imp in FORBIDDEN_CORE_IMPORTS:
                violations.append(f"{py_file.relative_to(SRC_DIR.parent)} imports '{imp}'")

    assert not violations, (
        "Portability violation: core logic must not depend on cloudlayer or cloud SDKs:\n"
        + "\n".join(violations)
    )


def test_cloudlayer_contains_adapter_and_concrete_azure():
    """Verify that cloudlayer exists and exports both protocol and concrete implementations."""
    from cloudlayer.adapter import CloudDeploymentAdapter
    from cloudlayer.azure_adapter import AzureContainerAppAdapter

    assert issubclass(AzureContainerAppAdapter, CloudDeploymentAdapter)


def test_core_can_run_locally_without_cloudlayer():
    """Verify that the FastAPI app and inference module initialize with zero cloudlayer imports."""
    from feedbackpulse.api import create_app
    from feedbackpulse.config import Settings

    dummy_settings = Settings(
        service_token="local-token",
        model_dir=Path("tests"),  # dummy path for unit test
        model_version="test-v1",
    )
    # create_app should construct cleanly with no cloud dependencies
    app = create_app(settings=dummy_settings)
    assert app.title == "FeedbackPulse"
