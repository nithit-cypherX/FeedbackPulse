# FeedbackPulse — Overview Plan

อัปเดตสถานะ: 2026-10-08 · P01: `in_progress` · **P02: `done`** · **P03: `done`** · P04–P06: `planned`

ผมเสนอแบ่ง **FeedbackPulse เป็น 6 ส่วนหลัก** ครับ โดยใช้ skill `plan-and-track-work`: วางภาพรวมให้ครบก่อน แล้วค่อยแตกงานย่อยเฉพาะส่วนที่กำลังทำ เพื่อไม่ให้รายการงานเยอะเกินไป

ตอนนี้ repo ในเครื่องมี proposal, README และ `.gitignore` แล้ว แต่ยังไม่มีโค้ดระบบ ดังนั้นแผนด้านล่างคือ **งานที่เสนอจะทำ ไม่ใช่งานที่เสร็จแล้ว**

## ภาพรวม 6 ส่วน

อิงจาก [เกณฑ์ capstone ของอาจารย์](https://github.com/pasdptt/public_teaching_mlaiops/blob/2e29fae/course/project/project-brief.md) และขอบเขต FeedbackPulse ที่เราตกลงกัน:

| ส่วน | เราจะทำอะไร | ถือว่าจบเมื่อ |
|---|---|---|
| **P01 — ตกลงแบบระบบและแบ่งหน้าที่** | กำหนด API ว่ารับอะไร ส่งอะไรกลับ และจัดโครงสร้างตามกติกาแยก core, configuration และ cloud adapter พร้อมแบ่งเจ้าของงาน | ทีมเข้าใจตรงกัน มีแบบระบบสำหรับ architecture review และยืนยันสถานะอนุมัติ proposal ก่อนเริ่มพัฒนา |
| **P02 — เตรียม model และ pipeline ที่ทำซ้ำได้** | ใช้ pretrained model เวอร์ชันตายตัว จัดข้อมูล evaluation ให้มี version แล้วทำขั้นตอน evaluate → package → register พร้อม lineage | รัน workflow ซ้ำได้ และย้อนจาก model ที่ลงทะเบียนไปหา code, data, model revision และผล evaluation ได้ — ตอบ **R1** |
| [**P03 — ทำ backend ให้ใช้งานได้ในเครื่อง**](docs/plans/P03-local-backend.md) | รับข้อความภาษาอังกฤษ คืน sentiment, score และ model version มี validation, access control, health/readiness checks และ Docker | เรียก API ใน container ได้จริง พร้อม tests สำหรับข้อมูลปกติ ข้อมูลผิด และ model ไม่พร้อม — เป็นฐานของ **R2** |
| **P04 — Deploy และปล่อยเวอร์ชันอย่างปลอดภัย** | ทำ CI/CD ทดสอบก่อน deploy ไป Azure Container Apps วัด latency และลอง rollback พร้อมจัดการ credentials, tags และงบตั้งแต่เริ่มใช้ cloud | การเปลี่ยนแปลงที่ผิดถูก tests บล็อก เวอร์ชันที่ผ่าน deploy ได้ และ rollback กลับเวอร์ชันเดิมได้จริง — ตอบ **R2** |
| **P05 — เฝ้าระวังและทดลองเหตุขัดข้อง** | ทำ dashboard และ alert แล้วจำลอง model artifact ใช้งานไม่ได้ตาม proposal ตรวจการแจ้งเตือน กู้ระบบ และเพิ่ม regression test | แสดงหลักฐานได้ครบว่า “เกิดอะไร → รู้ได้อย่างไร → กู้อย่างไร → ตรวจไม่ให้ปัญหาเดิมหลุดอีกอย่างไร” — ตอบ **R3–R4** |
| **P06 — ตรวจงานส่งและเตรียม demo** | รวบรวม README ที่ทำตามได้, model card หนึ่งหน้า, ต้นทุนต่อ 1,000 predictions, teardown และซ้อมนำเสนอ | เพื่อนทำตามจาก fresh clone ได้ หลักฐานครบ และทีมสาธิตระบบกับ failure พร้อมตอบคำถามได้ — ตอบ **R5 และ demo 15 คะแนน** |

**เราจะทดสอบและเก็บ evidence ไปพร้อมแต่ละส่วน** ส่วน P06 เป็นการตรวจความครบและจัดงานส่ง ไม่ใช่เพิ่งเริ่มเขียนหลักฐานหรือทดสอบทั้งหมดตอนท้ายครับ

## ฝั่ง ML กับฝั่ง Dev แบ่งอย่างไร

สำหรับทีม 3 คน ผมเสนอแบ่งความรับผิดชอบหลักตาม proposal เดิม:

- **คนที่ 1 — Model และ evaluation:** ดูแล P02 และส่วนเชื่อม model เข้า API
- **คนที่ 2 — Backend และ deployment:** ดูแล P03–P04
- **คนที่ 3 — Monitoring และ reliability:** ดูแล P05 รวมการรวบรวมต้นทุนและเอกสาร
- **ทุกคนร่วมกัน:** ตกลงแบบระบบใน P01 และเตรียม demo ใน P06

ยังไม่ผูกกับชื่อสมาชิกจนกว่าคุณจะแบ่งกันครับ และไม่ต้องรอคนแรกทำทุกอย่างเสร็จคนถัดไปถึงเริ่มได้ เช่น เมื่อตกลงรูปแบบ input/output แล้ว ฝั่ง API สามารถเริ่มทำส่วนรับส่งข้อมูลระหว่างที่อีกคนเตรียม model ได้

## สิ่งที่เราจะไม่เพิ่มเข้าไป

ยังคงขอบเขตเดิม: **backend เดียว, pretrained model เดียว, sentiment 3 กลุ่ม** ไม่มี frontend, CRM integration, chatbot หรือการ train/fine-tune เพิ่ม

แต่การไม่ train เอง **ไม่ได้แปลว่าข้ามงาน MLOps ฝั่ง model** เรายังต้อง version, evaluate, track และ register ให้ตรวจย้อนกลับได้ แผน P02 เป็นการปรับตามคำชี้แจงอาจารย์ที่คุณเล่ามา ไม่ใช่อ้างว่าเราทำซ้ำการฝึก model ต้นฉบับได้ เอกสารกลางยังใช้คำว่า *automated training* แต่ผู้ใช้แจ้งเมื่อ 2026-10-05 ว่าอาจารย์ยืนยัน proposal และขอบเขต pretrained ที่เราตกลงกันแล้ว

## งานปัจจุบัน: P01

แตกเป็นแค่ 3 งานย่อยก่อน:

1. **P01-T01 — ยืนยันขอบเขตและสถานะ proposal**

   ยืนยันขอบเขตและสถานะ proposal แล้ว ตามที่ผู้ใช้แจ้งเมื่อ 2026-10-05 ว่าอาจารย์ยืนยันแล้ว ส่วนรายชื่อเจ้าของงานยังไม่ได้บันทึกในเอกสาร ให้ทีมเป็นผู้ระบุ

2. **P01-T02 — ตกลงรูปแบบ API**

   ข้อตกลงหลักได้รับความเห็นชอบแล้ว ดู [API contract](docs/plans/P01-T02-api-contract.md) สำหรับ request/response, validation และ error handling · **สถานะเป็น `done` เฉพาะการตกลงแล้วเมื่อ 2026-10-07** เพราะเพดานความยาวข้อความยืนยันแล้วใน P02-T03 คือ 510 content tokens (รวม special tokens เป็น 512); ยังไม่ได้ implement หรือทดสอบ — การตรวจ boundary ผ่าน API อยู่ใน P03

3. **P01-T03 — วางโครงสร้างระบบและจุดตรวจ**

   สถานะ `done` เฉพาะการตกลงแผน — ยืนยันครบทั้ง 3 เรื่องแล้ว: หน้าที่ของระบบ โครงสร้างโฟลเดอร์กับกติกาเข้า Git และจุดตรวจพร้อมหลักฐาน R1–R5 ดู [System structure](docs/plans/P01-T03-system-structure.md) เพื่อใช้เป็นฐานสำหรับ architecture review; ยังไม่ได้ implement หรือทดสอบ

**การส่งต่องาน:** P01 บันทึกข้อตกลงไว้ครบแล้ว · **เพดานความยาวข้อความปิดแล้วใน P02-T03** จึงเหลือเพียง **รายชื่อเจ้าของงานใน [Proposal §7](PROPOSAL.md) ที่ยังเป็น `[Name]`** ที่ทำให้ยังไม่ปิด P01 ทั้งส่วน

## P02 เสร็จแล้ว 

ดู [P02 phase plan](docs/plans/P02-model-pipeline.md) · เจ้าของงาน: คนที่ 1

- `model_version` ที่ใช้งาน: `sentiment-6e7ff9fbc17c-0110c462` พร้อม lineage ใน `reports/registry/` · run ID `run-20261007T192531Z-d36357`
- ผล evaluation บน 14,640 แถว: **accuracy 0.8100 · macro-F1 0.7606** ([หลักฐาน ส่วนที่ 2](reports/P02-evidence.md))

**การส่งต่องาน:**
- **คนที่ 2 เริ่ม P03 ได้แล้ว** — อ่าน [interface ที่ล็อกไว้ (ส่วนที่ 9)](reports/P02-evidence.md) และ [การตัดสินที่เก็บ artifact (ส่วนที่ 7)](reports/P02-evidence.md) · เพดานข้อความอยู่ใน [P01-T02 §7](docs/plans/P01-T02-api-contract.md)
- **คนที่ 3 ต้องอ่าน** [หลักฐาน ส่วนที่ 7](reports/P02-evidence.md) — การสาธิต failure เปลี่ยนวิธี เพราะ artifact อยู่ใน image ไม่มี blob ให้ลบ

## P03 เสร็จแล้ว — ทำ backend ให้ใช้งานได้ในเครื่อง

ดู [P03 phase plan](docs/plans/P03-local-backend.md) · [หลักฐานการทดสอบและวัดค่า](reports/P03-evidence.md) · เจ้าของงาน: คนที่ 2
- สถานะ: `done` (ครบทั้ง 8 tasks T01–T08)
- Automated tests: **55/55 รายการผ่านครบ 100%** ใน ~7.68 วินาที
- Container image: `feedbackpulse:local` (digest `16030a4a4dbf`) รันเป็น non-root พร้อมโมเดลในตัว
- Smoke test: เรียก API ใน container จริงผ่านครบทุกเงื่อนไข (ปกติ, 401, 400, 422, token limit 510 tokens)
- Memory usage ใน container: **645.8 MiB** (ใช้ตัดสิน sizing ใน P04)
- Simulated failure: ตรวจสอบความพร้อม `/health` (200) แยกจาก `/ready` (503) สำเร็จ

## งานถัดไป: P04 — Deploy และปล่อยเวอร์ชันอย่างปลอดภัย

เจ้าของงาน: คนที่ 2 (Backend และ deployment)
- เป้าหมาย: สร้าง infrastructure บน Azure Container Apps, ตั้งค่า CI/CD บน GitHub Actions, วัด end-to-end latency และทดสอบ rollback
- ข้อมูลป้อนเข้าจาก P03: Image build สำเร็จ, ขนาด memory ~646 MiB, configuration template ใน `cloud.env.example`

