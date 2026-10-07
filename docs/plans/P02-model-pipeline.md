# P02 — Model และ pipeline ที่ทำซ้ำได้

- แผนหลัก: [Overview plan](../../overview-plan.md) · ขอบเขตโครงการ: [Proposal](../../PROPOSAL.md)
- ข้อตกลงที่ต้องทำตาม: [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md)
- สถานะ P02: `planned`
- เจ้าของ: คนที่ 1 — Model และ evaluation (ตาม [overview](../../overview-plan.md))
- อัปเดต: 2026-10-07

ไฟล์นี้เป็น **แผนของ phase P02** ยังไม่ใช่หลักฐานว่าทำอะไรเสร็จแล้ว ทุก task ด้านล่างสถานะ `planned` และช่อง "ผลจริง" ระบุว่า *ยังไม่รัน* ทั้งหมด การเขียนแผนเสร็จไม่ได้แปลว่าเริ่ม implement แล้ว

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

ทุก task สถานะ `planned` · ช่อง "ผลจริง" = ยังไม่รัน · ค่าที่ต้องวัด (metric, เพดานความยาวข้อความ, tolerance, RAM, เวลาโหลด) เขียนไว้เป็นสิ่งที่ต้องวัดแล้วบันทึก **ไม่ใส่ตัวเลขคาดเดาล่วงหน้า**

**ลำดับการทำงาน ไม่ใช่เรียงตามหมายเลข** — ID คงที่ตามที่ตั้งไว้ แต่ลำดับจริงคือ:

```text
T11 (environment)  →  T01 (model)  →  T03 (เพดานข้อความ)
                   ↘               ↘  T04 (inference module)  →  T09 (RAM/เวลาโหลด)
                     T02 (dataset)  →  T05 (evaluate)  →  T08 (tolerance)
                                    ↘  T06 (artifact)  →  T07 (lineage)  →  T10 (storage, รอมติทีม)
```

**T11 ต้องเสร็จก่อน T01 และ T02** เพราะทั้งสอง task ต้องรันโค้ดที่ติดตั้ง dependency แล้ว (ดาวน์โหลด model, อ่าน `config.json`, ดึง dataset) ไม่ใช่งานที่ทำควบคู่กันได้

### P02-T01 — ดึง model และ pin revision พร้อมบันทึก provenance

