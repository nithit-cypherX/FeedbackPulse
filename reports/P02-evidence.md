# P02 — หลักฐานของ pipeline ที่ทำซ้ำได้

รายงานนี้คือ **ผลที่วัดและรันจริง** ของ P02 ทั้งเฟส · ข้อตกลงและสถานะ task อยู่ใน [phase plan](../docs/plans/P02-model-pipeline.md) ไม่เล่าซ้ำที่นี่

| | ค่าของรอบที่ลงทะเบียนไว้ |
|---|---|
| `model_version` | **`sentiment-6e7ff9fbc17c-850de906`** |
| `run_id` | `run-20261007T171530Z-e49706` |
| Code commit | `f1e7f0fa5f40603818e5ab524204dfaa3571d0dd` |
| ผล evaluation บน 14,640 แถว | **accuracy `0.8100409836065574` · macro-F1 `0.7605863552090412`** |
| Registry entry | [`registry/sentiment-6e7ff9fbc17c-850de906.json`](registry/sentiment-6e7ff9fbc17c-850de906.json) |

**เครื่องที่วัดทุกค่าในรายงานนี้:** macOS 15.5 arm64 · Python 3.13.11 · `torch 2.14.1` · `transformers 5.19.0` · `numpy 2.5.3` · `tokenizers 0.23.2` · `safetensors 0.8.0` · **ไม่ใช่ในคอนเทนเนอร์และไม่ใช่บน Azure** — ดูส่วนที่ 8

---

## 1. วิธีรันซ้ำ

### ขั้นตอนทั้งสี่

```bash
uv sync --frozen                                              # prepare: environment
PYTHONPATH=src uv run python -m feedbackpulse.evaluate         # prepare: model + data, แล้ว evaluate
PYTHONPATH=src uv run python -m feedbackpulse.package_artifact # package
PYTHONPATH=src uv run python -m feedbackpulse.registry         # register
```

`evaluate` ดึง model และ dataset ให้เองถ้ายังไม่มีในเครื่อง จึงไม่มีขั้น prepare แยกเป็นคำสั่งที่ห้า

**ต้องใช้ `PYTHONPATH=src`** — `pythonpath` ใน `pyproject.toml` มีผลกับ pytest เท่านั้น ไม่มีผลกับ `python -m` · ตรงกับที่ container ใช้ `PYTHONPATH=/app/src`

### รอบล่าสุดรันจาก fresh state จริง

ลบ `.venv` (778 MB), HF cache (479 MB) และ `artifacts/` (477 MiB) ทิ้งก่อน แล้วรันทั้งสี่ขั้นใหม่ · `artifact_id` ที่ได้หลัง build ใหม่ทั้งชุดคือ **`sentiment-6e7ff9fbc17c` ค่าเดิม** และ metric ตรงกับรอบก่อนทุกหลัก

### สิทธิ์ที่ต้องมี

Kaggle API token · `kagglehub 1.0.2` อ่านจาก env `KAGGLE_USERNAME` + `KAGGLE_KEY`, env `KAGGLE_API_TOKEN`, ไฟล์ `~/.kaggle/kaggle.json` หรือ `KAGGLE_CONFIG_DIR` · สร้าง token ที่ <https://www.kaggle.com/settings/api>

**บันทึกเฉพาะวิธีได้มา ไม่เก็บค่า token** ที่ใดใน repo ตามจุดตรวจ Secrets ใน [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) · ค้น pattern `KGAT_…`, `KAGGLE_KEY=`, `KAGGLE_API_TOKEN=` ใน **ทุก commit ของ Git history** และในไฟล์ที่จะ commit → **ไม่พบ** · `git check-ignore` ยืนยันว่า `data/Tweets.csv` ถูกกันด้วย `.gitignore:31`

### ตัวกันไม่ให้รันผิดชุดโดยไม่รู้ตัว

| กลไก | ทำอะไร |
|---|---|
| `dataset.verify()` | ตรวจ sha256 ของ `data/Tweets.csv` ก่อนเริ่มทุกรอบ · **โยน `DatasetMismatch`** ถ้าไม่ตรง |
| `snapshot_download(revision=…)` | ดึงเฉพาะ 6 ไฟล์ที่ pin ไว้จาก commit SHA ไม่ใช่ tag |
| `register()` ปฏิเสธ | 5 เงื่อนไขในส่วนที่ 5 |

**ข้าม `tf_model.h5` และ `.gitattributes`** เพราะเป็น TensorFlow weights และ metadata ของ Git ที่ไม่ใช้ ประหยัดการดาวน์โหลดไปราว 500 MB · ผลข้างเคียงที่ต้องรู้: `snapshot_download(..., local_files_only=True)` จะ error ว่า snapshot ไม่ครบถ้าไม่ส่ง `allow_patterns` ชุดเดิม

### สคริปต์วัด RAM และเวลาโหลด

ไม่ได้เก็บเป็น module ใน `src/` เพราะไม่ใช่โค้ดที่ระบบใช้ทำงาน · บันทึกไว้ให้ copy ไปรันซ้ำได้ รวมถึงในคอนเทนเนอร์ของ P03–P04

> **`ru_maxrss` เป็น bytes บน macOS แต่เป็น kilobytes บน Linux** · ถ้าใช้หน่วยผิดตัวเลขจะคลาดไป **1024 เท่า** ในค่าที่ใช้ตั้ง memory limit และจะมองไม่เห็นเพราะผลลัพธ์ยังดูเป็นตัวเลขปกติ · **อย่าตัดบรรทัดที่แปลงหน่วยออก**

บันทึกเป็น `measure_once.py` แล้วรัน **5 รอบ รอบละ process ใหม่** — การโหลดซ้ำใน process เดียวจะใช้ allocator ที่อุ่นแล้วและไฟล์ที่ map อยู่แล้ว ซึ่งรายงานเวลาโหลดถูกกว่าครั้งแรกที่ container เจอจริง

```python
import resource, statistics, sys, time
from pathlib import Path

def peak_rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw if sys.platform == "darwin" else raw * 1024   # ← บรรทัดที่ห้ามตัด

PROBE = "My flight was delayed and nobody helped me." if len(sys.argv) < 3 else "ok " * 509   # arg ที่ 2 = วัดที่เพดาน
t0 = time.perf_counter(); sys.path.insert(0, "src")
import torch, transformers                                   # ← ห้ามตัด ดูหมายเหตุใต้สคริปต์
from feedbackpulse.inference import SentimentClassifier
t1 = time.perf_counter(); rss_import = peak_rss_bytes()
clf = SentimentClassifier.load(Path(sys.argv[1]), model_version="measure")
t2 = time.perf_counter(); rss_load = peak_rss_bytes()
lat = []
for _ in range(50):
    t = time.perf_counter(); clf.predict(PROBE); lat.append(time.perf_counter() - t)
print(f"import {t1-t0:.3f}s  load {t2-t1:.3f}s  total {t2-t0:.3f}s  "
      f"rss_import {rss_import/2**20:.1f}  rss_load {rss_load/2**20:.1f}  "
      f"rss_predict {peak_rss_bytes()/2**20:.1f} MiB  predict_median {statistics.median(lat)*1000:.2f}ms")
```

**ต้อง `import torch` และ `import transformers` ไว้ตรงนั้น** — `inference.py` import สองตัวนี้ **ข้างใน `load()` และ `predict()`** ไม่ใช่ระดับ module · ถ้าสคริปต์ import แค่ `feedbackpulse.inference` เฟสแรกจะวัดได้ **0.004 วินาที** ซึ่งไม่ใช่เวลา import framework แล้วเวลานั้นจะไปโผล่รวมอยู่ในเฟส "อ่าน weights" แทน · วัดได้จากการรันสคริปต์ที่ไม่มีสองบรรทัดนี้ จึงเขียนกำกับไว้

```bash
for i in 1 2 3 4 5; do PYTHONPATH=src uv run python measure_once.py artifacts/sentiment-6e7ff9fbc17c/model; done
for i in 1 2 3 4 5; do PYTHONPATH=src uv run python measure_once.py artifacts/sentiment-6e7ff9fbc17c/model cap; done
# ในคอนเทนเนอร์ของ P03-P04 เปลี่ยนเป็น PYTHONPATH=/app/src python … /app/artifacts/…/model
```

---

## 2. ผล evaluation

**14,640 แถว · ข้ามไป 0 แถว** · ใช้ทุกแถวในไฟล์ ไม่ sample ไม่ split ไม่กรอง จึง**ไม่มี random seed เกี่ยวข้องกับการเลือกแถว**

