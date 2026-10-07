# P02-T04 — Shared inference interface

- Task: [P02-T04 ใน phase plan](../docs/plans/P02-model-pipeline.md) · ข้อตกลง API: [P01-T02](../docs/plans/P01-T02-api-contract.md) · โครงสร้าง: [P01-T03 §4](../docs/plans/P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด)
- รันเมื่อ: 2026-10-07 · model revision `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`
- **สถานะ: interface ล็อกแล้ว** โดยคนที่ 1 เมื่อ 2026-10-07

รายงานนี้คือ **interface ที่ล็อกแล้วให้คนที่ 2 (P03–P04) รับไปใช้** ไม่ใช่ข้อเสนอให้รีวิว · เดิมแผนกำหนดให้ตกลงกับคนที่ 2 ก่อน แต่ผู้ใช้สั่งเมื่อ 2026-10-07 ว่าให้คนที่ 1 ตัดสินเองแล้วคนที่ 2 ทำต่อตามนี้ · ถ้าคนที่ 2 เจอเหตุผลทางเทคนิคที่ทำให้ใช้ไม่ได้ ให้แจ้งกลับมาแก้ที่โมดูลนี้ ไม่ใช่สร้างทางของตัวเอง

---

## 1. ของที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|---|---|
| `src/feedbackpulse/inference.py` | **core** — preprocess → predict → แปลงเป็น sentiment + score · ไม่อ่าน env ไม่ต่อ network ไม่เรียก cloud |
| `src/feedbackpulse/model_files.py` | **configuration/prepare** — เก็บ repo, revision และรายการไฟล์ที่ pin ไว้ พร้อมฟังก์ชันดาวน์โหลด |
| `tests/test_inference.py` | 11 tests ครอบข้อความปกติ ขอบเขต ข้อความว่าง และกรณีโหลด model ไม่สำเร็จ |

แยกสองไฟล์เพราะ [P01-T03 §4](../docs/plans/P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด) กำหนดให้แยก core ออกจาก configuration · `inference.py` รับ path กับ version string เข้ามา **ไม่ไปหาเอง** ทำให้ P03 กำหนดได้ว่าจะเอา model จากไหนโดยไม่ต้องแก้ core

## 2. Interface ที่ขอให้ยืนยัน

```python
from feedbackpulse.inference import (
    SentimentClassifier, Prediction,
    ModelNotReady, InvalidText, TextTooLong,
)
from feedbackpulse.model_files import ensure_model_files

# ตอน process เริ่ม — ครั้งเดียว
clf = SentimentClassifier.load(ensure_model_files(), model_version="<ค่าจาก T07>")

# ต่อ request
result = clf.predict("My flight was delayed.")
# -> Prediction(sentiment='negative', score=0.9436, model_version='<ค่าจาก T07>')
```

### ชนิดข้อมูล

| ชื่อ | รูปแบบ |
|---|---|
| `SentimentClassifier.load(model_dir, model_version) -> SentimentClassifier` | โหลด model จาก directory ในเครื่อง · **เรียกครั้งเดียวตอน process เริ่ม** |
| `SentimentClassifier.predict(text: str) -> Prediction` | ทำนายข้อความเดียว |
| `Prediction` | `frozen dataclass` มี `sentiment: str`, `score: float`, `model_version: str` — ตรงกับ 3 fields ใน [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) |
| `clf.max_content_tokens -> int` | เพดานเนื้อหาเป็น token (ค่าปัจจุบัน **510**) ใช้เขียนข้อความ error ได้ |
| `clf.count_tokens(text) -> int` | นับ token ของเนื้อหา ไม่รวม special tokens |
| `clf.labels -> tuple[str, ...]` | `('negative', 'neutral', 'positive')` อ่านจาก `config.json` ของ model |
| `clf.model_version -> str` | ค่าที่ส่งเข้ามาตอน `load` |

### ข้อผิดพลาดและ HTTP status ที่ควร map

| Exception | เมื่อไร | P03 ควรตอบ |
|---|---|---|
| `ModelNotReady` (`RuntimeError`) | `load()` ล้มเหลว | `/ready` → `503` · `/predict` → `503` **ไม่คืน sentiment ปลอม** |
| `TextTooLong` (`InvalidText` → `ValueError`) | เนื้อหาเกิน `max_content_tokens` | `422` — มี `.token_count` และ `.limit` ให้ใส่ในข้อความ |
| `InvalidText` (`ValueError`) | ข้อความว่างหรือมีแต่ช่องว่าง หรือไม่ใช่ string | `422` |

