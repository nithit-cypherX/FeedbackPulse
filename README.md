# FeedbackPulse

A backend API that classifies short English feedback as negative, neutral, or
positive for human review. It returns the sentiment, score and model version.
We use a pinned pretrained model and evaluate, package and register it; we do
not train a new model in this project.

## Status

Last recorded checks: **11 October 2026**. The API has been deployed to Azure
Container Apps, CI/CD has passed, and the localhost demo has called the real API.
The monitoring dashboard and traffic alert have also been checked, including
email receipt confirmed by the owner. These are recorded results, not a live
service-status check.

We are now preparing the final documentation in P06. The submission is not yet
complete; see the remaining items below.

## Run the local demo

The page runs on your laptop and sends requests through a local Python relay to
the deployed API. The relay keeps the service token out of the browser. It does
not load the model locally or deploy anything to Azure.

**Working-copy note:** `demo/`, the dashboard export and screenshots are still
local, uncommitted files. The steps below apply to this working copy; a fresh
clone of `main` does not include these files yet.

You need Python **3.13**, `uv`, Bash (for example, Ubuntu in WSL), internet access,
and the deployed API's `SERVICE_TOKEN` from its owner. An Azure login is not
needed for predictions, but the private monitoring dashboard needs an account
with access to the Azure resources.

From the repository root:

```bash
# Skip this if the project's locked .venv is already prepared.
uv sync --frozen

# API used in the latest recorded demo. Use its matching service token.
export FEEDBACKPULSE_API_URL='https://feedbackpulse-api.happybay-6ab85ce1.malaysiawest.azurecontainerapps.io'
read -rsp 'Service token: ' SERVICE_TOKEN; echo
export SERVICE_TOKEN
.venv/bin/python -m demo.server
# After stopping the server with Ctrl+C:
unset SERVICE_TOKEN
```

Open **http://127.0.0.1:8080**, click **Check API**, then enter English feedback
and click **Analyse feedback**. The page shows the API's result, not a preset
answer. **Open monitoring** opens the private Azure dashboard in another tab.

Keep the relay on localhost; do not expose it through a tunnel. Do not commit
tokens or put them in frontend code. The relay reads environment variables, not
`.env` files automatically. See the [demo guide](demo/README.md) for checks,
timeouts, privacy limits and screenshots.

## Evidence and project guides

| Area | Where to look | What the evidence covers |
|---|---|---|
| Model summary | [FeedbackPulse model card](MODEL_CARD.md) | Intended use, model version, evaluation results, limitations and licences |
| Model pipeline | [P02 evidence](reports/P02-evidence.md) | Evaluation, repeatability, pinned model/data versions, packaging and registry lineage |
| API and local checks | [API contract](docs/plans/P01-T02-api-contract.md), [P03 evidence](reports/P03-evidence.md) | Inputs, authentication, validation, health/readiness and local model-unavailable checks |
| Team deployment results | [P04 evidence](reports/P04-evidence.md) | East Asia API checks, warm p95 of 0.213 s at two concurrent users, and a 15 s rollback traffic cutover |
| Latest automated deployment | [CI #11](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139654748), [CD #9](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139856763), [P04 handoff](docs/plans/P04-deployment-and-cicd.md) | Passing CI/CD for commit `8d3964c` in Malaysia West, including readiness and smoke checks |
| Demo and monitoring | [Demo guide and evidence](demo/README.md) | Three live sentiment examples, three dashboard charts and a traffic alert that reached the owner's email |
| Cost estimate | [Cost per 1,000 predictions](reports/cost-report.md) | Scenario assumptions, rates, calculation, shared-cost treatment and exclusions; not an actual Azure bill |
| Architecture and operations | [System structure](docs/plans/P01-T03-system-structure.md), [cloud adapter](cloudlayer/README.md), [operations scripts](scripts/README.md) | System design, deployment configuration and existing operational commands |

The East Asia latency/rollback results and the Malaysia West CD/demo results
come from different deployments. We have not repeated the East Asia benchmarks
in Malaysia West. The demo's response time is one browser round trip, not p95.
The P04 report is the team's earlier record; use the linked CI/CD runs and
handoff for the later Malaysia West deployment.

## Failure story: model unavailable and rollback

These were **two separate experiments**, not one failure followed by a rollback.

### P03 — What happens when the model cannot load?

In the local container test, we set `MODEL_DIR` to a folder that did not exist.
The API process kept running: `/health` returned 200, but `/ready` and `/predict`
returned 503 with `MODEL_NOT_READY`. It did not return a fake prediction.

This showed why “the API is running” and “the model is ready” need separate
checks. Our existing `test_health_and_readiness_separation` checks this behavior
so future changes do not accidentally report an unavailable model as ready.

Evidence: [P03 report](reports/P03-evidence.md) and [API test](tests/test_api.py).

### P04 — Can we switch back to an earlier version?

In a separate East Asia drill, we sent traffic to the newer revision, then
switched 100% back to the previous stable revision. The recorded traffic change
took **15 seconds**. Readiness checks ran afterward, and `/health`, `/ready`, and
`/predict` returned 200.

This showed that we could switch back without rebuilding the image. It also
showed why we should check readiness after changing traffic. The drill did
**not** deliberately break the newer revision, and 15 seconds was the
traffic-change time—not the total recovery time.

Evidence: [P04 rollback report](reports/P04-evidence.md) and
[recorded result](reports/P04-rollback-evidence.json).

## Remaining submission work

- **Before push:** run the relevant tests/lint, review the exact file set, and
  check secrets, screenshot privacy and remote/CI/CD state. A push to `main`
  triggers CI and can trigger deployment if `FEEDBACKPULSE_CD_ENABLED=true`.
  Include only reviewed files after commit/push approval. Remove the working-copy
  note above when those files are included in the submission commit.
- **Before the presentation:** keep the App and monitoring resources needed for
  the demo. Start the localhost page when needed and stop it afterward; stopping
  the local page does not stop Azure resources. Use the saved failure/rollback
  evidence instead of running a new incident drill.
- **After the presentation, with approval:** review the alert/action group and
  App cleanup, then any other project-only resources that are no longer needed.
  Check exact targets and shared use first. Do not delete the shared ACR, Log
  Analytics workspace or the whole resource group as routine project cleanup.
  `make teardown` deletes only the App and its revisions, not all resources or
  the alert. Current CD updates an existing App; a push will not recreate a
  deleted App. See the [cleanup guide](scripts/README.md#4-cloud-resource-cleanup-teardown--p04-t06).

See the [original proposal](PROPOSAL.md) for the initial scope and budget, and
the [overview plan](overview-plan.md) for task history. Some older plan entries
describe earlier states; they are not the latest deployment result.

This repository is for the team project. Individual coursework and labs remain
in the separate [MLOps Engineering repository](https://github.com/nithit-cypherX/mlops-engineering).
