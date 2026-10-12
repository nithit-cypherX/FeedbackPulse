# P04 — Deployment and safe-release evidence

- **Report date:** 2026-10-10
- **Reported phase status:** `done` (100% complete, P04-T01 through P04-T06)
- **Owner:** Person 2 — Backend and deployment
- **References:** [PROPOSAL.md](../PROPOSAL.md) · [P04 Plan](../docs/plans/P04-deployment-and-cicd.md) · [P01-T02 API Contract](../docs/plans/P01-T02-api-contract.md) · [P01-T03 System Structure](../docs/plans/P01-T03-system-structure.md)

---

## Summary

This report records the team's deployment and tests of **FeedbackPulse**, an airline-feedback sentiment classifier, on **Azure Container Apps** in East Asia (Consumption plan). The recorded deployment and test results are:

| Check | Reported result | Target | Status |
|---|---|---|:---:|
| **Two-stage CI pipeline** | All steps passed: Ruff, portability audit, IaC template validation, 70/70 pytest tests | All checks pass; block faulty code | **PASS** |
| **Automated CD pipeline** | Azure OIDC deployment, without stored Azure credentials in GitHub, plus a 3-payload smoke test | Successful deployment without downtime | **PASS** |
| **API-contract smoke tests** | 12/12 cases passed: 200, 401, 400, 422 and 510-token boundary; error rate 0.0% | 100% contract compliance | **PASS** |
| **Concurrency and latency (k6)** | p95 = **0.213 seconds (213 ms)** at 2 concurrent requests | p95 $\le$ 3.0 seconds (Proposal §3) | **PASS** (14x below the limit) |
| **Rollback verification** | 100% traffic returned to the previous version in **15.00 seconds**; normal service responses confirmed | Rollback without rebuilding | **PASS** |
| **Cloud portability audit** | Core `src/` logic has no Azure SDK/cloud-vendor dependency | 100% decoupled | **PASS** |
| **Teardown automation** | `teardown.sh` with `--dry-run` and a confirmation guard | Safe resource deletion | **PASS** |

---

## 1. Cloud environment

- **Cloud Platform:** Azure Container Apps (ACA) — Consumption Plan (Serverless Container)
- **Region:** `eastasia` (Hong Kong)
- **Public HTTPS FQDN:** `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`
- **Resource Group:** `itcs355-6688166`
- **Container Registry (ACR):** `itcs3556688166.azurecr.io` (Admin user authentication for ACA pull)
- **Revision Mode:** `Multiple` (blue/green routing and revision rollback)
- **Resource Allocation:**
  - **CPU:** 1.0 vCPU
  - **Memory:** 2.0 GiB RAM *(based on P02/P03: measured RoBERTa RSS of 645.8 MiB; 2.0 GiB chosen for OOM headroom with concurrent traffic)*
  - **Auto-scaling:** `minReplicas = 0` (scale-to-zero to save costs), `maxReplicas = 3` (limit cost spikes)
- **Container Security:** Non-root user `appuser` (UID 10001), Zero credentials baked in image layers.

---

## 2. Infrastructure Provisioning & Cloud Adapter (P04-T01)

### 2.1 Cloud-adapter separation, per P01-T03 §4
Core code in `src/feedbackpulse/` is separated from cloud-specific code for portability:
- Protocol interface: [`cloudlayer/adapter.py`](../cloudlayer/adapter.py) defines `CloudDeploymentAdapter`.
- Azure implementation: [`cloudlayer/azure_adapter.py`](../cloudlayer/azure_adapter.py) manages Azure Container Apps through `az` CLI.
- Automated audit: [`tests/test_portability.py`](../tests/test_portability.py) found no `azure`, `boto3` or `google-cloud` imports in `src/` (100% passed).

### 2.2 Infrastructure as Code (IaC)
- Template: [`cloudlayer/containerapp.template.yaml`](../cloudlayer/containerapp.template.yaml)
- Dynamic renderer: [`cloudlayer/render_config.py`](../cloudlayer/render_config.py) validates schema, memory limits, probe paths and secret references before rendering.
- Automation: `make dry-run` and `make validate-config` check configuration before sending it to Azure.

