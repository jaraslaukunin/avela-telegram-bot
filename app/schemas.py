import uuid
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelegramLoginRequest(BaseModel):
    init_data: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int
    role: str
    first_name: str
    last_name: str
    username: str | None
    phone: str | None


class TelegramLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AppointmentOut(BaseModel):
    id: uuid.UUID
    status: str
    slot_id: uuid.UUID
    doctor_id: uuid.UUID
    service_id: uuid.UUID
    patient_id: uuid.UUID | None
    patient_name: str | None
    price: Decimal | None
    starts_at: datetime
    ends_at: datetime
    doctor_name: str
    service_name: str
    branch_name: str
    branch_address: str
    branch_phone: str
    branch_timezone: str
    cancellable_until: datetime


class SlotOut(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    service_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    price: Decimal | None


class NetworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    network_id: uuid.UUID
    name: str
    city: str
    region: str
    address: str
    phone: str
    timezone: str


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    full_name: str
    specialty: str
    photo_path: str | None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    network_id: uuid.UUID
    name: str
    duration_minutes: int


class BookingRequest(BaseModel):
    slot_id: uuid.UUID
    # Необязательно: без него бронируется пациент «по умолчанию»
    # (совместимость с ботом и старыми клиентами).
    patient_id: uuid.UUID | None = None


class RescheduleRequest(BaseModel):
    new_slot_id: uuid.UUID


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=300)
    birth_date: date | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    birth_date: date | None


# --- Административные схемы ---


class IsActiveUpdate(BaseModel):
    is_active: bool | None = None


class NetworkCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class NetworkUpdate(IsActiveUpdate):
    name: str | None = Field(default=None, min_length=1, max_length=200)


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str = ""
    region: str = ""
    address: str = ""
    phone: str = ""
    timezone: str = "Europe/Moscow"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError(f"Неизвестный часовой пояс: {value}") from exc
        return value


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = None
    region: str | None = None
    address: str | None = None
    phone: str | None = None
    timezone: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(gt=0, le=480)


class ServiceUpdate(IsActiveUpdate):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0, le=480)


class DoctorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=300)
    specialty: str = ""
    service_ids: list[uuid.UUID] = Field(default_factory=list)


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=300)
    specialty: str | None = None
    is_active: bool | None = None


class DoctorServicesUpdate(BaseModel):
    service_ids: list[uuid.UUID]


class BranchAdminAssign(BaseModel):
    telegram_id: int


class ScheduleTemplateCreate(BaseModel):
    service_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    valid_from: date
    valid_until: date | None = None

    @field_validator("end_time")
    @classmethod
    def _validate_times(cls, value: time, info: object) -> time:
        start = getattr(info, "data", {}).get("start_time")
        if isinstance(start, time) and value <= start:
            raise ValueError("end_time должен быть позже start_time")
        return value


class ScheduleTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_id: uuid.UUID
    service_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    valid_from: date
    valid_until: date | None
    is_active: bool


class SlotGenerationRequest(BaseModel):
    from_date: date
    to_date: date


class SlotGenerationResult(BaseModel):
    created: int
    skipped: int


class AdminAppointmentOut(BaseModel):
    id: uuid.UUID
    status: str
    patient_telegram_id: int
    patient_name: str
    doctor_name: str
    branch_id: uuid.UUID
    branch_name: str
    branch_timezone: str
    starts_at: datetime
    ends_at: datetime
    cancelled_by: str | None


class AnonymizationOut(BaseModel):
    anonymized: bool
    cancelled_appointments: int
    skipped_notifications: int


class AdminScopeOut(BaseModel):
    """Что видит администратор: роль и разрешённые сети/филиалы."""

    role: str
    can_access_all: bool
    network_ids: list[uuid.UUID]
    branch_ids: list[uuid.UUID]


class AdminDoctorOut(DoctorOut):
    """Врач в админке: нужен признак активности и список услуг."""

    is_active: bool
    service_ids: list[uuid.UUID]
