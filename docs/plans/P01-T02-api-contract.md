# P01-T02 — API Contract

Original agreement: 2026-10-05; text-length decision added on 2026-10-07.

Main plan: [Overview plan](../../overview-plan.md) · Project scope: [Proposal](../../PROPOSAL.md)

This is the P01 API contract. Implementation checks are in the [P03 plan](P03-local-backend.md) and [P03 evidence](../../reports/P03-evidence.md). The localhost demo calls this API without changing its contract.

## 1. Status and scope

- **P01-T02 status:** `done` for the agreement only. The open text-length limit was confirmed in P02-T03 on 2026-10-07; see section 7.
- **Implementation and testing:** Not implemented or tested at this planning stage.
- **Scope:** Accept one English feedback message and return a sentiment that the calling system can use to group messages for human review.
- **Out of scope:** Batch processing, CSV uploads, frontend, user registration, customer replies and urgency classification.

Changes to API behavior must also update this contract and its tests.

## 2. Agreed endpoints

| Method and path | Purpose | Expected result |
|---|---|---|
| `POST /predict` | Accept one message and return a prediction | `200` on success; errors follow section 4 |
| `GET /health` | Check whether the app responds | `200` when it responds; this does not prove the model is ready |
| `GET /ready` | Check whether the model loaded and can serve requests | `200` when ready; `503` otherwise |

If the app is running but the model cannot load, `/health` may pass while `/ready` must fail. These checks distinguish a running API from a model that is ready to serve requests.

## 3. Request and response

### Request

Send JSON to `POST /predict` with `Content-Type: application/json` and the service token described in section 5:

```json
{
  "text": "My flight was delayed and nobody helped me."
}
```

Rules for `text`:

- The field is required and must be a string, not a number, `null` or a list.
- It must not be empty or contain only whitespace.
- Accept one message at a time, not a file.
- Reject messages over the limit; do not silently cut off the end.
- The limit is **510 content tokens** (512 including 2 special tokens), counted by the tokenizer for the deployed model revision. **Do not count characters instead.** See section 7.

### Success response

Return HTTP `200` with JSON:

```json
{
  "sentiment": "negative",
  "score": 0.96,
  "model_version": "sentiment-v1"
}
```

**This is an example, not a measured result.** The score and version name only show the response format.

| Field | Meaning |
|---|---|
| `sentiment` | The model's chosen class: `negative`, `neutral` or `positive` |
| `score` | Score for that class, from 0–1; it is not a guarantee of correctness at that percentage |
| `model_version` | The version of the model artifact actually in use, traceable to its lineage; not a leftover example value |

Do not add suggested customer replies, urgency labels or generated explanations.

## 4. Validation and error handling

| Situation | HTTP status and behavior |
|---|---|
| Valid input and successful prediction | `200` with sentiment |
| Malformed JSON | `400`: the request cannot be read |
| Missing `text`, wrong type or empty text | `422`: input does not meet the rules |
| Text exceeds the supported limit | `422`: ask for shorter text; do not truncate and predict |
| Missing or incorrect token | `401`; do not call the model |
| Model is not ready or failed to load | `503`; do not make up a prediction |
| Unexpected error | `500`; do not expose internal details |

Errors handled by the app use one format, for example:

```json
{
  "error": {
    "code": "MODEL_NOT_READY",
    "message": "The model is not ready. Please try again later."
  }
}
```

`error.code` lets programs distinguish error types. `error.message` explains the problem to callers without exposing secrets or a stack trace.

HTTP status codes follow [HTTP Semantics — RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes). A `401` response must also include `WWW-Authenticate: Bearer`. The JSON format above is the app's contract; cloud errors raised before a request reaches the app may look different.

## 5. Access control and data we do not keep

`/predict` requires a service token in this header:

```http
Authorization: Bearer <service-token>
```

- Use HTTPS in the cloud.
- Store the token as a secret, not in Git or logs.
- Do not add user registration or a login page.
- Process feedback and return the result; do not store feedback in a database.
- Do not log full feedback text.

## 6. Implementation checklist

These are the **original acceptance criteria, not a current to-do list**. The boxes are left as requirements rather than test results; see [P03's checklist results](../../reports/P03-evidence.md#1-automated-test-results-checklist-verification) and [later P03 review](P03-local-backend.md) for what was verified.

- [ ] A valid request with a token returns `200` and all 3 response fields.
- [ ] `sentiment` is one of the 3 allowed classes and `score` is between 0–1.
- [ ] `model_version` matches the loaded artifact and can be traced to its lineage.
- [ ] Malformed JSON returns `400`.
- [ ] Missing `text`, `null`, a number, list, empty string or whitespace-only input returns `422`.
- [ ] **510 content tokens** are accepted; **511 content tokens** return `422` without truncation and prediction.
- [ ] A missing or incorrect token returns `401` with the authentication header, without calling the model.
- [ ] `/ready` returns `200` when the model is ready and `503` otherwise.
- [ ] When the app responds but the model is unavailable, `/health` remains separate from `/ready`, and `/predict` does not return a fake sentiment.
- [ ] Unexpected errors return `500` without exposing secrets or a stack trace.
- [ ] App-generated errors follow the agreed format; logs contain neither service tokens nor full feedback text.

The P05 traffic alert checks request volume, not model failure. See the [P05 scope](../../overview-plan.md#p05--local-demo-and-small-monitoring-setup-2026-10-11); no combined cloud failure-to-alert-to-recovery experiment was run.

## 7. Decisions and original handoff

### Text-length limit — locked on 2026-10-07

Confirmed using the tokenizer and model revision `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` used in P02. The experiment and evidence are in [P02 evidence, section 3](../../reports/P02-evidence.md).

| Item | Locked value |
|---|---|
| **Maximum content length** | **510 tokens** |
| **Included special tokens** | **2** — `<s>` at the start and `</s>` at the end |
| **Maximum total sequence length** | **512 tokens** |
| **Counting method** | Count **tokens** with the revision's tokenizer, **not characters** |

Why 512: `config.json` sets `max_position_embeddings = 514`, and RoBERTa reserves 2 positions. A total length of 512 passed the experiment; 513 failed with `RuntimeError: index 514 is out of bounds`.

**Do not substitute a character count.** The measured character-to-token ratio ranged from 0.52 (Thai) to 3.98 (one repeated letter). A character limit could let inputs over 512 tokens through.

**Count and reject before calling the model.** Otherwise, overlength input causes a `RuntimeError` and becomes a `500`, instead of the `422` required in section 4. **Do not use `truncation=True`**, because section 3 rules out silent truncation.

### What remained at handoff

At the P01 handoff, this contract was a design, not a tested implementation. Section 6's boundary checks were implemented in [P03](P03-local-backend.md). [P01-T03](P01-T03-system-structure.md) records the system structure.
