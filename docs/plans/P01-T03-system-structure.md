# P01-T03 — System Structure

Original planning record: 2026-10-05, with the P02 handoff added on 2026-10-07.

Main plan: [Overview plan](../../overview-plan.md) · Project scope: [Proposal](../../PROPOSAL.md) · API contract: [P01-T02](P01-T02-api-contract.md)

**How to read this record:** This preserves the agreed design and decisions at the P01–P02 handoff. Statements about work not yet implemented refer to that stage. Later implementation and verification are recorded in [P03](P03-local-backend.md) and [P04](P04-deployment-and-cicd.md); current submission status is in the [README](../../README.md#submission-status-and-presentation-notes).

## 1. Agreed status and scope

- **P01-T03 status:** `done` for the three planning decisions, not for implementation.
- **Part 1 — Component roles and connections:** Approved by the user.
- **Part 2 — Locations for code, data, models and configuration:** The user approved the top-level structure and Git rules.
- **Part 3 — Checks and evidence for R1–R5:** The user approved the checks and evidence approach.
- **Implementation and testing:** This structure had not yet been implemented, deployed or tested.

FeedbackPulse will have one backend service, with the API and model in the same container. Model preparation and evaluation are a separate workflow in the same repo. This does not require exactly one instance or a second always-running server for model preparation.

Component roles, top-level folders, Git rules and evidence checks are agreed. Machine sizing and cloud resources are not fixed at this stage. Discuss changes and update this file rather than creating another copy of the agreement.

## 2. Model preparation — before using a release

This part will:

- Prepare a specified pretrained model revision.
- Evaluate it against versioned evaluation data.
- Package the required model, tokenizer and configuration files.
- Register the model with its code, data and upstream model versions.

**The output is a traceable model package that the serving system can use.**

Run this workflow when preparing a model or a new release, not for every feedback request. Training and fine-tuning remain out of scope.

## 3. Serving — receive feedback and predict

The backend will run on Azure Container Apps, as proposed. It will:

1. Receive the request and check its token and input.
2. Call the prepared model version.
3. Return the response defined in P01-T02.

Load the specified model when the app process starts, then reuse it across requests. Do not reload it for each message. Every new process or instance must load its own model before becoming ready. Process and instance counts are not decided at this stage.

For example, when “The staff were helpful.” arrives, the backend validates the request and uses the prepared model. It does not evaluate the dataset or prepare a new model during that request. This illustrates the agreed behavior, not a measured result.

If the model is not ready, report that state without returning a fake prediction. Follow the `/predict`, `/health` and `/ready` behavior in the [API contract](P01-T02-api-contract.md), rather than defining a second set of rules here.

## 4. One container, separate code responsibilities

- **API code:** Receive requests, check access and input, and format responses.
- **Inference code:** Prepare text for the model and turn its output into sentiment and score.
- **Cloud code:** Keep cloud calls in an adapter and read environment-specific values from configuration, following the course rules.

Evaluation and the API must share preprocessing and inference. Otherwise, the model could be evaluated one way and used differently in production.

Section 6 sets the top-level folders. Subfolders and individual filenames are not fixed yet.

## 5. Reasons and trade-offs

The scope has one API and one model. Keeping them in one container lets us build, deploy and roll them back together without another connection between an API service and a model service.

The trade-offs are:

- The API and model share resources.
- They cannot scale independently.
- Requests must wait until the model has loaded.

P02–P03 must measure RAM and startup time and test the proposal's performance target. The structure alone does not prove performance or cost.

## 6. Locations for code, data, models and configuration

The user approved these top-level locations and storage rules for implementation. **Do not create all these empty folders in advance.**

```text
/home/nirvana/feedbackpulse/
├── src/                  API, inference and evaluation code
├── cloudlayer/           Azure integration code
├── tests/                Test suite
├── data/                 Evaluation data downloaded locally
├── artifacts/            Prepared or downloaded model packages
├── reports/              Results and evidence
├── docs/
│   └── plans/            Agreed plans
├── cloud.env.example     Example configuration without secrets
├── cloud.env             Real configuration for this machine
├── .gitignore
├── README.md
├── PROPOSAL.md
└── overview-plan.md
```

Do not decide every subfolder and filename before the code shows what is needed.

Evaluation and the API both belong in the core code so they can share preprocessing and inference. Azure integration remains separate, as agreed in part 1.

Here, `data/` and `artifacts/` are local storage for downloaded or prepared files. This original structure did not choose shared artifact storage or how to put the model into the container.

## 7. What belongs in Git

| Item | Agreed rule |
|---|---|
| Code, tests and documentation | Commit to Git |
| Example configuration | Commit, without tokens or secrets |
| Real configuration and credentials | Do not commit or include in the Docker image |
| Actual datasets and large model files | Do not commit directly |
| Versions, hashes and dataset/model retrieval instructions | Commit so teammates can use the same versions |
| Required reports and evidence | Commit after checking for sensitive data |
| Caches, environments, raw logs and temporary files | Do not commit |

Keeping models out of Git does not mean teammates must find them themselves. Record versions and retrieval steps. Artifact storage was **decided in P02-T10 on 2026-10-07: include the artifact in the container image at build time**. See [P02 evidence, section 7](../../reports/P02-evidence.md).

These are development rules. This planning step did not edit `.gitignore` or create Docker build controls. Check actual file exclusion during the relevant implementation task; writing a rule does not prove protection.

## 8. Document roles and file creation

- **Overview:** Overall progress, status and next work.
- **Plans:** Agreements the team must follow.
- **Reports:** Observed results, such as evaluation, load tests and recovery.
- **README:** What a new user needs and how to run the project after cloning.

“The system must return `503` when the model is unavailable” is an agreement. Evidence must show that it actually returns `503` when model loading is deliberately broken. This example does not claim that test has run.

Create folders when there is a real file or task for them. Add build files, dependencies and CI when needed.

This file holds all three P01-T03 agreements. Do not create a separate document for every topic.

## 9. Checks and evidence for the course criteria

Based on the [instructor's capstone brief](https://github.com/pasdptt/public_teaching_mlaiops/blob/2e29fae/course/project/project-brief.md), this table records the agreed checks for FeedbackPulse. These are not recorded passes or new features.

| Criterion | What we must show | Evidence to keep |
|---|---|---|
| **R1 — Reproducible ML Pipeline** | Repeat prepare → evaluate → package → register and trace a deployed model to its code, data and upstream model revision | Reproduction steps, evaluation results, versions/hashes, run ID and lineage |
| **R2 — Deployment & CI/CD** | Follow P01-T02; tests block faulty changes, passing changes deploy, and rollback to an earlier release works | Test results, CI links, revisions before/after rollback and API results |
| **R3 — Monitoring & Reliability** | A dashboard shows real usage and at least one alert actually sends a notification | Dashboard/alert configuration, request counts, latency, errors and timestamped notification evidence |
| **R4 — Failure Handling & Technical Defense** | Deliberately make the model artifact unavailable; do not return fake predictions; detect the problem, recover, and use the lesson to add or improve a regression test | Event sequence, readiness/API results before/during/after the failure and the related regression test |
| **R5 — Documentation & Presentation** | Others can follow the README, understand model limits and trace cost calculations | Fresh-clone results, a one-page model card, cost per 1,000 predictions with calculations, and teardown evidence |
| **Live demo / defense** | Demonstrate the system, failure and unexpected-input handling, and explain the choices | Prepare and rehearse an 8-minute demo with 5 minutes of Q&A |

For R1, we reproduce the workflow that uses a pretrained model. We do not claim to reproduce its original training. This follows the instructor's approval as reported by the user in the [overview](../../overview-plan.md).

## 10. Checks to keep in view

- **Performance:** The proposal targets end-to-end p95 within 3 seconds at 2 concurrent requests after model loading. Report cold start and error rate separately. This is a target, not a measured result.
- **Portability:** Separate core code, configuration and cloud adapters as required by the course. Pass `make portability-audit` after implementing the relevant parts. At this planning stage, the command had not been created or run.
- **Secrets:** Check both Git history and the Docker image for credentials. Having `.gitignore` is not enough.
- **Reproduction:** The README must explain how to obtain data/model files and what access is needed, without relying on developer-only files.
- **Teardown:** Provide removal steps and evidence of the state after actual cleanup when usage ends, not just a written command.
- **Values to check in P02:** ~~Text limit and tolerance~~ → **checked on 2026-10-07**. The limit is 510 content tokens, or 512 with special tokens; see [P01-T02 §7](P01-T02-api-contract.md#7-decisions-and-original-handoff) and [evidence, section 3](../../reports/P02-evidence.md). Repeat-evaluation tolerance came from 6 measured runs; see [evidence, section 2](../../reports/P02-evidence.md). The rule against guessing measured values still applies to future checks.

## 11. Keep evidence short and checkable

Each evidence set should answer:

> What was checked → which version and conditions → expected result → actual result → limitations

Save useful summaries in `reports/` after real experiments, and link them from the README as described in section 8. Do not write a long report for every command or include secrets or sensitive data.

One experiment may support several criteria. For example, a model-loading failure could show both the R3 alert and R4 recovery. Do not repeat an incident only to split its reports.

## 12. Decisions at the original handoff

At this handoff, the first item had been resolved in P02 and the others were assigned to P03–P04. This list is historical, not work still waiting to start. Later container and cloud decisions are recorded in the [P03 plan](P03-local-backend.md) and [P04 plan](P04-deployment-and-cicd.md).

- ~~Shared model artifact storage~~ → **decided on 2026-10-07: put the artifact in the container image at build time, without separate blob storage**. This keeps the binding claimed by `model_version` true: replacing an artifact at runtime would leave that binding unenforced. It also makes rollback one operation. See [P02 evidence, section 7](../../reports/P02-evidence.md).
- How to bring model files into the container, such as including them at build time or downloading at startup.
- CPU and RAM allocation.
- Process and instance counts.

The text limit is recorded in [P01-T02 section 7](P01-T02-api-contract.md#7-decisions-and-original-handoff) instead of duplicating its status here.

**Handoff:** **P02 was completed**, and a teammate would take P03 next, as recorded in the [overview](../../overview-plan.md). P02 filled in the values left open by P01—text limit, tolerance and artifact storage—and recorded evidence for the team, without starting P03.

The decisions were handed to P03–P04 with this warning: [P02 evidence, section 6](../../reports/P02-evidence.md) reports peak RSS of **783 MiB** for maximum-length API inputs, **not the 341 MiB measured after loading**. This is the maximum across 10 boundary-length samples; use the maximum, not the median. **These measurements were on macOS, not in a container, so they did not establish container sizing.** Later container checks are in the [P03 review](P03-local-backend.md#check-docker-for-the-latest-code-locally--2026-10-10). P02 itself did not provide CPU, process-count or instance-count measurements.

All three P01-T03 planning decisions were agreed. Overall P01 status and open work remain in the [overview](../../overview-plan.md). This record does not automatically authorize implementation, cloud resource creation or commit/push.
