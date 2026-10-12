# P03 — Local backend development and test evidence

**Historical test report:** Results below belong to the 2026-10-08 test run. Later review fixes and container checks are in the [P03 plan](../docs/plans/P03-local-backend.md). The handoff to P04 is history, not a new deployment task.

- **Test date:** 2026-10-08
- **Status:** `done`
- **Course criteria:** **R2 (Deployment & Container readiness)**, **R4 (Readiness/Liveness probe separation)**
- **Built image:** `feedbackpulse:local` (image id: `d7a3500d767a`)
  - **Base image builder:** `python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c` (pinned strictly by digest, no tag)
  - **Uv binary builder:** `ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21` (pinned strictly by digest, no tag)
  - **Base image runtime:** `python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c` (pinned strictly by digest, no tag)
  - **Security check:** Non-root user `appuser` (UID 10001), Zero credentials baked into image layers (credentials arrive via runtime environment variables only).
- **Verified model version:** `sentiment-6e7ff9fbc17c-0110c462`

---

## 1. Automated test results (checklist verification)

Command: `uv run pytest`, using Python 3.13.0.
- **Overall result:** **55 passed** in ~7.68 seconds.
- **API tests (`tests/test_api.py`):** 18 tests cover all 11 checklist items in `P01-T02 §6`:

| Item | Checklist requirement | Observed behavior | Result |
|---|---|---|---|
| 1–3 | Valid request/token returns 200 with `sentiment`, `score`, `model_version` | HTTP 200; sentiment is one of 3 classes, score in [0, 1], model_version matches registry | **PASS** |
| 4 | Malformed JSON returns 400 | Invalid JSON string returns HTTP 400, code `BAD_REQUEST` | **PASS** |
| 5 | Missing/null/numeric/list/empty/whitespace-only text returns 422 | All listed inputs return HTTP 422, code `INVALID_TEXT` | **PASS** |
| 6 | Accept 510 tokens (200), reject 511 (422 `TEXT_TOO_LONG`), no silent truncation | 510 tokens -> 200; 511 -> 422 `TEXT_TOO_LONG` | **PASS** |
| 7 | Missing/wrong token returns 401 with `WWW-Authenticate: Bearer`, without calling the model | Missing/wrong token returns HTTP 401 with the required header | **PASS** |
| 8–9 | Model ready: `/ready` 200; not ready: `/health` 200, `/ready` and `/predict` 503 | Model-load failure gives `/health` -> 200, `/ready` -> 503, `/predict` -> 503 `MODEL_NOT_READY`, no fake prediction | **PASS** |
| 10 | Unexpected errors return 500 without stack traces/internal secrets | Simulated exception returns HTTP 500, code `INTERNAL_ERROR`, with no secret in the body | **PASS** |
| 11 | Errors follow the schema; logs exclude tokens/full feedback | JSON matches the contract; caplog contains no token/private message | **PASS** |

- **Lint:** `uv run ruff check` passed 100%, with no errors.

---

## 2. Tests in a real Docker container (`feedbackpulse:local`)

Built with `docker build -t feedbackpulse:local .` (multi-stage build, non-root `appuser`, baked-in model artifacts).

### 2.1 Container endpoint smoke tests

```bash
docker run -d --name feedbackpulse-test -p 8000:8000 -e SERVICE_TOKEN="test-token-123" feedbackpulse:local
```

#### 1) Liveness Probe (`GET /health`):
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"healthy"}
```

#### 2) Readiness Probe (`GET /ready`):
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"ready","model_version":"sentiment-6e7ff9fbc17c-0110c462"}
```

#### 3) Prediction Tests (`POST /predict`):
- **Positive input:** `"Flight attendant was super polite and helpful. Amazing trip!"`
  ```json
  {"sentiment":"positive","score":0.9855,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```
- **Negative input:** `"Worst experience ever. Lost luggage and flight delayed 10 hours."`
  ```json
  {"sentiment":"negative","score":0.9536,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```
- **Neutral input:** `"Flight UA123 departed on schedule."`
  ```json
  {"sentiment":"neutral","score":0.8869,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```

#### 4) Error Handling Verification:
- **Unauthorized (Wrong Token):**
  ```http
  HTTP/1.1 401 Unauthorized
  www-authenticate: Bearer

  {"error":{"code":"UNAUTHORIZED","message":"Missing or invalid service token."}}
  ```
- **Malformed JSON:**
  ```http
  HTTP/1.1 400 Bad Request

  {"error":{"code":"BAD_REQUEST","message":"Request body must be valid JSON."}}
  ```
- **Empty text:**
  ```http
  HTTP/1.1 422 Unprocessable Content

  {"error":{"code":"INVALID_TEXT","message":"text must be a non-empty string."}}
  ```
- **Over 510 tokens:**
  ```http
  HTTP/1.1 422 Unprocessable Content

  {"error":{"code":"TEXT_TOO_LONG","message":"text is 601 tokens, limit is 510"}}
  ```

---

## 3. Container memory measurements

Measured with `docker stats --no-stream feedbackpulse-test`:

| Metric | Measured in the Linux container | Note |
|---|---|---|
| **Memory Usage (Active)** | **645.8 MiB** | After model loading and serving requests |
| **CPU Usage** | **0.51%** | While idle |
| **PIDs** | **24** | Includes worker threads and PyTorch runtime |

> **Sizing input for P04 (Azure Container Apps):**
> Based on the 645.8 MiB measurement, the proposed 1 vCPU / 1.5–2.0 GiB RAM on Consumption was considered enough for 2 concurrent requests without OOM, while staying within Proposal §6's budget.

---

## 4. Simulated failure: model unavailable

Ran a container with a missing model path (`MODEL_DIR=/nonexistent_dir`):
```bash
docker run -d --name feedbackpulse-broken -p 8001:8000 -e MODEL_DIR="/nonexistent_dir" feedbackpulse:local
```

**Observed results:**
1. The container process kept running instead of immediately crash-looping.
2. `GET /health` returned **HTTP 200 OK** (`{"status":"healthy"}`).
3. `GET /ready` returned **HTTP 503 Service Unavailable**.
   ```json
   {"error":{"code":"MODEL_NOT_READY","message":"The model is not ready. Please try again later."}}
   ```
4. `POST /predict` returned **HTTP 503 Service Unavailable**, without making up a prediction.

This confirms readiness/liveness separation in the tested case. It was a base for the originally planned P05 failure drill, which the user later canceled. The presentation now uses this result and the separate P04 rollback evidence in the [failure story](../README.md#failure-story-model-unavailable-and-rollback); it does not claim one cloud failure-to-alert-to-recovery experiment.

---

## 5. Handoff to P04

- **Person 2 (Backend and Deployment):**
  - `feedbackpulse:local` is ready. Use the `Dockerfile` and workflow to set up GitHub Actions CI/CD in P04.
  - Manage `SERVICE_TOKEN`, `MODEL_DIR`, `MODEL_VERSION` through `cloud.env.example`.
