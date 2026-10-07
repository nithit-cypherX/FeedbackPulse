# P02 — Model และ pipeline ที่ทำซ้ำได้

- **สถานะ: `done`** — ทั้ง 11 task เสร็จเมื่อ 2026-10-07 · ข้อเดียวที่ยืนยันไม่ครบคือ "evaluation path กับ API path เรียกฟังก์ชันเดียวกัน" ซึ่งฝั่ง evaluation ยืนยันแล้วแต่ **ฝั่ง API ต้องตรวจซ้ำใน P03** เพราะยังไม่มี endpoint
- เจ้าของ: คนที่ 1 — Model และ evaluation
- แผนหลัก: [Overview](../../overview-plan.md) · ขอบเขต: [Proposal](../../PROPOSAL.md) · ข้อตกลงที่ต้องทำตาม: [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md)

**หลักฐานทั้งเฟสอยู่ในไฟล์เดียว:** [reports/P02-evidence.md](../../reports/P02-evidence.md) — วิธีรันซ้ำ, ผล evaluation, version/hash, run ID, lineage, ผลวัด RAM/เวลา และข้อจำกัดทั้งหมด · แผนนี้ถือ **สถานะงาน การตัดสินที่ล็อก และเส้นแบ่งความรับผิดชอบ** ไม่เล่าตัวเลขซ้ำ

---

## 1. ขอบเขต