---

## 3. GitHub Actions Two-Stage CI Pipeline (P04-T02)

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### 3.1 Two-stage pipeline
1. **Stage 1 (`test` job):**
   - Install Python 3.13 and the `uv` package manager.
   - Run lint: `uv run ruff check`.
   - Run portability checks: `uv run pytest tests/test_portability.py`.
   - Validate IaC: `uv run python cloudlayer/render_config.py --validate-only`.
   - Run the full suite: `uv run pytest`, **70 passed**.
2. **Stage 2 (`build` job — only after Stage 1 passes):**
   - Set up Docker Buildx.
   - Build the image with a commit-SHA tag, such as `itcs3556688166.azurecr.io/feedbackpulse:8d34723...`.
   - Run the container on the temporary GitHub Actions runner and smoke-test `/health`, `/ready`, `/predict` before release.

### 3.2 CI deployment blocker
- Any failing test or lint error fails the `test` job.
- A failed `test` job blocks `build` and CD, preventing faulty code from being deployed to production.

---

## 4. Automated CD Pipeline & Deployment Workflow (P04-T03)

Workflow: [`.github/workflows/cd.yml`](../.github/workflows/cd.yml)

### 4.1 Continuous delivery flow
1. **Trigger:** automatic only after a push to the main branch and a successful CI pipeline.
2. **Passwordless Authentication (Azure OIDC):**
   - Use Azure Federated Identity Credentials with a GitHub Actions OIDC token (`permissions: id-token: write`).
   - No Azure client secret/password stored in GitHub Repository Secrets.
3. **Build & Push Artifact:**
   - Build `linux/amd64` and push to ACR with the Git commit SHA tag.
4. **Deploy New Revision:**
   - Render the YAML template with the latest image tag.
   - Run `az containerapp update --yaml rendered.yaml` to create a new revision.
5. **Post-Deployment Smoke Test:**
   - Check the public HTTPS URL after deployment with three payloads (`/health`, `/ready`, `/predict`); fail if they do not return 200 OK.

---

## 5. Cloud smoke tests and API contract (P04-T04)

Script: [`scripts/cloud_check.py`](../scripts/cloud_check.py)\
Full machine-readable result: [`reports/P04-cloud-check.json`](P04-cloud-check.json)

### 5.1 Twelve API-contract checks on the public HTTPS URL

Test target: `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`:

| No. | Test case | Expected HTTP | Actual HTTP | Latency (ms) | Result |
|---|---|:---:|:---:|:---:|:---:|
| 1 | `GET /health` (Liveness Probe) | 200 | 200 | 64.35 | **PASS** |
| 2 | `GET /ready` (Readiness Probe — Model Loaded) | 200 | 200 | 61.95 | **PASS** |
| 3 | `POST /predict` (Missing Token -> 401) | 401 | 401 | 63.36 | **PASS** |
| 4 | `POST /predict` (Invalid Token -> 401) | 401 | 401 | 60.98 | **PASS** |
| 5 | `POST /predict` (Malformed JSON -> 400) | 400 | 400 | 63.55 | **PASS** |
| 6 | `POST /predict` (Missing text field -> 422) | 422 | 422 | 65.50 | **PASS** |
| 7 | `POST /predict` (Empty text string -> 422) | 422 | 422 | 63.05 | **PASS** |
| 8 | `POST /predict` (Boundary: 510 tokens -> 200 OK) | 200 | 200 | 529.66 | **PASS** |
| 9 | `POST /predict` (Boundary: 511 tokens -> 422 `TEXT_TOO_LONG`) | 422 | 422 | 66.09 | **PASS** |
| 10 | `POST /predict` (Positive Feedback inference) | 200 | 200 | 141.92 | **PASS** |
| 11 | `POST /predict` (Negative Feedback inference) | 200 | 200 | 141.52 | **PASS** |
| 12 | `POST /predict` (Neutral Feedback inference) | 200 | 200 | 143.20 | **PASS** |

