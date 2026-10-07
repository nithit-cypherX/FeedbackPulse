# P02 — Model และ pipeline ที่ทำซ้ำได้

- แผนหลัก: [Overview plan](../../overview-plan.md) · ขอบเขตโครงการ: [Proposal](../../PROPOSAL.md)
- ข้อตกลงที่ต้องทำตาม: [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md)
- สถานะ P02: `in_progress` — T01–T07, T09 และ T11 `done` · T08 กับ T10 `planned`
- เจ้าของ: คนที่ 1 — Model และ evaluation (ตาม [overview](../../overview-plan.md))
- อัปเดต: 2026-10-07

**การเปลี่ยนอำนาจตัดสินใจ (ผู้ใช้สั่งเมื่อ 2026-10-07):** เรื่องที่แผนเดิมเขียนว่า *รอมติทีม* หรือ *รอคนที่ 2 ยืนยัน* เปลี่ยนเป็น **คนที่ 1 ตัดสินเอง แล้วคนที่ 2 รับไปทำต่อโดยอิงการตัดสินนี้** · กระทบ T04, T10 และ T11 · บันทึกไว้เพื่อให้เห็นว่าเป็นการเปลี่ยนขอบเขตที่ได้รับอนุญาต ไม่ใช่การลดเกณฑ์เพื่อปิด task · **เกณฑ์ทางเทคนิคอื่นไม่เปลี่ยน** — task ที่ยังตรวจไม่ได้ก็ยังปิดไม่ได้

ไฟล์นี้เป็น **แผนของ phase P02** พร้อมบันทึกความคืบหน้าจริง · **เสร็จแล้ว 9 task:** [T01](../../reports/P02-T01-model-provenance.md), [T02](../../reports/P02-T02-evaluation-dataset.md), [T03](../../reports/P02-T03-text-length-cap.md), [T04](../../reports/P02-T04-inference-interface.md), [T05](../../reports/P02-T05-evaluation.md), [T06](../../reports/P02-T06-artifact-layout.md), [T07](../../reports/P02-T07-model-version-lineage.md), [T09](../../reports/P02-T09-load-and-memory.md) และ T11 · T08 กับ T10 ยังเป็น `planned` และช่อง "ผลจริง" ยังเป็น *ยังไม่รัน*

---

## 1. Outcome และขอบเขต

