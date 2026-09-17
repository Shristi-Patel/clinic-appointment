"""Integration coverage for simulated time, scheduled jobs, and rescheduling."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from app.clock import get_now
from app.db import SessionLocal
from app.main import app

client = TestClient(app)


def auth_headers():
    response = client.post('/auth/register', json={'name': 'Clock Desk', 'email': f'{uuid4()}@example.com', 'password': 'password123'})
    assert response.status_code == 201
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def clock_now():
    with SessionLocal() as db:
        return get_now(db)


def book(headers, doctor_id, start, name=None):
    response = client.post('/appointments', headers=headers, json={
        'doctor_id': doctor_id,
        'patient': {'name': name or 'Riya', 'email': f'{uuid4()}@example.com'},
        'start_time': start.isoformat(),
        'end_time': (start + timedelta(minutes=30)).isoformat(),
    })
    assert response.status_code == 201, response.text
    return response.json()

@pytest.mark.integration
def test_reschedule_conflict_preserves_original_time():
    headers = auth_headers(); start = clock_now() + timedelta(days=3, minutes=uuid4().int % 10000)
    first = book(headers, 1, start); second = book(headers, 1, start + timedelta(hours=1))
    response = client.patch(f"/appointments/{first['id']}/reschedule", headers=headers, json={'start_time': second['start_time'], 'end_time': second['end_time']})
    assert response.status_code == 409
    unchanged = client.get(f"/appointments/{first['id']}", headers=headers).json()
    assert unchanged['start_time'] == first['start_time']
    assert unchanged['end_time'] == first['end_time']

@pytest.mark.integration
def test_cancelled_appointment_cannot_be_rescheduled():
    headers = auth_headers(); start = clock_now() + timedelta(days=4 + uuid4().int % 10000, minutes=uuid4().int % 10000)
    appointment = book(headers, 1, start, 'Ira')
    original_start = appointment['start_time']; original_end = appointment['end_time']
    assert client.patch(f"/appointments/{appointment['id']}/cancel", headers=headers).status_code == 200
    response = client.patch(f"/appointments/{appointment['id']}/reschedule", headers=headers, json={'start_time': (start + timedelta(hours=2)).isoformat(), 'end_time': (start + timedelta(hours=2, minutes=30)).isoformat()})
    assert response.status_code == 409
    unchanged = client.get(f"/appointments/{appointment['id']}", headers=headers).json()
    assert unchanged['start_time'] == original_start
    assert unchanged['end_time'] == original_end

@pytest.mark.integration
def test_clock_sends_one_morning_reminder():
    headers = auth_headers(); now = clock_now(); day = (now + timedelta(days=2 + uuid4().int % 1000)).replace(hour=7, minute=0, second=0, microsecond=0)
    client.post('/clock', headers=headers, json={'advance_to': day.isoformat()})
    appointment = book(headers, 2, day.replace(hour=10), 'Riya')
    response = client.post('/clock', headers=headers, json={'advance_to': day.replace(hour=8, minute=1).isoformat()})
    assert response.status_code == 200 and response.json()['reminders_sent'] >= 1
    outbox = client.get(f"/outbox?appointment_id={appointment['id']}", headers=headers).json()
    assert outbox['total'] == 1
    client.post('/clock', headers=headers, json={'advance_by_minutes': 60})
    assert client.get(f"/outbox?appointment_id={appointment['id']}", headers=headers).json()['total'] == 1

@pytest.mark.integration
def test_clock_marks_booked_no_show_but_not_completed():
    headers = auth_headers(); now = clock_now(); start = now + timedelta(days=3, minutes=uuid4().int % 10000)
    booked = book(headers, 3, start, 'Hiya')
    completed = book(headers, 3, start + timedelta(hours=1), 'Adi')
    complete_response = client.patch(f"/appointments/{completed['id']}/complete", headers=headers)
    assert complete_response.status_code == 200
    response = client.post('/clock', headers=headers, json={'advance_to': (start + timedelta(minutes=29)).isoformat()})
    assert response.status_code == 200
    assert client.get(f"/appointments/{booked['id']}", headers=headers).json()['status'] == 'booked'
    response = client.post('/clock', headers=headers, json={'advance_to': (start + timedelta(minutes=31)).isoformat()})
    assert response.status_code == 200
    assert client.get(f"/appointments/{booked['id']}", headers=headers).json()['status'] == 'no_show'
    assert client.get(f"/appointments/{completed['id']}", headers=headers).json()['status'] == 'completed'

@pytest.mark.integration
def test_future_booking_after_clock_reset_ignores_previous_advance():
    headers = auth_headers(); now = clock_now()
    assert client.post('/clock', headers=headers, json={'advance_to': (now + timedelta(days=30)).isoformat()}).status_code == 200
    reset = client.post('/clock', headers=headers, json={'reset': True})
    assert reset.status_code == 200
    start = datetime.now(timezone.utc) + timedelta(days=3)
    appointment = book(headers, 1, start, 'Myra')
    assert appointment['status'] == 'booked'

@pytest.mark.integration
def test_future_local_datetime_with_timezone_offset_is_accepted():
    headers = auth_headers()
    assert client.post('/clock', headers=headers, json={'reset': True}).status_code == 200
    local_start = (datetime.now(ZoneInfo('America/New_York')) + timedelta(days=3)).replace(hour=16, minute=57, second=0, microsecond=0)
    response = client.post('/appointments', headers=headers, json={
        'doctor_id': 2,
        'patient': {'name': 'Vihaan'},
        'start_time': local_start.isoformat(),
        'end_time': (local_start + timedelta(minutes=30)).isoformat(),
    })
    assert response.status_code == 201, response.text
