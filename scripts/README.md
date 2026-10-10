# FeedbackPulse — Automation & Verification Scripts

โฟลเดอร์นี้รวบรวม Script สำหรับการตรวจสอบคุณภาพ (Smoke Test) และการทดสอบกระบวนการปล่อยและกู้คืนเวอร์ชัน (Rollback Verification) บน **Azure Container Apps** ตามเกณฑ์ **R2 (Deployment & CI/CD)** ของวิชา ITCS355

---

## สารบัญ Script

| ไฟล์ Script | วัตถุประสงค์ | คำสั่งรัน | บันทึกหลักฐานที่ |
|---|---|---|---|
| [`cloud_check.py`](cloud_check.py) | ตรวจสอบ API Contract 12 รายการบน Public URL, วัด Cold-Start Time และ Error Rate แยกต่างหาก | `make smoke-test` | `reports/P04-cloud-check.json` |
| [`verify_rollback.py`](verify_rollback.py) | ทดสอบและพิสูจน์กระบวนการ Rollback (สลับ Traffic 100% กลับเวอร์ชันเดิมแบบ Zero-Downtime) | `make verify-rollback [SIMULATE=1]` | `reports/P04-rollback-evidence.json` |

---

## 1. คำอธิบายสถาปัตยกรรม Rollback (Native Revision Management)

ระบบ Cloud บน **Azure Container Apps** ถูกตั้งค่าด้วย `activeRevisionsMode: Multiple` ในไฟล์ IaC (`cloudlayer/containerapp.template.yaml`):

- **ไม่ใช่การลบแล้วสร้าง Container App ใหม่:** ระบบยังคงใช้ Public FQDN URL เดิมเสมอ (`https://feedbackpulse-api...azurecontainerapps.io`)
- **Blue/Green Instant Cutover (100 / 0):** แต่ละเวอร์ชันที่ Deploy จะถูกสร้างเป็น **Revision** ที่ไม่สามารถแก้ไขได้ (Immutable Snapshot) 
  - `feedbackpulse-api--2zaws5o`: **[PREVIOUS STABLE]** เวอร์ชันเสถียรตัวเดิม
  - `feedbackpulse-api--rev2`: **[NEW / LATEST]** เวอร์ชันใหม่ที่เพิ่งปล่อย
- เมื่อเกิดปัญหาในเวอร์ชันใหม่ Load Balancer ของ Ingress จะโยก Traffic 100% กลับไปยังเวอร์ชันเดิมได้ทันทีในเวลา **~15 วินาที** โดยไม่ต้อง Build Docker Image ใหม่ และไม่ต้อง Revert Git Commit

---

## 2. วิธีการทดสอบ Rollback (Rollback Testing Guide)

สามารถทดสอบได้ **3 รูปแบบ** ตามความสะดวกในการใช้งานหรือการ Demo:

### วิธีที่ 1: การทดสอบอัตโนมัติครบวงจรในคำสั่งเดียว (Automated 1-Click Test — แนะนำ)

คำสั่งนี้จะจำลองสถานการณ์ตั้งแต่ต้น: ปล่อยของใหม่ให้รับ Traffic 100% $\rightarrow$ สั่ง Rollback กลับของเดิม 100% $\rightarrow$ รอป้องกัน Cold-start $\rightarrow$ ยิงทดสอบ Endpoint:

```bash
make verify-rollback SIMULATE=1
```
หรือ
```bash
python scripts/verify_rollback.py --simulate-new-first
```

> [!NOTE]
> **ทำไมต้องใช้ `SIMULATE=1` แทนที่จะเป็น `make verify-rollback --simulate-new-first`? และเลข `1` หมายถึงอะไร?**
>
> 1. **ทำไมรัน `make verify-rollback --simulate-new-first` ตรงๆ ไม่ได้?**
>    - โปรแกรม **GNU Make** จะมองว่าอาร์กิวเมนต์ที่ขึ้นต้นด้วย `--` เป็น Option ของตัวคำสั่ง `make` เอง (เช่น `make --help`, `make --dry-run`)
>    - หากส่ง `--simulate-new-first` ต่อท้าย `make` ระบบจะแจ้งเตือน Error ทันทีว่า `make: unrecognized option '--simulate-new-first'` เพราะ Make ไม่ได้ส่ง Flag แปลกปลอมต่อให้คำสั่งภายในอัตโนมัติ
>
> 2. **เลข `1` ใน `SIMULATE=1` หมายถึงอะไร?**
>    - เลข `1` คือสัญลักษณ์แทนค่าจริง (**Boolean `True`** หรือ Flag Enabled) ตามแบบแผนสากลของ Unix CLI / Makefile
>    - ใน [`Makefile`](../Makefile) ถูกเขียนเงื่อนไขไว้ดังนี้:
>      ```makefile
>      verify-rollback:
>      	PYTHONPATH=src $(UV) run python scripts/verify_rollback.py $(if $(SIMULATE),--simulate-new-first,) $(ARGS)
>      ```
>      ฟังก์ชัน `$(if $(SIMULATE),...)` ของ Make จะตรวจสอบว่า ถ้าตัวแปร `SIMULATE` ไม่เป็นค่าว่าง (เช่น เป็น `1`, `true`, `yes`) ระบบ Make จะทำการแทรก Flag `--simulate-new-first` เข้าไปในคำสั่ง Python เบื้องหลังให้โดยอัตโนมัติ
>
> 3. **สรุป 3 ทางเลือกในการส่ง Flag จำลองสถานการณ์:**
>    - `make verify-rollback SIMULATE=1` *(แนะนำที่สุด — สั้น กระชับ จำง่าย)*
>    - `make verify-rollback ARGS="--simulate-new-first"` *(ส่งผ่านตัวแปร ARGS เข้าไป)*
>    - `python scripts/verify_rollback.py --simulate-new-first` *(รันคำสั่งผ่าน Python โดยตรงโดยไม่ผ่าน Make)*
>
> *(หมายเหตุ: หากรัน `make verify-rollback` เฉยๆ โดยไม่ใส่ `SIMULATE=1` สคริปต์จะทำการ Rollback ย้อนกลับจากสถานะ Traffic ปัจจุบันทันที)*

