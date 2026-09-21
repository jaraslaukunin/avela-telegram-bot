import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.db import get_session
from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import Slot
from app.models.user import User
from app.schemas import AppointmentOut, BookingRequest, RescheduleRequest
from app.services.booking import (
    AppointmentNotFoundError,
    BookingError,
    DeadlinePassedError,
    SlotUnavailableError,
    book_slot,
    cancel_appointment,
    get_appointment_context,
    reschedule_appointment,
)

BookingRateLimit = RateLimiter(limit=30)

router = APIRouter(tags=["appointments"], dependencies=[Depends(BookingRateLimit)])
logger = logging.getLogger(__name__)


def _to_out(
    appointment: Appointment,
    slot: Slot,
    doctor: Doctor,
    service: Service,
    branch: Branch,
) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        status=appointment.status,
        slot_id=slot.id,
        doctor_id=doctor.id,
        service_id=service.id,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        doctor_name=doctor.full_name,
        service_name=service.name,
        branch_name=branch.name,
        branch_address=branch.address,
        branch_phone=branch.phone,
        branch_timezone=branch.timezone,
        cancellable_until=branch.cancel_deadline(slot.starts_at),
    )


async def _context_or_404(
    session: AsyncSession,
    patient_id: uuid.UUID,
    appointment_id: uuid.UUID,
) -> AppointmentOut:
    context = await get_appointment_context(session, patient_id, appointment_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return _to_out(context[0], context[1], context[2], context[3], context[4])


@router.get("/appointments")
async def my_appointments(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AppointmentOut]:
    stmt = (
        select(Appointment, Slot, Doctor, Service, Branch)
        .join(Slot, Appointment.slot_id == Slot.id)
        .join(Doctor, Slot.doctor_id == Doctor.id)
        .join(Branch, Doctor.branch_id == Branch.id)
        .join(Service, Slot.service_id == Service.id)
        .where(Appointment.patient_id == current.id)
        .order_by(Slot.starts_at.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).all()
    return [_to_out(row[0], row[1], row[2], row[3], row[4]) for row in rows]


@router.post("/appointments")
async def create_appointment(
    payload: BookingRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AppointmentOut:
    try:
        appointment = await book_slot(session, current, payload.slot_id)
    except SlotUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "Запись создана appointment_id=%s patient_id=%s",
        appointment.id,
        current.id,
    )
    return await _context_or_404(session, current.id, appointment.id)


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment_route(
    appointment_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AppointmentOut:
    try:
        await cancel_appointment(session, current.id, appointment_id)
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DeadlinePassedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("Запись отменена appointment_id=%s", appointment_id)
    return await _context_or_404(session, current.id, appointment_id)


@router.post("/appointments/{appointment_id}/reschedule")
async def reschedule_appointment_route(
    appointment_id: uuid.UUID,
    payload: RescheduleRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AppointmentOut:
    try:
        new_appointment = await reschedule_appointment(
            session, current.id, appointment_id, payload.new_slot_id
        )
    except AppointmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DeadlinePassedError, SlotUnavailableError, BookingError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "Запись перенесена new_appointment_id=%s из=%s",
        new_appointment.id,
        appointment_id,
    )
    return await _context_or_404(session, current.id, new_appointment.id)
