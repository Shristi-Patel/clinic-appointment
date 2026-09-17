from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.config import settings
from app.clock import advance_value, get_now, set_now
from app.db import get_db
from app.models import Appointment, Doctor, Outbox, Patient, User
from app.scheduler import process_due_jobs
from app.schemas import AppointmentCreate, AppointmentOut, CancelOut, ClockRequest, ClockResponse, DoctorCreate, DoctorOut, LoginRequest, OutboxOut, Page, PatientOut, RescheduleRequest, Token, UserCreate

app = FastAPI(title='ClinicDesk API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = 'HS256'


def password_hash(value: str) -> str: return pwd_context.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd_context.verify(value, hashed)
def make_token(user: User, now: datetime) -> str:
    return jwt.encode({'sub': str(user.id), 'exp': now + timedelta(minutes=settings.access_token_expire_minutes)}, settings.secret_key, algorithm=ALGORITHM)


def require_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(status_code=401, detail='Authentication required')
    try: user_id = int(jwt.decode(authorization[7:], settings.secret_key, algorithms=[ALGORITHM]).get('sub'))
    except (JWTError, TypeError, ValueError): raise HTTPException(status_code=401, detail='Invalid or expired token')
    user = db.get(User, user_id)
    if not user: raise HTTPException(status_code=401, detail='Invalid user')
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != 'admin': raise HTTPException(status_code=403, detail='Admin access required')
    return user


def page_result(items, page: int, size: int, total: int):
    return {'items': items, 'page': page, 'size': size, 'total': total, 'pages': ceil(total / size) if total else 0}


@app.get('/health')
def health(): return {'status': 'ok'}

@app.post('/clock', response_model=ClockResponse)
def advance_clock(payload: ClockRequest, db: Session = Depends(get_db), _: User = Depends(require_user)):
    current = get_now(db)
    try:
        target = advance_value(current, payload.advance_to, payload.advance_by_minutes)
    except ValueError as error:
        raise HTTPException(422, str(error))
    set_now(db, target)
    summary = process_due_jobs(db, current, target)
    db.commit()
    return {'current_time': target, **summary}


@app.post('/auth/register', response_model=Token, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == payload.email.lower())): raise HTTPException(409, 'An account with this email already exists')
    is_first_admin = settings.first_admin_email and payload.email.lower() == settings.first_admin_email.lower()
    user = User(name=payload.name, email=payload.email.lower(), hashed_password=password_hash(payload.password), role='admin' if is_first_admin else 'staff')
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account with this email already exists')
    db.refresh(user)
    return Token(access_token=make_token(user, get_now(db)))


@app.post('/auth/login', response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password): raise HTTPException(401, 'Email or password is incorrect')
    return Token(access_token=make_token(user, get_now(db)))

@app.get('/outbox', response_model=Page[OutboxOut])
def outbox(appointment_id: int | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_user)):
    base = select(Outbox)
    if appointment_id: base = base.where(Outbox.appointment_id == appointment_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.order_by(Outbox.sent_at.desc(), Outbox.id.desc()).offset((page - 1) * size).limit(size)).all()
    return page_result(items, page, size, total)


@app.get('/doctors', response_model=Page[DoctorOut])
def doctors(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), sort: str = 'name', db: Session = Depends(get_db), _: User = Depends(require_user)):
    sort_fields = {'name': Doctor.name, '-name': Doctor.name.desc(), 'id': Doctor.id, '-id': Doctor.id.desc()}
    if sort not in sort_fields: raise HTTPException(422, 'Unsupported doctor sort field')
    base = select(Doctor).where(Doctor.active.is_(True))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.order_by(sort_fields[sort]).offset((page - 1) * size).limit(size)).all()
    return page_result(items, page, size, total)


@app.post('/doctors', response_model=DoctorOut, status_code=201)
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    doctor = Doctor(**payload.model_dump()); db.add(doctor); db.commit(); db.refresh(doctor); return doctor


@app.patch('/doctors/{doctor_id}/deactivate', response_model=DoctorOut)
def deactivate_doctor(doctor_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor: raise HTTPException(404, 'Doctor not found')
    doctor.active = False; db.commit(); db.refresh(doctor); return doctor


@app.get('/doctors/{doctor_id}/schedule', response_model=list[AppointmentOut])
def schedule(doctor_id: int, day: date = Query(..., alias='date'), db: Session = Depends(get_db), _: User = Depends(require_user)):
    start = datetime.combine(day, time.min, tzinfo=timezone.utc); end = start + timedelta(days=1)
    query = select(Appointment).options(joinedload(Appointment.patient), joinedload(Appointment.doctor)).where(Appointment.doctor_id == doctor_id, Appointment.start_time >= start, Appointment.start_time < end).order_by(Appointment.start_time)
    return db.scalars(query).all()


@app.get('/patients', response_model=Page[PatientOut])
def patients(search: str = '', page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_user)):
    base = select(Patient).where(Patient.name.ilike(f'%{search}%'))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.order_by(Patient.name).offset((page - 1) * size).limit(size)).all()
    return page_result(items, page, size, total)


