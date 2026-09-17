from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
class Token(BaseModel): access_token: str; token_type: str = 'bearer'
class ClockRequest(BaseModel):
    advance_to: datetime | None = None
    advance_by_minutes: int | None = Field(default=None, ge=0)
class ClockResponse(BaseModel):
    current_time: datetime
    reminders_sent: int
    appointments_marked_no_show: int
ItemT = TypeVar('ItemT')
class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    size: int
    total: int
    pages: int

class DoctorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialty: str = Field(min_length=2, max_length=120)
class DoctorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    specialty: str | None = Field(default=None, min_length=2, max_length=120)
    active: bool | None = None
class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; specialty: str; active: bool
class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120); phone: str | None = None; email: EmailStr | None = None
class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
class PatientMergeRequest(BaseModel):
    merged_into_patient_id: int
class PatientOut(PatientCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int; created_at: datetime; merged_into_patient_id: int | None = None
class AppointmentCreate(BaseModel):
    doctor_id: int; patient_id: int | None = None; patient: PatientCreate | None = None
    start_time: datetime; end_time: datetime
class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; doctor_id: int; patient_id: int; start_time: datetime; end_time: datetime; status: str
    late_fee_charged: bool; late_fee_amount: Decimal; patient_name: str | None = None; doctor_name: str | None = None
    @field_serializer('late_fee_amount')
    def serialize_fee(self, value: Decimal) -> float: return float(value)
class RescheduleRequest(BaseModel): start_time: datetime; end_time: datetime
class CancelOut(AppointmentOut): cancelled_at: datetime | None = None
class OutboxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; sent_at: datetime; recipient: str; subject: str; body: str
    appointment_id: int | None = None; reminder_date: date | None = None