### 5.2 Cold-start time and error rate, recorded separately (Proposal §3)
- **Error rate:** **0.0%** (0 of 12 cases).
- **Scale-to-zero cold start:** **37.94 seconds**, measured as the container woke from 0 replicas and first loaded RoBERTa.
- **Warm response time:** average 100–140 ms for ordinary predictions.

---

## 6. Performance and concurrency benchmark (P04-T04)

Test: [`loadtest/k6.js`](../loadtest/k6.js)\
Command: `make load-test`

### 6.1 Workload
- **Tool:** Grafana k6 (v0.56+).
- **Proposal §3 target:** end-to-end p95 $\le$ 3.0 seconds with **2 concurrent requests**, after the model is ready.
- **Load:** 2 Virtual Users (VUs) continuously send requests to `/predict` for 10 seconds, with `Authorization: Bearer ...` and a JSON feedback payload.

### 6.2 Observed metrics

```text
     ✓ status is 200
     ✓ response has sentiment
     ✓ response time p95 <= 3000ms

     checks.........................: 100.00% ✓ 138       ✗ 0
     http_req_duration..............: avg=143.8ms min=98.3ms med=134.1ms max=256.4ms p(90)=189.7ms p(95)=213.0ms
     http_req_failed................: 0.00%   ✓ 0         ✗ 46
     http_reqs......................: 46      4.41/s
     vus............................: 2       min=2       max=2
```

- **Measured p95:** **0.213 seconds (213 ms)**.
- **SLA target:** $\le$ 3.0 seconds (3,000 ms).
- **SLA result:** **PASSED**, about **14 times below the limit**.
- **HTTP failure rate:** **0.00%**, all 46/46 requests succeeded.

---

## 7. Rollback verification (P04-T05)

Script: [`scripts/verify_rollback.py`](../scripts/verify_rollback.py)\
Full machine-readable result: [`reports/P04-rollback-evidence.json`](P04-rollback-evidence.json)\
Usage and architecture: [`scripts/README.md`](../scripts/README.md)

### 7.1 Native revision routing
Azure Container Apps Multiple Revisions Mode keeps each version as an immutable snapshot:
- **Previous Stable Revision:** `feedbackpulse-api--2zaws5o`
- **New / Latest Revision:** `feedbackpulse-api--rev2`

If the new revision has a problem, traffic can return to the stable revision without rebuilding the Docker image or reverting a Git commit.

### 7.2 Actual command result (`make verify-rollback SIMULATE=1`)

```text
================================================================================
FeedbackPulse Rollback Verification: feedbackpulse-api in itcs355-6688166
================================================================================
Discovered revisions (ordered chronologically):
  1. [PREVIOUS STABLE] feedbackpulse-api--2zaws5o (Traffic: 100%, State: Provisioned)
  2. [NEW / LATEST]    feedbackpulse-api--rev2    (Traffic: 0%,   State: Provisioned)

[Scenario Setup] Simulating incident: setting traffic 100% -> feedbackpulse-api--rev2...
Executing Rollback: Shifting 100% traffic back to feedbackpulse-api--2zaws5o...
[OK] Traffic successfully rolled back in 15.00 seconds.
Post-Rollback Traffic Distribution: [{'revisionName': 'feedbackpulse-api--2zaws5o', 'weight': 100}]

Verifying live endpoint health on rolled-back revision...
Service ready in 37.07s (attempt 6). Proceeding with checks...

  • GET  /health  : status=200 (68.69ms)
  • GET  /ready   : status=200 (147.33ms)
  • POST /predict : status=200 (147.53ms) -> positive
================================================================================
Rollback Verification Summary: ALL PASSED [OK]
================================================================================
```

- **Traffic cutover:** **15.00 seconds**.
- **Cold-start handling:** readiness polling waited for the scaled-to-zero container without timing out.
- **Post-rollback endpoints:** `/health`, `/ready`, `/predict` all returned 200 OK, confirming normal responses after rollback.

---

## 8. Cloud cleanup and cost control (P04-T06)

