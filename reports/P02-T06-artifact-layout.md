# P02-T06 — รูปแบบชุด model artifact

- Task: [P02-T06 ใน phase plan](../docs/plans/P02-model-pipeline.md) · หน้าที่ของส่วนเตรียม model: [P01-T03 §2](../docs/plans/P01-T03-system-structure.md#2-ส่วนเตรียม-model--ทำก่อนนำรุ่นนั้นไปใช้งาน) · ตำแหน่งโฟลเดอร์: [P01-T03 §6](../docs/plans/P01-T03-system-structure.md#6-ตำแหน่ง-code-data-model-และ-configuration)
- สร้างเมื่อ: 2026-10-07 · ชุดที่สร้าง: `sentiment-6e7ff9fbc17c`
- เครื่อง: macOS 15.5 arm64 · `torch 2.14.1` · `transformers 5.19.0` · `safetensors 0.8.0`

**รูปแบบนี้ไม่ผูกกับบริการเก็บไฟล์** การเลือกที่เก็บเป็นงาน **T10** และวิธีนำเข้า container เป็นงาน **P03–P04** — โครงสร้างนี้ตั้งใจไม่ปิดทางเลือกใดของทั้งสองเรื่อง

---

## 1. ตรวจอะไร

กำหนดว่าชุด model ที่ package แล้วมีไฟล์อะไร วางโครงสร้างไหน และอ้างถึงด้วย id แบบไหน · แล้วยืนยันว่า **โหลดได้โดยไม่ต้องพึ่งไฟล์นอกชุด** ตามที่ [P01-T03 §2](../docs/plans/P01-T03-system-structure.md#2-ส่วนเตรียม-model--ทำก่อนนำรุ่นนั้นไปใช้งาน) กำหนดว่าผลลัพธ์ต้องเป็น "ชุด model ที่พร้อมให้ระบบบริการนำไปใช้ และตรวจย้อนกลับได้"

## 2. โครงสร้างที่ล็อก

```text
artifacts/
└── sentiment-6e7ff9fbc17c/
    ├── manifest.json             lineage, hash ของทุกไฟล์, metadata
    ├── upstream-model-card.md     model card ต้นทาง (เครดิตตาม CC BY 4.0)
    └── model/                     สิ่งที่ loader อ่าน และไม่มีอะไรเกินนั้น
        ├── config.json
        ├── model.safetensors
        ├── vocab.json
        ├── merges.txt
        └── special_tokens_map.json
```

| สิ่งที่ตัดสิน | ค่า | เหตุผล |
|---|---|---|
| **โฟลเดอร์ที่โหลด** | `model/` แยกจาก manifest | `transformers` สแกนทั้ง directory ที่ส่งให้ · แยกไว้ทำให้ manifest และ model card ไม่ไปปนกับไฟล์ที่ loader อ่าน |
| **รูปแบบ weights** | `model.safetensors` | ดูส่วนที่ 4 |
| **ไฟล์ที่คัดลอกทั้ง byte** | `config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json` | hash ยังตรงกับต้นทางที่ [P02-T01](P02-T01-model-provenance.md) บันทึก จึงตรวจย้อนได้ตรง ๆ |
| **model card ต้นทาง** | `upstream-model-card.md` อยู่ที่ราก **ไม่อยู่ใน `model/`** | CC BY 4.0 ต้องให้เครดิต แต่ loader ไม่ได้อ่านไฟล์นี้ |
| **ที่เก็บ** | `artifacts/` ในเครื่อง | ตาม [P01-T03 §6](../docs/plans/P01-T03-system-structure.md#6-ตำแหน่ง-code-data-model-และ-configuration) · `.gitignore` กันไว้แล้ว ไฟล์ไม่เข้า Git |

### `artifact_id` — content-addressed

```
sentiment-<sha256(ของรายการ "ชื่อไฟล์:hash" ของไฟล์ใน model/ เรียงแล้ว) 12 ตัวแรก>
```

**ใช้การอ้างตามเนื้อหา ไม่ใช่ตัวนับ** เพราะ input ชุดเดิมให้ id เดิมเสมอ ดังนั้นสองคนที่ package แยกกันบอกได้ว่าได้ของชุดเดียวกันหรือไม่ โดยไม่ต้องมีทะเบียนกลาง — ซึ่งสำคัญเพราะยังไม่ได้เลือกบริการเก็บ artifact (T10)

คิด hash จากไฟล์ใน `model/` เท่านั้น ทำให้ `manifest.json` บันทึก id ของตัวเองได้โดยไม่วนซ้ำ

**`artifact_id` ไม่ใช่ `model_version`** ที่ API คืนตาม [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) · `model_version` เป็นงาน **T07** ซึ่งจะอ้าง `artifact_id` ตัวนี้ได้

### `manifest.json` บันทึกอะไร

`artifact_id` · เวลาสร้าง · `loadable_dir` · repo/revision/licence ต้นทาง · **hash ต้นทางของทุกไฟล์รวม `pytorch_model.bin`** · รายละเอียดการแปลง weights · labels และ `max_content_tokens` · commit ที่ build · เวอร์ชัน `torch`/`transformers`/`safetensors` · hash ของทุกไฟล์ในชุด

`labels` และ `max_content_tokens` **อ่านจาก loader ที่โหลดชุดที่ build เสร็จแล้ว** ไม่ได้คำนวณซ้ำใน packaging script · ทำให้ manifest รายงานตัวเลขของ loader เองและ **การ build จะล้มทันทีถ้าชุดที่ประกอบขึ้นโหลดไม่ได้** ไม่ต้องรอตรวจด้วยมือ

**ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ผูกกับการตัดสินของ T10

## 3. วิธีรันซ้ำ

```bash
PYTHONPATH=src uv run python -m feedbackpulse.package_artifact
```

## 4. การแปลง weights เป็น safetensors

[P02-T01](P02-T01-model-provenance.md) ส่งเรื่องนี้มาให้ T06 ตัดสิน เพราะ repo ต้นทางมีแต่ `pytorch_model.bin` ไม่มี `model.safetensors`

**ตัดสินใจ: แปลงเป็น safetensors**

| เหตุผล | รายละเอียด |
|---|---|
| **ไม่ต้อง unpickle ตอนโหลด** | `pytorch_model.bin` เป็น pickle ซึ่งรันโค้ดได้ตอน deserialize · [Proposal §5](../PROPOSAL.md#5-planned-failure) ระบุว่า P05 จะ**ตั้งใจทำให้ artifact ใช้งานไม่ได้** การโหลดไฟล์ที่ถูกแก้ไขจึงไม่ควรเป็นการรันโค้ดจากไฟล์นั้น |
| **โหลดเร็วกว่า** | ช่วย cold start ซึ่ง Proposal §3 ระบุว่าต้องรายงานแยก · ยังไม่ได้วัดตัวเลข — เป็นงาน T09 |
| **ไม่เพิ่ม dependency** | `safetensors 0.8.0` เป็น dependency ต่อเนื่องของ `transformers` อยู่แล้ว |

### สิ่งที่การแปลงเปลี่ยนไป และสิ่งที่ยืนยันแล้วว่าไม่เปลี่ยน

ต้นทางมี **204 tensor** ชุดที่เขียนลง safetensors มี **201 tensor** · ที่หายไป 3 ตัวคือ

- `roberta.embeddings.position_ids` — buffer ที่ `transformers` รุ่นนี้ไม่ได้เก็บแล้ว
- `roberta.pooler.dense.weight` และ `.bias` — pooler ที่ sequence-classification head ไม่เรียกใช้ (ตรงกับที่ `transformers` รายงานเป็น `UNEXPECTED` ตอนโหลดต้นทาง)

**บันทึกไว้ใน manifest เพราะชุดนี้ไม่ใช่สำเนาของต้นทาง** และยืนยันว่าไม่กระทบผลด้วยการเทียบจริง:

| ตรวจ | ผล |
|---|---|
| `state_dict` จาก safetensors เทียบจาก `.bin` | key ตรงกันทั้ง 201 ตัว · **ทุก tensor เท่ากันทุก bit** |
| logits บนข้อความจริง 300 แถวจาก evaluation set | ความต่างสูงสุด **0.000e+00** |
| sentiment ที่ทำนายต่างกัน | **0 / 300** |

## 5. ผล Check — โหลดได้โดยไม่พึ่งไฟล์นอกชุด

ตั้ง `HF_HOME` ชี้ไป directory ว่าง พร้อม `HF_HUB_OFFLINE=1` และ `TRANSFORMERS_OFFLINE=1` แล้วโหลดจาก `artifacts/sentiment-6e7ff9fbc17c/model`:

| ตรวจ | ผล |
|---|---|
| `HF_HOME` ว่างจริงตอนรัน | ยืนยันด้วยการไล่ไฟล์ใน directory → ไม่มีไฟล์ |
| `SentimentClassifier.load()` | สำเร็จ **ไม่แตะ cache และไม่ต่อ network** |
| `labels` | `('negative', 'neutral', 'positive')` ตรงกับ [P02-T01](P02-T01-model-provenance.md) |
| `max_content_tokens` | **510** ตรงกับ [P02-T03](P02-T03-text-length-cap.md) |
| ทำนาย 3 ข้อความอ้างอิง | `negative` 0.943575 · `positive` 0.941379 · `neutral` 0.925601 — ตรงกับที่ T01 บันทึก |

hash ของไฟล์ที่คัดลอกมาตรงกับที่ [P02-T01](P02-T01-model-provenance.md) บันทึกทุกตัว: `config.json` `d2fba199…` · `merges.txt` `1ce16647…` · `special_tokens_map.json` `378eb3bf…` · `vocab.json` `06b4d46c…` · model card `05ad8514…`

## 6. มีข้อจำกัดอะไร และส่งต่ออะไร

**ไม่ได้เพิ่ม `tokenizer_config.json` เข้าชุด** ทั้งที่ [P02-T01](P02-T01-model-provenance.md) พบว่าการไม่มีไฟล์นี้ทำให้ `tokenizer.model_max_length` คืนค่า sentinel · เหตุผล: ถ้าเพิ่มจะมีแหล่งความจริงสองที่สำหรับเพดานความยาวข้อความ ขณะที่ `SentimentClassifier` คำนวณจาก `config.json` อยู่แล้ว · แทนที่จะเพิ่มไฟล์ จึงบันทึก `max_content_tokens: 510` ไว้ใน `manifest.json` เป็น metadata ที่คนอ่านได้

**แก้ช่องที่พังเงียบแล้ว (2026-10-07):** `SentimentClassifier.load()` ตั้ง `tokenizer.model_max_length` ให้เป็นค่าที่ derive ได้ (512) · วัดได้ก่อนแก้ว่าข้อความ 603 tokens เทียบกับ sentinel ให้ผล `False` คือ **ตรวจไม่เจอว่าเกินเพดาน** ซึ่งจะทำให้ข้อความยาวเกินไปถึง model แล้วกลายเป็น `500` แทน `422` · ตัวเลขยังมาจาก `config.json` ที่เดียวเหมือนเดิม ไม่ได้เพิ่มไฟล์ที่เราแต่งขึ้น · ผลพลอยได้: `transformers` เตือนดัง ๆ ว่า `603 > 512 ... will result in indexing errors` ซึ่งเดิมเงียบสนิท · มี test กำกับไว้

**ที่ยังกันไม่ได้:** ถ้าใครเปิด `artifacts/<id>/model` ด้วย `AutoTokenizer` โดยตรงโดยไม่ผ่านโมดูลของเรา ก็ยังเจอค่า sentinel — กันด้วยเอกสารใน [P02-T04](P02-T04-inference-interface.md) ที่ระบุว่าห้ามเรียก tokenizer หรือ model เอง

**ยังไม่ได้วัดเวลาโหลดจาก safetensors เทียบกับ `.bin`** — อ้างว่าเร็วกว่าตามคุณสมบัติของรูปแบบ **ไม่ใช่จากการวัดของเรา** · T09 เป็นผู้วัดเวลาโหลดและ RAM จริง

**ยังไม่มี `model_version`** — การทดลองโหลดใช้ `artifact_id` เป็นค่าชั่วคราวเพื่อให้เห็นว่าโมดูลส่งค่าผ่านได้ · scheme จริงเป็นงาน **T07**

**ขนาดชุด artifact ราว 476 MiB** (`model.safetensors` 498,615,868 bytes) — เป็นข้อมูลที่ **T10** ต้องใช้ประเมินค่าเก็บข้อมูลกับงบ USD 15 และที่ **P03–P04** ต้องใช้ประเมินขนาด image กับเวลา cold start

**ยังไม่ได้ทดสอบว่าชุดนี้ทนการถูกแก้ไขอย่างไร** — P05 จะทำให้ artifact ใช้งานไม่ได้ตาม Proposal §5 · `manifest.json` มี hash ของทุกไฟล์ให้ตรวจความครบถ้วนได้ แต่ **ยังไม่มีโค้ดที่เรียกตรวจตอน startup** และยังไม่ได้ตกลงว่าจะตรวจที่ไหน — เป็นเรื่องที่ P03 และ P05 ต้องตัดสิน
