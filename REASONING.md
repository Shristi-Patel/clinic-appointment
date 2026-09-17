# ClinicDesk Engineering Reasoning

## Scope

ClinicDesk is a FastAPI, PostgreSQL, and React/Vite clinic scheduling system. The implementation prioritizes database-enforced scheduling safety, deterministic time-driven behavior, and front-desk workflows that remain understandable under errors.

## Key Decisions

### Appointment overlap protection

Overlapping active appointments are prevented by PostgreSQL's GiST exclusion constraint using the doctor id and a half-open time range. This remains the source of truth for both normal booking and concurrent booking attempts. API handlers catch the exclusion violation and return `409 Conflict`.

Cancelled and no-show appointments are excluded from the constraint so they no longer reserve the doctor's slot. The constraint was kept database-side rather than replaced with a UI or application-only check.

### Simulated clock

Scheduled behavior uses a database-backed single-row clock. `get_now(db)` is used by appointment validation and late-cancellation logic, while `POST /clock` advances the time and synchronously runs reminders and no-show processing.

Investigation found that the clock could remain advanced after a manual or test run. That made real future appointments look like past appointments. `GET /clock` now exposes the current value and `POST /clock` accepts `{ "reset": true }` to restore real UTC time. This preserves deterministic test scenarios while providing an explicit recovery path for normal operation.

The frontend converts `datetime-local` values with the browser's local timezone before sending ISO timestamps. Backend validation normalizes naive values to UTC and compares aware timestamps against one simulated `now` value.

### Notifications and scheduled jobs

Reminder delivery uses an outbox table and an idempotent appointment/date uniqueness key. The scheduler runs synchronously during clock advancement, so tests can immediately inspect notifications and status changes. Booked appointments become no-shows after the configured grace period; completed and cancelled appointments are not changed.

### Appointment mutations

Rescheduling is restricted to booked appointments, validates the new range, records the old range in `appointment_history`, and then relies on the same exclusion-constraint conflict path as booking. The history insert and time change share the transaction, so a conflict rolls both back.

Booking supports an `Idempotency-Key` header. The key and appointment are stored atomically, with a TTL and a PostgreSQL advisory transaction lock to serialize concurrent retries.

### Patient and doctor management

Patients can be edited by authenticated staff. Patient deletion is blocked with `409 Conflict` when appointments or merge references exist, preventing orphaned appointment records. Doctor creation and editing remain admin-only through the existing role guard.

## Frontend Structure

The React client uses real routes for landing, authentication, dashboard, booking, doctor schedule, and patient search. Shared API helpers inject JWT headers and redirect on `401`. Patient suggestions populate name, phone, and `patient_id`; selecting one causes booking to reuse the existing patient rather than create a duplicate.

List endpoints return pagination envelopes with `items`, `page`, `size`, `total`, and `pages`. Appointment sorting is server-side and uses an explicit whitelist.

## Testing and Verification

The backend integration suite covers:

- Overlapping bookings returning `409`.
- Concurrent booking attempts allowing exactly one success.
- On-time and late cancellation fees.
- Reschedule conflicts preserving the original appointment time.
- Cancelled appointments being rejected by reschedule.
- Morning reminder delivery and duplicate suppression.
- No-show transitions and preservation of completed status.
- Clock reset followed by a valid future booking.
- Future local-time timestamps with timezone offsets.
- Missing-token `401` and non-admin `403` behavior.
- Pagination beyond the final page.
- Patient update persistence and safe deletion behavior.

Verification commands used:

```bash
cd backend
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. pytest -q -m integration

cd ../frontend
npm run build
```

The final integration run passed all 15 tests, and the production frontend build completed successfully. Live smoke checks also verified `GET /clock`, clock reset, and a future appointment booking returning `201`.

## Operational Note

The PostgreSQL container and Vite/FastAPI development servers are separate processes. When backend routes change, the Uvicorn process must be restarted if it was launched without reload; a stale process previously caused the frontend to receive `404` responses for newly added patient CRUD routes.
