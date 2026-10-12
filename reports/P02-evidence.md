# P02 — Evidence for the reproducible pipeline

This report records **actual P02 runs and measurements**. Agreements and task status are in the [phase plan](../docs/plans/P02-model-pipeline.md), rather than repeated here.

**Historical results:** Later integration/container checks are in the [P03 plan](../docs/plans/P03-local-backend.md). The [failure story](../README.md#failure-story-model-unavailable-and-rollback) records separate missing-model and rollback experiments; the proposed new P05 incident drill was canceled.

| | Registered run value |
|---|---|
| `model_version` | **`sentiment-6e7ff9fbc17c-0110c462`** |
| `run_id` | `run-20261007T192531Z-d36357` |
| Code commit | `bbe375df940dc5a8b0d1bd716cf94c7ac15dcb92` |
| Evaluation on 14,640 rows | **accuracy `0.8100409836065574` · macro-F1 `0.7605863552090412`** |
| Registry entry | [`registry/sentiment-6e7ff9fbc17c-0110c462.json`](registry/sentiment-6e7ff9fbc17c-0110c462.json) |

**Machine used for all measurements in this report:** macOS 15.5 arm64 · Python 3.13.11 · `torch 2.14.1` · `transformers 5.19.0` · `numpy 2.5.3` · `tokenizers 0.23.2` · `safetensors 0.8.0` · **Not in a container or on Azure** — see section 8.

---

## 1. How to reproduce

### Four steps

```bash
uv sync --frozen                                              # prepare: environment
PYTHONPATH=src uv run python -m feedbackpulse.evaluate         # prepare: model + data, then evaluate
PYTHONPATH=src uv run python -m feedbackpulse.package_artifact # package
PYTHONPATH=src uv run python -m feedbackpulse.registry         # register
```

`evaluate` downloads the model and dataset if they are missing, so there is no separate fifth preparation command.

**`PYTHONPATH=src` is required.** The `pythonpath` setting in `pyproject.toml` applies only to pytest, not `python -m`. This matches the container's `PYTHONPATH=/app/src`.

### Latest run started from a fresh state

Removed `.venv` (778 MB), the HF cache (479 MB) and `artifacts/` (477 MiB), then reran all four steps. The rebuilt `artifact_id` was **the same: `sentiment-6e7ff9fbc17c`**, and every metric digit matched the previous run.

### Required access

Kaggle API token: `kagglehub 1.0.2` reads `KAGGLE_USERNAME` + `KAGGLE_KEY`, `KAGGLE_API_TOKEN`, `~/.kaggle/kaggle.json` or `KAGGLE_CONFIG_DIR`. Create a token at <https://www.kaggle.com/settings/api>.

**Record how to obtain the token, never its value** anywhere in the repo, following the Secrets check in [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-checks-to-keep-in-view). Searched `KGAT_…`, `KAGGLE_KEY=`, `KAGGLE_API_TOKEN=` in **every Git-history commit** and files to commit: **no matches**. `git check-ignore` confirmed `data/Tweets.csv` is excluded by `.gitignore:31`.

### Guards against silently using the wrong inputs

| Guard | What it does |
|---|---|
| `dataset.verify()` | Checks `data/Tweets.csv` SHA-256 before every run; **raises `DatasetMismatch`** on mismatch |
| `snapshot_download(revision=…)` | Downloads only the 6 pinned files from a commit SHA, not a tag |
| `register()` rejection | Five conditions in section 5 |

**Skip `tf_model.h5` and `.gitattributes`**: unused TensorFlow weights and Git metadata. This saves about 500 MB of downloads. One caveat: `snapshot_download(..., local_files_only=True)` reports an incomplete snapshot unless given the same `allow_patterns`.

---

## 2. Evaluation results

**14,640 rows · 0 skipped.** Used every row, with no sampling, splitting or filtering, so **row selection has no random seed**.

| Decision | Reason |
|---|---|
| Use the whole file, no sampling | No random seed needed; the evaluation set stays fixed for direct comparison between runs |
| No train/test split | No training or fine-tuning under [Proposal §2](../PROPOSAL.md#2-model-and-dataset), so no data needs holding out for training |
| No `airline_sentiment_confidence` filter | A cutoff would be our own choice and could make the scores look better without a justified basis |

### Baseline comparison

There was no predefined quality target in the Proposal. We therefore compare against a **class-balance baseline**: predict `negative` for every row.

| Metric | Measured | Always-`negative` baseline |
|---|---:|---:|
| Accuracy | **0.8100** | 0.6271 |
| **Macro-F1** (main metric) | **0.7606** | 0.2569 |
| Macro precision | 0.7453 | — |
| Macro recall | 0.7825 | — |

**Why macro-F1 is the main metric:** 62.7% of the evaluation set is `negative`. Accuracy alone can make a model that ignores the two smaller classes look too good: always predicting `negative` already gets 0.6271 accuracy.

### Per-class

| Label | Precision | Recall | F1 | support | Dataset share |
|---|---:|---:|---:|---:|---:|
| `negative` | 0.9153 | 0.8599 | 0.8867 | 9,178 | 62.7% |
| `neutral` | 0.6163 | 0.6137 | **0.6150** | 3,099 | 21.2% |
| `positive` | 0.7043 | 0.8739 | 0.7800 | 2,363 | 16.1% |

### Confusion matrix

Rows = true labels · columns = model predictions.

| | → negative | → neutral | → positive |
|---|---:|---:|---:|
| **negative** | **7,892** | 966 | 320 |
| **neutral** | 650 | **1,902** | 547 |
| **positive** | 80 | 218 | **2,065** |

`neutral` is the weakest class (F1 0.6150), with errors in both directions: 650 neutral rows were predicted as negative and 547 as positive. `positive` has high recall (0.8739) but lower precision (0.7043), because 547 neutral and 320 negative rows were predicted as positive. The 218 figure is positive rows predicted as neutral.

### Independent cross-checks

**Checked through a different calculation path, not just rerunning our own logic: 15/15 passed.**

| Type | Check | Result |
|---|---|---|
| **Source bytes** | Model files downloaded after clearing the cache match the SHA-256 values in section 3 | 5/5 match |
| **Data invariant** | Each label's `support` matches counts read from CSV with stdlib `csv`, **without our metric code** | 9,178 / 3,099 / 2,363 match |
| **Data invariant** | `total` matches the CSV row count | 14,640 matches |
| **Internal invariant** | Sum of confusion cells = `total`; each row sum = `support`; `trace/total` = accuracy; `correct` = trace | 4/4 match |
| **Reference result** | Recalculate macro-F1 and per-class metrics from the confusion matrix with `scikit-learn 1.9.1` | All values match within 1e-12 |

Used `scikit-learn` ephemerally (`uv run --with scikit-learn`), **without adding it to the lockfile**, because it was only a verification tool, not a runtime dependency.

### Repeat-run tolerance — measured across 7 runs

Matching the **confusion matrix or aggregate metrics is not enough**: row-level differences can cancel out. `evaluate.py` therefore computes a row-level fingerprint.

```
predictions_sha256 = sha256( "<index>\t<sentiment>\t<repr(score)>\n" for every row in order )
```

Uses the score's `repr()` to compare the **full float value**, not rounded decimals. `tests/test_evaluation.py` includes the case this fingerprint should catch: two prediction sets that differ on every row but produce the same confusion matrix.

Repeated **7 runs** on the same machine, including a fresh-state rebuild (removed `.venv` + HF cache) and a complete artifact rebuild:

| Value | Measured difference |
|---|---|
| Row-level predictions (`predictions_sha256`) | **0** — `05ddac7af1112f6c…5ad3b4` matches bit for bit |
| Accuracy, macro-F1, macro precision/recall, confusion matrix | **0** across all runs, at full float precision |
| Skipped rows | 0 in every run |
| **Runtime** | 351.4–678.9 seconds → **93% range, not an acceptance criterion** |

### Chosen tolerance — only for measured conditions

| Compared item | Requirement | Basis |
|---|---|---|
| `predictions_sha256` | **Exact match** | Zero measured difference across fresh-state and full artifact rebuilds |
| Accuracy, macro-F1, macro precision/recall | **Exact match** | Zero measured difference in 7 runs |
| Confusion matrix | **Every cell must match** | Zero measured difference in 7 runs |
| Skipped rows | **Must be 0** | Zero in every run |
| Runtime | **Not an acceptance criterion** | 93% range |

**Any difference in the first four rows needs investigation, not dismissal as noise.** This strict rule is based on deterministic inference with no sampling. A change points to a changed dependency, model file or code.

**No tolerance is set for other platforms because we have no measurements for them.** Only one machine was tested. A different CPU architecture, OS, `torch` build or BLAS backend can change floating-point addition order, shifting the last bits of logits and changing `predictions_sha256` even if every sentiment label stays the same. **This is reasoning, not a measured result.**

---

## 3. Versions and hashes

### Upstream model

| Item | Value |
|---|---|
| Repo | `cardiffnlp/twitter-roberta-base-sentiment-latest` (linked in [Proposal §2](../PROPOSAL.md#2-model-and-dataset)) |
| **Pinned revision** | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` — **commit SHA, not a movable tag** |
| Commit last updated | 2025-08-04 07:58:29 UTC |
| Licence (Hub card metadata) | `cc-by-4.0`, **matching Proposal §2** |
| Architecture | `RobertaForSequenceClassification`, 12 layers, hidden 768, vocab 50265 |

### Evaluation dataset

| Item | Value |
|---|---|
| Dataset | `crowdflower/twitter-airline-sentiment` (linked in Proposal §2) |
| **Pinned version** | **4** |
| Licence | CC BY-NC-SA 4.0 (**non-commercial + ShareAlike**) |
| File used | `data/Tweets.csv` · 3,421,431 bytes · 14,640 rows · 15 columns |
| **sha256** | `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` |

### Artifact bundle

`artifact_id` = **`sentiment-6e7ff9fbc17c`** · **477 MiB** · content-addressed:

```
sentiment-<first 12 characters of sha256(sorted "filename:hash" entries for files in model/)>
```

Only files in `model/` contribute to the hash, so `manifest.json` can record its own artifact ID without a circular dependency. **The same inputs always give the same ID**, confirmed in run 6 after deleting `artifacts/` and rebuilding the whole bundle.

```text
artifacts/sentiment-6e7ff9fbc17c/
├── manifest.json             lineage, every file's hash, metadata
├── upstream-model-card.md    upstream model card (CC BY 4.0 attribution); outside model/ because the loader does not read it
└── model/                    only files the loader reads
```

| File | bytes | sha256 | HF source | Artifact bundle |
|---|---:|---|:---:|:---:|
| `config.json` | 929 | `d2fba19997da698157196ba16f5fcb30a97a7551cef6845a0f3d743ee19c6129` | ✓ | ✓ `model/` |
| `vocab.json` | 898,822 | `06b4d46c8e752d410213d9548eb27a54db70fda0319b6271fb8d59dead5e1cab` | ✓ | ✓ `model/` |
| `merges.txt` | 456,318 | `1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5` | ✓ | ✓ `model/` |
| `special_tokens_map.json` | 239 | `378eb3bf733eb16e65792d7e3fda5b8a4631387ca04d2015199c4d4f22ae554d` | ✓ | ✓ `model/` |
| model card · `README.md` ↔ `upstream-model-card.md` | 4,328 | `05ad85143ed60f0abe631ab935485db046c24710d9bec50829b017cfc1e12bf7` | ✓ | ✓ root |
| `pytorch_model.bin` | 501,045,531 | `4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae` | ✓ | — converted |
| `model.safetensors` | 498,615,868 | `deece7c9f6d59c96ac2a9ef285a6b0f20f9bea463b90242a0578bdfae8010718` | — | ✓ `model/` |
| `manifest.json` | — | `db8ceb69c7f6b291e1e5775c4c3c94ab94c9b09c8603aa4929d496993e1990d0` | — | ✓ root |

The first five rows have **the same hashes on both sides**: byte-for-byte copies that can be traced directly from artifact to source. `pytorch_model.bin` is excluded because it was converted to safetensors (next section).

`labels` and `max_content_tokens` in `manifest.json` are **read from the loader after loading the built bundle**, not recalculated by the packaging script. The manifest therefore reports the loader's own values, and **the build fails if the bundle cannot load**. **No storage location/URL is recorded**, keeping this independent of the decision in section 7.

### Environment

| Item | Value |
|---|---|
| `uv.lock` sha256 | `897a91df2d1fbc88d6a5fcb2fd4dc37c4affdd40be55b7ea293d88385797bb96` |
| Python | `3.13.11` |
| Packages affecting inference | `torch 2.14.1` · `transformers 5.19.0` · `numpy 2.5.3` · `tokenizers 0.23.2` |

### Text-length limit — measured result

The tokenizer adds **2 tokens** to each input: `<s>` before and `</s>` after (`tok.num_special_tokens_to_add(pair=False) == 2`).

| Total tokens (including special tokens) | Forward result |
|---:|---|
| 510, 511 | Pass |
| **512** | **Pass — highest usable length** |
| 513, 514 | Fails: `RuntimeError: index 514 is out of bounds for dimension 1 with size 514` |

Confirmed again with **real text through the tokenizer**, not hand-built `input_ids`: 1,527 characters → 512 total / 510 content → pass; 1,530 characters → 513 total / 511 content → fail.

Result: maximum sequence length **512 tokens**, including **2 special tokens**, leaving **510 content tokens**, counted by the pinned revision's tokenizer, **not by character count**.

**Why `tokenizer.model_max_length` cannot be used directly:** the model repo has **no `tokenizer_config.json`**, so it returns sentinel `1000000000000000019884624838656`, not a real limit. The supporting value is `max_position_embeddings = 514` in `config.json` (RoBERTa uses 512 + 2 reserved positions), together with the checks above.

**Fixed the silent gap:** `load()` sets `tokenizer.model_max_length` to the derived value (512). Previously, comparing 603 tokens against the sentinel returned `False`, **missing the over-limit input**. It then reached the model and caused `500` instead of `422`.

The value still comes only from `config.json`. **No `tokenizer_config.json` was added**, which would create a second source of truth. Instead, `manifest.json` records `max_content_tokens: 510`, covered by a test. **Remaining limit:** loading `artifacts/<id>/model` directly with `AutoTokenizer`, outside our module, still returns the sentinel.

**The tokenizer does not truncate unless asked.** `tok(text)` returns 513 without truncation; `tok(text, truncation=True, max_length=512)` returns 512 by cutting the input. `truncation=True` violates [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-and-response), so **our code does not use `truncation=True`**: it counts and rejects.

**Characters cannot replace tokens.** The measured character/token ratio varies from 0.52–3.98 by language (Thai can produce more tokens than characters). A character limit based on English could let inputs over 512 tokens through.

### Label mapping — read directly from this revision's `config.json`

| index | Label in `config.json` | `airline_sentiment` in dataset |
|---|---|---|
| 0 | `negative` | `negative` |
| 1 | `neutral` | `neutral` |
| 2 | `positive` | `positive` |

**All three sources use matching label names, so no conversion table is needed.** The code still reads labels from `config.json` at runtime rather than hardcoding index order, which could change with a different revision. Covered by `test_labels_come_from_the_model_config`.

**`score` definition:** apply `softmax(logits)` and take the `argmax` class's value. All class probabilities sum to `1.000000` in every example, keeping scores within 0–1 as required by [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-and-response).

**Handwritten reference input**, used to check the mechanism across steps, **not an evaluation result**: `"My flight was delayed and nobody helped me."` → `negative`, score `0.943575` (probs 0.9436 / 0.0521 / 0.0044). Reused in section 5 (trace-back layer 8) and section 9 (interface example).

### Convert weights to safetensors

The upstream repo provides `pytorch_model.bin`, not `model.safetensors`. **We chose to convert it** for the remaining reason below:

| Reason | Status |
|---|---|
| **No unpickling at load time** | Applies: `pytorch_model.bin` uses pickle, which can execute code during deserialization. The original [Proposal §5](../PROPOSAL.md#5-planned-failure) planned to make the artifact unusable, so safe loading of a modified file was part of the decision. That new P05 experiment was later canceled; this is not evidence that it was performed |
| **No extra dependency** | Applies: `safetensors 0.8.0` is already a transitive dependency of `transformers` |
| ~~Faster loading~~ | **Withdrawn**: measured time/RAM did not differ; see section 6 |

**This bundle is not an exact copy of the source.** The source has **204 tensors**; safetensors contains **201**. Three were omitted:

- `roberta.embeddings.position_ids` — a buffer this `transformers` version no longer saves.
- `roberta.pooler.dense.weight` and `.bias` — the sequence-classification head does not use the pooler. This matches `transformers` reporting them as `UNEXPECTED` when loading upstream weights; it is an observation, not a failure. All weights used for prediction loaded.

All three are recorded in `manifest.json`. Actual comparisons checked that predictions were unaffected:

| Check | Result |
|---|---|
| `state_dict` from safetensors vs `.bin` | All 201 keys match; **every tensor is bit-identical** |
| Logits on 300 real evaluation rows | Maximum difference **0.000e+00** |
| Different sentiment predictions | **0 / 300** |

### Load without files outside the bundle

Set `HF_HOME` to an empty directory, with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, then load `artifacts/sentiment-6e7ff9fbc17c/model`:

| Check | Result |
|---|---|
| `HF_HOME` really empty during the run | Directory listing confirmed no files |
| `SentimentClassifier.load()` | Succeeded **without cache or network access** |
| `labels` | `('negative', 'neutral', 'positive')` |
| `max_content_tokens` | **510** |
| Predict the reference input | `negative` `0.943575`, matching the recorded value |

---

## 4. Run ID

| Recorded item | Registered run value | Identifies |
|---|---|---|
| `run_id` | `run-20261007T192531Z-d36357` | **That run**; format `run-<UTC timestamp>-<3 random bytes>` |
| `finished_utc` | `2026-10-07T19:38:39+00:00` | Completion time |
| `seconds` | `643.5` | Runtime |
| `code.commit` | `bbe375df940dc5a8b0d1bd716cf94c7ac15dcb92` · `dirty: false` · `uncommitted: []` | **Code version used** |
| `predictions_sha256` | `05ddac7af1112f6c12267e820832a678b19155bd61fd55a67150e50b7e5ad3b4` | **Output**, not the run |
| Result-copy SHA-256 | `45338f35ce4ec5024a488ca7e3353fc8f4d7d1ac3f2e295ada429b4bbef324cb` | **This run's result file**, stored beside the registry entry |

**Why `run_id` is separate from `predictions_sha256`:** this deterministic pipeline gives the same prediction hash for the same inputs, as confirmed in section 2. That hash identifies the **output**, not **a run**, so it cannot replace a run ID. The random suffix distinguishes runs that start in the same second.

`run_id` is saved in the result (`run.run_id`) and registry lineage (`evaluation.run_id`). It also **names the evaluation-result copy** stored beside the entry; see section 5.

---

## 5. Lineage

### Registry-entry structure

`reports/registry/<model_version>.json` stores 6 sections:

| Section | Records |
|---|---|
| `artifact` | `artifact_id`, `manifest.json` hash and every bundled file's hash |
| `source_model` | Repo, revision, licence and **source hashes for every file, including `pytorch_model.bin`** |
| `evaluation_data` | Version-4 handle, SHA-256 and row count |
| `code` | commit |
| `environment` | Python, **`uv.lock` hash** and inference-package versions |
| `evaluation` | Result-copy name/hash, `run_id`, runtime, accuracy and macro-F1 |

**No storage location/URL is recorded**, keeping this independent of section 7's decision.

### `model_version` scheme

```
sentiment-6e7ff9fbc17c-0110c462
│         │             │
│         │             8-character lineage digest: SHA-256 of the full lineage record
│         │             (artifact, upstream model, dataset, code commit, environment, evaluation result)
│         artifact_id — content-addressed from files in model/
model family — readable in logs and response bodies
```

| Decision | Reason |
|---|---|
| **3 parts, not one hash** | The middle `artifact_id` makes it easy to see whether two releases use the same weights, useful during rollback. One hash hides that distinction |
| **Content-addressed, not a counter** | No central service is needed to issue the next number, especially before choosing artifact storage |
| **Digest covers code/environment, not only weights** | `predict()` also depends on our code. If preprocessing changes but the version does not, the version becomes misleading |
| **31 characters long** | Fits JSON responses/logs without being unwieldy |

**`model_version` stays stable for the same artifact and inputs, but changes after a new evaluation run.** `run_finished_utc` and `result_sha256` are part of the hashed payload, and the result file contains a timestamp. Rerunning `evaluate` therefore produces a new digest even if model, dataset, code and lockfile are unchanged.

**Observed result:** three consecutive runs produced `…-c9386c0e`, `…-850de906`, then `…-0110c462`, all with the same `artifact_id`, `sentiment-6e7ff9fbc17c`. On 2026-10-07 we chose to keep this behavior. P03–P04 requirements are in [phase plan §3](../docs/plans/P02-model-pipeline.md).

### The registry rejects unsupported claims

`register()` raises `CannotRegister` rather than issuing a version it cannot support. It rejects uncommitted code/evaluation, changes to **prediction-affecting files** (`gitinfo.BEHAVIOUR_PATHS`) since evaluation, and model-revision/dataset mismatches.

**This guard has actually fired.** Registration was rejected after `inference.py`/`evaluate.py` changed since the previous evaluation, requiring a new evaluation before registration.

### Trace-back from one `model_version` — 36/36
 
Started with only `sentiment-6e7ff9fbc17c-0110c462`, then traced each layer, **recomputing hashes from real files on disk rather than comparing saved values with themselves**.

| Layer | Check | Result |
|---|---|---|
| 1 | **Recompute the digest from stored lineage and get the same version**; entry `model_version` matches its filename | 2/2 |
| 2 | `manifest.json` and 6 bundled-file hashes match; **recomputing `artifact_id` from `model/` files gives the same ID** | 8/8 |
| 3 | Revision matches the code pin; 6 source-file hashes match | 7/7 |
| 4 | Handle matches the code pin; `data/Tweets.csv` hash matches | 2/2 |
| 5 | Commit exists, is in `HEAD` history, and prediction-affecting files have not changed since it | 3/3 |
| 6 | `uv.lock` hash matches | 1/1 |
| 7 | This entry's evaluation copy exists and its hash matches; `run_id`, accuracy/macro-F1 match lineage; copy contains `predictions_sha256`; evaluation used the lineage's commit, revision and dataset | 8/8 |
| 8 | Artifact loads/predicts (`negative` 0.943575), returns this `model_version`, and has `labels`/`max_content_tokens` matching the manifest | 4/4 |

**Each entry keeps its own evaluation-result copy** beside it as `<run_id>-evaluation.json`, instead of pointing to `reports/P02-T05-evaluation-result.json`, which is overwritten on every run.

**Two bugs found and fixed:** both let registry entries claim lineage that could not be verified:

1. The first entry pointed to a **shared result path** overwritten each run, so **rerunning evaluation immediately broke traceability**. Fixed by keeping a copy beside the entry, with a test that overwrites the shared file and checks that the entry still resolves.
2. That fix named the copy from `model_version`, requiring **`result_file` to be added to lineage after hashing**. The saved entry then **could not reproduce its own version**. The first check missed this because it compared against `None`, which was always true. Fixed by naming the copy from the already-available `run_id`, plus a **test that recomputes the version from stored lineage**. Layer 1 above is now covered by a CI regression test.

All entries created by the faulty code were deleted because they could not be recovered and had never been deployed. Git history keeps their record.

### Lineage mismatch and why it was accepted

`manifest.json` records `built_with.code_commit = 3b8e584`, while current lineage records `code.commit = bbe375d`. The artifact was packaged once at `3b8e584`, then evaluated/registered twice more (`f1e7f0f`, then `bbe375d`) without rebuilding. Five prediction-affecting files changed between these commits, **only in commit `bbe375d`** (`3b8e584`→`f1e7f0f` did not touch them). Changes were comments/docstrings only, confirmed by identical AST nodes before that commit. Every bundled-file hash still matches lineage (layer 2).

**However, `package_artifact.py` and `registry.py` are outside `BEHAVIOUR_PATHS`**, so the guard would not catch packaging-logic changes after a build. This run was verified manually through AST/hash checks, not that automatic guard.

---

## 6. Startup time and memory

These measurements inform startup and memory decisions in [P01-T03 §5](../docs/plans/P01-T03-system-structure.md#5-reasons-and-trade-offs). **Two sessions on different days gave roughly twofold timing differences, while peak RSS was consistent. The cause is unknown; CPU load was not recorded. Timing here is not an acceptance criterion.**

**Method:** multiple runs, each in a new process, using `resource.getrusage().ru_maxrss` at three points: after framework import, weights loading and 50 predictions. There are **two easy-to-miss measurement traps**:

- **`ru_maxrss` units differ by platform:** bytes on macOS, **kilobytes on Linux**. Missing the conversion creates a **1024-fold error** in values used for memory limits, while still looking like an ordinary number.
- **Run `import torch`/`transformers` where `inference.py` does**, inside `load()`/`predict()`, not at module level. Importing earlier makes the "import framework" phase appear to take ~0.004 seconds; the time is instead mixed into "load weights".

### Main results

| | Highest measured value (both sessions) |
|---|---:|
| After loading weights | ~341 MiB |
| After the first short prediction | ~706 MiB |
| **After 50 predictions at the limit (510 tokens)** | **783.4 MiB** |

**The first prediction adds about 365 MiB**, more than loading the weights, because torch allocates forward-pass workspace then. **Sizing only from the ~341 MiB "loaded" value can kill the container on its first request. Use 783 MiB for sizing, not 341 MiB.** Memory was repeatable across the sessions (748 vs 783.4), unlike timing. **No leak signal was observed**: values at 25 and 50 predictions were the same.

**Per-prediction time:** limit-length inputs were **3.6–4.2 times** slower than short inputs, depending on the session. P03–P04 need long inputs in p95 testing, not only short ones.

**Startup time:** 1.36–2.95 seconds depending on the session, roughly a twofold difference. **Not an acceptance criterion**; P03–P04 must measure it in the container.

**Safetensors vs `pytorch_model.bin`:** no measured time/RAM difference; details in section 3.

**Evaluation runtime:** 351–679 seconds for 14,640 rows, one input at a time. **This is not API latency.** The p95 target is P03–P04 work.

---

## 7. Model-artifact storage

**Decision: put the artifact bundle in the container image at build time**, not separate blob storage. Decided by Person 1 under the authority given on 2026-10-07.

### Use only supported decision criteria

| Criterion | Basis | Evidence type |
|---|---|---|
| Artifact size: 477 MiB | Section 3 | **Measured** |
| Startup: 1.42–2.93 s with local files | Section 6 | **Measured**, with roughly twofold variation between sessions |
| Whether startup includes a download step | Design behavior | **Structural** |
| How many items rollback must revert | Design behavior | **Structural** |
| Which option fits the budget | [Proposal §6](../PROPOSAL.md#6-cost-estimate) already assumes "one Basic container registry, 5 GB of blob storage" | **Document assumption** |

**Deliberately excluded: download time for 477 MiB from the real service.** It could not be measured locally, and guessing would conflict with [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-checks-to-keep-in-view), which says not to invent measurements.

### Compare two options

**A** = `COPY` the artifact into the image at build time, then push to a container registry. **B** = store it in Blob Storage and download 477 MiB whenever the container starts.

| Criterion | A — inside the image (chosen) | B — download at startup |
|---|---|---|
| **When bytes move** | With the image pull | Image pull **plus** a separate artifact download |
| **Cold start** | Artifact is already in the image; image grows by 477 MiB | **Every startup** adds a 477 MiB download after pulling the image. [Proposal §3](../PROPOSAL.md#3-serving-pattern-and-requirements) says the service **scales to zero when idle**, so cold starts may be frequent |
| **Rollback** | **Revert one item**: image revision carries code + artifact together | **Revert two items**: image revision and blob pointer, which can get out of sync |
| **Budget (Proposal §6)** | Fits the assumed registry; no extra egress beyond image pulls | Fits the assumed 5 GB blob storage, but **adds egress on every cold start**, using the $3.55 reserved for "requests, network, operations" |
| **Model-unavailability testing** | Modify a file in the running container or deploy an intentionally broken image | **Easier**: delete/rename the blob and readiness should fail |
| **Change the model** | Rebuild + redeploy | Point configuration to a new blob |

### Why option A was chosen

**Keep the binding claimed by `model_version` real — the main reason.** The digest covers code commit + environment + artifact, because `predict()` depends on our code as well as weights. A runtime-swappable blob would let `model_version` claim a binding that nothing enforces: someone could change the blob while the API still returns the old version. Other reasons/trade-offs are in the comparison above. **Testing limitation:** The proposed cloud experiment would have used a changed container file or a broken image, rather than deleting a blob. That experiment was canceled; it is not a recorded result or an instruction to change the running App.

The chosen option supports the real artifact, as checked in section 3: ordinary files with no symlinks can be copied into the image; offline loading works; core code has no cloud calls; and 477 MiB fits the Basic container registry assumed in Proposal §6.

### Formula for P04 — not a guessed measurement

Extra artifact cold-start time = **477 MiB ÷ measured throughput**.

This is **arithmetic from the measured size**, not a claim about unmeasured Azure throughput. **P04 should measure throughput and substitute it.**

Locally, reading 477 MiB from a warm page cache took **0.10–0.15 seconds**. It was used only as a **lower bound**, based on local reads being faster than network transfer. Most extra time would therefore come from the network. **This is not a download-time estimate.**

---

## 8. Limitations carried with the work

**All measurements came from macOS 15.5 arm64, not a container or Azure.** Main limitations:

- `safetensors` uses **mmap**, so loaded peak RSS (341 MiB) is **below file size (476 MiB)** because untouched pages are not counted. **Linux may count mapped pages toward the cgroup limit**, making real container usage higher. **Not yet tested.**
- CPU architecture differs: arm64 vs the x86-64 commonly used on Azure, so inference timings are not directly comparable.
- No container memory limit was imposed, so the OOM-kill threshold is unknown.
- **Remeasure these values before choosing container size.**

**Timings were not repeatable between measurement sessions.** Two days on the same machine gave roughly twofold differences across timings, while peak RSS was consistent. **Cause unknown**; see section 6. **Timing values cannot be pass/fail criteria or cold-start estimates.** Compare alternatives within the same measurement session.

**Tolerance applies only to the measured platform.** If CI runs on Linux x86-64, **do not immediately use exact bit equality as a gate**. See the reasoning at the end of section 2's tolerance discussion.

**Fresh state still had limits:** `.venv`, HF cache and `artifacts/` were rebuilt, but **the Python interpreter stayed the same** (`3.13.11` from Anaconda), as did `data/Tweets.csv`. Dataset `verify()` checks SHA-256 every run. Different Python patch versions were not tested; Python is pinned only to the minor version.

**Evaluation uses the HF snapshot, not the deployable artifact.** `evaluate.py` reads HF-cache files. Results apply to the artifact **through equal logits on 300 rows, not because the files are identical** (section 3). **Unimplemented proposal:** evaluate the artifact directly to close this gap, but that would make evaluation depend on packaging, reversing the dependency order.

**Metrics measure agreement with this dataset's labels, not the model's maximum capability.** Minimum `airline_sentiment_confidence` is 0.335; **4,195 rows (28.7%) are below 1.0**, and **3,872 (26.4%) below 0.7**. Crowdsourced annotators did not agree on every row, so some errors may come from labels rather than the model. No filtering was applied to avoid improving scores through an arbitrary cutoff.

**Results describe airline feedback only**, as Proposal §2 says. These are short airline tweets, at most 186 characters, so they **never reach the 510-token limit**. Boundary tests need constructed text; P03 cannot test the API boundary using this dataset alone.

**The tolerance has not been deliberately challenged**, for example by changing `torch` to see whether it detects a difference. That experiment is closer to P05 regression work.

**No concurrency measurement:** one request at a time in one process. The p95 target at 2 concurrent requests belongs to P03–P04.

**No lineage trace-back script is stored in the repo.** The 36/36 checks in section 5 used a temporary script that was not kept. Layer 1 has a regression test in `tests/test_registry.py`; the others do not. If P04 needs a CI gate, it must implement one using section 5's checklist.

**No multi-version release process yet.** `registry.main()` registers the only artifact present and rejects multiple bundles instead of guessing. Multi-version handling is needed for **P04** rollback but was not designed yet; a `ponytail:` marker records this.

**The registry is files in Git, not a service.** This was chosen because Git files can record the required model lineage. If a service with its own registry is selected later, these entries remain reference records. **Migration vs maintaining both has not been assessed.**

**Artifact storage was chosen without Azure experiments.** The machine had no `az` CLI or credentials; resource creation belongs to P04. The decision used design properties and Proposal budget assumptions, **not cloud measurements**.

**Azure Container Apps image-layer caching during cold starts is unknown.** Strong caching would favor A more; no caching would bring the options closer. **P04 must check** and revisit if this assumption is materially wrong. **No third option** (Azure ML model registry, volume mount) was compared because it adds services outside Proposal §6's budget assumptions.

**Dataset licence limit:** CC BY-NC-SA 4.0 is non-commercial + ShareAlike. It can be used for coursework evaluation with attribution. ShareAlike implications for publishing sample texts were not assessed, so **not a single real dataset text is copied into `reports/`**. Results contain only counts/version metadata, no tokens.

**All results are tied to revision `3216a57f…` and dataset version 4.** Changing either requires rerunning checks because `max_position_embeddings`, tokenizer, label mapping and metrics may change.

---

## 9. Model-to-API interface — module-side verification only

The [Overview](../overview-plan.md) assigns Person 1 both P02 and the model-to-API interface. **The module side is verified; endpoints did not yet exist because they belong to P03.**

### Delivered interface

```python
from feedbackpulse.inference import (
    SentimentClassifier, Prediction,
    ModelNotReady, InvalidText, TextTooLong,
)
from feedbackpulse.model_files import ensure_model_files

clf = SentimentClassifier.load(ensure_model_files(), model_version="<read from registry entry>")  # once at process startup
result = clf.predict("My flight was delayed and nobody helped me.")   # per request
# -> Prediction(sentiment='negative', score=0.943575, model_version='sentiment-6e7ff9fbc17c-0110c462')
```

| Check | Result |
|---|---|
| `Prediction` has the 3 fields in [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-and-response) | `sentiment: str`, `score: float`, `model_version: str` — no extra fields |
| Exception mapping covers the 3 statuses in [P01-T02 §4](../docs/plans/P01-T02-api-contract.md#4-validation-and-error-handling) | `ModelNotReady` ← `RuntimeError` → `503` · `TextTooLong` ⊂ `InvalidText` ← `ValueError` → `422` |
| Load once in `load()`, per [P01-T03 §3](../docs/plans/P01-T03-system-structure.md#3-serving--receive-feedback-and-predict) | No `from_pretrained` in `predict()`; `__init__` receives an already-loaded model |
| Core does not read env, call the network or use cloud services | No `os.environ`, `getenv`, `requests`, `azure`, `boto` in `inference.py` |
| **One tokenization/prediction implementation in `src/`** | `AutoTokenizer`, `softmax`, `argmax` appear only in `inference.py` |
| `ruff check` · `ruff format --check` · `pytest` | All pass; **35 tests** |

**`package_artifact.py` also calls `from_pretrained`**, but only to **convert weights to safetensors** (`save_model` + `state_dict`). No tokenizer, softmax/argmax or prediction. It then loads the built bundle through `SentimentClassifier.load()` to read `labels`/`max_content_tokens`, so this is not a second inference path.

**`TextTooLong` inherits from `InvalidText`**, so catching `InvalidText` can return `422` for both. `TextTooLong` provides `.token_count` and `.limit` for the error message.

### Behavior covered by regression tests

| Behavior | Test |
|---|---|
| **Check length before calling the model**: 511 tokens raise `TextTooLong`, never reaching a forward pass that could raise `RuntimeError` and become `500` | `test_text_one_token_over_the_limit_is_rejected_not_truncated` |
| **No truncation**, as required by P01-T02 §3 | Same test: exception, not prediction from shortened text |
| Read labels from config, not hardcoded index order | `test_labels_come_from_the_model_config` |
| Limit matches the measured value (510) | `test_token_limit_matches_the_recorded_value` |
| Tokenizer does not report the sentinel | `test_tokenizer_reports_a_usable_limit_rather_than_the_sentinel` |
| Return the supplied `model_version`, not a self-generated value | `test_prediction_matches_the_api_contract` |
| Distinguishable model-load error | `test_load_failure_is_distinguishable` |
| **Version recomputed from stored lineage matches the entry name** | `tests/test_registry.py` |
| Fingerprint catches different predictions with the same confusion matrix | `tests/test_evaluation.py` |

### One-time checks without regression tests

| Behavior | Evidence | Gap |
|---|---|---|
| **Load once**: weights stay in the instance, not reloaded for each `predict()` | True by structure: `predict()` does not call `from_pretrained` | No assertion prevents a future change from loading inside `predict()` |
| **Core does not read env/use the network; one tokenization path** | `grep` in `src/` | A point-in-time check, **not protection against future additions**. Enforcing this needs a test/lint rule scanning `src/`, not yet present |

### Unverified items and ownership

**Only half of "evaluation and API call the same function" was verified.** Evaluation does: `evaluate.py` calls `SentimentClassifier.predict()` per input without its own tokenization. **The API had no endpoint yet**, so **P03 must check that side**.

**`make portability-audit` is not a P02 gate.** [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-checks-to-keep-in-view) asks for core/configuration/**cloud-adapter** separation once those parts exist. **P02 has no cloud adapter**, so that gate belongs to **P03–P04**. P02 owns core (`inference.py`) vs configuration (`model_files.py`) separation, checked above.

**No check yet that the deployed version matches the loaded artifact.** `load()` simply accepts a supplied `model_version`; a wrong value from P03 would be returned by the API without detection.

The registry entry and `manifest.json` provide every file hash, but **calling verification at startup belongs to P03**, per P01-T02 §4. Defining what makes an artifact "unusable" belongs to **P05**. P02 did not prebuild that function without a caller, since its call site/error semantics would have been guesses.
