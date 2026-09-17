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
PYTHONPATH=. python scripts/seed.py
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API docs are at `http://localhost:8000/docs`.

Run `backend/scripts/seed.py` explicitly to add the demo doctors: Maya Chen (Family Medicine), Elias Romero (Cardiology), and Priya Shah (Pediatrics). Configure `DATABASE_URL`, `SECRET_KEY`, `LATE_CANCELLATION_HOURS`, `LATE_CANCELLATION_FEE`, `FIRST_ADMIN_EMAIL`, and `CORS_ORIGINS` in `backend/.env`.

## API

All routes except registration, login, and health require `Authorization: Bearer <JWT>`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a staff account. JSON: `name`, `email`, `password`. |
| POST | `/auth/login` | Return a JWT. JSON: `email`, `password`. |
| GET | `/health` | Basic service health check. |
| GET | `/doctors` | Paginated envelope `{items, page, size, total, pages}` of active doctors. Supports `page`, `size`, and whitelisted `sort=name`, `-name`, `id`, or `-id`. |
| POST | `/doctors` | Create a doctor; admin role required. |
| PATCH | `/doctors/{id}/deactivate` | Deactivate a doctor; admin role required. |
| GET | `/doctors/{id}/schedule?date=YYYY-MM-DD` | List one doctor's appointments for a day. |
| POST | `/appointments` | Book an appointment; accepts an existing `patient_id` or inline `patient` details. Rejects past times, invalid ranges, and overlaps. |
| GET | `/appointments` | Paginated envelope `{items, page, size, total, pages}`. Supports `patient_name`, `patient_id`, `doctor_id`, `date_from`, `date_to`, `status`, `page`, `size`, and whitelisted `sort=start_time`, `-start_time`, `doctor_name`, `-doctor_name`, `patient_name`, `-patient_name`, `status`, or `-status`. |
| GET | `/appointments/{id}` | Get appointment detail. |
| PATCH | `/appointments/{id}/cancel` | Cancel an appointment and return `late_fee_charged` plus `late_fee_amount`. |
| PATCH | `/appointments/{id}/reschedule` | Move only the appointment time after rechecking simulated time and overlap rules. |
| PATCH | `/appointments/{id}/complete` | Mark a booked appointment completed; other statuses return 409. |
| GET | `/patients?search=name` | Paginated patient envelope `{items, page, size, total, pages}` with `page` and `size`. |
| POST | `/clock` | Move the simulated clock with `advance_to` or `advance_by_minutes`; synchronously runs reminders and no-show jobs and returns their counts. |
| GET | `/outbox` | Inspect paginated notifications sorted newest-first; optionally filter by `appointment_id`. |

## Business Rules

- Appointment intervals use a half-open range: an appointment ending at 10:00 does not conflict with one starting at 10:00.
- `end_time` must be after `start_time`, and `start_time` cannot be in the past.
- Cancelled appointments are excluded from the overlap constraint and can free a slot.
- A cancellation is late when it is less than `LATE_CANCELLATION_HOURS` before its start. Late cancellations set `late_fee_charged=true` and use `LATE_CANCELLATION_FEE`; earlier cancellations are free.
- The cancellation calculation is performed server-side at cancellation time, not in the browser.
- Appointment statuses are `booked`, `cancelled`, `completed`, and `no_show`. No-shows free their doctor's slot for later bookings.
- `MORNING_REMINDER_HOUR` controls the daily reminder hour in `CLINIC_TIMEZONE`; `NO_SHOW_WINDOW_MINUTES` controls the start-time grace period.
- The simulated clock starts at real current time until first overridden, only moves forward, and runs all due scheduled jobs synchronously when advanced.

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

Clock and scheduling coverage in `tests/test_clock_features.py` proves reschedule conflicts preserve the original appointment, reminders are idempotent, and completed appointments are not marked no-show.

## Product Direction

ClinicDesk is designed for clinics and front-desk staff who need a fast, dependable schedule during a busy day. It makes the two costly failure modes visible and consistent: double bookings are blocked at the database boundary, and late-cancellation fees are applied from a configurable policy.

Coming next: SMS reminders, multi-location support, and waitlist auto-fill when cancellations open a slot.