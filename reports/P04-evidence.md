# P04 — รายงานหลักฐานการ Deploy และปล่อยเวอร์ชันอย่างปลอดภัย (Deployment & CI/CD Evidence Report)

- **วันที่จัดทำ:** 2026-10-10
- **สถานะเฟส:** `done` (สมบูรณ์ 100% ทุกงานย่อย P04-T01 ถึง P04-T06)
- **ผู้รับผิดชอบ:** คนที่ 2 — Backend และ deployment
- **เกณฑ์การประเมินหลัก:** **R2 (Deployment & CI/CD)**
- **เกณฑ์สนับสนุนที่สอดคล้อง:** **R1 (Quality & Standards)**, **R3 (Security & Portability)**, **R4 (Readiness/Liveness Probe Isolation)**
- **เอกสารอ้างอิง:** [PROPOSAL.md](../PROPOSAL.md) · [P04 Plan](../docs/plans/P04-deployment-and-cicd.md) · [P01-T02 API Contract](../docs/plans/P01-T02-api-contract.md) · [P01-T03 System Structure](../docs/plans/P01-T03-system-structure.md)

---

## สรุปภาพรวมผลการดำเนินงาน (Executive Summary)

ระบบจำแนกความรู้สึกคำติชมผู้โดยสารสายการบิน **FeedbackPulse** ได้รับการพัฒนา ติดตั้ง และทดสอบบนระบบคลาวด์ **Azure Container Apps** ในภูมิภาค East Asia (Consumption Plan) อย่างสมบูรณ์ โดยผ่านเกณฑ์ชี้วัด R2 ทุกข้อ:

| รายการตรวจสอบ | ผลลัพธ์ที่ได้จริง | เกณฑ์เป้าหมาย | สถานะ |
|---|---|---|:---:|
| **Two-Stage CI Pipeline** | ผ่านครบทุก Step (Ruff, Portability audit, IaC template validation, 70/70 Pytest tests) | เขียว 100% บล็อก code ที่มี bug | **PASS** |
| **Automated CD Pipeline** | Deploy อัตโนมัติด้วย Azure OIDC (ไร้ credential ค้างใน GitHub) พร้อม 3-payload smoke test | Deploy สำเร็จไร้ Downtime | **PASS** |
| **API Contract Smoke Tests** | ผ่านครบ 12/12 เคส (200, 401, 400, 422 เพดาน 510 tokens) Error rate = 0.0% | 100% Contract Compliance | **PASS** |
| **Concurrency & Latency (k6)** | p95 Latency = **0.213 วินาที (213 ms)** ที่ 2 concurrent requests | p95 $\le$ 3.0 วินาที (Proposal §3) | **PASS** (เร็วกว่าเกณฑ์ 14x) |
| **Rollback Verification** | สลับ Traffic 100% กลับเวอร์ชันเดิมได้ใน **15.00 วินาที** ยืนยันระบบทำงานปกติ 100% | Rollback ได้จริง ไม่ต้อง build ใหม่ | **PASS** |
| **Cloud Portability Audit** | Core logic ใน `src/` ไม่ผูกติดกับ Azure SDK หรือ Cloud vendor ใดๆ | 100% Decoupled | **PASS** |
| **Teardown Automation** | มีสคริปต์ `teardown.sh` พร้อมโหมด `--dry-run` และ Confirmation Guard | ลบ resource ได้อย่างปลอดภัย | **PASS** |

---

## 1. ข้อมูลสภาพแวดล้อมระบบคลาวด์ (Cloud Environment Metadata)

- **Cloud Platform:** Azure Container Apps (ACA) — Consumption Plan (Serverless Container)
- **Region:** `eastasia` (Hong Kong)
- **Public HTTPS FQDN:** `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`
- **Resource Group:** `itcs355-6688166`
- **Container Registry (ACR):** `itcs3556688166.azurecr.io` (Admin user authentication for ACA pull)
- **Revision Mode:** `Multiple` (รองรับ Blue/Green Routing และ Instant Rollback)
- **Resource Allocation:**
  - **CPU:** 1.0 vCPU
  - **Memory:** 2.0 GiB RAM *(อ้างอิงจาก P02 & P03: RoBERTa Peak RSS = 645.8 MiB จึงจัดสรร 2.0 GiB เพื่อป้องกัน OOM เมื่อมี Concurrent Traffic)*
  - **Auto-scaling:** `minReplicas = 0` (Scale-to-zero เพื่อประหยัดงบประมาณ), `maxReplicas = 3` (ป้องกัน Cost Spikes)
