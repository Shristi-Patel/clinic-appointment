"""Integration coverage for auth guards, pagination, and patient CRUD."""
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.clock import get_now
from app.db import SessionLocal
from app.models import Patient

client = TestClient(app)


def staff_headers():
    response = client.post('/auth/register', json={
        'name': 'Pagination Desk',
        'email': f'{uuid4()}@example.com',
        'password': 'password123',
    })
    assert response.status_code == 201
    return {'Authorization': f"Bearer {response.json()['access_token']}"}

@pytest.mark.integration
def test_missing_token_returns_401():
    response = client.get('/appointments')
    assert response.status_code == 401

@pytest.mark.integration
def test_staff_cannot_manage_doctors():
    response = client.post('/doctors', headers=staff_headers(), json={'name': 'Unauthorized Doctor', 'specialty': 'General Medicine'})
    assert response.status_code == 403

@pytest.mark.integration
def test_appointments_pagination_beyond_last_page_is_empty():
    headers = staff_headers()
    first = client.get('/appointments?page=1&size=2', headers=headers)
    assert first.status_code == 200
    body = first.json()
    beyond = client.get(f"/appointments?page={max(body['pages'] + 1, 2)}&size=2", headers=headers)
    assert beyond.status_code == 200
    result = beyond.json()
    assert result['items'] == []
    assert result['total'] == body['total']
    assert result['pages'] == body['pages']

@pytest.mark.integration
def test_patients_pagination_beyond_last_page_is_empty():
    headers = staff_headers()
    first = client.get('/patients?page=1&size=2', headers=headers)
    assert first.status_code == 200
    body = first.json()
    beyond = client.get(f"/patients?page={max(body['pages'] + 1, 2)}&size=2", headers=headers)
    assert beyond.status_code == 200
    result = beyond.json()
    assert result['items'] == []
    assert result['total'] == body['total']
    assert result['pages'] == body['pages']

@pytest.mark.integration
def test_patient_update_persists_phone():
    headers = staff_headers()
    with SessionLocal() as db:
        patient = Patient(name='Alia', phone='555-0200')
        db.add(patient); db.commit(); db.refresh(patient)
        patient_id = patient.id
    response = client.patch(f'/patients/{patient_id}', headers=headers, json={'phone': '555-0201'})
    assert response.status_code == 200
    assert response.json()['phone'] == '555-0201'
    assert client.get('/patients?search=Alia&size=100', headers=headers).json()['items']

@pytest.mark.integration
def test_patient_delete_allowed_without_appointments_and_blocked_with_appointments():
    headers = staff_headers()
    with SessionLocal() as db:
        deletable = Patient(name='Riya')
        db.add(deletable); db.commit(); db.refresh(deletable)
        deletable_id = deletable.id
        now = get_now(db)
    assert client.delete(f'/patients/{deletable_id}', headers=headers).status_code == 204

    appointment = client.post('/appointments', headers=headers, json={
        'doctor_id': 1,
        'patient': {'name': 'Hiya'},
        'start_time': (now + timedelta(days=45)).isoformat(),
        'end_time': (now + timedelta(days=45, minutes=30)).isoformat(),
    })
    assert appointment.status_code == 201
    patient_id = appointment.json()['patient_id']
    blocked = client.delete(f'/patients/{patient_id}', headers=headers)
    assert blocked.status_code == 409
