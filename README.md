<div align="center">

<img src="static/img/logo.png" alt="VeloxDonate Logo" width="120"/>

# VeloxDonate

**ระบบรับ Donate แบบ Real-time สำหรับ Streamer ไทย**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Version](https://img.shields.io/badge/Version-Alpha-purple?style=flat-square)]()

</div>

---

## 📖 เกี่ยวกับ VeloxDonate

VeloxDonate คือระบบรับ Donate แบบ Real-time สำหรับ Streamer ชาวไทย ทำงานร่วมกับ **PromptPay** ผ่านการอ่านการแจ้งเตือนจากแอป LINE บน Windows ด้วย OCR ไม่ต้องพึ่งพา API ธนาคารใดๆ

### ✨ ฟีเจอร์หลัก

| ฟีเจอร์ | รายละเอียด |
|---|---|
| 💸 **PromptPay Real-time** | ตรวจจับการโอนเงินผ่าน LINE Notification + OCR อัตโนมัติ |
| 🎨 **OBS Overlay** | Alert สวยงาม พร้อม Animation, เสียงเอฟเฟกต์, TTS |
| 📊 **Widgets** | Top Donator, Recent Donate, Goal Bar แบบ Real-time |
| 🎛️ **Controller Dashboard** | จัดการทุกอย่างผ่าน Web UI |
| 🌐 **Cloudflare Tunnel** | เชื่อมต่อจากภายนอกแบบ Zero-config |
| 🔒 **Secure Token** | Token 22 หลัก (A-Za-z0-9) สุ่มทุกครั้ง |
| 🚀 **Auto-Update** | อัปเดตตัวเองแบบ 1-Click ผ่าน Dashboard |
| 📦 **Portable** | แพ็กเกจ Portable แบบพกพา ดับเบิลคลิกรันได้ทันที ไม่ต้องติดตั้งโปรแกรม |

---

## 🖥️ ความต้องการของระบบ

- **OS:** Windows 10 / 11 (64-bit)
- **LINE PC:** ติดตั้งและ Login เรียบร้อยแล้ว
- **OBS Studio:** สำหรับนำ URL ไปใส่ใน Browser Source

---

## 🚀 วิธีติดตั้งและใช้งาน

> 📺 **วิดีโอสอนการติดตั้งแบบละเอียดบน YouTube — Coming Soon!**

---

## 🔧 Build แพ็กเกจ Portable (สำหรับ Developer)

```bash
python build_portable.py
```

ไฟล์ ZIP จะถูกสร้างไว้ที่ `dist_portable/VeloxDonate_v0.1.1_Portable.zip` (มี Python Embedded ภายในตัว ไม่โดน Windows SmartScreen บล็อก)

---

## 🗂️ โครงสร้างโปรเจกต์

```
veloxdonate/
├── app.py                  # Flask server หลัก
├── db.py                   # SQLite database layer
├── tunnel.py               # Cloudflare Tunnel manager
├── interceptor.py          # LINE OCR interceptor
├── ocr_engine.py           # OCR engine
├── controller.html         # Controller Dashboard UI
├── index.html              # Donate page
├── overlay.html            # OBS Alert Overlay
├── widget_*.html           # OBS Widgets
├── static/                 # CSS, JS, รูปภาพ, เสียง
├── config.example.json     # ตัวอย่าง config
├── requirements.txt        # Python dependencies
└── build_portable.py       # Build script สำหรับแพ็กเกจ Portable
```

---

## 🔒 ความปลอดภัย

- Token ทุกตัวสุ่มด้วย `secrets.token_urlsafe` — ไม่ซ้ำกันระหว่าง Streamer
- `config.json` อยู่ใน `.gitignore` — Token จริงไม่หลุด GitHub
- Admin Token และ Widget Token แยกกัน
- Cloudflare Tunnel เข้ารหัส TLS อัตโนมัติ

---

<div align="center">
Made with ❤️ by <a href="https://veloxgg.com">VeloxGG Team</a>
</div>
