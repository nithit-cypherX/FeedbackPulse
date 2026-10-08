# P03 — รายงานหลักฐานการพัฒนาและทดสอบ Backend ในเครื่อง (Evidence Report)

- **วันที่ทดสอบ:** 2026-10-08
- **สถานะ:** `done`
- **เกณฑ์ที่ตอบสนอง:** **R2 (Deployment & Container readiness)**, **R4 (Readiness/Liveness probe separation)**
- **Image ที่สร้าง:** `feedbackpulse:local` (image id: `d7a3500d767a`)
  - **Base image builder:** `python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c` (pinned strictly by digest, no tag)
  - **Uv binary builder:** `ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21` (pinned strictly by digest, no tag)
  - **Base image runtime:** `python@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c` (pinned strictly by digest, no tag)
  - **Security check:** Non-root user `appuser` (UID 10001), Zero credentials baked into image layers (credentials arrive via runtime environment variables only).
- **Model Version ที่ยืนยัน:** `sentiment-6e7ff9fbc17c-0110c462`

---

## 1. สรุปผลการทดสอบระดับ Automated Test Suite (Checklist Verification)

รันคำสั่ง: `uv run pytest` บนสภาพแวดล้อม Python 3.13.0
- **ผลการทดสอบทั้งหมด:** **55 ผ่านครบทุกรายการ (55 passed)** ในเวลา ~7.68 วินาที
- **การทดสอบ API เฉพาะเจาะจง (`tests/test_api.py`):** 18 รายการ ครอบคลุม checklist ทั้ง 11 ข้อใน `P01-T02 §6`:

| ข้อที่ | ข้อกำหนดใน Checklist | พฤติกรรมที่สังเกตได้จริง | ผลทดสอบ |
|---|---|---|---|
| 1–3 | Request ถูกต้องพร้อม token คืน 200 ครบทั้ง 3 fields (`sentiment`, `score`, `model_version`) | ได้ HTTP 200, sentiment อยู่ใน 3 class, score อยู่ใน [0, 1], model_version ตรงกับ registry | **PASS** |
| 4 | JSON เสียรูปแบบ คืน 400 | ส่ง invalid JSON string ได้ HTTP 400 code `BAD_REQUEST` | **PASS** |
| 5 | ไม่มี text, เป็น null, ตัวเลข, list, ข้อความว่าง หรือมีแต่ช่องว่าง คืน 422 | ส่งค่ารูปแบบดังกล่าวทั้งหมดได้ HTTP 422 code `INVALID_TEXT` | **PASS** |
| 6 | เพดานความยาว 510 tokens รับได้ (200), 511 tokens ปฏิเสธ (422 `TEXT_TOO_LONG`) โดยไม่ตัดทิ้งเงียบ ๆ | ทดสอบขอบเขต 510 tokens -> 200, 511 tokens -> 422 `TEXT_TOO_LONG` | **PASS** |
| 7 | ไม่มี token หรือ token ผิด ได้ 401 พร้อม header `WWW-Authenticate: Bearer` และไม่เรียก model | ส่งไม่มี token หรือ token ผิด ได้ HTTP 401 พร้อม header ครบถ้วน | **PASS** |
| 8–9 | Model พร้อม `/ready` ได้ 200; Model ไม่พร้อม `/health` ได้ 200 แต่ `/ready` และ `/predict` ได้ 503 | เมื่อโหลด model ไม่สำเร็จ: `/health` -> 200, `/ready` -> 503, `/predict` -> 503 code `MODEL_NOT_READY` ไม่คืนผลทำนายปลอม | **PASS** |
| 10 | Error ไม่คาดคิดคืน 500 โดยไม่ leak stack trace หรือ internal secrets | จำลอง exception ได้ HTTP 500 code `INTERNAL_ERROR` โดยไม่มีข้อความลับใน body | **PASS** |
| 11 | Error payload ตาม schema และ logs ไม่เก็บ token หรือ feedback ฉบับเต็ม | รูปแบบ JSON ตรงตามสัญญา และ caplog ไม่พบบันทึก token หรือข้อความลับ | **PASS** |

- **การตรวจสอบ Linter:** `uv run ruff check` ผ่าน 100% ไม่มีข้อผิดพลาด

---

## 2. ผลการทดสอบบน Docker Container จริง (`feedbackpulse:local`)

สร้างด้วย `docker build -t feedbackpulse:local .` (Multi-stage build, non-root user `appuser`, baked model artifacts).

### 2.1 Smoke Test Endpoints ใน Container

