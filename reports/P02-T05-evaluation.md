# P02-T05 — ผล evaluation

- Task: [P02-T05 ใน phase plan](../docs/plans/P02-model-pipeline.md) · ผลแบบ machine-readable: [`P02-T05-evaluation-result.json`](P02-T05-evaluation-result.json)
- รันเสร็จ: 2026-10-07 10:51 UTC · ใช้เวลา 674.1 วินาที (11.2 นาที) · **รันจาก tree ที่สะอาด**
- เครื่อง: macOS 15.5 arm64 · Python 3.13.11 · `torch 2.14.1` · `transformers 5.19.0` · `numpy 2.5.3` · `tokenizers 0.23.2`

---

## 1. ตรวจอะไร

วัดว่า model รุ่นที่ pin ไว้ทำนาย evaluation set ที่ pin ไว้ได้ตรงกับ label แค่ไหน และบันทึกให้ย้อนกลับไปหา code, data และ model ต้นทางได้ ตามเกณฑ์ **R1** ใน [P01-T03 §9](../docs/plans/P01-T03-system-structure.md#9-จุดตรวจและหลักฐานตามเกณฑ์อาจารย์)

## 2. ใช้รุ่นและเงื่อนไขไหน

| รายการ | ค่า | ตรงกับ |
|---|---|---|
| Model revision | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` | [P02-T01](P02-T01-model-provenance.md) ✓ |
| Dataset | `crowdflower/twitter-airline-sentiment/versions/4` · `data/Tweets.csv` | [P02-T02](P02-T02-evaluation-dataset.md) ✓ |
| Dataset sha256 | `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` | [P02-T02](P02-T02-evaluation-dataset.md) ✓ |
| Labels (อ่านจาก `config.json` ของ model) | `negative`, `neutral`, `positive` | [P02-T01](P02-T01-model-provenance.md) ✓ |
| เพดานข้อความที่ใช้ตรวจ | 510 content tokens | [P02-T03](P02-T03-text-length-cap.md) ✓ |
| Code commit | `40dcb77b5402ad23d74529e13e2589663217905b` | `dirty: false`, `uncommitted: []` — **ย้อนกลับไปหา code รุ่นนี้จาก commit ได้** |

**วิธีรันซ้ำ:**

```bash
PYTHONPATH=src uv run python -m feedbackpulse.evaluate
```

สคริปต์ตรวจ sha256 ของ `data/Tweets.csv` ก่อนเริ่มทุกครั้ง และ **โยน `DatasetMismatch` ถ้าไม่ตรง** เพื่อไม่ให้รายงานผลจากไฟล์คนละชุดโดยไม่รู้ตัว

**evaluation ใช้เส้นทางเดียวกับที่ API จะใช้** — `evaluate.py` เรียก `SentimentClassifier.predict()` ทีละข้อความ ไม่ได้ tokenize เอง ตามที่ [P01-T03 §4](../docs/plans/P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด) กำหนด

## 3. คาดหวังอะไร

ไม่มีเป้าตัวเลขที่เอกสารกำหนดไว้ล่วงหน้า — Proposal ไม่ได้ตั้งเกณฑ์คุณภาพ จึงใช้ **baseline ที่คำนวณจาก class balance** เป็นจุดเทียบ: ถ้าตอบ `negative` ทุกข้อจะได้ accuracy 0.6271 และ macro-F1 0.2569 · ผลที่ใช้ได้ต้องดีกว่านี้อย่างชัดเจน ไม่ใช่แค่เกิน accuracy ของการเดา

**metric ที่เลือกและเหตุผล:** **macro-F1 เป็นตัวหลัก** เพราะ evaluation set เป็น `negative` 62.7% การอ่าน accuracy อย่างเดียวจะทำให้ model ที่ละเลยสองกลุ่มเล็กดูดีเกินจริง · รายงาน accuracy, macro-F1/precision/recall, per-class และ confusion matrix ประกอบกัน

## 4. ได้ผลอะไร

**14,640 แถว · ข้ามไป 0 แถว**

| Metric | ค่า | baseline เดา `negative` ทุกข้อ |
|---|---:|---:|
| Accuracy | **0.8100** | 0.6271 |
| **Macro-F1** | **0.7606** | 0.2569 |
| Macro precision | 0.7453 | — |
| Macro recall | 0.7825 | — |

### Per-class

| Label | Precision | Recall | F1 | support |
|---|---:|---:|---:|---:|
| `negative` | 0.9153 | 0.8599 | 0.8867 | 9,178 |
| `neutral` | 0.6163 | 0.6137 | **0.6150** | 3,099 |
| `positive` | 0.7043 | 0.8739 | 0.7800 | 2,363 |

### Confusion matrix

แถว = label จริง · คอลัมน์ = ที่ model ทำนาย

| | → negative | → neutral | → positive |
|---|---:|---:|---:|
| **negative** | **7,892** | 966 | 320 |
| **neutral** | 650 | **1,902** | 547 |
| **positive** | 80 | 218 | **2,065** |

`neutral` เป็นกลุ่มที่อ่อนที่สุด (F1 0.6150) และความผิดพลาดกระจายไปทั้งสองทาง — 650 แถวที่เป็น `neutral` ถูกทำนายเป็น `negative` และ 547 แถวเป็น `positive` · ส่วน `positive` มี recall สูง (0.8739) แต่ precision ต่ำกว่า (0.7043) เพราะรับ `neutral` เข้ามาผิด 218 แถว

### ผลการตรวจ (Check ของ T05)

**เทียบเลขในรายงานกับการคำนวณคนละทาง** — คำนวณใหม่จาก confusion matrix ที่บันทึกไว้ ด้วย `scikit-learn 1.9.1` และด้วย `trace/total` สำหรับ accuracy:

| ตรวจ | ผล |
|---|---|
| ผลรวม confusion matrix = `total` | 14,640 = 14,640 ✓ |
| accuracy เทียบ `trace/total` | ตรงกันถึง 1e-12 ✓ |
| macro-F1 เทียบ sklearn | ตรงกันถึง 1e-12 ✓ |
| per-class precision/recall/F1/support เทียบ sklearn | ตรงกันทุกตัวถึง 1e-12 ✓ |

`scikit-learn` ใช้แบบ ephemeral (`uv run --with scikit-learn`) **ไม่เพิ่มเข้า lockfile** เพราะใช้ตรวจเท่านั้น ไม่ใช่ของที่ runtime ต้องมี

**ตรวจว่า metric คำนวณจาก label mapping ที่บันทึกไว้** — ไฟล์ผลบันทึก `labels_from_model_config = ["negative","neutral","positive"]` ซึ่งอ่านจาก `config.json` ของ model ตอน runtime และตรงกับที่ [P02-T01](P02-T01-model-provenance.md) บันทึก · `model_revision` และ `dataset_sha256` ในไฟล์ผลตรงกับ T01 และ T02 ทุกตัว

**ไม่มี secret หรือข้อมูลอ่อนไหวในรายงาน** — ไฟล์ผลเก็บเฉพาะตัวเลขนับและ metadata ของรุ่น ไม่มี token และ **ไม่มีข้อความจาก dataset แม้แต่แถวเดียว**

## 5. มีข้อจำกัดอะไร และส่งต่ออะไร

**ผลนี้อธิบายประสิทธิภาพบน airline feedback ไม่ได้พิสูจน์ว่าได้ผลเท่ากันทุกอุตสาหกรรม** ตามที่ [Proposal §2](../PROPOSAL.md#2-model-and-dataset) ระบุไว้เอง · ข้อความในชุดนี้เป็นทวีตสั้นเกี่ยวกับสายการบิน ยาวสุด 186 อักขระ

**ตัวเลขนี้คือความตรงกับ label ชุดนี้ ไม่ใช่เพดานความสามารถของ model** — [P02-T02](P02-T02-evaluation-dataset.md) พบว่า 4,195 แถว (28.7%) มี `airline_sentiment_confidence` ต่ำกว่า 1.0 และ 3,872 แถว (26.4%) ต่ำกว่า 0.7 · label มาจาก crowdsourcing ที่ผู้ตัดสินไม่เห็นตรงกันทุกแถว เราเลือกไม่กรองเพื่อไม่ให้ตัวเลขดูดีขึ้นด้วยดุลพินิจของเรา ดังนั้นความผิดพลาดบางส่วนในตารางอาจมาจาก label ไม่ใช่จาก model

**ยังไม่มี `model_version` จริง** — ไฟล์ผลใช้ค่าชั่วคราว `unversioned-3216a57f2a0d` เพราะ scheme เป็นงานของ **T07** · ไม่ได้ตั้งค่าที่ดูเหมือนเป็นเวอร์ชันจริงเพื่อไม่ให้เข้าใจผิด

**ส่งต่อให้ T08:** ไฟล์ `P02-T05-evaluation-result.json` ออกแบบให้เทียบสองรอบได้ตรง ๆ · การรันครั้งนี้ใช้ 648 วินาที ดังนั้นรอบเทียบของ T08 จะใช้เวลาใกล้เคียง · **ยังไม่มีค่า tolerance** — T08 เป็นผู้กำหนดจากผลที่วัดได้จริง

**รันซ้ำแล้วได้เลขเดียวกันทุกหลัก** — รันสองรอบบนเครื่องเดียวกัน (รอบแรก 10:27 UTC จาก tree ที่ยังไม่สะอาด · รอบสอง 10:51 UTC จาก commit `40dcb77`) · **ทุก metric ตรงกันถึงความละเอียดเต็มของ float** และ confusion matrix ตรงกันทุกช่อง · ต่างกันแค่เวลารัน 648.1 → 674.1 วินาที

นี่เป็น**ข้อมูลให้ T08 ไม่ใช่การปิด T08** — ยังไม่ได้ทดสอบจาก fresh state (ลบ `.venv` และ cache แล้วติดตั้งใหม่) และยังไม่ได้ทดสอบข้ามเครื่อง · การกำหนด tolerance ยังเป็นงานของ T08 ที่ต้องตรวจสองเงื่อนไขนั้นก่อน

**ประสิทธิภาพ:** 648 วินาทีสำหรับ 14,640 แถว = ราว 44 ms ต่อข้อความ แบบทำนายทีละข้อความ · **ตัดสินใจไม่เพิ่ม batch** เพราะ evaluation รันตอน release ไม่ใช่ต่อ request และ API ตาม [P01-T02 §1](../docs/plans/P01-T02-api-contract.md#1-สถานะและขอบเขต) รับครั้งละหนึ่งข้อความอยู่แล้ว · ตัวเลขนี้**ไม่ใช่ latency ของ API** การวัดเป้า p95 เป็นงาน P03–P04
