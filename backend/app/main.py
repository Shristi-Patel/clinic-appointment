from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import Appointment, Doctor, Patient, User
from app.schemas import AppointmentCreate, AppointmentOut, CancelOut, DoctorOut, LoginRequest, PatientOut, RescheduleRequest, Token, UserCreate

app = FastAPI(title='ClinicDesk API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = 'HS256'

def password_hash(value: str) -> str: return pwd_context.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd_context.verify(value, hashed)
def make_token(user: User) -> str:
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)}, settings.secret_key, algorithm=ALGORITHM)

# Read bearer tokens without coupling the API to form-encoded OAuth flows.
def require_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(status_code=401, detail='Authentication required')
    try: user_id = int(jwt.decode(authorization[7:], settings.secret_key, algorithms=[ALGORITHM]).get('sub'))
    except (JWTError, TypeError, ValueError): raise HTTPException(status_code=401, detail='Invalid or expired token')
    user = db.get(User, user_id)
    if not user: raise HTTPException(status_code=401, detail='Invalid user')
    return user

@app.get('/health')
def health(): return {'status': 'ok'}

@app.post('/auth/register', response_model=Token, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == payload.email.lower())): raise HTTPException(409, 'An account with this email already exists')
    user = User(name=payload.name, email=payload.email.lower(), hashed_password=password_hash(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return Token(access_token=make_token(user))

@app.post('/auth/login', response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password): raise HTTPException(401, 'Email or password is incorrect')
    return Token(access_token=make_token(user))

@app.get('/doctors', response_model=list[DoctorOut])
def doctors(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), sort: str = 'name', db: Session = Depends(get_db), _: User = Depends(require_user)):
    return db.scalars(select(Doctor).where(Doctor.active.is_(True)).order_by(Doctor.name if sort == 'name' else Doctor.id).offset((page-1)*size).limit(size)).all()

@app.get('/doctors/{doctor_id}/schedule', response_model=list[AppointmentOut])
def schedule(doctor_id: int, day: date = Query(..., alias='date'), db: Session = Depends(get_db), _: User = Depends(require_user)):
    start = datetime.combine(day, time.min, tzinfo=timezone.utc); end = start + timedelta(days=1)
    return db.scalars(select(Appointment).where(Appointment.doctor_id == doctor_id, Appointment.start_time >= start, Appointment.start_time < end).order_by(Appointment.start_time)).all()

@app.get('/patients', response_model=list[PatientOut])
def patients(search: str = '', page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_user)):
    query = select(Patient).where(Patient.name.ilike(f'%{search}%')).order_by(Patient.name).offset((page-1)*size).limit(size)
    return db.scalars(query).all()

def appointment_query():
    return select(Appointment).join(Patient).join(Doctor)

@app.get('/appointments', response_model=list[AppointmentOut])
def appointments(patient_name: str = '', doctor_id: int | None = None, date_from: datetime | None = None, date_to: datetime | None = None, status_filter: str | None = Query(None, alias='status'), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), sort: str = 'start_time', db: Session = Depends(get_db), _: User = Depends(require_user)):
    query = appointment_query()
    if patient_name: query = query.where(Patient.name.ilike(f'%{patient_name}%'))
    if doctor_id: query = query.where(Appointment.doctor_id == doctor_id)
    if date_from: query = query.where(Appointment.start_time >= date_from)
    if date_to: query = query.where(Appointment.start_time <= date_to)
    if status_filter: query = query.where(Appointment.status == status_filter)
    return db.scalars(query.order_by(Appointment.start_time.desc() if sort == '-start_time' else Appointment.start_time).offset((page-1)*size).limit(size)).all()

@app.get('/appointments/{appointment_id}', response_model=AppointmentOut)
def appointment_detail(appointment_id: int, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, 'Appointment not found')
    return item

def validate_times(start: datetime, end: datetime):
    now = datetime.now(timezone.utc)
    if end <= start: raise HTTPException(422, 'end_time must be after start_time')
    if start < now: raise HTTPException(422, 'Appointments cannot be booked in the past')

def conflict_error(error: IntegrityError):
    if 'no_overlapping_active_appointments' in str(error.orig): return HTTPException(409, 'That doctor already has an overlapping appointment')
    return None

@app.post('/appointments', response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    validate_times(payload.start_time, payload.end_time)
    if not db.get(Doctor, payload.doctor_id): raise HTTPException(404, 'Doctor not found')
    patient = db.get(Patient, payload.patient_id) if payload.patient_id else None
    if not patient and payload.patient: patient = Patient(**payload.patient.model_dump()); db.add(patient); db.flush()
    if not patient: raise HTTPException(422, 'Select an existing patient or provide patient details')
    item = Appointment(doctor_id=payload.doctor_id, patient_id=patient.id, start_time=payload.start_time, end_time=payload.end_time, created_by_user_id=user.id)
    db.add(item)
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); conflict = conflict_error(error)
        if conflict: raise conflict
        raise HTTPException(400, 'Could not create appointment')
    db.refresh(item); return item

@app.patch('/appointments/{appointment_id}/cancel', response_model=CancelOut)
def cancel(appointment_id: int, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, 'Appointment not found')
    if item.status == 'cancelled': raise HTTPException(409, 'Appointment is already cancelled')
    now = datetime.now(timezone.utc); item.status = 'cancelled'; item.cancelled_at = now
    late = item.start_time - now < timedelta(hours=settings.late_cancellation_hours)
    item.late_fee_charged = late; item.late_fee_amount = settings.late_cancellation_fee if late else 0
    db.commit(); db.refresh(item); return item

@app.patch('/appointments/{appointment_id}/reschedule', response_model=AppointmentOut)
def reschedule(appointment_id: int, payload: RescheduleRequest, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, 'Appointment not found')
    validate_times(payload.start_time, payload.end_time); item.start_time = payload.start_time; item.end_time = payload.end_time
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); conflict = conflict_error(error)
        if conflict: raise conflict
        raise HTTPException(400, 'Could not reschedule appointment')
    db.refresh(item); return item
