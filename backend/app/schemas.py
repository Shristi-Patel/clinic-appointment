from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
class Token(BaseModel): access_token: str; token_type: str = 'bearer'
class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; specialty: str; active: bool
class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120); phone: str | None = None; email: EmailStr | None = None
class PatientOut(PatientCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int; created_at: datetime
class AppointmentCreate(BaseModel):
    doctor_id: int; patient_id: int | None = None; patient: PatientCreate | None = None
    start_time: datetime; end_time: datetime
class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; doctor_id: int; patient_id: int; start_time: datetime; end_time: datetime; status: str
    late_fee_charged: bool; late_fee_amount: float; patient_name: str | None = None; doctor_name: str | None = None
class RescheduleRequest(BaseModel): start_time: datetime; end_time: datetime
class CancelOut(AppointmentOut): cancelled_at: datetime | None = None