**สิ่งที่สคริปต์ทำงาน:**
1. แสดงรายชื่อ Revision ทั้งหมดและจัดลำดับเวลา (เก่าสุด = Stable, ใหม่สุด = Latest)
2. สลับ Ingress ให้ New Revision (`rev2`) รับ Traffic 100% (จำลองเหตุการณ์ก่อนเกิดปัญหา)
3. สั่ง Rollback สลับ Traffic 100% กลับมายัง Stable Revision (`2zaws5o`) ทันที
4. รอระบบ Polling Readiness จนกว่า Container จะตื่นและโหลด RoBERTa Model พร้อม (`/ready` 200 OK)
5. ยิงทดสอบ `/health`, `/ready`, `/predict` เพื่อยืนยันว่าระบบกลับมาปกติ 100%
6. บันทึกหลักฐานลงใน `reports/P04-rollback-evidence.json`

---

### วิธีที่ 2: การทดสอบทีละขั้นตอนด้วยตนเอง (Manual Step-by-Step)

หากต้องการสาธิตให้อาจารย์ดูทีละขั้นตอน:

#### สเต็ป 1: สลับ Traffic ไปยังเวอร์ชันใหม่ (New Version 100%)
```bash
make change-traffic REV=feedbackpulse-api--rev2
```
*ตรวจผลลัพธ์:* รัน `make status` จะเห็น `rev2` ได้รับ Traffic 100%

#### สเต็ป 2: สั่ง Rollback ย้อนกลับไปหาเวอร์ชันเดิมที่เสถียร (Rollback to Stable 100%)
```bash
make verify-rollback
```
*(สคริปต์จะตรวจพบว่าของใหม่อยู่ที่ 100% และจะสั่งสลับกลับไปหาของเดิม `2zaws5o` ทันที พร้อมยิงทดสอบระบบให้)*

#### สเต็ป 3: ตรวจสอบสถานะยืนยัน
```bash
make status
```
*ผลลัพธ์จะแสดงว่ากลับมาที่ Revision เดิมเรียบร้อย:*
```json
"Traffic": [
  {
    "revisionName": "feedbackpulse-api--2zaws5o",
    "weight": 100
  }
]
```

---

### วิธีที่ 3: ปรับผ่านหน้าจอ Azure Portal (GUI Visualization)

1. เปิด Azure Portal $\rightarrow$ เข้าไปที่ **`feedbackpulse-api`**
2. เมนูด้านซ้ายเลือก **Application $\rightarrow$ Revision management**
3. ปรับค่าในช่อง **Traffic (%)**:
   - `feedbackpulse-api--rev2`: **0%**
   - `feedbackpulse-api--2zaws5o`: **100%**
4. กดปุ่ม **`💾 Save`** ด้านบน
5. สามารถสลับเป็น Canary Deployment เช่น **50% / 50%** เพื่อกระจายโหลดได้เช่นกัน

---

## 3. ตัวอย่างผลลัพธ์ที่บันทึกในรายงานหลักฐาน

เมื่อรัน `verify_rollback.py` ผลลัพธ์จะถูกบันทึกเป็น JSON ใน [`reports/P04-rollback-evidence.json`](../reports/P04-rollback-evidence.json):

```json
{
  "timestamp_utc": "2026-10-10T07:49:09Z",
  "container_app": "feedbackpulse-api",
  "resource_group": "itcs355-6688166",
  "newest_revision": "feedbackpulse-api--rev2",
  "previous_stable_revision": "feedbackpulse-api--2zaws5o",
  "rollback_target_revision": "feedbackpulse-api--2zaws5o",
  "shift_duration_seconds": 15.27,
  "endpoint_verification": {
    "health": { "status_code": 200, "latency_ms": 64.3 },
    "ready": { "status_code": 200, "latency_ms": 63.28 },
    "predict": { "status_code": 200, "latency_ms": 110.46 }
  },
  "status": "PASSED"
}
```
