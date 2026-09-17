from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Outbox

class NotificationService:
    def __init__(self, db: Session, now: datetime):
        self.db = db
        self.now = now

    def send(self, to: str, subject: str, body: str, appointment_id: int | None = None, reminder_date: date | None = None) -> Outbox | None:
        message = Outbox(sent_at=self.now, recipient=to, subject=subject, body=body, appointment_id=appointment_id, reminder_date=reminder_date)
        try:
            with self.db.begin_nested():
                self.db.add(message)
                self.db.flush()
        except IntegrityError:
            return None
        return message