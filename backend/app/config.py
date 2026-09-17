from decimal import Decimal
from zoneinfo import ZoneInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://clinicdesk:clinicdesk@localhost:5432/clinicdesk'
    secret_key: str = 'change-this-in-production'
    access_token_expire_minutes: int = 480
    late_cancellation_hours: int = 24
    late_cancellation_fee: Decimal = Decimal('50.00')
    first_admin_email: str | None = None
    morning_reminder_hour: int = 8
    no_show_window_minutes: int = 30
    clinic_timezone: str = 'UTC'
    cors_origins: str = 'http://localhost:5173'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()
clinic_zone = ZoneInfo(settings.clinic_timezone)