`TextTooLong` สืบทอดจาก `InvalidText` จึงจับ `InvalidText` ตัวเดียวแล้วตอบ `422` ได้ทั้งสองกรณี

## 3. พฤติกรรมของโค้ดนี้ และหลักฐานที่รองรับแต่ละข้อ

**แยกตามความแข็งของหลักฐาน** — ข้อที่มี test กันการถดถอยได้ กับข้อที่ยืนยันด้วยการตรวจครั้งเดียวซึ่งไม่กันการถดถอย

### มี test รองรับ

| พฤติกรรม | test |
|---|---|
| **เพดานตรวจก่อนเรียก model** — 511 tokens ถูกปฏิเสธด้วย `TextTooLong` ไม่ถึง forward pass ที่จะโยน `RuntimeError` และกลายเป็น `500` | `test_text_one_token_over_the_limit_is_rejected_not_truncated` |
| **ไม่ตัดข้อความ** ตามที่ [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) ห้าม | test เดียวกัน (ได้ exception ไม่ได้ผลทำนายจากข้อความที่ถูกตัด) |
| **ชื่อกลุ่มอ่านจาก config** ไม่ hardcode ลำดับ index | `test_labels_come_from_the_model_config` |
| **เพดานตรงกับที่ T03 บันทึก** | `test_token_limit_matches_the_recorded_value` |
| **tokenizer ไม่รายงานค่า sentinel** | `test_tokenizer_reports_a_usable_limit_rather_than_the_sentinel` |
| **`model_version` คืนค่าที่ส่งเข้ามา** ไม่ได้ตั้งเอง | `test_prediction_matches_the_api_contract` |
| **โหลดไม่สำเร็จได้ error ที่แยกแยะได้** | `test_load_failure_is_distinguishable` |

### ยืนยันด้วยการตรวจครั้งเดียว — **ไม่มี test กันการถดถอย**

