# FeedbackPulse — Cloud Adapter & Infrastructure (`cloudlayer/`)

เอกสารกำกับและคู่มือการจัดการ **Cloud Adapter** และ Infrastructure บน **Azure Container Apps (Consumption plan)** สำหรับโครงการ FeedbackPulse (Phase **P04-T01**).

สอดคล้องตามข้อตกลงใน [docs/plans/P01-T03-system-structure.md §4 และ §6](../docs/plans/P01-T03-system-structure.md):
- **Core (ใน `src/`):** เป็นอิสระจาก Cloud 100% ไม่ import cloud SDK ใด ๆ
- **Configuration (ใน `src/feedbackpulse/config.py`):** อ่านค่าผ่าน environment variables / `.env`
- **Cloud Adapter (ใน `cloudlayer/`):** แยกโค้ดที่ติดต่อและจัดการ Cloud ออกมาเป็น Adapter ชัดเจน

---

## 1. Cloud Adapter Architecture

โครงสร้างใน `cloudlayer/` ใช้ Adapter Pattern:

- **`CloudDeploymentAdapter` (`cloudlayer/adapter.py`):** Protocol interface กำหนด contract สำหรับ deployment, revision inspection, traffic splitting, และ rollback
- **`AzureContainerAppAdapter` (`cloudlayer/azure_adapter.py`):** Concrete implementation ที่ติดต่อ Azure Container Apps ผ่าน Azure CLI
  - `get_service_url()`: ดึง FQDN HTTPS ของ Container App
  - `list_revisions()`: ดึงรายชื่อ revision ทั้งหมดพร้อมสัดส่วน traffic %
  - `get_active_revision()`: คืนค่าชื่อ revision ที่รับ traffic 100%
  - `set_traffic_weights(weights)`: ปรับสัดส่วน traffic ระหว่าง revisions
  - `rollback_to_revision(revision_name)`: ปรับ traffic 100% กลับไปยัง revision เป้าหมายทันที (Zero downtime)
  - `deploy_config(yaml_path)`: สั่ง deploy / update ด้วย configuration YAML

---

## 2. Infrastructure Sizing & Configuration

FeedbackPulse นำส่งโมเดลและ REST API ในคอนเทนเนอร์เดียวบน **Azure Container Apps**:

- **Resource Group:** `itcs355-6688166` (ภูมิภาค `southeastasia`)
- **Container Registry (ACR):** `itcs3556688166.azurecr.io` (SKU Basic)
- **Container Apps Environment:** `itcs355-env` (Consumption plan)
- **Container App:** `feedbackpulse-api`
- **Sizing:** 1.0 vCPU / 2.0 GiB RAM (สอดคล้องกับผลวัดใน container ที่ 645.8 MiB และอยู่ในงบประมาณ USD 15)
- **Scale:** `minReplicas: 0` (scale-to-zero เมื่อ idle), `maxReplicas: 3`
- **Revisions Mode:** `Multiple` (รองรับ zero-downtime rollback)
- **Ingress:** External HTTPS บน Port 8000

---

## 3. Health & Readiness Probes

สอดคล้องตามข้อตกลง [API contract](../docs/plans/P01-T02-api-contract.md) และ [System Structure](../docs/plans/P01-T03-system-structure.md):

| Probe Type | Endpoint | Interval | Initial Delay | Threshold | หน้าที่ |
|---|---|---|---|---|---|
| **Liveness** | `GET /health` | 15s | 10s | 3 | ตรวจสอบว่า web server process (uvicorn) ยังตอบสนอง |
| **Readiness** | `GET /ready` | 10s | 15s | 3 | ตรวจสอบว่าโมเดลโหลดเสร็จสมบูรณ์และพร้อมทำนาย (คืน 200 เมื่อพร้อม, 503 เมื่อไม่พร้อม) |

---

## 4. นโยบายความปลอดภัยของ Secrets (Zero Leaked Credentials)

- **ไม่มีการ bake secret ลงใน Docker image หรือ Git repository**: `SERVICE_TOKEN` และ ACR credentials จะถูกส่งผ่าน runtime environment variables และ Container App Secrets เท่านั้น
- ไฟล์ `cloudlayer/containerapp.template.yaml` ใช้ตัวแปร `${VAR_NAME}` และจะถูก render ผ่าน `cloudlayer/render_config.py` ซึ่งจะลบไฟล์ชั่วคราวทิ้งทันทีเมื่อเสร็จสิ้น

---

## 5. ไฟล์ที่เกี่ยวข้อง

- `cloudlayer/adapter.py`: Protocol interface สำหรับ Cloud Deployment Adapter
- `cloudlayer/azure_adapter.py`: Azure Container Apps Adapter implementation
- `cloudlayer/containerapp.template.yaml`: IaC - Infrastructure as Code file สำหรับ Azure Container Apps ทำหน้าที่เป็น All-in-one Config สำหรับการ deploy และอัพเดท Container App โดยเฉพาะ เพื่อให้มั่นใจว่าสภาพแวดล้อมและการ deploy สามารถทำซ้ำได้ (Reproducible Environment and Deployment)
- `cloudlayer/render_config.py`: สคริปต์ตรวจสอบความถูกต้อง (schema, sizing, probes) และ render template
- `Makefile`: Single entrypoint สำหรับคำสั่ง Docker, Cloud Provisioning, Deploy, Status, และ Rollback
- `tests/test_cloudlayer.py`: Unit tests สำหรับ Adapter, Template structure, และ Constraint validation
- `tests/test_portability.py`: Automated Portability Audit ตรวจสอบว่า core `src/` ไม่ผูกติดกับ cloud SDK หรือ adapter

---

## 6. วิธีการใช้งาน (Makefile Single Entrypoint)

### 6.1 ตรวจสอบความถูกต้องโดยไม่แก้ไข Cloud Resource (Dry Run)
```bash
make dry-run
```

### 6.2  Push image ตัว linux/amd64 ขึ้น ACR
```bash
make docker-push
```

### 6.3 สั่ง Deploy หรือ Update Container App จริง
```bash
make deploy
```

### 6.4 ตรวจสอบสถานะและ Revisions
```bash
make status
```

### Optional: สั่ง Rollback Traffic 100% กลับไปยัง Revision ที่ระบุ
```bash
make rollback REV=<target-revision-name>
```

### Optional: รันชุดทดสอบความถูกต้องของ Cloudlayer & Portability
```bash
uv run pytest tests/test_cloudlayer.py tests/test_portability.py
```
