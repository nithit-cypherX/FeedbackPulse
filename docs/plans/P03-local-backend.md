# P03 — Run the backend locally

- **Original handoff status:** `done` (2026-10-08) · The new technical review passed on 2026-10-10; waiting for the user's review before accepting P03 and returning to P04. See the notes below.
- **Owner:** Person 2 — Backend and deployment
- **Main plan:** [Overview](../../overview-plan.md) · **Scope:** [Proposal](../../PROPOSAL.md) · **Agreed requirements:** [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md) · [P02 Model pipeline](P02-model-pipeline.md)
- **Phase evidence:** [reports/P03-evidence.md](../../reports/P03-evidence.md)

## Token-only review fix — 2026-10-10

- The user approved only **T01: require `SERVICE_TOKEN`**. Removed the fallback token from `config.py`. A missing, empty or whitespace-only value now stops startup before model lookup, with an error that does not show the token. Bearer-token validation and endpoints are unchanged.
- Updated `.env.example` to mark the value as required. Tests set their own dummy token in `tests/conftest.py`; this is not a default for the real app. Added tests for missing/empty values and assertions that unauthorized requests do not call the model.
- Before the config fix, **5 new cases failed**. After the fix, **41 tests passed** (`test_config.py`, `test_evaluation.py`, `test_gitinfo.py`, `test_registry.py`), plus **3 existing portability tests**. Another **7 startup/auth checks passed** without opening a port: startup rejects missing/empty/whitespace values; requests reject missing/wrong tokens and the old fallback when a different token is configured, without calling the model; the configured token is accepted. Lint passed for the changed Python files.
- This check used Python **3.11.16**, FastAPI **0.141.1** and a mock model for auth, not the locked Python 3.13 environment. The full `tests/test_api.py` suite, real model and Docker were not tested because the dependencies/model were not ready. Nothing was installed.
- **Not changed in this token fix:** model-version binding, model lookup before startup, private data in error logs, or the other fallback token in `.github/workflows/cd.yml`, which belongs to P04. No CI/CD, Azure, real secrets, commits or pushes were changed in that round.

## Model-version-only review fix — 2026-10-10

- The user approved only the link between the version name and real model files in **T02/T05/T06**. Before loading the model, the API reads the configured version's registry entry, checks the version against its lineage and compares the real file hashes with the record. It reuses P02's file checker without creating a new version or evaluation result.
- The check runs once at startup. A missing registry entry, version mismatch, missing/changed file or extra unregistered file in the model directory prevents the model loader from running. `/health` still returns 200; `/ready` and authenticated `/predict` return 503. If the check passes, the verified version goes to the loader and the API response.
- Uses the file hashes in the existing registry. A newly generated `manifest.json` does not need the same hash as the first one, because packaging timestamps can change without changing the model files. This verifies the artifact, not that the running environment/code is identical to the evaluation run.
- Added only `reports/registry/sentiment-*.json` to the Docker image through `Dockerfile` and `.dockerignore`. Evaluation results and other reports are not copied. File-selection paths were checked, but **the image was not built yet**.
- Added [tests/test_model_binding.py](../../tests/test_model_binding.py) with small files and a mock loader. Before the fix, **10 startup regression cases failed** because the old code still called the loader when binding was invalid. After the fix, **67 tests passed**: 23 new and 44 existing (`test_registry.py`, `test_config.py`, `test_evaluation.py`, `test_gitinfo.py`, `test_portability.py`). These call real ASGI routes in-process and confirm that binding is checked only once. Lint and `git diff --check` passed.
- Used Python **3.11.16** / FastAPI **0.141.1** from the existing environment, with downloads disabled and no new installs. The full `tests/test_api.py` suite, real model and Docker under the Python 3.13 lockfile were still untested because dependencies/model and Docker in WSL were not ready. This was not full P03 acceptance.
- Did not change the existing registry, evaluation scores, model, pre-startup model lookup or error logs. No CI/CD/Azure changes or commit/push. P04 OIDC/CD remained paused under the overview's conditions.

---

## Config/startup fix for a missing model — 2026-10-10

