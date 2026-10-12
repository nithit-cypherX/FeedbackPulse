# FeedbackPulse — Overview Plan

**Latest work point — 2026-10-12:** P05 `done` within the approved local-demo/monitoring scope. P06 submission checks are complete, and the reviewed demo, documentation and evidence were pushed to `main` in `df46c10`. [CI #12](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211616924) passed; [CD #10](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211845155) was skipped with `FEEDBACKPULSE_CD_ENABLED=false`. No new deployment. Presentation and later cleanup remain separate from submission. See [P06 handoff](#p06--final-submission-and-handoff).

Keep the team's existing P01–P04 work and the verified CD fix as the base. P05-T03 remains canceled; no new failure/recovery experiment or traffic-spike button is required. The local demo is stopped. Cloud results below are dated evidence, not a live status check; presentation resources have not been cleaned up in this documentation step.

**Previous P05 handoff — 2026-10-11:** P05 `in_progress`, P06 `planned` at that point. The user chose to use the team's existing P04 work plus the fixed CD as the base, without revising the old report or adding more P04 work. **P05-T01 and P05-T02 are complete within the demo/monitoring scope:** three dashboard graphs, an Open monitoring button and a traffic alert at `Requests >= 20 / 1 minute`. All 25 `/ready` requests passed in 28.874s; Azure counted 25 and the alert Fired at 22:39:43 Thai time. The user confirmed email receipt. See the [alert record](demo/README.md#traffic-alert--p05-t02-part-3). This is not model-failure/recovery evidence for canceled P05-T03. No API/CD changes or commit/push; P06 had not started at this handoff.

Status before P05: 2026-10-11 · main branch: `main` · P01: `in_progress` · P02: `done` per the original report · P03: new technical review passed; user approved returning to P04 · P04: `in_progress` (CI #11 and CD #9 passed after the bounded-readiness-wait fix; revision 0000002 Healthy/Running, 100% traffic, API 6/6 passed) · P05–P06: `planned`.

**Previous P04 handoff:** Fixed only the CD readiness wait, with a 5-minute limit and 75 passing tests. Committed/pushed only workflow/tests in `8d3964c`. [CI #11](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139654748) and [CD #9](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139856763) passed automatically through smoke tests. The live run waited about 34 seconds until latest=ready=`feedbackpulse-api--0000002`, image matched the SHA and traffic was 100%. Post-CD Azure/API checks passed 6/6. No new roles/resources, secret changes or extra trial runs. Images/notes stayed local, not committed/pushed; existing pending work was preserved. CD switch remained true. This closed the bug, not the whole P04 phase or authorization to start P05–P06. See the [P04 plan](docs/plans/P04-deployment-and-cicd.md#latest-handoff--wait-for-revision-readiness-before-passing-cd--2026-10-11). Entries below are history, not current status.

## Work point at the time — resume OIDC/CD on user approval, 2026-10-10

- After reviewing results, the user resumed P04 one part at a time. **2.1 target inspection** was completed read-only. **2.2** created `id-feedbackpulse-cd` in the user's Azure account and confirmed **0** federated credentials / **0** role assignments. No Lab 4 identity, GitHub/CD or deployment changes.
- Saved a real Overview capture for presentation at [reports/screenshots/p04-02-02-managed-identity-created-2026-10-10.jpg](reports/screenshots/p04-02-02-managed-identity-created-2026-10-10.jpg), with results/limits in the [P04 plan](docs/plans/P04-deployment-and-cicd.md#resume-p04-t03-inspect-the-target-and-create-an-identity--2026-10-10).
- **2.3 first attempt:** Safety review blocked trust creation before execution because `production` had no branch restriction. See the [original obstacle](reports/screenshots/p04-02-03-production-branch-restriction-pending-2026-10-10.jpg). This condition was later fixed as recorded below.
- The user requested a branch rename first. GitHub's default branch and the local branch became `main`, tracking `origin/main`; commits and uncommitted work were preserved. See [rename evidence](reports/screenshots/p04-default-branch-main-2026-10-10.jpg) and the P04 plan.
- GitHub automatically started CI #7 after rename; it passed. CD #5 then failed at Azure login because settings were missing, and deployment was skipped. Cancellation did not succeed and completed runs no longer needed cancellation. Details/screenshots/run links are in the P04 plan.
- **2.3 configured:** `production` allows only `main` (1 branch/0 tags). Azure has one `github-feedbackpulse-production` trust entry on `id-feedbackpulse-cd`, with matching read-back. Roles remained **0**; no workflow/login/deployment yet. See [GitHub](reports/screenshots/p04-02-03-production-main-only-2026-10-10.jpg), [Azure](reports/screenshots/p04-02-03-federated-trust-created-2026-10-10.jpg) and verification limits in the P04 plan.
- **2.4 item 1, local only:** Added a manual/main/production login-only workflow and a default-off CD guard requiring repository variable `FEEDBACKPULSE_CD_ENABLED=true`. **24 tests**, lint and diff checks passed locally. No roles/GitHub settings, commit/push, workflow run or deployment. Details/limits: [P04 plan](docs/plans/P04-deployment-and-cicd.md#section-24-item-1--prepare-login-only-locally--2026-10-10).
- **2.4 item 2 succeeded:** Committed/pushed only two workflows and one test file in `5ef6c90`. [CI #8](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38067390683) passed; [CD #6](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38067594679) and its deploy job were **Skipped**. Login-only still had 0 runs. No secrets, roles or deployment. Saved [CI](reports/screenshots/p04-02-04-ci-pass-2026-10-10.jpg), [CD](reports/screenshots/p04-02-04-cd-skipped-2026-10-10.jpg) and plan notes locally; images/plans/P02–P03 work were not in the commit.
- **2.4 item 3, part A complete:** Verified this repo's identity/trust, **0** roles, main-only `production` and CD still off. Set the two Environment secrets `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`, confirmed their names after reload and saved [evidence](reports/screenshots/p04-02-04-production-login-settings-2026-10-10.jpg). Login-only still **0 runs**. No workflow/code, commit/push, roles or deployment.
- **2.4 item 3, part B passed:** With user approval, ran [OIDC login-only #1](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38068476836) once on `main`/`5ef6c90`: **Success 13s**, login/identity-check job **7s**. See [passed steps](reports/screenshots/p04-02-04-oidc-login-steps-2026-10-10.jpg) and log/warning limitations in the P04 plan. Roles remained **0**, latest CD was still #6. No deployment, workflow/code changes or commit/push.
- **2.5 item 1, local only — 2026-10-11:** The user approved removing old target/sample-token fallbacks and replacing ACR password auth with managed identity. Changed template/renderer, `Makefile:deploy` caller, config example, docs and tests within P04. **84 focused tests**, lint/template/diff checks passed. No P01–P03, dependency, CI or login-only-workflow changes; no commit/push, roles, resources or deployment. See [P04 plan](docs/plans/P04-deployment-and-cicd.md#section-25-item-1--local-cd-changes-awaiting-diff-review--2026-10-11).
- **2.5 item 2 complete — 2026-10-11:** Created `id-feedbackpulse-pull` and granted `AcrPull` only on ACR `itcs355u6688124`, as approved. Read-back: one role, 0 federated credentials, CD roles still 0. No registry-setting changes, App/Environment creation or deployment. See [identity](reports/screenshots/p04-02-05-pull-identity-created-2026-10-11.jpg), [AcrPull](reports/screenshots/p04-02-05-pull-acrpull-2026-10-11.jpg) and [scope/limits](docs/plans/P04-deployment-and-cicd.md#section-25-item-2--prepare-the-pull-identity-and-acrpull--2026-10-11).
- **2.6 not accepted yet — 2026-10-11:** Created Malaysia West `feedbackpulse-env` with existing Log Analytics. Portal/ARM API `2026-07-01` confirmed Express, which lacks the multiple revisions/traffic splitting required by the template/rollback plan. CPU usages were empty, leaving quota unconfirmed. See [actual result](reports/screenshots/p04-02-06-environment-created-2026-10-11.jpg) and [P04 details](docs/plans/P04-deployment-and-cicd.md#section-26--environment-created-but-its-type-differs-from-the-plan--2026-10-11). CD roles 0, Apps 0; no logs-setting/code changes, push or deployment.
- **2.6 type-change request failed — 2026-10-11:** One PATCH on the existing Environment at 12:57:47 Thai time. Observed Failed at 13:26:23 with `ManagedEnvironmentOperationFailed / internal server error`. Mode changed to WorkloadProfiles but was not usable. Existing logs/profile remained, Apps/Jobs 0, CD roles 0. No retry/delete/replacement. See [error](reports/screenshots/p04-02-06-workload-profiles-update-failed-2026-10-11.jpg) and [read-back](docs/plans/P04-deployment-and-cicd.md#section-26-continued--one-attempt-to-change-the-existing-environment-type--2026-10-11).
- **2.6 separately approved recovery succeeded:** One more PATCH at 13:43:39 Thai time on 2026-10-11. Observed WorkloadProfiles / Succeeded with no error at 13:45:01, without deletion/recreation. Kept one Consumption profile/existing Log Analytics. Post-check: no App/Job, CD roles 0 and existing pull AcrPull. See the [recorded results and limits](docs/plans/P04-deployment-and-cicd.md#section-26--one-more-recovery-attempt-on-the-same-environment--2026-10-11). The saved screenshot does not show the recovery result and is not used as evidence.
- **2.7 CD permissions on existing resources complete — 2026-10-11:** With approval, granted `id-feedbackpulse-cd` `AcrPush` only on the existing ACR, `Container Apps Operator` only on `feedbackpulse-env`, and `Managed Identity Operator` only on `id-feedbackpulse-pull`. All 3 matched principal/scope on read-back. Existing pull AcrPull remained. No App/Job, CD enablement, workflow run, image push or deployment. See [roles](reports/screenshots/p04-02-07-cd-resource-roles-2026-10-11.jpg) and [details/limits](docs/plans/P04-deployment-and-cicd.md#section-27--cd-permissions-on-existing-resources--2026-10-11). Accepted that AcrPush covers the whole existing registry, not only the feedbackpulse repository.
- **Not yet approved at this point:** App creation and `Container Apps Contributor`. Propose the first real App deployment using the user's account, then give CD access only to that App. No RG-wide roles, automatic CD enablement or commit/push. Consumption CPU quota remained unconfirmed; role grants did not prove deployment would work. No further Environment recovery needed.

## Pause point and conditions for returning to OIDC/CD — 2026-10-10

- The user paused GitHub Actions/Azure work to review and understand P01–P03. Only proposing the review and recording the agreement were authorized, not all inspections or changes to teammates' implementation.
- **Do not start part 2 of the OIDC/CD fix** (identity, trust, permissions/GitHub settings) until P01–P03 pass the agreed checks, evidence supports relevant requirements, and the user reviews the explanation. Report/propose fixes for incorrect or unverified requirements first; do not skip this condition.
- Proposed review order: compare brief/proposal with P01 agreements → check P02 model/pipeline/evidence → check P03 API/container → check model-artifact, configuration and model-version handoffs. Review one part at a time and explain in chat. No Azure deployment, monitoring or new features.
- Finding an issue does not automatically authorize a fix. Separate requirement-breaking problems from optional improvements, and propose focused changes for user review.
- Resume point: OIDC/CD inspection part 1 was completed read-only. The Azure account had Owner. [CD run #4](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38048373569) failed at Service Principal Fallback because login settings were missing; repo/`production` had no secrets/variables at inspection. No identity, permission change or deployment yet.
- After these conditions pass, propose part 2 and recheck relevant Azure/GitHub state. Old checks do not prove current state. The `done` labels/results below are original handoff records, not acceptance from this new P01–P03 review.

The original proposal split **FeedbackPulse into 6 main parts**, using `plan-and-track-work`: outline the project first, then break down only the active phase to keep the task list manageable.

At initial planning, the local repo had a proposal, README and `.gitignore`, but no system code. The plan below therefore described **proposed work, not completed work**.

## Six-part overview

Based on the [instructor's capstone criteria](https://github.com/pasdptt/public_teaching_mlaiops/blob/2e29fae/course/project/project-brief.md) and agreed FeedbackPulse scope:

| Phase | Work | Done when |
|---|---|---|
| **P01 — Agree on the system and responsibilities** | Define API input/output, separate core/configuration/cloud adapter, and assign owners | Team agrees on the design for architecture review and confirms proposal approval before development |
| **P02 — Reproducible model pipeline** | Pin a pretrained model, version evaluation data, then evaluate → package → register with lineage | Workflow can be rerun; a registered model traces to code, data, model revision and evaluation — **R1** |
| [**P03 — Run the backend locally**](docs/plans/P03-local-backend.md) | Accept English text; return sentiment, score and model version; add validation, access control, health/readiness and Docker | Real container API works, with tests for valid/bad input and model-not-ready cases — base for **R2** |
| [**P04 — Deploy and release safely**](docs/plans/P04-deployment-and-cicd.md) | Test before Azure Container Apps deployment through CI/CD; measure latency, test rollback, manage credentials/tags/budget from the start | Tests block faulty changes, passing versions deploy, and rollback works — **R2** |
| **P05 — Local demo and small monitoring setup** | One localhost page calls the real Azure API through a server-side-token relay; add only needed dashboard/alert work. Use team screenshots instead of a new failure/recovery experiment, as requested | Web UI calls the API and shows errors honestly. Verify dashboard/alert separately from UI; old images cannot prove untested behavior |
| **P06 — Finish submission and presentation** | Fill only gaps in demo instructions, README, model card, cost per 1,000 predictions, existing evidence, teardown and rehearsal | Others can follow the instructions; evidence limits are clear; unused resources are cleaned up with approval. No unrelated features |

**Test and collect evidence during each phase.** P06 checks completeness and prepares the submission; it is not the first time tests/evidence are written.

## ML and development responsibilities

For three team members, the original proposal assigns:

- **Person 1 — Model and evaluation:** P02 and the model-to-API interface.
- **Person 2 — Backend and deployment:** P03–P04.
- **Person 3 — Monitoring and reliability:** P05, cost records and documentation.
- **Everyone:** P01 design agreement and P06 demo preparation.

Member names remain for the team to assign. Work does not need to be fully sequential: after input/output agreement, API work can start while the model is being prepared.

## What stays outside scope

Keep **one backend, one pretrained model and three sentiment classes**. No production frontend, CRM integration, chatbot or training/fine-tuning. On 2026-10-11, the user approved only a localhost demo page: a client for the existing API, not a full web product.

Using a pretrained model **does not remove model-side MLOps work**. We still version, evaluate, track and register it for traceability. P02 adapts to the instructor clarification reported by the user; it does not claim to reproduce the upstream model's training. The shared brief still says *automated training*, but on 2026-10-05 the user reported instructor approval of the proposal and agreed pretrained scope.

## Original P01 plan and status

Start with just three tasks:

1. **P01-T01 — Confirm scope and proposal status**

   Scope/status were confirmed from the user's 2026-10-05 report of instructor approval. Owner names were still missing from the documents and remained for the team to fill in.

2. **P01-T02 — Agree on the API format**

   Main agreements were approved. See the [API contract](docs/plans/P01-T02-api-contract.md) for request/response, validation and errors. **`done` means agreement only, as of 2026-10-07**: P02-T03 confirmed 510 content tokens (512 with special tokens). Implementation/testing were not yet done; API boundary checks belong to P03.

3. **P01-T03 — Define system structure and checks**

   `done` for planning only. All three areas were agreed: system responsibilities, folders/Git rules, and R1–R5 checks/evidence. See [System structure](docs/plans/P01-T03-system-structure.md) for the architecture-review base. Not implemented/tested at this stage.

**Handoff:** P01 agreements were recorded. **P02-T03 closed the text-length limit**, leaving only **owner names still shown as `[Name]` in [Proposal §7](PROPOSAL.md)** before full P01 closure.

## P02 complete

See [P02 phase plan](docs/plans/P02-model-pipeline.md) · Owner: Person 1.

- Active `model_version`: `sentiment-6e7ff9fbc17c-0110c462`, with lineage in `reports/registry/`; run ID `run-20261007T192531Z-d36357`.
- Evaluation on 14,640 rows: **accuracy 0.8100 · macro-F1 0.7606** ([evidence, section 2](reports/P02-evidence.md)).

**Handoff:**
- **Person 2 can start P03:** read the [locked interface, section 9](reports/P02-evidence.md) and [artifact-storage decision, section 7](reports/P02-evidence.md). Text limit: [P01-T02 §7](docs/plans/P01-T02-api-contract.md).
- **Person 3 must read** [evidence, section 7](reports/P02-evidence.md): the failure-demo method changes because the artifact is in the image, not a deletable blob.

## P03 complete — local backend

**New review, 2026-10-10:** Token, model-binding, startup and error-log fixes passed **106 tests** in the locked environment. Latest container build/smoke checks also passed: local image ID `e4159c364b3ab`, non-root, **20 HTTP checks**, missing-token startup and Docker healthcheck. Included offline missing-model and 510–511-token boundaries. Details/RAM: [P03 plan](docs/plans/P03-local-backend.md#check-docker-for-the-latest-code-locally--2026-10-10). At this handoff, user review was still needed before acceptance; returning to OIDC/CD was not automatic. Numbers below are the original handoff, not the new image/test run.

See [P03 phase plan](docs/plans/P03-local-backend.md) · [test/measurement evidence](reports/P03-evidence.md) · Owner: Person 2.
- Status: `done`, all 8 tasks T01–T08.
- Automated tests: **55/55 passed, 100%**, in ~7.68 seconds.
- Container: `feedbackpulse:local` (recorded digest `16030a4a4dbf`), non-root with the model included.
- Smoke tests: real container API passed valid, 401, 400, 422 and 510-token-limit cases.
- Container memory: **645.8 MiB**, used for P04 sizing.
- Simulated failure: confirmed separation of `/health` (200) and `/ready` (503).

## P04 — original handoff and CD-verification limits

**Status at that handoff:** P04 could not close because the latest automated CD had failed, as noted in the pause record above. The `done` items below are the original teammate report, not the new review's confirmation of CD success. This does not automatically invalidate other manual-deployment evidence.

See [P04 phase plan](docs/plans/P04-deployment-and-cicd.md) · [test/measurement evidence](reports/P04-evidence.md) · Owner: Person 2 (Backend and deployment).
- **Reported status:** `done`, all 6 tasks T01–T06, **R2** reported 100% complete.
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

## P05 — local demo and small monitoring setup (approved scope, 2026-10-11)

- **P05-T01 — demo calling the real API:** `done`: (1) relay/tests, (2) HTML/CSS/JavaScript page, (3) browser-to-Azure check/screenshots below. This did not automatically close all P05 or start P05-T02.
- **P05-T02 — small monitoring setup:** `done`: dashboard/demo link and live traffic alert. `/ready` 25/25 returned 200, metric counted 25, alert Fired and the user confirmed email receipt. See [part 3 record](demo/README.md#traffic-alert--p05-t02-part-3). No API/CD changes or model-failure proof.
- **P05-T03 — new failure/recovery experiment:** canceled by the user due to presentation time limits. Use the existing [failure story](README.md#failure-story-model-unavailable-and-rollback) and linked team evidence. P03's local missing-model test and P04's East Asia rollback were separate experiments, not one failure-to-alert-to-recovery run.
- **Non-goals:** no login/database, permanent feedback storage, frontend deployment, local model loading or existing API/CD changes.

### P05-T01 part 1 — localhost relay: `done`

- Added [demo/server.py](demo/server.py), [relay instructions](demo/README.md) and [tests/test_demo.py](tests/test_demo.py), using Python 3.13.11 and existing `.venv` dependencies. No `pyproject.toml`/`uv.lock` changes.
- Accepts only `POST /api/predict` and `GET /api/ready`. HTTPS target/token come from environment. Callers supply only text, not URLs/headers. No redirect following, retries or token exposure to the browser. Restricts localhost Host/Origin and binds `127.0.0.1:8080`.
- Total deadline 60 seconds, connect timeout 10 seconds. Returns short errors, not raw upstream errors; no feedback/token logging. The existing API still enforces 510 tokens.
- **Checks:** `.venv/bin/python -m pytest -q tests/test_demo.py tests/test_cd_deployment.py tests/test_oidc_workflow.py` passed **162 tests** (87 demo + 75 existing CI/CD) in 7.13s. Ruff passed for the two new Python files. One existing Starlette TestClient/httpx warning; no replacement packages installed.
- **Issue fixed:** An incomplete Unicode surrogate in JSON caused pre-send encoding to fail. Now returns `422`, covered by a passing regression test. Malformed Unicode upstream responses return `502`.
- **Real process check:** Started the WSL entry point with dummy config/token. Four localhost HTTP cases passed: no web page 404, invalid input 422, other origin 403, target query 400. All stopped before upstream; no Azure requests. Stopped the created process and confirmed port 8080 closed.
- **Limits/handoff:** Mock-transport tests, not live Azure results. No page yet; parts 2/3 had not started. No API/CD/Makefile or existing-pending-work changes. No commit/push.

### P05-T01 part 2 — localhost demo page: `done`

- Added [HTML](demo/static/index.html), [CSS](demo/static/styles.css) and [JavaScript](demo/static/app.js), following the agreed layout: text/examples on the left, sentiment/model score/response time/model version on the right, Check API below. Narrow screens use one column.
- Examples only fill text; Analyse sends through the relay. No token/target URL in the browser, history or polling. Editing/Clear removes old results; canceled-request results cannot overwrite new text. Explains score vs accuracy and request round-trip time vs p95 separately.
- `demo/server.py` serves only `/` and `demo/static/`, with same-origin script/style/connect CSP, not other repo files. Updated [demo instructions](demo/README.md) to match behavior. No new dependencies or API/CD/Makefile changes.
- **Automated checks:** `.venv/bin/python -m pytest -q tests/test_demo.py tests/test_cd_deployment.py tests/test_oidc_workflow.py` passed **171 tests** (96 demo + 75 existing CI/CD) in 8.42s. Ruff check/format passed; one existing Starlette TestClient/httpx deprecation warning. No installs.
- **Browser checks:** Real WSL FastAPI relay with `httpx.MockTransport`/dummy token, no Azure/network upstream. Checked initial empty/Not checked, no automatic submission from examples, positive/negative/neutral, Ready → check failed, 401/503/timeout/over-limit errors, disabled waiting buttons, Clear during a request without stale results, and markup displayed as text rather than HTML. Checked two columns at 1440px and one at 390px, with no horizontal overflow.
- **Mock UI screenshots only:** [Desktop](reports/screenshots/p05-t01-part2-mock-desktop-2026-10-11.jpg) · [Mobile](reports/screenshots/p05-t01-part2-mock-mobile-2026-10-11.jpg). Score/time/Ready values are mocked, not live Azure, accuracy or benchmark evidence.
- Stopped the created mock server, confirmed port 8080 was not listening and Check API reported the local relay unavailable. Restored the viewport and closed QA tabs.
- **Handoff:** Wait for part 3 approval to check browser → relay → real Azure API and capture actual results. P05-T01 was not fully closed yet. No commit/push.

### P05-T01 part 3 — end-to-end check with real Azure: `done`

- Used `python -m demo.server` from the existing `.venv`, bound to `127.0.0.1:8080`, with the existing Git-ignored `cloud.env` token. Target: Malaysia West `feedbackpulse-api`. Verified name/URL/Running status in Azure Portal first. No mock transport or local model.
- Ran Check API once (Ready at 21:00:34 Asia/Bangkok), then Analyse once each for Praise, Complaint and Other: **4 API requests** total. Results were positive/negative/neutral, with `sentiment-6e7ff9fbc17c-0110c462`. No browser errors/warnings observed.
- Actual results/images: [demo/README.md](demo/README.md#live-check--2026-10-11-p05-t01-part-3). UI scores are rounded to three decimals; timing is per-request round trip, not p95, accuracy or cold-start measurement. No extra load test or failure/recovery experiment.
- **Obstacle:** `az containerapp show` could not start because the Azure CLI `ml` extension was incomplete, so Portal was used to inspect the target. No extension deletion/install/fix, and no claim it was repaired. Did not use the P04 `scripts/cloud_check.py` suite.
- No demo/API/CD, dependency, `cloud.env` or cloud-resource changes. Updated only work/usage notes and added real-result screenshots. Stopped the local server afterward. No commit/push; existing pending work preserved.
- **Handoff:** P05-T01 can close within demo-page scope. Next: propose P05-T02 small monitoring before starting. The CLI extension remains a separate tooling issue to inspect if later work needs CLI.

### P05-T02 parts 1–2 — inspect existing monitoring and build the dashboard: `done` for these parts only

- Read-only inspection found native `Requests` and `ResponseTime` metrics on the existing App, usable without API/logger changes or a new metrics system. Timing is **Average Response Time (Preview)**, not p95, and covers the whole App, not only `/predict`.
- Created private dashboard **FeedbackPulse — API Monitoring**: Requests/Sum, ResponseTime/Avg, and Requests/Sum filtered/split by `statusCodeCategory` into 4xx/5xx. All share Past 24 hours, UTC and manual refresh. Notes explain scope, units and missing data.
- Saved [Portal export](cloudlayer/azure-dashboard.json) and [Azure screenshot](reports/screenshots/p05-t02-part2-azure-dashboard-2026-10-11.jpg). The image shows Requests 24, average time 65.44 ms, 4xx 3; Azure returned no 5xx series, so this is not a measured zero. A point-in-time view, not a benchmark/SLO.
- Added **Open monitoring ↗** beside Check API on the existing page, labeled Malaysia West / Azure sign-in / new tab. No separate monitoring page/backend route, SERVICE_TOKEN in the link or public dashboard sharing.
- **Checks:** `test_demo.py`, `test_cd_deployment.py`, `test_oidc_workflow.py` passed **172 tests** in 3.45s. Ruff check/format and `git diff --check` passed, with one existing Starlette/httpx deprecation warning. No installs. JSON metrics/filters/tile positions matched saved settings.
- **Browser check:** Opened the demo with dummy config/mock transport; the link opened a new Azure tab with the correct dashboard. Saved the [demo-button screenshot](reports/screenshots/p05-t02-part2-demo-monitoring-2026-10-11.jpg). No desktop horizontal overflow or console errors/warnings. Did not click Check API/Analyse or create new App test traffic. Stopped the local server and restored the viewport.
- **Limits:** The mobile viewport setting did not resize the demo tab, so no mobile-QA pass is claimed for this round. Reimporting the JSON as another dashboard was not tested; that does not block the dashboard already created, saved and opened.
- **Handoff:** Propose the alert and wait for approval. No API/CD, cloud.env, dependency or role changes; no deploy or commit/push. Existing pending work preserved. The **dashboard plus alert** criterion was not fully verified at this step.

## P06 — final submission and handoff

**Status: submission checks and push complete, 12 October 2026.** P06 remains `in_progress` only for presentation and later approved cleanup.

- **Written:** [demo instructions and evidence index](README.md), [model card](MODEL_CARD.md), [cost estimate](reports/cost-report.md), and [failure story](README.md#failure-story-model-unavailable-and-rollback). Plans and reports are in English; the original experimental results are preserved.
- **Documentation review:** current status, configuration loading, historical rollback examples and cleanup scope have been clarified. The cost is a scenario estimate, not an Azure bill; the two failure-story experiments remain separate.
- **Submission checks completed:** 319 tests and Ruff passed in the existing environment. File selection, secrets, screenshot privacy and remote/CI/CD state were reviewed. Only the approved 63 files were committed and pushed in `df46c10`; the 10 excluded screenshots stayed local and were not deleted.
- **Push verified:** local `main` and GitHub `main` matched `df46c10`. [CI #12](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211616924) passed; [CD #10](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38211845155) and its deploy job were skipped. CD remains paused with `FEEDBACKPULSE_CD_ENABLED=false` at the user's request.
- **Presentation and cleanup:** keep the required resources until the presentation. Later cleanup needs approval and a checked target list; shared lab resources must not be deleted as part of routine App cleanup. See the [handoff checklist](README.md#remaining-submission-work).
- **Limits:** the submission push did not deploy a new API version. No new benchmark, failure drill, alert test or Azure resource change was made for submission. Member-name placeholders stay as the user requested.

