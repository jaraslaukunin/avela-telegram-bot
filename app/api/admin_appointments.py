"""Административный API: записи пациентов (просмотр и отмена)."""
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.rate_limit import RateLimiter
from app.core.roles import ADMIN_ROLES
from app.db import get_session
from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import Slot
from app.models.user import User
from app.schemas import (
    AdminAppointmentOut,
    AdminMessageRequest,
    AdminMessageResponse,
    RescheduleRequest,
)
from app.services import permissions
from app.services.booking import (
    AppointmentNotFoundError,
    BookingError,
    cancel_appointment_by_admin,
    get_appointment_context_for_admin,
    reschedule_appointment_by_admin,
)
from app.services.messaging import (
    PatientUnreachableError,
    send_message_to_appointment_patient,
)

logger = logging.getLogger(__name__)

AdminAppointmentsRateLimit = RateLimiter(limit=120)

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(AdminAppointmentsRateLimit)]
)

AdminUser = Annotated[User, Depends(require_roles(*ADMIN_ROLES))]
DbSession = Annotated[AsyncSession, Depends(get_session)]


def _to_admin_out(
    appointment: Appointment,
    slot: Slot,
    doctor: Doctor,
    _service: Service,
    branch: Branch,
    patient: User,
) -> AdminAppointmentOut:
    patient_name = f"{patient.first_name} {patient.last_name}".strip() or "—"
    return AdminAppointmentOut(
        id=appointment.id,
        status=appointment.status,
        patient_telegram_id=patient.telegram_id,
        patient_name=patient_name,
        doctor_name=doctor.full_name,
        branch_id=branch.id,
        branch_name=branch.name,
        branch_timezone=branch.timezone,
        doctor_id=doctor.id,
        service_id=_service.id,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        cancelled_by=appointment.cancelled_by,
    )


@router.get("/appointments")
async def list_appointments(
    current: AdminUser,
    session: DbSession,
    branch_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminAppointmentOut]:
    allowed = await permissions.scoped_branch_ids(session, current)

    if branch_id is not None and not permissions.can_access_branch(allowed, branch_id):
        raise HTTPException(status_code=404, detail="Филиал не найден")

    stmt = (
        select(Appointment, Slot, Doctor, Service, Branch, User)
        .join(Slot, Appointment.slot_id == Slot.id)
        .join(Doctor, Slot.doctor_id == Doctor.id)
        .join(Service, Slot.service_id == Service.id)
        .join(Branch, Doctor.branch_id == Branch.id)
        .join(User, Appointment.patient_id == User.id)
        .order_by(Slot.starts_at.desc())
        .limit(limit)
    )
    if allowed is not None:
        stmt = stmt.where(Branch.id.in_(allowed))
    if branch_id is not None:
        stmt = stmt.where(Branch.id == branch_id)

    rows = (await session.execute(stmt)).all()
    return [
        _to_admin_out(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows
    ]


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment_admin(
    appointment_id: uuid.UUID, current: AdminUser, session: DbSession
) -> AdminAppointmentOut:
    context = await get_appointment_context_for_admin(session, appointment_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    appointment, slot, doctor, service, branch = context

    allowed = await permissions.scoped_branch_ids(session, current)
    if not permissions.can_access_branch(allowed, branch.id):
        raise HTTPException(status_code=404, detail="Запись не найдена")

    patient = await session.get(User, appointment.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    try:
        cancelled = await cancel_appointment_by_admin(session, current, appointment.id)
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "Запись отменена администратором appointment_id=%s actor=%s",
        cancelled.id,
        current.telegram_id,
    )
    return _to_admin_out(cancelled, slot, doctor, service, branch, patient)


@router.post("/appointments/{appointment_id}/reschedule")
async def reschedule_appointment_admin(
    appointment_id: uuid.UUID,
    payload: RescheduleRequest,
    current: AdminUser,
    session: DbSession,
) -> AdminAppointmentOut:
    """Перенос записи администратором — без лимита 2 часов, с аудитом."""
    context = await get_appointment_context_for_admin(session, appointment_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    appointment, _slot, _doctor, _service, branch = context

    allowed = await permissions.scoped_branch_ids(session, current)
    if not permissions.can_access_branch(allowed, branch.id):
        raise HTTPException(status_code=404, detail="Запись не найдена")

    try:
        moved = await reschedule_appointment_by_admin(
            session, current, appointment.id, payload.new_slot_id
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "Запись перенесена администратором new_appointment_id=%s (из %s) actor=%s",
        moved.id,
        appointment.id,
        current.telegram_id,
    )

    new_context = await get_appointment_context_for_admin(session, moved.id)
    if new_context is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    new_appointment, new_slot, doctor, service, new_branch = new_context
    patient = await session.get(User, new_appointment.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    return _to_admin_out(new_appointment, new_slot, doctor, service, new_branch, patient)


@router.post("/appointments/{appointment_id}/message")
async def message_appointment_patient(
    appointment_id: uuid.UUID,
    payload: AdminMessageRequest,
    current: AdminUser,
    session: DbSession,
) -> AdminMessageResponse:
    """Сообщение пациенту от имени бота — например, «врач задерживается».

    Права проверяются здесь (зона филиала), отправка и аудит — в сервисе.
    """
    context = await get_appointment_context_for_admin(session, appointment_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    _appointment, _slot, _doctor, _service, branch = context
    allowed = await permissions.scoped_branch_ids(session, current)
    if not permissions.can_access_branch(allowed, branch.id):
        raise HTTPException(status_code=404, detail="Запись не найдена")

    try:
        await send_message_to_appointment_patient(
            session, current, appointment_id, payload.text
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PatientUnreachableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return AdminMessageResponse(sent=True)
