# P02 — Reproducible model pipeline

- **Status: `done`** for the P02 delivery and reviewed fixes. All 11 tasks were originally reported complete on 2026-10-07. Later [P03 checks](P03-local-backend.md#check-docker-for-the-latest-code-locally--2026-10-10) verified the real-model/API integration and container. Original P02 measurements and their limits are unchanged.
- Owner: Person 1 — Model and evaluation.
- Main plan: [Overview](../../overview-plan.md) · Scope: [Proposal](../../PROPOSAL.md) · Required agreements: [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md).

**Evidence for the whole phase is in one file:** [P02 evidence](../../reports/P02-evidence.md)—reproduction steps, evaluation, versions/hashes, run IDs, lineage, RAM/loading measurements and limitations. This plan holds **task status, locked decisions and ownership boundaries**, without repeating result tables.

## Review fixes — 2026-10-10

The checks below were run before the later Python 3.13 and container checks linked above.

- Two review fixes: **T05**, correct the reversed confusion-matrix explanation (`neutral` → `positive` is 547, not 218) without changing scores; and **T07**, check that manifest files exist and their SHA-256 matches before registration. On a mismatch, stop, name the file and do not create a registry entry.
- Added small-fixture tests in `tests/test_registry.py`: complete files pass; missing/changed files, a directory in place of a file, an empty hash list and paths outside the artifact are rejected. Before the fix, 9 invalid cases were accepted. After the fix, **33 tests passed** across `test_evaluation.py`, `test_gitinfo.py` and `test_registry.py`; `ruff check` passed on the two changed code files.
- Checked in WSL using the existing Python **3.11.16**, with pytest cache disabled and no dependency installation. **This was not the full suite on the project's Python 3.13 environment.** No model download or new evaluation was performed because the checkout had no dataset/artifact. Earlier results and `reports/registry/` were unchanged.
- These fixtures checked the two fixes, not full model/API integration. The later [P03 checks](P03-local-backend.md) cover that integration.

---

## 1. Scope

**Required outcome:** A repeatable `prepare → evaluate → package → register` workflow. A registered model must trace back to its **code, evaluation data, upstream model revision, environment and evaluation results**. See the [system checks](P01-T03-system-structure.md#9-system-checks-and-evidence) and [versioning scope](../../PROPOSAL.md#4-mlops-scope).

**Outside P02:**

- API endpoints `/predict`, `/health` and `/ready` → P03. However, **the module that loads the model and predicts belongs to P02**; see section 4.
- Azure resources, `Dockerfile` and CI/CD → P03–P04.
- Dashboard and alerts → P05. The proposed combined failure/recovery experiment was canceled; see the [P05 scope](../../overview-plan.md#p05--local-demo-and-small-monitoring-setup-2026-10-11).
- **No training or fine-tuning**, following [Proposal §2](../../PROPOSAL.md#2-model-and-dataset).

**Sources:** Use only the links in [Proposal §2](../../PROPOSAL.md#2-model-and-dataset), not mirrors or similarly named repos.

| | Source | Licence |
|---|---|---|
| Model | `cardiffnlp/twitter-roberta-base-sentiment-latest`, revision `3216a57f…` | CC BY 4.0 |
| Dataset | `crowdflower/twitter-airline-sentiment`, **version 4** | CC BY-NC-SA 4.0 |

---

## 2. Tasks

All tasks were marked `done` in the original handoff. Evidence is in the listed sections of [P02 evidence](../../reports/P02-evidence.md).

| ID | Task | Evidence |
|---|---|---|
| T11 | Set up the environment: Python version, dependency manager and lockfile | Sections 1, 3 |
| T01 | Fetch and pin the model revision with provenance | Section 3 |
| T02 | Version the evaluation dataset | Sections 1, 2, 3 |
| T03 | Confirm the text-length limit | Section 3 |
| T04 | Shared inference module | Section 9 |
| T05 | Evaluation step and metrics | Sections 2, 4 |
| T06 | Lock the artifact layout | Section 3 |
| T07 | Lock lineage metadata and `model_version` | Sections 4, 5 |
| T08 | Set repeat-evaluation tolerance | Section 2 |
| T09 | Measure RAM and model-loading time | Sections 1, 6 |
| T10 | Choose artifact storage | Section 7 |

**Actual order, not numerical order:** `T11 → T01, T02`, then `T03`, `T04 → T09`, `T05 → T08`, and `T06 → T07 → T10`. T11 came first because the other tasks needed installed dependencies.

---

## 3. Decisions P03–P04 must follow

| Topic | Locked decision | Applies to |
|---|---|---|
| **Text-length limit** | **510 content tokens**, or 512 with special tokens; count with the tokenizer, **not characters**. See [P01-T02 §7](P01-T02-api-contract.md#7-decisions-and-original-handoff). | P03 |
| **Inference interface** | Call `SentimentClassifier.load()` once at process startup, then `predict()` per request. `ModelNotReady` → `503`; `InvalidText`/`TextTooLong` → `422`. **Do not call the tokenizer or model separately.** | P03 |
| **`model_version`** | `sentiment-<artifact_id>-<lineage digest>`. P03 reads it from the registry entry or configuration, not a hardcoded value. **A new evaluation run changes this value; update deployed configuration too.** See [report section 5](../../reports/P02-evidence.md). | P03–P04 |
| **Artifact storage** | **Include it in the image at build time**, without separate blob storage. This keeps the binding claimed by `model_version` intact; runtime replacement would make it unenforced. See [report section 7](../../reports/P02-evidence.md) for the A/B comparison. | P03–P04 |
| **Python and dependencies** | `uv` + `uv.lock` + Python `3.13`; container runtime uses `uv sync --no-default-groups`. | P03–P04 |
| **Artifact layout** | `artifacts/<artifact_id>/` contains `manifest.json`, `upstream-model-card.md` and `model/` with only loader-required files; weights use `safetensors`. | P03–P04 |
| **Repeat-evaluation tolerance** | On the same platform and `uv.lock`, **every metric and `predictions_sha256` must match bit-for-bit**. **No cross-platform tolerance is set without evidence.** | P04 (CI) |
| **Main metric** | **Macro-F1**, not accuracy, because classes are imbalanced; measured proportions are in the report. | P04 |

**P02 informs but does not own:** Model delivery into the container, CPU/RAM, and process/instance counts belong to P03–P04 under [P01-T03 §12](P01-T03-system-structure.md#12-decisions-at-the-original-handoff). [Proposal §6](../../PROPOSAL.md#6-cost-estimate) assumed 2 vCPU / 4 GiB, leaving room above P02's measurements. **If reducing size to save money, do not go below roughly 1 GiB without testing.**

---

## 4. Boundary with P03

The [Overview](../../overview-plan.md) gives Person 1 both P02 and the model-to-API integration, while Person 2 owns P03 overall.

P02 owns the **module and loader that load the model and predict**. P03 owns **endpoints, validation and responses**.

---

## 5. Limitations carried into the handoff

Read [P02 evidence, section 8](../../reports/P02-evidence.md): measurements were on macOS rather than in a container; tolerance applies only to the measured platform; evaluation used the HF snapshot rather than the packaged artifact; metrics measure agreement with this dataset's labels; results concern airline feedback; and some checks remained undone.

**Read section 8 before using any result to make a decision.**
