# ClinicDesk

ClinicDesk is a full-stack front-desk scheduling system for busy clinics. It combines a FastAPI API, PostgreSQL persistence, Alembic migrations, and a React/Vite staff workspace.

The scheduling guarantee lives in PostgreSQL: active appointments have a partial GiST exclusion constraint on `(doctor_id, tstzrange(start_time, end_time, '[)'))`. Two overlapping inserts cannot both commit, including concurrent requests. The API translates the constraint violation into `409 Conflict`.

## Run Locally

Requirements: Docker, Python 3.11+, and Node.js 18+.

```bash
docker compose up -d
cd backend
cp .env.example .env
python -m pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API docs are at `http://localhost:8000/docs`.

The first migration seeds three doctors: Maya Chen (Family Medicine), Elias Romero (Cardiology), and Priya Shah (Pediatrics). Configure `DATABASE_URL`, `SECRET_KEY`, `LATE_CANCELLATION_HOURS`, `LATE_CANCELLATION_FEE`, and `CORS_ORIGINS` in `backend/.env`.

## API

All routes except registration, login, and health require `Authorization: Bearer <JWT>`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a staff account. JSON: `name`, `email`, `password`. |
| POST | `/auth/login` | Return a JWT. JSON: `email`, `password`. |
| GET | `/health` | Basic service health check. |
| GET | `/doctors` | List active doctors. Supports `page`, `size`, and `sort=name`. |
| GET | `/doctors/{id}/schedule?date=YYYY-MM-DD` | List one doctor's appointments for a day. |
| POST | `/appointments` | Book an appointment; accepts an existing `patient_id` or inline `patient` details. Rejects past times, invalid ranges, and overlaps. |
| GET | `/appointments` | Search and page appointments. Supports `patient_name`, `doctor_id`, `date_from`, `date_to`, `status`, `page`, `size`, and `sort=start_time` or `sort=-start_time`. |
| GET | `/appointments/{id}` | Get appointment detail. |
| PATCH | `/appointments/{id}/cancel` | Cancel an appointment and return `late_fee_charged` plus `late_fee_amount`. |
| PATCH | `/appointments/{id}/reschedule` | Move an appointment after rechecking time and overlap rules. |
| GET | `/patients?search=name` | Find patients by name with `page` and `size`. |

## Business Rules

- Appointment intervals use a half-open range: an appointment ending at 10:00 does not conflict with one starting at 10:00.
- `end_time` must be after `start_time`, and `start_time` cannot be in the past.
- Cancelled appointments are excluded from the overlap constraint and can free a slot.
- A cancellation is late when it is less than `LATE_CANCELLATION_HOURS` before its start. Late cancellations set `late_fee_charged=true` and use `LATE_CANCELLATION_FEE`; earlier cancellations are free.
- The cancellation calculation is performed server-side at cancellation time, not in the browser.

## Schema

```text
users (id, name, email, hashed_password, role, created_at)
doctors (id, name, specialty, active)
patients (id, name, phone, email, created_at)
appointments (
	id, doctor_id -> doctors.id, patient_id -> patients.id,
	start_time, end_time, status, created_by_user_id -> users.id,
	created_at, cancelled_at, late_fee_charged, late_fee_amount
)
```

Indexes support email, doctor/patient names, appointment start time, status, and foreign keys. The migration enables PostgreSQL's `btree_gist` extension for the exclusion constraint.

## Tests

With PostgreSQL running and the migration applied:

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_business_rules.py -m integration
```

The integration suite proves overlapping bookings are rejected, concurrent booking attempts cannot both succeed, and on-time versus late cancellation fee logic is applied.

## Product Direction

ClinicDesk is designed for clinics and front-desk staff who need a fast, dependable schedule during a busy day. It makes the two costly failure modes visible and consistent: double bookings are blocked at the database boundary, and late-cancellation fees are applied from a configurable policy.

Coming next: SMS reminders, multi-location support, and waitlist auto-fill when cancellations open a slot.