- The user approved review finding 3 in **T01/T02**: removed automatic downloads from `get_default_model_dir()` in `config.py`. If `MODEL_DIR` is set, use that path; otherwise use the existing packaged-artifact path without checking/downloading in config. Updated the explanation in `.env.example`.
- Reused the existing registry/file checks and startup error handling without changing `api.py`. With a missing model, the app can still be created and enter its lifespan: `/health` returns 200, `/ready` and authenticated `/predict` return 503, and a request without a token still gets 401. An invalid or missing `SERVICE_TOKEN` still stops the app; this requirement was not relaxed.
- Added **5 cases** in `test_config.py` and `test_model_binding.py`: the default path with/without a directory, the API with a missing model with/without `MODEL_DIR`, and importing the default app in a new process from an empty directory. All cases forbid downloader calls. Before the fix: **3 failed / 2 passed**. After the fix, including existing tests: **72 passed**. Lint, format and `git diff --check` passed.
- Checked with Python **3.11.16** / FastAPI **0.141.1** in the existing environment, with downloads disabled and no new installs. Used small files/mock models and in-process ASGI routes. The full `tests/test_api.py` suite, real model and Docker under the locked Python 3.13 environment still needed checking before full P03 acceptance.
- Files outside scope matched the baseline: P02 download/evaluate/package code, registry/model-version guard, model/evaluation records, Docker and CI/CD. Error logs were not changed. No Azure actions or commit/push. P04 OIDC/CD remained paused under the overview.

---

## Error-log-only review fix — 2026-10-10

- The user approved review finding 4 in **T03/T05**, following the privacy contract. `api.py` now logs the failure location and exception type, such as `Inference failed (RuntimeError)`, instead of raw exception messages/tracebacks during prediction, request-error handling and model loading. The 500/503 responses and auth rules are unchanged.
- Inspection of the installed Starlette/Uvicorn code showed that a generic error handler can send a response and still re-raise the exception for the server to log. The existing middleware now catches request errors before that point, uses the existing handler and 500 message, and keeps request status/duration logging. No global log filter was added, and logging was not disabled system-wide. This covers the current JSON-request path, not every external service's logs.
- Added **4 cases** in [tests/test_api_logging.py](../../tests/test_api_logging.py): inference error, a chained exception with a note, response-building error and model-load error. Dummy feedback/tokens are checked against responses and formatted logs, including tracebacks. The tested request errors must not escape the ASGI app and be logged again by the server. Reused the helper in `test_model_binding.py`, adding support for a dummy body.
- Before the fix: **4 new tests failed**. After the fix, including regressions: **76 passed**. Lint/format and `git diff --check` passed. This still used Python **3.11.16** / FastAPI **0.141.1** with mock models, not the full `tests/test_api.py` suite, real model or Docker under Python 3.13/lockfile. Those checks were still needed before full P03 acceptance.
- Detailed error messages and tracebacks at these points are no longer logged, so there is less debugging detail. The failure location, error type and request status/duration remain available. Files outside scope matched the baseline. No model/scores, config/token, registry guard, Docker, Azure/CI/CD or commit/push changes. P04 OIDC/CD remained paused under the overview.

---

## Prepare Python and the locked environment — 2026-10-10

- The user approved only environment setup: installed Python **3.13.11** through `uv` without changing Ubuntu's system Python, then created `/home/nirvana/feedbackpulse/.venv` with `uv sync --frozen --python 3.13.11 --managed-python --no-python-downloads`. Used the project's existing default `dev` and `data` groups: **52 packages** in total.
- `uv sync --frozen --check --offline` required no package changes, and `uv pip check --python .venv/bin/python --offline` passed. FastAPI, HTTPX, PyTorch and Transformers imported offline without calling the model loader. Main versions: FastAPI **0.142.4**, Starlette **1.7.0**, PyTorch **2.14.1+cpu** and Transformers **5.19.0**.
- `.python-version`, `pyproject.toml` and `uv.lock` were unchanged. `.venv/` is Git-ignored, and system Python remained **3.10.12**. All earlier code changes were kept.
- There was still no `artifacts/` directory or cache for the project's model. No model/data download, tests, API run, Docker build or Azure/CI/CD actions in this step. It confirmed environment setup, not P03 acceptance. Tests in this environment, the real model and the container still needed checking; P04 OIDC/CD remained paused under the overview.