**ผลที่ต้องได้:** ขั้นตอน `prepare → evaluate → package → register` ที่รันซ้ำได้ และย้อนจาก model ที่ลงทะเบียนกลับไปหา **code, evaluation data, model revision ต้นทาง, environment และผล evaluation** ได้ — ตามเกณฑ์ **R1** ใน [P01-T03 §9](P01-T03-system-structure.md#9-จุดตรวจและหลักฐานตามเกณฑ์อาจารย์) และสิ่งที่ [Proposal §4](../../PROPOSAL.md#4-mlops-scope) สั่งให้ version

**ไม่รวมใน P02:**

- API endpoints `/predict`, `/health`, `/ready` → P03 · แต่ **module ที่โหลด model แล้วให้ผลทำนายเป็นของ P02** (ดูส่วนที่ 4)
- Azure resource, `Dockerfile`, CI/CD → P03–P04
- Dashboard, alert, การสาธิตเหตุขัดข้อง → P05
- **ไม่ train และไม่ fine-tune** ตาม [Proposal §2](../../PROPOSAL.md#2-model-and-dataset)

**แหล่งที่มา — ใช้ลิงก์ใน [Proposal §2](../../PROPOSAL.md#2-model-and-dataset) เท่านั้น** ไม่ใช้ mirror หรือ repo ที่ชื่อคล้ายกัน

| | แหล่ง | Licence |
|---|---|---|
| Model | `cardiffnlp/twitter-roberta-base-sentiment-latest` revision `3216a57f…` | CC BY 4.0 |
| Dataset | `crowdflower/twitter-airline-sentiment` **version 4** | CC BY-NC-SA 4.0 |

---

## 2. Tasks

ทุก task `done` · หลักฐานของทุก task อยู่ใน [reports/P02-evidence.md](../../reports/P02-evidence.md) ตามส่วนที่ระบุ

| ID | งาน | หลักฐาน |
|---|---|---|
| T11 | ตั้ง environment — Python version, dependency manager, lockfile | ส่วนที่ 1, 3 |
| T01 | ดึง model และ pin revision พร้อม provenance | ส่วนที่ 3 |
| T02 | จัด evaluation dataset ให้มี version | ส่วนที่ 1, 2, 3 |
| T03 | ยืนยันเพดานความยาวข้อความ | ส่วนที่ 3 |
| T04 | Shared inference module | ส่วนที่ 9 |
| T05 | Evaluation step และ metrics | ส่วนที่ 2, 4 |
| T06 | Lock รูปแบบชุด artifact | ส่วนที่ 3 |
| T07 | Lock lineage metadata และ `model_version` | ส่วนที่ 4, 5 |
| T08 | กำหนด tolerance ของการ evaluate ซ้ำ | ส่วนที่ 2 |
| T09 | วัด RAM และเวลาโหลด model | ส่วนที่ 1, 6 |
| T10 | ตัดสินที่เก็บ model artifact | ส่วนที่ 7 |

**ลำดับที่ทำจริง ไม่ใช่เรียงตามหมายเลข** — `T11 → T01, T02` แล้วจึงแตกเป็น `T03`, `T04 → T09`, `T05 → T08`, `T06 → T07 → T10` · T11 ต้องมาก่อนเพราะ task อื่นต้องรันโค้ดที่ติดตั้ง dependency แล้ว

---

## 3. การตัดสินที่ยังผูกพัน P03–P04

| เรื่อง | ค่าที่ล็อก | ใครต้องทำตาม |
|---|---|---|
| **เพดานความยาวข้อความ** | **510 content tokens** (รวม special tokens เป็น 512) นับด้วย tokenizer **ไม่ใช่นับอักขระ** · บันทึกไว้ที่ [P01-T02 §7](P01-T02-api-contract.md#7-จุดที่ยังต้องยืนยันและการส่งต่องาน) | P03 |
| **Interface ของ inference module** | `SentimentClassifier.load()` ครั้งเดียวตอน process เริ่ม แล้ว `predict()` ต่อ request · `ModelNotReady` → `503` · `InvalidText`/`TextTooLong` → `422` · **ห้ามเรียก tokenizer หรือ model เอง** | P03 |
| **`model_version`** | `sentiment-<artifact_id>-<lineage digest>` · P03 **อ่านค่าจาก registry entry หรือ configuration** ไม่ hardcode · **ถ้ารัน evaluation ซ้ำ ค่านี้จะเปลี่ยน ต้องอัปเดตค่าที่ deploy ด้วย** (กลไกและหลักฐานอยู่ใน [รายงาน ส่วนที่ 5](../../reports/P02-evidence.md)) | P03–P04 |
| **ที่เก็บ artifact** | **ใส่เข้า container image ตอน build** ไม่ใช้ blob storage แยก · เหตุผลหลักคือรักษาการผูกที่ `model_version` อ้างไว้ให้เป็นจริง — artifact ที่สลับได้ตอน runtime จะทำให้ version อ้างการผูกที่ไม่มีอะไรบังคับ ([เหตุผลเต็มและตารางเทียบ A/B](../../reports/P02-evidence.md) ส่วนที่ 7) | P03–P04 |
| **Python / dependency** | `uv` + `uv.lock` + Python `3.13` · runtime ใน container ใช้ `uv sync --no-default-groups` | P03–P04 |
| **รูปแบบชุด artifact** | `artifacts/<artifact_id>/` มี `manifest.json`, `upstream-model-card.md` และโฟลเดอร์ `model/` ที่มีเฉพาะสิ่งที่ loader อ่าน · weights เป็น `safetensors` | P03–P04 |
| **Tolerance การ evaluate ซ้ำ** | บน platform เดียวกันและ `uv.lock` เดียวกัน: **ทุก metric และ `predictions_sha256` ต้องตรงทุก bit** · **ไม่กำหนดสำหรับ platform อื่นเพราะไม่มีหลักฐาน** | P04 (CI) |
| **Metric หลัก** | **macro-F1** ไม่ใช่ accuracy เพราะ class ไม่สมดุล (สัดส่วนที่วัดได้อยู่ในรายงาน) | P04 |

**P02 ป้อนข้อมูลให้แต่ไม่ได้ตัดสิน:** วิธีนำ model เข้า container, จำนวน CPU/RAM, จำนวน process และ instance — เป็นของ P03–P04 ตาม [P01-T03 §12](P01-T03-system-structure.md#12-สิ่งที่ยังไม่-lock-และงานคุยถัดไป) · **เงื่อนไขที่ต้องทำตามตอนตัดสิน:** [Proposal §6](../../PROPOSAL.md#6-cost-estimate) สมมติไว้ 2 vCPU / 4 GiB ซึ่งเหลือที่เยอะเทียบกับที่ P02 วัดได้ — **ถ้าจะลดเพื่อประหยัดงบ อย่าลดต่ำกว่าราว 1 GiB โดยไม่ทดสอบ**

---

## 4. เส้นแบ่งกับ P03

[Overview](../../overview-plan.md) มอบให้คนที่ 1 ทั้ง "ดูแล P02" และ "ส่วนเชื่อม model เข้า API" ขณะที่ P03 ทั้งก้อนเป็นของคนที่ 2

P02 รับผิดชอบ **module และ loader ที่โหลด model แล้วให้ผลทำนาย** ส่วนการเขียน **endpoint, validation และ response เป็นของ P03**

---

## 5. ข้อจำกัดที่ติดไปกับผลงาน

อยู่ใน [reports/P02-evidence.md ส่วนที่ 8](../../reports/P02-evidence.md) ทั้งหมด — ผลวัดทุกค่ามาจาก macOS ไม่ใช่ในคอนเทนเนอร์, tolerance ใช้ได้เฉพาะ platform ที่วัด, evaluation ประเมิน HF snapshot ไม่ใช่ชุด artifact, metric คือความตรงกับ label ชุดนี้, ผลอธิบายเฉพาะ airline feedback และรายการที่ยังไม่มีใครตรวจ

**ใครรับช่วงต่อต้องอ่านส่วนที่ 8 ก่อนใช้ตัวเลขใดไปตัดสิน**
