# FeedbackPulse — Automation & Verification Scripts

This folder contains smoke-test, rollback-verification and cleanup scripts for **Azure Container Apps**.

**Before running commands:** the revision names and recorded examples below are
from the team's East Asia deployment, not the later Malaysia West deployment.
Some scripts still have the old target defaults. Check the subscription, resource
group, App, endpoint, revision and matching token before use; do not assume that
every command selects the latest deployment automatically.

**Rollback changes live traffic, including with `SIMULATE=1`.** It is not an
offline simulation. Use the saved P04 results to inspect past behavior without
changing traffic. Confirm the target and obtain the operator's approval before
running a new rollback or cleanup.

---

## Script index

| Script | Purpose | Command | Evidence output |
|---|---|---|---|
| [`cloud_check.py`](cloud_check.py) | Check 12 API-contract cases on the public URL; measure cold-start time and error rate separately | `make smoke-test` | `reports/P04-cloud-check.json` |
| [`verify_rollback.py`](verify_rollback.py) | Route 100% traffic to an earlier revision, then check the endpoints | `make verify-rollback [SIMULATE=1]` | `reports/P04-rollback-evidence.json` |
| [`teardown.sh`](teardown.sh) | Delete only the configured App and its revisions, with dry-run and confirmation guards | `make teardown` or `make teardown-dry-run` | Console / dry-run logs |

---

## 1. How rollback works (Native Revision Management)

**Azure Container Apps** uses `activeRevisionsMode: Multiple` in the IaC file (`cloudlayer/containerapp.template.yaml`):

- **It does not delete/recreate the Container App.** The public FQDN stays the same (`https://feedbackpulse-api...azurecontainerapps.io`).
- **Blue/green traffic cutover (100 / 0):** each deployed version becomes an immutable **revision**.
  - `feedbackpulse-api--2zaws5o`: **[PREVIOUS STABLE]** previous stable version.
  - `feedbackpulse-api--rev2`: **[NEW / LATEST]** newly released version.
- If the new version has a problem, ingress can route 100% of traffic back to the old version. The recorded cutover took **~15 seconds**, without rebuilding the Docker image or reverting a Git commit.

---

## 2. Rollback testing guide

There are **3 ways** to run the check or demonstrate it:

### Method 1: one-command automated rollback check

This simulates the sequence: new version receives 100% traffic $\rightarrow$ rollback to the old version at 100% $\rightarrow$ wait for cold-start readiness $\rightarrow$ test endpoints.

```bash
make verify-rollback SIMULATE=1
```
Or:
```bash
python scripts/verify_rollback.py --simulate-new-first
```

> [!NOTE]
> **Why `SIMULATE=1`, not `make verify-rollback --simulate-new-first`? What does `1` mean?**
>
> 1. **Why not pass `--simulate-new-first` straight to Make?**
>    - **GNU Make** reads `--` arguments as its own options, such as `make --help` or `make --dry-run`.
>    - `make verify-rollback --simulate-new-first` therefore fails with `make: unrecognized option '--simulate-new-first'`. Make does not automatically forward unknown flags to the inner command.
>
> 2. **What does `1` in `SIMULATE=1` mean?**
>    - `1` conventionally means enabled (**Boolean `True`**) in Unix CLI / Makefile usage.
>    - The [`Makefile`](../Makefile) uses this condition:
>      ```makefile
>      verify-rollback:
>      	PYTHONPATH=src $(UV) run python scripts/verify_rollback.py $(if $(SIMULATE),--simulate-new-first,) $(ARGS)
>      ```
>      Make's `$(if $(SIMULATE),...)` checks whether `SIMULATE` is non-empty, such as `1`, `true` or `yes`. If so, it adds `--simulate-new-first` to the Python command.
>
> 3. **Three ways to pass the simulation flag:**
>    - `make verify-rollback SIMULATE=1` *(recommended: short and easy to remember)*
>    - `make verify-rollback ARGS="--simulate-new-first"` *(forward through ARGS)*
>    - `python scripts/verify_rollback.py --simulate-new-first` *(run Python directly, without Make)*
>
> *Without `SIMULATE=1`, `make verify-rollback` starts rollback from the current traffic state.*

