"""Integration tests. Run after `alembic upgrade head` against PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def auth_headers():
    email = f'{uuid4()}@example.com'
    response = client.post('/auth/register', json={'name': 'Test Desk', 'email': email, 'password': 'password123'})
    assert response.status_code == 201
    return {'Authorization': f"Bearer {response.json()['access_token']}"}

def booking_payload(start, end, doctor_id=1):
    return {'doctor_id': doctor_id, 'patient': {'name': 'Alia'}, 'start_time': start.isoformat(), 'end_time': end.isoformat()}

def unique_start(days=3):
    return datetime.now(timezone.utc) + timedelta(days=days, minutes=uuid4().int % 100000)

@pytest.mark.integration
def test_overlapping_booking_is_rejected():
    headers = auth_headers(); start = unique_start()
    first = client.post('/appointments', json=booking_payload(start, start + timedelta(minutes=30)), headers=headers)
    second = client.post('/appointments', json=booking_payload(start + timedelta(minutes=10), start + timedelta(minutes=40)), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 409

@pytest.mark.integration
def test_concurrent_bookings_only_allow_one_success():
    start = unique_start(4); payload = booking_payload(start, start + timedelta(minutes=30))
    def book(): return client.post('/appointments', json=payload, headers=auth_headers()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: book(), range(2)))
    assert sorted(results) == [201, 409]

@pytest.mark.integration
def test_cancellation_fee_changes_at_configured_cutoff():
    headers = auth_headers(); on_time = unique_start(5)
    early = client.post('/appointments', json=booking_payload(on_time, on_time + timedelta(minutes=30), doctor_id=2), headers=headers).json()
    early_result = client.patch(f"/appointments/{early['id']}/cancel", headers=headers)
    assert early_result.status_code == 200 and early_result.json()['late_fee_charged'] is False

    late = datetime.now(timezone.utc) + timedelta(hours=2)
    late_item = client.post('/appointments', json=booking_payload(late, late + timedelta(minutes=30), doctor_id=2), headers=headers).json()
    late_result = client.patch(f"/appointments/{late_item['id']}/cancel", headers=headers)
    assert late_result.status_code == 200
    assert late_result.json()['late_fee_charged'] is True
    assert late_result.json()['late_fee_amount'] > 0
