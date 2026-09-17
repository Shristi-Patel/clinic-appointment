from datetime import datetime
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30), default='staff')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Doctor(Base):
    __tablename__ = 'doctors'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    specialty: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

class Patient(Base):
    __tablename__ = 'patients'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(255))
    merged_into_patient_id: Mapped[int | None] = mapped_column(ForeignKey('patients.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey('doctors.id'), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey('patients.id'), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default='booked', index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    late_fee_charged: Mapped[bool] = mapped_column(Boolean, default=False)
    late_fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    doctor: Mapped[Doctor] = relationship()
    patient: Mapped[Patient] = relationship()
    @property
    def patient_name(self) -> str: return self.patient.name
    @property
    def doctor_name(self) -> str: return self.doctor.name
    __table_args__ = (
        ExcludeConstraint(
            ('doctor_id', '='),
            (func.tstzrange(start_time, end_time, '[)'), '&&'),
            where=(status.not_in(('cancelled', 'no_show'))),
            name='no_overlapping_active_appointments',
            using='gist',
        ),
    )

class AppointmentHistory(Base):
    __tablename__ = 'appointment_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id'), index=True)
    old_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    old_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class AppointmentIdempotency(Base):
    __tablename__ = 'appointment_idempotency'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    appointment_id: Mapped[int] = mapped_column(ForeignKey('appointments.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ClockState(Base):
    __tablename__ = 'clock_state'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    current_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class Outbox(Base):
    __tablename__ = 'outbox'
    id: Mapped[int] = mapped_column(primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey('appointments.id'), nullable=True, index=True)
    reminder_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    __table_args__ = (UniqueConstraint('appointment_id', 'reminder_date', name='uq_outbox_appointment_reminder_day'),)
