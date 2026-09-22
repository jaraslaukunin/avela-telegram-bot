"""Пациенты аккаунта: список и создание.

Один Telegram-аккаунт может вести несколько пациентов (взрослые и дети):
профили хранят ФИО и дату рождения, а пересечения приёмов считаются
на уровне конкретного пациента.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.db import get_session
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