- **สถานะ:** `planned`
- **งาน:** ดึง model จากลิงก์ HF ใน Proposal §2 แล้วบันทึกข้อมูลระบุรุ่นลง Git (ตัวไฟล์ไม่เข้า Git ตาม [P01-T03 §7](P01-T03-system-structure.md#7-อะไรเข้า-git-และอะไรไม่เข้า))
- **Done when:**
  - บันทึก **commit SHA ของ revision ที่ใช้** ไม่ใช่แค่ tag `latest` — tag ขยับได้ ทำให้รันซ้ำไม่ได้จริง
  - บันทึก licence CC BY 4.0 และการให้เครดิตตาม Proposal §2
  - **อ่าน label mapping จาก `config.json` ที่ดึงมาจริง** (`id2label`) แล้วบันทึกว่า index ไหนตรงกับ `negative`, `neutral`, `positive` ตาม 3 กลุ่มใน [P01-T02 §3](P01-T02-api-contract.md#3-request-และ-response) — ไม่เดาจากชื่อ
  - บันทึกว่า `score` ที่จะคืนคืออะไร (เช่น ค่าของ class ที่เลือกหลัง softmax) ให้ตรงกับนิยาม "คะแนนของกลุ่มที่เลือก อยู่ระหว่าง 0–1" ใน P01-T02 §3
- **Check:** ดึง revision เดิมซ้ำจาก SHA ที่บันทึกแล้วได้ไฟล์ชุดเดียวกัน · เทียบ mapping ที่บันทึกกับ `config.json`
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** **T11** (ต้องมี environment ที่ติดตั้ง dependency แล้วจึงรันได้) · ลิงก์ใน Proposal §2

### P02-T02 — จัด evaluation dataset ให้มี version

- **สถานะ:** `planned`
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
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** **T11** (ต้องมี environment ที่ติดตั้ง dependency แล้วจึงรันได้) · ลิงก์ใน Proposal §2

### P02-T03 — ยืนยันเพดานความยาวข้อความ (ปลด blocker ของ P03)

- **สถานะ:** `planned`
- **งาน:** ตรวจ tokenizer ของ revision ที่ pin ใน T01 แล้วบันทึกผลกลับไปที่ [P01-T02 §7](P01-T02-api-contract.md#7-จุดที่ยังต้องยืนยันและการส่งต่องาน) ตามที่ §7 สั่งไว้
- **Done when:** บันทึกใน P01-T02 ครบ 3 อย่าง — **ค่าที่รองรับ**, **วิธีนับ** (อักขระหรือ token) และ **การรวม special tokens** · ยืนยันพฤติกรรมที่ตกลงแล้วว่า ยาวเกินแล้ว **ปฏิเสธ ไม่ตัดเงียบ ๆ**
- **Check:** ส่งข้อความความยาวที่เพดานและเกินเพดานเข้า tokenizer จริง แล้วเทียบกับค่าที่บันทึก (การตรวจ boundary ผ่าน API เป็นงาน P03)
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T01
- **หมายเหตุ:** แก้ P01-T02 §7 **ในไฟล์เดิม** ไม่สร้างสำเนาข้อตกลงชุดใหม่ ([P01-T02 §1](P01-T02-api-contract.md#1-สถานะและขอบเขต))

### P02-T04 — Shared inference module

- **สถานะ:** `planned`
- **งาน:** เขียน module เดียวใน `src/` ที่ทำ preprocess → predict → แปลงผลเป็น sentiment + score ให้ **ทั้ง evaluation และ API เรียกใช้ร่วมกัน** ตาม [P01-T03 §4](P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด) ที่กำหนดว่า "ตอนประเมินทำแบบหนึ่ง ตอนใช้งานจริงทำอีกแบบ" ไม่ได้
- **Done when:**
  - มีจุดเรียกเดียวที่ evaluation script และ API ใช้ร่วม — ไม่มี preprocessing สองชุด
  - คืนค่า `sentiment` ใน 3 กลุ่ม และ `score` อยู่ระหว่าง 0–1 ตาม P01-T02 §3
  - โหลด model **ครั้งเดียวเมื่อ process เริ่ม** แล้วใช้ซ้ำหลาย request ตาม [P01-T03 §3](P01-T03-system-structure.md#3-ส่วนให้บริการ--รับ-feedback-แล้วทำนาย)
  - มีพฤติกรรมชัดเจนเมื่อโหลด model ไม่สำเร็จ (ยกข้อผิดพลาดที่แยกแยะได้) เพื่อให้ P03 ทำ `/ready` คืน `503` และ `/predict` ไม่คืน sentiment ปลอมได้
  - **ตกลง interface กับคนที่ 2** ก่อนปิด task: ชื่อจุดเรียก, ชนิด input/output, ข้อผิดพลาดที่โยน
  - module ไม่อ่าน environment variable และไม่เรียก Azure เอง — ค่าของ environment รับเข้ามาจากภายนอก ตามการแยก core / configuration / cloud adapter ใน [P01-T03 §4](P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด)
- **Check:** unit test กรณีข้อความปกติ, ข้อความขอบเขต และกรณี model โหลดไม่สำเร็จ · ยืนยันว่า evaluation path กับ API path เรียกฟังก์ชันเดียวกันจริง · ต้องผ่าน `make portability-audit` ตามจุดตรวจ Portability ใน [P01-T03 §10](P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) เมื่อคำสั่งนี้ถูกนิยามแล้ว (ยังไม่มีนิยาม ดู §5 ข้อ 3)
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T01

### P02-T05 — Evaluation step และ metrics

- **สถานะ:** `planned`
- **งาน:** รัน evaluation บน dataset จาก T02 ผ่าน module จาก T04 แล้วออกรายงาน
- **Done when:**
  - **เลือก metric และบันทึกเหตุผล** — P01 ยังไม่ได้กำหนดไว้ ต้องตัดสินใน P02 และต้องเลือกก่อนจึงจะกำหนด tolerance ใน T08 ได้
  - ผลสรุปอยู่ใน `reports/` ตามรูปแบบหลักฐานใน [P01-T03 §11](P01-T03-system-structure.md#11-วิธีเก็บหลักฐานให้สั้นแต่ตรวจได้): *ตรวจอะไร → ใช้รุ่นและเงื่อนไขไหน → คาดหวังอะไร → ได้ผลอะไร → มีข้อจำกัดอะไร*
  - รายงานระบุ model revision, dataset version/hash และ code version ที่ใช้
  - รายงานระบุข้อจำกัดว่า **ผลนี้อธิบายประสิทธิภาพบน airline feedback ไม่ได้พิสูจน์ว่าได้ผลเท่ากันทุกอุตสาหกรรม** (Proposal §2)
  - ตรวจว่ารายงานไม่มี secret หรือข้อมูลอ่อนไหวก่อนเข้า Git (P01-T03 §7)
  - ถ้ายกตัวอย่างข้อความจาก dataset ในรายงาน ต้องสอดคล้องกับ [P01-T02 §5](P01-T02-api-contract.md#5-access-control-และข้อมูลที่ไม่เก็บ) ที่กำหนดว่าไม่บันทึก feedback เต็มข้อความ และกับ licence CC BY-NC-SA ของ dataset — ยกเท่าที่จำเป็นต่อการอธิบายผล
- **Check:** เทียบตัวเลขในรายงานกับ output ของการรันจริง · ตรวจว่า metric คำนวณจาก label mapping ที่บันทึกใน T01/T02
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T02, T04

### P02-T06 — Lock รูปแบบชุด artifact

- **สถานะ:** `planned`
- **งาน:** กำหนดว่าชุด model ที่ package แล้วประกอบด้วยอะไรและวางโครงสร้างอย่างไร โดยเก็บไว้ที่ `artifacts/` ตามโครงสร้างใน [P01-T03 §6](P01-T03-system-structure.md#6-ตำแหน่ง-code-data-model-และ-configuration) และหน้าที่ของส่วนเตรียม model ใน [P01-T03 §2](P01-T03-system-structure.md#2-ส่วนเตรียม-model--ทำก่อนนำรุ่นนั้นไปใช้งาน) ("model, tokenizer และ configuration")
- **Done when:** ระบุรายการไฟล์ในชุด artifact, โครงสร้างภายใน และ **version id ที่ใช้อ้างถึงชุดนั้น** — โดย**ไม่ผูกกับบริการเก็บไฟล์** เพื่อไม่ปิดทางเลือกของ T10 และไม่ปิดทางเลือกวิธีนำเข้า container ของ P03–P04
- **Check:** ประกอบชุด artifact จากขั้นตอนที่เขียนไว้ แล้วโหลดด้วย module จาก T04 ได้สำเร็จโดยไม่ต้องพึ่งไฟล์นอกชุด
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T01

### P02-T07 — Lock lineage metadata และ `model_version` scheme

- **สถานะ:** `planned`
- **งาน:** กำหนดรูปแบบ `model_version` ที่ API จะคืน และ metadata ที่ทำให้ย้อนกลับไปหาต้นทางได้
- **Done when:**
  - `model_version` ย้อนกลับไปหา **code, evaluation data, model revision ต้นทาง, ผล evaluation, run ID และ environment** ได้ ตาม R1 และ [P01-T02 §3](P01-T02-api-contract.md#3-request-และ-response) ที่กำหนดว่าต้องเป็น "รุ่นของ model artifact ที่กำลังใช้งานจริง... ไม่ใช่ชื่อเวอร์ชันตัวอย่างที่ใส่ค้างไว้"
  - ค่า `"sentiment-v1"` ใน P01-T02 เป็นเพียงตัวอย่างรูปแบบ — ต้องแทนด้วย scheme จริง
  - ส่วน environment ใช้ค่าที่ T11 กำหนด (Python version + lockfile) — Proposal §4 สั่งให้ version environment ด้วย แต่ตาราง R1 ใน P01-T03 §9 ไม่ได้ระบุไว้ ดู §5 ข้อ 9
  - **แจ้ง scheme ที่ตกลงให้คนที่ 2** เพราะ API ต้องคืนค่านี้
- **Check:** หยิบ `model_version` หนึ่งค่าแล้วไล่ย้อนไปถึงไฟล์/commit/รายงานต้นทางได้ครบทุกชั้น
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T06

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

- **สถานะ:** `planned`
- **งาน:** วัดหน่วยความจำที่ใช้และเวลาโหลด model เพื่อเป็น input ให้ P03–P04 กำหนดขนาด container ตาม [P01-T03 §5](P01-T03-system-structure.md#5-เหตุผลและข้อแลกเปลี่ยน) ที่ระบุว่า "ต้องวัด RAM และเวลาเริ่มระบบใน P02–P03"
- **Done when:** มีตัวเลข RAM และเวลาโหลดที่วัดจากการรันจริง พร้อมเงื่อนไขการวัด ส่งต่อให้คนที่ 2 · **ไม่ใส่ค่าคาดเดาไว้ก่อน**
- **Check:** วัดซ้ำได้ผลใกล้เคียง และบันทึกช่วงที่เห็น
- **ผลจริง:** ยังไม่รัน
- **ขึ้นกับ:** T04
- **หมายเหตุ:** การทดสอบเป้า p95 ≤ 3 วินาที ที่ 2 concurrent requests เป็นงาน P03–P04 ไม่ใช่ T09 · ตัวเลขใน Proposal §3 เป็นเป้าหมาย ยังไม่ใช่ผลวัด

### P02-T10 — เสนอตัวเลือกที่เก็บ model artifact ให้ทีมตัดสิน

- **สถานะ:** `planned`
- **งาน:** [P01-T03 §12](P01-T03-system-structure.md#12-สิ่งที่ยังไม่-lock-และงานคุยถัดไป) และ [§7](P01-T03-system-structure.md#7-อะไรเข้า-git-และอะไรไม่เข้า) มอบการตัดสิน "บริการหรือรูปแบบเก็บ model artifact ที่ทีมจะใช้ร่วมกัน" ให้ P02 แต่เพราะเป็น **ของที่ทีมใช้ร่วมกัน** และกระทบ architecture กับงบ จึงเสนอให้ทีมตัดสิน ไม่ตัดสินคนเดียว
- **Done when:**
  - เสนออย่างน้อย 2 ทางเลือกพร้อม trade-off ด้าน **cold start, งบ USD 15 ต่อ 30 วัน (Proposal §6), ความง่ายในการ rollback (R2) และผลต่อการสาธิตเหตุขัดข้องของคนที่ 3 (R4)**
  - ทีมเลือกและบันทึกผลกลับเข้า P01-T03 §12 ในไฟล์เดิม
  - **ต้องปิดก่อนคนที่ 2 เริ่มงานที่ต้องนำ model เข้า container ใน P03**
- **Check:** มีมติที่บันทึกแล้ว และทางเลือกที่เลือกรองรับชุด artifact จาก T06 ได้
- **ผลจริง:** ยังไม่รัน — **pending decision**
- **ขึ้นกับ:** T06

### P02-T11 — ตั้ง convention: Python version, dependency manager, lockfile

- **สถานะ:** `planned`
- **งาน:** repo ยังไม่มี `requirements.txt` หรือ `pyproject.toml` ขณะที่ `.gitignore` ชี้ว่าจะใช้ Python + pytest + ruff · `.agents/AGENTS.template.md` สั่งให้ "ใช้ package manager และ lockfile convention ของ repo" ซึ่งยังไม่มี จึงต้องตั้งในรอบนี้
- **Done when:** ตกลง Python version, dependency manager และ lockfile **ร่วมกับคนที่ 2** เพราะ P03–P04 ใช้ชุดเดียวกัน · ล็อกเวอร์ชัน dependency ที่กระทบผล inference
- **ถ้าคนที่ 2 ยังตอบไม่ได้:** ตั้ง environment พร้อม lockfile ใช้งานก่อนเพื่อไม่ให้ T01 และ T02 ค้าง แล้วนำค่าที่ใช้จริงไปขอมติให้เป็น convention ร่วมทีมภายหลัง · **ไม่ถือว่า T11 เสร็จจนกว่าทีมจะยืนยัน** เพราะ P03–P04 ต้องใช้ชุดเดียวกัน
- **Check:** ติดตั้งจาก lockfile บนเครื่องเปล่าแล้วรัน pipeline ได้
- **ผลจริง:** ยังไม่รัน
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
| บริการเก็บ artifact | **pending — ขอมติทีม** (T10) | ทีม |
| Python/dependency convention | **pending — ตกลงกับคนที่ 2** (T11) | คนที่ 1 + คนที่ 2 |
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

**เส้นแบ่งกับ P03 ที่ต้องยืนยันกับคนที่ 2:** [overview](../../overview-plan.md) มอบให้คนที่ 1 ทั้ง "ดูแล P02" และ "ส่วนเชื่อม model เข้า API" ขณะที่ P03 ทั้งก้อนเป็นของคนที่ 2 · แผนนี้ตีความว่า **P02 รับผิดชอบ module และ loader ที่โหลด model แล้วให้ผลทำนาย (T04) ส่วนการเขียน endpoint, validation และ response เป็นของ P03** — *ยังไม่ได้ตกลงกับคนที่ 2 จึงยังไม่ถือเป็นข้อตกลง*

**เงื่อนไขบังคับอีกข้อ:** การเลือกที่เก็บ artifact (T10) **ต้องปิดก่อนคนที่ 2 เริ่มงานที่ต้องนำ model เข้า container ใน P03** ไม่ใช่แค่ "ควรคุยแต่เนิ่น ๆ" · ส่วน Python/dependency convention (T11) **ต้องเสร็จก่อน P02 เริ่ม T01** และควรตกลงให้ตรงกับที่คนที่ 2 จะใช้ใน P03–P04 ตั้งแต่รอบแรก

---

## 5. Handoff และรายการที่ต้องคุยกับทีม

**สถานะรอบนี้:** เขียนแผน P02 เสร็จ ยังไม่เริ่ม implement ยังไม่ดึง model หรือ dataset ยังไม่สร้างโฟลเดอร์โค้ด (ตาม [P01-T03 §8](P01-T03-system-structure.md#8-หน้าที่ของเอกสารและการสร้างไฟล์) ที่ห้ามสร้างโฟลเดอร์เปล่ารอล่วงหน้า)

**งานที่เหลือและ blocker:** ทุก task (T01–T11) ยังเป็น `planned` ไม่มีส่วนใดเสร็จ · blocker เดียวที่บล็อกการเริ่มคือ **T11** ซึ่งรอให้ตกลง Python version กับคนที่ 2 (มีทางออกชั่วคราวใน T11) ส่วน T10 รอมติทีมแต่ไม่บล็อก T01

**Next action:** เริ่มที่ **T11** (environment) เพราะ T01 และ T02 รันไม่ได้ก่อนมันเสร็จ · ขอมติ T10 ขนานไปได้เพราะไม่บล็อก T01 · ถ้าคนที่ 2 ยังตอบ T11 ไม่ได้ ใช้ทางออกใน T11 คือตั้ง environment ใช้งานก่อนแล้ว lock เป็น convention ร่วมทีมภายหลัง

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

**Recheck เมื่อกลับมาทำต่อ:** ถ้า revision ของ model หรือ version ของ dataset เปลี่ยน ต้องตรวจ T01–T03, T05 และ T08 ใหม่ — ผลการวัดรอบก่อนไม่ใช่หลักฐานของรุ่นใหม่