**What the script does:**
1. Lists revisions in time order and uses the oldest as the default rollback target, labeled Stable. Age alone does not prove it is healthy; confirm a known-good target before running.
2. Routes 100% traffic to the new revision (`rev2`) to simulate the pre-rollback state.
3. Rolls back 100% traffic to the stable revision (`2zaws5o`).
4. Polls readiness until the container wakes and the RoBERTa model is ready (`/ready` 200 OK).
5. Checks `/health`, `/ready`, `/predict` to confirm normal responses.
6. Saves evidence to `reports/P04-rollback-evidence.json`.

---

### Method 2: manual step-by-step check

To inspect and change traffic step by step:

#### Step 1: route 100% traffic to the new version
```bash
make change-traffic REV=feedbackpulse-api--rev2
```
*Check:* `make status` should show `rev2` receiving 100% traffic.

#### Step 2: roll back to the stable version at 100%
```bash
make verify-rollback
```
*The script detects the new version at 100%, switches back to `2zaws5o` and tests the service.*

#### Step 3: confirm the status
```bash
make status
```
*The result should show traffic back on the previous revision:*
```json
"Traffic": [
  {
    "revisionName": "feedbackpulse-api--2zaws5o",
    "weight": 100
  }
]
```

---

### Method 3: use Azure Portal

1. Open Azure Portal $\rightarrow$ **`feedbackpulse-api`**.
2. In the left menu, choose **Application $\rightarrow$ Revision management**.
3. Set **Traffic (%)**:
   - `feedbackpulse-api--rev2`: **0%**
   - `feedbackpulse-api--2zaws5o`: **100%**
4. Click **`💾 Save`** at the top.
5. A canary split such as **50% / 50%** is also possible.

---

## 3. Example recorded evidence

Use the saved [`reports/P04-rollback-evidence.json`](../reports/P04-rollback-evidence.json)
instead of a copied JSON example. The East Asia record is timestamped
**10 October 2026, 08:13:33 UTC** and reports a **15.00-second traffic cutover**.
The endpoint checks afterward returned 200 for `/health`, `/ready` and `/predict`.
This is not the total recovery time or a measurement of uninterrupted availability,
and it is not a Malaysia West rollback result. Running the script again with its
default output path would overwrite this evidence file.

---

## 4. Cloud-resource cleanup (teardown — P04-T06)

[`teardown.sh`](teardown.sh) cleans up the Azure Container App to help control Azure for Students costs, with the following safeguards:

> [!NOTE]
> **Default safe scope (`--app-only`):**
> `make teardown` deletes **only the configured Container App and its revisions**.
> The Environment, ACR, Log Analytics workspace, identities/role assignments,
> monitoring dashboard, alert and action group are not removed by this script.
>
> **Current CD does not recreate a deleted App.** It updates an existing App and
> fails if that App is missing. Older comments/output in `teardown.sh` still say
> a push recreates it; that message does not match the current CD workflow.

Keep resources while they are still needed. Before cleanup, review the exact
targets with the resource owner, including the alert/action group separately.
Do not uncomment base-resource deletion commands or delete the whole resource
group as routine cleanup: the ACR and Log Analytics workspace are shared with
other projects. Keeping these resources can still incur costs after App deletion.

### 4.1 Preview deletion with dry-run — no actual deletion
```bash
make teardown-dry-run
# Or
./scripts/teardown.sh --dry-run
```
*Prints the planned CLI commands for review without changing/deleting cloud resources.*

### 4.2 Interactive deletion with confirmation
```bash
make teardown
# Or
./scripts/teardown.sh
```
*Shows affected resources and waits for an explicit `yes` before deletion.*