def appointment_base(patient_name: str, patient_id: int | None, doctor_id: int | None, date_from: datetime | None, date_to: datetime | None, status_filter: str | None):
    query = select(Appointment).join(Patient).join(Doctor)
    if patient_name: query = query.where(Patient.name.ilike(f'%{patient_name}%'))
    if patient_id: query = query.where(Appointment.patient_id == patient_id)
    if doctor_id: query = query.where(Appointment.doctor_id == doctor_id)
    if date_from: query = query.where(Appointment.start_time >= date_from)
    if date_to: query = query.where(Appointment.start_time <= date_to)
    if status_filter: query = query.where(Appointment.status == status_filter)
    return query


@app.get('/appointments', response_model=Page[AppointmentOut])
def appointments(patient_name: str = '', patient_id: int | None = None, doctor_id: int | None = None, date_from: datetime | None = None, date_to: datetime | None = None, status_filter: str | None = Query(None, alias='status'), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), sort: str = 'start_time', db: Session = Depends(get_db), _: User = Depends(require_user)):
    sort_fields = {'start_time': Appointment.start_time, '-start_time': Appointment.start_time.desc(), 'doctor_name': Doctor.name, '-doctor_name': Doctor.name.desc(), 'patient_name': Patient.name, '-patient_name': Patient.name.desc(), 'status': Appointment.status, '-status': Appointment.status.desc()}
    if sort not in sort_fields: raise HTTPException(422, 'Unsupported appointment sort field')
    base = appointment_base(patient_name, patient_id, doctor_id, date_from, date_to, status_filter)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    query = base.options(joinedload(Appointment.patient), joinedload(Appointment.doctor)).order_by(sort_fields[sort], Appointment.id)
    items = db.scalars(query.offset((page - 1) * size).limit(size)).all()
    return page_result(items, page, size, total)


@app.get('/appointments/{appointment_id}', response_model=AppointmentOut)
def appointment_detail(appointment_id: int, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.scalar(select(Appointment).options(joinedload(Appointment.patient), joinedload(Appointment.doctor)).where(Appointment.id == appointment_id))
    if not item: raise HTTPException(404, 'Appointment not found')
    return item


def validate_times(start: datetime, end: datetime, now: datetime):
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
    if end <= start: raise HTTPException(422, 'end_time must be after start_time')
    if start < now: raise HTTPException(422, 'Appointments cannot be booked in the past')


def conflict_error(error: IntegrityError):
    if 'no_overlapping_active_appointments' in str(error.orig): return HTTPException(409, 'That doctor already has an overlapping appointment')
    return None


@app.post('/appointments', response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    validate_times(payload.start_time, payload.end_time, get_now(db))
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
    now = get_now(db); item.status = 'cancelled'; item.cancelled_at = now
    late = item.start_time - now < timedelta(hours=settings.late_cancellation_hours)
    item.late_fee_charged = late; item.late_fee_amount = settings.late_cancellation_fee if late else 0
    db.commit(); db.refresh(item); return item

@app.patch('/appointments/{appointment_id}/complete', response_model=AppointmentOut)
def complete(appointment_id: int, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, 'Appointment not found')
    if item.status != 'booked': raise HTTPException(409, 'Only booked appointments can be completed')
    item.status = 'completed'; db.commit(); db.refresh(item); return item


@app.patch('/appointments/{appointment_id}/reschedule', response_model=AppointmentOut)
def reschedule(appointment_id: int, payload: RescheduleRequest, db: Session = Depends(get_db), _: User = Depends(require_user)):
    item = db.get(Appointment, appointment_id)
    if not item: raise HTTPException(404, 'Appointment not found')
    validate_times(payload.start_time, payload.end_time, get_now(db)); item.start_time = payload.start_time; item.end_time = payload.end_time
    try: db.commit()
    except IntegrityError as error:
        db.rollback(); conflict = conflict_error(error)
        if conflict: raise conflict
        raise HTTPException(400, 'Could not reschedule appointment')
    db.refresh(item); return item