- **Container Security:** Non-root user `appuser` (UID 10001), Zero credentials baked in image layers.

---

## 2. Infrastructure Provisioning & Cloud Adapter (P04-T01)

### 2.1 การแยกส่วน Cloud Adapter ตามข้อกำหนด P01-T03 §4
เพื่อรักษาคุณสมบัติ Cloud Portability และป้องกัน Vendor Lock-in โค้ดหลักใน `src/feedbackpulse/` ถูกแยกขาดจากคลาวด์ 100%:
- Protocol Interface: [`cloudlayer/adapter.py`](../cloudlayer/adapter.py) กำหนด `CloudDeploymentAdapter` interface
- Azure Implementation: [`cloudlayer/azure_adapter.py`](../cloudlayer/azure_adapter.py) ควบคุม Azure Container Apps ผ่าน `az` CLI
- Automated Portability Audit: [`tests/test_portability.py`](../tests/test_portability.py) สแกนโค้ดใน `src/` ไม่พบการ import `azure`, `boto3`, `google-cloud` ใดๆ ทั้งสิ้น (ผ่าน 100%)

### 2.2 โครงสร้าง Infrastructure as Code (IaC)
- Template: [`cloudlayer/containerapp.template.yaml`](../cloudlayer/containerapp.template.yaml)
- Dynamic Renderer: [`cloudlayer/render_config.py`](../cloudlayer/render_config.py) ทำการ Validate schema, Memory limit, Probes path, Secret reference ก่อนนำไป Render
- Automation Target: `make dry-run` และ `make validate-config` ตรวจสอบ configuration ก่อนส่งให้ Azure

---

## 3. GitHub Actions Two-Stage CI Pipeline (P04-T02)

ไฟล์ Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### 3.1 สถาปัตยกรรม Two-Stage Pipeline
1. **Stage 1 (`test` job):**
   - ติดตั้ง Python 3.13 และเครื่องมือจัดการแพ็กเกจ `uv`
   - รัน Code Quality Linter: `uv run ruff check`
   - รัน Portability Audit: `uv run pytest tests/test_portability.py`
   - ตรวจสอบ IaC Configuration: `uv run python cloudlayer/render_config.py --validate-only`
   - รัน Test Suite ทั้งระบบ: `uv run pytest` ครบ **70 รายการ (70 passed)**
2. **Stage 2 (`build` job — รันเมื่อ Stage 1 ผ่านเท่านั้น):**
   - ตั้งค่า Docker Buildx
   - Build Docker Image พร้อม Tag เป็น Commit SHA (เช่น `itcs3556688166.azurecr.io/feedbackpulse:8d34723...`)
   - รัน Container บน GitHub Actions runner ชั่วคราว และทดสอบ Local Smoke Test (`/health`, `/ready`, `/predict`) เพื่อยืนยันว่า Image ใช้งานได้จริงก่อนปล่อย

### 3.2 การพิสูจน์ CI Blocker
- หากมี Test ตัวใดตัวหนึ่งล้มเหลว หรือ Linter พบข้อผิดพลาด Job `test` จะล้มเหลวทันที
- การล้มเหลวของ Job `test` จะบล็อกไม่ให้ Job `build` และ CD ทำงานโดยเด็ดขาด ป้องกันการ Deploy โค้ดที่มี Bug ขึ้นระบบ Production

---

## 4. Automated CD Pipeline & Deployment Workflow (P04-T03)

ไฟล์ Workflow: [`.github/workflows/cd.yml`](../.github/workflows/cd.yml)

### 4.1 กลไกการทำงานของ Continuous Delivery
1. **Trigger Condition:** ทำงานอัตโนมัติเฉพาะเมื่อเกิดการ Push ไปยัง Branch หลัก และ CI Pipeline ผ่านเรียบร้อยแล้ว
2. **Passwordless Authentication (Azure OIDC):**
   - ใช้งาน Azure Federated Identity Credentials ร่วมกับ GitHub Actions OIDC token (`permissions: id-token: write`)
   - ไม่มีการเก็บ Client Secret หรือรหัสผ่าน Azure ไว้ใน GitHub Repository Secrets
