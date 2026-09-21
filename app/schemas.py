import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class RescheduleRequest(BaseModel):
    new_slot_id: uuid.UUID
