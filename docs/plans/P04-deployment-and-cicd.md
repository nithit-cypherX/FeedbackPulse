# P04 — Deploy และปล่อยเวอร์ชันอย่างปลอดภัย (Deployment & CI/CD)

- **สถานะ:** `planned`
- **เจ้าของ:** คนที่ 2 — Backend และ deployment
- **แผนหลัก:** [Overview](../../overview-plan.md) · **ขอบเขต:** [Proposal](../../PROPOSAL.md) · **เกณฑ์ที่ตอบสนอง:** **R2 (Deployment & CI/CD)**
- **ข้อตกลงที่ต้องทำตาม:** [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md) · [P02 Model pipeline](P02-model-pipeline.md) · [P03 Local backend](P03-local-backend.md)
- **หลักฐานที่จะส่งมอบ:** `reports/P04-evidence.md`

---

## 1. ขอบเขตและเป้าหมาย

### ผลที่ต้องได้
ระบบ Cloud Deployment บน **Azure Container Apps (Consumption plan)** พร้อมท่อ **CI/CD บน GitHub Actions** ที่ทดสอบโค้ดอัตโนมัติก่อน deploy, มีการจัดการ secrets อย่างปลอดภัย, วัดผลประสิทธิภาพตรงตามเป้าใน [Proposal §3](../../PROPOSAL.md#3-serving-pattern-and-requirements), และสามารถ **Rollback** กลับเวอร์ชันก่อนหน้าได้จริงเมื่อเกิดปัญหา เพื่อตอบโจทย์เกณฑ์ **R2** อย่างสมบูรณ์

### สิ่งที่ส่งมอบใน P04
1. **Azure Infrastructure & Configuration:**
   - Resource Group ในภูมิภาค Southeast Asia
   - Azure Container Registry (ACR) หรือ GitHub Container Registry (GHCR) สำหรับเก็บ image ที่ build จาก commit SHA
   - Azure Container Apps Environment (Consumption plan) ที่ตั้งค่า scale-to-zero (min replicas = 0)
   - Sizing ทรัพยากร 1.0 vCPU และ 2.0 GiB RAM (อิงจากผลวัด P03 ที่ 645.8 MiB เพื่อความปลอดภัยและคุมงบประมาณ USD 15)
   - Probe configuration: Liveness probe ชี้ไปที่ `/health` และ Readiness probe ชี้ไปที่ `/ready`
   - Secret injection: ส่ง `SERVICE_TOKEN` ผ่าน Container App Secrets / Environment Variables เท่านั้น (ห้าม bake เข้า image)
2. **Automated CI Workflow (GitHub Actions):**
   - รัน Linter (`ruff check`) และ Test Suite (`uv run pytest`) ครบ 55/55 รายการเมื่อมี Pull Request หรือ Push
   - บล็อกการ merge หรือ deploy ทันทีหาก test หรือ lint ไม่ผ่าน
3. **Automated CD & Safe Release Workflow:**
   - Build container image ด้วย `Dockerfile` (multi-stage, non-root `appuser`, model artifact baked-in)
   - Tag image ด้วย immutable tag (Git commit SHA) และ push ไปยัง Registry
   - Deploy revision ใหม่ไปยัง Azure Container Apps และสลับ traffic
4. **Latency Benchmark & SLA Verification:**
   - วัด end-to-end p95 latency ณ concurrency = 2 (เป้าหมาย <= 3 วินาทีตาม Proposal §3) ด้วยชุดทดสอบที่ versioned
   - วัด cold-start time (จาก 0 replica ถึงรับ request แรกได้) แยกเป็นอิสระ
5. **Rollback Verification:**
   - ทดสอบและบันทึกหลักฐานการ Rollback กลับ revision ก่อนหน้าบน Azure Container Apps ได้ทันทีโดยระบบไม่ล่ม
6. **Teardown & Cleanup Automation:**
   - Script สำหรับสั่งลบ resource ทั้งหมดหลังเสร็จสิ้นการทดสอบ เพื่อป้องกันค่าใช้จ่ายส่วนเกิน

### สิ่งที่ไม่รวมใน P04
- Dashboard และการตั้ง Alert แจ้งเตือน (อยู่ใน P05)
- การทดลองจำลอง failure บน cloud (Planned Failure ใน P05)
- Model card ฉบับสมบูรณ์และการซ้อม demo (อยู่ใน P06)

---

## 2. Tasks และการแบ่งงาน

| Task ID | งานที่ทำ | สถานะ | สิ่งที่ตรวจว่างานเสร็จ (Done when) | วิธีตรวจ (Check) |
|---|---|---|---|---|
| **P04-T01** | **กำหนด Infrastructure Provisioning, Cloud Adapter & Configuration** | `done` | แยก Cloud Adapter ใน `cloudlayer/` (`adapter.py`, `azure_adapter.py`), template `cloudlayer/containerapp.template.yaml` (1.0 vCPU / 2.0 GiB, min=0, max=3, probes `/health` & `/ready`, secret token), `cloudlayer/render_config.py`, และ `Makefile` automation | `make dry-run` ผ่านฉลุย, `make portability-audit` ผ่าน 100%, `uv run pytest tests/test_cloudlayer.py` ผ่าน 12/12 tests (ทั้งระบบ 70/70), ตรวจไม่พบ credentials ใน repo |
| **P04-T02** | **สร้าง GitHub Actions CI Pipeline (Automated Testing)** | `planned` | มี workflow `.github/workflows/ci.yml` รัน `ruff check` และ `pytest` ผ่าน 55/55 รายการใน runner | จำลอง push หรือ PR: workflow รันสำเร็จเขียวทั้งหมด; จำลอง test จงใจ fail: workflow บล็อกและห้าม deploy |
| **P04-T03** | **สร้าง Automated CD & Deployment Workflow** | `planned` | มี workflow `.github/workflows/cd.yml` ที่ build image จาก `Dockerfile`, tag ด้วย commit SHA, push ไปยัง registry, และ deploy revision ใหม่ไป Azure Container Apps | GitHub Actions deploy สำเร็จ และ Azure Container Apps สร้าง revision ใหม่พร้อม traffic 100% |
| **P04-T04** | **Smoke Test บน Cloud และวัด Latency Benchmark** | `planned` | ยิงทดสอบ public HTTPS URL ของ Container App ครบทุกเคส (200, 401, 400, 422 เพดาน 510 tokens) และวัด end-to-end p95 latency ที่ 2 concurrent requests ได้ <= 3.0 วินาที | รัน benchmark script บันทึก latency p50, p95, p99, error rate และ cold-start time ลงในรายงานหลักฐาน |
| **P04-T05** | **ทดสอบและพิสูจน์กระบวนการ Rollback** | `planned` | สามารถสลับ traffic กลับไป revision ก่อนหน้าที่ทำงานปกติได้อย่างสมบูรณ์ โดยไม่ต้อง build image ใหม่ | สั่ง rollback ผ่าน Azure CLI / Actions, ตรวจ revision active และยิงทดสอบ API ยืนยันว่ากลับไปรุ่นเดิมสำเร็จ |
| **P04-T06** | **สร้าง Teardown Script และสรุปหลักฐาน P04-evidence** | `planned` | มีคำสั่ง `teardown.sh` ที่ลบ resource บน cloud ครบถ้วน พร้อมเอกสาร `reports/P04-evidence.md` รวบรวมผล CI, deployment run, latency numbers, และ rollback evidence | ตรวจสอบเอกสารหลักฐาน ลิงก์ CI run, output การทดสอบ และทดสอบคำสั่ง teardown ใน dry-run / review mode |

---

## 3. การตัดสินใจทางเทคนิคและข้อแลกเปลี่ยน (Decisions & Constraints)

1. **การกำหนดขนาด Resource (Sizing):**
   - *ข้อมูลจาก P02 & P03:* ในเครื่อง macOS วัด peak RSS ได้ 783 MiB (P02), ใน Docker container รันจริงวัด RSS ได้ 645.8 MiB (P03)
   - *การตัดสินใจ:* กำหนด **1.0 vCPU และ 2.0 GiB RAM** บน Azure Container Apps Consumption plan
   - *เหตุผล:* ปลอดภัยกว่า 1.0 GiB (ซึ่งอาจเสี่ยง OOM หากมี concurrent requests ซ้อนกัน) และประหยัดกว่าสมมติฐาน 2 vCPU / 4 GiB ใน [Proposal §6](../../PROPOSAL.md#6-cost-estimate) ทำให้ค่าใช้จ่ายอยู่ในกรอบงบประมาณ USD 15 ต่อ 30 วัน
2. **การตั้งค่า Auto-scaling:**
   - `minReplicas = 0` เพื่อ scale-to-zero เมื่อไม่มี request ช่วยประหยัดงบประมาณ
   - `maxReplicas = 3` เพื่อป้องกัน traffic spike ดูดงบประมาณจนเกินเพดาน
3. **การแยก Probes:**
   - Liveness Probe (`GET /health`): HTTP status 200, interval 15s (ตรวจว่า uvicorn process ยังมีชีวิต)
   - Readiness Probe (`GET /ready`): HTTP status 200, failureThreshold 3 (ตรวจว่าโหลดโมเดลสำเร็จและพร้อม infer)
4. **Zero Secrets in Image Layers:**
   - Image ที่ push ไป registry มีเฉพาะโค้ดและโมเดลที่ verify แล้ว
   - `SERVICE_TOKEN` ต้องถูกใส่ผ่าน Azure Container Apps Secrets เท่านั้น
5. **Rollback Strategy:**
   - ใช้ Native Revision Management ของ Azure Container Apps ในการ route traffic 100% กลับไปยัง revision เดิม
   - ไม่ใช้วิธีลบ repo หรือ deploy git commit ย้อนหลังแบบ manual เพื่อให้ rollback ได้เร็วภายในไม่กี่วินาที

---

## 4. เกณฑ์การผ่านเฟส P04 (Phase Acceptance Checklist — ตอบ R2)

- [ ] **CI Pipeline ทำงานสมบูรณ์:** GitHub Actions รัน `ruff check` และ `pytest` ผ่านครบ 100% (55/55 tests) บน pull request/push
- [ ] **CI Blocker:** การเปลี่ยนแปลงที่มี bug หรือ test fail ต้องถูกบล็อกไม่ให้ deploy โดยเด็ดขาด
- [ ] **CD Deployment สำเร็จ:** Build image แบบ non-root และ deploy ขึ้น Azure Container Apps สำเร็จ
- [ ] **Cloud Smoke Test ผ่านครบถ้วน:** ยิง public HTTPS URL แล้วตอบสนองตาม API contract (200, 401, 400, 422 boundary 510 tokens, 503)
- [ ] **Latency ตามเป้า:** End-to-end p95 latency <= 3.0s ที่ 2 concurrent requests เมื่อโมเดลโหลดแล้ว (พร้อมบันทึก cold start แยกต่างหาก)
- [ ] **Rollback ผ่านการทดสอบจริง:** มีหลักฐานยืนยันว่าสลับ traffic กลับไป revision เดิมได้สำเร็จ
- [ ] **Teardown พร้อมใช้งาน:** มี script ลบ resource ทั้งหมดบน Azure อย่างหมดจด
- [ ] **รวบรวมหลักฐานครบถ้วน:** บันทึกผลทั้งหมดใน `reports/P04-evidence.md` และอัปเดต `overview-plan.md`
