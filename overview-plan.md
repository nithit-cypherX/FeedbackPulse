# FeedbackPulse — Overview Plan

อัปเดตสถานะ: 2026-10-10 · P01: `in_progress` · **P02: `done`** · **P03: `done`** · **P04: `done`** · P05–P06: `planned`

ผมเสนอแบ่ง **FeedbackPulse เป็น 6 ส่วนหลัก** ครับ โดยใช้ skill `plan-and-track-work`: วางภาพรวมให้ครบก่อน แล้วค่อยแตกงานย่อยเฉพาะส่วนที่กำลังทำ เพื่อไม่ให้รายการงานเยอะเกินไป

ตอนนี้ repo ในเครื่องมี proposal, README และ `.gitignore` แล้ว แต่ยังไม่มีโค้ดระบบ ดังนั้นแผนด้านล่างคือ **งานที่เสนอจะทำ ไม่ใช่งานที่เสร็จแล้ว**

## ภาพรวม 6 ส่วน

อิงจาก [เกณฑ์ capstone ของอาจารย์](https://github.com/pasdptt/public_teaching_mlaiops/blob/2e29fae/course/project/project-brief.md) และขอบเขต FeedbackPulse ที่เราตกลงกัน:

| ส่วน | เราจะทำอะไร | ถือว่าจบเมื่อ |
|---|---|---|
| **P01 — ตกลงแบบระบบและแบ่งหน้าที่** | กำหนด API ว่ารับอะไร ส่งอะไรกลับ และจัดโครงสร้างตามกติกาแยก core, configuration และ cloud adapter พร้อมแบ่งเจ้าของงาน | ทีมเข้าใจตรงกัน มีแบบระบบสำหรับ architecture review และยืนยันสถานะอนุมัติ proposal ก่อนเริ่มพัฒนา |
| **P02 — เตรียม model และ pipeline ที่ทำซ้ำได้** | ใช้ pretrained model เวอร์ชันตายตัว จัดข้อมูล evaluation ให้มี version แล้วทำขั้นตอน evaluate → package → register พร้อม lineage | รัน workflow ซ้ำได้ และย้อนจาก model ที่ลงทะเบียนไปหา code, data, model revision และผล evaluation ได้ — ตอบ **R1** |
| [**P03 — ทำ backend ให้ใช้งานได้ในเครื่อง**](docs/plans/P03-local-backend.md) | รับข้อความภาษาอังกฤษ คืน sentiment, score และ model version มี validation, access control, health/readiness checks และ Docker | เรียก API ใน container ได้จริง พร้อม tests สำหรับข้อมูลปกติ ข้อมูลผิด และ model ไม่พร้อม — เป็นฐานของ **R2** |
| [**P04 — Deploy และปล่อยเวอร์ชันอย่างปลอดภัย**](docs/plans/P04-deployment-and-cicd.md) | ทำ CI/CD ทดสอบก่อน deploy ไป Azure Container Apps วัด latency และลอง rollback พร้อมจัดการ credentials, tags และงบตั้งแต่เริ่มใช้ cloud | การเปลี่ยนแปลงที่ผิดถูก tests บล็อก เวอร์ชันที่ผ่าน deploy ได้ และ rollback กลับเวอร์ชันเดิมได้จริง — ตอบ **R2** |
| **P05 — เฝ้าระวังและทดลองเหตุขัดข้อง** | ทำ dashboard และ alert แล้วจำลอง model artifact ใช้งานไม่ได้ตาม proposal ตรวจการแจ้งเตือน กู้ระบบ และเพิ่ม regression test | แสดงหลักฐานได้ครบว่า “เกิดอะไร → รู้ได้อย่างไร → กู้อย่างไร → ตรวจไม่ให้ปัญหาเดิมหลุดอีกอย่างไร” — ตอบ **R3–R4** |
| **P06 — ตรวจงานส่งและเตรียม demo** | รวบรวม README ที่ทำตามได้, model card หนึ่งหน้า, ต้นทุนต่อ 1,000 predictions, teardown และซ้อมนำเสนอ | เพื่อนทำตามจาก fresh clone ได้ หลักฐานครบ และทีมสาธิตระบบกับ failure พร้อมตอบคำถามได้ — ตอบ **R5 และ demo 15 คะแนน** |

**เราจะทดสอบและเก็บ evidence ไปพร้อมแต่ละส่วน** ส่วน P06 เป็นการตรวจความครบและจัดงานส่ง ไม่ใช่เพิ่งเริ่มเขียนหลักฐานหรือทดสอบทั้งหมดตอนท้ายครับ

## ฝั่ง ML กับฝั่ง Dev แบ่งอย่างไร

สำหรับทีม 3 คน ผมเสนอแบ่งความรับผิดชอบหลักตาม proposal เดิม:

- **คนที่ 1 — Model และ evaluation:** ดูแล P02 และส่วนเชื่อม model เข้า API
- **คนที่ 2 — Backend และ deployment:** ดูแล P03–P04
- **คนที่ 3 — Monitoring และ reliability:** ดูแล P05 รวมการรวบรวมต้นทุนและเอกสาร
- **ทุกคนร่วมกัน:** ตกลงแบบระบบใน P01 และเตรียม demo ใน P06

ยังไม่ผูกกับชื่อสมาชิกจนกว่าคุณจะแบ่งกันครับ และไม่ต้องรอคนแรกทำทุกอย่างเสร็จคนถัดไปถึงเริ่มได้ เช่น เมื่อตกลงรูปแบบ input/output แล้ว ฝั่ง API สามารถเริ่มทำส่วนรับส่งข้อมูลระหว่างที่อีกคนเตรียม model ได้

## สิ่งที่เราจะไม่เพิ่มเข้าไป

ยังคงขอบเขตเดิม: **backend เดียว, pretrained model เดียว, sentiment 3 กลุ่ม** ไม่มี frontend, CRM integration, chatbot หรือการ train/fine-tune เพิ่ม

แต่การไม่ train เอง **ไม่ได้แปลว่าข้ามงาน MLOps ฝั่ง model** เรายังต้อง version, evaluate, track และ register ให้ตรวจย้อนกลับได้ แผน P02 เป็นการปรับตามคำชี้แจงอาจารย์ที่คุณเล่ามา ไม่ใช่อ้างว่าเราทำซ้ำการฝึก model ต้นฉบับได้ เอกสารกลางยังใช้คำว่า *automated training* แต่ผู้ใช้แจ้งเมื่อ 2026-10-05 ว่าอาจารย์ยืนยัน proposal และขอบเขต pretrained ที่เราตกลงกันแล้ว

## งานปัจจุบัน: P01

แตกเป็นแค่ 3 งานย่อยก่อน:

1. **P01-T01 — ยืนยันขอบเขตและสถานะ proposal**

   ยืนยันขอบเขตและสถานะ proposal แล้ว ตามที่ผู้ใช้แจ้งเมื่อ 2026-10-05 ว่าอาจารย์ยืนยันแล้ว ส่วนรายชื่อเจ้าของงานยังไม่ได้บันทึกในเอกสาร ให้ทีมเป็นผู้ระบุ

2. **P01-T02 — ตกลงรูปแบบ API**

   ข้อตกลงหลักได้รับความเห็นชอบแล้ว ดู [API contract](docs/plans/P01-T02-api-contract.md) สำหรับ request/response, validation และ error handling · **สถานะเป็น `done` เฉพาะการตกลงแล้วเมื่อ 2026-10-07** เพราะเพดานความยาวข้อความยืนยันแล้วใน P02-T03 คือ 510 content tokens (รวม special tokens เป็น 512); ยังไม่ได้ implement หรือทดสอบ — การตรวจ boundary ผ่าน API อยู่ใน P03

3. **P01-T03 — วางโครงสร้างระบบและจุดตรวจ**

   สถานะ `done` เฉพาะการตกลงแผน — ยืนยันครบทั้ง 3 เรื่องแล้ว: หน้าที่ของระบบ โครงสร้างโฟลเดอร์กับกติกาเข้า Git และจุดตรวจพร้อมหลักฐาน R1–R5 ดู [System structure](docs/plans/P01-T03-system-structure.md) เพื่อใช้เป็นฐานสำหรับ architecture review; ยังไม่ได้ implement หรือทดสอบ

**การส่งต่องาน:** P01 บันทึกข้อตกลงไว้ครบแล้ว · **เพดานความยาวข้อความปิดแล้วใน P02-T03** จึงเหลือเพียง **รายชื่อเจ้าของงานใน [Proposal §7](PROPOSAL.md) ที่ยังเป็น `[Name]`** ที่ทำให้ยังไม่ปิด P01 ทั้งส่วน

## P02 เสร็จแล้ว 

ดู [P02 phase plan](docs/plans/P02-model-pipeline.md) · เจ้าของงาน: คนที่ 1

- `model_version` ที่ใช้งาน: `sentiment-6e7ff9fbc17c-0110c462` พร้อม lineage ใน `reports/registry/` · run ID `run-20261007T192531Z-d36357`
- ผล evaluation บน 14,640 แถว: **accuracy 0.8100 · macro-F1 0.7606** ([หลักฐาน ส่วนที่ 2](reports/P02-evidence.md))

**การส่งต่องาน:**
- **คนที่ 2 เริ่ม P03 ได้แล้ว** — อ่าน [interface ที่ล็อกไว้ (ส่วนที่ 9)](reports/P02-evidence.md) และ [การตัดสินที่เก็บ artifact (ส่วนที่ 7)](reports/P02-evidence.md) · เพดานข้อความอยู่ใน [P01-T02 §7](docs/plans/P01-T02-api-contract.md)
- **คนที่ 3 ต้องอ่าน** [หลักฐาน ส่วนที่ 7](reports/P02-evidence.md) — การสาธิต failure เปลี่ยนวิธี เพราะ artifact อยู่ใน image ไม่มี blob ให้ลบ

## P03 เสร็จแล้ว — ทำ backend ให้ใช้งานได้ในเครื่อง

ดู [P03 phase plan](docs/plans/P03-local-backend.md) · [หลักฐานการทดสอบและวัดค่า](reports/P03-evidence.md) · เจ้าของงาน: คนที่ 2
- สถานะ: `done` (ครบทั้ง 8 tasks T01–T08)
- Automated tests: **55/55 รายการผ่านครบ 100%** ใน ~7.68 วินาที
- Container image: `feedbackpulse:local` (digest `16030a4a4dbf`) รันเป็น non-root พร้อมโมเดลในตัว
- Smoke test: เรียก API ใน container จริงผ่านครบทุกเงื่อนไข (ปกติ, 401, 400, 422, token limit 510 tokens)
- Memory usage ใน container: **645.8 MiB** (ใช้ตัดสิน sizing ใน P04)
- Simulated failure: ตรวจสอบความพร้อม `/health` (200) แยกจาก `/ready` (503) สำเร็จ

## P04 เสร็จแล้ว — Deploy และปล่อยเวอร์ชันอย่างปลอดภัย

ดู [P04 phase plan](docs/plans/P04-deployment-and-cicd.md) · [หลักฐานการทดสอบและวัดค่า](reports/P04-evidence.md) · เจ้าของงาน: คนที่ 2 (Backend และ deployment)
- **สถานะ:** `done` (ครบทั้ง 6 tasks T01–T06 — ตอบเกณฑ์ **R2** สมบูรณ์ 100%)
- **Public Cloud URL:** `https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io`
- **Infrastructure:** Azure Container Apps (East Asia, Consumption Plan, 1.0 vCPU / 2.0 GiB, scale-to-zero)
- **CI/CD Pipelines:** GitHub Actions Two-stage CI (70/70 tests, Docker buildx) และ CD (Azure OIDC passwordless, zero downtime revision rollout)
- **Contract & Benchmark:** 12/12 API contract tests ผ่านฉลุย, k6 concurrency p95 latency = **0.213s** (เป้าหมาย $\le$ 3.0s, Error rate 0.0%)
- **Rollback:** Zero-downtime Blue/Green traffic shift 100% กลับ baseline revision ใน **15.00s** บันทึกใน `reports/P04-rollback-evidence.json`
- **Teardown & Cost:** มีคำสั่ง `scripts/teardown.sh` / `make teardown` พร้อมโหมด `--dry-run` ป้องกันค่าใช้จ่ายค้างคา
- **งานย่อยใน P04:**
  - P04-T01: **กำหนด Infrastructure Provisioning, Cloud Adapter & Configuration** (`done` — Cloud Adapter ใน `cloudlayer/` [`adapter.py`, `azure_adapter.py`], template `cloudlayer/containerapp.template.yaml`, `Makefile`, `make portability-audit` ผ่าน 100%, tests ผ่าน 70/70 tests)
  - P04-T02: **สร้าง GitHub Actions CI Pipeline** (`done` — `.github/workflows/ci.yml` โครงสร้าง Two-stage: Job `test` [Astral `uv`, `ruff check`, portability audit, template validation, 70/70 tests] และ Job `build` [Docker buildx `--platform linux/amd64`, commit SHA tagging, container smoke test `/ready` & `/predict`])
  - P04-T03: **สร้าง Automated CD & Deployment Workflow** (`done` — `.github/workflows/cd.yml` รันบน main branch, Azure OIDC `id-token: write` ไม่ใช้ long-lived keys, build & push image ด้วย commit SHA tag, render template, deploy Azure Container Apps และ smoke test ตรวจสอบ live endpoint)
  - P04-T04: **Smoke Test บน Cloud และวัด Latency Benchmark** (`done` — รัน `scripts/cloud_check.py` ผ่าน 12/12 contract tests และรัน `loadtest/k6.js` วัด p95 latency ที่ 2 concurrent requests ได้ 0.213s [เป้าหมาย <= 3.0s, Error rate 0.0%])
  - P04-T05: **ทดสอบและพิสูจน์กระบวนการ Rollback** (`done` — สร้าง `scripts/verify_rollback.py` และ `make verify-rollback`, พิสูจน์การสลับ traffic 100% กลับ baseline revision `feedbackpulse-api--2zaws5o` ใน 15.00s โดยไม่ต้อง rebuild image, ยิงตรวจ `/health`, `/ready`, `/predict` 200 OK และบันทึก `reports/P04-rollback-evidence.json`)
  - P04-T06: **สร้าง Teardown Script และสรุปหลักฐาน P04-evidence** (`done` — สร้าง `scripts/teardown.sh` / `make teardown` พร้อมโหมด `--dry-run` และเขียนรายงานสรุปหลักฐานครบถ้วนใน `reports/P04-evidence.md`)

## งานถัดไป: P05 — เฝ้าระวังและทดลองเหตุขัดข้อง (Monitoring & Reliability)

เจ้าของงาน: คนที่ 3 (Monitoring และ reliability)
- **เป้าหมาย:** ทำ dashboard และ alert แล้วจำลอง model failure ตาม proposal ตรวจการแจ้งเตือน กู้ระบบ และเพิ่ม regression test (ตอบเกณฑ์ **R3–R4**)

