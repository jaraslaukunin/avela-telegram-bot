"""Публичный каталог: сети, филиалы, услуги, врачи и свободные слоты.

Справочники кэшируются на короткий TTL: каждый запрос к Supabase — это
сетевой round-trip (~60 мс до региона проекта), а данные меняются редко.
Слоты НЕ кэшируются — они меняются с каждой записью.
"""
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import ttl_cache
from app.core.deps import get_current_user
from app.db import get_session, get_session_factory
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.user import User
from app.schemas import BranchOut, DoctorOut, NetworkOut, ServiceOut, SlotOut
from app.services.booking import list_available_slots

router = APIRouter(tags=["catalog"])

CATALOG_TTL_SECONDS = 20


@ttl_cache(CATALOG_TTL_SECONDS)
async def load_networks() -> list[NetworkOut]:
    factory = get_session_factory()
    async with factory() as session:
        networks = (
            await session.execute(
                select(Network).where(Network.is_active.is_(True)).order_by(Network.name)
            )
        ).scalars().all()
    return [NetworkOut.model_validate(network) for network in networks]


@ttl_cache(CATALOG_TTL_SECONDS)
async def load_branches(network_id: uuid.UUID) -> list[BranchOut]:
    factory = get_session_factory()
    async with factory() as session:
        branches = (
            await session.execute(
                select(Branch)
                .where(Branch.network_id == network_id, Branch.is_active.is_(True))
                .order_by(Branch.name)
            )
        ).scalars().all()
    return [BranchOut.model_validate(branch) for branch in branches]


@ttl_cache(CATALOG_TTL_SECONDS)
async def load_services(network_id: uuid.UUID) -> list[ServiceOut]:
    factory = get_session_factory()
    async with factory() as session:
        services = (
            await session.execute(
                select(Service)
                .where(Service.network_id == network_id, Service.is_active.is_(True))
                .order_by(Service.name)
            )
        ).scalars().all()
    return [ServiceOut.model_validate(service) for service in services]


@ttl_cache(CATALOG_TTL_SECONDS)
async def load_doctors(
    branch_id: uuid.UUID,
    service_id: uuid.UUID | None,
) -> list[DoctorOut]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Doctor).where(
            Doctor.branch_id == branch_id, Doctor.is_active.is_(True)
        )
        if service_id is not None:
            stmt = (
                stmt.join(DoctorService, DoctorService.doctor_id == Doctor.id)
                .where(DoctorService.service_id == service_id)
            )
        doctors = (await session.execute(stmt.order_by(Doctor.full_name))).scalars().all()
    return [DoctorOut.model_validate(doctor) for doctor in doctors]


@router.get("/networks")
async def list_networks(current: User = Depends(get_current_user)) -> list[NetworkOut]:
    return await load_networks()


@router.get("/networks/{network_id}/branches")
async def list_branches(
    network_id: uuid.UUID,
    current: User = Depends(get_current_user),
) -> list[BranchOut]:
    return await load_branches(network_id)


@router.get("/services")
async def list_services(
    network_id: uuid.UUID = Query(...),
    current: User = Depends(get_current_user),
) -> list[ServiceOut]:
    return await load_services(network_id)


@router.get("/branches/{branch_id}/doctors")
async def list_doctors(
    branch_id: uuid.UUID,
    service_id: uuid.UUID | None = None,
    current: User = Depends(get_current_user),
) -> list[DoctorOut]:
    return await load_doctors(branch_id, service_id)


@router.get("/slots/available")
async def available_slots(
    service_id: uuid.UUID = Query(...),
    branch_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SlotOut]:
    """Свободные слоты. Без doctor_id — «любой свободный врач»."""
    start = from_dt or datetime.now(UTC)
    end = to_dt or start + timedelta(days=14)

    rows = await list_available_slots(
        session, service_id, start, end, branch_id=branch_id, doctor_id=doctor_id
    )
    return [
        SlotOut(
            id=slot.id,
            doctor_id=slot.doctor_id,
            service_id=slot.service_id,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            price=slot.price,
        )
        for slot, _doctor, _branch in rows
    ]