---

## Run model-free tests in the locked environment — 2026-10-10

- The user approved only this step: ran `.venv/bin/python -B -m pytest -v -p no:cacheprovider` with Python **3.13.11**, pytest **9.1.1**, FastAPI **0.142.4** and Starlette **1.7.0** from `uv.lock`. The working tree included earlier fixes on base commit `21d189d` (fixes not yet committed). Result: **77 passed in 9.03s**.
- Ran `test_api_logging.py`, `test_config.py`, `test_model_binding.py`, `test_registry.py`, `test_evaluation.py`, `test_gitinfo.py`, `test_portability.py` and only `test_inference.py::test_load_failure_is_distinguishable`, all under `tests/`. These use dummy data/models or missing-model cases, not real weights. Disabled plugin autoload, bytecode and downloads with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `UV_OFFLINE=1`; tests used a dummy token.
- After the run, `uv sync --frozen --check --offline` confirmed that the 52 packages needed no changes. There was still no `artifacts/` directory or project-model cache. Code, tests, dependencies and previous evaluation results were unchanged. `git diff --check` passed.
- This completed only model-free verification in the locked environment. `tests/test_api.py`, real-model inference tests and Docker build/smoke tests were still pending. `test_cloudlayer.py` belongs to P04 and was excluded. No Azure/CI/CD actions, full P03 acceptance or return to OIDC/CD yet.

---

## Check the real model and local API — 2026-10-10

- After the model-free tests passed, the user approved the next step. Downloaded the same revision, `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`, and checked that **6/6 source-file SHA-256 hashes matched the registry**. Then ran the existing `package_artifact.build()` offline to create `artifacts/sentiment-6e7ff9fbc17c/`. **6/6 artifact files matched the registry**, and `verify_model()` passed for `sentiment-6e7ff9fbc17c-0110c462`. No new registry entry or evaluation result was created.
- **Obstacle:** Xet in WSL reported `connection struggling`; HTTP in WSL was also slow. Stopped both processes and downloaded the same file through Windows HTTP into Ubuntu's cache (501,045,531 bytes; SHA-256 matched the registry). One agent check imported a helper from the wrong location and stopped before downloading; only that command was fixed, not the dependencies. Removed about 104 MiB of incomplete downloads from the two stopped attempts after verifying the complete file. This did not establish that the user's internet was the cause.
- **106 passed, 10 warnings in 9.30s** in the locked Python **3.13.11** `.venv`: **18** cases in `tests/test_api.py`, **12** in `tests/test_inference.py` and **76** existing regressions, using `pytest -v -p no:cacheprovider`. Plugin autoload/bytecode were disabled, with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `UV_OFFLINE=1`. API tests used the packaged model; inference tests used the verified upstream snapshot in cache. This included accepting 510 tokens and rejecting 511.
- Also checked startup with a lifespan-aware `TestClient`, **without injecting a classifier**. The API checked the registry and loaded the real artifact itself: `/health` and `/ready` returned **200**, and `/predict` returned **200** with the same version. Sample text `The staff were helpful.` returned `positive`, score `0.9414`. Missing/wrong tokens returned **401** with a Bearer challenge. Changing only the settings to a missing-model path still allowed startup: `/health` **200**, `/ready` and authenticated `/predict` **503**. All checks were in-process/offline, without opening a server port.
- Pytest warnings: Starlette's HTTPX-based TestClient warning **1** time, HTTP 422 constant-name warnings **8** times, and PyTorch's tensor-with-`requires_grad=True` to scalar warning **1** time. Tests passed; no code/dependency changes were made for these warnings. Packaging also reported pooler weights unused by the classification model, as already noted in P02. Every artifact file hash matched.
- Code, tests, lockfile, registry and previous scores matched the baseline. `.venv` still matched the same 52 packages, and the artifact was Git-ignored. Only this plan was updated. **Docker for the latest code** and `test_cloudlayer.py` were not tested yet. No Azure/CI/CD actions or commit/push. P03 was not fully accepted yet; the next step was to propose a local container check before returning to P04.

