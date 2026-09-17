"""Seed local/demo doctors and promote FIRST_ADMIN_EMAIL when configured."""
from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import Doctor, User

DOCTORS = (
    ('Maya Chen', 'Family Medicine'),
    ('Elias Romero', 'Cardiology'),
    ('Priya Shah', 'Pediatrics'),
)

with SessionLocal() as db:
    for name, specialty in DOCTORS:
        if not db.scalar(select(Doctor).where(Doctor.name == name)):
            db.add(Doctor(name=name, specialty=specialty))
    if settings.first_admin_email:
        user = db.scalar(select(User).where(User.email == settings.first_admin_email.lower()))
        if user:
            user.role = 'admin'
    db.commit()
    print('ClinicDesk seed complete')