```bash
docker run -d --name feedbackpulse-test -p 8000:8000 -e SERVICE_TOKEN="test-token-123" feedbackpulse:local
```

#### 1) Liveness Probe (`GET /health`):
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"healthy"}
```

#### 2) Readiness Probe (`GET /ready`):
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"ready","model_version":"sentiment-6e7ff9fbc17c-0110c462"}
```

#### 3) Prediction Tests (`POST /predict`):
- **Positive input:** `"Flight attendant was super polite and helpful. Amazing trip!"`
  ```json
  {"sentiment":"positive","score":0.9855,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```
- **Negative input:** `"Worst experience ever. Lost luggage and flight delayed 10 hours."`
  ```json
  {"sentiment":"negative","score":0.9536,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```
- **Neutral input:** `"Flight UA123 departed on schedule."`
  ```json
  {"sentiment":"neutral","score":0.8869,"model_version":"sentiment-6e7ff9fbc17c-0110c462"}
  ```

#### 4) Error Handling Verification:
- **Unauthorized (Wrong Token):**
  ```http
  HTTP/1.1 401 Unauthorized
  www-authenticate: Bearer

  {"error":{"code":"UNAUTHORIZED","message":"Missing or invalid service token."}}
  ```
- **Malformed JSON:**
  ```http
  HTTP/1.1 400 Bad Request

  {"error":{"code":"BAD_REQUEST","message":"Request body must be valid JSON."}}
  ```
- **Empty text:**
  ```http
  HTTP/1.1 422 Unprocessable Content

  {"error":{"code":"INVALID_TEXT","message":"text must be a non-empty string."}}
  ```
- **Over 510 tokens:**
  ```http
  HTTP/1.1 422 Unprocessable Content

  {"error":{"code":"TEXT_TOO_LONG","message":"text is 601 tokens, limit is 510"}}
  ```

---

## 3. ผลการวัด Memory Usage ของ Container

วัดด้วยคำสั่ง `docker stats --no-stream feedbackpulse-test`:

| Metric | ค่าที่วัดได้ใน Linux Container | หมายเหตุ |
|---|---|---|
| **Memory Usage (Active)** | **645.8 MiB** | หลังโหลด model และให้บริการคำขอแล้ว |
| **CPU Usage** | **0.51%** | ขณะ idle |
| **PIDs** | **24** | รวม worker threads และ PyTorch runtime |

> **ข้อมูลสำหรับ P04 (Azure Container Apps Resource Sizing):**
> จากผลวัดจริง 645.8 MiB ทำให้คอนฟิก 1 vCPU / 1.5–2.0 GiB RAM บน Azure Container Apps Consumption plan ปลอดภัยเพียงพอต่อการรับงาน 2 concurrent requests โดยไม่เกิด Out-Of-Memory (OOM) และประหยัดงบประมาณตาม Proposal §6

---

## 4. ผลการทดสอบ Simulated Failure (Model Unavailability)

รัน container จำลองสถานการณ์โมเดลโหลดไม่สำเร็จ (`MODEL_DIR=/nonexistent_dir`):
```bash
docker run -d --name feedbackpulse-broken -p 8001:8000 -e MODEL_DIR="/nonexistent_dir" feedbackpulse:local
```

**ผลลัพธ์ที่วัดได้จริง:**
1. Container process ยังทำงานต่อไปได้ (ไม่ crash-loop ทันที)
2. `GET /health` ตอบ **HTTP 200 OK** (`{"status":"healthy"}`)
3. `GET /ready` ตอบ **HTTP 503 Service Unavailable**
   ```json
   {"error":{"code":"MODEL_NOT_READY","message":"The model is not ready. Please try again later."}}
   ```
4. `POST /predict` ตอบ **HTTP 503 Service Unavailable** โดยไม่สร้างผลทำนายปลอม

หลักฐานนี้ยืนยันว่าการแยก readiness check ออกจาก liveness check ทำงานได้สมบูรณ์ และเป็นฐานพร้อมสำหรับ **P05 (Planned failure drill)**

---

## 5. การส่งต่องานสู่ P04

- **คนที่ 2 (Backend and Deployment):**
  - Container image `feedbackpulse:local` พร้อมแล้ว สามารถนำ `Dockerfile` และ workflow ไปตั้งค่า GitHub Actions CI/CD ใน P04
  - ค่า environment `SERVICE_TOKEN`, `MODEL_DIR`, `MODEL_VERSION` จัดการผ่าน `cloud.env.example`
