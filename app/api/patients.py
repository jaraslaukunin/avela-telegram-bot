"""Пациенты аккаунта: список и создание.

Один Telegram-аккаунт может вести несколько пациентов (взрослые и дети):
профили хранят ФИО и дату рождения, а пересечения приёмов считаются
на уровне конкретного пациента.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.db import get_session
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.user import User
from app.schemas import PatientCreate, PatientOut

PatientsRateLimit = RateLimiter(limit=60)

router = APIRouter(tags=["patients"], dependencies=[Depends(PatientsRateLimit)])
logger = logging.getLogger(__name__)


@router.get("/patients")
async def my_patients(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PatientOut]:
    patients = (
        await session.execute(
            select(Patient)
            .where(Patient.user_id == current.id)
            .order_by(Patient.created_at)
        )
    ).scalars().all()
    return [PatientOut.model_validate(patient) for patient in patients]


@router.post("/patients", status_code=201)
async def create_patient(
    payload: PatientCreate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PatientOut:
    patient = Patient(user_id=current.id, **payload.model_dump())
    session.add(patient)
    await session.commit()
    logger.info("Пациент создан patient_id=%s user_id=%s", patient.id, current.id)
    return PatientOut.model_validate(patient)


@router.delete("/patients/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: uuid.UUID,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Удаление профиля пациента.

    Нельзя удалить пациента с активными записями — сначала их нужно
    отменить, иначе история записи потеряет привязку к человеку.
    """
    patient = await session.get(Patient, patient_id)
    if patient is None or patient.user_id != current.id:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    has_active = await session.scalar(
        select(Appointment.id)
        .where(
            Appointment.patient_profile_id == patient.id,
            Appointment.status == "active",
        )
        .limit(1)
    )
    if has_active is not None:
        raise HTTPException(
            status_code=409,
            detail="У пациента есть активные записи — сначала отмените их",
        )

    await session.delete(patient)
    await session.commit()
    logger.info("Пациент удалён patient_id=%s user_id=%s", patient.id, current.id)
    return Response(status_code=204)
