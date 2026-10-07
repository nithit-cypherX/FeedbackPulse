# P02-T01 — Model provenance

- Task: [P02-T01 ใน phase plan](../docs/plans/P02-model-pipeline.md) · ขอบเขต: [Proposal §2](../PROPOSAL.md#2-model-and-dataset)
- รันเมื่อ: 2026-10-07 · เครื่อง: macOS 15.5 arm64 · Python 3.13.11 · `torch 2.14.1` · `transformers 5.19.0` · `huggingface_hub 1.33.0`

รายงานนี้เป็น **หลักฐานของสิ่งที่รันจริง** ไม่ใช่ข้อตกลง ข้อตกลงอยู่ใน `docs/plans/`

---

## 1. ตรวจอะไร

ยืนยัน 4 เรื่องตาม "Done when" ของ P02-T01 ก่อนนำ model รุ่นนี้ไปใช้ต่อ:

1. revision ที่ใช้ถูก pin ด้วย **commit SHA** ไม่ใช่ tag ที่ขยับได้
2. licence ตรงกับที่ Proposal §2 อ้าง
3. **label mapping อ่านจาก `config.json` ที่ดึงมาจริง** ไม่ใช่เดาจากชื่อ
4. `score` ที่จะคืนตรงกับนิยามใน [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) — "คะแนนของกลุ่มที่เลือก อยู่ระหว่าง 0–1"

## 2. ใช้รุ่นและเงื่อนไขไหน

| รายการ | ค่า |
|---|---|
| Repo | `cardiffnlp/twitter-roberta-base-sentiment-latest` (ลิงก์จาก Proposal §2) |
| **Revision ที่ pin** | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` |
| Commit นี้แก้ล่าสุด | 2025-08-04 07:58:29 UTC |
| Licence (จาก card metadata บน Hub) | `cc-by-4.0` |
| Architecture | `RobertaForSequenceClassification`, 12 layers, hidden 768, vocab 50265 |

**วิธีรันซ้ำ** — ดึงเฉพาะไฟล์ที่ PyTorch inference ใช้:

```python
from huggingface_hub import snapshot_download
snapshot_download(
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
    revision="3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7",
    allow_patterns=["config.json","pytorch_model.bin","vocab.json",
                    "merges.txt","special_tokens_map.json","README.md"],
)
```

**ข้าม `tf_model.h5` และ `.gitattributes`** เพราะเป็น TensorFlow weights และ metadata ของ Git ที่ไม่ใช้ ประหยัดการดาวน์โหลดไปราว 500 MB · ผลข้างเคียงที่ต้องรู้: `snapshot_download(..., local_files_only=True)` จะ error ว่า snapshot ไม่ครบถ้าไม่ส่ง `allow_patterns` ชุดเดิม

ไฟล์อยู่ใน HF cache ของเครื่อง (`~/.cache/huggingface/hub/`) **ไม่ได้อยู่ใน repo** จึงไม่ต้องเพิ่ม `.gitignore` ในรอบนี้ · การจัดชุดไฟล์ลง `artifacts/` เป็นงานของ T06

### Hash ของไฟล์ที่ใช้ (sha256)

| ไฟล์ | bytes | sha256 |
|---|---:|---|
| `config.json` | 929 | `d2fba19997da698157196ba16f5fcb30a97a7551cef6845a0f3d743ee19c6129` |
| `pytorch_model.bin` | 501,045,531 | `4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae` |
| `vocab.json` | 898,822 | `06b4d46c8e752d410213d9548eb27a54db70fda0319b6271fb8d59dead5e1cab` |
| `merges.txt` | 456,318 | `1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5` |
| `special_tokens_map.json` | 239 | `378eb3bf733eb16e65792d7e3fda5b8a4631387ca04d2015199c4d4f22ae554d` |
| `README.md` (model card ต้นทาง) | 4,328 | `05ad85143ed60f0abe631ab935485db046c24710d9bec50829b017cfc1e12bf7` |

## 3. คาดหวังอะไร

- `id2label` ต้องแยกได้เป็น 3 กลุ่มที่ตรงกับ `negative`, `neutral`, `positive` ใน P01-T02 §3
- `score` ต้องอยู่ระหว่าง 0–1 และเป็นคะแนนของกลุ่มที่ถูกเลือก
- licence ต้องเป็น CC BY 4.0 ตาม Proposal §2

## 4. ได้ผลอะไร

**Label mapping — อ่านจาก `config.json` ของ revision นี้โดยตรง:**

| index | label ใน `config.json` | ตรงกับกลุ่มใน P01-T02 §3 |
|---|---|---|
| 0 | `negative` | `negative` |
| 1 | `neutral` | `neutral` |
| 2 | `positive` | `positive` |

`config.json` ใช้ชื่อกลุ่มตรงตัวอยู่แล้ว **ไม่ใช่ `LABEL_0/1/2`** จึงไม่ต้องสร้างตาราง map เพิ่ม — แต่ P02 ยังต้องอ่านค่าจาก config ตอน runtime ไม่ hardcode ลำดับ เพราะถ้าเปลี่ยน revision ลำดับอาจเปลี่ยน

**นิยามของ `score` ที่ยืนยันแล้ว:** `softmax(logits)` แล้วเอาค่าของ class ที่ `argmax` · ผลรวมของทุก class = `1.000000` ทุกตัวอย่าง จึงอยู่ในช่วง 0–1 ตามที่ P01-T02 §3 กำหนด

**ผลทำนายที่รันจริง** (ใช้ยืนยันกลไก ไม่ใช่ผล evaluation — ผล evaluation เป็นงาน T05):

| ข้อความ | sentiment | score | probs [neg, neu, pos] |
|---|---|---|---|
| "My flight was delayed and nobody helped me." | `negative` | 0.9436 | 0.9436 / 0.0521 / 0.0044 |
| "The staff were helpful." | `positive` | 0.9414 | 0.0139 / 0.0447 / 0.9414 |
| "The flight landed at 6pm." | `neutral` | 0.9256 | 0.0082 / 0.9256 / 0.0662 |

**ตรวจว่าดึงซ้ำได้ของเดิม (Check ข้อแรกของ T01):** ดาวน์โหลดใหม่จาก SHA เดียวกันลง cache directory แยกคนละที่กับ cache หลัก แล้วเทียบ sha256 ทั้ง 6 ไฟล์ → **ตรงกันทุกไฟล์ทุก byte** จึงยืนยันได้ว่า pin ด้วย commit SHA ให้ของชุดเดิมจริง ไม่ใช่เชื่อเพราะ cache เดิมยังอยู่ · cache ชั่วคราวลบทิ้งแล้วหลังตรวจ

**Licence:** card metadata บน Hub ระบุ `cc-by-4.0` **ตรงกับที่ Proposal §2 อ้าง** · การให้เครดิตตาม CC BY 4.0 จะใส่ใน README และ model card ของโครงการ

## 5. มีข้อจำกัดอะไร และส่งต่ออะไร

**สำคัญต่อ T03 — ห้ามอ่านเพดานความยาวข้อความจาก tokenizer:**

repo นี้ **ไม่มี `tokenizer_config.json`** ทำให้ `tokenizer.model_max_length` คืนค่า sentinel `1000000000000000019884624838656` ซึ่งไม่ใช่เพดานจริง · ค่าที่เป็นหลักฐานคือ `max_position_embeddings = 514` ใน `config.json` (RoBERTa ใช้ 512 + 2 ตำแหน่งสำรอง) · **T03 ต้องยืนยันเพดานจาก `config.json` และการทดลองกับ tokenizer จริง ไม่ใช่จาก `model_max_length`** แล้วบันทึกวิธีนับกับการรวม special tokens ลง P01-T02 §7

**ข้อสังเกตตอนโหลด (ไม่ใช่ปัญหา):** transformers รายงาน `roberta.pooler.dense.weight` และ `.bias` เป็น `UNEXPECTED` เพราะ sequence-classification head ไม่ใช้ pooler · น้ำหนักส่วนที่ใช้ทำนายโหลดครบ ผลทำนายจึงใช้ได้ บันทึกไว้เพื่อให้คนที่เห็น log ไม่เข้าใจผิดว่าโหลดไม่สมบูรณ์

**ข้อจำกัดอื่น:**

- ตัวเลขในส่วนที่ 4 เป็นการ **ยืนยันกลไก** ด้วย 3 ประโยคที่เราแต่งเอง **ไม่ใช่ผล evaluation** และไม่บอกคุณภาพ model — ผลจริงบน versioned test set เป็นงาน T05
- ยังไม่ได้วัด RAM และเวลาโหลด model (งาน T09) จึงยังไม่มีข้อมูลสำหรับกำหนดขนาด container
- `pytorch_model.bin` เป็นรูปแบบ pickle ไม่มี `model.safetensors` ใน repo นี้ · ยังไม่ได้ประเมินว่าจะแปลงเป็น safetensors ตอน package หรือไม่ — เป็นเรื่องที่ T06 ต้องตัดสิน
- ผลนี้ผูกกับ revision `3216a57f…` เท่านั้น ถ้าเปลี่ยน revision ต้องรัน T01 ใหม่ทั้งหมด