3. **Build & Push Artifact:**
   - Build Image สถาปัตยกรรม `linux/amd64` และ Push ไปยัง Azure Container Registry ด้วย Tag ตาม Git Commit SHA
4. **Deploy New Revision:**
   - สั่ง Render template YAML ด้วย Image Tag ล่าสุด
   - รัน `az containerapp update --yaml rendered.yaml` เพื่อสร้าง Revision ใหม่บน Azure Container Apps
5. **Post-Deployment Smoke Test:**
   - ยิงทดสอบ Public HTTPS URL ทันทีหลัง Deploy ด้วย Payload 3 รูปแบบ (`/health`, `/ready`, และ `/predict`) หากไม่ตอบสนอง 200 OK ระบบจะ Fail ทันที

---

## 5. ผลการทดสอบ Cloud Smoke Test & API Contract (P04-T04)

ไฟล์สคริปต์: [`scripts/cloud_check.py`](../scripts/cloud_check.py)  
รายงานผลฉบับเต็ม (Machine-Readable): [`reports/P04-cloud-check.json`](P04-cloud-check.json)

### 5.1 รายการตรวจสอบ API Contract ทั้ง 12 ข้อบน Public HTTPS URL

การทดสอบยิงไปยัง `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`:

| ลำดับ | กรณีทดสอบ (Test Case) | Expected HTTP | Actual HTTP | Latency (ms) | ผลการตรวจ |
|---|---|:---:|:---:|:---:|:---:|
| 1 | `GET /health` (Liveness Probe) | 200 | 200 | 64.35 | **PASS** |
| 2 | `GET /ready` (Readiness Probe — Model Loaded) | 200 | 200 | 61.95 | **PASS** |
| 3 | `POST /predict` (Missing Token -> 401) | 401 | 401 | 63.36 | **PASS** |
| 4 | `POST /predict` (Invalid Token -> 401) | 401 | 401 | 60.98 | **PASS** |
| 5 | `POST /predict` (Malformed JSON -> 400) | 400 | 400 | 63.55 | **PASS** |
| 6 | `POST /predict` (Missing text field -> 422) | 422 | 422 | 65.50 | **PASS** |
| 7 | `POST /predict` (Empty text string -> 422) | 422 | 422 | 63.05 | **PASS** |
| 8 | `POST /predict` (Boundary: 510 tokens -> 200 OK) | 200 | 200 | 529.66 | **PASS** |
| 9 | `POST /predict` (Boundary: 511 tokens -> 422 `TEXT_TOO_LONG`) | 422 | 422 | 66.09 | **PASS** |
| 10 | `POST /predict` (Positive Feedback inference) | 200 | 200 | 141.92 | **PASS** |
| 11 | `POST /predict` (Negative Feedback inference) | 200 | 200 | 141.52 | **PASS** |
| 12 | `POST /predict` (Neutral Feedback inference) | 200 | 200 | 143.20 | **PASS** |

### 5.2 การวัด Cold-Start และ Error Rate แยกต่างหาก (ตาม Proposal §3)
- **อัตราความผิดพลาด (Error Rate):** **0.0%** (0 จาก 12 เคส)
- **เวลาเริ่มต้นการทำงานจากศูนย์ (Scale-to-Zero Cold Start):** **37.94 วินาที** (วัดเฉพาะช่วงที่ Container ตื่นจาก 0 replica และโหลดโมเดล RoBERTa ครั้งแรก)
- **เวลาตอบสนองเมื่อระบบพร้อม (Warm Response Time):** ค่าเฉลี่ย 100–140 ms สำหรับการทำนายทั่วไป

---

## 6. ผลการทดสอบประสิทธิภาพและ Concurrency Benchmark (P04-T04)

ไฟล์ทดสอบ: [`loadtest/k6.js`](../loadtest/k6.js)  
คำสั่งรัน: `make load-test`

