# P03 — ทำ backend ให้ใช้งานได้ในเครื่อง

- **สถานะ:** `done`
- **เจ้าของ:** คนที่ 2 — Backend และ deployment
- **แผนหลัก:** [Overview](../../overview-plan.md) · **ขอบเขต:** [Proposal](../../PROPOSAL.md) · **ข้อตกลงที่ต้องทำตาม:** [P01-T02 API contract](P01-T02-api-contract.md) · [P01-T03 System structure](P01-T03-system-structure.md) · [P02 Model pipeline](P02-model-pipeline.md)
- **หลักฐานทั้งเฟส:** [reports/P03-evidence.md](../../reports/P03-evidence.md)

---

## 1. ขอบเขตและเป้าหมาย

**ผลที่ต้องได้:**
ระบบ backend API และ Docker container ที่รันได้จริงในเครื่อง พร้อมชุดทดสอบที่ยืนยัน checklist ใน [P01-T02 §6](P01-T02-api-contract.md#6-checklist-สำหรับตรวจตอน-implement) ครบทุกข้อ เพื่อเป็นฐานที่มั่นคงก่อนนำไป deploy บน Azure Container Apps ใน P04 (ตอบโจทย์เกณฑ์ **R2**)

**สิ่งที่ส่งมอบแล้วใน P03:**
1. โค้ด configuration และ service API แยกส่วนตามกติกา core / configuration / cloud adapter ([P01-T03 §4](P01-T03-system-structure.md#4-อยู่ใน-container-เดียวกัน-แต่แยกหน้าที่ของโค้ด)) ใน `src/feedbackpulse/config.py` และ `src/feedbackpulse/api.py`
2. Endpoints ครบ 3 เส้น: `POST /predict`, `GET /health`, `GET /ready` ตามข้อตกลงใน [P01-T02](P01-T02-api-contract.md)
3. Validation, access control (Bearer token) และ error format ที่ตรงตามมาตรฐาน RFC และ API contract
4. การเชื่อมต่อกับ shared inference module (`SentimentClassifier` จาก P02) โดยโหลด model ครั้งเดียวตอนเริ่ม process
5. ชุดทดสอบอัตโนมัติ (unit & integration tests) ผ่านครบ 55/55 รายการ (100%)
6. `Dockerfile` ที่ใส่ชุด model artifact เข้า image ตอน build ([การตัดสินใน P02-T10](P02-model-pipeline.md#3-การตัดสินที่ยังผูกพัน-p03p04)) และรันเป็น non-root user `appuser`
7. ผลทดสอบเรียก API ใน container จริงและการวัด RAM/latency เบื้องต้นในเครื่อง บันทึกใน [reports/P03-evidence.md](../../reports/P03-evidence.md)

**สิ่งที่ไม่รวมใน P03:**
- การสร้าง Azure resources และการ deploy ขึ้น cloud (อยู่ใน P04)
- CI/CD workflow บน GitHub Actions (อยู่ใน P04)
- Dashboard และ Alerting (อยู่ใน P05)
- การทดลอง failure บน cloud (อยู่ใน P05)

---

## 2. Tasks และการแบ่งงาน

| Task ID | งานที่ทำ | สถานะ | สิ่งที่ตรวจว่างานเสร็จ (Done when) | วิธีตรวจ (Check) |
|---|---|---|---|---|
| **P03-T01** | **กำหนด Dependencies และ Configuration Layer** | `done` | เพิ่ม web framework (`fastapi`, `uvicorn`) ใน `pyproject.toml` และสร้าง `config.py` ที่อ่าน token, path, port จาก environment พร้อม `.env.example` / `cloud.env.example` | `uv sync` สำเร็จ และ unit tests ใน `tests/test_config.py` ผ่านครบ 100% |
| **P03-T02** | **Lifespan และ Model State Management** | `done` | จัดการ lifecycle ของแอป โหลด `SentimentClassifier` ครั้งเดียวตอน startup หากโหลดไม่สำเร็จไม่ crash เพื่อให้ `/health` ยังตอบได้ แต่บันทึกสถานะว่า model ไม่พร้อม | Test จำลองการโหลด model สำเร็จและล้มเหลว ตรวจสอบ state ของแอป ใน `tests/test_api.py` |
| **P03-T03** | **Auth, Endpoints และ Error Handling** | `done` | ทำ endpoint `/health`, `/ready`, `/predict` พร้อม Bearer token check, error payload RFC 9110 (`UNAUTHORIZED`, `INVALID_TEXT`, `BAD_REQUEST`, `MODEL_NOT_READY`, `INTERNAL_ERROR`) | ตรวจ response status, error code และ header `WWW-Authenticate: Bearer` เมื่อไม่มี token |
| **P03-T04** | **Input Token Boundary Validation** | `done` | ตรวจ `text` ว่าไม่ว่างเปล่า และตรวจเพดาน 510 content tokens ด้วย tokenizer ตามที่ล็อกไว้ใน P02-T03 ห้ามใช้ `truncation=True` และปฏิเสธด้วย 422 ทันที | Test ป้อนข้อความว่าง -> 422, ข้อความ 510 tokens -> 200, ข้อความ 511 tokens -> 422 (`TEXT_TOO_LONG`) |
| **P03-T05** | **Checklist Verification Tests** | `done` | เขียน automated tests ใน `tests/test_api.py` ครอบคลุม checklist ทั้ง 11 ข้อใน [P01-T02 §6](P01-T02-api-contract.md#6-checklist-สำหรับตรวจตอน-implement) | รัน `uv run pytest tests/test_api.py` ผ่าน 18/18 รายการ (รวมทั้งระบบ 55/55 รายการ) |
| **P03-T06** | **สร้าง Dockerfile และ Build Image** | `done` | เขียน `Dockerfile` ที่ใช้ `python:3.13-slim`, ติดตั้ง dependencies ด้วย `uv sync --no-default-groups`, copy artifact เข้า image, ตั้ง non-root user `appuser` | รัน `docker build -t feedbackpulse:local .` สำเร็จ Image ID: `16030a4a4dbf` |
| **P03-T07** | **Container Smoke Test และวัด Memory** | `done` | รัน container ในเครื่อง ยิงทดสอบทั้งกรณีปกติ ข้อมูลผิด token ผิด และทดสอบกรณี model fail พร้อมวัด RAM peak/idle | ยิง `curl` ทดสอบ endpoints จริงใน container ผ่านครบทุกกรณี และบันทึก memory usage (645.8 MiB) |
| **P03-T08** | **สรุปหลักฐานและส่งต่องาน** | `done` | เขียนเอกสาร `reports/P03-evidence.md` รวบรวมผลทดสอบและค่าที่วัดได้ พร้อมอัปเดตสถานะใน `overview-plan.md` | เอกสารครบถ้วน ลิงก์ตรง และพร้อมส่งต่อไปยัง P04 |

---

## 3. กติกาและข้อตกลงที่ล็อกไว้ (รักษาไว้ครบถ้วน)

1. **ห้ามนับอักขระแทน token:** เพดานคือ 510 content tokens (รวม special tokens เป็น 512) นับด้วย tokenizer ของ revision ที่ใช้งานจริงเท่านั้น
2. **ห้ามตัดข้อความเงียบ ๆ (`truncation=False`):** ข้อความที่ยาวเกิน 510 tokens คืน `422` พร้อม code `TEXT_TOO_LONG`
3. **การเก็บ Artifact:** ใส่ model artifact เข้าไปใน Docker image ตอน build ตามข้อตกลง P02-T10
4. **ความลับและ Privacy ใน Logs:** ไม่บันทึกค่า `service-token` และไม่บันทึกข้อความ feedback ฉบับเต็มลงใน logs
5. **แยก `/health` กับ `/ready`:** เมื่อแอปทำงานแต่โหลด model ไม่ได้ `/health` ตอบ `200` ส่วน `/ready` และ `/predict` ตอบ `503` โดยไม่คืนผลทำนายปลอม
6. **`model_version`:** อ่านจาก registry / config จริง (`sentiment-6e7ff9fbc17c-0110c462`)

---

## 4. เกณฑ์การผ่านเฟส P03 (Phase Acceptance)

- [x] รัน `uv run pytest` ผ่านครบทุก test (ทั้งชุดเดิมและ API tests ใหม่ รวม 55/55 รายการ)
- [x] Container image build สำเร็จ และรันได้โดยไม่มี error (`feedbackpulse:local`)
- [x] Container ผ่าน smoke test ครบทุกกรณี: 200 (valid), 400 (bad json), 401 (no/bad token), 422 (invalid/too long text), 503 (model not ready)
- [x] มีผลวัด RAM ของ container ขณะ idle และ peak บันทึกไว้เป็นหลักฐานสำหรับ P04 (645.8 MiB ใน container)
