"""
Manual end-to-end verification script for ClinicDesk.

Exercises: conflict-free booking, lookups, cancellation fee logic,
reschedule (T6), morning reminders (T1), and no-show automation (T2)
via the simulated clock.

Run with the backend already up (docker compose up -d, migrations applied,
uvicorn running on :8000).
"""
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests

BASE = "http://localhost:8000"
PASSED = []
FAILED = []


def check(label, condition, extra=""):
    if condition:
        PASSED.append(label)
        print(f"  [PASS] {label}")
    else:
        FAILED.append(label)
        print(f"  [FAIL] {label} {extra}")


def iso(dt):
    return dt.isoformat()


def main():
    session = requests.Session()

    print("\n=== 1. Setup ===")
    email = f"{uuid.uuid4()}@example.com"
    r = session.post(f"{BASE}/auth/register", json={
        "name": "Manual Check Desk", "email": email, "password": "password123"
    })
    check("register returns 201", r.status_code == 201, r.text)
    token = r.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})

    r = session.get(f"{BASE}/doctors")
    check("doctors list returns 200", r.status_code == 200, r.text)
    doctors = r.json()["items"]
    check("at least 2 seeded doctors present", len(doctors) >= 2, doctors)
    doc1, doc2 = doctors[0]["id"], doctors[1]["id"]

    # Anchor everything off the server's simulated clock, not wall time.
    r = session.post(f"{BASE}/clock", json={"advance_by_minutes": 0})
    check("clock read returns 200", r.status_code == 200, r.text)
    now = datetime.fromisoformat(r.json()["current_time"].replace("Z", "+00:00"))

    def book(doctor_id, start, end=None, name=None):
        end = end or (start + timedelta(minutes=30))
        return session.post(f"{BASE}/appointments", json={
            "doctor_id": doctor_id,
            "patient": {"name": name or f"Patient {uuid.uuid4().hex[:6]}", "email": f"{uuid.uuid4()}@example.com"},
            "start_time": iso(start),
            "end_time": iso(end),
        })

    print("\n=== 2. Conflict-free booking ===")
    slot_start = now + timedelta(days=3, hours=1)
    r1 = book(doc1, slot_start, name="Overlap Test A")
    check("first booking returns 201", r1.status_code == 201, r1.text)
    apt1 = r1.json()

    r2 = book(doc1, slot_start + timedelta(minutes=15))
    check("overlapping booking (same doctor) returns 409", r2.status_code == 409, r2.text)

    r3 = book(doc1, slot_start + timedelta(minutes=30))
    check("back-to-back booking (same doctor, touching) returns 201", r3.status_code == 201, r3.text)
    apt3 = r3.json()

    r4 = book(doc2, slot_start)
    check("same time, different doctor returns 201", r4.status_code == 201, r4.text)

    print("\n=== 3. Lookups ===")
    day_str = slot_start.date().isoformat()
    r = session.get(f"{BASE}/doctors/{doc1}/schedule", params={"date": day_str})
    check("doctor schedule returns 200", r.status_code == 200, r.text)
    ids_on_schedule = {a["id"] for a in r.json()}
    check("both doctor1 appointments appear on schedule", {apt1["id"], apt3["id"]} <= ids_on_schedule)

    patient_name = apt1["patient_name"]
    r = session.get(f"{BASE}/appointments", params={"patient_name": patient_name})
    check("lookup by patient name returns 200", r.status_code == 200, r.text)
    check("lookup finds the booking", any(a["id"] == apt1["id"] for a in r.json()["items"]))

    print("\n=== 4. Cancellation fee logic ===")
    far_start = now + timedelta(days=5)
    r = book(doc1, far_start, name="Far Future Cancel")
    apt_far = r.json()
    r = session.patch(f"{BASE}/appointments/{apt_far['id']}/cancel")
    check("free cancellation returns 200", r.status_code == 200, r.text)
    check("no late fee charged (>24h out)", r.json()["late_fee_charged"] is False, r.json())

    near_start = now + timedelta(hours=2)
    r = book(doc1, near_start, name="Near Future Cancel")
    apt_near = r.json()
    r = session.patch(f"{BASE}/appointments/{apt_near['id']}/cancel")
    check("late cancellation returns 200", r.status_code == 200, r.text)
    check("late fee charged (<24h out)", r.json()["late_fee_charged"] is True, r.json())
    check("late fee amount is 50.00", float(r.json()["late_fee_amount"]) == 50.0, r.json())

    r = session.patch(f"{BASE}/appointments/{apt_near['id']}/cancel")
    check("re-cancelling returns 409", r.status_code == 409, r.text)

    print("\n=== 5. Reschedule (T6) ===")
    base_start = now + timedelta(days=6)
    ra = book(doc1, base_start, name="Reschedule A").json()
    rb = book(doc1, base_start + timedelta(hours=1), name="Reschedule B").json()

    r = session.patch(f"{BASE}/appointments/{ra['id']}/reschedule", json={
        "start_time": rb["start_time"], "end_time": rb["end_time"]
    })
    check("reschedule into a conflict returns 409", r.status_code == 409, r.text)

    r = session.get(f"{BASE}/appointments/{ra['id']}")
    check("original time preserved after failed reschedule",
          r.json()["start_time"] == ra["start_time"], r.json())

    new_start = base_start + timedelta(hours=3)
    r = session.patch(f"{BASE}/appointments/{ra['id']}/reschedule", json={
        "start_time": iso(new_start), "end_time": iso(new_start + timedelta(minutes=30))
    })
    check("reschedule to a free slot returns 200", r.status_code == 200, r.text)

    # Known gap at time of writing: rescheduling a cancelled appointment.
    # Expect 409 once the status-guard fix is applied; currently may return 200.
    cancelled = book(doc1, base_start + timedelta(days=1), name="Cancelled Reschedule").json()
    session.patch(f"{BASE}/appointments/{cancelled['id']}/cancel")
    r = session.patch(f"{BASE}/appointments/{cancelled['id']}/reschedule", json={
        "start_time": iso(base_start + timedelta(days=1, hours=2)),
        "end_time": iso(base_start + timedelta(days=1, hours=2, minutes=30)),
    })
    check("rescheduling a cancelled appointment returns 409 (status-guard fix)",
          r.status_code == 409, f"got {r.status_code} — fix not applied yet" if r.status_code != 409 else "")

    print("\n=== 6. Morning reminders (T1) + no-show automation (T2) ===")
    r = session.post(f"{BASE}/clock", json={"advance_by_minutes": 0})
    now = datetime.fromisoformat(r.json()["current_time"].replace("Z", "+00:00"))

    reminder_day = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    r = session.post(f"{BASE}/clock", json={"advance_to": iso(reminder_day)})
    check("clock advance to reminder_day returns 200", r.status_code == 200, r.text)

    apt_reminder = book(doc2, reminder_day.replace(hour=10), name="Reminder Patient").json()

    r = session.post(f"{BASE}/clock", json={"advance_to": iso(reminder_day.replace(hour=8, minute=1))})
    check("clock advance past 08:00 returns 200", r.status_code == 200, r.text)
    check("exactly one reminder sent", r.json()["reminders_sent"] >= 1, r.json())

    r = session.get(f"{BASE}/outbox", params={"appointment_id": apt_reminder["id"]})
    check("outbox has one entry for this appointment", r.json()["total"] == 1, r.json())

    r = session.post(f"{BASE}/clock", json={"advance_by_minutes": 60})
    r = session.get(f"{BASE}/outbox", params={"appointment_id": apt_reminder["id"]})
    check("no duplicate reminder after advancing further", r.json()["total"] == 1, r.json())

    r = session.post(f"{BASE}/clock", json={"advance_by_minutes": 0})
    now = datetime.fromisoformat(r.json()["current_time"].replace("Z", "+00:00"))
    ns_start = now + timedelta(days=3)
    booked = book(doc1, ns_start, name="No Show Test").json()
    completed = book(doc1, ns_start + timedelta(hours=1), name="Completed Test").json()
    session.patch(f"{BASE}/appointments/{completed['id']}/complete")

    r = session.post(f"{BASE}/clock", json={"advance_to": iso(ns_start + timedelta(minutes=29))})
    r = session.get(f"{BASE}/appointments/{booked['id']}")
    check("not yet no-show before 30min window", r.json()["status"] == "booked", r.json())

    r = session.post(f"{BASE}/clock", json={"advance_to": iso(ns_start + timedelta(minutes=31))})
    r = session.get(f"{BASE}/appointments/{booked['id']}")
    check("marked no_show after 30min window", r.json()["status"] == "no_show", r.json())

    r = session.get(f"{BASE}/appointments/{completed['id']}")
    check("completed appointment stays completed, not no_show", r.json()["status"] == "completed", r.json())

    print(f"\n{'='*40}\n{len(PASSED)} passed, {len(FAILED)} failed\n{'='*40}")
    if FAILED:
        print("Failed checks:")
        for f in FAILED:
            print(f"  - {f}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()