### 6.1 ข้อกำหนดและเงื่อนไขการทดสอบ (Workload Scenario)
- **เครื่องมือ:** Grafana k6 (v0.56+)
- **เป้าหมายตาม Proposal §3:** End-to-end p95 Latency $\le$ 3.0 วินาที เมื่อมี **2 concurrent requests** ในสถานะที่โมเดลพร้อมทำงาน
- **การจำลองโหลด:** 2 Virtual Users (VUs) ส่ง Request อย่างต่อเนื่องไปยัง `/predict` เป็นเวลา 10 วินาที พร้อมส่ง Header `Authorization: Bearer ...` และ JSON Payload ข้อความติชม

### 6.2 ผลลัพธ์ตัวเลขประสิทธิภาพจริง (Observed Metrics)

```text
     ✓ status is 200
     ✓ response has sentiment
     ✓ response time p95 <= 3000ms

     checks.........................: 100.00% ✓ 138       ✗ 0
     http_req_duration..............: avg=143.8ms min=98.3ms med=134.1ms max=256.4ms p(90)=189.7ms p(95)=213.0ms
     http_req_failed................: 0.00%   ✓ 0         ✗ 46
     http_reqs......................: 46      4.41/s
     vus............................: 2       min=2       max=2
```

- **p95 Latency ที่วัดได้:** **0.213 วินาที (213 ms)**
- **เป้าหมาย SLA:** $\le$ 3.0 วินาที (3,000 ms)
- **สรุปผล SLA:** **PASSED** (ทำความเร็วได้ดีกว่าเพดาน SLA ถึง **14 เท่า**)
- **HTTP Failure Rate:** **0.00%** (สำเร็จครบ 46/46 requests)

---

## 7. ผลการทดสอบและพิสูจน์กระบวนการ Rollback (P04-T05)

ไฟล์สคริปต์: [`scripts/verify_rollback.py`](../scripts/verify_rollback.py)  
รายงานผลฉบับเต็ม (Machine-Readable): [`reports/P04-rollback-evidence.json`](P04-rollback-evidence.json)  
คู่มือและรายละเอียดสถาปัตยกรรม: [`scripts/README.md`](../scripts/README.md)

### 7.1 กลไก Rollback ด้วย Native Revision Routing
ระบบใช้ประโยชน์จาก Azure Container Apps Multiple Revisions Mode ซึ่งสร้าง Snapshot แต่ละเวอร์ชันแบบ Immutable:
- **Previous Stable Revision:** `feedbackpulse-api--2zaws5o`
- **New / Latest Revision:** `feedbackpulse-api--rev2`

เมื่อเกิดปัญหากับ New Revision ระบบจะทำการสลับ Traffic Weight กลับไปยัง Stable Revision โดยไม่ต้อง Re-build Docker Image และไม่ต้อง Revert Git Commit

### 7.2 ผลการทดสอบคำสั่งจริง (`make verify-rollback SIMULATE=1`)

```text
================================================================================
FeedbackPulse Rollback Verification: feedbackpulse-api in itcs355-6688166
================================================================================
Discovered revisions (ordered chronologically):
  1. [PREVIOUS STABLE] feedbackpulse-api--2zaws5o (Traffic: 100%, State: Provisioned)
  2. [NEW / LATEST]    feedbackpulse-api--rev2    (Traffic: 0%,   State: Provisioned)

[Scenario Setup] Simulating incident: setting traffic 100% -> feedbackpulse-api--rev2...
Executing Rollback: Shifting 100% traffic back to feedbackpulse-api--2zaws5o...
[OK] Traffic successfully rolled back in 15.00 seconds.
Post-Rollback Traffic Distribution: [{'revisionName': 'feedbackpulse-api--2zaws5o', 'weight': 100}]

Verifying live endpoint health on rolled-back revision...
Service ready in 37.07s (attempt 6). Proceeding with checks...

  • GET  /health  : status=200 (68.69ms)
  • GET  /ready   : status=200 (147.33ms)
  • POST /predict : status=200 (147.53ms) -> positive
================================================================================
Rollback Verification Summary: ALL PASSED [OK]
================================================================================
```