**ผลที่ต้องได้:** ขั้นตอน `prepare → evaluate → package → register` ที่รันซ้ำได้ และย้อนจาก model ที่ลงทะเบียนกลับไปหา code, evaluation data, model revision ต้นทาง, ผล evaluation และ environment ได้ — ครบ 4 อย่างที่ [Proposal §4](../../PROPOSAL.md#4-mlops-scope) กำหนดให้ version ("code, evaluation data, model revision, and environment") บวกผล evaluation

**Phase acceptance:** ตามเกณฑ์ **R1 — Reproducible ML Pipeline** ใน [P01-T03 §9](P01-T03-system-structure.md#9-จุดตรวจและหลักฐานตามเกณฑ์อาจารย์) ไม่เขียนเกณฑ์ชุดใหม่ในไฟล์นี้ หลักฐานที่ต้องเก็บคือ วิธีรันซ้ำ, ผล evaluation, version/hash, run ID และ lineage

**ไม่รวมใน P02 (non-goals):**

- เขียน API endpoints `/predict`, `/health`, `/ready` → P03 · แต่ **ส่วนเชื่อม model เข้า API เป็นของคนที่ 1** ตาม [overview](../../overview-plan.md) ดูเส้นแบ่งในส่วนที่ 4
- สร้าง Azure resource, Dockerfile, CI/CD → P03–P04
- Dashboard, alert, การสาธิตเหตุขัดข้อง → P05
- **ไม่ train และไม่ fine-tune** ตาม [Proposal §2](../../PROPOSAL.md#2-model-and-dataset) — P02 คือการนำ pretrained model มาใช้ให้ตรวจย้อนกลับได้ ไม่ใช่การทำซ้ำการฝึก model ต้นฉบับ

### แหล่งที่มาของ model และ dataset

**ใช้ลิงก์ใน [Proposal §2](../../PROPOSAL.md#2-model-and-dataset) เท่านั้น** ไม่เลือก model หรือ dataset อื่น ไม่ใช้ mirror หรือ repo ที่ชื่อคล้ายกัน:

| สิ่งที่ดึง | แหล่ง | Licence |
|---|---|---|
| Model | <https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest> | CC BY 4.0 |
| Evaluation dataset | <https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment> **version 4** | CC BY-NC-SA 4.0 |

ถ้าลิงก์ใดเข้าไม่ได้ หรือเนื้อหาที่ได้ไม่ตรงกับที่ Proposal ระบุ ให้มาร์ค task นั้นเป็น `blocked` แล้วกลับไปคุยกับทีมหรืออาจารย์ **ไม่หา model ทดแทนเอง** เพราะ Proposal เป็นขอบเขตที่ทีมยึดตาม และ [overview](../../overview-plan.md) บันทึกว่าผู้ใช้แจ้งเมื่อ 2026-10-05 ว่าอาจารย์ยืนยันขอบเขตนี้แล้ว — **ยังไม่มีหลักฐานลายลักษณ์อักษร** ดู §5 ข้อ 5

### Dependency

- ต้องเข้าถึง Hugging Face และ Kaggle ได้ — ผู้ใช้ยืนยันเมื่อ 2026-10-07 ว่าเข้าถึงได้ แต่ **ยังไม่ได้โหลดลงเครื่อง** จึงยังไม่มี task ใดที่ `blocked` จากเรื่องนี้
- ข้อตกลงที่พร้อมใช้แล้ว: API contract (ยกเว้นเพดานความยาวข้อความ), โครงสร้างโฟลเดอร์, กติกาเข้า Git, mapping R1–R5 — **P02 เริ่มได้โดยไม่ต้องรอ phase อื่น**

---

## 2. Tasks และ verification

T08 กับ T10 สถานะ `planned` ช่อง "ผลจริง" = ยังไม่รัน · **T01–T07, T09 และ T11 `done`** มีผลจริงบันทึกไว้ · ค่าที่ต้องวัด (metric, เพดานความยาวข้อความ, tolerance, RAM, เวลาโหลด) เขียนไว้เป็นสิ่งที่ต้องวัดแล้วบันทึก **ไม่ใส่ตัวเลขคาดเดาล่วงหน้า**

**ลำดับการทำงาน ไม่ใช่เรียงตามหมายเลข** — ID คงที่ตามที่ตั้งไว้ แต่ลำดับจริงคือ:

```text
T11 (environment)  →  T01 (model)  →  T03 (เพดานข้อความ)
                   ↘               ↘  T04 (inference module)  →  T09 (RAM/เวลาโหลด)
                     T02 (dataset)  →  T05 (evaluate)  →  T08 (tolerance)
                                    ↘  T06 (artifact)  →  T07 (lineage)  →  T10 (storage, รอมติทีม)
```

**T11 ต้องเสร็จก่อน T01 และ T02** เพราะทั้งสอง task ต้องรันโค้ดที่ติดตั้ง dependency แล้ว (ดาวน์โหลด model, อ่าน `config.json`, ดึง dataset) ไม่ใช่งานที่ทำควบคู่กันได้

### P02-T01 — ดึง model และ pin revision พร้อมบันทึก provenance

- **สถานะ:** `done` — ครบทั้ง 4 ข้อใน "Done when" และผ่าน "Check" แล้ว
- **งาน:** ดึง model จากลิงก์ HF ใน Proposal §2 แล้วบันทึกข้อมูลระบุรุ่นลง Git (ตัวไฟล์ไม่เข้า Git ตาม [P01-T03 §7](P01-T03-system-structure.md#7-อะไรเข้า-git-และอะไรไม่เข้า))
- **Done when:**
  - บันทึก **commit SHA ของ revision ที่ใช้** ไม่ใช่แค่ tag `latest` — tag ขยับได้ ทำให้รันซ้ำไม่ได้จริง
  - บันทึก licence CC BY 4.0 และการให้เครดิตตาม Proposal §2
  - **อ่าน label mapping จาก `config.json` ที่ดึงมาจริง** (`id2label`) แล้วบันทึกว่า index ไหนตรงกับ `negative`, `neutral`, `positive` ตาม 3 กลุ่มใน [P01-T02 §3](P01-T02-api-contract.md#3-request-และ-response) — ไม่เดาจากชื่อ
  - บันทึกว่า `score` ที่จะคืนคืออะไร (เช่น ค่าของ class ที่เลือกหลัง softmax) ให้ตรงกับนิยาม "คะแนนของกลุ่มที่เลือก อยู่ระหว่าง 0–1" ใน P01-T02 §3
- **Check:** ดึง revision เดิมซ้ำจาก SHA ที่บันทึกแล้วได้ไฟล์ชุดเดียวกัน · เทียบ mapping ที่บันทึกกับ `config.json`
- **ผลจริง (รัน 2026-10-07):** หลักฐานเต็มใน [reports/P02-T01-model-provenance.md](../../reports/P02-T01-model-provenance.md)
  - **Observed:** pin revision `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` (commit SHA ไม่ใช่ tag `latest`) · บันทึก sha256 ของทั้ง 6 ไฟล์ที่ดึงมา
  - **Observed:** ดึงซ้ำจาก SHA เดิมลง cache directory แยก แล้วเทียบ sha256 ทั้ง 6 ไฟล์ → **ตรงกันทุก byte** (ไม่ได้อาศัย cache เดิม) · cache ชั่วคราวลบแล้ว
  - **Observed:** licence บน Hub card metadata = `cc-by-4.0` **ตรงกับที่ Proposal §2 อ้าง**
  - **Observed:** `config.json` ระบุ `id2label` = `{0: negative, 1: neutral, 2: positive}` ตรงกับ 3 กลุ่มใน P01-T02 §3 — **ไม่ใช่ `LABEL_0/1/2`** จึงไม่ต้องสร้างตาราง map เพิ่ม
  - **Observed:** `score` = `softmax(logits)` ของ class ที่ `argmax` · ผลรวมทุก class = `1.000000` จึงอยู่ในช่วง 0–1 ตาม P01-T02 §3
  - **Decision:** ข้าม `tf_model.h5` (TensorFlow weights ไม่ใช้) ประหยัดการดาวน์โหลดราว 500 MB · ผลข้างเคียง: ใช้ offline ต้องส่ง `allow_patterns` ชุดเดิม
  - **Decision:** ยังไม่เขียน script ใน `src/` รอบนี้ — T04 เป็นเจ้าของ path การโหลด model ที่ evaluation และ API ใช้ร่วมกัน การเขียน loader แยกตอนนี้จะสร้างตรรกะโหลด model สองชุดซึ่ง P01-T03 §4 ห้ามไว้ · วิธีรันซ้ำบันทึกเป็นคำสั่งในรายงานแล้ว
  - **ไฟล์ model ไม่เข้า repo** — อยู่ใน HF cache ของเครื่อง จึงยังไม่ต้องแก้ `.gitignore` รอบนี้ (การจัดลง `artifacts/` เป็นงาน T06)
- **ขึ้นกับ:** **T11** (ต้องมี environment ที่ติดตั้ง dependency แล้วจึงรันได้) · ลิงก์ใน Proposal §2
- **ส่งต่อให้ T03:** repo นี้ **ไม่มี `tokenizer_config.json`** ทำให้ `tokenizer.model_max_length` คืนค่า sentinel `1e30` ซึ่งไม่ใช่เพดานจริง · ค่าที่เป็นหลักฐานคือ `max_position_embeddings = 514` ใน `config.json` → **T03 ต้องยืนยันเพดานจาก config + การทดลองกับ tokenizer จริง ห้ามอ่านจาก `model_max_length`**
- **ส่งต่อให้ T06:** repo นี้มีแต่ `pytorch_model.bin` (pickle) **ไม่มี `model.safetensors`** → T06 ต้องตัดสินว่าจะแปลงเป็น safetensors ตอน package หรือไม่

### P02-T02 — จัด evaluation dataset ให้มี version

- **สถานะ:** `done` — ครบทุกข้อใน "Done when" และผ่าน "Check" ทั้งสองข้อแล้ว
- **งาน:** ดึง Twitter US Airline Sentiment **version 4** จากลิงก์ Kaggle ใน Proposal §2 ลงที่ `data/` ตามโครงสร้างใน [P01-T03 §6](P01-T03-system-structure.md#6-ตำแหน่ง-code-data-model-และ-configuration) แล้วกำหนด evaluation set ที่คงที่
- **Done when:**
  - บันทึก**วิธีได้มา**ของสิทธิ์/credential ที่ต้องใช้ ไม่ใช่ค่า token จริง ให้เพื่อนทำตามได้ ตามจุดตรวจ Reproduction ใน [P01-T03 §10](P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน)
  - บันทึก row count, วิธี split หรือ sample, และ **random seed** — ถ้าไม่มี seed การ evaluate ซ้ำจะเทียบกันไม่ได้
  - บันทึก **hash ของไฟล์ที่ใช้จริง** เพื่อยืนยันว่าเป็นข้อมูลชุดเดียวกัน
  - บันทึกว่า label ของ dataset map กับ 3 กลุ่มของ model อย่างไร (ต่อจาก T01)
  - บันทึกข้อจำกัด licence **CC BY-NC-SA 4.0 (non-commercial + ShareAlike)** และผลต่อสิ่งที่เราเผยแพร่ใน repo
  - ตัวไฟล์ dataset **ไม่เข้า Git** ตาม P01-T03 §7
  - ชุดนี้คือ **versioned test set** เดียวกับที่ [Proposal §3](../../PROPOSAL.md#3-serving-pattern-and-requirements) อ้างถึงตอนวัดเป้า p95 — P03–P04 ใช้ชุดนี้ ไม่สร้างชุดใหม่
- **Check:** ทำตามวิธีที่บันทึกจากเครื่องเปล่าแล้วได้ไฟล์ที่ hash ตรงกัน · ตรวจ Git history ว่าไม่มี Kaggle token หลุดเข้าไปก่อน push ตามจุดตรวจ Secrets ใน [P01-T03 §10](P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) ที่ระบุว่ามี `.gitignore` แล้วไม่ถือว่าปลอดภัยครบ
- **ผลจริง (รัน 2026-10-07):** หลักฐานเต็มใน [reports/P02-T02-evaluation-dataset.md](../../reports/P02-T02-evaluation-dataset.md)
  - **Decision:** ใช้ `kagglehub` ไม่ใช่ `kaggle` CLI · **Source:** `kagglehub` parse handle `.../versions/4` ได้ `version=4, is_versioned=True` ขณะที่ `kaggle datasets download` ไม่มี flag เลือก version (ตรวจ argparse แล้ว) → ตัวเดียวที่ pin **version 4** ตาม Proposal §2 ได้
  - **Observed:** `data/Tweets.csv` 3,421,431 bytes · sha256 `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` · **14,640 แถว** 15 columns
  - **Observed:** `airline_sentiment` มี 3 ค่าคือ `negative` 9,178 / `neutral` 3,099 / `positive` 2,363 — **ชื่อตรงตัวกับ `id2label` ของ model ทั้ง 3 กลุ่ม ไม่ต้องสร้างตารางแปลง**
  - **Observed:** ไม่มีแถว `text` ว่าง ไม่มีแถวไม่มี label ไม่มี label นอก 3 กลุ่ม → การตัดสินใจ "ใช้ทุกแถว ไม่กรอง" ที่วางไว้ล่วงหน้าใช้ได้จริง
  - **Decision:** evaluation set = **ทุกแถวในไฟล์ ไม่ sample ไม่ split ไม่กรองด้วย `airline_sentiment_confidence`** → **ไม่มี random seed ที่เกี่ยวข้องกับการเลือกแถว** เพราะไม่ได้สุ่ม · ถ้า T05/T08 ต้องสุ่มลำดับหรือ batch ต้องบันทึก seed ของขั้นตอนนั้นแยก
  - **Observed (Check 1):** ดึงซ้ำลง `KAGGLEHUB_CACHE` แยก แล้วเทียบ sha256 → **ตรงกันทุก byte** · cache ชั่วคราวลบแล้ว
  - **Observed (Check 2):** ค้น `KGAT_…`, `KAGGLE_KEY=`, `KAGGLE_API_TOKEN=` ใน **ทุก commit ของ Git history** และในไฟล์ที่จะ commit → **ไม่พบ** · `git check-ignore` ยืนยัน `data/Tweets.csv` ถูกกันด้วย `.gitignore:31`
  - **Observed:** เพิ่ม `kagglehub>=1.0.2` ใน dependency group `data` **ไม่ใส่ใน `[project.dependencies]`** เพื่อให้ image ของ P03–P04 ไม่ติด Kaggle client ที่ไม่ได้เรียกตอน inference · ยืนยันด้วย `uv sync --no-default-groups --dry-run`
  - **Observed:** เพิ่ม `data/` และ `artifacts/` ใน `.gitignore` (ปิดช่องว่างที่บันทึกไว้ใน §5 ข้อ 4)
- **ขึ้นกับ:** **T11** (environment) · ลิงก์ใน Proposal §2 · Kaggle credential ของเจ้าของงาน (ได้รับแล้ว 2026-10-07)
- **ส่งต่อให้ T05:** **class imbalance** `negative` 62.7% เทียบ `positive` 16.1% → **accuracy เพียงตัวเดียวทำให้เข้าใจผิด** เพราะเดา `negative` ทั้งหมดได้ 62.7% แล้ว · ควรใช้ macro-F1 และรายงาน per-class ประกอบ · **คุณภาพ label:** 4,195 แถว (28.7%) มี `airline_sentiment_confidence` < 1.0 และ 3,872 แถว (26.4%) < 0.7 → metric ที่วัดได้คือความตรงกับ label ชุดนี้ ไม่ใช่เพดานความสามารถของ model ต้องเขียนกำกับผลทุกครั้ง
- **ส่งต่อให้ T03:** `text` ยาวสุด **186 อักขระ** สั้นกว่าเพดาน 512 token มาก → **dataset นี้จะไม่แตะเพดานเลย** T03 ต้องยืนยันเพดานด้วยข้อความที่สร้างขึ้นเอง และ boundary case ของ API ใน P03 ก็ทดสอบจาก dataset นี้ไม่ได้
- **ข้อจำกัด licence:** CC BY-NC-SA 4.0 เป็น non-commercial + ShareAlike · ยังไม่ประเมินว่าการยกตัวอย่างข้อความจริงลงรายงานติดเงื่อนไข ShareAlike แค่ไหน จึงยังไม่ยกตัวอย่างข้อความใดใน `reports/` · ถ้า T05 ต้องยก ต้องตัดสินเรื่องนี้ก่อน

### P02-T03 — ยืนยันเพดานความยาวข้อความ (ปลด blocker ของ P03)

- **สถานะ:** `done` — บันทึกครบ 3 อย่างใน P01-T02 §7 และผ่าน Check แล้ว
- **งาน:** ตรวจ tokenizer ของ revision ที่ pin ใน T01 แล้วบันทึกผลกลับไปที่ [P01-T02 §7](P01-T02-api-contract.md#7-จุดที่ยังต้องยืนยันและการส่งต่องาน) ตามที่ §7 สั่งไว้
- **Done when:** บันทึกใน P01-T02 ครบ 3 อย่าง — **ค่าที่รองรับ**, **วิธีนับ** (อักขระหรือ token) และ **การรวม special tokens** · ยืนยันพฤติกรรมที่ตกลงแล้วว่า ยาวเกินแล้ว **ปฏิเสธ ไม่ตัดเงียบ ๆ**
- **Check:** ส่งข้อความความยาวที่เพดานและเกินเพดานเข้า tokenizer จริง แล้วเทียบกับค่าที่บันทึก (การตรวจ boundary ผ่าน API เป็นงาน P03)
- **ข้อมูลจาก T01 ที่ต้องใช้:** `tokenizer.model_max_length` **ใช้ไม่ได้** เพราะ repo ไม่มี `tokenizer_config.json` (คืนค่า sentinel `1e30`) · ให้ยึด `max_position_embeddings = 514` ใน `config.json` แล้วทดลองหาเพดาน token จริงรวม special tokens — ดู [reports/P02-T01-model-provenance.md](../../reports/P02-T01-model-provenance.md) §5
- **ข้อมูลจาก T02 ที่ต้องใช้:** ข้อความใน dataset ยาวสุด 186 อักขระ **ไม่แตะเพดาน** → ต้องสร้างข้อความทดสอบเองเพื่อหาเพดาน ไม่ใช้ dataset
- **ผลจริง (รัน 2026-10-07):** หลักฐานเต็มใน [reports/P02-T03-text-length-cap.md](../../reports/P02-T03-text-length-cap.md)
  - **ค่าที่ล็อก:** เนื้อหา **510 tokens** · special tokens **2** (`<s>` + `</s>`) · ความยาวรวม **512 tokens** · **นับ token ไม่ใช่อักขระ**
  - **Observed:** ทดลอง forward ที่ความยาวรวม 510/511/512 ผ่าน · 513 และ 514 พังด้วย `RuntimeError: index 514 is out of bounds for dimension 1 with size 514`
  - **Observed:** ยืนยันซ้ำด้วยข้อความจริงผ่าน tokenizer — 1,527 อักขระ = 512 tokens ผ่าน · 1,530 อักขระ = 513 tokens พัง
  - **Observed:** `tok(text)` **ไม่ตัดให้** คืนความยาวจริง 513 · `tok(text, truncation=True, max_length=512)` **ตัดจริง** → โค้ดของเราต้องไม่ใช้ `truncation=True` เพราะขัดกับ P01-T02 §3
  - **Observed:** อัตราอักขระต่อ token ไม่คงที่ 0.52 (ภาษาไทย) ถึง 3.98 (ตัวอักษรเดียวติดกัน) → **เพดานแบบนับอักขระใช้แทนไม่ได้**
  - **Observed:** บันทึกค่ากลับเข้า [P01-T02](P01-T02-api-contract.md) แล้วใน §1, §3, §6 และ §7 **ในไฟล์เดิม** ไม่สร้างสำเนา
- **ขึ้นกับ:** T01
- **ส่งต่อให้ P03:** ต้อง **นับ token แล้วปฏิเสธก่อนเรียก model** — ถ้าปล่อยถึง model จะได้ `RuntimeError` ซึ่งกลายเป็น `500` ไม่ใช่ `422` ตาม P01-T02 §4 · เพิ่มเข้า checklist §6 ของ P01-T02 แล้ว

### P02-T04 — Shared inference module

- **สถานะ:** `done` — ครบทุกข้อใน "Done when" และ Check ข้อ "evaluation path กับ API path เรียกฟังก์ชันเดียวกัน" ปิดได้แล้วด้วย T05 (ฝั่ง API ตรวจซ้ำอีกครั้งใน P03)
- **งาน:** เขียน module เดียวใน `src/` ที่ทำ preprocess → predict → แปลงผลเป็น sentiment + score ให้ **ทั้ง evaluation และ API เรียกใช้ร่วมกัน** ตาม [P01-T03 §4](P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด) ที่กำหนดว่า "ตอนประเมินทำแบบหนึ่ง ตอนใช้งานจริงทำอีกแบบ" ไม่ได้
- **Done when:**
  - มีจุดเรียกเดียวที่ evaluation script และ API ใช้ร่วม — ไม่มี preprocessing สองชุด
  - คืนค่า `sentiment` ใน 3 กลุ่ม และ `score` อยู่ระหว่าง 0–1 ตาม P01-T02 §3
  - โหลด model **ครั้งเดียวเมื่อ process เริ่ม** แล้วใช้ซ้ำหลาย request ตาม [P01-T03 §3](P01-T03-system-structure.md#3-ส่วนให้บริการ--รับ-feedback-แล้วทำนาย)
  - มีพฤติกรรมชัดเจนเมื่อโหลด model ไม่สำเร็จ (ยกข้อผิดพลาดที่แยกแยะได้) เพื่อให้ P03 ทำ `/ready` คืน `503` และ `/predict` ไม่คืน sentiment ปลอมได้
  - ~~ตกลง interface กับคนที่ 2 ก่อนปิด task~~ → **แทนที่เมื่อ 2026-10-07: คนที่ 1 ล็อก interface เอง คนที่ 2 รับไปใช้** ดูค่าที่ล็อกในผลจริง
  - module ไม่อ่าน environment variable และไม่เรียก Azure เอง — ค่าของ environment รับเข้ามาจากภายนอก ตามการแยก core / configuration / cloud adapter ใน [P01-T03 §4](P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด)
- **Check:** unit test กรณีข้อความปกติ, ข้อความขอบเขต และกรณี model โหลดไม่สำเร็จ · ยืนยันว่า evaluation path กับ API path เรียกฟังก์ชันเดียวกันจริง · ต้องผ่าน `make portability-audit` ตามจุดตรวจ Portability ใน [P01-T03 §10](P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) เมื่อคำสั่งนี้ถูกนิยามแล้ว (ยังไม่มีนิยาม ดู §5 ข้อ 3)
- **ผลจริง (รัน 2026-10-07):** interface ที่ล็อกให้คนที่ 2 ใช้อยู่ใน [reports/P02-T04-inference-interface.md](../../reports/P02-T04-inference-interface.md)
  - **Observed:** สร้าง `src/feedbackpulse/inference.py` (core) และ `src/feedbackpulse/model_files.py` (configuration/prepare) แยกกันตาม P01-T03 §4 · core รับ `model_dir` และ `model_version` เข้ามา **ไม่ไปหาเอง**
  - **Observed:** `ruff check` และ `ruff format --check` ผ่าน · **`pytest -q` ผ่าน 11 tests**
  - **Observed:** ตรวจการแยก core ด้วย grep — ไม่มี `os.environ`, `getenv`, `requests`, `azure`, `boto` ใน `inference.py`
  - **Observed:** **มี preprocessing และ predict ชุดเดียวจริง** — grep `AutoTokenizer`/`from_pretrained`/`softmax`/`argmax` ใน `src/` พบเฉพาะใน `inference.py`
  - **Observed:** ไม่มี `truncation=True` ที่ใดใน `src/` · ข้อความ 511 tokens ได้ `TextTooLong` **ก่อน** ถึง forward pass จึงไม่กลายเป็น `500`
  - **Decision:** `model_version` **รับจากภายนอกตอน `load()`** ไม่ตั้งค่าเอง เพื่อไม่ตัดสินแทน T07 ที่เป็นเจ้าของ scheme
  - **Decision:** ชื่อกลุ่มอ่านจาก `config.json` ของ model ตอน runtime ไม่ hardcode ลำดับ index
  - **Decision:** ยังไม่ทำ batch API — `predict()` รับข้อความเดียว ยังไม่มีผู้ใช้ที่ต้องการ batch · ถ้า T05 ช้าเกินรับได้ **ให้เพิ่ม batch ในโมดูลนี้** ไม่ใช่เขียน loop ที่ tokenize เองใน script ของ T05 เพราะจะเป็น preprocessing สองชุดที่ P01-T03 §4 ห้าม
  - **Observed:** เพิ่ม `[tool.pytest.ini_options]` ใน `pyproject.toml` ตั้ง `pythonpath = ["src"]` เพราะ `src/` ไม่ได้ติดตั้งเป็น package
  - **Observed (ปิด Check แล้ว 2026-10-07):** T05 เขียน `evaluate.py` ที่เรียก `SentimentClassifier.predict()` ทีละข้อความ · grep ยืนยันว่า `evaluate.py` ไม่มี `AutoTokenizer`/`from_pretrained`/`softmax`/`argmax` เลย → **evaluation ใช้เส้นทางเดียวกับที่ API จะใช้จริง** · ฝั่ง API ยังต้องตรวจซ้ำใน P03
  - **ยังครบไม่ได้:** `make portability-audit` ยังไม่มีนิยามใน repo (§5 ข้อ 3)
- **Decision ที่ล็อกแล้ว 3 เรื่อง (คนที่ 1 ตัดสิน 2026-10-07 · คนที่ 2 รับไปใช้ ไม่ต้องตกลงใหม่):**
  1. **วิธี import: ใช้ `PYTHONPATH=/app/src` ไม่ build wheel** · เหตุผล: `pyproject.toml` ตั้ง `package = false` อยู่แล้วจึงไม่ต้องมี build backend · repo นี้มี service เดียวไม่ได้แจกจ่าย library · Docker ตั้ง env ตัวเดียวจบ · ถ้าภายหลังต้องแจกเป็น library ให้เปลี่ยนเป็น installable package แล้วแก้เฉพาะ `pyproject.toml` กับ `Dockerfile`
  2. **map exception → HTTP status ล็อกตามตารางใน [รายงาน §2](../../reports/P02-T04-inference-interface.md)** — `ModelNotReady` → `503`, `InvalidText` และ `TextTooLong` → `422` · ตรงกับ [P01-T02 §4](P01-T02-api-contract.md#4-validation-และ-error-handling) อยู่แล้ว
  3. **ไม่มี batch และไม่มี async** — `predict()` รับข้อความเดียว · API ตาม P01-T02 รับครั้งละหนึ่งข้อความจึงไม่มีผู้ใช้ batch · ถ้า T05 วัดแล้วช้าเกินรับได้ ให้เพิ่ม batch **ในโมดูลนี้** ไม่ใช่เขียน tokenize ซ้ำใน script ของ T05
- **ส่งต่อให้ P03 เพิ่มเติม:** รันโค้ดนี้นอก pytest ต้องตั้ง `PYTHONPATH=src` เอง — `pythonpath` ใน `pyproject.toml` ครอบแค่ pytest ไม่ครอบ `python -m` (เจอตอน T05)
- **ขึ้นกับ:** T01

### P02-T05 — Evaluation step และ metrics

- **สถานะ:** `done` — ครบทุกข้อใน "Done when" และผ่าน Check ทั้งสองข้อแล้ว
- **งาน:** รัน evaluation บน dataset จาก T02 ผ่าน module จาก T04 แล้วออกรายงาน
- **Done when:**
  - **เลือก metric และบันทึกเหตุผล** — P01 ยังไม่ได้กำหนดไว้ ต้องตัดสินใน P02 และต้องเลือกก่อนจึงจะกำหนด tolerance ใน T08 ได้
  - ผลสรุปอยู่ใน `reports/` ตามรูปแบบหลักฐานใน [P01-T03 §11](P01-T03-system-structure.md#11-วิธีเก็บหลักฐานให้สั้นแต่ตรวจได้): *ตรวจอะไร → ใช้รุ่นและเงื่อนไขไหน → คาดหวังอะไร → ได้ผลอะไร → มีข้อจำกัดอะไร*
  - รายงานระบุ model revision, dataset version/hash และ code version ที่ใช้
  - รายงานระบุข้อจำกัดว่า **ผลนี้อธิบายประสิทธิภาพบน airline feedback ไม่ได้พิสูจน์ว่าได้ผลเท่ากันทุกอุตสาหกรรม** (Proposal §2)
  - ตรวจว่ารายงานไม่มี secret หรือข้อมูลอ่อนไหวก่อนเข้า Git (P01-T03 §7)
  - ถ้ายกตัวอย่างข้อความจาก dataset ในรายงาน ต้องสอดคล้องกับ [P01-T02 §5](P01-T02-api-contract.md#5-access-control-และข้อมูลที่ไม่เก็บ) ที่กำหนดว่าไม่บันทึก feedback เต็มข้อความ และกับ licence CC BY-NC-SA ของ dataset — ยกเท่าที่จำเป็นต่อการอธิบายผล
- **Check:** เทียบตัวเลขในรายงานกับ output ของการรันจริง · ตรวจว่า metric คำนวณจาก label mapping ที่บันทึกใน T01/T02
- **ผลจริง (รัน 2026-10-07 10:51 UTC · 674.1 วินาที · จาก commit `40dcb77` tree สะอาด):** หลักฐานใน [reports/P02-T05-evaluation.md](../../reports/P02-T05-evaluation.md) · ผล machine-readable ใน [`P02-T05-evaluation-result.json`](../../reports/P02-T05-evaluation-result.json)
  - **Decision:** **macro-F1 เป็น metric หลัก** ไม่ใช่ accuracy · เหตุผล: T02 พบว่า evaluation set เป็น `negative` 62.7% การตอบ `negative` ทุกข้อได้ accuracy 0.6271 แล้ว แต่ macro-F1 แค่ 0.2569 · มี test ที่พิสูจน์จุดนี้
  - **Observed:** 14,640 แถว ข้ามไป 0 แถว · **accuracy 0.8100 · macro-F1 0.7606** · macro precision 0.7453 · macro recall 0.7825
  - **Observed (per-class):** `negative` F1 0.8867 (n=9,178) · `neutral` F1 **0.6150** (n=3,099 — อ่อนที่สุด) · `positive` F1 0.7800 (n=2,363)
  - **Observed (Check 1):** คำนวณใหม่จาก confusion matrix ด้วย `scikit-learn 1.9.1` และด้วย `trace/total` → **ตรงกันทุกตัวถึง 1e-12** ทั้ง accuracy, macro-F1 และ per-class · ผลรวม confusion matrix = 14,640 ตรงกับ `total`
  - **Observed (Check 2):** ไฟล์ผลบันทึก `labels_from_model_config = ["negative","neutral","positive"]` อ่านจาก `config.json` ตอน runtime · `model_revision` และ `dataset_sha256` ในไฟล์ผล **ตรงกับ T01 และ T02 ทุกตัว**
  - **Observed:** `scikit-learn` ใช้แบบ ephemeral (`uv run --with`) **ไม่เพิ่มเข้า lockfile** เพราะใช้ตรวจเท่านั้น
  - **Observed:** ไม่มี secret และ **ไม่มีข้อความจาก dataset แม้แต่แถวเดียว** ในรายงานหรือไฟล์ผล → ปิดประเด็น licence CC BY-NC-SA ที่ T02 ทิ้งไว้
  - **Decision:** ไม่เพิ่ม batch — วัดได้ราว 44 ms/ข้อความ รวม 648 วินาที ซึ่งรับได้สำหรับงานที่รันตอน release · ตัวเลขนี้**ไม่ใช่ latency ของ API**
  - **Observed:** รันซ้ำจาก tree ที่สะอาดแล้ว — ไฟล์ผลบันทึก `commit 40dcb77`, `dirty: false`, `uncommitted: []` → **ย้อนกลับไปหา code รุ่นที่ให้ผลนี้ได้จาก commit** · ใช้เป็น lineage ของ T07 และฐานเทียบของ T08 ได้
  - **Observed (ข้อมูลให้ T08):** รันสองรอบบนเครื่องเดียวกันได้ **metric ตรงกันทุกหลักและ confusion matrix ตรงทุกช่อง** ต่างแค่เวลา 648.1 → 674.1 วินาที · **ยังไม่ปิด T08** เพราะยังไม่ทดสอบจาก fresh state และยังไม่ทดสอบข้ามเครื่อง
  - **ข้อจำกัด:** `model_version` ในไฟล์ผลเป็นค่าชั่วคราว `unversioned-3216a57f2a0d` เพราะ scheme เป็นงานของ T07
- **ขึ้นกับ:** T02, T04
- **ส่งต่อให้ T08:** ไฟล์ JSON ออกแบบให้เทียบสองรอบได้ตรง ๆ · รอบเทียบใช้เวลาราว 650–680 วินาที · **ยังไม่มีค่า tolerance** — T08 เป็นผู้กำหนดจากผลที่วัดได้ โดยต้องตรวจเพิ่มสองเงื่อนไขที่ยังไม่ทำ: รันจาก fresh state และรันข้ามเครื่อง

### P02-T06 — Lock รูปแบบชุด artifact

- **สถานะ:** `done` — รูปแบบล็อกแล้ว และผ่าน Check ว่าโหลดได้โดยไม่พึ่งไฟล์นอกชุด
- **งาน:** กำหนดว่าชุด model ที่ package แล้วประกอบด้วยอะไรและวางโครงสร้างอย่างไร โดยเก็บไว้ที่ `artifacts/` ตามโครงสร้างใน [P01-T03 §6](P01-T03-system-structure.md#6-ตำแหน่ง-code-data-model-และ-configuration) และหน้าที่ของส่วนเตรียม model ใน [P01-T03 §2](P01-T03-system-structure.md#2-ส่วนเตรียม-model--ทำก่อนนำรุ่นนั้นไปใช้งาน) ("model, tokenizer และ configuration")
- **Done when:** ระบุรายการไฟล์ในชุด artifact, โครงสร้างภายใน และ **version id ที่ใช้อ้างถึงชุดนั้น** — โดย**ไม่ผูกกับบริการเก็บไฟล์** เพื่อไม่ปิดทางเลือกของ T10 และไม่ปิดทางเลือกวิธีนำเข้า container ของ P03–P04
- **Check:** ประกอบชุด artifact จากขั้นตอนที่เขียนไว้ แล้วโหลดด้วย module จาก T04 ได้สำเร็จโดยไม่ต้องพึ่งไฟล์นอกชุด
- **ผลจริง (รัน 2026-10-07):** หลักฐานใน [reports/P02-T06-artifact-layout.md](../../reports/P02-T06-artifact-layout.md) · ชุดที่สร้าง `sentiment-6e7ff9fbc17c` (477 MiB)
  - **Decision (โครงสร้าง):** `artifacts/<artifact_id>/` มี `manifest.json`, `upstream-model-card.md` และโฟลเดอร์ `model/` ที่มีเฉพาะสิ่งที่ loader อ่าน — แยก `model/` เพราะ `transformers` สแกนทั้ง directory ที่ส่งให้
  - **Decision (`artifact_id`):** **content-addressed** `sentiment-<sha256 ของรายการ ชื่อไฟล์:hash ใน model/ 12 ตัวแรก>` → input เดิมให้ id เดิมเสมอ สองคนที่ package แยกกันบอกได้ว่าได้ของชุดเดียวกัน โดยไม่ต้องมีทะเบียนกลาง (สำคัญเพราะยังไม่เลือกบริการเก็บใน T10) · **ไม่ใช่ `model_version`** ซึ่งเป็นงาน T07
  - **Decision (safetensors):** **แปลง `pytorch_model.bin` เป็น `model.safetensors`** · เหตุผลหลัก: `.bin` เป็น pickle ที่รันโค้ดตอน deserialize ขณะที่ Proposal §5 ระบุว่า P05 จะ**ตั้งใจทำให้ artifact ใช้งานไม่ได้** การโหลดไฟล์ที่ถูกแก้ไขจึงไม่ควรเป็นการรันโค้ดจากไฟล์นั้น · `safetensors` เป็น dependency ต่อเนื่องของ `transformers` อยู่แล้ว ไม่เพิ่มของใหม่
  - **Observed:** ชุดที่แปลงมี **201 tensor** ขณะที่ต้นทางมี 204 — หายไป `roberta.embeddings.position_ids` (buffer) และ pooler 2 ตัวที่ head ไม่เรียก · **บันทึกใน manifest เพราะชุดนี้ไม่ใช่สำเนาต้นทาง**
  - **Observed (ยืนยันว่าการแปลงไม่เปลี่ยนผล):** `state_dict` ตรงกันทั้ง 201 ตัว **เท่ากันทุก bit** · logits บนข้อความจริง 300 แถวจาก evaluation set ต่างกันสูงสุด **0.000e+00** · sentiment ที่ทำนายต่างกัน **0/300**
  - **Observed (Check):** ตั้ง `HF_HOME` ชี้ไป directory ว่าง + `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` แล้วโหลดสำเร็จ → **ไม่แตะ cache และไม่ต่อ network** · `labels` และ `max_content_tokens` (510) ตรงกับ T01/T03 · ทำนาย 3 ข้อความอ้างอิงได้ค่าตรงกับที่ T01 บันทึก
  - **Observed:** hash ของไฟล์ที่คัดลอกทั้ง byte ตรงกับที่ T01 บันทึกทุกตัว จึงตรวจย้อนถึงต้นทางได้ตรง ๆ
  - **Decision:** **ไม่เพิ่ม `tokenizer_config.json`** เข้าชุด แม้ T01 พบว่าการไม่มีไฟล์นี้ทำให้ `model_max_length` เป็น sentinel · เพราะจะมีแหล่งความจริงสองที่สำหรับเพดาน ขณะที่ `SentimentClassifier` คำนวณจาก `config.json` อยู่แล้ว
  - **แก้เพิ่ม 2026-10-07 (ของเราเอง ไม่ใช่ของ P03):** `SentimentClassifier.load()` ตั้ง `tokenizer.model_max_length` เป็นค่าที่ derive ได้ (512) · วัดได้ก่อนแก้ว่าข้อความ 603 tokens เทียบกับ sentinel ให้ `False` คือ **ตรวจไม่เจอว่าเกิน** จะทำให้กลายเป็น `500` แทน `422` · ตัวเลขยังมาจาก `config.json` ที่เดียว ไม่ได้เพิ่มไฟล์ที่เราแต่ง · มี test กำกับ · **ที่ยังกันไม่ได้:** เปิด `model/` ด้วย `AutoTokenizer` ตรง ๆ โดยไม่ผ่านโมดูลเรา ยังเจอ sentinel
  - **แก้เพิ่ม 2026-10-07:** `package_artifact.py` เลิกคำนวณเพดานซ้ำ — โหลดชุดที่ build เสร็จด้วย `SentimentClassifier` แล้วอ่าน `labels` กับ `max_content_tokens` จากที่นั่น · ปิดการมีตรรกะเดียวกันสองที่ และทำให้ **build ล้มทันทีถ้าชุดโหลดไม่ได้**
  - **ไม่ผูกกับบริการเก็บ:** manifest **ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ปิดทางเลือกของ T10 และ P03–P04
- **ขึ้นกับ:** T01
- **ส่งต่อให้ T10:** ชุด artifact **477 MiB** (`model.safetensors` 498,615,868 bytes) — ใช้ประเมินค่าเก็บข้อมูลกับงบ USD 15
- **ส่งต่อให้ T09:** ยังไม่ได้วัดว่า safetensors โหลดเร็วกว่า `.bin` จริงเท่าไร — อ้างตามคุณสมบัติของรูปแบบ ไม่ใช่จากการวัดของเรา
- **ส่งต่อให้ P03 และ P05 (ไม่ใช่งานของ P02):** `manifest.json` มี hash ของทุกไฟล์ให้ตรวจความครบถ้วนได้ · **P02 ผลิตข้อมูลให้แล้ว ส่วนการเรียกตรวจตอน startup เป็นของ P03 (`P01-T02 §4`) และการตัดสินว่าอะไรนับเป็น artifact ใช้ไม่ได้เป็นของ P05 (`Proposal §5`)** · ไม่เขียนฟังก์ชันตรวจไว้ล่วงหน้าเพราะยังไม่มีผู้ใช้และจะต้องเดา call site กับ error semantics ของเขา

### P02-T07 — Lock lineage metadata และ `model_version` scheme

- **สถานะ:** `done` — scheme ล็อกแล้ว และผ่าน Check ไล่ย้อนครบ 26/26
- **งาน:** กำหนดรูปแบบ `model_version` ที่ API จะคืน และ metadata ที่ทำให้ย้อนกลับไปหาต้นทางได้
- **Done when:**
  - `model_version` ย้อนกลับไปหา **code, evaluation data, model revision ต้นทาง, ผล evaluation, run ID และ environment** ได้ ตาม R1 และ [P01-T02 §3](P01-T02-api-contract.md#3-request-และ-response) ที่กำหนดว่าต้องเป็น "รุ่นของ model artifact ที่กำลังใช้งานจริง... ไม่ใช่ชื่อเวอร์ชันตัวอย่างที่ใส่ค้างไว้"
  - ค่า `"sentiment-v1"` ใน P01-T02 เป็นเพียงตัวอย่างรูปแบบ — ต้องแทนด้วย scheme จริง
  - ส่วน environment ใช้ค่าที่ T11 กำหนด (Python version + lockfile) — Proposal §4 สั่งให้ version environment ด้วย แต่ตาราง R1 ใน P01-T03 §9 ไม่ได้ระบุไว้ ดู §5 ข้อ 9
  - **แจ้ง scheme ที่ตกลงให้คนที่ 2** เพราะ API ต้องคืนค่านี้
- **Check:** หยิบ `model_version` หนึ่งค่าแล้วไล่ย้อนไปถึงไฟล์/commit/รายงานต้นทางได้ครบทุกชั้น
- **ผลจริง (รัน 2026-10-07):** หลักฐานใน [reports/P02-T07-model-version-lineage.md](../../reports/P02-T07-model-version-lineage.md) · version แรก `sentiment-6e7ff9fbc17c-c18ecbc6`
  - **Decision (scheme):** `sentiment-<artifact_id>-<lineage digest 8 ตัว>` · 3 ส่วนเพราะ `artifact_id` ตรงกลางทำให้เห็นทันทีว่าสอง release ใช้ weights ชุดเดียวกันหรือไม่ ซึ่งต้องอ่านเร็วตอน rollback (R2) · **content-addressed ไม่ใช่ตัวนับ** จึงไม่ต้องมีทะเบียนกลางแจกเลข (สำคัญเพราะยังไม่เลือกบริการเก็บใน T10)
  - **Decision:** digest ครอบ **code commit และ environment ไม่ใช่แค่ weights** เพราะ `predict()` ขึ้นกับโค้ดของเราด้วย ถ้าเปลี่ยน preprocessing แล้ว version ไม่เปลี่ยน version นั้นจะโกหก
  - **Observed:** lineage record ที่ `reports/registry/<version>.json` เก็บ 6 ส่วน — artifact (+ hash ทุกไฟล์), source_model (+ hash ต้นทางรวม `pytorch_model.bin`), evaluation_data, code commit, environment (+ hash ของ `uv.lock`), evaluation (+ hash ของไฟล์ผล) · **ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ผูกกับ T10
  - **Observed (guard ทำงานจริง):** `register()` ปฏิเสธรอบแรกเพราะตรวจพบว่า `inference.py` และ `evaluate.py` เปลี่ยนไปตั้งแต่ commit `40dcb77` ที่ eval รอบก่อนรัน → **บังคับให้รัน evaluation ใหม่** ก่อนออก version
  - **Observed (Check):** เริ่มจากสตริง `model_version` ค่าเดียว ไล่ย้อน 8 ชั้น **ผ่าน 26/26** โดย**คำนวณ hash จากไฟล์จริงทุกตัว** ไม่ใช่อ่านค่าที่บันทึกมาเทียบกับตัวเอง — artifact 7/7 · ไฟล์ต้นทาง 7/7 · dataset 2/2 · code 3/3 (commit มีจริง, อยู่ในสาย HEAD, ไฟล์ตัดสินผลไม่เปลี่ยน) · `uv.lock` · ผล evaluation 3/3 · โหลดแล้วทำนายได้และคืน version นี้
  - **Observed:** ผล evaluation **เหมือนกัน 3 รอบติด** ที่ commit `40dcb77` / `35e881f` / `ad382f1` ทุก metric และ confusion matrix ตรงทุกหลัก ต่างแค่เวลา 648.1 / 674.1 / 678.9 วินาที → ยืนยันว่าการแก้ `tokenizer.model_max_length` **ไม่เปลี่ยนผลทำนาย**
  - **Observed (bug ที่เจอและแก้):** `_git()` ทำ `.strip()` กับ porcelain output ซึ่งกินช่องว่างนำหน้าของบรรทัดแรก ทำให้ path ที่ parse ได้หายตัวอักษรแรก (`src/...` → `rc/...`) · อยู่ใน code ที่ commit ไปแล้วตอน T05 · แก้แล้วพร้อม regression test
  - **Observed:** ย้าย git helper ไป `gitinfo.py` เพื่อให้ eval result และ registry entry ตอบ "commit ไหน" แบบเดียวกัน ไม่มีตรรกะซ้ำสองที่
- **ขึ้นกับ:** T06
- **ส่งต่อให้ P03:** ต้อง**อ่าน `model_version` จาก registry entry หรือ configuration แล้วส่งเข้า `load()`** ไม่ hardcode · `load()` รับค่าที่ส่งมาเฉย ๆ ถ้าส่งผิด API จะคืนค่าผิดโดยไม่มีอะไรจับได้ — registry มี hash ทุกไฟล์ให้ตรวจ แต่**การเรียกตรวจตอน startup เป็นของ P03** ไม่ใช่ P02
- **ส่งต่อให้ P04:** ตอนนี้มี version เดียว และ `main()` ปฏิเสธถ้าเจอ artifact มากกว่าหนึ่งชุดแทนที่จะเดา · การจัดการหลาย version พร้อมกันจำเป็นตอน rollback ซึ่งยังไม่ได้ออกแบบ
- **ส่งต่อให้ T10:** registry เป็นไฟล์ใน Git ไม่ใช่บริการ · ถ้า T10 เลือกบริการที่มี registry ของตัวเอง **ยังไม่ได้ประเมินว่าจะย้ายหรือทำสองที่**

### P02-T08 — กำหนด tolerance ของการ evaluate ซ้ำ

- **สถานะ:** `planned`
- **งาน:** รัน pipeline ทั้งชุดซ้ำ เทียบผลสองรอบ แล้วกำหนด tolerance ที่จะใช้ตัดสินผ่าน/ไม่ผ่าน ตามที่ [P01-T03 §10](P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) ระบุว่าเป็น "ค่าที่ยังต้องตรวจใน P02"
- **Done when:**
  - กำหนด tolerance จาก **ผลที่วัดได้จริง** — P01-T03 §10 สั่งว่า "ไม่เดาตัวเลขล่วงหน้า"
  - บันทึกเงื่อนไขการรัน (เครื่อง, เวอร์ชัน dependency, seed) ที่ค่านี้ใช้ได้
  - การยืนยันผลต้องไม่ใช่การรันตรรกะเดิมซ้ำเพียงอย่างเดียว — ใช้การคำนวณคนละทาง, reference result หรือ invariant ประกอบ ตาม `.agents/protocols/evidence-and-verification.md`
- **Check:** รัน pipeline ซ้ำจาก fresh state แล้วผลต่างอยู่ในช่วง tolerance ที่กำหนด
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T05, T07
- **หมายเหตุ:** ค่านี้ใช้ตัดสินผ่าน/ไม่ผ่านของการ evaluate ซ้ำใน P02 (เกณฑ์ R1) **ไม่ใช่ของที่ P03 รอ** — ของที่ P03 รออยู่ในส่วนที่ 4

### P02-T09 — วัด RAM และเวลาโหลด model

- **สถานะ:** `done` — วัดแล้ว 5 samples ใน process ใหม่ทุกรอบ และผ่าน Check ว่าซ้ำได้ในช่วงแคบ
- **งาน:** วัดหน่วยความจำที่ใช้และเวลาโหลด model เพื่อเป็น input ให้ P03–P04 กำหนดขนาด container ตาม [P01-T03 §5](P01-T03-system-structure.md#5-เหตุผลและข้อแลกเปลี่ยน) ที่ระบุว่า "ต้องวัด RAM และเวลาเริ่มระบบใน P02–P03"
- **Done when:** มีตัวเลข RAM และเวลาโหลดที่วัดจากการรันจริง พร้อมเงื่อนไขการวัด ส่งต่อให้คนที่ 2 · **ไม่ใส่ค่าคาดเดาไว้ก่อน**
- **Check:** วัดซ้ำได้ผลใกล้เคียง และบันทึกช่วงที่เห็น
- **ผลจริง (วัด 2026-10-07 บน macOS 15.5 arm64):** หลักฐานใน [reports/P02-T09-load-and-memory.md](../../reports/P02-T09-load-and-memory.md)
  - **Observed (เวลาเริ่มระบบ):** import `torch`+`transformers` **1.629 s** · อ่าน weights **1.309 s** · **รวม 2.934 s** (median จาก 5 samples) · แยกสองช่วงเพราะเวลา import ไม่ขึ้นกับขนาด weights แต่เวลาอ่านขึ้น
  - **Observed (หน่วยความจำ — ค่าสูงสุดไม่ได้อยู่ที่การโหลด):** Python เปล่า ~11 MiB → หลัง import ~217 MiB → หลังโหลด weights ~341 MiB → **หลังทำนายครั้งแรก ~706 MiB** · **การทำนายครั้งแรกกินเพิ่มอีกราว 365 MiB มากกว่าการอ่าน weights ทั้งก้อน** เพราะ torch จอง workspace ของ forward pass
  - **Observed (ตามความยาวข้อความ):** ข้อความสั้น 5 tokens ขึ้นถึง **712 MiB** แล้วคงที่ · ข้อความที่เพดาน 510 tokens ขึ้นถึง **748 MiB** แล้วคงที่ · ค่าที่ 25 กับ 50 ครั้งเท่ากันทั้งสองกรณี → **ไม่พบสัญญาณว่ารั่ว**
  - **Observed:** **ข้อความที่เพดานช้ากว่า 3.6 เท่า** — 184 ms เทียบ 51 ms
  - **Observed (หักล้างข้ออ้างของ T06):** safetensors อ่าน weights 1.292–1.316 s เทียบ `pytorch_model.bin` 1.294–1.328 s และ RAM เท่ากัน → **ไม่ต่างกัน** · T06 เคยอ้างว่า safetensors โหลดเร็วกว่าโดยกำกับไว้ว่าไม่ใช่ผลวัดของเรา **แก้ใน T06 แล้ว** · การตัดสินใจแปลงยังคงเดิมเพราะเหตุผลหลักคือไม่ต้อง unpickle
  - **Observed (Check):** ช่วงที่เห็นใน 5 samples — import 1.7% · อ่าน weights 2.2% · เริ่มระบบรวม 0.7% · peak RSS 1.5% · เวลาทำนาย 6.0% · ทุกค่าซ้ำได้ในช่วงแคบ
  - **Decision:** วัดใน **process ใหม่ทุก sample** เพราะโหลดซ้ำใน process เดียวจะใช้ allocator ที่อุ่นแล้วและไฟล์ที่ map อยู่แล้ว ซึ่งรายงานถูกกว่าครั้งแรกที่ container เจอจริง
  - **Decision:** รายงานเป็น **peak RSS** เพราะ container limit ตั้งจากค่าสูงสุด · `ru_maxrss` เป็น bytes บน macOS แต่ KiB บน Linux — โค้ดแปลงตาม platform เพราะผิดแล้วคลาด 1024 เท่า
- **ขึ้นกับ:** T04
- **ส่งต่อให้ P04 (สำคัญ):** **sizing memory ที่ ~750 MiB ไม่ใช่ 341 MiB** ไม่งั้น container จะตายตอน request แรก · Proposal §6 สมมติ 2 vCPU / 4 GiB ซึ่งเหลือที่เยอะ แต่ถ้าจะลดเพื่อประหยัดงบ **อย่าต่ำกว่าราว 1 GiB โดยไม่ทดสอบ** · รันคำสั่งเดียวกันใน container ได้: `PYTHONPATH=/app/src python -m feedbackpulse.measure` · **ทดสอบเป้า p95 ด้วยข้อความยาวด้วย** เพราะต่างกัน 3.6 เท่า
- **ส่งต่อให้ T10:** เวลาอ่าน weights 1.3 วินาทีไม่ขึ้นกับรูปแบบไฟล์ แต่ขึ้นกับว่าไฟล์อยู่ที่ไหน · ถ้าเลือกดาวน์โหลดตอน start เวลาดึง 476 MiB จะบวกเข้าเวลาเริ่มระบบ
- **ข้อจำกัดที่ใหญ่ที่สุด:** วัดบน **macOS arm64 ไม่ใช่ใน container บน Azure** · `safetensors` ใช้ mmap ทำให้ peak RSS (341 MiB) ต่ำกว่าขนาดไฟล์ (476 MiB) เพราะหน้าที่ยังไม่ถูกแตะไม่ถูกนับ — **บน Linux หน้าที่ mmap อาจถูกนับเข้า cgroup limit ทำให้ตัวเลขจริงสูงกว่านี้ ยังไม่ได้ทดสอบ** · CPU ต่าง architecture และไม่มี memory limit มาบีบ จึงยังไม่รู้ว่าจำกัดที่ค่าใดจะถูก OOM kill
- **หมายเหตุ:** การทดสอบเป้า p95 ≤ 3 วินาที ที่ 2 concurrent requests เป็นงาน P03–P04 ไม่ใช่ T09 · ตัวเลขใน Proposal §3 เป็นเป้าหมาย ยังไม่ใช่ผลวัด

### P02-T10 — ตัดสินที่เก็บ model artifact

- **สถานะ:** `planned`
- **งาน:** [P01-T03 §12](P01-T03-system-structure.md#12-สิ่งที่ยังไม่-lock-และงานคุยถัดไป) และ [§7](P01-T03-system-structure.md#7-อะไรเข้า-git-และอะไรไม่เข้า) มอบการตัดสิน "บริการหรือรูปแบบเก็บ model artifact ที่ทีมจะใช้ร่วมกัน" ให้ P02 · **คนที่ 1 ตัดสินเองตามอำนาจที่ได้รับเมื่อ 2026-10-07** แล้วบันทึกเหตุผลและ trade-off ให้คนที่ 2 รับไปทำต่อ
- **Done when:**
  - เทียบอย่างน้อย 2 ทางเลือกด้าน **cold start, งบ USD 15 ต่อ 30 วัน (Proposal §6), ความง่ายในการ rollback (R2) และผลต่อการสาธิตเหตุขัดข้องของคนที่ 3 (R4)**
  - ~~ทีมเลือก~~ → **คนที่ 1 เลือกและบันทึกเหตุผลลง `reports/` พร้อมอัปเดต P01-T03 §12** แล้วแจ้งคนที่ 2 และคนที่ 3
  - **ต้องปิดก่อนคนที่ 2 เริ่มงานที่ต้องนำ model เข้า container ใน P03**
- **Check:** มีการตัดสินที่บันทึกแล้ว และทางเลือกที่เลือกรองรับชุด artifact จาก T06 ได้
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T06

### P02-T11 — ตั้ง convention: Python version, dependency manager, lockfile

- **สถานะ:** `done` — ตั้งใช้งานได้ ตรวจแล้ว และล็อกเป็น convention ของทีมโดยคนที่ 1
- **งาน:** repo ยังไม่มี `requirements.txt` หรือ `pyproject.toml` ขณะที่ `.gitignore` ชี้ว่าจะใช้ Python + pytest + ruff · `.agents/AGENTS.template.md` สั่งให้ "ใช้ package manager และ lockfile convention ของ repo" ซึ่งยังไม่มี จึงต้องตั้งในรอบนี้
- **Done when:** ~~ตกลงร่วมกับคนที่ 2~~ → **แทนที่เมื่อ 2026-10-07: คนที่ 1 ล็อก convention เอง คนที่ 2 ใช้ชุดเดียวกันใน P03–P04** · ล็อกเวอร์ชัน dependency ที่กระทบผล inference
- **Check:** ติดตั้งจาก lockfile บนเครื่องเปล่าแล้วรัน pipeline ได้
- **ผลจริง (รัน 2026-10-07 บน macOS 15.5 arm64):**
  - **Decision (ล็อกแล้ว):** `uv` + `uv.lock` + Python `3.13` — ผู้ใช้เลือกเมื่อ 2026-10-07 · **เป็น convention ของทีม คนที่ 2 ใช้ชุดนี้ใน P03–P04** · runtime ที่ใส่ container ใช้ `uv sync --no-default-groups` (ไม่รวม group `dev` และ `data`)
  - **Source:** `uv pip compile` ยืนยันว่า `torch==2.14.1`, `transformers==5.19.0`, `numpy==2.5.3` resolve ได้เหมือนกันทั้ง Python 3.12 และ 3.13 → ML stack ไม่บังคับเวอร์ชัน จึงเลือก 3.13 ที่มีในเครื่องแล้ว
  - **Observed:** สร้าง `pyproject.toml`, `.python-version`, `uv.lock` (59 packages) · ลบ `.venv` แล้ว `uv sync --frozen` ติดตั้งกลับได้จาก lockfile เพียงอย่างเดียว
  - **Observed:** เวอร์ชันที่ติดตั้งจริงตรงกับที่ pin — `torch 2.14.1`, `transformers 5.19.0`, `numpy 2.5.3`, `tokenizers 0.23.2`, Python `3.13.11` · dev tools `ruff 0.16.10`, `pytest 9.1.1`
  - **Observed (ปิด Check แล้ว):** หลัง T04 มีโค้ดจริง `uv run pytest -q` ผ่าน 11 tests จาก environment ที่ติดตั้งด้วย `uv sync --frozen` → ยืนยันว่าติดตั้งจาก lockfile แล้วรันโค้ดของโครงการได้ · การรัน pipeline ครบวงจรยังรอ T05
  - **ข้อจำกัดที่รู้แล้ว:** pin ถึงระดับ Python **minor** (`3.13`) ไม่ใช่ patch · เครื่องนี้ใช้ `3.13.11` (Anaconda build) เครื่องอื่นอาจได้ patch อื่น → ต้องบันทึก patch ที่ใช้จริงลงรายงานตาม T05 และ T08
  - **ยังไม่เพิ่ม dependency ของ task ถัดไป** — Kaggle client (T02) และ metric library (T05) จะเพิ่มเมื่อถึง task นั้น ตามกติกา "add only the dependency required for the current feature" ใน `.agents/AGENTS.template.md`
- **ขึ้นกับ:** ไม่ขึ้นกับ task อื่น แต่ **ต้องทำก่อน T01 และ T02** — เป็น task แรกของ phase นี้
- **หมายเหตุ:** *ไม่มีเอกสารใดมอบ task นี้ให้ P02 โดยตรง* — เป็นการตีความของผู้เขียนแผนว่าต้องมีก่อนจึงจะรัน task อื่นซ้ำได้ และเป็นกลไกที่ใช้ version environment ตาม Proposal §4

---

## 3. Evidence และ decision ที่ยังค้าง

| เรื่อง | สถานะ | ใครตัดสิน |
|---|---|---|
| รูปแบบชุด artifact | **P02 lock** (T06) | คนที่ 1 |
| Lineage metadata และ `model_version` | **P02 lock** (T07) | คนที่ 1 (แจ้งคนที่ 2) |
| เพดานความยาวข้อความ | **P02 วัดแล้วบันทึกกลับ P01-T02 §7** (T03) | คนที่ 1 |
| Tolerance การ evaluate ซ้ำ | **P02 วัดแล้วกำหนด** (T08) | คนที่ 1 |
| Metric ที่ใช้ตัดสิน | **P02 เลือกและบันทึกเหตุผล** (T05) | คนที่ 1 |
| บริการเก็บ artifact | **pending — คนที่ 1 ตัดสิน** (T10) | คนที่ 1 |
| Python/dependency convention | **ล็อกแล้ว** — uv + uv.lock + Python 3.13 (T11) | คนที่ 1 |
| วิธีนำ model เข้า container | **P02 ป้อนข้อมูลให้ คนที่ 2 ตัดสิน** — P01-T03 §12 ไม่ได้มอบการตัดสินให้ P02 แต่ระบุว่ารอ "ข้อมูลจากการตรวจ model" ซึ่ง P02 เป็นคนหามาจาก T06 และ T09 · งานจริงอยู่ P03–P04 | คนที่ 2 |
| CPU/RAM, จำนวน process/instance | **P02 ป้อนผลวัดจาก T09 ให้ คนที่ 2 ตัดสิน** | คนที่ 2 |

**ไฟล์นี้ไม่มีผลวัดของเราเลย** — ยังไม่มีค่า metric, เพดานความยาวข้อความ, tolerance, RAM หรือเวลาโหลด เพราะทุกตัวต้องวัดใน task ที่ยังไม่รัน

ตัวเลขที่ปรากฏในไฟล์นี้มาจากเอกสารอื่นทั้งหมด และไม่ใช่ผลวัดของ P02:

- **เป้าหมายจาก Proposal:** p95 ≤ 3 วินาที ที่ 2 concurrent requests (§3) และงบ USD 15 ต่อ 30 วัน (§6) — เป็นเป้าและกรอบงบ ไม่ใช่ผลวัด
- **ค่าที่ระบุไว้ในแหล่งต้นทาง:** dataset version 4, licence CC BY 4.0 และ CC BY-NC-SA 4.0
- **ค่าที่ตกลงไว้แล้วใน P01-T02:** HTTP status เช่น `503`

---

## 4. สิ่งที่ P03 รอจาก P02

ตาม [overview](../../overview-plan.md) ที่ระบุว่าไม่ต้องรอ phase ก่อนจบทั้งหมด คนที่ 2 เริ่ม P03 ส่วนรับส่งข้อมูลได้เลย และรอ 3 อย่างนี้จาก P02:

1. **เพดานความยาวข้อความ** (T03) — ใช้ทำ validation และ boundary test · P01-T02 §7 ระบุเองว่าต้องยืนยันใน P02 ก่อนตรวจ boundary cases ใน P03 และ checklist §6 เขียนว่า "หลังยืนยันเพดานใน P02"
2. **Interface ของ inference module** (T04) — จุดเรียก, input/output, ข้อผิดพลาดตอน model ไม่พร้อม · *ข้อนี้เป็นการตีความของผู้เขียนแผน* ไม่ใช่ข้อความใน P01 โดยตรง — P01-T03 §4 สั่งแค่ว่า evaluation กับ API ต้องใช้วิธีเตรียมข้อความและทำนายชุดเดียวกัน จึงต้องตกลง interface กันก่อนเขียนทั้งสองฝั่ง
3. **`model_version` scheme จริง** (T07) — ค่าที่ `/predict` ต้องคืน ตาม P01-T02 §3 ที่กำหนดว่าต้องเป็นรุ่นที่ใช้งานจริงและย้อน lineage ได้

**เส้นแบ่งกับ P03 ที่ต้องยืนยันกับคนที่ 2:** [overview](../../overview-plan.md) มอบให้คนที่ 1 ทั้ง "ดูแล P02" และ "ส่วนเชื่อม model เข้า API" ขณะที่ P03 ทั้งก้อนเป็นของคนที่ 2 · **คนที่ 1 ตัดสินแล้วเมื่อ 2026-10-07: P02 รับผิดชอบ module และ loader ที่โหลด model แล้วให้ผลทำนาย (T04) ส่วนการเขียน endpoint, validation และ response เป็นของ P03** คนที่ 2 รับไปทำต่อตามนี้

**เงื่อนไขบังคับอีกข้อ:** การเลือกที่เก็บ artifact (T10) **ต้องปิดก่อนคนที่ 2 เริ่มงานที่ต้องนำ model เข้า container ใน P03** · ส่วน Python/dependency convention (T11) **ล็อกแล้ว** — คนที่ 2 ใช้ `uv` + `uv.lock` + Python 3.13 ชุดเดียวกัน และใช้ `uv sync --no-default-groups` สำหรับ runtime ใน container

---

## 5. Handoff และรายการที่ต้องคุยกับทีม

**สถานะรอบนี้:** **T04 `done`** — shared inference module พร้อม interface ที่ล็อกให้คนที่ 2 · **T05 `done`** — evaluate 14,640 แถวได้ **macro-F1 0.7606 / accuracy 0.8100** ยืนยันเลขด้วย scikit-learn และรันซ้ำจาก tree สะอาดได้เลขเดิมทุกหลัก · **T11 `done`** — uv + uv.lock + Python 3.13 เป็น convention ของทีม · รวม 27 tests ผ่านหมด · **T01 เสร็จ** — pin revision, ยืนยัน licence, อ่าน label mapping จาก config จริง, ยืนยันนิยาม `score` · **T02 เสร็จ** — pin dataset version 4, นิยาม evaluation set 14,640 แถว, ยืนยัน label ตรงกับ model · **T03 เสร็จ** — ล็อกเพดาน 510 content tokens และบันทึกกลับเข้า P01-T02 แล้ว **ปลด blocker ให้ P03** · หลักฐานทั้งสามอยู่ใน `reports/` · ยังไม่เขียนโค้ดใน `src/` (ตาม [P01-T03 §8](P01-T03-system-structure.md#8-หน้าที่ของเอกสารและการสร้างไฟล์) ที่ห้ามสร้างโฟลเดอร์เปล่ารอล่วงหน้า)

**งานที่เหลือและ blocker:** T08 กับ T10 ยังเป็น `planned` · T01–T07, T09 และ T11 `done` · **ไม่มี blocker** · ผล evaluation ผูกกับ commit `40dcb77` ที่ tree สะอาด จึงใช้เป็น lineage ของ T07 และฐานเทียบของ T08 ได้แล้ว · T11 `in_progress` ปิดไม่ได้จนคนที่ 2 ยืนยัน convention · **ไม่มี blocker ที่หยุดงานฝั่งเราอยู่** · T10 รอมติทีมแต่บล็อกแค่คนที่ 2 ตอนนำ model เข้า container

**Next action:** **T10** (ตัดสินที่เก็บ artifact — มีข้อมูลครบแล้วจาก T06 ขนาด 477 MiB และ T09 เวลาเริ่มระบบ 2.9 วินาที) → ปิดด้วย **T08** (tolerance) ซึ่งต้องรันจาก fresh state และข้ามเครื่อง: ส่ง `pyproject.toml` กับ `uv.lock` ให้คนที่ 2 ยืนยัน T11 และขอมติ T10 · **rotate Kaggle token** เพราะค่าเดิมอยู่ใน transcript แล้ว

ช่องว่างที่พบระหว่างอ่านเอกสาร P01 — **ยังไม่แก้ไฟล์ของคนอื่นในรอบนี้** ต้องคุยกันก่อน:

1. **P01-T03 §6 ใช้ absolute path `/home/nirvana/feedbackpulse/`** ซึ่งขัดกับจุดตรวจ Reproduction ใน §10 เองที่ห้ามพึ่งไฟล์เฉพาะเครื่องผู้พัฒนา → เสนอแก้เป็น path แบบ repo-relative
2. **Proposal §7 ยังเป็น `[Name]` ทั้ง 3 ช่อง** ขณะที่ overview แบ่งคนที่ 1/2/3 ไว้แล้ว → ควรผูกชื่อกับหน้าที่ให้ตรงกัน
3. **`make portability-audit` เป็นจุดตรวจบังคับใน P01-T03 §10 แต่ไม่มี Makefile และไม่มีนิยามว่าตรวจอะไร** → ต้องถามที่มาและเกณฑ์ผ่านจากเอกสารวิชา
4. **`.gitignore` ยังไม่กัน `data/` และ `artifacts/`** ที่ P02 จะเป็นคนสร้าง ขณะที่ P01-T03 §7 ตกลงว่า dataset และไฟล์ model ขนาดใหญ่ต้องไม่เข้า Git → ต้องเพิ่ม rule ตอนสร้างสองโฟลเดอร์นี้จริง และตรวจว่าไม่ติดไป Docker image ด้วย
5. **ไม่มีหลักฐานลายลักษณ์อักษรเรื่องขอบเขต pretrained-only** — [overview](../../overview-plan.md) อ้างคำยืนยันของอาจารย์ที่ผู้ใช้แจ้งเมื่อ 2026-10-05 ขณะที่เอกสารกลางยังใช้คำว่า *automated training* → ควรเก็บหลักฐานไว้กันถูกถามเรื่อง R1 ตอน defense
6. **Model card:** Proposal §4 นับเป็น deliverable แต่ overview วางไว้ P06 ทั้งที่ข้อมูลที่ต้องใช้เกิดใน P02 ทั้งหมด → ถามทีมว่าให้ P02 ร่างไว้เลยไหม
7. **`.agents/AGENTS.template.md` ยังไม่ถูก copy เป็น `AGENTS.md` ที่ root** ตามที่ comment หัวไฟล์สั่ง → agent ที่ค้นหาตามมาตรฐานจะไม่เห็นกติกาชุดนี้
8. **ยังไม่ตกลงว่าใครอัปเดต `overview-plan.md`** และกติกา PR/merge เข้า `codex/bootstrap` (ใคร review, ใคร approve) — skill `plan-and-track-work` ระบุว่าถ้าหลายคนทำพร้อมกันต้องตกลงผู้อัปเดต overview เพราะ Markdown ไม่ใช่ระบบ lock

9. **ตาราง R1 ใน `P01-T03` §9 ไม่ได้ระบุ `environment`** ขณะที่ Proposal §4 สั่งให้ version "code, evaluation data, model revision, **and environment**" → แผนนี้ยึดตาม Proposal (ดูส่วนที่ 1 และ T07) แต่ควรแก้ตาราง R1 ให้ตรงกัน และยืนยันกับทีมว่า R1 ของเราครอบ environment ด้วย
10. **จำนวนขั้นของ pipeline ไม่ตรงกันระหว่างเอกสาร** — [overview](../../overview-plan.md) เขียน "evaluate → package → register" (3 ขั้น) แต่ `P01-T03` §9 เขียน "prepare → evaluate → package → register" (4 ขั้น) → แผนนี้ยึดตาม P01-T03 ควรแก้ overview ให้ตรง

11. **`overview-plan.md` ยังอ้างว่าเพดานความยาวข้อความค้างอยู่ ทั้งที่ T03 ปิดแล้ว** — บรรทัด 51 ("สถานะยังเป็น `in_progress` เพราะตัวเลขเพดานความยาวข้อความรอยืนยันกับ model ใน P02") และบรรทัด 57 ("ส่วนเพดานความยาวข้อความของ P01-T02 ยังรอผลตรวจ model ใน P02") · **ยังไม่แก้เพราะยังไม่ได้รับอำนาจกับไฟล์นี้** · `P01-T03` §10 แก้แล้วเมื่อ 2026-10-07 ให้เหลือแค่ tolerance (T08) ที่ค้างจริง
12. **`P01-T03` บรรทัด 168 ใช้คำว่า "ยังติดตาม"** สำหรับเพดานความยาวข้อความ ซึ่งอ่านเหมือนยังไม่ปิด · ตัวชี้ไป P01-T02 §7 ยังถูก แต่ถ้อยคำควรเปลี่ยนเป็นว่าค่าอยู่ที่นั่นแล้ว

**Recheck เมื่อกลับมาทำต่อ:** ถ้า revision ของ model หรือ version ของ dataset เปลี่ยน ต้องตรวจ T01–T03, T05 และ T08 ใหม่ — ผลการวัดรอบก่อนไม่ใช่หลักฐานของรุ่นใหม่
