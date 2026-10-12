# FeedbackPulse — Cloud Adapter & Infrastructure (`cloudlayer/`)

Documentation and usage guide for FeedbackPulse's **cloud adapter** and infrastructure on **Azure Container Apps (Consumption plan)**, phase **P04-T01**.

Follows [docs/plans/P01-T03-system-structure.md §4 and §6](../docs/plans/P01-T03-system-structure.md):
- **Core (`src/`):** cloud-independent; no cloud SDK imports.
- **Configuration (`src/feedbackpulse/config.py`):** reads environment variables; it does not load `.env` automatically. The Makefile loads `cloud.env` when present and exports its settings to commands.
- **Cloud adapter (`cloudlayer/`):** keeps cloud calls and management separate from core code.

---

## 1. Cloud Adapter Architecture

`cloudlayer/` uses the Adapter Pattern:

- **`CloudDeploymentAdapter` (`cloudlayer/adapter.py`):** protocol interface for deployment, revision inspection, traffic splitting and rollback.
- **`AzureContainerAppAdapter` (`cloudlayer/azure_adapter.py`):** implementation using Azure CLI.
  - `get_service_url()`: returns the Container App's HTTPS FQDN.
  - `list_revisions()`: lists revisions and traffic percentages.
  - `get_active_revision()`: returns the revision receiving 100% traffic.
  - `set_traffic_weights(weights)`: adjusts traffic between revisions.
  - `rollback_to_revision(revision_name)`: routes 100% of traffic back to the target revision (zero-downtime rollback).
  - `deploy_config(yaml_path)`: deploys/updates from YAML configuration.

---

## 2. Infrastructure Sizing & Configuration

FeedbackPulse packages the model and REST API in one container on **Azure Container Apps**:

- **Target:** explicitly set the Resource Group, ACR, Container Apps Environment and App using [cloud.env.example](../cloud.env.example). `make deploy` and CD require explicit deployment settings. The Malaysia West deployment passed CI #11/CD #9 and post-deployment checks on 11 October 2026; see the [recorded P04 result](../docs/plans/P04-deployment-and-cicd.md#deployment-history--wait-for-revision-readiness-before-passing-cd--2026-10-11). This is dated evidence, not a live service-status check. Older operational scripts can still have East Asia defaults; check their targets before use.
- **Sizing:** 1.0 vCPU / 2.0 GiB RAM, based on the 645.8 MiB container measurement and USD 15 budget.
- **Scale:** `minReplicas: 0` (scale to zero when idle), `maxReplicas: 3`.
- **Revisions Mode:** `Multiple`, for zero-downtime rollback.
- **Ingress:** external HTTPS, port 8000.

---

## 3. Health & Readiness Probes

Follows the [API contract](../docs/plans/P01-T02-api-contract.md) and [System Structure](../docs/plans/P01-T03-system-structure.md):

| Probe Type | Endpoint | Interval | Initial Delay | Threshold | Purpose |
|---|---|---|---|---|---|
| **Liveness** | `GET /health` | 15s | 10s | 3 | Check that the web-server process (uvicorn) responds |
| **Readiness** | `GET /ready` | 10s | 15s | 3 | Check that the model is loaded and ready to predict: 200 when ready, 503 otherwise |

---

## 4. Secret handling (Zero Leaked Credentials)

- **Never bake secrets into the Docker image or Git repository.** Set your own `SERVICE_TOKEN`, not the old sample value. CD reads it from a production Environment secret and passes it to a Container App Secret.
- Image pulls use a user-assigned managed identity set through `AZURE_REGISTRY_IDENTITY_ID` (resource ID, not client ID). Prepare the identity and `AcrPull` first. No ACR username/password or admin account is needed. See [Microsoft Learn](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull).
- CD uses repository variables `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP_ENV`, `AZURE_CONTAINER_APP_NAME`, `AZURE_REGISTRY_NAME`, `AZURE_REGISTRY_SERVER`, `AZURE_REGISTRY_IDENTITY_ID`. Login uses production secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. Missing required settings stop it before later steps. `FEEDBACKPULSE_CD_ENABLED` must be enabled separately; editing files does not enable it.
- `cloudlayer/render_config.py` only validates/renders the template; it creates no identities/roles. `make deploy` and CD remove temporary token-containing YAML after use. `--validate-only` uses dummy values and does not prove Azure permissions or deployment.

---

## 5. Related files

- `cloudlayer/adapter.py`: cloud-deployment adapter protocol interface.
- `cloudlayer/azure_adapter.py`: Azure Container Apps Adapter implementation
- `cloudlayer/containerapp.template.yaml`: Infrastructure as Code (IaC) configuration for deploying/updating the Container App, so environment and deployment settings can be reproduced.
- `cloudlayer/render_config.py`: validates schema, sizing and probes, then renders the template.
- `Makefile`: one entry point for Docker, cloud provisioning, deployment, status and rollback commands.
- `tests/test_cloudlayer.py`: unit tests for the adapter, template structure and constraints.
- `tests/test_portability.py`: automated audit checking that core `src/` does not depend on cloud SDKs/adapters.

---

## 6. Usage through Makefile

### 6.1 Validate without changing cloud resources (dry run)
```bash
make dry-run
```

### 6.2 Push a linux/amd64 image to ACR
```bash
make docker-push
```

### 6.3 Deploy or update the real Container App
```bash
make deploy
```

### 6.4 Check status and revisions
```bash
make status
```

### Optional: run cloudlayer and portability tests
```bash
uv run pytest tests/test_cloudlayer.py tests/test_portability.py
```