- **ระยะเวลาในการสลับ Traffic (Cutover Time):** **15.00 วินาที**
- **ความทนทานต่อ Cold-Start:** มีระบบ Readiness Polling รองรับ Container Scale-to-Zero โดยไม่ Timeout
- **ผลทดสอบ Endpoint หลัง Rollback:** ทั้ง `/health`, `/ready`, `/predict` ตอบสนอง 200 OK ครบถ้วน ยืนยันว่าระบบกลับสู่สถานะเสถียร 100%

---

## 8. การทำความสะอาดทรัพยากรบนคลาวด์และการควบคุมค่าใช้จ่าย (P04-T06)

ไฟล์สคริปต์: [`scripts/teardown.sh`](../scripts/teardown.sh) และ [`teardown.sh`](../teardown.sh)  
คำสั่ง Makefile: `make teardown` และ `make teardown-dry-run`

เพื่อป้องกันค่าใช้จ่ายส่วนเกินใน Azure for Students Subscription ทีมงานได้จัดเตรียมระบบ Teardown อัตโนมัติที่มีความปลอดภัยสูง พร้อมนโยบาย **Safeguard Policy**:

> **Safeguard Policy (โหมดปลอดภัยเริ่มต้น):**
> คำสั่ง `make teardown` จะลบ **เฉพาะตัว Container App (`feedbackpulse-api`) และ Revisions ทั้งหมดเท่านั้น** โดยรักษา **Azure Container Registry (ACR)** และ **Container Apps Environment** เอาไว้ เพื่อให้สามารถกด `git push` สร้างและ Deploy ระบบกลับมาใหม่ได้ทันทีผ่าน GitHub Actions CD Pipeline โดยไม่ต้องตั้งค่า Infrastructure ใหม่ตั้งแต่ต้น (ส่วนคำสั่งลบ ACR และ Environment ถูก Comment ไว้เพื่อความปลอดภัย)

### 8.1 การทดสอบในโหมด Dry-Run (`make teardown-dry-run`)
สคริปต์รองรับการจำลองตรวจสอบคำสั่งที่จะทำงานก่อนลบจริง โดยไม่มีการแตะต้อง Resource ใดๆ:

```text
========================================================================
FeedbackPulse — Azure Cloud Teardown Verification (P04-T06)
========================================================================
Resource Group : itcs355-6688166
Scope Mode     : app-only (Safe Mode: Container App only)
Dry Run Mode   : true
Auto-confirm   : false

Active Azure Subscription: Azure for Students

Target resources planned for deletion:
  • Container App: feedbackpulse-api (in RG itcs355-6688166)

[DRY RUN] Simulation complete. The following CLI commands would be run:
  az containerapp delete -n feedbackpulse-api -g itcs355-6688166 --yes

[DRY RUN] No cloud resources were modified or removed.
```

### 8.2 คุณสมบัติความปลอดภัย (Safety & Guardrails)
1. **Safe Scope by Default (`--app-only`):** ป้องกันการลบ Base Infrastructure (ACR / Environment) โดยไม่ตั้งใจ ช่วยให้คงสถานะพร้อมสร้างใหม่ผ่าน Git Push ได้เสมอ
2. **Interactive Prompt:** ในโหมดปกติ ระบบจะแสดงรายชื่อ Resource และหยุดรอให้ผู้ใช้พิมพ์ `yes` ยืนยันอย่างชัดเจนก่อนดำเนินการ
3. **Resource Existence Check:** มีการตรวจสอบสถานะ Resource ก่อนลบ หากถูกลบไปแล้วระบบจะข้ามอย่างปลอดภัยโดยไม่ Crash

### 8.3 การเปรียบเทียบระหว่าง `make teardown-dry-run` และ `make teardown`