| การตัดสิน | เหตุผล |
|---|---|
| ไม่ sample ใช้ทั้งไฟล์ | ไม่ต้องพึ่ง random seed ชุดทดสอบจึงนิ่งและเทียบสองรอบได้ตรง ๆ |
| ไม่ split train/test | ไม่ได้ train หรือ fine-tune ตาม [Proposal §2](../PROPOSAL.md#2-model-and-dataset) จึงไม่มีเหตุต้องกันข้อมูลไว้ |
| ไม่กรองด้วย `airline_sentiment_confidence` | การเลือกเกณฑ์กรองเป็นดุลพินิจของเรา ถ้ากรองจะทำให้ตัวเลขดูดีขึ้นโดยไม่มีฐาน |

### เทียบกับ baseline

ไม่มีเป้าตัวเลขที่เอกสารกำหนดล่วงหน้า — Proposal ไม่ได้ตั้งเกณฑ์คุณภาพ จึงใช้ **baseline ที่คำนวณจาก class balance** เป็นจุดเทียบ: ตอบ `negative` ทุกข้อ

| Metric | ค่าที่วัดได้ | baseline เดา `negative` ทุกข้อ |
|---|---:|---:|
| Accuracy | **0.8100** | 0.6271 |
| **Macro-F1** (metric หลัก) | **0.7606** | 0.2569 |
| Macro precision | 0.7453 | — |
| Macro recall | 0.7825 | — |

**ทำไม macro-F1 เป็นตัวหลัก:** evaluation set เป็น `negative` 62.7% การอ่าน accuracy อย่างเดียวจะทำให้ model ที่ละเลยสองกลุ่มเล็กดูดีเกินจริง — เดา `negative` ทั้งหมดก็ได้ accuracy 0.6271 แล้ว

### Per-class

| Label | Precision | Recall | F1 | support | สัดส่วนใน dataset |
|---|---:|---:|---:|---:|---:|
| `negative` | 0.9153 | 0.8599 | 0.8867 | 9,178 | 62.7% |
| `neutral` | 0.6163 | 0.6137 | **0.6150** | 3,099 | 21.2% |
| `positive` | 0.7043 | 0.8739 | 0.7800 | 2,363 | 16.1% |

### Confusion matrix

แถว = label จริง · คอลัมน์ = ที่ model ทำนาย

| | → negative | → neutral | → positive |
|---|---:|---:|---:|
| **negative** | **7,892** | 966 | 320 |
| **neutral** | 650 | **1,902** | 547 |
| **positive** | 80 | 218 | **2,065** |

`neutral` เป็นกลุ่มที่อ่อนที่สุด (F1 0.6150) และความผิดพลาดกระจายไปทั้งสองทาง — 650 แถวที่เป็น `neutral` ถูกทำนายเป็น `negative` และ 547 แถวเป็น `positive` · ส่วน `positive` มี recall สูง (0.8739) แต่ precision ต่ำกว่า (0.7043) เพราะรับ `neutral` เข้ามาผิด 218 แถว

### การยืนยันที่ไม่ใช่การรันตรรกะเดิมซ้ำ

[P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) และ `.agents/protocols/evidence-and-verification.md` กำหนดให้ต้องมีการคำนวณคนละทาง, reference result หรือ invariant ประกอบ · **ผ่าน 15/15**

| ประเภท | ตรวจอะไร | ผล |
|---|---|---|
| **ไบต์ต้นทาง** | ไฟล์ model ที่ดาวน์โหลดใหม่หลังลบ cache ตรงกับ sha256 ในส่วนที่ 3 | 5/5 ตรง |
| **Invariant จากข้อมูล** | `support` ของแต่ละ label เท่ากับจำนวนที่นับจาก CSV ด้วย stdlib `csv` **โดยไม่ผ่านโค้ด metric ของเรา** | 9,178 / 3,099 / 2,363 ตรง |
| **Invariant จากข้อมูล** | `total` เท่ากับจำนวนแถวใน CSV | 14,640 ตรง |
| **Invariant ภายใน** | ผลรวมทุกช่องของ confusion = `total` · ผลรวมแต่ละแถว = `support` · `trace/total` = accuracy · `correct` = trace | 4/4 ตรง |
| **Reference result** | คำนวณ macro-F1 และ per-class ใหม่จาก confusion matrix ด้วย `scikit-learn 1.9.1` | ตรงถึง 1e-12 ทุกค่า |

`scikit-learn` ใช้แบบ ephemeral (`uv run --with scikit-learn`) **ไม่เพิ่มเข้า lockfile** เพราะใช้ตรวจเท่านั้น ไม่ใช่ของที่ runtime ต้องมี

### Tolerance ของการรันซ้ำ — วัดจาก 6 รอบ

เทียบ **confusion matrix หรือ metric รวมไม่เพียงพอ** — ผลรายแถวอาจต่างกันแบบหักล้างกันเองจนตัวเลขรวมยังตรง · `evaluate.py` จึงคำนวณ fingerprint รายแถว

```
predictions_sha256 = sha256( "<index>\t<sentiment>\t<repr(score)>\n" ทุกแถวตามลำดับ )
```

ใช้ `repr()` ของ score เพื่อเทียบถึง **ระดับ bit ของ float** ไม่ใช่ทศนิยมที่ปัดแล้ว · `tests/test_evaluation.py` มี test ที่แสดงเคสที่ fingerprint มีไว้เพื่อจับ: ผลทำนายสองชุดที่ต่างกันทุกแถวแต่ได้ confusion matrix เดียวกัน

| รอบ | commit | เงื่อนไข |
|---|---|---|
| 1–3 | `40dcb77`, `35e881f`, `ad382f1` | tree สะอาด, `.venv` และ HF cache เดิม · **ยังไม่มี fingerprint** (เพิ่มเข้ามาภายหลัง) เทียบได้ที่ระดับ metric และ confusion matrix |
| 4 | `f282add` | เหมือนเดิม · เริ่มมี fingerprint |
| 5 | `f282add` | **ลบ `.venv` และ HF cache แล้วติดตั้งใหม่จาก `uv.lock` และดาวน์โหลด model ใหม่** |
| 6 | `f1e7f0f` | **ลบ `.venv`, HF cache และ `artifacts/` แล้วรันครบทั้งสี่ขั้นใหม่** — รอบที่ลงทะเบียนในรายงานนี้ |

| ค่า | ความต่างที่วัดได้ |
|---|---|
| ผลทำนายรายแถว (`predictions_sha256`) | **0** — `05ddac7af1112f6c…5ad3b4` ตรงกันทุก bit ในรอบ 4, 5, 6 |
| accuracy, macro-F1, macro precision/recall | **0** ทุกรอบ ถึงความละเอียดเต็มของ float |
| confusion matrix ทุกช่อง · per-class ทั้ง 12 ค่า | **0** ทุกรอบ |
| แถวที่ข้าม | 0 ทุกรอบ |
| **เวลารัน** | 648.1 / 674.1 / 678.9 / 650.8 / 674.2 / **351.4** วินาที → **ช่วง 93%** |

**เวลารันไม่นิ่ง** — รอบที่ 6 ใช้ 351.4 วินาที เทียบกับ 648–679 วินาทีในห้ารอบก่อน · ยังไม่ได้หาสาเหตุ (ภาระเครื่องและสถานะ thermal ต่างกันเป็นคำอธิบายที่เป็นไปได้ **แต่ยังไม่ได้วัดเพื่อยืนยัน**) · ตอกย้ำว่าเวลารันใช้เป็นเกณฑ์ตัดสินไม่ได้

### Tolerance ที่กำหนด — เฉพาะเงื่อนไขที่วัดแล้ว

| สิ่งที่เทียบ | เกณฑ์ | ฐาน |
|---|---|---|
| `predictions_sha256` | **ต้องตรงทุก bit** | วัดได้ 0 ความต่าง ข้าม fresh-state rebuild และข้ามการ build artifact ใหม่ |
| accuracy, macro-F1, macro precision/recall | **ต้องตรงทุก bit** | วัดได้ 0 ความต่างใน 6 รอบ |
| confusion matrix | **ต้องตรงทุกช่อง** | วัดได้ 0 ความต่างใน 6 รอบ |
| จำนวนแถวที่ข้าม | **ต้องเป็น 0** | วัดได้ 0 ทุกรอบ |
| เวลารัน | **ไม่ใช่เกณฑ์ตัดสิน** | ช่วง 93% |

**ความต่างใดก็ตามในสี่แถวแรกถือเป็นสัญญาณที่ต้องสอบ ไม่ใช่ noise** · เหตุผลที่ตั้งเข้มได้คือ inference เป็น deterministic และไม่มีการสุ่มที่ไหนเลย ดังนั้นถ้าเลขขยับ แปลว่ามีอะไรเปลี่ยนจริง — เวอร์ชัน dependency, ไฟล์ model หรือโค้ด

**ไม่กำหนด tolerance สำหรับ platform อื่นเพราะไม่มีหลักฐาน** — ทดสอบเพียงเครื่องเดียว · การเปลี่ยน CPU architecture, OS, build ของ `torch` หรือ BLAS backend เปลี่ยนลำดับการบวกทศนิยมได้ ซึ่งทำให้ logits ขยับในระดับ bit สุดท้ายและ `predictions_sha256` ต่างทันทีแม้ sentiment ทุกแถวยังเหมือนเดิม · **นี่เป็นการให้เหตุผล ไม่ใช่ผลวัด**

---

## 3. Version และ hash

### Model ต้นทาง

| รายการ | ค่า |
|---|---|
| Repo | `cardiffnlp/twitter-roberta-base-sentiment-latest` (ลิงก์จาก [Proposal §2](../PROPOSAL.md#2-model-and-dataset)) |
| **Revision ที่ pin** | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` — **commit SHA ไม่ใช่ tag ที่ขยับได้** |
| Commit นี้แก้ล่าสุด | 2025-08-04 07:58:29 UTC |
| Licence (จาก card metadata บน Hub) | `cc-by-4.0` **ตรงกับที่ Proposal §2 อ้าง** |
| Architecture | `RobertaForSequenceClassification`, 12 layers, hidden 768, vocab 50265 |

**pin ด้วย commit SHA ให้ของชุดเดิมจริง** — ดาวน์โหลดใหม่จาก SHA เดียวกันลง cache directory แยกคนละที่กับ cache หลัก แล้วเทียบ sha256 ทั้ง 6 ไฟล์ → **ตรงกันทุกไฟล์ทุก byte** ไม่ใช่เชื่อเพราะ cache เดิมยังอยู่ · cache ชั่วคราวลบทิ้งแล้วหลังตรวจ

### Evaluation dataset

| รายการ | ค่า |
|---|---|
| Dataset | `crowdflower/twitter-airline-sentiment` (ลิงก์จาก Proposal §2) |
| **Version ที่ pin** | **4** |
| Licence | CC BY-NC-SA 4.0 (**non-commercial + ShareAlike**) |
| ไฟล์ที่ใช้ | `data/Tweets.csv` · 3,421,431 bytes · 14,640 แถว · 15 columns |
| **sha256** | `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` |

**ทำไมใช้ `kagglehub` ไม่ใช่ `kaggle` CLI:** Proposal §2 ระบุ version 4 · `kagglehub` รับ handle `.../versions/4` และ parse ได้ `version=4, is_versioned=True` ส่วน `kaggle datasets download` ไม่มี flag เลือก version (ตรวจ argparse ของ CLI แล้ว) จึง pin ไม่ได้

Version 4 มี 2 ไฟล์คือ `Tweets.csv` และ `database.sqlite` (5,038,080 bytes) ซึ่งเป็นข้อมูลชุดเดียวกันในอีกรูปแบบ · **ใช้ `Tweets.csv` เป็นแหล่งเดียว** เพื่อไม่ให้มีสองแหล่งที่อาจไม่ตรงกัน

**ดึงซ้ำได้ของเดิม** — ดาวน์โหลด version 4 ใหม่ลง `KAGGLEHUB_CACHE` แยกคนละที่ แล้วเทียบ sha256 → **ตรงกันทุก byte** · cache ชั่วคราวลบแล้ว

**ความสมบูรณ์ของข้อมูล:** แถวที่ `text` ว่างหรือมีแต่ช่องว่าง **0** · แถวที่ไม่มี label **0** · label นอก 3 กลุ่ม **ไม่มี** · ความยาว `text` 12–186 อักขระ เฉลี่ย 103.8

### ชุด artifact

`artifact_id` = **`sentiment-6e7ff9fbc17c`** · **477 MiB** · content-addressed:

```
sentiment-<sha256(ของรายการ "ชื่อไฟล์:hash" ของไฟล์ใน model/ เรียงแล้ว) 12 ตัวแรก>
```

คิด hash จากไฟล์ใน `model/` เท่านั้น ทำให้ `manifest.json` บันทึก id ของตัวเองได้โดยไม่วนซ้ำ · **input ชุดเดิมให้ id เดิมเสมอ** — ยืนยันแล้วจากรอบที่ 6 ที่ลบ `artifacts/` ทิ้งแล้ว build ใหม่ทั้งชุดและได้ id เดิม

```text
artifacts/sentiment-6e7ff9fbc17c/
├── manifest.json             lineage, hash ของทุกไฟล์, metadata
├── upstream-model-card.md    model card ต้นทาง (เครดิตตาม CC BY 4.0) — loader ไม่อ่าน จึงไม่อยู่ใน model/
└── model/                    สิ่งที่ loader อ่าน และไม่มีอะไรเกินนั้น
```

| ไฟล์ | bytes | sha256 | ต้นทาง HF | ในชุด artifact |
|---|---:|---|:---:|:---:|
| `config.json` | 929 | `d2fba19997da698157196ba16f5fcb30a97a7551cef6845a0f3d743ee19c6129` | ✓ | ✓ `model/` |
| `vocab.json` | 898,822 | `06b4d46c8e752d410213d9548eb27a54db70fda0319b6271fb8d59dead5e1cab` | ✓ | ✓ `model/` |
| `merges.txt` | 456,318 | `1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5` | ✓ | ✓ `model/` |
| `special_tokens_map.json` | 239 | `378eb3bf733eb16e65792d7e3fda5b8a4631387ca04d2015199c4d4f22ae554d` | ✓ | ✓ `model/` |
| model card · `README.md` ↔ `upstream-model-card.md` | 4,328 | `05ad85143ed60f0abe631ab935485db046c24710d9bec50829b017cfc1e12bf7` | ✓ | ✓ ราก |
| `pytorch_model.bin` | 501,045,531 | `4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae` | ✓ | — แปลงแล้ว |
| `model.safetensors` | 498,615,868 | `deece7c9f6d59c96ac2a9ef285a6b0f20f9bea463b90242a0578bdfae8010718` | — | ✓ `model/` |
| `manifest.json` | — | `db8ceb69c7f6b291e1e5775c4c3c94ab94c9b09c8603aa4929d496993e1990d0` | — | ✓ ราก |

ห้าแถวแรกมี **hash เดียวกันทั้งสองฝั่ง** — ไฟล์ถูกคัดลอกทั้ง byte จึงตรวจย้อนจากชุด artifact ไปถึงต้นทางได้ตรง ๆ · `pytorch_model.bin` ไม่เข้าชุดเพราะแปลงเป็น safetensors แล้ว (ดูหัวข้อถัดไป)

`labels` และ `max_content_tokens` ใน `manifest.json` **อ่านจาก loader ที่โหลดชุดที่ build เสร็จแล้ว** ไม่ได้คำนวณซ้ำใน packaging script · ทำให้ manifest รายงานตัวเลขของ loader เองและ **การ build ล้มทันทีถ้าชุดที่ประกอบขึ้นโหลดไม่ได้** · **ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ผูกกับการตัดสินในส่วนที่ 7

### Environment

| รายการ | ค่า |
|---|---|
| `uv.lock` sha256 | `897a91df2d1fbc88d6a5fcb2fd4dc37c4affdd40be55b7ea293d88385797bb96` |
| Python | `3.13.11` |
| Package ที่กระทบ inference | `torch 2.14.1` · `transformers 5.19.0` · `numpy 2.5.3` · `tokenizers 0.23.2` |

### เพดานความยาวข้อความ — ค่าที่วัดได้

tokenizer เติม **2 tokens** ให้ทุกข้อความ: `<s>` ข้างหน้าและ `</s>` ข้างหลัง (`tok.num_special_tokens_to_add(pair=False) == 2`)

| total tokens (รวม special) | ผล forward |
|---:|---|
| 510, 511 | ผ่าน |
| **512** | **ผ่าน — ค่าสูงสุดที่ใช้ได้** |
| 513, 514 | พัง `RuntimeError: index 514 is out of bounds for dimension 1 with size 514` |

ยืนยันซ้ำด้วย **ข้อความจริงผ่าน tokenizer** ไม่ใช่สร้าง `input_ids` เอง: 1,527 อักขระ → 512 total / 510 content → ผ่าน · 1,530 อักขระ → 513 total / 511 content → พัง

สรุป: ความยาวลำดับรวมสูงสุด **512 tokens** · special tokens **2 ตัว** · **เนื้อหาสูงสุด 510 content tokens** นับด้วย tokenizer ของ revision ที่ pin **ไม่ใช่นับอักขระ**

**ทำไมอ่าน `tokenizer.model_max_length` ไม่ได้:** repo ของ model **ไม่มี `tokenizer_config.json`** ทำให้ค่านี้คืน sentinel `1000000000000000019884624838656` ซึ่งไม่ใช่เพดานจริง · ค่าที่เป็นหลักฐานคือ `max_position_embeddings = 514` ใน `config.json` (RoBERTa ใช้ 512 + 2 ตำแหน่งสำรอง) ประกอบกับการทดลองข้างบน

**แก้ช่องที่พังเงียบแล้ว:** `load()` ตั้ง `tokenizer.model_max_length` เป็นค่าที่ derive ได้ (512) · ก่อนแก้ ข้อความ 603 tokens เทียบกับ sentinel ให้ `False` คือ **ตรวจไม่เจอว่าเกินเพดาน** ทำให้ข้อความยาวเกินไปถึง model แล้วกลายเป็น `500` แทน `422`

ตัวเลขยังมาจาก `config.json` ที่เดียวเหมือนเดิม · **ไม่ได้เพิ่ม `tokenizer_config.json` เข้าชุด** เพราะจะมีแหล่งความจริงสองที่ · บันทึก `max_content_tokens: 510` ใน `manifest.json` แทน · มี test กำกับ · **ที่ยังกันไม่ได้:** ใครเปิด `artifacts/<id>/model` ด้วย `AutoTokenizer` เองโดยไม่ผ่านโมดูลของเรา ก็ยังเจอ sentinel

**tokenizer ไม่ตัดให้เอง ถ้าไม่สั่ง** — `tok(text)` คืน 513 ไม่ตัด · `tok(text, truncation=True, max_length=512)` คืน 512 ตัดจริง · `truncation=True` ทำสิ่งที่ [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) ห้ามไว้ → **โค้ดของเราไม่ใช้ `truncation=True`** นับแล้วปฏิเสธ

**นับอักขระแทน token ไม่ได้** — อัตราอักขระต่อ token ไม่คงที่:

| ข้อความ | อักขระ | tokens | อักขระ/token |
|---|---:|---:|---:|
| คำสั้นซ้ำ (`"ok "`) | 1,530 | 513 | 2.98 |
| ตัวอักษรเดียวติดกัน (`"a"*2000`) | 2,000 | 502 | 3.98 |
| ภาษาไทย | 1,300 | 2,502 | **0.52** |

ภาษาไทยให้ token **มากกว่า**จำนวนอักขระ ดังนั้นเพดานแบบนับอักขระที่ตั้งจากกรณีภาษาอังกฤษ (เช่น 1,527 อักขระ) จะ **ปล่อยข้อความที่เกิน 512 tokens ผ่านไปได้** · ขอบเขตโครงการรับเฉพาะภาษาอังกฤษ แต่ไม่มีอะไรห้ามผู้เรียกส่งภาษาอื่นมา

### Label mapping — อ่านจาก `config.json` ของ revision นี้โดยตรง

| index | label ใน `config.json` | `airline_sentiment` ใน dataset |
|---|---|---|
| 0 | `negative` | `negative` |
| 1 | `neutral` | `neutral` |
| 2 | `positive` | `positive` |

**ชื่อกลุ่มตรงตัวทั้งสามฝ่าย ไม่ต้องสร้างตารางแปลง** — แต่โค้ดอ่านชื่อกลุ่มจาก `config.json` ตอน runtime **ไม่ hardcode ลำดับ index** เพราะถ้าเปลี่ยน revision ลำดับอาจเปลี่ยน · มี test กำกับ (`test_labels_come_from_the_model_config`)

**นิยามของ `score`:** `softmax(logits)` แล้วเอาค่าของ class ที่ `argmax` · ผลรวมของทุก class = `1.000000` ทุกตัวอย่าง จึงอยู่ในช่วง 0–1 ตามที่ [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) กำหนด

**ข้อความอ้างอิง 3 ประโยคที่เราแต่งขึ้นเอง** ใช้ยืนยันกลไกและใช้เทียบข้ามขั้นตอน **ไม่ใช่ผล evaluation**:

| ข้อความ | sentiment | score | probs [neg, neu, pos] |
|---|---|---|---|
| "My flight was delayed and nobody helped me." | `negative` | 0.943575 | 0.9436 / 0.0521 / 0.0044 |
| "The staff were helpful." | `positive` | 0.941379 | 0.0139 / 0.0447 / 0.9414 |
| "The flight landed at 6pm." | `neutral` | 0.925601 | 0.0082 / 0.9256 / 0.0662 |

### การแปลง weights เป็น safetensors

repo ต้นทางมีแต่ `pytorch_model.bin` ไม่มี `model.safetensors` · **ตัดสินใจแปลง** ด้วยเหตุผลเดียวที่เหลืออยู่:

| เหตุผล | สถานะ |
|---|---|
| **ไม่ต้อง unpickle ตอนโหลด** | ใช้ได้ · `pytorch_model.bin` เป็น pickle ซึ่งรันโค้ดได้ตอน deserialize และ [Proposal §5](../PROPOSAL.md#5-planned-failure) ระบุว่า P05 จะ**ตั้งใจทำให้ artifact ใช้งานไม่ได้** การโหลดไฟล์ที่ถูกแก้ไขจึงไม่ควรเป็นการรันโค้ดจากไฟล์นั้น |
| **ไม่เพิ่ม dependency** | ใช้ได้ · `safetensors 0.8.0` เป็น dependency ต่อเนื่องของ `transformers` อยู่แล้ว |
| ~~โหลดเร็วกว่า~~ | **ถอนแล้ว** — วัดแล้วไม่ต่างกัน ทั้งเวลาและ RAM · ตัวเลขอยู่ใน ส่วนที่ 6 |

**ชุดนี้ไม่ใช่สำเนาของต้นทาง** — ต้นทางมี **204 tensor** ชุดที่เขียนลง safetensors มี **201 tensor** · ที่หายไป 3 ตัว:

- `roberta.embeddings.position_ids` — buffer ที่ `transformers` รุ่นนี้ไม่ได้เก็บแล้ว
- `roberta.pooler.dense.weight` และ `.bias` — pooler ที่ sequence-classification head ไม่เรียกใช้ (ตรงกับที่ `transformers` รายงานเป็น `UNEXPECTED` ตอนโหลดต้นทาง — เป็นข้อสังเกต ไม่ใช่ปัญหา น้ำหนักส่วนที่ใช้ทำนายโหลดครบ)

บันทึกทั้งสามตัวไว้ใน `manifest.json` และยืนยันว่าไม่กระทบผลด้วยการเทียบจริง:

| ตรวจ | ผล |
|---|---|
| `state_dict` จาก safetensors เทียบจาก `.bin` | key ตรงกันทั้ง 201 ตัว · **ทุก tensor เท่ากันทุก bit** |
| logits บนข้อความจริง 300 แถวจาก evaluation set | ความต่างสูงสุด **0.000e+00** |
| sentiment ที่ทำนายต่างกัน | **0 / 300** |

### โหลดได้โดยไม่พึ่งไฟล์นอกชุด

ตั้ง `HF_HOME` ชี้ไป directory ว่าง พร้อม `HF_HUB_OFFLINE=1` และ `TRANSFORMERS_OFFLINE=1` แล้วโหลดจาก `artifacts/sentiment-6e7ff9fbc17c/model`:

| ตรวจ | ผล |
|---|---|
| `HF_HOME` ว่างจริงตอนรัน | ยืนยันด้วยการไล่ไฟล์ใน directory → ไม่มีไฟล์ |
| `SentimentClassifier.load()` | สำเร็จ **ไม่แตะ cache และไม่ต่อ network** |
| `labels` | `('negative', 'neutral', 'positive')` |
| `max_content_tokens` | **510** |
| ทำนาย 3 ข้อความอ้างอิง | ตรงกับตารางข้างบนทุกค่า |

---

## 4. Run ID

| สิ่งที่บันทึก | ค่าของรอบที่ลงทะเบียน | ระบุอะไร |
|---|---|---|
| `run_id` | `run-20261007T171530Z-e49706` | **การรันครั้งนั้น** · รูปแบบ `run-<UTC timestamp>-<สุ่ม 3 bytes>` |
| `finished_utc` | `2026-10-07T17:21:22+00:00` | เวลาที่รันเสร็จ |
| `seconds` | `351.4` | เวลาที่ใช้ |
| `code.commit` | `f1e7f0fa5f40603818e5ab524204dfaa3571d0dd` · `dirty: false` · `uncommitted: []` | **code รุ่นที่รัน** |
| `predictions_sha256` | `05ddac7af1112f6c12267e820832a678b19155bd61fd55a67150e50b7e5ad3b4` | **ผลลัพธ์** ไม่ใช่การรัน |
| sha256 ของสำเนาผล | `ea43c8965cef796944bec293158e74d9bef656db8d47229d5b928e3173d8e508` | **ไฟล์ผลของรอบนี้** ที่เก็บข้าง registry entry |

**ทำไมต้องมี `run_id` แยกจาก `predictions_sha256`** — pipeline เป็น deterministic จึงได้ `predictions_sha256` ค่าเดียวกันทุกรอบที่ input เหมือนกัน (ยืนยันแล้วในส่วนที่ 2) · มันจึงระบุ **ผลลัพธ์** ไม่ใช่ **การรัน** และแทน run ID ไม่ได้ · ส่วนสุ่มท้าย `run_id` ทำให้สองรอบที่เริ่มในวินาทีเดียวกันยังแยกกันได้

`run_id` ถูกบันทึกทั้งในไฟล์ผล (`run.run_id`) และใน lineage ของ registry entry (`evaluation.run_id`) และ**ใช้เป็นชื่อสำเนาผล evaluation** ที่เก็บข้าง entry — ดูส่วนที่ 5

---

## 5. Lineage

### โครงสร้าง registry entry

`reports/registry/<model_version>.json` เก็บ 6 ส่วน:

| ส่วน | บันทึกอะไร |
|---|---|
| `artifact` | `artifact_id`, hash ของ `manifest.json`, hash ของทุกไฟล์ในชุด |
| `source_model` | repo, revision, licence, **hash ต้นทางของทุกไฟล์รวม `pytorch_model.bin`** |
| `evaluation_data` | handle version 4, sha256, จำนวนแถว |
| `code` | commit |
| `environment` | Python, **hash ของ `uv.lock`**, เวอร์ชัน package ที่กระทบ inference |
| `evaluation` | ชื่อสำเนาผล + hash, `run_id`, เวลารัน, accuracy, macro-F1 |

**ไม่บันทึกที่เก็บหรือ URL** เพื่อไม่ผูกกับการตัดสินในส่วนที่ 7

### `model_version` scheme

```
sentiment-6e7ff9fbc17c-850de906
│         │             │
│         │             lineage digest 8 ตัว — sha256 ของ lineage record ทั้งก้อน
│         │             (artifact, model ต้นทาง, dataset, code commit, environment, ผล evaluation)
│         artifact_id — content-addressed จากไฟล์ใน model/
model family — อ่านออกใน log และใน response body
```

| สิ่งที่ตัดสิน | เหตุผล |
|---|---|
| **3 ส่วน ไม่ใช่ hash ตัวเดียว** | `artifact_id` ตรงกลางทำให้เห็นทันทีว่าสอง release ใช้ weights ชุดเดียวกันหรือไม่ ซึ่งต้องอ่านเร็วตอน rollback (R2) · hash ตัวเดียวอ่านอะไรไม่ได้เลย |
| **content-addressed ไม่ใช่ตัวนับ** | ไม่ต้องมีทะเบียนกลางแจกเลขถัดไป ซึ่งสำคัญตอนที่ยังไม่เลือกบริการเก็บ artifact |
| **digest ครอบ code และ environment ไม่ใช่แค่ weights** | `predict()` ขึ้นกับโค้ดของเราด้วย · ถ้าเปลี่ยน preprocessing แล้ว version ไม่เปลี่ยน version นั้นจะโกหก |
| **ยาว 31 อักขระ** | ใส่ใน JSON response และ log ได้โดยไม่เทอะทะ |

**`model_version` เสถียรเมื่อ artifact และ input เหมือนเดิม แต่เปลี่ยนเมื่อรัน evaluation ใหม่** — `run_finished_utc` และ `result_sha256` อยู่ใน payload ที่ hash (และไฟล์ผลมี timestamp อยู่ข้างใน) ดังนั้นรัน `evaluate` ใหม่ก็ได้ digest ใหม่แม้ model, dataset, code และ lockfile ไม่เปลี่ยนเลย

**ยืนยันจากของจริง:** สองรอบติดกันให้ `…-c9386c0e` แล้ว `…-850de906` โดย `artifact_id` เป็น `sentiment-6e7ff9fbc17c` ค่าเดิมทั้งสองรอบ · เลือกคงไว้แบบนี้เมื่อ 2026-10-07 ไม่แก้ digest · เงื่อนไขที่ P03–P04 ต้องทำตามอยู่ใน [phase plan §3](../docs/plans/P02-model-pipeline.md)

### Registry ปฏิเสธมากกว่ายอมบันทึก

`register()` โยน `CannotRegister` แทนที่จะออก version ที่อ้างสิ่งที่พิสูจน์ไม่ได้:

| เงื่อนไขที่ปฏิเสธ | เหตุผล |
|---|---|
| มี input ที่ยัง uncommitted | version จะอ้าง commit ที่สร้างกลับมาไม่ได้ |
| evaluation รันบน code ที่ยัง uncommitted | ตัวเลขไม่ผูกกับ commit ใด |
| **ไฟล์ที่ตัดสินผลทำนายเปลี่ยนตั้งแต่ eval รัน** | ผล evaluation ไม่ได้อธิบาย code ที่กำลัง release |
| model revision ไม่ตรงกับที่ eval ใช้ | lineage ไม่สอดคล้องกันเอง |
| dataset ไม่ตรงกับที่ eval ใช้ | เหมือนกัน |

ไฟล์ที่นับว่า "ตัดสินผลทำนาย" อยู่ใน `gitinfo.BEHAVIOUR_PATHS`: `inference.py`, `model_files.py`, `dataset.py`, `evaluation.py`, `evaluate.py`, `pyproject.toml`, `uv.lock`

**guard ข้อที่สามทำงานจริง** — ตรวจพบว่า `inference.py` และ `evaluate.py` เปลี่ยนไปตั้งแต่ commit `40dcb77` ที่ evaluation รอบก่อนรัน จึงปฏิเสธการ register และบังคับให้รัน evaluation ใหม่ก่อน

### ผลไล่ย้อนจาก `model_version` ค่าเดียว — 36/36

เริ่มจากสตริง `sentiment-6e7ff9fbc17c-850de906` อย่างเดียว แล้วไล่ย้อนทุกชั้น โดย **คำนวณ hash จากไฟล์จริงบน disk ทุกตัว ไม่ใช่อ่านค่าที่บันทึกไว้มาเทียบกับตัวเอง**

| ชั้น | ตรวจอะไร | ผล |
|---|---|---|
| 1 | **คำนวณ digest ใหม่จาก lineage ที่เก็บ แล้วได้ชื่อ version เดิม** · entry บันทึก `model_version` ตรงกับชื่อไฟล์ | 2/2 |
| 2 | `manifest.json` + ไฟล์ในชุด 6 ไฟล์ hash ตรง · **คำนวณ `artifact_id` ใหม่จากไฟล์ใน `model/` ได้ค่าเดิม** | 8/8 |
| 3 | revision ตรงกับที่ pin ในโค้ด · ไฟล์ต้นทาง 6 ไฟล์ hash ตรง | 7/7 |
| 4 | handle ตรงกับที่ pin ในโค้ด · `data/Tweets.csv` hash ตรง | 2/2 |
| 5 | commit มีอยู่จริง · อยู่ในสายของ `HEAD` · ไฟล์ที่ตัดสินผลทำนายไม่เปลี่ยนตั้งแต่นั้น | 3/3 |
| 6 | `uv.lock` hash ตรง | 1/1 |
| 7 | สำเนาผล evaluation ของ entry นี้มีอยู่และ hash ตรง · `run_id` ในสำเนาตรงกับ lineage · accuracy/macro-F1 ตรง · `predictions_sha256` อยู่ในสำเนา · eval รันบน commit เดียวกับ lineage · revision และ dataset ที่ eval ใช้ตรงกับ lineage | 8/8 |
| 8 | โหลด artifact แล้วทำนายได้ (`negative` 0.943575) · คืน `model_version` ค่านี้ · `labels` และ `max_content_tokens` ตรงกับ manifest | 4/4 |

**แต่ละ entry เก็บสำเนาผล evaluation ของตัวเองไว้ข้าง ๆ** เป็น `<run_id>-evaluation.json` แทนการชี้ไป `reports/P02-T05-evaluation-result.json` ที่ถูกเขียนทับทุกรอบ

**ข้อบกพร่องสองรอบที่พบและแก้แล้ว** — บันทึกไว้เพราะทั้งสองทำให้ entry อ้างสิ่งที่พิสูจน์ไม่ได้ ซึ่งตรงข้ามกับที่ R1 และ R2 ต้องการ:

1. entry แรกบันทึกผลด้วย **path ที่ใช้ร่วมกัน** ซึ่งถูกเขียนทับทุกรอบ → version นั้น **trace ไม่ได้ทันทีที่รัน evaluation ซ้ำ** · แก้ด้วยการคัดลอกสำเนาไว้ข้าง entry พร้อม test ที่เขียนทับไฟล์กลางแล้วยืนยันว่า entry ยัง resolve ได้
2. การแก้ครั้งนั้นตั้งชื่อสำเนาจาก `model_version` จึงต้อง**เขียน `result_file` ลง lineage หลังคำนวณ digest แล้ว** → entry ที่เก็บไว้ **คำนวณ version ของตัวเองกลับมาไม่ได้** · ตรวจไม่พบตอนแรกเพราะการตรวจของเราเทียบกับ `None` ซึ่งจริงเสมอ · แก้ด้วยการตั้งชื่อสำเนาจาก `run_id` ที่มีอยู่ก่อนการ hash พร้อม **test ที่คำนวณ version ใหม่จาก lineage ที่เก็บ** (ชั้นที่ 1 ข้างบนจึงมี test กันการถดถอยใน CI)

entry ที่สร้างด้วยโค้ดที่มีข้อบกพร่องถูกลบทั้งหมดเพราะกู้คืนไม่ได้และไม่เคย deploy ที่ไหน · git history เก็บบันทึกไว้ว่ามีอยู่

### จุดที่ lineage ไม่สอดคล้องกันเอง และเหตุผลที่ยอมรับได้

`manifest.json` บันทึก `built_with.code_commit = 3b8e584` แต่ lineage บันทึก `code.commit = f1e7f0f` เพราะ artifact ถูก package ก่อนการแก้ `registry.py` รอบที่สอง · ตรวจแล้วว่า:

- ไฟล์ที่เปลี่ยนระหว่างสอง commit นั้นมีเฉพาะ `registry.py`, `tests/test_registry.py` และไฟล์ใน `reports/`
- `gitinfo.behaviour_changed_between('3b8e584')` → **ไม่เปลี่ยน** — ไฟล์ที่ตัดสินผลทำนายไม่ต่างกัน
- hash ของไฟล์ในชุด artifact ตรงกับที่ lineage บันทึกทุกตัว (ชั้นที่ 2)

**แต่ `package_artifact.py` และ `registry.py` ไม่อยู่ใน `BEHAVIOUR_PATHS`** จึงไม่มี guard ที่จะจับได้ถ้า packaging logic เปลี่ยนไปหลัง build · รอบนี้ยืนยันด้วยการตรวจ hash ไม่ใช่ด้วย guard

---

## 6. เวลาเริ่มระบบและหน่วยความจำ

วัดด้วยสคริปต์ในส่วนที่ 1 · **รอบละ process ใหม่** เพราะการโหลดซ้ำใน process เดียวจะใช้ allocator ที่อุ่นแล้วและไฟล์ที่ map อยู่แล้ว · รายงานเป็น **peak RSS** เพราะ container limit ตั้งจากค่าสูงสุด · ไม่ใช่หลักฐาน R1 แต่เป็นผลวัดที่ [P01-T03 §5](../docs/plans/P01-T03-system-structure.md#5-เหตุผลและข้อแลกเปลี่ยน) สั่งให้วัดใน P02–P03

> **วัดสองรอบคนละวัน ได้เวลาต่างกันราวสองเท่า แต่หน่วยความจำตรงกัน** · รายงานทั้งสองรอบไว้ตรง ๆ · **ค่าเวลาใช้เป็นเกณฑ์ตัดสินไม่ได้** ดูท้ายส่วนนี้

### เวลาเริ่มระบบ

| ช่วง | 2026-10-08 · 8 samples (min / median / max) | 2026-10-07 · 5 samples (min / median / max) |
|---|---|---|
| import `torch` + `transformers` | 0.740 / **0.770** / 0.786 s | 1.610 / **1.629** / 1.637 s |
| อ่าน weights จาก artifact | 0.617 / **0.640** / 0.651 s | 1.292 / **1.309** / 1.320 s |
| **รวมเวลาเริ่มระบบ** | 1.357 / **1.409** / 1.437 s | 2.925 / **2.934** / 2.946 s |

แยกสองช่วงเพราะโตไม่เหมือนกัน — เวลา import เท่าเดิมไม่ว่า weights จะใหญ่แค่ไหน ส่วนเวลาอ่าน weights โตตามขนาด artifact · ภายในรอบของตัวเองวัดซ้ำได้ในช่วงแคบ (รอบใหม่กว้าง 5.5–6.2% · รอบเก่า 0.7–2.2%)

### หน่วยความจำ — ค่าสูงสุดไม่ได้อยู่ที่การโหลด

| จุด | 2026-10-08 (ช่วง 8 samples เว้นที่ระบุ) | 2026-10-07 |
|---|---|---|
| Python เปล่า | — | ~11 MiB |
| หลัง import framework | 216.9–219.7 MiB | ~217 MiB |
| หลังโหลด weights | 332.1–341.3 MiB | ~341 MiB |
| **หลังทำนาย 50 ครั้ง · ข้อความสั้น (5 tokens)** | **688.4–698.9 MiB** | **712 MiB** |
| **หลังทำนาย 50 ครั้ง · ข้อความที่เพดาน (510 tokens)** | **735.1–783.4 MiB** (9 samples) | **748 MiB** |

**การทำนายครั้งแรกกินเพิ่มอีกราว 365 MiB** มากกว่าการอ่าน weights ทั้งก้อน — เป็นตอนที่ torch จอง workspace ของ forward pass · **ถ้า sizing จากตัวเลข "หลังโหลด" ~341 MiB container จะตายตอน request แรก**

**ค่าสูงสุดที่วัดได้คือ 783.4 MiB** (ข้อความที่เพดาน) · ต่างจากตัวเลขเวลา **หน่วยความจำวัดซ้ำได้ข้ามสองรอบ** จึงใช้ sizing ได้ — แต่ให้ยึด**ค่าสูงสุดที่วัดได้ ไม่ใช่ค่ากลาง** เพราะกระจาย 6.6% และ 783.4 MiB โผล่ในตัวอย่างสุดท้ายไม่ใช่ตัวแรก

**หน่วยความจำขึ้นแล้วคงที่ ไม่โตต่อ** — รอบ 2026-10-07 วัดที่ 1, 10, 25 และ 50 ครั้ง พบว่าที่ 25 กับ 50 ครั้งได้ค่าเดียวกันทั้งสองความยาว จึง**ไม่พบสัญญาณว่ารั่ว**ในช่วงที่วัด

### เวลาต่อการทำนาย

| | 2026-10-08 · median (ช่วง) | 2026-10-07 · median (ช่วง) |
|---|---|---|
| ข้อความสั้น (5 tokens) | **26.76 ms** (24.64–27.22) | **51 ms** (48.74–51.66) |
| ข้อความที่เพดาน (510 tokens) | **111.63 ms** (109.02–114.89) | **184 ms** |
| **อัตราส่วน เพดาน ÷ สั้น** | **4.2 เท่า** | **3.6 เท่า** |

**ข้อความที่เพดานช้ากว่าหลายเท่าในทั้งสองรอบ** — P03–P04 ต้องใช้ข้อมูลนี้ตอนทดสอบเป้า p95 เพราะทดสอบด้วยข้อความสั้นจะได้ตัวเลขดีเกินจริง · อัตราส่วนไม่เท่ากันสองรอบ (3.6 กับ 4.2) จึงใช้เป็นช่วง ไม่ใช่ค่าเดียว

### safetensors เทียบ `pytorch_model.bin`

วัดในรอบ 2026-10-07: `model.safetensors` ใช้ 1.292–1.316 s เทียบ `pytorch_model.bin` 1.294–1.328 s และ RAM เพิ่มเท่ากัน (+116 ถึง +121 MiB) · **ไม่ต่างกัน ช่วงที่วัดได้ทับกัน** — นี่คือผลที่หักล้างข้ออ้าง "โหลดเร็วกว่า" ในส่วนที่ 3 · ข้อสรุปยังใช้ได้แม้เวลาสัมบูรณ์ของรอบนั้นสูงกว่ารอบใหม่ เพราะเป็นการเทียบสองรูปแบบ**ภายในรอบเดียวกัน** · **ยังไม่ได้วัดซ้ำในรอบใหม่**

### ความต่างระหว่างสองรอบ — ยังหาสาเหตุไม่ได้

เวลาทุกค่าเร็วขึ้นใกล้ ๆ สองเท่าไปด้วยกัน (import 1.629 → 0.770 s · อ่าน weights 1.309 → 0.640 s · ทำนาย 51 → 26.76 ms · evaluation ทั้งชุด 648–679 → 351.4 s) ขณะที่ **peak RSS ทุกจุดตรงกัน**

**เบาะแสที่วัดได้ ไม่ใช่ข้อสรุป:** เกิดสองครั้งว่าการรันครั้งแรกหลังเว้นช่วงให้ `import` 1.624 s และ 1.555 s แล้วครั้งถัดไปทันทีกลับมาที่ ~0.78 s · ค่าที่เว้นช่วงใกล้ median ของรอบ 2026-10-07 (1.629 s) มาก ซึ่งเข้ากับเรื่องสถานะ page cache ของไลบรารี `torch` · **แต่อธิบาย 5 ตัวอย่างติดกันที่ ~1.63 s ของรอบนั้นไม่ได้** เพราะถ้าเป็น cache ล้วน ตัวอย่างที่สองควรเร็วขึ้นแล้ว · ไม่ได้บันทึก CPU load หรืออุณหภูมิไว้ตอนวัดรอบแรก จึงเทียบกลับไปไม่ได้

**ผลที่ตามมา:** ค่าเวลาในส่วนนี้ **ใช้เป็นเกณฑ์ผ่าน/ไม่ผ่านไม่ได้** และใช้ประมาณ cold start ของ container ไม่ได้ · **P03–P04 ต้องวัดเองในคอนเทนเนอร์** และถ้าจะเทียบสองค่า ให้วัดทั้งสองค่าในรอบเดียวกันเหมือนที่ทำกับ safetensors เทียบ `.bin`

### ประสิทธิภาพของ evaluation

351–679 วินาทีสำหรับ 14,640 แถว แบบทำนายทีละข้อความ · **ตัวเลขนี้ไม่ใช่ latency ของ API** — การวัดเป้า p95 เป็นงาน P03–P04

**ตัดสินใจไม่เพิ่ม batch** เพราะ evaluation รันตอน release ไม่ใช่ต่อ request และ [P01-T02 §1](../docs/plans/P01-T02-api-contract.md#1-สถานะและขอบเขต) กำหนดว่ารับครั้งละหนึ่งข้อความ · ถ้าภายหลังต้องเพิ่ม ให้เพิ่ม **ใน `inference.py`** ไม่ใช่เขียน tokenize ซ้ำที่อื่น — มี `ponytail:` marker กำกับที่ `predict()`

---

## 7. ที่เก็บ model artifact

**ตัดสิน: ใส่ชุด artifact เข้าไปใน container image ตอน build** ไม่ใช้ blob storage แยก · ผู้ตัดสิน: คนที่ 1 ตามอำนาจที่ได้รับเมื่อ 2026-10-07

### ตัดสินจากเกณฑ์ที่ยืนยันได้เท่านั้น

| เกณฑ์ | ยืนยันได้จาก | ประเภทหลักฐาน |
|---|---|---|
| ขนาด artifact 477 MiB | ส่วนที่ 3 | **ผลวัด** |
| เวลาเริ่มระบบ 1.42–2.93 s เมื่อไฟล์อยู่ในเครื่องแล้ว | ส่วนที่ 6 | **ผลวัด** (สองรอบต่างกันราวสองเท่า) |
| ทางเลือกนั้นมีขั้นดาวน์โหลดตอน start หรือไม่ | คุณสมบัติของการออกแบบ | **เชิงโครงสร้าง** |
| rollback ต้องย้อนกี่สิ่ง | คุณสมบัติของการออกแบบ | **เชิงโครงสร้าง** |
| งบรองรับทางเลือกไหน | [Proposal §6](../PROPOSAL.md#6-cost-estimate) ระบุสมมติฐานไว้แล้วว่า "one Basic container registry, 5 GB of blob storage" | **ข้ออ้างจากเอกสาร** |

**สิ่งที่ตั้งใจไม่ใช้เป็นเกณฑ์: เวลาดาวน์โหลด 477 MiB จากบริการจริง** เพราะวัดในเครื่องไม่ได้ และการเดาค่าจะขัดกับ [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) ที่สั่งว่า "ไม่เดาตัวเลขล่วงหน้า"

### เทียบสองทางเลือก

**A** = `COPY` artifact เข้า image ตอน build แล้ว push ไป container registry · **B** = เก็บใน Blob Storage แล้วดึง 477 MiB ทุกครั้งที่ container เริ่ม

| เกณฑ์ | A — ใส่ใน image (ที่เลือก) | B — ดาวน์โหลดตอน start |
|---|---|---|
| **bytes เดินทางเมื่อไร** | ไปกับ image ตอน pull | pull image **แล้วยัง**ต้องดึง artifact อีกต่อหนึ่ง |
| **ผลต่อ cold start** | artifact อยู่ใน image แล้ว เริ่มได้เลย · ขนาด image โตขึ้น 477 MiB | **ทุกครั้งที่เริ่ม**ต้องดึง 477 MiB เพิ่มจากการ pull image · [Proposal §3](../PROPOSAL.md#3-serving-pattern-and-requirements) ระบุว่า service **scale to zero เมื่อ idle** จึงเกิด cold start บ่อย |
| **rollback (R2)** | **ย้อนสิ่งเดียว** — image revision พา code + artifact ไปพร้อมกัน | **ย้อนสองสิ่ง** — image revision กับ pointer ที่ชี้ blob · ทั้งสองคลาดกันได้ |
| **งบ (Proposal §6)** | registry ที่สมมติไว้แล้วรองรับ · ไม่เพิ่ม egress นอกจากการ pull image | blob 5 GB ที่สมมติไว้แล้วรองรับ · **แต่เพิ่ม egress ทุก cold start** ซึ่งกินเข้า $3.55 ที่สำรองไว้สำหรับ "requests, network, operations" |
| **failure demo (R4)** | ต้องแก้ไฟล์ในคอนเทนเนอร์ที่รันอยู่ หรือ deploy image ที่พังตั้งใจ | **ง่ายกว่า** — ลบหรือเปลี่ยนชื่อ blob แล้ว readiness ต้อง fail |
| **เปลี่ยน model** | ต้อง build + deploy ใหม่ | เปลี่ยน config ชี้ blob ใหม่ |

### เหตุผลที่เลือก A

1. **รักษาการผูกที่ `model_version` อ้างไว้ให้เป็นจริง (เหตุผลหลัก)** — digest ครอบ code commit + environment + artifact พร้อมกัน เพราะ `predict()` ขึ้นกับโค้ดของเราไม่ใช่แค่ weights · ถ้า artifact อยู่ใน blob ที่สลับได้ตอน runtime **`model_version` จะอ้างการผูกที่ไม่มีอะไรบังคับ** — คนเปลี่ยน blob แล้ว API ยังคืน version เดิมได้
2. **rollback ย้อนสิ่งเดียว** — R2 ต้องพิสูจน์ว่า rollback กลับรุ่นก่อนหน้าได้จริง · ย้อนสองสิ่งที่คลาดกันได้คือความเสี่ยงที่ไม่ต้องรับ
3. **ไม่จ่ายค่าดึง artifact ซ้ำทุก cold start** — Proposal §3 เลือก scale to zero เอง ดังนั้น cold start ไม่ใช่กรณียกเว้น
4. **artifact เป็น immutable เข้ากับ `artifact_id` ที่ content-addressed** — ของที่อยู่ใน image แก้ไม่ได้จากภายนอก

### สิ่งที่แลกไป

- **image โตขึ้น 477 MiB** → การ pull image ตอน cold start หนักขึ้น · **P04 ต้องวัด**
- **เปลี่ยน model ต้อง build ใหม่** ไม่ใช่แก้ config — ช้ากว่าแต่ตรวจสอบได้มากกว่า
- **failure demo ของคนที่ 3 ต้องเปลี่ยนวิธี** จากลบ blob เป็นแก้หรือลบไฟล์ใน `model/` ของคอนเทนเนอร์ที่รันอยู่แล้วให้ readiness fail เมื่อ restart (ใกล้เคียง disk corruption ที่เกิดได้จริง) หรือ deploy image ที่ตั้งใจใส่ artifact ที่พัง

### ทางเลือกที่เลือกรองรับชุด artifact จริง

| ตรวจ | ผล |
|---|---|
| ชุด artifact เป็น directory ของไฟล์ธรรมดา `COPY` เข้า image ได้ | 6 ไฟล์ ไม่มี symlink ไม่มี sparse file |
| loader รับแค่ path ในเครื่อง ไม่ต้องต่อ network | ยืนยันแล้วด้วยการโหลด offline ในส่วนที่ 3 |
| ไม่ต้องมีโค้ดติดต่อ cloud ใน core | `inference.py` ไม่มี `azure`/`boto`/`blob`/`requests` เลย |
| ขนาดพอดีกับงบที่สมมติไว้ | 477 MiB เทียบ Basic container registry ที่ Proposal §6 สมมติไว้แล้ว |

### สูตรแทนค่าให้ P04 — ไม่ใช่ตัวเลขที่เดา

เวลา cold start ที่เพิ่มจาก artifact = **477 MiB ÷ throughput ที่วัดได้**

เป็น**เลขคณิตจากขนาดที่วัดแล้ว** ไม่ใช่การอ้าง throughput ของ Azure ที่เราไม่ได้วัด · **P04 วัด throughput จริงแล้วแทนค่าเอง**

สิ่งที่วัดในเครื่องได้คือ อ่านไฟล์ 477 MiB จาก page cache ที่อุ่นแล้วใช้ **0.10–0.15 วินาที** · ใช้ได้อย่างเดียวคือเป็น **ขอบล่างสุด** — การขนผ่าน network เร็วกว่าการอ่านจากเครื่องตัวเองไม่ได้ · แปลว่าเวลาที่เพิ่มขึ้นมาจาก network แทบทั้งหมด **ไม่ใช่การประมาณเวลาดาวน์โหลด**

---

## 8. ข้อจำกัดที่ติดไปกับผลงาน

**ผลวัดทั้งหมดมาจาก macOS 15.5 arm64 ไม่ใช่ในคอนเทนเนอร์และไม่ใช่บน Azure** — ข้อจำกัดที่ใหญ่ที่สุด:

- `safetensors` ใช้ **mmap** ทำให้ peak RSS หลังโหลด (341 MiB) **ต่ำกว่าขนาดไฟล์ (476 MiB)** เพราะหน้าที่ยังไม่ถูกแตะไม่ถูกนับ · **บน Linux หน้าที่ mmap มาอาจถูกนับเข้า cgroup limit** ซึ่งจะทำให้ตัวเลขจริงใน container สูงกว่านี้ · **ยังไม่ได้ทดสอบ**
- สถาปัตยกรรม CPU ต่างกัน (arm64 เทียบ x86-64 ที่ Azure มักให้) ทำให้เวลาทำนายเทียบตรงไม่ได้
- ไม่มี container memory limit มาบีบ จึงยังไม่รู้ว่าถ้าจำกัดที่ค่าใดจะถูก OOM kill
- **ตัวเลขทุกตัวต้องวัดซ้ำก่อนใช้ตัดสินขนาด container**

**ตัวเลขเวลาวัดซ้ำไม่ได้ข้ามรอบการวัด** — สองรอบคนละวันบนเครื่องเดียวกันให้เวลาต่างกันราวสองเท่าทุกค่า ขณะที่ peak RSS ตรงกัน · **ยังหาสาเหตุไม่ได้** (รายละเอียดและเบาะแสอยู่ใน ส่วนที่ 6) · **ค่าเวลาทุกค่าใช้เป็นเกณฑ์ผ่าน/ไม่ผ่านไม่ได้** และใช้ประมาณ cold start ไม่ได้ · การเทียบสองทางเลือกต้องวัดทั้งสองค่าในรอบเดียวกันเสมอ

**tolerance ใช้ได้เฉพาะ platform ที่วัด** — ถ้า CI รันบน Linux x86-64 **อย่าใช้เกณฑ์ "ตรงทุก bit" เป็น gate ทันที** · เหตุผลและทางเลือกที่แนะนำอยู่ใน ส่วนที่ 2 ท้ายหัวข้อ tolerance

**fresh state ยังไม่สุด** — ลบ `.venv`, HF cache และ `artifacts/` แล้วสร้างใหม่ทั้งหมด แต่ **ยังใช้ Python interpreter ตัวเดิม** (`3.13.11` จาก Anaconda) และ `data/Tweets.csv` ไฟล์เดิม · dataset มี `verify()` ตรวจ sha256 ทุกรอบอยู่แล้ว ส่วน interpreter ยังไม่ได้ทดสอบว่าเปลี่ยน patch version แล้วผลเปลี่ยนไหม — pin ถึงระดับ minor เท่านั้น

**evaluation ประเมิน HF snapshot ไม่ใช่ชุด artifact ที่จะ deploy** — `evaluate.py` ใช้ไฟล์จาก HF cache · ผลใช้กับ artifact ได้ **ผ่านความเท่ากันของ logits บน 300 แถว ไม่ใช่เพราะเป็นไฟล์เดียวกัน** (ส่วนที่ 3) · **ข้อเสนอที่ยังไม่ได้ทำ:** ให้ `evaluate.py` ประเมินจากชุด artifact โดยตรงจะปิดช่องนี้ แต่จะทำให้ evaluation ขึ้นกับ packaging ซึ่งกลับลำดับ dependency

**metric ที่วัดได้คือความตรงกับ label ชุดนี้ ไม่ใช่เพดานความสามารถของ model** — `airline_sentiment_confidence` ต่ำสุด 0.335 · **4,195 แถว (28.7%) ต่ำกว่า 1.0** และ **3,872 แถว (26.4%) ต่ำกว่า 0.7** · label มาจาก crowdsourcing ที่ผู้ตัดสินไม่เห็นตรงกันทุกแถว ความผิดพลาดบางส่วนในตารางจึงอาจมาจาก label ไม่ใช่จาก model · เลือกไม่กรองเพื่อไม่ให้ตัวเลขดูดีขึ้นด้วยดุลพินิจของเรา

**ผลอธิบายประสิทธิภาพบน airline feedback เท่านั้น** ตามที่ Proposal §2 ระบุเอง · ข้อความในชุดนี้เป็นทวีตสั้นเกี่ยวกับสายการบิน ยาวสุด 186 อักขระ จึง **ไม่แตะเพดาน 510 tokens เลย** — การทดสอบ boundary case ต้องใช้ข้อความที่สร้างขึ้นเอง และ P03 ทดสอบ boundary ของ API จาก dataset นี้ไม่ได้

**ไม่ได้ทดสอบว่า tolerance นี้จับความผิดปกติได้จริง** — ยังไม่ได้ลองทำให้ผลเปลี่ยนโดยเจตนา (เช่น เปลี่ยนเวอร์ชัน `torch`) เพื่อดูว่าเกณฑ์จับได้ · การทดลองแบบนั้นใกล้เคียงงาน regression test ใน P05 มากกว่า

**ไม่ได้วัดภายใต้ concurrency** — วัดทีละ request ใน process เดียว · เป้า p95 ที่ 2 concurrent requests เป็นงาน P03–P04

**ยังไม่มีสคริปต์ไล่ย้อน lineage ใน repo** — การไล่ย้อน 36/36 ในส่วนที่ 5 ใช้สคริปต์ชั่วคราวที่ไม่ได้เก็บไว้ · ชั้นที่ 1 มี test กันการถดถอยใน `tests/test_registry.py` แล้ว ส่วนชั้นอื่นยังไม่มี · ถ้า P04 ต้องการ gate ใน CI ต้องเขียนขึ้น โดยใช้ตารางในส่วนที่ 5 เป็นรายการตรวจ

**ยังไม่มีขั้นตอน release หลาย version** — `registry.main()` ลงทะเบียน artifact ชุดเดียวที่มีอยู่ และปฏิเสธถ้าเจอมากกว่าหนึ่งชุดแทนที่จะเดาว่าอันไหน · การจัดการหลาย version พร้อมกันจะจำเป็นตอน rollback ใน **P04** ซึ่งยังไม่ได้ออกแบบ · มี `ponytail:` marker กำกับไว้

**registry เป็นไฟล์ใน Git ไม่ใช่บริการ** — เลือกแบบนี้เพราะไฟล์ใน Git ก็ตรวจย้อนได้ตามที่ R1 ต้องการ · ถ้าภายหลังเลือกบริการที่มี registry ของตัวเอง entry พวกนี้ยังใช้เป็นบันทึกอ้างอิงได้ **ยังไม่ได้ประเมินว่าจะย้ายหรือทำสองที่**

**ตัดสินที่เก็บ artifact โดยไม่ได้ทดลองกับ Azure เลย** — ไม่มี `az` CLI และไม่มี credential ในเครื่อง การสร้าง resource อยู่ใน P04 · การตัดสินวางบนคุณสมบัติเชิงโครงสร้างและสมมติฐานงบที่ Proposal เขียนไว้เอง **ไม่ใช่ผลทดลองบน cloud**

**ยังไม่รู้ว่า Azure Container Apps cache image layer ระหว่าง cold start อย่างไร** — ถ้า cache ดีมากข้อดีของทางเลือก A จะยิ่งชัด ถ้าไม่ cache เลยทั้งสองทางเลือกจะใกล้กันขึ้น · **P04 ต้องตรวจ** และถ้าสมมติฐานนี้ผิดอย่างมีนัยสำคัญ ให้กลับมาทบทวน · **ไม่ได้เทียบทางเลือกที่สาม** (Azure ML model registry, volume mount) เพราะเพิ่มบริการที่ Proposal §6 ไม่ได้สมมติไว้ในงบ

**ข้อจำกัดด้าน licence ของ dataset** — CC BY-NC-SA 4.0 เป็น non-commercial + ShareAlike · ใช้ประเมินในงานเรียนได้และต้องให้เครดิต · ยังไม่ได้ประเมินว่าการเผยแพร่ตัวอย่างข้อความจาก dataset ติดเงื่อนไข ShareAlike แค่ไหน จึง **ไม่ยกข้อความจริงจาก dataset ลง `reports/` แม้แต่แถวเดียว** · ไฟล์ผลเก็บเฉพาะตัวเลขนับและ metadata ของรุ่น ไม่มี token

**ผลทั้งหมดผูกกับ revision `3216a57f…` และ dataset version 4** — ถ้าเปลี่ยนอย่างใดอย่างหนึ่ง ต้องรันใหม่ทั้งหมดเพราะ `max_position_embeddings`, tokenizer, label mapping และ metric อาจต่างไป

---

## 9. ส่วนเชื่อม model เข้า API — ยืนยันได้เท่าที่ฝั่ง module มี

[Overview](../overview-plan.md) มอบให้คนที่ 1 ทั้ง "ดูแล P02" และ "ส่วนเชื่อม model เข้า API" · **ฝั่ง module ยืนยันแล้ว ฝั่ง endpoint ยังไม่มีเพราะเป็นงาน P03**

### Interface ที่ส่งมอบ

```python
from feedbackpulse.inference import (
    SentimentClassifier, Prediction,
    ModelNotReady, InvalidText, TextTooLong,
)
from feedbackpulse.model_files import ensure_model_files

clf = SentimentClassifier.load(ensure_model_files(), model_version="<อ่านจาก registry entry>")  # ครั้งเดียวตอน process เริ่ม
result = clf.predict("My flight was delayed.")   # ต่อ request
# -> Prediction(sentiment='negative', score=0.943575, model_version='sentiment-6e7ff9fbc17c-850de906')
```

| ตรวจ | ผล |
|---|---|
| `Prediction` มี 3 fields ตรงกับ [P01-T02 §3](../docs/plans/P01-T02-api-contract.md#3-request-และ-response) | `sentiment: str`, `score: float`, `model_version: str` — ไม่มีเกิน |
| exception map ครบ 3 สถานะที่ [P01-T02 §4](../docs/plans/P01-T02-api-contract.md#4-validation-และ-error-handling) กำหนด | `ModelNotReady` ← `RuntimeError` → `503` · `TextTooLong` ⊂ `InvalidText` ← `ValueError` → `422` |
| โหลดครั้งเดียวตอน `load()` ตาม [P01-T03 §3](../docs/plans/P01-T03-system-structure.md#3-ส่วนให้บริการ--รับ-feedback-แล้วทำนาย) | `predict()` ไม่มี `from_pretrained` · `__init__` รับ model ที่โหลดแล้ว |
| core ไม่อ่าน env ไม่ต่อ network ไม่เรียก cloud | `inference.py` ไม่มี `os.environ`, `getenv`, `requests`, `azure`, `boto` |
| **มี tokenize และ predict ชุดเดียวใน `src/`** | `AutoTokenizer`, `softmax`, `argmax` พบเฉพาะใน `inference.py` |
| `ruff check` · `ruff format --check` · `pytest` | ผ่านทั้งหมด · **35 tests** |

**`package_artifact.py` เรียก `from_pretrained` ด้วย** — เพื่อ **แปลง weights เป็น safetensors เท่านั้น** (`save_model` + `state_dict`) ไม่มี tokenizer ไม่มี softmax/argmax ไม่ทำนาย · มันยังโหลดชุดที่ build เสร็จผ่าน `SentimentClassifier.load()` เพื่ออ่าน `labels` และ `max_content_tokens` จึงไม่มี path ทำนายที่สอง

**`TextTooLong` สืบทอดจาก `InvalidText`** จึงจับ `InvalidText` ตัวเดียวแล้วตอบ `422` ได้ทั้งสองกรณี · `TextTooLong` มี `.token_count` และ `.limit` ให้ใส่ในข้อความ error

### พฤติกรรมที่มี test กันการถดถอย

| พฤติกรรม | test |
|---|---|
| **เพดานตรวจก่อนเรียก model** — 511 tokens ถูกปฏิเสธด้วย `TextTooLong` ไม่ถึง forward pass ที่จะโยน `RuntimeError` และกลายเป็น `500` | `test_text_one_token_over_the_limit_is_rejected_not_truncated` |
| **ไม่ตัดข้อความ** ตามที่ P01-T02 §3 ห้าม | test เดียวกัน (ได้ exception ไม่ได้ผลทำนายจากข้อความที่ถูกตัด) |
| ชื่อกลุ่มอ่านจาก config ไม่ hardcode ลำดับ index | `test_labels_come_from_the_model_config` |
| เพดานตรงกับค่าที่วัดได้ (510) | `test_token_limit_matches_the_recorded_value` |
| tokenizer ไม่รายงานค่า sentinel | `test_tokenizer_reports_a_usable_limit_rather_than_the_sentinel` |
| `model_version` คืนค่าที่ส่งเข้ามา ไม่ได้ตั้งเอง | `test_prediction_matches_the_api_contract` |
| โหลดไม่สำเร็จได้ error ที่แยกแยะได้ | `test_load_failure_is_distinguishable` |
| **version ที่คำนวณใหม่จาก lineage ที่เก็บ ตรงกับชื่อ entry** | `tests/test_registry.py` |
| fingerprint จับผลทำนายที่ต่างกันแต่ confusion matrix เท่ากัน | `tests/test_evaluation.py` |

### ยืนยันด้วยการตรวจครั้งเดียว — ไม่มี test กันการถดถอย

| พฤติกรรม | หลักฐาน | ช่องว่าง |
|---|---|---|
| **โหลดครั้งเดียว** weights อยู่ใน instance ไม่โหลดใหม่ต่อ `predict()` | จริงโดยโครงสร้าง — `predict()` ไม่เรียก `from_pretrained` | ไม่มี test ที่ assert ว่า `predict()` ไม่โหลดซ้ำ ถ้ามีใครย้ายการโหลดเข้าไปใน `predict()` จะไม่มีอะไรจับได้ |
| **core ไม่อ่าน env ไม่ต่อ network** · **มี tokenize ชุดเดียว** | `grep` ใน `src/` | เป็นการตรวจ ณ เวลานั้น **ไม่กันคนเพิ่มภายหลัง** · ถ้าต้องการบังคับจริงต้องมี test หรือ lint rule ที่สแกน `src/` ซึ่งยังไม่มี |

### ยังยืนยันไม่ได้ และเป็นของใคร

**"evaluation path กับ API path เรียกฟังก์ชันเดียวกัน" ยืนยันได้ครึ่งเดียว** — ฝั่ง evaluation ยืนยันแล้ว: `evaluate.py` เรียก `SentimentClassifier.predict()` ทีละข้อความ ไม่ได้ tokenize เอง · **ฝั่ง API ยืนยันไม่ได้เพราะยังไม่มี endpoint** → **P03 ต้องตรวจซ้ำ**

**`make portability-audit` ไม่ใช่จุดตรวจของ P02** — [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน) ให้ตรวจการแยก core, configuration และ **cloud adapter** โดยมีเงื่อนไขว่า "เมื่อพัฒนาส่วนที่เกี่ยวข้องแล้ว" · **P02 ไม่มี cloud adapter** จึงเป็นจุดตรวจของ **P03–P04** · ส่วนที่ P02 รับผิดชอบคือแยก core (`inference.py`) ออกจาก configuration (`model_files.py`) ซึ่งตรวจแล้วข้างบน

**ยังไม่มีการตรวจว่า version ที่ deploy ตรงกับ artifact ที่โหลดจริง** — `load()` รับ `model_version` ที่ส่งมาเฉย ๆ ถ้า P03 ส่งค่าผิด API จะคืนค่าผิดโดยไม่มีอะไรจับได้

registry entry และ `manifest.json` มี hash ของทุกไฟล์ให้ตรวจได้ แต่ **การเรียกตรวจตอน startup เป็นของ P03** ตาม P01-T02 §4 และการตัดสินว่าอะไรนับเป็น "artifact ใช้งานไม่ได้" เป็นของ **P05** · P02 ไม่เขียนฟังก์ชันตรวจไว้ล่วงหน้าเพราะยังไม่มีผู้ใช้ และจะต้องเดา call site กับ error semantics ของเขา

**สถานะงาน การตัดสินที่ล็อก ขอบเขตความรับผิดชอบ และแผนที่ task → ส่วนไหนของรายงานนี้** อยู่ใน [phase plan](../docs/plans/P02-model-pipeline.md) ไม่เล่าซ้ำที่นี่