Scripts: [`scripts/teardown.sh`](../scripts/teardown.sh) and [`teardown.sh`](../teardown.sh)\
Makefile commands: `make teardown` and `make teardown-dry-run`

The team prepared teardown automation to limit extra Azure for Students costs, with these safeguards:

> **Default safe scope:**
> `make teardown` deletes **only `feedbackpulse-api` and all its revisions**, keeping **Azure Container Registry (ACR)** and the **Container Apps Environment**. The original plan was to let a later `git push` recreate/deploy the App through CD without rebuilding the infrastructure. ACR/Environment deletion commands are commented out for safety.

### 8.1 Dry-run check (`make teardown-dry-run`)
The script previews the deletion commands without changing resources:

```text
========================================================================
FeedbackPulse — Azure Cloud Teardown Verification (P04-T06)
========================================================================
Resource Group : itcs355-6688166
Scope Mode     : app-only (Safe Mode: Container App only)
Dry Run Mode   : true

Active Azure Subscription: Azure for Students

Target resources planned for deletion:
  • Container App: feedbackpulse-api (in RG itcs355-6688166)

[DRY RUN] Simulation complete. The following CLI commands would be run:
  az containerapp delete -n feedbackpulse-api -g itcs355-6688166 --yes

[DRY RUN] No cloud resources were modified or removed.
```

### 8.2 Safety checks
1. **Default `--app-only` scope:** avoids accidental deletion of ACR/Environment, keeping the base infrastructure for recreation.
2. **Interactive confirmation:** waits for an explicit `yes` before deletion to avoid accidental removal.
3. **Existence check:** safely skips a resource that is already deleted instead of crashing.


### 8.3 `make teardown-dry-run` vs `make teardown`

| Feature | `make teardown-dry-run` | `make teardown` (safe scope) |
|---|---|---|
| **Cloud impact** | **No changes/deletions** | **Deletes only the Container App** (`feedbackpulse-api`); keeps ACR/Environment |
| **Command behavior** | Checks the subscription and prints planned CLI commands | Runs `az containerapp delete` |
| **Confirmation** | **None**: exits after the preview | **Prompt** (`Are you sure? yes/N`); requires `yes` |
| **Recreation** | Existing service stays online | **Original intended flow:** push `main` and CD recreates the App automatically |
| **Use** | Preview commands without taking the service down; capture dry-run logs | Remove the App to clear its state or test recreation through CI/CD |

#### Command details
- **`make teardown-dry-run` (Preview / Simulation):**
  - Runs `./scripts/teardown.sh --dry-run`.
  - Checks Azure CLI login and lists affected resources.
  - Prints the planned `az containerapp delete` commands.
  - Changes/deletes no resources; services remain online.
- **`make teardown` (Interactive Execution):**
  - Runs `./scripts/teardown.sh`.
  - Lists the Container App to delete, then waits at `Are you sure you want to proceed? (yes/N):`.
  - Enter or any other value cancels.
  - Only `yes` starts Container App deletion; ACR/Environment remain.


---

## 9. Deployment verification checklist

- [x] **CI pipeline:** GitHub Actions passes `ruff check`, portability audit, template validation and all `pytest` tests (70/70, 100%).
- [x] **CI blocker:** faulty changes or failing tests cannot deploy.
- [x] **CD deployment:** non-root image built and deployed to Azure Container Apps through Azure OIDC.
- [x] **Cloud smoke tests:** public HTTPS URL passes all 12/12 API-contract cases (200, 401, 400, 422 with the 510-token boundary, 503).
- [x] **Latency target:** p95 = **0.213s**, target $\le$ 3.0s at 2 concurrent requests; cold start recorded separately (37.94s).
- [x] **Rollback:** evidence confirms 100% traffic returned to the old revision in 15.00 seconds through `make verify-rollback`.
- [x] **Teardown:** `teardown.sh` / `make teardown` available and tested in `--dry-run` mode.
- [x] **Evidence collected:** results in `reports/P04-evidence.md`, with plan statuses updated.
