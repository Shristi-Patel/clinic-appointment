from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.config import clinic_zone, settings
from app.models import Appointment
from app.notifications import NotificationService

def _days_between(start: datetime, end: datetime):
    day = start.astimezone(clinic_zone).date()
    last = end.astimezone(clinic_zone).date()
    while day <= last:
        yield day
        day += timedelta(days=1)

def process_due_jobs(db: Session, previous: datetime, current: datetime) -> dict[str, int]:
    reminders_sent = 0
    service = NotificationService(db, current)
    for day in _days_between(previous, current):
        due_local = datetime.combine(day, time(settings.morning_reminder_hour), tzinfo=clinic_zone)
        due = due_local.astimezone(timezone.utc)
        if not previous < due <= current:
            continue
        start = datetime.combine(day, time.min, tzinfo=clinic_zone)
        finish = start + timedelta(days=1)
        appointments = db.scalars(select(Appointment).options(joinedload(Appointment.patient)).where(Appointment.status == 'booked', Appointment.start_time >= start, Appointment.start_time < finish)).all()
        for appointment in appointments:
            recipient = appointment.patient.email or appointment.patient.phone or appointment.patient.name
            message = service.send(recipient, 'ClinicDesk appointment reminder', f"Reminder: {appointment.patient.name} has an appointment at {appointment.start_time.astimezone(clinic_zone).strftime('%H:%M')} on {day.isoformat()}.", appointment.id, day)
            reminders_sent += 1 if message else 0

    cutoff = current - timedelta(minutes=settings.no_show_window_minutes)
    overdue = db.scalars(select(Appointment).where(Appointment.status == 'booked', Appointment.start_time <= cutoff)).all()
    for appointment in overdue:
        appointment.status = 'no_show'
    db.flush()
    return {'reminders_sent': reminders_sent, 'appointments_marked_no_show': len(overdue)}