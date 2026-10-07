# P02 — Model และ pipeline ที่ทำซ้ำได้

- **สถานะ: `done`** — ทั้ง 11 task เสร็จและผ่าน Check ครบ เมื่อ 2026-10-07
- เจ้าของ: คนที่ 1 — Model และ evaluation
- แผนหลัก: [Overview](../../overview-plan.md) · ขอบเขต: [Proposal](../../PROPOSAL.md) · ข้อตกลงที่ต้องทำตาม: [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md)

`model_version` ที่ใช้งาน: **`sentiment-6e7ff9fbc17c-32855c02`** · ผล evaluation บน 14,640 แถว: **accuracy 0.8100 · macro-F1 0.7606**

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

ทุก task `done` · หลักฐานเต็มอยู่ในรายงานที่ลิงก์ไว้ ไม่เล่าซ้ำที่นี่

| ID | งาน | หลักฐาน |
|---|---|---|
| T11 | ตั้ง environment — Python version, dependency manager, lockfile | ดูส่วนที่ 3 |
| T01 | ดึง model และ pin revision พร้อม provenance | [รายงาน](../../reports/P02-T01-model-provenance.md) |
| T02 | จัด evaluation dataset ให้มี version | [รายงาน](../../reports/P02-T02-evaluation-dataset.md) |
| T03 | ยืนยันเพดานความยาวข้อความ | [รายงาน](../../reports/P02-T03-text-length-cap.md) |
| T04 | Shared inference module | [รายงาน](../../reports/P02-T04-inference-interface.md) |
| T05 | Evaluation step และ metrics | [รายงาน](../../reports/P02-T05-evaluation.md) |
| T06 | Lock รูปแบบชุด artifact | [รายงาน](../../reports/P02-T06-artifact-layout.md) |
| T07 | Lock lineage metadata และ `model_version` | [รายงาน](../../reports/P02-T07-model-version-lineage.md) |
| T08 | กำหนด tolerance ของการ evaluate ซ้ำ | [รายงาน](../../reports/P02-T08-reproducibility-tolerance.md) |
| T09 | วัด RAM และเวลาโหลด model | [รายงาน](../../reports/P02-T09-load-and-memory.md) |
| T10 | ตัดสินที่เก็บ model artifact | [รายงาน](../../reports/P02-T10-artifact-storage.md) |

**ลำดับที่ทำจริง ไม่ใช่เรียงตามหมายเลข** — `T11 → T01, T02` แล้วจึงแตกเป็น `T03`, `T04 → T09`, `T05 → T08`, `T06 → T07 → T10` · T11 ต้องมาก่อนเพราะ task อื่นต้องรันโค้ดที่ติดตั้ง dependency แล้ว

---

## 3. การตัดสินที่ยังผูกพัน P03–P04

| เรื่อง | ค่าที่ล็อก | ใครต้องทำตาม |
|---|---|---|
| **เพดานความยาวข้อความ** | **510 content tokens** (รวม special tokens เป็น 512) นับด้วย tokenizer **ไม่ใช่นับอักขระ** · บันทึกไว้ที่ [P01-T02 §7](P01-T02-api-contract.md#7-จุดที่ยังต้องยืนยันและการส่งต่องาน) | P03 |
| **Interface ของ inference module** | `SentimentClassifier.load()` ครั้งเดียวตอน process เริ่ม แล้ว `predict()` ต่อ request · `ModelNotReady` → `503` · `InvalidText`/`TextTooLong` → `422` · **ห้ามเรียก tokenizer หรือ model เอง** | P03 |
| **`model_version`** | `sentiment-<artifact_id>-<lineage digest>` · P03 **อ่านค่าจาก registry entry หรือ configuration** ไม่ hardcode | P03 |
| **ที่เก็บ artifact** | **ใส่เข้า container image ตอน build** ไม่ใช้ blob storage แยก | P03–P04 |
| **Python / dependency** | `uv` + `uv.lock` + Python `3.13` · runtime ใน container ใช้ `uv sync --no-default-groups` | P03–P04 |
| **รูปแบบชุด artifact** | `artifacts/<artifact_id>/` มี `manifest.json`, `upstream-model-card.md` และโฟลเดอร์ `model/` ที่มีเฉพาะสิ่งที่ loader อ่าน · weights เป็น `safetensors` | P03–P04 |
| **Tolerance การ evaluate ซ้ำ** | บน platform เดียวกันและ `uv.lock` เดียวกัน: **ทุก metric และ `predictions_sha256` ต้องตรงทุก bit** · **ไม่กำหนดสำหรับ platform อื่นเพราะไม่มีหลักฐาน** | P04 (CI) |
| **Metric หลัก** | **macro-F1** ไม่ใช่ accuracy เพราะชุดข้อมูลเป็น `negative` 62.7% | P04 |

**P02 ป้อนข้อมูลให้แต่ไม่ได้ตัดสิน:** วิธีนำ model เข้า container, จำนวน CPU/RAM, จำนวน process และ instance — เป็นของ P03–P04 ตาม [P01-T03 §12](P01-T03-system-structure.md#12-สิ่งที่ยังไม่-lock-และงานคุยถัดไป)

---

## 4. เส้นแบ่งกับ P03

[Overview](../../overview-plan.md) มอบให้คนที่ 1 ทั้ง "ดูแล P02" และ "ส่วนเชื่อม model เข้า API" ขณะที่ P03 ทั้งก้อนเป็นของคนที่ 2

P02 รับผิดชอบ **module และ loader ที่โหลด model แล้วให้ผลทำนาย** ส่วนการเขียน **endpoint, validation และ response เป็นของ P03**

---

## 5. ข้อจำกัดที่ติดไปกับผลงาน

- **ผลวัดทั้งหมดมาจาก macOS 15.5 arm64 ไม่ใช่ในคอนเทนเนอร์** — `safetensors` ใช้ mmap ทำให้ peak RSS ต่ำกว่าขนาดไฟล์ และบน Linux หน้าที่ mmap อาจถูกนับเข้า cgroup limit · **ยังไม่ได้ทดสอบ** · ตัวเลขทุกตัวต้องวัดซ้ำก่อนใช้ตัดสินขนาด container
- **tolerance ใช้ได้เฉพาะ platform ที่วัด** — ถ้า CI รันบน Linux x86-64 ต้องวัดที่นั่นก่อนตั้ง gate ไม่ใช่ใช้เกณฑ์ "ตรงทุก bit" ทันที
- **evaluation ประเมิน HF snapshot ไม่ใช่ชุด artifact ที่จะ deploy** — เชื่อมกันด้วยการตรวจใน T06 ที่พบว่า logits เท่ากันทุก bit **ไม่ใช่เพราะเป็นไฟล์เดียวกัน**
- **metric ที่วัดได้คือความตรงกับ label ชุดนี้ ไม่ใช่เพดานความสามารถของ model** — 28.7% ของแถวมี `airline_sentiment_confidence` ต่ำกว่า 1.0
- **ผลอธิบายประสิทธิภาพบน airline feedback เท่านั้น** ตามที่ Proposal §2 ระบุเอง
- **ยังไม่มีใครตรวจ hash จาก `manifest.json` ตอน startup** — P02 ผลิตข้อมูลให้แล้ว การเรียกตรวจเป็นของ P03 และการตัดสินว่าอะไรนับเป็น artifact ใช้ไม่ได้เป็นของ P05
