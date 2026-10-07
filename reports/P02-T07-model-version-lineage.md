# P02-T07 — `model_version` และ lineage

- Task: [P02-T07 ใน phase plan](../docs/plans/P02-model-pipeline.md) · ข้อตกลง API: [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) · เกณฑ์: **R1** ใน [P01-T03 §9](../docs/plans/P01-T03-system-structure.md#9-จุดตรวจและหลักฐานตามเกณฑ์อาจารย์)
- รันเมื่อ: 2026-10-07 · version แรกที่ออก: `sentiment-6e7ff9fbc17c-32855c02`
- Registry entry: [`reports/registry/sentiment-6e7ff9fbc17c-32855c02.json`](registry/sentiment-6e7ff9fbc17c-32855c02.json) พร้อมสำเนาผล evaluation ของตัวเองข้าง ๆ

---

## 1. ตรวจอะไร

[P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) กำหนดว่า `model_version` ต้องเป็น "รุ่นของ model artifact ที่กำลังใช้งานจริง และย้อนกลับไปหา lineage ได้ **ไม่ใช่ชื่อเวอร์ชันตัวอย่างที่ใส่ค้างไว้**" · ค่า `"sentiment-v1"` ในเอกสารนั้นเป็นตัวอย่างรูปแบบ T07 จึงต้องกำหนดของจริง

R1 ต้องย้อนจาก model ที่ deploy ไปหา **code, evaluation data, model revision ต้นทาง, ผล evaluation และ environment** ได้ · `environment` มาจาก [Proposal §4](../PROPOSAL.md#4-mlops-scope) ที่สั่งให้ version ทั้งสี่อย่าง

## 2. Scheme ที่ล็อก

```
sentiment-6e7ff9fbc17c-32855c02
│         │             │
│         │             lineage digest 8 ตัว — sha256 ของ lineage record ทั้งก้อน
│         │             (code commit, environment, dataset, ผล evaluation)
│         artifact_id จาก P02-T06 — content-addressed จากไฟล์ใน model/
model family — อ่านออกใน log และใน response body
```

| สิ่งที่ตัดสิน | เหตุผล |
|---|---|
| **3 ส่วน ไม่ใช่ hash ตัวเดียว** | `artifact_id` ตรงกลางทำให้เห็นได้ทันทีว่าสอง release ใช้ weights ชุดเดียวกันหรือไม่ ซึ่งเป็นสิ่งที่ต้องอ่านเร็วตอน rollback (R2) · hash ตัวเดียวจะอ่านอะไรไม่ได้เลย |
| **content-addressed ไม่ใช่ตัวนับ** | ไม่ต้องมีทะเบียนกลางแจกเลขถัดไป ซึ่งสำคัญเพราะยังไม่เลือกบริการเก็บ artifact (T10) · input ชุดเดิมให้ version เดิมเสมอ |
| **digest ครอบ code และ environment ไม่ใช่แค่ weights** | `predict()` ขึ้นกับโค้ดของเราด้วย ไม่ใช่แค่ weights · ถ้าเปลี่ยน preprocessing แล้ว version ไม่เปลี่ยน version นั้นจะโกหก |
| **ยาว 31 อักขระ** | ใส่ใน JSON response และ log ได้โดยไม่เทอะทะ |

### Lineage record

`reports/registry/<model_version>.json` เก็บ 6 ส่วน:

| ส่วน | บันทึกอะไร |
|---|---|
| `artifact` | `artifact_id`, hash ของ `manifest.json`, hash ของทุกไฟล์ในชุด |
| `source_model` | repo, revision, licence, **hash ต้นทางของทุกไฟล์รวม `pytorch_model.bin`** |
| `evaluation_data` | handle version 4, sha256, จำนวนแถว |
| `code` | commit |
| `environment` | Python, **hash ของ `uv.lock`**, เวอร์ชัน package ที่กระทบ inference |
| `evaluation` | ไฟล์ผล + hash, เวลารัน, accuracy, macro-F1 |

**ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ผูกกับการตัดสินของ T10

## 3. Registry ปฏิเสธมากกว่ายอมบันทึก

`register()` โยน `CannotRegister` แทนที่จะออก version ที่อ้างสิ่งที่พิสูจน์ไม่ได้:

| เงื่อนไขที่ปฏิเสธ | เหตุผล |
|---|---|
| มี input ที่ยัง uncommitted | version จะอ้าง commit ที่สร้างกลับมาไม่ได้ |
| evaluation รันบน code ที่ยัง uncommitted | ตัวเลขไม่ผูกกับ commit ใด |
| **ไฟล์ที่ตัดสินผลทำนายเปลี่ยนตั้งแต่ eval รัน** | ผล evaluation ไม่ได้อธิบาย code ที่กำลัง release |
| model revision ไม่ตรงกับที่ eval ใช้ | lineage ไม่สอดคล้องกันเอง |
| dataset ไม่ตรงกับที่ eval ใช้ | เหมือนกัน |

รายการไฟล์ที่นับว่า "ตัดสินผลทำนาย" อยู่ใน `gitinfo.BEHAVIOUR_PATHS`: `inference.py`, `model_files.py`, `dataset.py`, `evaluation.py`, `evaluate.py`, `pyproject.toml`, `uv.lock`

**guard ข้อที่สามทำงานจริงในรอบนี้** — ตรวจพบว่า `inference.py` และ `evaluate.py` เปลี่ยนไปตั้งแต่ commit `40dcb77` ที่ evaluation รอบก่อนรัน จึงปฏิเสธการ register และบังคับให้รัน evaluation ใหม่ก่อน

## 4. ผล Check — ไล่ย้อนจาก `model_version` ค่าเดียว

เริ่มจากสตริง `sentiment-6e7ff9fbc17c-32855c02` อย่างเดียว แล้วไล่ย้อนทุกชั้น โดย**คำนวณ hash จากไฟล์จริงทุกตัว ไม่ใช่อ่านค่าที่บันทึกไว้มาเทียบกับตัวเอง**

| ชั้น | ตรวจอะไร | ผล |
|---|---|---|
| 1 | digest ในสตริงตรงกับ hash ของ lineage ที่บันทึก | ผ่าน |
| 2 | `manifest.json` และไฟล์ในชุดทั้ง 6 ไฟล์ hash ตรง | ผ่าน 7/7 |
| 3 | revision ตรงกับที่ pin ในโค้ด และไฟล์ต้นทางทั้ง 6 ไฟล์ hash ตรง | ผ่าน 7/7 |
| 4 | `data/Tweets.csv` hash ตรง และ handle ตรงกับที่ pin | ผ่าน 2/2 |
| 5 | commit มีอยู่จริง · อยู่ในสายของ `HEAD` · ไฟล์ที่ตัดสินผลทำนายไม่เปลี่ยนตั้งแต่นั้น | ผ่าน 3/3 |
| 6 | `uv.lock` hash ตรง | ผ่าน |
| 7 | ไฟล์ผล evaluation hash ตรง · metric ตรง · รันที่ commit เดียวกับ lineage | ผ่าน 3/3 |
| 8 | โหลด artifact แล้วทำนายได้ และคืน `model_version` ค่านี้ | ผ่าน (`negative` 0.943575) |

**รวม 26/26**

## 5. มีข้อจำกัดอะไร และส่งต่ออะไร

**ปิดข้อจำกัดของ T06 ที่ค้างไว้** — [P02-T06](P02-T06-artifact-layout.md) บันทึกว่ายังไม่มี `model_version` จริง และใช้ `artifact_id` เป็นค่าชั่วคราว · ตอนนี้มี scheme จริงแล้ว

**`model_version` เป็น input ของ `SentimentClassifier.load()` ไม่ใช่ค่าที่โมดูลหาเอง** — ตรงตามที่ [P02-T04](P02-T04-inference-interface.md) ล็อกไว้ · **P03 ต้องอ่านค่าจาก registry entry หรือจาก configuration แล้วส่งเข้าไป** ไม่ใช่ hardcode

**ยังไม่มีการตรวจว่า version ที่ deploy ตรงกับ artifact ที่โหลดจริง** — `load()` รับ `model_version` ที่ส่งมาเฉย ๆ ถ้า P03 ส่งค่าผิด API จะคืนค่าผิดโดยไม่มีอะไรจับได้ · registry entry มี hash ของทุกไฟล์ให้ตรวจได้ แต่ **การเรียกตรวจตอน startup เป็นของ P03** ตาม [P01-T02 §4](../docs/plans/P01-T02-api-contract.md#4-validation-และ-error-handling) และการตัดสินว่าอะไรนับเป็น artifact ใช้ไม่ได้เป็นของ P05 — P02 ไม่เขียนฟังก์ชันตรวจไว้ล่วงหน้าเพราะยังไม่มีผู้ใช้และจะต้องเดา call site กับ error semantics ของเขา

**แก้ข้อบกพร่องที่พบตอน T08 (2026-10-07):** entry เดิมบันทึกผล evaluation ด้วย **path ที่ใช้ร่วมกัน** (`reports/P02-T05-evaluation-result.json`) ซึ่งถูกเขียนทับทุกรอบ · version แรกที่ออก (`…-c18ecbc6`) จึง **trace ไม่ได้ทันทีที่รัน evaluation ซ้ำใน T08** — hash ที่บันทึกไว้ไม่ตรงกับไฟล์ใด · ถ้า rollback ไป version นั้นจะได้ lineage ที่ตรวจไม่ได้ ซึ่งตรงข้ามกับที่ R2 ต้องการ · **แก้แล้ว: แต่ละ entry คัดลอกผล evaluation ของตัวเองไว้ข้าง ๆ เป็น `<version>-evaluation.json`** พร้อม test ที่เขียนทับไฟล์กลางแล้วยืนยันว่า entry ยัง resolve ได้ · version เดิมถูกลบเพราะสำเนาถูกเขียนทับไปก่อนที่จะพบปัญหาและกู้คืนไม่ได้ จึงเป็น entry ที่อ้างสิ่งที่พิสูจน์ไม่ได้อีก — ไม่เคย deploy ที่ไหน และ git history เก็บบันทึกไว้ว่ามีอยู่

**registry เป็นไฟล์ใน Git ไม่ใช่บริการ** — เลือกแบบนี้เพราะยังไม่ตัดสินบริการเก็บ artifact (T10) และไฟล์ใน Git ก็ตรวจย้อนได้ตามที่ R1 ต้องการ · ถ้า T10 เลือกบริการที่มี registry ของตัวเอง entry พวกนี้ยังใช้เป็นบันทึกอ้างอิงได้ **ยังไม่ได้ประเมินว่าจะย้ายหรือทำสองที่**

**ยังไม่มีขั้นตอน release หลาย version** — ตอนนี้มี version เดียวและ `main()` ปฏิเสธถ้าเจอ artifact มากกว่าหนึ่งชุด แทนที่จะเดาว่าอันไหน · การจัดการหลาย version พร้อมกันจะจำเป็นตอน rollback ใน **P04** ซึ่งยังไม่ได้ออกแบบ

**ผล evaluation เหมือนกัน 3 รอบติด** — รันที่ commit `40dcb77`, `35e881f` (ผ่าน) และ `ad382f1` · ทุก metric และ confusion matrix ตรงกันทุกหลัก ต่างแค่เวลา 648.1 / 674.1 / 678.9 วินาที · ยืนยันว่าการแก้ `tokenizer.model_max_length` ใน `83c202c` **ไม่เปลี่ยนผลทำนาย** · เป็นข้อมูลให้ **T08** ไม่ใช่การปิด T08 — ยังไม่ทดสอบจาก fresh state และยังไม่ทดสอบข้ามเครื่อง