---

## Check Docker for the latest code locally — 2026-10-10

- The user approved a container build/test to close the P03 gap, without push/deploy. `docker build --platform linux/amd64 --progress plain --tag feedbackpulse:p03-review-20261010 .` succeeded on the first attempt from the working tree with earlier fixes on base commit `21d189d` (not yet committed). Local image ID: `sha256:e4159c364b3ab9c8b8afb1a9341f0c8bf79eeae947e14099c5c555d851084709`. This is not a registry digest.
- Used the existing Dockerfile and base-image digest. Python **3.13.16** satisfies `3.13.*`; **42 production packages** were installed with `uv sync --frozen --no-default-groups --no-install-project`. This differs from the local 3.13.11 `.venv`, which also includes dev/data groups. Dependencies and lockfile were unchanged.
- Ran this image ID with **1 CPU / 2 GiB, `--network none`, no host port or mount**, and a dummy runtime token. Confirmed non-root UID **10001**, source-Python SHA-256 hashes matching the working tree, and successful `verify_model()` artifact/registry checks for `sentiment-6e7ff9fbc17c-0110c462`. No model download was needed at API startup.
- Sent real HTTP requests to Uvicorn over container loopback: **16 checks passed**. These covered health/ready, prediction with the correct 3 fields/version, missing/wrong token → **401** with a Bearer challenge, malformed JSON → **400**, missing/null/number/list/empty/whitespace text and invalid body types → **422**, and text counted by the packaged tokenizer: **510 tokens → 200 / 511 tokens → 422**. `The staff were helpful.` returned `positive`, score **0.9414**.
- Tested the same image with `MODEL_DIR` overridden to a missing path: **4 checks passed** (`/health` 200, `/ready` 503, authenticated `/predict` 503 and no token 401). Another container without `SERVICE_TOKEN` exited with code **1** and the expected config error. The image's Docker HEALTHCHECK also reported **healthy** (exit 0).
- Measured RAM through cgroup during the same HTTP run: **1,274.4 MiB** before requests, peak **1,364.8 MiB**, including file cache and helper processes. The API process alone had **383.5 MiB** RSS before requests and **753.0 MiB** high-water RSS. There was no OOM kill. Two short predictions took **888.83 / 394.55 ms**; the 510-token input took **6,389.59 ms**. These are one-off local smoke-test measurements, not p95/load testing or confirmed Azure sizing/SLO.
- The tested request logs contained neither the dummy token nor full feedback. Image config had no `SERVICE_TOKEN`, and `/app/.env`, `/app/cloud.env`, `/app/.git` were absent. This was not a scan of every layer or logging system. Simulated error/500 coverage still comes from the earlier regression tests; the container was not modified to create extra errors.
- Code, tests, Dockerfile, dependencies, registry and previous evaluation results matched the baseline. Removed only the **4 test containers** created for this check after recording results; kept the image and artifact. Updated only the existing plan and overview. Together with the **106 tests passed in the previous step**, P03's technical checks were complete, awaiting user review before acceptance. **P04 OIDC/CD remained paused**. No Azure/GitHub actions or commit/push.

---

## 1. Scope and goal

