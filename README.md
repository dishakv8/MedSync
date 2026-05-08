# 🏥 Healthcare Memory System — Backend

AI-powered longitudinal healthcare memory system built with FastAPI + PostgreSQL.

## 🚀 Quick Start (Docker — Recommended)

```bash
# 1. Clone / enter project
cd healthcare-backend

# 2. Copy env and add your Gemini API key
cp .env.example .env
# Edit .env → set GEMINI_API_KEY

# 3. Start everything
docker-compose up --build

# API docs available at:
# http://localhost:8000/docs
```

---

## 🛠 Manual Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+

### Steps

```bash
# 1. Create virtualenv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install deps
pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
# Edit .env — set DATABASE_URL and GEMINI_API_KEY

# 4. Run migrations
alembic upgrade head
# OR just start the app (auto-creates tables on first run)

# 5. Seed demo data
python seed.py

# 6. Run server
uvicorn app.main:app --reload
```

---

## 🔐 Demo Credentials

| Role    | Email                    | Password      |
|---------|--------------------------|---------------|
| Doctor  | doctor@demo.com          | Demo@1234     |
| Patient | rahul.mehta@demo.com     | Patient@1234  |
| Patient | priya.sharma@demo.com    | Patient@1234  |

---

## 📡 API Reference

### Auth
| Method | Endpoint              | Description                    |
|--------|-----------------------|--------------------------------|
| POST   | /auth/register        | Register doctor or patient     |
| POST   | /auth/login           | Login → JWT token              |
| POST   | /auth/otp/send        | Send OTP to phone              |
| POST   | /auth/otp/verify      | Verify OTP → JWT token         |

### Patients (Doctor only)
| Method | Endpoint                         | Description                    |
|--------|----------------------------------|--------------------------------|
| POST   | /patients/                       | Register new patient           |
| GET    | /patients/search?q=              | Search by name/phone/ID        |
| GET    | /patients/{patient_id}           | Full patient profile           |
| GET    | /patients/{patient_id}/timeline  | All consultations + history    |
| GET    | /patients/{patient_id}/insights  | Recurring pattern detection    |

### Consultations
| Method | Endpoint                              | Access  | Description                |
|--------|---------------------------------------|---------|----------------------------|
| POST   | /consultations/                       | Doctor  | Create consultation        |
| POST   | /consultations/{id}/upload-audio      | Doctor  | Upload audio file          |
| POST   | /consultations/{id}/transcribe        | Doctor  | Run Whisper transcription  |
| POST   | /consultations/{id}/process           | Doctor  | AI extraction via Gemini   |
| GET    | /consultations/{id}                   | Doctor  | Full SOAP note view        |
| GET    | /consultations/{id}/patient-view      | Both    | Patient-friendly view      |

---

## 🤖 AI Pipeline Flow

```
1. POST /consultations/              → Create consultation record
2. POST /{id}/upload-audio           → Upload .mp3/.wav
3. POST /{id}/transcribe             → Whisper → stored transcript
4. POST /{id}/process                → Gemini extracts:
                                         symptoms, diagnosis, severity,
                                         medications, SOAP note,
                                         doctor_summary, patient_summary
```

> **Whisper not available?** The system falls back to a mock transcript automatically — useful for demos without GPU.

> **Gemini key not set?** The `/process` endpoint will return a 500 with a clear message.

---

## 🔁 Insights — Recurring Pattern Detection

`GET /patients/{patient_id}/insights`

- Default: Fast **rule-based** detection (no AI cost)
- Pass `?use_ai=true` to use **Gemini** for richer narrative insights

**Rule-based detection:**
- Checks last 90 days of consultations
- Groups symptoms into categories: respiratory, GI, fever, pain, skin, neurological, cardiac
- Flags if 2+ visits share the same category

**Response shape:**
```json
[
  {
    "type": "recurring",
    "message": "Recurring respiratory symptoms detected across 3 visit(s) in the last 90 days.",
    "severity": "moderate"
  }
]
```

---

## 🗄️ Database Migrations (Alembic)

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## 📁 Project Structure

```
healthcare-backend/
├── app/
│   ├── api/
│   │   ├── deps.py            # JWT auth dependencies
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── consultations.py
│   │       ├── insights.py
│   │       └── patients.py
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── responses.py       # Consistent JSON wrapper
│   │   └── security.py        # JWT + bcrypt
│   ├── db/
│   │   └── session.py         # SQLAlchemy engine + session
│   ├── models/
│   │   └── models.py          # ORM models
│   ├── schemas/
│   │   └── schemas.py         # Pydantic v2 schemas
│   ├── services/
│   │   ├── gemini_service.py  # Gemini AI integration
│   │   └── whisper_service.py # Whisper transcription
│   └── main.py
├── alembic/
├── uploads/                   # Audio file storage
├── seed.py                    # Demo data seeder
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
