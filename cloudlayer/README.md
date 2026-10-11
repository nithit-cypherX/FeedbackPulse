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

- **ปลายทาง:** ตั้ง Resource Group, ACR, Container Apps Environment และ App ผ่านค่าที่ระบุเองตาม [cloud.env.example](../cloud.env.example) ไม่มี fallback ไป resource ของ deployment เดิม การเตรียมปลายทาง Azure ของผู้ใช้ยังไม่เสร็จ ดู [สถานะ P04](../docs/plans/P04-deployment-and-cicd.md)
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

- **ไม่มีการ bake secret ลงใน Docker image หรือ Git repository**: `SERVICE_TOKEN` ต้องตั้งเอง ไม่ใช้ค่าตัวอย่างเดิม; CD รับผ่าน production Environment secret แล้วส่งให้ Container App Secret
- การดึง image ใช้ user-assigned managed identity ที่กำหนดด้วย `AZURE_REGISTRY_IDENTITY_ID` (resource ID ไม่ใช่ client ID) ต้องเตรียม identity และสิทธิ์ `AcrPull` ก่อน ไม่ใช้ ACR username/password และไม่ต้องเปิด admin account ดู [Microsoft Learn](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull)
- CD ใช้ repository variables `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP_ENV`, `AZURE_CONTAINER_APP_NAME`, `AZURE_REGISTRY_NAME`, `AZURE_REGISTRY_SERVER`, `AZURE_REGISTRY_IDENTITY_ID`; login ใช้ production secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` ค่าจำเป็นไม่ครบจะหยุดก่อนขั้นอื่น สวิตช์ `FEEDBACKPULSE_CD_ENABLED` ยังต้องเปิดแยกภายหลัง ไม่ได้เปิดจากการแก้ไฟล์
- `cloudlayer/render_config.py` render template และตรวจโครงสร้างเท่านั้น ไม่สร้าง identity หรือ role; `make deploy` และ CD เป็นผู้ลบ YAML ชั่วคราวที่มี token หลังใช้งาน การตรวจ `--validate-only` ใช้ค่าจำลอง ไม่ยืนยันสิทธิ์หรือ deployment บน Azure

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

### Optional: รันชุดทดสอบความถูกต้องของ Cloudlayer & Portability
```bash
uv run pytest tests/test_cloudlayer.py tests/test_portability.py
```
