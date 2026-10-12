# FeedbackPulse — Overview Plan

**Recorded status — 12 October 2026:** the local demo and monitoring checks are complete.
The documentation and validation results are recorded under [P06](#p06--documentation-and-operations).
CD was paused with `FEEDBACKPULSE_CD_ENABLED=false`; the local demo was stopped.
Cloud results below are dated evidence, not live service-status checks.

The latest verified deployment was Malaysia West [CI #11](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139654748)
and [CD #9](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139856763).
The readiness wait took about 34 seconds; revision `feedbackpulse-api--0000002`
matched the image SHA, received 100% traffic and passed 6/6 post-deployment API checks.
[The P04 history](docs/plans/P04-deployment-and-cicd.md#deployment-history--wait-for-revision-readiness-before-passing-cd--2026-10-11)
records the earlier login, permissions and provisioning failures, fixes and test limits.

The original plan below defines six development phases. P05-T03's new incident
drill was later canceled; the existing missing-model and rollback experiments
remain separate. Cleanup is still required when the resources are no longer needed.

## Six-part overview

The phases cover model preparation, serving, releases, monitoring and operations:

| Phase | Work | Done when |
|---|---|---|
| **P01 — Agree on the system and responsibilities** | Define API input/output, separate core/configuration/cloud adapter, and assign owners | API behavior, component responsibilities and owners are documented |
| **P02 — Reproducible model pipeline** | Pin a pretrained model, version evaluation data, then evaluate → package → register with lineage | Workflow can be rerun; a registered model traces to code, data, model revision and evaluation |
| [**P03 — Run the backend locally**](docs/plans/P03-local-backend.md) | Accept English text; return sentiment, score and model version; add validation, access control, health/readiness and Docker | Real container API works, with tests for valid/bad input and model-not-ready cases |
| [**P04 — Deploy and release safely**](docs/plans/P04-deployment-and-cicd.md) | Test before Azure Container Apps deployment through CI/CD; measure latency, test rollback, manage credentials/tags/budget from the start | Tests block faulty changes, passing versions deploy, and rollback works |
| **P05 — Local demo and small monitoring setup** | One localhost page calls the real Azure API through a server-side-token relay; add only needed dashboard/alert work. Use the existing failure/rollback records instead of a new incident drill | Web UI calls the API and shows errors honestly. Verify dashboard/alert separately from UI; old images cannot prove untested behavior |
| **P06 — Documentation and operations** | Fill only gaps in demo instructions, README, model card, cost per 1,000 predictions, existing evidence, teardown and rehearsal | Others can follow the instructions; evidence limits are clear; unused resources are cleaned up with approval. No unrelated features |

**Test and collect evidence during each phase.** P06 brings together the usage guides and operational notes; each phase records its own checks.

## ML and development responsibilities

For three team members, the original proposal assigns:

- **Person 1 — Model and evaluation:** P02 and the model-to-API interface.
- **Person 2 — Backend and deployment:** P03–P04.
- **Person 3 — Monitoring and reliability:** P05, cost records and documentation.
- **Everyone:** P01 design agreement and P06 demo preparation.

Member names remain for the team to assign. Work does not need to be fully sequential: after input/output agreement, API work can start while the model is being prepared.

## What stays outside scope

Keep **one backend, one pretrained model and three sentiment classes**. No production frontend, CRM integration, chatbot or training/fine-tuning. The localhost demo added on 2026-10-11 is a client for the existing API, not a full web product.

Using a pretrained model **does not remove model-side MLOps work**. We still version, evaluate, track and register it for traceability. Reproducibility covers our integration workflow, not the upstream model's training.

## Original P01 plan and status

Start with just three tasks:

1. **P01-T01 — Confirm scope and proposal status**

   The pretrained-model scope was recorded on 2026-10-05. Role-specific owner names remain placeholders in the proposal.

2. **P01-T02 — Agree on the API format**

   See the [API contract](docs/plans/P01-T02-api-contract.md) for request/response, validation and errors. **`done` means agreement only, as of 2026-10-07**: P02-T03 confirmed 510 content tokens (512 with special tokens). Implementation/testing were not yet done; API boundary checks belong to P03.

3. **P01-T03 — Define system structure and checks**

   `done` for planning only. All three areas were agreed: system responsibilities, folders/Git rules, and system checks. See [System structure](docs/plans/P01-T03-system-structure.md) for the architecture-review base. Not implemented/tested at this stage.

**P01 status:** the design is recorded and P02-T03 resolved the text-length limit. Role-specific owner names remain `[Name]` in [Proposal §7](PROPOSAL.md).

## P02 complete

See [P02 phase plan](docs/plans/P02-model-pipeline.md) · Owner: Person 1.

- Active `model_version`: `sentiment-6e7ff9fbc17c-0110c462`, with lineage in `reports/registry/`; run ID `run-20261007T192531Z-d36357`.
- Evaluation on 14,640 rows: **accuracy 0.8100 · macro-F1 0.7606** ([evidence, section 2](reports/P02-evidence.md)).

**Integration references:**
- See the [locked interface, section 9](reports/P02-evidence.md) and [artifact-storage decision, section 7](reports/P02-evidence.md). Text limit: [P01-T02 §7](docs/plans/P01-T02-api-contract.md).
- The artifact is in the image, not a separate blob; [section 7](reports/P02-evidence.md) explains the rollback and testing trade-offs.

## P03 complete — local backend

**New review, 2026-10-10:** Token, model-binding, startup and error-log fixes passed **106 tests** in the locked environment. Latest container build/smoke checks also passed: local image ID `e4159c364b3ab`, non-root, **20 HTTP checks**, missing-token startup and Docker healthcheck. Included offline missing-model and 510–511-token boundaries. Details/RAM: [P03 plan](docs/plans/P03-local-backend.md#check-docker-for-the-latest-code-locally--2026-10-10). Numbers below are the original handoff, not the new image/test run.

See [P03 phase plan](docs/plans/P03-local-backend.md) · [test/measurement evidence](reports/P03-evidence.md) · Owner: Person 2.
- Status: `done`, all 8 tasks T01–T08.
- Automated tests: **55/55 passed, 100%**, in ~7.68 seconds.
- Container: `feedbackpulse:local` (recorded digest `16030a4a4dbf`), non-root with the model included.
- Smoke tests: real container API passed valid, 401, 400, 422 and 510-token-limit cases.
- Container memory: **645.8 MiB**, used for P04 sizing.
- Simulated failure: confirmed separation of `/health` (200) and `/ready` (503).

## P04 — original handoff and CD-verification limits

**Evidence scope:** latency/rollback results are from East Asia; the later CD fix was verified in Malaysia West. Benchmarks were not repeated in Malaysia West; CD is paused. See the [current P04 status](docs/plans/P04-deployment-and-cicd.md).

The items below preserve the original East Asia report. The later automated-deployment checks and earlier CD login failures are recorded in the P04 history.

See [P04 phase plan](docs/plans/P04-deployment-and-cicd.md) · [test/measurement evidence](reports/P04-evidence.md) · Owner: Person 2 (Backend and deployment).
- **Reported status:** `done`, all 6 tasks T01–T06.
- **Public Cloud URL:** `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`
- **Infrastructure:** Azure Container Apps (East Asia, Consumption Plan, 1.0 vCPU / 2.0 GiB, scale-to-zero).
- **CI/CD:** GitHub Actions two-stage CI (70/70 tests, Docker buildx) and CD (passwordless Azure OIDC, zero-downtime revision rollout).
- **Contract/benchmark:** 12/12 API-contract tests passed; k6 p95 = **0.213s** (target $\le$ 3.0s, error rate 0.0%).
- **Rollback:** Blue/green 100% traffic shift to baseline in **15.00s**, recorded in `reports/P04-rollback-evidence.json`.
- **Teardown/cost:** `scripts/teardown.sh` / `make teardown` with `--dry-run` for cleanup and cost control.
- **P04 tasks:**
  - P04-T01: **Infrastructure, cloud adapter and configuration** (`done`: `cloudlayer/` [`adapter.py`, `azure_adapter.py`], `cloudlayer/containerapp.template.yaml`, `Makefile`, `make portability-audit` 100% passed, tests 70/70).
  - P04-T02: **GitHub Actions CI** (`done`: two-stage `.github/workflows/ci.yml`; `test` [Astral `uv`, `ruff check`, portability audit, template validation, 70/70 tests] and `build` [Docker buildx `--platform linux/amd64`, SHA tagging, container `/ready` & `/predict` smoke tests]).
  - P04-T03: **Automated CD/deployment** (`done`: `.github/workflows/cd.yml` on main, Azure OIDC `id-token: write` without long-lived keys, build/push SHA-tagged image, render template, deploy Azure Container Apps, smoke-test live endpoint).
  - P04-T04: **Cloud smoke test/latency benchmark** (`done`: `scripts/cloud_check.py` passed 12/12; `loadtest/k6.js` measured p95 0.213s at 2 concurrent requests [target <= 3.0s, error rate 0.0%]).
  - P04-T05: **Rollback verification** (`done`: `scripts/verify_rollback.py` / `make verify-rollback` returned 100% traffic to `feedbackpulse-api--2zaws5o` in 15.00s without rebuilding; `/health`, `/ready`, `/predict` returned 200 OK; recorded `reports/P04-rollback-evidence.json`).
  - P04-T06: **Teardown/evidence** (`done`: `scripts/teardown.sh` / `make teardown` with `--dry-run`, results collected in `reports/P04-evidence.md`).

## P05 — local demo and small monitoring setup (2026-10-11)

- **P05-T01 — demo calling the real API:** `done`: (1) relay/tests, (2) HTML/CSS/JavaScript page, (3) browser-to-Azure check/screenshots below.
- **P05-T02 — small monitoring setup:** `done`: dashboard/demo link and live traffic alert. `/ready` 25/25 returned 200, metric counted 25, alert Fired and the owner confirmed email receipt. See [part 3 record](demo/README.md#traffic-alert--p05-t02-part-3). No API/CD changes or model-failure proof.
- **P05-T03 — new failure/recovery experiment:** canceled to avoid waiting for a new recovery drill during the demo. Use the existing [failure story](README.md#failure-story-model-unavailable-and-rollback) and linked team evidence. P03's local missing-model test and P04's East Asia rollback were separate experiments, not one failure-to-alert-to-recovery run.
- **Non-goals:** no login/database, permanent feedback storage, frontend deployment, local model loading or existing API/CD changes.

### P05-T01 part 1 — localhost relay: `done`

- Added [demo/server.py](demo/server.py), [relay instructions](demo/README.md) and [tests/test_demo.py](tests/test_demo.py), using Python 3.13.11 and existing `.venv` dependencies. No `pyproject.toml`/`uv.lock` changes.
- Accepts only `POST /api/predict` and `GET /api/ready`. HTTPS target/token come from environment. Callers supply only text, not URLs/headers. No redirect following, retries or token exposure to the browser. Restricts localhost Host/Origin and binds `127.0.0.1:8080`.
- Total deadline 60 seconds, connect timeout 10 seconds. Returns short errors, not raw upstream errors; no feedback/token logging. The existing API still enforces 510 tokens.
- **Checks:** `.venv/bin/python -m pytest -q tests/test_demo.py tests/test_cd_deployment.py tests/test_oidc_workflow.py` passed **162 tests** (87 demo + 75 existing CI/CD) in 7.13s. Ruff passed for the two new Python files. One existing Starlette TestClient/httpx warning; no replacement packages installed.
- **Issue fixed:** An incomplete Unicode surrogate in JSON caused pre-send encoding to fail. Now returns `422`, covered by a passing regression test. Malformed Unicode upstream responses return `502`.
- **Real process check:** Started the WSL entry point with dummy config/token. Four localhost HTTP cases passed: no web page 404, invalid input 422, other origin 403, target query 400. All stopped before upstream; no Azure requests. Stopped the created process and confirmed port 8080 closed.
- **Limits:** mock-transport and local-process checks only. The web page and live Azure check were added in parts 2 and 3.

### P05-T01 part 2 — localhost demo page: `done`

- Added [HTML](demo/static/index.html), [CSS](demo/static/styles.css) and [JavaScript](demo/static/app.js), following the agreed layout: text/examples on the left, sentiment/model score/response time/model version on the right, Check API below. Narrow screens use one column.
- Examples only fill text; Analyse sends through the relay. No token/target URL in the browser, history or polling. Editing/Clear removes old results; canceled-request results cannot overwrite new text. Explains score vs accuracy and request round-trip time vs p95 separately.
- `demo/server.py` serves only `/` and `demo/static/`, with same-origin script/style/connect CSP, not other repo files. Updated [demo instructions](demo/README.md) to match behavior. No new dependencies or API/CD/Makefile changes.
- **Automated checks:** `.venv/bin/python -m pytest -q tests/test_demo.py tests/test_cd_deployment.py tests/test_oidc_workflow.py` passed **171 tests** (96 demo + 75 existing CI/CD) in 8.42s. Ruff check/format passed; one existing Starlette TestClient/httpx deprecation warning. No installs.
- **Browser checks:** Real WSL FastAPI relay with `httpx.MockTransport`/dummy token, no Azure/network upstream. Checked initial empty/Not checked, no automatic submission from examples, positive/negative/neutral, Ready → check failed, 401/503/timeout/over-limit errors, disabled waiting buttons, Clear during a request without stale results, and markup displayed as text rather than HTML. Checked two columns at 1440px and one at 390px, with no horizontal overflow.
- **Mock UI screenshots only:** [Desktop](reports/screenshots/p05-t01-part2-mock-desktop-2026-10-11.jpg) · [Mobile](reports/screenshots/p05-t01-part2-mock-mobile-2026-10-11.jpg). Score/time/Ready values are mocked, not live Azure, accuracy or benchmark evidence.
- Stopped the created mock server, confirmed port 8080 was not listening and Check API reported the local relay unavailable. Restored the viewport and closed QA tabs.
- **Limits:** the mock UI checks did not verify a real Azure request; part 3 records that separate check.

### P05-T01 part 3 — end-to-end check with real Azure: `done`

- Used `python -m demo.server` from the existing `.venv`, bound to `127.0.0.1:8080`, with the existing Git-ignored `cloud.env` token. Target: Malaysia West `feedbackpulse-api`. Verified name/URL/Running status in Azure Portal first. No mock transport or local model.
- Ran Check API once (Ready at 21:00:34 Asia/Bangkok), then Analyse once each for Praise, Complaint and Other: **4 API requests** total. Results were positive/negative/neutral, with `sentiment-6e7ff9fbc17c-0110c462`. No browser errors/warnings observed.
- Actual results/images: [demo/README.md](demo/README.md#live-check--2026-10-11-p05-t01-part-3). UI scores are rounded to three decimals; timing is per-request round trip, not p95, accuracy or cold-start measurement. No extra load test or failure/recovery experiment.
- **Obstacle:** `az containerapp show` could not start because the Azure CLI `ml` extension was incomplete, so Portal was used to inspect the target. No extension deletion/install/fix, and no claim it was repaired. Did not use the P04 `scripts/cloud_check.py` suite.
- Stopped the local server after the live check. The CLI extension issue was not repaired.

### P05-T02 parts 1–2 — inspect existing monitoring and build the dashboard: `done` for these parts only

- Read-only inspection found native `Requests` and `ResponseTime` metrics on the existing App, usable without API/logger changes or a new metrics system. Timing is **Average Response Time (Preview)**, not p95, and covers the whole App, not only `/predict`.
- Created private dashboard **FeedbackPulse — API Monitoring**: Requests/Sum, ResponseTime/Avg, and Requests/Sum filtered/split by `statusCodeCategory` into 4xx/5xx. All share Past 24 hours, UTC and manual refresh. Notes explain scope, units and missing data.
- Saved [Portal export](cloudlayer/azure-dashboard.json) and [Azure screenshot](reports/screenshots/p05-t02-part2-azure-dashboard-2026-10-11.jpg). The image shows Requests 24, average time 65.44 ms, 4xx 3; Azure returned no 5xx series, so this is not a measured zero. A point-in-time view, not a benchmark/SLO.
- Added **Open monitoring ↗** beside Check API on the existing page, labeled Malaysia West / Azure sign-in / new tab. No separate monitoring page/backend route, SERVICE_TOKEN in the link or public dashboard sharing.
- **Checks:** `test_demo.py`, `test_cd_deployment.py`, `test_oidc_workflow.py` passed **172 tests** in 3.45s. Ruff check/format and `git diff --check` passed, with one existing Starlette/httpx deprecation warning. No installs. JSON metrics/filters/tile positions matched saved settings.
- **Browser check:** Opened the demo with dummy config/mock transport; the link opened a new Azure tab with the correct dashboard. Saved the [demo-button screenshot](reports/screenshots/p05-t02-part2-demo-monitoring-2026-10-11.jpg). No desktop horizontal overflow or console errors/warnings. Did not click Check API/Analyse or create new App test traffic. Stopped the local server and restored the viewport.
- **Limits:** The mobile viewport setting did not resize the demo tab, so no mobile-QA pass is claimed for this round. Reimporting the JSON as another dashboard was not tested; that does not block the dashboard already created, saved and opened.
- **Limits:** this checked the dashboard and its link, not alert delivery. The later [traffic-alert check](demo/README.md#traffic-alert--p05-t02-part-3) recorded 25/25 readiness requests in 28.874 seconds, Total = 25, Fired at 22:39:43 Asia/Bangkok and email receipt confirmed by the owner.

## P06 — documentation and operations

**Documentation and validation complete — 12 October 2026.** P06 remains
`in_progress` for demo operation and cleanup when the resources are no longer needed.

- **Guides:** [demo instructions and evidence index](README.md),
  [model card](MODEL_CARD.md), [cost estimate](reports/cost-report.md), and
  [failure story](README.md#failure-story-model-unavailable-and-rollback).
- **Validation:** 319 local tests and Ruff passed before `df46c10`. Files,
  credentials and screenshot privacy were reviewed.
  [CI #12](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211616924)
  passed; [CD #10](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211845155)
  and its deployment job were skipped with `FEEDBACKPULSE_CD_ENABLED=false`.
- **Operations:** keep resources while the demo needs them. Cleanup requires a
  checked target list and the resource owner's approval; do not remove shared
  resources as routine App cleanup. See the [operational notes](README.md#operational-notes).
- **Limits:** the documentation update did not redeploy or run a new benchmark,
  incident drill or alert test. The cost report is a scenario estimate, not a bill.
  Missing-model and rollback results came from separate experiments.