| พฤติกรรม | หลักฐาน | ช่องว่าง |
|---|---|---|
| **โหลดครั้งเดียว** weights อยู่ใน instance ไม่โหลดใหม่ต่อ `predict()` ตาม [P01-T03 §3](../docs/plans/P01-T03-system-structure.md#3-ส่วนให้บริการ--รับ-feedback-แล้วทำนาย) | จริงโดยโครงสร้าง — `__init__` รับ model ที่โหลดแล้ว และ `predict()` ไม่เรียก `from_pretrained` | ไม่มี test ที่ assert ว่า `predict()` ไม่โหลดซ้ำ ถ้ามีใครย้ายการโหลดเข้าไปใน `predict()` จะไม่มีอะไรจับได้ |
| **core ไม่อ่าน env ไม่ต่อ network** | `grep` แล้วไม่มี `os.environ`, `getenv`, `requests`, `azure`, `boto` ใน `inference.py` | เป็นการตรวจ ณ เวลานั้น **ไม่กันคนเพิ่มภายหลัง** · ถ้าต้องการให้บังคับจริงต้องมี test หรือ lint rule ที่สแกน `src/` ซึ่งยังไม่มี |

## 4. ผลตรวจ

```
ruff check src/ tests/      -> All checks passed!
ruff format --check         -> 4 files already formatted
pytest -q                   -> 11 passed
```

Tests ที่รันผ่าน:

| กรณี | ผล |
|---|---|
| โหลดจาก path ที่ไม่มี model | ได้ `ModelNotReady` |
| label อ่านจาก config | `('negative','neutral','positive')` |
| เพดานตรงกับที่บันทึกใน T03 | `max_content_tokens == 510` |
| ข้อความปกติ 3 แบบ | `sentiment` อยู่ใน 3 กลุ่ม · `0.0 <= score <= 1.0` · `model_version` ตรงกับที่ส่งเข้า |
| ข้อความว่าง / ช่องว่าง / `\n\t` | ได้ `InvalidText` |
| ข้อความที่ 510 tokens | ทำนายได้ |
| ข้อความที่ 511 tokens | ได้ `TextTooLong` พร้อม `token_count=511, limit=510` **ไม่ถูกตัดแล้วทำนายต่อ** |

**มี preprocessing และ predict ชุดเดียวจริง** — grep หา `AutoTokenizer`, `from_pretrained`, `softmax`, `argmax` ใน `src/` พบเฉพาะใน `inference.py`

## 5. ยังไม่ครบ และของที่ล็อกให้คนที่ 2

**ยังยืนยันไม่ได้ว่า "evaluation path กับ API path เรียกฟังก์ชันเดียวกัน"** เพราะยังไม่มีทั้ง evaluation script (T05) และ API (P03) · ตอนนี้ยืนยันได้แค่ว่า **มีจุดเรียกเดียวให้ใช้** · **นี่คือเหตุผลเดียวที่ T04 ยังปิดไม่ได้** ปิดได้ทันทีที่ T05 ยืนยันฝั่ง evaluation แล้วตรวจฝั่ง API ซ้ำใน P03

**`make portability-audit` ไม่ใช่จุดตรวจของ P02** — [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) กำหนดให้ตรวจการแยก **core, configuration และ cloud adapter** โดยมีเงื่อนไขว่า "เมื่อพัฒนาส่วนที่เกี่ยวข้องแล้ว" · **P02 ไม่มี cloud adapter** (ไม่มี `cloudlayer/` และไม่มีโค้ดติดต่อ cloud ใน `src/`) จึงเป็นจุดตรวจของ **P03–P04** ตอนเขียนส่วนที่ติดต่อ Azure · ส่วนที่ P02 รับผิดชอบคือการแยก core ออกจาก configuration ซึ่งตรวจแล้วในตารางข้างบน

### Decision ที่ล็อกแล้ว — คนที่ 2 ใช้ตามนี้

| เรื่อง | การตัดสิน | เหตุผล |
|---|---|---|
| **วิธี import** | **ตั้ง `PYTHONPATH=/app/src` ใน container ไม่ build wheel** | `pyproject.toml` ตั้ง `package = false` อยู่แล้วจึงไม่ต้องมี build backend · repo นี้มี service เดียว ไม่ได้แจกจ่ายเป็น library · Docker ตั้ง env ตัวเดียวจบ · ถ้าภายหลังต้องแจกเป็น library ให้แก้เฉพาะ `pyproject.toml` กับ `Dockerfile` ไม่ต้องแตะ core |
| **map exception → HTTP** | **ตามตารางในส่วนที่ 2** — `ModelNotReady` → `503`, `InvalidText`/`TextTooLong` → `422` | ตรงกับ [P01-T02 §4](../docs/plans/P01-T02-api-contract.md#4-validation-และ-error-handling) อยู่แล้ว ไม่ได้เพิ่มกติกาใหม่ |
| **batch / async** | **ไม่มีทั้งสอง** — `predict()` รับข้อความเดียว | [P01-T02 §1](../docs/plans/P01-T02-api-contract.md#1-สถานะและขอบเขต) กำหนดขอบเขตว่ารับครั้งละหนึ่งข้อความและไม่รวม batch processing จึงไม่มีผู้ใช้ batch · ถ้า T05 วัดแล้วช้าเกินรับได้ ให้เพิ่ม batch **ในโมดูลนี้** ไม่ใช่เขียน tokenize ซ้ำที่อื่น |

### สิ่งที่คนที่ 2 ต้องทำตามใน P03

- `SentimentClassifier.load(...)` **ครั้งเดียวตอน process เริ่ม** เก็บไว้ใช้ซ้ำ ไม่โหลดต่อ request
- จับ `ModelNotReady` ตอน startup → `/ready` ตอบ `503` และ `/predict` ตอบ `503` **ไม่คืน sentiment ปลอม**
- จับ `InvalidText` (ครอบ `TextTooLong` ด้วย) → `422`
- **ห้ามเรียก tokenizer หรือ model เอง** ให้เรียกผ่านโมดูลนี้เท่านั้น เพื่อไม่ให้มี preprocessing สองชุดตาม [P01-T03 §4](../docs/plans/P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด)
- `model_version` ที่ส่งเข้า `load()` ใช้ค่าที่ **T07** กำหนด ไม่ตั้งเอง

**หมายเหตุสำหรับ T05:** ถ้า evaluate 14,640 แถวด้วย `predict()` ทีละข้อความช้าเกินรับได้ ให้เพิ่ม batch **ในโมดูลนี้** ไม่ใช่เขียน loop ที่ tokenize เองใน script ของ T05 เพราะจะกลายเป็น preprocessing สองชุดที่ P01-T03 §4 ห้าม
