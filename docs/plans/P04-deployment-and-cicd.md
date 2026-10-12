# P04 — Deploy and release versions safely (Deployment & CI/CD)

- **Status:** `done` within the accepted P04 scope: the team's East Asia latency/rollback evidence plus the verified Malaysia West CD fix. CI #11 and CD #9 passed on 2026-10-11, including smoke tests and later API checks (6/6). Latency/rollback were not repeated in Malaysia West.
- **Release setting checked on 2026-10-12:** CD is paused with `FEEDBACKPULSE_CD_ENABLED=false`. The documentation push `3c428ec` passed [CI #13](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38212947323), and [CD #11](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38213177775) was skipped. No new deployment. This is not a fresh Azure service-status check.
- **Owner:** Person 2 — Backend and deployment
- **Main plan:** [Overview](../../overview-plan.md) · **Scope:** [Proposal](../../PROPOSAL.md)
- **Agreed requirements:** [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md) · [P02 Model pipeline](P02-model-pipeline.md) · [P03 Local backend](P03-local-backend.md)
- **Evidence deliverable:** `reports/P04-evidence.md`

The dated records below cover deployment failures, fixes, checks and limits. Earlier states are historical; the original phase plan remains at the end.

**Initial CD failure, 2026-10-10:** [CD run #4](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38048373569) failed at login, so automated CD in T03 was not yet confirmed. The table/checklist below retain the original report for comparison, not the latest verified CD result. Other manual-deployment evidence must be assessed separately.

## Deployment history — wait for revision readiness before passing CD — 2026-10-11

- **Fix:** `Verify deployed revision` polls every 10 seconds for up to 300 seconds using a monotonic deadline. Each read is limited to 30 seconds or the remaining time. It does not redeploy. Failed/Canceled states, read errors, a wrong image SHA or a ready revision without full traffic fail the check. Succeeded, latest=ready and 100% traffic are still required before smoke tests.
- **Tests:** Regression tests execute the workflow's actual Python code with an Azure stub/virtual clock. They cover immediate/delayed readiness, an old ready revision, read time counting toward the deadline, readiness exactly at the deadline failing, terminal failure and read errors. **75 CD/OIDC tests passed**, along with Ruff and `git diff --check`.
- **Fix version:** `.github/workflows/cd.yml` and `tests/test_cd_deployment.py` were committed in [`8d3964c79c1266315fd39e60f4088daa8aa3fda5`](https://github.com/nithit-cypherX/FeedbackPulse/commit/8d3964c79c1266315fd39e60f4088daa8aa3fda5).
- **Live result:** [CI #11](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139654748) succeeded in **3m 8s** and automatically triggered [CD #9](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38139856763), which succeeded in **3m 36s**. OIDC, build/push, deploy, verification and all three smoke-test payloads passed.
- **Evidence for the fix:** At 12:38:28, 12:38:39 and 12:38:50 UTC, latest was `0000002` but ready was `0000001`, so the check kept waiting. At 12:39:01 UTC it confirmed the new ready revision, matching SHA and 100% traffic, then ran smoke tests, which passed at 12:39:06 UTC. Verification took about **34 seconds**, within the 5-minute deadline.
- **Read-back after CD:** At 12:40 UTC, the App was Succeeded/Running, latest=ready=`feedbackpulse-api--0000002`, the revision was Provisioned/Healthy/Running, and both App/revision image tags matched `8d3964c79c1266315fd39e60f4088daa8aa3fda5`. Traffic was 100% to latest. Extra HTTP checks with TLS verification/no redirects passed **6/6**: health 200, ready 200, no token 401 and positive/negative/neutral predictions 200 with expected labels/model version. This was a post-deployment check, not another deployment.
- **Screenshots:** [CI #11 Success](../../reports/screenshots/p04-readiness-wait-ci-success-2026-10-11.jpg), [CD #9 Success](../../reports/screenshots/p04-readiness-wait-cd-success-2026-10-11.jpg), [revision 0000002 Running](../../reports/screenshots/p04-readiness-wait-revision-running-2026-10-11.jpg). Real browser captures were copied into reports and their hashes compared.
- **Release state:** the readiness fix passed without changing roles, resources or secrets. CD was enabled for this run, then paused on 2026-10-12. Existing Node/Ubuntu workflow warnings were not fixed.

## History — enable live CD — 2026-10-11

- **Permissions:** The old Environment-scoped assignment was gone after resource deletion. Restored `Container Apps Operator` only on `feedbackpulse-env` (assignment `ff93199a-db3a-4bf1-9644-94b57451d47b`) and added `Container Apps Contributor` only on `feedbackpulse-api` (`b104832c-bfc5-45a4-b705-5add1c511a26`) for `id-feedbackpulse-cd`. Read-back showed all 4 roles, including existing AcrPush/Managed Identity Operator. No RG/subscription-wide assignment or role-granting permission. OIDC trust and pull identity were unchanged.
- **GitHub:** Production remained main-only. Added `AZURE_SUBSCRIPTION_ID` and `SERVICE_TOKEN` from private configuration through [encrypted environment secrets](https://docs.github.com/en/rest/actions/secrets#create-or-update-an-environment-secret), without displaying values. Repository variables for RG, Environment, App, ACR name/server and pull identity matched manual deployment. Used the existing credential manager/LibSodium; no tools installed.
- **Workflow:** Kept the existing CD but limited it to updating an existing App, with no create fallback after a failed read. Before smoke tests, it checks Succeeded, latest=ready, image tag matching the CI-selected SHA and 100% traffic to the latest revision. Readiness failure now fails the workflow; temporary YAML permissions are owner-only.
- **Checks and publication:** 60 CD/OIDC tests, Ruff and diff checks passed. Committed/pushed only `.github/workflows/cd.yml` and `tests/test_cd_deployment.py` in `2caf9de201ebe8605f4aac0110cfdac3d3c7388e`.
- **Live run:** Set repository variable `FEEDBACKPULSE_CD_ENABLED=true` at 12:11 UTC, then pushed main once. [CI #10](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38138314681) passed in 3m 3s and automatically triggered [CD #8](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38138504090). OIDC login, ACR login, build/push, render and deploy succeeded, but the workflow ended in Failure after 2m 51s. This is not a green CD run or a passed smoke step.
- **Obstacle in the new check:** Deploy finished at 12:16:57 UTC. The immediate verification read failed at 12:16:59 UTC with `Deployment failed: the latest revision is not confirmed ready.`, skipping the workflow smoke test. The verification check did not wait for Azure's asynchronous readiness, even though offline tests passed. After Azure accepts the command, readiness needs a bounded wait, not a single read that assumes success or failure too early.
- **Later Azure/API result:** A GET at 12:18:49 UTC confirmed App Succeeded/Running, latest=ready=`feedbackpulse-api--0000001`, image tag `2caf9de201ebe8605f4aac0110cfdac3d3c7388e`, revision Provisioned/Healthy and 100% traffic to latest. API checks at 12:20 UTC passed 6/6: health 200, ready 200, no token 401, positive/negative/neutral predictions 200 with expected labels/model version (scores 0.9796/0.9251/0.6282). These HTTP checks happened after the workflow ended; they were not a rerun and do not change CD #8's Failure status.
- **Result:** no rerun followed the error. The new revision was running, with the older manual revision Active at 0% traffic/scaled to 0. The bounded-readiness fix above addressed the premature verification failure without new roles or resources.
- **Screenshots:** [CI passed](../../reports/screenshots/p04-cd-live-ci-success-2026-10-11.jpg), [CD failed at verification](../../reports/screenshots/p04-cd-live-verify-failed-2026-10-11.jpg), [new revision Running](../../reports/screenshots/p04-cd-live-new-revision-running-2026-10-11.jpg).

## History — recreate the Environment and App — 2026-10-11

- **Recovery target:** recreate `feedbackpulse-env` and `feedbackpulse-api` in Malaysia West while keeping the existing ACR, identities and Log Analytics.
- **Old resources deleted:** One Environment DELETE returned HTTP 202 at 11:09 UTC (request/correlation `5ca4bbd4-2161-4a7a-bef0-11c7bb943430`). While waiting, work switched to checking the teammate's deployment. At 11:44 UTC, both the old Environment and App returned HTTP 404; the exact deletion completion time is unknown. Existing ACR, pull identity and workspace still returned HTTP 200.
- **Separate East Asia check:** the teammate's API passed 10/10 smoke checks. The Malaysia West retry below used this deployment's own resources and configuration, not `.env.friend-test`.
- **New Environment ready:** Sent a PUT for `feedbackpulse-env` in Malaysia West at 11:45 UTC using API `2026-07-01`, with `environmentMode=WorkloadProfiles` and one Consumption profile from the start, linked to existing Log Analytics. GET confirmed Succeeded at 11:47:52 UTC. New domain: `happybay-6ab85ce1.malaysiawest.azurecontainerapps.io`; correlation `37e6cc3c-3452-4acf-b8f8-fa592624b12f`. See [Environment screenshot](../../reports/screenshots/p04-manual-retry-env-succeeded-2026-10-11.jpg).
- **Preflight:** The renderer validated real settings without showing the token. Digest `sha256:af2854fbd8982758aff1cae7b4882ff47f03b3c419ebc1a514afdde3d9d692c0` was still in ACR, and the pull identity still had AcrPull. The first role-read command could not combine `--scope` and `--all`; removing `--all` fixed the check. This was not a deployment failure, and no roles changed.
- **Manual deployment passed:** Ran `make dry-run`, then `make deploy` once, using the existing Python environment without syncing/installing dependencies. Did not run `docker-push` because the digest was already in ACR. Revision `feedbackpulse-api--ec2psff` was created at 11:49:31 UTC. GET at 11:52:59 UTC confirmed App Succeeded/Running and latest revision matching latest ready revision. At 11:54 UTC, revision checks showed Provisioned/Healthy with no error. See [App Running](../../reports/screenshots/p04-manual-retry-app-running-2026-10-11.jpg) and [revision screenshot](../../reports/screenshots/p04-manual-retry-revision-ready-2026-10-11.jpg).
- **API checks passed 4/4 — 11:53 UTC:** New endpoint: `https://feedbackpulse-api.happybay-6ab85ce1.malaysiawest.azurecontainerapps.io`. `/health` → 200 healthy, `/ready` → 200 ready, `/predict` without token → 401, with token → 200 (`I love this product.` → positive, score 0.9842). Model version matched `sentiment-6e7ff9fbc17c-0110c462`. Used SERVICE_TOKEN from private `cloud.env`, verified TLS and did not follow redirects. No token was logged. This was not a load or accuracy test.
- **Scope after completion:** Existing ACR, pull/CD identities and Log Analytics still returned HTTP 200. Registry auth used the pull identity with no passwordSecretRef; multiple revisions, 100% traffic to latest and scale 0–3 matched the existing template. No new roles/quota, admin/CD enablement, new build/push or P01–P03 code changes.
- **Conclusion:** this manual deployment passed, but creating WorkloadProfiles from the start does not prove the cause of the earlier Operation expired error. Automated CD was checked separately. Permissions on recreated resources must be rechecked; assignments on deleted resources cannot be assumed to survive.

## History — App deletion before Environment recreation — 2026-10-11

- **Sequence:** the App was deleted first. The Environment deletion and recreation happened separately, as recorded above.
- **Preflight passed:** The Environment had only `feedbackpulse-api`, with no Jobs, storages, Dapr components or certificates. The App had no volumes/ready revision. Renderer/private configuration checks passed without showing the token. The existing digest was in ACR, the pull identity had AcrPull, and the workspace matched the logging destination.
- **Completed action:** DELETE of only `feedbackpulse-api` returned HTTP 202 at 10:59:43 UTC. GET from 11:00:40 UTC onward returned HTTP 404 `ResourceNotFound`, confirming deletion. The old App/revisions cannot be recovered by undo, but configuration/image for recreation remained.
- **Still present:** `feedbackpulse-env` returned HTTP 200, WorkloadProfiles/Succeeded with its existing Consumption profile. ACR, Log Analytics workspace and `id-feedbackpulse-pull` returned HTTP 200. No resource-group/lab-resource deletion, admin/role change, build/push or CD enablement.
- **State at this check:** Environment recreation had not started; it was still an untested recovery approach.
- **Conclusion limit:** Recreation was an unproven recovery approach, not evidence that the old Environment caused Operation expired.

## History — public-image experiment and cleanup — 2026-10-11

- **Experiment:** created one temporary App, `feedbackpulse-diag-public`, in the existing Malaysia West `feedbackpulse-env`, using `mcr.microsoft.com/k8se/quickstart:latest`, Consumption, CPU 1 / RAM 2 GiB, replicas 1–1 and HTTPS target port 80. No identity, registry credentials or secrets, so it did not use FeedbackPulse code/model/ACR or change the real App.
- **Result:** Azure Activity Log started at 09:45:24 UTC and ended `Failed / ContainerAppOperationError / Operation expired` at 10:05:34 UTC (about 20 minutes; correlation `ee76b80e-ad0c-4965-9b0a-ac1875040c11`). Reading the App at 10:06 UTC confirmed Failed with blank latest/ready revisions, so no HTTP checks were sent. Revision reads also returned `InternalServerError` while waiting. CLI exit 0 when accepting the request was not treated as success. See [provisioning screenshot](../../reports/screenshots/p04-public-probe-provisioning-2026-10-11.jpg) and [Failed screenshot](../../reports/screenshots/p04-public-probe-failed-2026-10-11.jpg).
- **What this shows:** Provisioning also failed for a sample App without our private ACR or code, so the problem was not limited to those. It still did not identify the Environment, capacity/quota or another cause, nor prove every part of our private-image path correct. Before the experiment, image-pull diagnostics were unavailable because the region's Kusto cluster could not be resolved. See [diagnostics limitation](../../reports/screenshots/p04-image-pull-diagnostics-unavailable-2026-10-11.jpg).
- **Separate ACR admin error:** ACR Activity Log recorded `listCredentials/action` failures with `UnAuthorizedForCredentialOperations` at 09:28:51 and 09:54:47 UTC, after real-App failures at 08:58:52 and 09:24:56 UTC. These later events cannot explain the earlier failures by themselves. The requesting page/tool was unknown. At inspection, the real App used UserAssigned `id-feedbackpulse-pull` with no registry username/passwordSecretRef. [Microsoft supports managed-identity image pulls without admin credentials](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull), so ACR admin was not enabled based on the generic suggestion.
- **Cleanup complete:** Checked the temporary App's name/ID, experiment tag, image and Environment before deletion. Sent DELETE at 10:08:02 UTC; GET returned `404 ResourceNotFound` at 10:08:32 UTC, also shown in Portal. See [temporary App deleted](../../reports/screenshots/p04-public-probe-deleted-details-2026-10-11.jpg). Did not delete the shared Environment, ACR, workspace or resource group. The Environment remained Succeeded after cleanup. Actual cost was not measured; deletion does not refund earlier usage or stop other resources' costs.
- **Real App state:** after cleanup, `feedbackpulse-api` read InProgress with no ready revision. The owner reported stopping it, but a final Stopped state was not confirmed. The experiment did not establish that the real App was usable.
- **Local evidence:** All four images are real screenshots in `reports/screenshots/`, with matching original/copy SHA-256 hashes. These record a failed experiment, not a successful deployment.

## History — fix false success and update the App once — 2026-10-11

- **First create result:** Sent `make deploy` at 08:38:29 UTC to `feedbackpulse-api` in `feedbackpulse-env`, using image `itcs355u6688124.azurecr.io/feedbackpulse@sha256:af2854fbd8982758aff1cae7b4882ff47f03b3c419ebc1a514afdde3d9d692c0` from source commit `777f6537f792887b077071f729b865bdf1724bcc`. The initial check recorded InProgress, but Activity Log's final result at 08:58:52 UTC was `Failed / ContainerAppOperationError / Operation expired` (correlation `2dbf64b2-f2d4-4471-a6ab-5eb6cb5c127c`). See [provisioning](../../reports/screenshots/p04-first-app-provisioning-2026-10-11.jpg) and [final error](../../reports/screenshots/p04-first-app-operation-expired-2026-10-11.jpg). This was not a success.
- **Makefile issue:** The first Azure CLI command returned exit 0, so the old message said Deployment complete even though the App failed. A guard fix and one update attempt followed on the same App.
- **Local fix:** After create/update, `make deploy` must read `provisioningState=Succeeded` and a non-empty `latestRevisionName` matching `latestReadyRevisionName` before reporting success. Read failure, Failed/InProgress or an old ready revision fails the check. The success message still asks for API checks. No automatic retry or CD-workflow change in this round.
- **Tests:** Added cases to the existing Azure CLI stub harness in `tests/test_oidc_workflow.py`. Before the fix, 6 cases reproduced false success. After the fix, `.venv/bin/python -B -m pytest tests/test_oidc_workflow.py tests/test_cloudlayer.py tests/test_portability.py -q -p no:cacheprovider` passed **92 tests**. Focused Ruff and `git diff --check` passed. These tests did not call Azure, install dependencies or download models.
- **Retry result:** At 09:24:49–09:24:56 UTC (16:24 Thai time), called `az containerapp update` directly **once** with YAML from the existing renderer/private token, limiting the action to update with no create fallback. The image/Environment/pull identity matched the preflight check. Exit 1: `InternalServerError`, correlation `0bc9167c-b288-4d85-b1bf-8d16f4eb045d`. Activity Log confirmed `Microsoft.App/containerApps/write` Failed at 09:24:56.848 UTC; this was not just a local display issue.
- The retry Activity Log also showed `listSecrets/action` Failed with `ResourceNotProvisioned` because the App had never provisioned successfully. The write error gave no deeper cause, so quota, image pull, probes and model code remained unconfirmed possibilities. The Environment was still Succeeded, ACR held the same digest, ACR ARM authentication was enabled and the pull identity had AcrPull. Earlier usage output had no Consumption entry; that was not interpreted as zero quota.
- **State after retry:** The App was still `Failed`, with blank `latestRevisionName` and `latestReadyRevisionName`, despite `runningStatus=Running`. Usability was unconfirmed. **None of the four API checks ran** (`/health`, `/ready`, `/predict` with/without token), and none was claimed to pass. Azure's assigned URL was still `https://feedbackpulse-api.yellowsky-37e5f0ed.malaysiawest.azurecontainerapps.io`.
- **Scope afterward:** Role assignments matched the baseline: 3 for CD and 1 pull AcrPull, with no App Contributor. Temporary rendered YAML was deleted.
- **Retry screenshot:** [Azure Activity Log — InternalServerError at 16:24:56](../../reports/screenshots/p04-app-update-internal-server-error-2026-10-11.jpg) is an unedited real viewport capture, copied into the repo with matching hash. It shows the operation, time and error code. Longer text is limited by the screen size, so use the CLI/Activity Log results above alongside it. It is not evidence of passed API checks.
- **Result limit:** deployment remained failed after the single retry. It was not automatically retried or recreated.

## P04-T03 — target inspection and identity creation — 2026-10-10

- **2.1:** The Azure for Students subscription was Enabled, and the account had Owner. Resource group `itcs355-u6688124` contained ACR `itcs355u6688124` (Malaysia West, Basic, legacy RBAC, admin account disabled) and three Lab 4 identities. No FeedbackPulse Container App/Environment existed. The old CD's teammate-resource fallback was not used. GitHub default branch was `codex/bootstrap`; `production` and the repository had no secrets/variables, deployment branches were No restriction, and required reviewers were not enabled.
- The repo uses an **immutable OIDC subject**, as shown in GitHub Settings, with prefix `repo:nithit-cypherX@90242135/FeedbackPulse@1386609561`. Section 2.3 must use this repo's value, not copied Lab 4 trust or a repo-name-only subject. No federated credential or real token exchange yet.
- **2.2 succeeded:** Created User-assigned Managed Identity `id-feedbackpulse-cd` in the existing resource group at `malaysiawest`, tagged `project=feedbackpulse`, `course=itcs355`, `student=itcs355-u6688124`, `purpose=github-actions-cd`. Read-back with `az identity show` and Azure Portal Overview matched the created name/location/Client ID/Principal ID.
- Reads returned **0 federated credentials** and **0 ARM role assignments** for this principal. No client secret or cloud permissions were added at this stage.
- **Inspection obstacles:** The existing CLI could not load extension `ml`, so core commands used a process-only temporary extension directory, without config changes or installs. Graph lookup did not find the new principal immediately after creation, so ARM role assignments were read and filtered directly by principal ID. No duplicate Service Principal was created.
- **Screenshot:** [Azure Portal — identity created](../../reports/screenshots/p04-02-02-managed-identity-created-2026-10-10.jpg) is a real 1280 × 480 screenshot, cropped only to remove the top email/account bar. Result text was unchanged. It contains no password/token, but does show Overview resource identifiers. It proves identity creation, not successful OIDC login or CD.
- **Limits:** identity creation did not test trust or token exchange. The App/Environment were still missing, and old CD still tried to read ACR admin credentials while that account was disabled.

---

## Section 2.3 — trust preflight — 2026-10-10

- Rechecked GitHub Settings: the default immutable-subject prefix remained `repo:nithit-cypherX@90242135/FeedbackPulse@1386609561`. CD uses `production`, which still had **No restriction** and no environment secrets/variables.
- Azure preflight: same `id-feedbackpulse-cd`, **0** federated credentials and **0** role assignments. Planned credential: `github-feedbackpulse-production`; issuer `https://token.actions.githubusercontent.com`; subject `repo:nithit-cypherX@90242135/FeedbackPulse@1386609561:environment:production`; audience `api://AzureADTokenExchange`.
- **Trust blocked:** creation did not run because `production` had no branch restriction. No trust, role or deployment change occurred.
- Reason: an environment subject does not also contain the branch, so this trust could not be described as limited to `codex/bootstrap`. See [GitHub subject reference](https://docs.github.com/en/actions/reference/security/oidc#example-subject-claims) and [environment protection guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure). Creating a credential alone also does not prove token exchange, as described in [Microsoft Learn](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust-user-assigned-managed-identity).
- [Obstacle screenshot — production had no branch restriction](../../reports/screenshots/p04-02-03-production-branch-restriction-pending-2026-10-10.jpg) shows real Settings, not successful trust/login.
- **Required protection:** restrict production deployments to the intended branch before creating the environment-scoped trust. The default branch was renamed to `main` next.

## Rename the default branch to main — 2026-10-10

- The default branch changed from `codex/bootstrap` to `main` before trust creation.
- Used GitHub's Rename default branch. `git ls-remote --symref origin HEAD` returned `refs/heads/main` at the same commit, `21d189d807150d70ab6390b8e1e7b28cb13d403a`. Remote `codex/bootstrap` was gone; the two teammate branches were unchanged.
- In `/home/nirvana/feedbackpulse`, renamed the local branch to `main`, fetched `origin/main`, and set upstream/`origin/HEAD` to `origin/main`. No commit, push, reset or merge. Working-tree/index diffs and untracked-file checksums matched before/after.
- Existing CI/CD already triggered on `main`, so workflows and historical old-branch references were not changed. GitHub does not automatically update teammates' local clones; those still on the old branch need to update their branch/upstream using [GitHub's instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/renaming-a-branch#updating-a-local-clone-after-a-branch-name-changes).
- **Observed side effect:** GitHub started [CI #7](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38065304132) on `main` at 22:51 Asia/Bangkok with event `push`, although the rename did not add a commit. CI was still running when the screenshot below was taken.
- [Main as default branch](../../reports/screenshots/p04-default-branch-main-2026-10-10.jpg) proves only the rename. CI was still pending in the image, not a new passed test run.
- **Final result update:** CI #7 succeeded in 2m 46s and triggered [CD #5](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38065492519), which failed after 31s at `Log in to Azure (Service Principal Fallback)` because client-id/tenant-id were missing. ACR login, build/push, render, deploy and live smoke tests were skipped. No deployment occurred. [Log showing no deployment](../../reports/screenshots/p04-main-rename-cd-login-failed-no-deploy-2026-10-10.jpg). This CI checked the existing remote commit, not uncommitted local P02/P03 work.

## Section 2.3 — main-only restriction and trust configured — 2026-10-10

- **GitHub:** Set Deployment branches and tags to Selected branches and tags, adding one **Branch** rule named `main` with no wildcard. Reload still showed **1 branch and 0 tags allowed**. No reviewer/timer, admin-bypass, secrets/variables or workflow changes.
- **Azure:** Created one federated credential, `github-feedbackpulse-production`, on `id-feedbackpulse-cd`, with issuer `https://token.actions.githubusercontent.com`, subject `repo:nithit-cypherX@90242135/FeedbackPulse@1386609561:environment:production` and audience `api://AzureADTokenExchange`. The subject identifies repo/environment; the GitHub production rule restricts the branch. The subject itself does not contain main.
- **Checks:** Before creation: 0 trust entries/roles. After creation, `show` matched issuer/subject/audience/name and `list` returned 1 trust entry. ARM role assignments filtered by principal ID remained **0**. Portal list/details matched. This configured trust only; cloud permissions were still absent.
- **Real screenshots:** [Production allows only main](../../reports/screenshots/p04-02-03-production-main-only-2026-10-10.jpg) · [Azure trust created](../../reports/screenshots/p04-02-03-federated-trust-created-2026-10-10.jpg). The Azure image was cropped only to remove the top account bar/blank space. The table shortens the subject onscreen, so CLI read-back and Portal details were used to check its full value; the image does not show the complete string.
- **What passed:** Configuration save/read-back only. No live branch-rejection test or OIDC token exchange yet, and not successful CD.

## Section 2.4 item 1 — prepare login-only locally — 2026-10-10

- **Base version:** `main` at `21d189d807150d70ab6390b8e1e7b28cb13d403a`; these checks covered local workflow changes before publication.
- Added [oidc-check.yml](../../.github/workflows/oidc-check.yml): manual-only, using `production` and requiring branch `main`. Checks `AZURE_CLIENT_ID`/`AZURE_TENANT_ID` secrets before OIDC login with `azure/login@v2` and `allow-no-subscriptions: true`. No subscription ID/client secret. After login, `az account show` checks client, tenant and service-principal type without printing account JSON/tokens. No checkout/build/push/resource write/deploy.
- Changed only the job guard/header comment in [cd.yml](../../.github/workflows/cd.yml): both CI-triggered and manual paths require **repository variable** `FEEDBACKPULSE_CD_ENABLED == 'true'` and `main`. An unset variable skips the job. Do not use an environment-level variable for this guard because it is unavailable when the job is evaluated. Existing deployment steps were not yet fixed or ready to enable.
- Followed [Azure Login v2 — login without subscription](https://github.com/Azure/login/tree/v2#login-without-subscription) and [GitHub vars context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#vars-context), separating authentication from resource permissions. No dependency additions or upgrades to existing CD actions.
- **Local results:** `pytest -q tests/test_oidc_workflow.py tests/test_cloudlayer.py` passed **24 tests** (12 new + 12 existing cloud-adapter tests). `ruff check tests/test_oidc_workflow.py` and `git diff --check` passed. Covered missing settings, matching/mismatching/missing identity fields and workflow/guard structure on both paths, using mocked Azure output. Initial lint found import-order/exec issues in tests; these were fixed without disabling lint rules.
- **Limits:** actionlint was unavailable, so GitHub workflow validation and real token exchange were not confirmed. These were local checks, not successful OIDC login. The guard was **not on GitHub yet** because it had not been pushed. No secrets/variables/roles, Azure changes, commit or CI/CD run.
- **Safety sequence:** publish the default-off guard before adding credentials that the old CD could use. Keep `FEEDBACKPULSE_CD_ENABLED` off until deployment configuration and permissions are ready.

## Section 2.4 item 2 — push and confirm deployment is skipped — 2026-10-10

- **Preflight:** remote `main` matched the local base. Repository/environment variables were unset, so CD was disabled.
- Commit [5ef6c9098ca3b6193f02ac3480d1db8975f01f22](https://github.com/nithit-cypherX/FeedbackPulse/commit/5ef6c9098ca3b6193f02ac3480d1db8975f01f22) contains only `.github/workflows/cd.yml`, `.github/workflows/oidc-check.yml`, `tests/test_oidc_workflow.py`. Remote main matched this commit; local P02–P03 changes were not part of this CI run.
- **Live result:** [CI #8](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38067390683) from the main push passed in **2m 59s**, including lint/tests and container build/integration smoke tests. Then [CD #6](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38067594679) showed **Skipped** in 1s, with job `Build, Push & Deploy to Azure Container Apps` skipped too. No Azure login, image push or deployment from this CD run. CI checked committed code, not local-only P02–P03 work.
- [Azure OIDC login check](https://github.com/nithit-cypherX/FeedbackPulse/actions/workflows/oidc-check.yml) was visible with **0 workflow runs**. No Run workflow/re-run or GitHub/Azure settings changes. This verifies the automatic guard path, not OIDC token exchange or a live manual-dispatch guard test.
- **Obstacle and workaround:** Ubuntu Git had no HTTPS push credential. The first attempt waited for a username and was stopped; a prompt-disabled attempt confirmed `could not read Username`. Windows Git with its existing credential manager pushed successfully. No token read/copy, new credential, installation or persistent config change. `safe.directory` was command-only and limited to the verified WSL repo path.
- **Screenshots:** [CI passed](../../reports/screenshots/p04-02-04-ci-pass-2026-10-10.jpg) and [CD/deploy job skipped](../../reports/screenshots/p04-02-04-cd-skipped-2026-10-10.jpg) are real, unedited captures stored locally with matching copy hashes.

## Section 2.4 item 3 part A — login configuration — 2026-10-10

- **Configuration:** set `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` in `production`. This step did not run login or grant roles.
- **Preflight:** `production` remained main-only (1 branch/0 tags). Repository/environment had no variables, so `FEEDBACKPULSE_CD_ENABLED` was still off. Read-back of `id-feedbackpulse-cd` and `github-feedbackpulse-production` matched the existing repo/environment. There was 1 federated credential and **0** ARM role assignments for the principal. Trust/permissions were unchanged.
- **Saved:** Added only the two Environment secrets above, using the client/tenant IDs read from Azure. Checked entered values before saving; both names remained after reload. No client secret/password, subscription ID or variables added.
- **Result limit:** Configuration was saved, but GitHub does not reveal secret values after saving, and OIDC login was untested. [Azure OIDC login check](https://github.com/nithit-cypherX/FeedbackPulse/actions/workflows/oidc-check.yml) still showed **0 workflow runs**. Run workflow was not clicked.
- **Real screenshot:** [Production — main-only and two Environment secrets](../../reports/screenshots/p04-02-04-production-login-settings-2026-10-10.jpg) shows secret names only, not values. Copy hashes matched.

## Section 2.4 item 3 part B — OIDC login-only passed — 2026-10-10

- Ran `Azure OIDC login check` once on `main`, with no roles, trust changes or deployment. Preflight confirmed remote HEAD `5ef6c9098ca3b6193f02ac3480d1db8975f01f22`, main-only production with two secrets and no repository/environment variables; CD remained off.
- **Live result:** [Login-only #1](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38068476836) started at 23:38 Asia/Bangkok and ended **Success, 13s**. The [login job](https://github.com/nithit-cypherX/FeedbackPulse/actions/runs/38068476836/job/114260862473) **succeeded, 7s**. The job page marked Check required login settings, Log in to Azure with OIDC only, Verify the signed-in identity and post-login cleanup as passed.
- This confirms authentication through the workflow's client-ID, tenant-ID and service-principal checks, without a client secret or deployment roles. It **does not prove image push/deployment permissions**. Azure identity still matched part A, and this principal still had **0** ARM role assignments in the subscription. CD still had 6 runs, latest the existing skipped CD #6; login-only did not trigger another CD.
- **Warnings:** GitHub reported `azure/login@v2` moving from Node.js 20 to Node.js 24, `Failed to parse Azure CLI version.`, and an upcoming Ubuntu-version change for `ubuntu-latest`. None failed the run. Workflow/dependencies were not changed for these warnings, and the CLI-version warning's cause remained unconfirmed.
- **Evidence limits:** Per-step log loading showed `Error:` even after reload; the browser blocked View raw logs. No claim was made to have read an internal PASS log line. Evidence used the Success status, passed steps and workflow at the executed commit. No bypass/rerun.
- **Real screenshot:** [Login job and identity-check steps passed](../../reports/screenshots/p04-02-04-oidc-login-steps-2026-10-10.jpg) contains no tokens/secret values. Full-page capture failed, so an unedited viewport capture was used. Copy hashes matched.
- **Limit:** authentication passed, not image push or deployment. The App/Environment and deployment permissions still needed setup, and the ACR-admin-password dependency needed replacing.

## Section 2.5 item 1 — local CD configuration changes — 2026-10-11

- **Base version:** `main` at `5ef6c9098ca3b6193f02ac3480d1db8975f01f22`. This changed CD configuration, not the API, model, Dockerfile or dependencies.
- **CD:** Removed teammate-target and credential fallbacks. Kept OIDC and added preflight before checkout/install/build to require login IDs, targets, registry identity and `SERVICE_TOKEN`. Missing/whitespace values or the old sample token stop the job without printing values. Existing CD/main gates remained; no GitHub Settings changes.
- **Registry auth:** The template attaches a user-assigned identity and uses the same resource ID in registry configuration, following [Azure YAML/ARM schema](https://learn.microsoft.com/en-us/azure/container-apps/azure-resource-manager-api-spec) and [managed identity image pull](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull). Removed the ACR password secret/admin-credential reads from CD and `Makefile:deploy`, which share the renderer. Other targets were unchanged.
- **Renderer/docs:** Accept `REGISTRY_IDENTITY_ID` or `AZURE_REGISTRY_IDENTITY_ID`, validate format/identity references, preserve quotes/newlines as YAML data and mask secrets on stdout. Updated `cloud.env.example` and deployment guidance in `cloudlayer/README.md`. No credential or real-target fallbacks.
- **Checks in the existing .venv:** Before changes, `test_cloudlayer`, `test_oidc_workflow`, `test_portability` passed **27 tests**; afterward **84 tests** passed, plus focused Ruff, renderer `--validate-only`, shell syntax and `git diff --check`. Executed the CD render script and `make deploy` with **Azure CLI/uv stubs in pytest temporary directories** to check identity/token forwarding and YAML cleanup. No live Azure calls, model download, Docker build or installs.
- **Changed areas:** CD, renderer, template, the Makefile deploy caller, configuration example, related documentation and tests.
- **Still unverified:** Image-pull identity, targets and permissions needed separate setup/checks. Local passing tests are not live deployment evidence. Create/update behavior, image tagging, model/runtime sizing and smoke-test behavior were unchanged in this round.

## Section 2.5 item 2 — prepare the pull identity and AcrPull — 2026-10-11

- **Preflight:** ACR `itcs355u6688124` in `itcs355-u6688124` used `LegacyRegistryPermissions`, with admin credentials disabled and `az acr config authentication-as-arm show` already `enabled`. Registry configuration was unchanged. No pull identity with this name existed; CD roles and App/Environment counts in the RG were 0.
- **Result:** Created `id-feedbackpulse-pull` in Malaysia West (principal ID `c9dd463a-bebb-4942-ae53-99f651bc04e0`, client ID `64ed7195-0e03-4401-8bd3-75a47ab7d990`). Granted built-in `AcrPull` (`7f951dda-4ed3-4680-a7ca-43fe172d538d`) only at ACR `itcs355u6688124` scope, not RG/subscription. Role assignment ID: `7ee2be03-cc3d-48ad-b874-bfa7de03bb9f`, created at 09:48 Thai time.
- **Read-back:** Azure CLI showed the pull identity with exactly one role at the intended scope and 0 federated credentials. `id-feedbackpulse-cd` still had 0 roles, registry configuration was unchanged, and App/Environment counts remained 0. Portal role assignments matched CLI: `AcrPull / itcs355u6688124 / Container registry / id-feedbackpulse-pull / None`.
- **Real screenshots:** [Identity Overview](../../reports/screenshots/p04-02-05-pull-identity-created-2026-10-11.jpg) and [Identity AcrPull](../../reports/screenshots/p04-02-05-pull-acrpull-2026-10-11.jpg), stored locally/copied into the repo with matching SHA-256 hashes. Some columns are clipped in the real viewport; full names/scopes were read through Portal accessibility and CLI, not edited into the image.
- **Minor issue:** The first create command stopped at CLI parsing of `--query` before resource creation. Removing the display query fixed it; creation and role assignment then succeeded. No extra permission or installation needed.
- **Limits:** In this registry mode, `AcrPull` can read images across the shared lab ACR, not only FeedbackPulse, but does not grant push/delete according to the checked role definition. The identity was not attached to an App; no live image-pull/deployment test, CD enablement or GitHub settings change.

## Section 2.6 — Environment created, but its type differs from the plan — 2026-10-11

- **Before creation:** Subscription policy `sys.regionrestriction` allowed Malaysia West but not Southeast Asia for new resources, although the existing RG was in Southeast Asia. The RG was not moved/changed. Malaysia West Environment-count quota read 0/1, and the target name did not exist.
- **Create result:** Used core CLI `az containerapp env create` with `--enable-workload-profiles true`, `--logs-destination log-analytics` and workspace `mlwitcs3logalytif5574ef1`'s customer ID directly. Read-back showed `Succeeded`, Malaysia West, one `Consumption` profile and the existing workspace's logs customer ID. No new Log Analytics, Dedicated profile or custom VNet.
- **Configuration obstacle:** Portal showed Environment type **Express**. ARM API `2026-07-01` confirmed `properties.environmentMode = Express`; the initially checked `2025-07-01` API did not show this field. A Consumption profile alone therefore did not prove the planned Workload profiles environment. The command did not request Express, and the installed core CLI help had no `--environment-mode`. This evidence alone did not establish the service-side cause.
- **Impact:** The [existing template](../../cloudlayer/containerapp.template.yaml) uses `activeRevisionsMode: Multiple`, and P04 needs traffic switching to an old revision. [Microsoft Learn — Express](https://learn.microsoft.com/en-us/azure/container-apps/express-overview#not-supported) says multiple revisions/traffic splitting are unsupported. Express therefore did not support the planned rollback behavior.
- **Quota/scope checks:** Both `az containerapp env list-usages` and REST usages API `2025-07-01` returned `value: []`. This proves neither zero CPU quota nor sufficient quota. RG resource count rose from 13 to 14, only this Environment. Apps remained 0, CD roles 0, and the pull identity retained one AcrPull role on the existing ACR. Workspace settings stayed retention 30 days, PerGB2018 and daily cap -1 (no cap); shared lab workspace settings were unchanged.
- **Real screenshot:** [Environment created: Express / Applications 0](../../reports/screenshots/p04-02-06-environment-created-2026-10-11.jpg), clipped to remove the top account bar without editing result text. Repo/original SHA-256 hashes matched. It shows creation and the obstacle, not successful CD or confirmed CPU quota.
- **Result limit:** the Environment was created, but its type did not support the required multiple revisions. CPU quota and deployment were still unverified.

### Section 2.6 continued — one attempt to change the existing Environment type — 2026-10-11

- **Preflight:** Live reads showed Express / Succeeded, 0 Apps/Jobs in the RG, 0 CD roles and ManagedEnvironmentCount quota 0/1. Used API `2026-07-01` because the installed core CLI lacked an environment-mode option. No tool install/upgrade.
- **One request:** Sent `PATCH` to the existing Environment ID at `2026-10-11T05:57:47Z` with body `{"location":"malaysiawest","properties":{"environmentMode":"WorkloadProfiles"}}`, without overwriting logs/other profiles. CLI exit 0; Activity Log showed Started / Accepted at 05:57:48Z. Only GET reads followed, no repeated PATCH.
- **During the operation:** First read: Archived / Updating; later WorkloadProfiles / Updating with null deploymentErrors. This was not success. Existing logs customer ID, retention 30 days, PerGB2018 SKU and daily cap -1 remained. CPU usages from APIs 2025-07-01 and 2026-07-01 were empty during Updating, so quota remained unconfirmed.
- **Final result — failed:** Observed Failed at `2026-10-11T06:26:23Z` (13:26:23 Thai time, about 28 minutes 36 seconds after the request; observation time, not event completion time). Error: `ErrorCode: ManagedEnvironmentOperationFailed, Message: The managed environment's operation failed due to internal server error, please retry later.` Stopped waiting at the terminal state. No second PATCH was sent during this attempt.
- **Read-back after failure:** At 06:28:49Z, the same Environment ID was WorkloadProfiles / Failed, with one Consumption profile, existing logs destination/customer ID and null infrastructureResourceGroup. RG resources remained 14, App/Job 0, CD roles 0, and one pull AcrPull role on the existing ACR. Activity Log still showed only Started/Accepted in the checked output. Final-state evidence came from resource GET and Portal showing Failed, not a claimed Failed Activity Log event.
- **Screenshot:** [Portal — provisioning Failed / internal server error](../../reports/screenshots/p04-02-06-workload-profiles-update-failed-2026-10-11.jpg) is a real capture with the top account bar removed and text unchanged. It shows Environment name/error/Failed status; mode/profile/logs were checked through API. Repo/original SHA-256 hashes matched.
- **Result limit:** Azure changed the mode field, but a working conversion was not proven. CPU quota/deployment remained unchecked, and the internal-server-error message did not identify a cause or prove recreation necessary.

### Section 2.6 — one more recovery attempt on the same Environment — 2026-10-11

- **Earlier read-only findings:** Environment was WorkloadProfiles / Failed; Malaysia West Environment-count quota was 1/1, with only `feedbackpulse-env` in that region. Activity Log still had Started/Accepted for the first request (correlation `f21f109a-3445-47dd-84c1-39341c9a8278`). Portal Environment Health and GET detector API returned errors; the deployment detector could not fetch Malaysia West data. Cause remained unknown. Quota 1/1 limits creating another Environment alongside it; it does not prove the failure's cause. Consumption CPU quota was still unconfirmed.
- **Preflight:** Live read at 06:43:09Z confirmed the same target ID, Failed / WorkloadProfiles, one Consumption profile and the same logs destination/customer ID. Apps/Jobs 0, CD roles 0.
- **Sent once — do not repeat:** At `2026-10-11T06:43:39Z` (13:43:39 Thai time), sent the same API `2026-07-01` PATCH with body `{"location":"malaysiawest","properties":{"environmentMode":"WorkloadProfiles"}}` once for this recovery attempt. CLI exit 0 with no response body. Read-back at 06:43:42Z showed Updating / WorkloadProfiles with the old error still present, not success or a new failure.
- **Final result — recovered:** GET observed `WorkloadProfiles / Succeeded` and `deploymentErrors = null` at `2026-10-11T06:45:01Z` (13:45:01 Thai time, about 1 minute 23 seconds after the request; observation time, not event completion time). Polling stopped at the terminal state, with no extra PATCH. Total: one original request and one recovery request. No archive/delete/recreation.
- **Post-success checks:** At 06:45:59Z, API confirmed the same name/region, Succeeded, WorkloadProfiles, no error, one Consumption profile and existing logs destination/customer ID. Workspace retention 30 days, PerGB2018 and daily cap -1 remained. RG resources stayed 14, no App/Job, CD roles 0 and one pull AcrPull role on the existing ACR. Recovery Activity Log showed Started/Accepted (correlation `e521807b-ae8c-42cc-909b-d7527c7d64e6`), but no terminal event in the retrieved list. Success was confirmed by resource GET/Portal, not a claimed Succeeded Activity Log event.
- **Screenshot correction — 2026-10-12:** The saved recovery screenshot shows the Environment header, but not the status or type fields. It cannot confirm recovery and is not used as evidence. The dated GET results above remain the recorded result. No replacement screenshot or new cloud check was made.
- **Limits:** provisioning recovery passed, but App deployment and Consumption CPU quota were still unproven. Usage output showed only General Purpose/Memory Optimized cores at limit 0, not evidence that Consumption was unavailable. Recovery did not identify the first internal server error's cause.

### Section 2.7 — CD permissions on existing resources — 2026-10-11

- **Preflight:** Principal ID/trust matched FeedbackPulse production; CD roles 0, Environment Succeeded and Apps 0. GitHub Actions variables showed no repository/environment variables, so no `FEEDBACKPULSE_CD_ENABLED=true`. GitHub settings were unchanged.
- **Result:** Created all three assignments for `id-feedbackpulse-cd`'s principal ID. Read-back at `2026-10-11T07:05:37Z` matched the 3 roles, principal and resource scopes below. No resource-group/subscription-wide access or permission to grant roles.

| Role | Resource scope in RG `itcs355-u6688124` | Assignment ID |
|---|---|---|
| `AcrPush` | ACR `itcs355u6688124` | `7235dc20-8fda-4a25-9f2a-e259cbce17dc` |
| `Container Apps Operator` | Environment `feedbackpulse-env` | `4052ba78-31a5-4904-9198-207757d978c3` |
| `Managed Identity Operator` | Identity `id-feedbackpulse-pull` | `8b6c4def-1894-48fe-a5ed-88f75ea56f2e` |

- **Permission boundary:** The existing ACR uses `LegacyRegistryPermissions`, so AcrPush covers the whole registry, including lab repositories, not only `feedbackpulse`. ACR mode/admin-account settings were unchanged. The Environment role provides read/join access; the identity role allows attaching the existing pull identity. CD was not allowed to manage all Apps in the RG.
- **Post-check:** CD had only these 3 assignments. The pull identity still had one AcrPull role on the existing ACR. Trust was unchanged; no App/Job or `Container Apps Contributor` yet. No workflow/deployment or P01–P03 code changes.
- **Screenshot:** [Azure Portal — CD resource roles](../../reports/screenshots/p04-02-07-cd-resource-roles-2026-10-11.jpg) is a real capture showing the identity and three assignments, with only the account bar removed. Portal shortens long names in this viewport; full names/scopes were confirmed by the CLI read-back above. This does not prove successful CD deployment.
- **Limits:** `feedbackpulse-api` and its App Contributor assignment did not exist yet. CD needed access only to that App, not an RG-wide role. Consumption CPU quota remained unconfirmed because the earlier output listed only Dedicated cores. Role grants alone do not prove quota or runtime deployment permissions.

## 1. Scope and goal

Sections 1–4 preserve the original phase plan and reported checklist. Actual results, including narrower cleanup behavior, are described above and in the [operations guide](../../scripts/README.md).

### Expected result
Cloud deployment on **Azure Container Apps (Consumption plan)** with **GitHub Actions CI/CD** that tests code before deployment, handles secrets safely, meets the performance target in [Proposal §3](../../PROPOSAL.md#3-serving-pattern-and-requirements) and can **roll back** to a previous version when something goes wrong.

### P04 deliverables
1. **Azure Infrastructure & Configuration:**
   - Resource Group in Southeast Asia.
   - Azure Container Registry (ACR) or GitHub Container Registry (GHCR) for images tagged by commit SHA.
   - Azure Container Apps Environment (Consumption plan) configured for scale-to-zero (min replicas = 0).
   - 1.0 vCPU and 2.0 GiB RAM, based on P03's 645.8 MiB measurement, with memory headroom and a USD 15 budget.
   - Liveness probe at `/health`; readiness probe at `/ready`.
   - Inject `SERVICE_TOKEN` only through Container App Secrets / Environment Variables, never bake it into the image.
2. **Automated CI Workflow (GitHub Actions):**
   - Run Linter (`ruff check`) and Test Suite (`uv run pytest`), all 55/55 tests, on Pull Request or Push.
   - Block merge or deployment if tests/lint fail.
3. **Automated CD & Safe Release Workflow:**
   - Build with `Dockerfile` (multi-stage, non-root `appuser`, model artifact baked in).
   - Use an immutable Git commit SHA image tag and push to the Registry.
   - Deploy a new Azure Container Apps revision and switch traffic.
4. **Latency Benchmark & SLA Verification:**
   - Measure end-to-end p95 latency at concurrency = 2 with a versioned test set (target <= 3 seconds, Proposal §3).
   - Measure cold-start time separately, from 0 replicas until the first request can be served.
5. **Rollback Verification:**
   - Test and record traffic rollback to a previous Azure Container Apps revision without taking the service down.
6. **Teardown & Cleanup Automation:**
   - A script to remove all resources after testing and avoid extra costs.

### Outside P04
- Dashboard and alert setup (P05).
- Cloud failure simulation (originally planned for P05; the new experiment was later canceled; existing experiments remain separate).
- Complete model card and demo rehearsal (P06).

---

## 2. Tasks and responsibilities

| Task ID | Work | Status | Done when | Check |
|---|---|---|---|---|
| **P04-T01** | **Infrastructure provisioning, cloud adapter and configuration** | `done` | Separate cloud adapter in `cloudlayer/` (`adapter.py`, `azure_adapter.py`), `cloudlayer/containerapp.template.yaml` (1.0 vCPU / 2.0 GiB, min=0, max=3, probes `/health` & `/ready`, secret token), `cloudlayer/render_config.py` and `Makefile` automation | `make dry-run` passes; `make portability-audit` passes 100%; `uv run pytest tests/test_cloudlayer.py` passes 12/12 (70/70 overall); no credentials found in the repo |
| **P04-T02** | **GitHub Actions CI pipeline (automated testing)** | `done` | Two-stage `.github/workflows/ci.yml`: job `test` (Ruff, portability audit, template validation, 70 pytest tests) and job `build` (Docker buildx, commit SHA tag, live smoke test) | Push/PR test: workflow passes; deliberate failing test: workflow blocks deployment |
| **P04-T03** | **Automated CD and deployment workflow** | `done` | `.github/workflows/cd.yml` builds from `Dockerfile`, tags with commit SHA, pushes to ACR through Azure OIDC, renders the template, deploys a new Azure Container Apps revision and smoke-tests the live endpoint | GitHub Actions deploy succeeds; Azure Container Apps creates a new revision with 100% traffic |
| **P04-T04** | **Cloud smoke test and latency benchmark** | `done` | Public HTTPS checks (200, 401, 400, 422 and 510-token boundary) pass 12/12; k6 with 2 concurrent requests gets p95 = 0.213s (target <= 3.0s, Proposal §3 SLA met, error rate 0.0%) | `scripts/cloud_check.py` (`make smoke-test`) records `reports/P04-cloud-check.json`; `loadtest/k6.js` (`make load-test`) passes all k6 thresholds, p95<3000ms |
| **P04-T05** | **Test and verify rollback** | `done` | Route traffic back to a working previous revision without rebuilding, using Azure Container Apps Native Revision Routing (`make rollback REV=...` and `make verify-rollback`) | `scripts/verify_rollback.py` (`make verify-rollback`) confirms 100% traffic to baseline `feedbackpulse-api--2zaws5o` in 17.52 seconds; `/health`, `/ready`, `/predict` return 200 OK; evidence in `reports/P04-rollback-evidence.json` |
| **P04-T06** | **Teardown script and P04 evidence** | `done` | `teardown.sh` / `make teardown` removes all cloud resources with a dry-run mode; `reports/P04-evidence.md` collects CI, deployment run, latency, rollback and teardown verification | Review evidence, CI links and test output; teardown dry-run/review mode passes |

---

## 3. Technical decisions and trade-offs (Decisions & Constraints)

1. **Resource sizing:**
   - *P02 & P03 data:* macOS peak RSS was 783 MiB (P02); real Docker-container RSS was 645.8 MiB (P03).
   - *Decision:* **1.0 vCPU and 2.0 GiB RAM** on Azure Container Apps Consumption.
   - *Reason:* More headroom than 1.0 GiB, which risks OOM with overlapping requests, and cheaper than the 2 vCPU / 4 GiB assumption in [Proposal §6](../../PROPOSAL.md#6-cost-estimate), keeping the plan within USD 15 per 30 days.
2. **Auto-scaling:**
   - `minReplicas = 0` enables scale-to-zero when idle to save costs.
   - `maxReplicas = 3` limits spending from traffic spikes.
3. **Separate probes:**
   - Liveness Probe (`GET /health`): HTTP 200, interval 15s, checks that the uvicorn process is alive.
   - Readiness Probe (`GET /ready`): HTTP 200, failureThreshold 3, checks that the model loaded and is ready for inference.
4. **Zero Secrets in Image Layers:**
   - Registry images contain only code and the verified model.
   - Inject `SERVICE_TOKEN` through Azure Container Apps Secrets only.
5. **Rollback strategy:**
   - Use Azure Container Apps Native Revision Management to route 100% of traffic to the previous revision.
   - Do not delete the repo or manually redeploy an old Git commit; revision routing allows rollback within seconds.

---

## 4. P04 deployment verification checklist

- [x] **CI pipeline:** GitHub Actions runs `ruff check` and all `pytest` tests successfully (70/70, 100%) on pull request/push.
- [x] **CI blocker:** Changes with bugs or failing tests cannot deploy.
- [x] **CD deployment:** Build a non-root image and deploy successfully to Azure Container Apps.
- [x] **Cloud smoke tests:** The public HTTPS URL follows the API contract (200, 401, 400, 422 with the 510-token boundary, 503).
- [x] **Latency target:** End-to-end p95 <= 3.0s at 2 concurrent requests after model loading, with cold start recorded separately.
- [x] **Rollback tested:** Evidence confirms traffic returned to the previous revision (`make verify-rollback`).
- [x] **Teardown ready:** A script removes all Azure resources (`scripts/teardown.sh` / `make teardown`).
- [x] **Evidence collected:** Results recorded in `reports/P04-evidence.md` and `overview-plan.md` updated.

