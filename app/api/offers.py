"""Поиск для пациента: специалист → предложения (филиал, врач, цена, время).

Отличие от «каталога по сети»: здесь поиск идёт по ВСЕМ сетям сразу —
пациенту важно найти врача, а не выбрать тенанта. Специалист ищется по
названию услуги, поэтому «Терапевт» в двух сетях — это один пункт поиска.

Кэш справочников — явный (последнее значение + TTL), а не декоратор:
загрузка выполняется через внедрённую сессию, поэтому её можно тестировать.
"""
import logging
import math
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db import get_session
from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.schedule import Slot
from app.models.user import User
from app.schemas import OfferOut, OffersResponse, ServiceNameOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["catalog"])

SERVICES_TTL_SECONDS = 60.0

# Последнее вычисленное значение справочника: (момент, данные).
_cached_services: tuple[float, list[ServiceNameOut]] | None = None
_cached_cities: tuple[float, list[str]] | None = None


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние по большому кругу (формула гаверсинуса)."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


async def _load_service_names(session: AsyncSession) -> list[ServiceNameOut]:
    """Специальности/услуги по всем активным сетям — без дублей по названию."""
    rows = (
        await session.execute(
            select(
                Service.name,
                func.min(Service.duration_minutes).label("duration_minutes"),
                func.count(func.distinct(Service.network_id)).label("networks"),
            )
            .join(Network, Service.network_id == Network.id)
            .where(Service.is_active.is_(True), Network.is_active.is_(True))
            .group_by(Service.name)
            .order_by(Service.name)
        )
    ).all()

    return [
        ServiceNameOut(name=row[0], duration_minutes=row[1], networks_count=row[2])
        for row in rows
    ]


async def _load_cities(session: AsyncSession) -> list[str]:
    rows = (
        await session.execute(
            select(Branch.city)
            .join(Network, Branch.network_id == Network.id)
            .where(
                Branch.is_active.is_(True),
                Branch.city != "",
                Network.is_active.is_(True),
            )
            .distinct()
            .order_by(Branch.city)
        )
    ).scalars().all()
    return list(rows)


@router.get("/services")
async def search_services(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ServiceNameOut]:
    """Шаг 1: выбор специалиста (услуги) по всем сетям."""
    global _cached_services

    if (
        _cached_services is not None
        and time.monotonic() - _cached_services[0] < SERVICES_TTL_SECONDS
    ):
        return _cached_services[1]

    values = await _load_service_names(session)
    _cached_services = (time.monotonic(), values)
    return values


@router.get("/cities")
async def search_cities(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Города, где есть активные филиалы — для шага «гео»."""
    global _cached_cities

    if (
        _cached_cities is not None
        and time.monotonic() - _cached_cities[0] < SERVICES_TTL_SECONDS
    ):
        return _cached_cities[1]

    values = await _load_cities(session)
    _cached_cities = (time.monotonic(), values)
    return values


@router.get("/offers")
async def search_offers(
    service_name: str = Query(...),
    city: str | None = None,
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    limit: int = Query(default=30, ge=1, le=100),
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OffersResponse:
    """Шаги 2–3: кто оказывает услугу, где, за сколько и когда ближайшее время.

    Сортировка: сначала те, у кого есть свободное время (ближайшее выше),
    при переданных координатах — по расстоянию.
    """
    now = datetime.now(UTC)

    busy_slot = exists().where(
        and_(Appointment.slot_id == Slot.id, Appointment.status == "active")
    )
    free_slot_condition = and_(
        Slot.doctor_id == Doctor.id,
        Slot.service_id == DoctorService.service_id,
        Slot.starts_at > now,
        ~busy_slot,
    )

    stmt = (
        select(
            Doctor.id,
            Doctor.full_name,
            Doctor.specialty,
            DoctorService.service_id,
            Branch.id,
            Branch.name,
            Branch.city,
            Branch.address,
            Branch.latitude,
            Branch.longitude,
            Network.name,
            DoctorService.price,
            func.min(Slot.starts_at).label("next_slot_at"),
            func.count(Slot.id).label("slots_count"),
        )
        .join(DoctorService, DoctorService.doctor_id == Doctor.id)
        .join(Service, Service.id == DoctorService.service_id)
        .join(Branch, Doctor.branch_id == Branch.id)
        .join(Network, Branch.network_id == Network.id)
        .outerjoin(Slot, free_slot_condition)
        .where(
            Service.name == service_name,
            Service.is_active.is_(True),
            Doctor.is_active.is_(True),
            Branch.is_active.is_(True),
            Network.is_active.is_(True),
        )
        .group_by(
            Doctor.id,
            Branch.id,
            Network.id,
            DoctorService.service_id,
            DoctorService.price,
        )
        .order_by(func.min(Slot.starts_at).asc().nulls_last())
        .limit(limit)
    )

    if city:
        stmt = stmt.where(Branch.city == city)

    rows = (await session.execute(stmt)).all()

    offers: list[OfferOut] = []
    for row in rows:
        branch_lat, branch_lng = row[8], row[9]
        distance: float | None = None
        if latitude is not None and longitude is not None and branch_lat and branch_lng:
            distance = round(_distance_km(latitude, longitude, branch_lat, branch_lng), 1)

        offers.append(
            OfferOut(
                doctor_id=row[0],
                doctor_name=row[1],
                specialty=row[2],
                service_id=row[3],
                branch_id=row[4],
                branch_name=row[5],
                city=row[6],
                address=row[7],
                network_name=row[10],
                price=row[11],
                next_slot_at=row[12],
                slots_count=row[13],
                distance_km=distance,
            )
        )

    if latitude is not None and longitude is not None:
        offers.sort(key=lambda offer: (offer.distance_km is None, offer.distance_km or 0.0))

    return OffersResponse(service_name=service_name, offers=offers)
