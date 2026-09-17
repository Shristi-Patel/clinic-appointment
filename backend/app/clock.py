from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ClockState

def get_now(db: Session) -> datetime:
    state = db.scalar(select(ClockState).where(ClockState.id == 1))
    if state is None:
        state = ClockState(id=1, current_time=datetime.now(timezone.utc))
        db.add(state)
        db.flush()
    return state.current_time

def set_now(db: Session, value: datetime) -> None:
    state = db.scalar(select(ClockState).where(ClockState.id == 1).with_for_update())
    if state is None:
        state = ClockState(id=1, current_time=value)
        db.add(state)
    else:
        state.current_time = value

def advance_value(current: datetime, advance_to: datetime | None, advance_by_minutes: int | None) -> datetime:
    if advance_to is not None and advance_by_minutes is not None:
        raise ValueError('Provide either advance_to or advance_by_minutes, not both')
    if advance_to is None and advance_by_minutes is None:
        raise ValueError('Provide advance_to or advance_by_minutes')
    value = advance_to if advance_to is not None else current + timedelta(minutes=advance_by_minutes or 0)
    if value < current:
        raise ValueError('The simulated clock can only move forward')
    return value