**Expected result:**
A backend API and Docker container that run locally, with automated tests covering every item in [P01-T02 §6](P01-T02-api-contract.md#6-implementation-checklist). This is the base for deployment to Azure Container Apps in P04 (course criterion **R2**).

**Original P03 deliverables:**
1. Configuration and service API code separated into core / configuration / cloud adapter responsibilities ([P01-T03 §4](P01-T03-system-structure.md#4-one-container-separate-code-responsibilities)), in `src/feedbackpulse/config.py` and `src/feedbackpulse/api.py`.
2. All 3 endpoints: `POST /predict`, `GET /health`, `GET /ready`, following [P01-T02](P01-T02-api-contract.md).
3. Validation, Bearer-token access control and error formats following the RFC requirements and API contract.
4. Connection to the shared inference module (`SentimentClassifier` from P02), loading the model once at process startup.
5. All 55/55 automated unit/integration tests passed (100%).
6. A `Dockerfile` that packages the model artifact into the image at build time ([P02-T10 decision](P02-model-pipeline.md#3-decisions-p03p04-must-follow)) and runs as non-root `appuser`.
7. Real container API checks and initial local RAM/latency measurements in [reports/P03-evidence.md](../../reports/P03-evidence.md).

**Outside P03:**
- Azure resource creation and cloud deployment (P04).
- GitHub Actions CI/CD workflow (P04).
- Dashboard and alerting (P05).
- Cloud failure experiment (P05).

---

## 2. Tasks and responsibilities

| Task ID | Work | Status | Done when | Check |
|---|---|---|---|---|
| **P03-T01** | **Dependencies and configuration layer** | `done` | Add the web framework (`fastapi`, `uvicorn`) to `pyproject.toml`; create `config.py` to read token, path and port from the environment, plus `.env.example` / `cloud.env.example` | `uv sync` succeeds and all unit tests in `tests/test_config.py` pass (100%) |
| **P03-T02** | **Lifespan and model state management** | `done` | Load `SentimentClassifier` once at startup. A model-load failure does not crash the app: `/health` still works, but model state is not ready | Simulate successful/failed model loading and check app state in `tests/test_api.py` |
| **P03-T03** | **Auth, endpoints and error handling** | `done` | Implement `/health`, `/ready`, `/predict`, Bearer-token checks and RFC 9110 error payloads (`UNAUTHORIZED`, `INVALID_TEXT`, `BAD_REQUEST`, `MODEL_NOT_READY`, `INTERNAL_ERROR`) | Check response status, error code and `WWW-Authenticate: Bearer` when the token is missing |
| **P03-T04** | **Input token boundary validation** | `done` | Reject empty `text` and check the 510-content-token limit with the tokenizer locked in P02-T03. Do not use `truncation=True`; reject overlong input with 422 | Empty text -> 422, 510 tokens -> 200, 511 tokens -> 422 (`TEXT_TOO_LONG`) |
| **P03-T05** | **Checklist verification tests** | `done` | Add automated tests in `tests/test_api.py` for all 11 checklist items in [P01-T02 §6](P01-T02-api-contract.md#6-implementation-checklist) | `uv run pytest tests/test_api.py`: 18/18 pass (55/55 across the whole suite) |
| **P03-T06** | **Create the Dockerfile and build the image** | `done` | Use `python:3.13-slim`, install dependencies with `uv sync --no-default-groups`, copy the artifact into the image and set non-root `appuser` | `docker build -t feedbackpulse:local .` succeeds. Image ID: `16030a4a4dbf` |
| **P03-T07** | **Container smoke test and memory measurement** | `done` | Run the container locally. Test valid input, bad input, wrong token and model failure; measure peak/idle RAM | Real `curl` endpoint checks pass; memory usage recorded (645.8 MiB) |
| **P03-T08** | **Evidence and handoff** | `done` | Record results/measurements in `reports/P03-evidence.md` and update `overview-plan.md` | Documents complete, links correct and ready for P04 |

---

## 3. Locked rules and decisions

1. **Do not count characters instead of tokens:** the limit is 510 content tokens (512 with special tokens), counted only by the tokenizer from the running revision.
2. **No silent truncation (`truncation=False`):** text over 510 tokens returns `422` with `TEXT_TOO_LONG`.
3. **Artifact storage:** put the model artifact in the Docker image at build time, as agreed in P02-T10.
4. **Secrets and log privacy:** do not log `service-token` values or full feedback text.
5. **Separate `/health` and `/ready`:** if the app runs but the model cannot load, `/health` returns `200`; `/ready` and `/predict` return `503`, never a fake prediction.
6. **`model_version`:** read the real registry/config value (`sentiment-6e7ff9fbc17c-0110c462`).

---

## 4. P03 phase acceptance

- [x] `uv run pytest` passes all tests (existing and new API tests: 55/55).
- [x] The container image builds and runs without errors (`feedbackpulse:local`).
- [x] Container smoke tests cover 200 (valid), 400 (bad JSON), 401 (no/bad token), 422 (invalid/too-long text) and 503 (model not ready).
- [x] Idle/peak container RAM is recorded for P04 sizing (645.8 MiB in the container).
