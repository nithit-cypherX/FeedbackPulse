# P02-T02 — Evaluation dataset

- Task: [P02-T02 ใน phase plan](../docs/plans/P02-model-pipeline.md) · ขอบเขต: [Proposal §2](../PROPOSAL.md#2-model-and-dataset)
- รันเมื่อ: 2026-10-07 · เครื่อง: macOS 15.5 arm64 · Python 3.13.11 · `kagglehub 1.0.2`

รายงานนี้เป็น **หลักฐานของสิ่งที่รันจริง** ไม่ใช่ข้อตกลง · ตัวไฟล์ dataset ไม่เข้า Git ตาม [P01-T03 §7](../docs/plans/P01-T03-system-structure.md#7-อะไรเข้า-git-และอะไรไม่เข้า)

---

## 1. ตรวจอะไร

ยืนยันว่า evaluation set ที่ T05 จะใช้ **ชี้ชัดได้ว่าเป็นข้อมูลชุดไหน และดึงซ้ำได้ของเดิม** ตามเกณฑ์ R1 พร้อมยืนยันว่า label ของ dataset ใช้กับ 3 กลุ่มของ model ได้

## 2. ใช้รุ่นและเงื่อนไขไหน

| รายการ | ค่า |
|---|---|
| Dataset | `crowdflower/twitter-airline-sentiment` (ลิงก์จาก Proposal §2) |
| **Version ที่ pin** | **4** |
| Licence | CC BY-NC-SA 4.0 |
| Client | `kagglehub` |
| ไฟล์ที่ใช้เป็น evaluation set | `data/Tweets.csv` |
| ขนาด | 3,421,431 bytes |
| **sha256** | `ea94b23f41892b290dec3330bb8cf9cb6b8bc669eaae5f3a84c40f7b0de8f15e` |

**วิธีรันซ้ำ:**

```python
import kagglehub, shutil, os
p = kagglehub.dataset_download("crowdflower/twitter-airline-sentiment/versions/4")
os.makedirs("data", exist_ok=True)
shutil.copyfile(os.path.join(p, "Tweets.csv"), "data/Tweets.csv")
```

**สิทธิ์ที่ต้องใช้:** ต้องมี Kaggle API token · `kagglehub 1.0.2` อ่านจาก env `KAGGLE_USERNAME` + `KAGGLE_KEY`, env `KAGGLE_API_TOKEN`, ไฟล์ `~/.kaggle/kaggle.json` หรือ `KAGGLE_CONFIG_DIR` · สร้าง token ที่ <https://www.kaggle.com/settings/api>

**บันทึกเฉพาะวิธีได้มา ไม่เก็บค่า token** ที่ใดในรายงานหรือใน repo ตามจุดตรวจ Secrets ใน [P01-T03 §10](../docs/plans/P01-T03-system-structure.md#10-จุดตรวจที่ต้องไม่หลุดระหว่างทำงาน)

**ทำไมใช้ `kagglehub` ไม่ใช่ `kaggle` CLI:** Proposal §2 ระบุ **version 4** · `kagglehub` รับ handle `.../versions/4` และ parse ได้ `version=4, is_versioned=True` ส่วน `kaggle datasets download` ไม่มี flag เลือก version (ตรวจ argparse ของ CLI แล้ว) จึง pin ไม่ได้

Version 4 มี 2 ไฟล์คือ `Tweets.csv` และ `database.sqlite` (5,038,080 bytes) ซึ่งเป็นข้อมูลชุดเดียวกันในอีกรูปแบบ · **ใช้ `Tweets.csv` เป็นแหล่งเดียว** เพื่อไม่ให้มีสองแหล่งที่อาจไม่ตรงกัน

## 3. คาดหวังอะไร

- ดึงซ้ำจาก version 4 แล้วได้ไฟล์ที่ sha256 ตรงกับที่บันทึก
- `airline_sentiment` ต้องแยกเป็นกลุ่มที่ใช้กับ `negative`, `neutral`, `positive` ของ model ได้
- Kaggle token ต้องไม่หลุดเข้า Git

## 4. ได้ผลอะไร

### นิยาม evaluation set

**ใช้ทุกแถวในไฟล์ = 14,640 แถว** (ไม่รวม header) · 15 columns · ใช้ column `text` เป็น input และ `airline_sentiment` เป็น label

| การตัดสินใจ | เหตุผล |
|---|---|
| **ไม่ sample** ใช้ทั้งไฟล์ | ไม่ต้องพึ่ง random seed ในการเลือกแถว ทำให้ชุดทดสอบนิ่งและเทียบกันได้ตรง ๆ ใน T08 |
| **ไม่ split train/test** | ไม่ได้ train หรือ fine-tune (Proposal §2) จึงไม่มีเหตุต้องกันข้อมูลไว้ |
| **ไม่กรองด้วย `airline_sentiment_confidence`** | การเลือกเกณฑ์กรองเป็นดุลพินิจของเรา ถ้ากรองจะทำให้ตัวเลขดูดีขึ้นโดยไม่มีฐาน · ดูข้อจำกัดในส่วนที่ 5 |

**ไม่มี random seed ที่เกี่ยวข้องกับการเลือกแถว** เพราะไม่ได้สุ่มเลย · ถ้า T05 หรือ T08 ต้องสุ่มลำดับหรือทำ batch ต้องบันทึก seed ของขั้นตอนนั้นแยก

### Label mapping

ค่าใน `airline_sentiment` ที่พบจริง เทียบกับ `id2label` ของ model ที่บันทึกใน [P02-T01](P02-T01-model-provenance.md):

| `airline_sentiment` ใน dataset | จำนวนแถว | สัดส่วน | ตรงกับ label ของ model |
|---|---:|---:|---|
| `negative` | 9,178 | 62.7% | `negative` (index 0) |
| `neutral` | 3,099 | 21.2% | `neutral` (index 1) |
| `positive` | 2,363 | 16.1% | `positive` (index 2) |

**ชื่อกลุ่มตรงตัวกันทั้ง 3 กลุ่ม ไม่ต้องสร้างตารางแปลง** · เทียบ label ได้ด้วยการจับคู่ string ตรง ๆ แต่โค้ดต้องอ่านชื่อกลุ่มจาก `config.json` ของ model ตอน runtime ไม่ hardcode ลำดับ index

### ความสมบูรณ์ของข้อมูล

| ตรวจ | ผล |
|---|---|
| แถวที่ `text` ว่างหรือมีแต่ช่องว่าง | **0** |
| แถวที่ไม่มี label | **0** |
| label นอก 3 กลุ่ม | **ไม่มี** |
| ความยาว `text` | 12–186 อักขระ เฉลี่ย 103.8 |

การตัดสินใจ "ใช้ทุกแถว ไม่กรอง" ที่วางไว้ล่วงหน้าจึงใช้ได้จริง ไม่ต้องปรับ เพราะไม่มีแถวเสียที่ต้องจัดการ

### ผล Check

- **ดึงซ้ำได้ของเดิม:** ดาวน์โหลด version 4 ใหม่ลง `KAGGLEHUB_CACHE` แยกคนละที่กับ cache หลัก แล้วเทียบ sha256 ของ `Tweets.csv` → **ตรงกันทุก byte** · cache ชั่วคราวลบแล้ว
- **ไม่มี token หลุดเข้า Git:** ค้น pattern `KGAT_…`, `KAGGLE_KEY=`, `KAGGLE_API_TOKEN=` ใน **ทุก commit ของ Git history** และในไฟล์ที่จะ commit (tracked + untracked ที่ไม่ถูก ignore) → **ไม่พบ** · `git check-ignore` ยืนยันว่า `data/Tweets.csv` ถูกกันด้วย `.gitignore:31`

## 5. มีข้อจำกัดอะไร และส่งต่ออะไร

**คุณภาพ label — สำคัญต่อการอ่านผล T05:** `airline_sentiment_confidence` ต่ำสุด 0.335 · **4,195 แถว (28.7%) มีค่าต่ำกว่า 1.0** และ **3,872 แถว (26.4%) ต่ำกว่า 0.7** · label ชุดนี้มาจาก crowdsourcing ที่ผู้ตัดสินไม่เห็นตรงกันทุกแถว ดังนั้น metric ที่ T05 วัดได้ **ไม่ใช่เพดานความสามารถของ model แต่เป็นความตรงกับ label ชุดนี้** · เราเลือกไม่กรองเพื่อไม่ให้ตัวเลขดูดีขึ้นด้วยดุลพินิจของเรา แต่ต้องเขียนข้อจำกัดนี้กำกับผลทุกครั้ง

**class imbalance:** `negative` 62.7% เทียบกับ `positive` 16.1% → **accuracy เพียงตัวเดียวจะทำให้เข้าใจผิด** เพราะเดา `negative` ทั้งหมดก็ได้ 62.7% แล้ว · T05 ควรเลือก metric ที่สะท้อนทุกกลุ่ม เช่น macro-F1 และรายงาน per-class ประกอบ

**ส่งต่อให้ T03:** `text` ยาวสุด 186 อักขระ ซึ่งสั้นกว่าเพดาน 512 token ของ model มาก → **ชุดนี้จะไม่แตะเพดานความยาวข้อความเลย** ดังนั้น T03 ต้องยืนยันเพดานด้วยข้อความที่สร้างขึ้นเอง ไม่ใช่จาก dataset นี้ และ boundary case ของ API ใน P03 ก็ทดสอบจาก dataset นี้ไม่ได้

**ส่งต่อให้ P03–P04:** ชุดนี้คือ **versioned test set** เดียวกับที่ [Proposal §3](../PROPOSAL.md#3-serving-pattern-and-requirements) อ้างถึงตอนวัดเป้า p95 ≤ 3 วินาที · ให้ใช้ไฟล์ที่ sha256 ตรงกับที่บันทึกไว้ ไม่สร้างชุดใหม่

**ข้อจำกัดด้าน licence:** CC BY-NC-SA 4.0 เป็น **non-commercial + ShareAlike** · ใช้ประเมินในงานเรียนได้และต้องให้เครดิต · ยังไม่ได้ประเมินว่าการเผยแพร่ตัวอย่างข้อความจาก dataset ในรายงานหรือ model card ติดเงื่อนไข ShareAlike แค่ไหน จึงหลีกเลี่ยงการยกข้อความจริงลง `reports/` และไม่ยกตัวอย่างข้อความใดในรายงานนี้ · ถ้า T05 จำเป็นต้องยกตัวอย่าง ต้องตัดสินเรื่องนี้ก่อน

**ข้อจำกัดอื่น:** ผลนี้ผูกกับ version 4 และ sha256 ที่บันทึกไว้เท่านั้น ถ้าเปลี่ยน version ต้องรัน T02 ใหม่และตรวจ T05 กับ T08 ซ้ำ