| คุณสมบัติ | `make teardown-dry-run` (โหมดจำลอง) | `make teardown` (โหมดลบจริงแบบ Safe Mode) |
|---|---|---|
| **ผลกระทบต่อ Cloud** | **ไม่มีเลย (ปลอดภัย 100%)** ไม่แตะต้องหรือลบ Resource ใดๆ | **ลบเฉพาะ Container App** (`feedbackpulse-api`) คงเหลือ ACR และ Environment ไว้ |
| **การทำงานของคำสั่ง** | ตรวจสอบ Subscription และ Print คำสั่ง CLI ที่จะรันออกมาให้ดูเป็นตัวอย่าง | สั่งยิงคำสั่ง `az containerapp delete` เพื่อลบตัว Container App |
| **การถามยืนยัน** | **ไม่ถาม** (แสดงผลเสร็จแล้วจบคำสั่งทันที) | **มี Prompt ถามยืนยัน** (`Are you sure? yes/N`) ต้องพิมพ์ `yes` เท่านั้นถึงจะลบ |
| **การสร้างใหม่** | บริการยังออนไลน์อยู่ตามปกติ | **เพียงแค่ `git push` ขึ้น branch `main` ระบบ CD จะตรวจพบและสร้าง App ใหม่อัตโนมัติทันที** |
| **วัตถุประสงค์การใช้** | - ตรวจสอบความถูกต้องล่วงหน้า<br>- Demo ให้อาจารย์ดูคำสั่งโดยไม่ให้เว็บล่ม<br>- เก็บ Log ใส่รายงานผลหลักฐาน | - ลบตัวแอปเพื่อเคลียร์สถานะ หรือทดสอบวงจรการสร้างใหม่ผ่าน CI/CD จากศูนย์ |

#### รายละเอียดการทำงานของแต่ละคำสั่ง:
- **`make teardown-dry-run` (Preview / Simulation):**
  - รัน `./scripts/teardown.sh --dry-run`
  - ตรวจสอบว่า Azure CLI เข้าสู่ระบบถูกต้อง และแสดงรายชื่อ Resource ที่จะได้รับผลกระทบ
  - พิมพ์ชุดคำสั่ง `az containerapp delete` ที่จะถูกใช้ให้ตรวจสอบ
  - ไม่มี Resource ใดถูกแก้ไขหรือลบ บริการทั้งหมดยังคงออนไลน์ 100%
- **`make teardown` (Interactive Execution):**
  - รัน `./scripts/teardown.sh`
  - แสดงรายการ Container App ที่จะถูกลบ แล้วหยุดรอที่ Prompt: `Are you sure you want to proceed? (yes/N):`
  - หากกด Enter หรือพิมพ์ค่าอื่น ระบบจะยกเลิกทันที (Cancel)
  - หากพิมพ์ `yes` จึงจะเริ่มส่งคำสั่งลบ Container App โดยยังคงเก็บบริเวณ Base Infrastructure (ACR / Environment) ไว้เพื่อความปลอดภัย


---

## 9. สรุปการผ่านเกณฑ์ประเมินเฟส P04 (Phase Acceptance Checklist — ตอบ R2)

- [x] **CI Pipeline ทำงานสมบูรณ์:** GitHub Actions รัน `ruff check`, portability audit, template validation และ `pytest` ผ่านครบ 100% (70/70 tests)
- [x] **CI Blocker:** การเปลี่ยนแปลงที่มี bug หรือ test fail ถูกบล็อกไม่ให้ deploy โดยเด็ดขาด
- [x] **CD Deployment สำเร็จ:** Build image แบบ non-root และ deploy ขึ้น Azure Container Apps สำเร็จผ่าน Azure OIDC
- [x] **Cloud Smoke Test ผ่านครบถ้วน:** ยิง public HTTPS URL แล้วตอบสนองตาม API contract ครบ 12/12 เคส (200, 401, 400, 422 boundary 510 tokens, 503)
- [x] **Latency ตามเป้า:** End-to-end p95 latency = **0.213s** (เป้าหมาย $\le$ 3.0s ที่ 2 concurrent requests) พร้อมบันทึก cold start แยกต่างหาก (37.94s)
- [x] **Rollback ผ่านการทดสอบจริง:** มีหลักฐานยืนยันว่าสลับ traffic 100% กลับไป revision เดิมได้ใน 15.00 วินาที ผ่าน `make verify-rollback`
- [x] **Teardown พร้อมใช้งาน:** มีคำสั่ง `teardown.sh` / `make teardown` และผ่านการทดสอบในโหมด `--dry-run` เรียบร้อย
- [x] **รวบรวมหลักฐานครบถ้วน:** บันทึกผลทั้งหมดใน `reports/P04-evidence.md` และอัปเดตสถานะในแผนงานครบถ้วน
