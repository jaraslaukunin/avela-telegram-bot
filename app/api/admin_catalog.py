"""Административный API: сети, филиалы, услуги, врачи, расписание и слоты.

Права проверяются здесь, на backend, для каждого действия.
Ресурсы вне зоны видимости администратора отдают 404, чтобы не раскрывать
существование чужих данных.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.rate_limit import RateLimiter
from app.core.roles import (
    ADMIN_ROLES,
    ROLE_AVELA_ADMIN,
    ROLE_BRANCH_ADMIN,
    ROLE_NETWORK_ADMIN,
    ROLE_PATIENT,
)
from app.db import get_session
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.schedule import ScheduleTemplate
from app.models.user import BranchAdmin, User
from app.schemas import (
    BranchAdminAssign,
    BranchCreate,
    BranchOut,
    BranchUpdate,
    DoctorCreate,
    DoctorOut,
    DoctorServicesUpdate,
    DoctorUpdate,
    NetworkCreate,
    NetworkOut,
    NetworkUpdate,
    ScheduleTemplateCreate,
    ScheduleTemplateOut,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    SlotGenerationRequest,
    SlotGenerationResult,
)
from app.services import audit, permissions
from app.services.scheduling import SchedulingError, generate_slots_for_template

AdminCatalogRateLimit = RateLimiter(limit=120)

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(AdminCatalogRateLimit)]
)

AdminUser = Annotated[User, Depends(require_roles(*ADMIN_ROLES))]
AvelaAdminUser = Annotated[User, Depends(require_roles(ROLE_AVELA_ADMIN))]
NetworkAdminUser = Annotated[User, Depends(require_roles(ROLE_NETWORK_ADMIN, ROLE_AVELA_ADMIN))]
DbSession = Annotated[AsyncSession, Depends(get_session)]


async def _network_or_404(session: AsyncSession, user: User, network_id: uuid.UUID) -> Network:
    network = await session.get(Network, network_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Сеть не найдена")

    allowed = await permissions.scoped_network_ids(session, user)
    if not permissions.can_access_network(allowed, network.id):
        raise HTTPException(status_code=404, detail="Сеть не найдена")
    return network


async def _branch_or_404(session: AsyncSession, user: User, branch_id: uuid.UUID) -> Branch:
    branch = await session.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    allowed = await permissions.scoped_branch_ids(session, user)
    if not permissions.can_access_branch(allowed, branch.id):
        raise HTTPException(status_code=404, detail="Филиал не найден")
    return branch


async def _doctor_or_404(session: AsyncSession, user: User, doctor_id: uuid.UUID) -> Doctor:
    doctor = await session.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Врач не найден")
    await _branch_or_404(session, user, doctor.branch_id)
    return doctor


async def _service_or_404(session: AsyncSession, user: User, service_id: uuid.UUID) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    allowed = await permissions.scoped_network_ids(session, user)
    if not permissions.can_access_network(allowed, service.network_id):
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return service


async def _validate_services_for_branch(
    session: AsyncSession, branch: Branch, service_ids: list[uuid.UUID]
) -> None:
    """Все услуги врача должны принадлежать сети его филиала."""
    if not service_ids:
        return

    rows = await session.execute(
        select(Service.id).where(
            Service.id.in_(service_ids), Service.network_id == branch.network_id
        )
    )
    found = set(rows.scalars().all())
    missing = [str(service_id) for service_id in service_ids if service_id not in found]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Услуги не найдены в сети филиала: {', '.join(missing)}",
        )


# --- Сети ---


@router.post("/networks", status_code=201)
async def create_network(
    payload: NetworkCreate, current: AvelaAdminUser, session: DbSession
) -> NetworkOut:
    network = Network(slug=payload.slug, name=payload.name)
    session.add(network)

    try:
        await session.flush()
        audit.write_audit(
            session,
            current,
            "network.create",
            entity_type="network",
            entity_id=network.id,
            network_id=network.id,
            details={"slug": payload.slug},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Сеть с таким slug уже есть") from exc

    return NetworkOut.model_validate(network)


@router.get("/networks")
async def list_networks(current: AdminUser, session: DbSession) -> list[NetworkOut]:
    allowed = await permissions.scoped_network_ids(session, current)
    stmt = select(Network).order_by(Network.name)
    if allowed is not None:
        stmt = stmt.where(Network.id.in_(allowed))

    networks = (await session.execute(stmt)).scalars().all()
    return [NetworkOut.model_validate(network) for network in networks]


@router.patch("/networks/{network_id}")
async def update_network(
    network_id: uuid.UUID, payload: NetworkUpdate, current: AdminUser, session: DbSession
) -> NetworkOut:
    network = await _network_or_404(session, current, network_id)

    if payload.is_active is not None:
        if current.role != ROLE_AVELA_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Активация и блокировка сети — только администратор Avela",
            )
        network.is_active = payload.is_active

    if payload.name is not None:
        if not permissions.can_manage_network(current, network.id):
            raise HTTPException(status_code=403, detail="Нет прав на изменение этой сети")
        network.name = payload.name

    audit.write_audit(
        session,
        current,
        "network.update",
        entity_type="network",
        entity_id=network.id,
        network_id=network.id,
    )
    await session.commit()
    return NetworkOut.model_validate(network)


# --- Филиалы ---


@router.post("/networks/{network_id}/branches", status_code=201)
async def create_branch(
    network_id: uuid.UUID,
    payload: BranchCreate,
    current: NetworkAdminUser,
    session: DbSession,
) -> BranchOut:
    network = await session.get(Network, network_id)
    if network is None or not permissions.can_manage_network(current, network_id):
        raise HTTPException(status_code=404, detail="Сеть не найдена")

    branch = Branch(network_id=network_id, **payload.model_dump())
    session.add(branch)

    try:
        await session.flush()
        audit.write_audit(
            session,
            current,
            "branch.create",
            entity_type="branch",
            entity_id=branch.id,
            network_id=network_id,
            details={"name": payload.name, "timezone": payload.timezone},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Филиал с таким названием уже есть в сети"
        ) from exc

    return BranchOut.model_validate(branch)


@router.get("/branches")
async def list_branches(
    current: AdminUser,
    session: DbSession,
    network_id: uuid.UUID | None = None,
) -> list[BranchOut]:
    allowed = await permissions.scoped_branch_ids(session, current)
    stmt = select(Branch).order_by(Branch.name)
    if allowed is not None:
        stmt = stmt.where(Branch.id.in_(allowed))
    if network_id is not None:
        stmt = stmt.where(Branch.network_id == network_id)

    branches = (await session.execute(stmt)).scalars().all()
    return [BranchOut.model_validate(branch) for branch in branches]


@router.patch("/branches/{branch_id}")
async def update_branch(
    branch_id: uuid.UUID, payload: BranchUpdate, current: AdminUser, session: DbSession
) -> BranchOut:
    branch = await _branch_or_404(session, current, branch_id)

    changes = payload.model_dump(exclude_unset=True)
    if "timezone" in changes and not permissions.can_manage_network(current, branch.network_id):
        raise HTTPException(
            status_code=403,
            detail="Смена часового пояса филиала — только администратор сети",
        )

    for field_name, value in changes.items():
        setattr(branch, field_name, value)

    audit.write_audit(
        session,
        current,
        "branch.update",
        entity_type="branch",
        entity_id=branch.id,
        network_id=branch.network_id,
        details={"fields": sorted(changes)},
    )
    await session.commit()
    return BranchOut.model_validate(branch)


@router.post("/branches/{branch_id}/admins", status_code=204)
async def assign_branch_admin(
    branch_id: uuid.UUID,
    payload: BranchAdminAssign,
    current: NetworkAdminUser,
    session: DbSession,
) -> Response:
    branch = await _branch_or_404(session, current, branch_id)
    if not permissions.can_manage_network(current, branch.network_id):
        raise HTTPException(
            status_code=403,
            detail="Назначать администраторов филиала может администратор сети",
        )

    user = await session.scalar(select(User).where(User.telegram_id == payload.telegram_id))
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден: ему нужно сначала войти в бота",
        )

    if user.role == ROLE_PATIENT:
        user.role = ROLE_BRANCH_ADMIN

    existing = await session.scalar(
        select(BranchAdmin).where(
            BranchAdmin.user_id == user.id, BranchAdmin.branch_id == branch.id
        )
    )
    if existing is None:
        session.add(BranchAdmin(user_id=user.id, branch_id=branch.id))

    audit.write_audit(
        session,
        current,
        "branch.admin.assign",
        entity_type="branch",
        entity_id=branch.id,
        network_id=branch.network_id,
        details={"telegram_id": payload.telegram_id},
    )
    await session.commit()
    return Response(status_code=204)


# --- Услуги ---


@router.post("/networks/{network_id}/services", status_code=201)
async def create_service(
    network_id: uuid.UUID,
    payload: ServiceCreate,
    current: NetworkAdminUser,
    session: DbSession,
) -> ServiceOut:
    network = await session.get(Network, network_id)
    if network is None or not permissions.can_manage_network(current, network_id):
        raise HTTPException(status_code=404, detail="Сеть не найдена")

    service = Service(network_id=network_id, **payload.model_dump())
    session.add(service)

    try:
        await session.flush()
        audit.write_audit(
            session,
            current,
            "service.create",
            entity_type="service",
            entity_id=service.id,
            network_id=network_id,
            details={"name": payload.name, "duration_minutes": payload.duration_minutes},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Такая услуга уже есть в сети") from exc

    return ServiceOut.model_validate(service)


@router.get("/services")
async def list_services(
    current: AdminUser,
    session: DbSession,
    network_id: uuid.UUID | None = None,
) -> list[ServiceOut]:
    allowed = await permissions.scoped_network_ids(session, current)
    stmt = select(Service).order_by(Service.name)
    if allowed is not None:
        stmt = stmt.where(Service.network_id.in_(allowed))
    if network_id is not None:
        stmt = stmt.where(Service.network_id == network_id)

    services = (await session.execute(stmt)).scalars().all()
    return [ServiceOut.model_validate(service) for service in services]


@router.patch("/services/{service_id}")
async def update_service(
    service_id: uuid.UUID, payload: ServiceUpdate, current: NetworkAdminUser, session: DbSession
) -> ServiceOut:
    service = await _service_or_404(session, current, service_id)
    if not permissions.can_manage_network(current, service.network_id):
        raise HTTPException(status_code=403, detail="Нет прав на изменение этой услуги")

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field_name, value)

    audit.write_audit(
        session,
        current,
        "service.update",
        entity_type="service",
        entity_id=service.id,
        network_id=service.network_id,
    )
    await session.commit()
    return ServiceOut.model_validate(service)


# --- Врачи ---


@router.post("/branches/{branch_id}/doctors", status_code=201)
async def create_doctor(
    branch_id: uuid.UUID, payload: DoctorCreate, current: AdminUser, session: DbSession
) -> DoctorOut:
    branch = await _branch_or_404(session, current, branch_id)
    await _validate_services_for_branch(session, branch, payload.service_ids)

    doctor = Doctor(
        branch_id=branch.id, full_name=payload.full_name, specialty=payload.specialty
    )
    session.add(doctor)
    await session.flush()

    for service_id in payload.service_ids:
        session.add(DoctorService(doctor_id=doctor.id, service_id=service_id))

    audit.write_audit(
        session,
        current,
        "doctor.create",
        entity_type="doctor",
        entity_id=doctor.id,
        network_id=branch.network_id,
        details={"full_name": payload.full_name},
    )
    await session.commit()
    return DoctorOut.model_validate(doctor)


@router.get("/branches/{branch_id}/doctors")
async def list_doctors(
    branch_id: uuid.UUID, current: AdminUser, session: DbSession
) -> list[DoctorOut]:
    branch = await _branch_or_404(session, current, branch_id)
    doctors = (
        await session.execute(
            select(Doctor).where(Doctor.branch_id == branch.id).order_by(Doctor.full_name)
        )
    ).scalars().all()
    return [DoctorOut.model_validate(doctor) for doctor in doctors]


@router.patch("/doctors/{doctor_id}")
async def update_doctor(
    doctor_id: uuid.UUID, payload: DoctorUpdate, current: AdminUser, session: DbSession
) -> DoctorOut:
    doctor = await _doctor_or_404(session, current, doctor_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field_name, value)

    audit.write_audit(
        session,
        current,
        "doctor.update",
        entity_type="doctor",
        entity_id=doctor.id,
        network_id=(await _branch_or_404(session, current, doctor.branch_id)).network_id,
    )
    await session.commit()
    return DoctorOut.model_validate(doctor)


@router.put("/doctors/{doctor_id}/services")
async def set_doctor_services(
    doctor_id: uuid.UUID,
    payload: DoctorServicesUpdate,
    current: AdminUser,
    session: DbSession,
) -> list[ServiceOut]:
    doctor = await _doctor_or_404(session, current, doctor_id)
    branch = await _branch_or_404(session, current, doctor.branch_id)
    await _validate_services_for_branch(session, branch, payload.service_ids)

    existing = (
        await session.execute(
            select(DoctorService).where(DoctorService.doctor_id == doctor.id)
        )
    ).scalars().all()
    for link in existing:
        await session.delete(link)

    for service_id in payload.service_ids:
        session.add(DoctorService(doctor_id=doctor.id, service_id=service_id))

    audit.write_audit(
        session,
        current,
        "doctor.services.update",
        entity_type="doctor",
        entity_id=doctor.id,
        network_id=branch.network_id,
        details={"service_ids": [str(service_id) for service_id in payload.service_ids]},
    )
    await session.commit()

    if not payload.service_ids:
        return []
    services = (
        await session.execute(
            select(Service)
            .where(Service.id.in_(payload.service_ids))
            .order_by(Service.name)
        )
    ).scalars().all()
    return [ServiceOut.model_validate(service) for service in services]


# --- Расписание и слоты ---


@router.post("/doctors/{doctor_id}/schedule-templates", status_code=201)
async def create_schedule_template(
    doctor_id: uuid.UUID,
    payload: ScheduleTemplateCreate,
    current: AdminUser,
    session: DbSession,
) -> ScheduleTemplateOut:
    doctor = await _doctor_or_404(session, current, doctor_id)
    branch = await _branch_or_404(session, current, doctor.branch_id)
    await _validate_services_for_branch(session, branch, [payload.service_id])

    template = ScheduleTemplate(
        doctor_id=doctor.id,
        service_id=payload.service_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    session.add(template)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Некорректный шаблон расписания") from exc

    audit.write_audit(
        session,
        current,
        "schedule.template.create",
        entity_type="schedule_template",
        entity_id=template.id,
        network_id=branch.network_id,
        details={"weekday": payload.weekday},
    )
    await session.commit()
    return ScheduleTemplateOut.model_validate(template)


@router.post("/schedule-templates/{template_id}/generate-slots")
async def generate_slots(
    template_id: uuid.UUID,
    payload: SlotGenerationRequest,
    current: AdminUser,
    session: DbSession,
) -> SlotGenerationResult:
    template = await session.get(ScheduleTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    doctor = await _doctor_or_404(session, current, template.doctor_id)
    branch = await _branch_or_404(session, current, doctor.branch_id)

    try:
        created, skipped = await generate_slots_for_template(
            session, template, payload.from_date, payload.to_date
        )
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit.write_audit(
        session,
        current,
        "schedule.slots.generate",
        entity_type="schedule_template",
        entity_id=template.id,
        network_id=branch.network_id,
        details={
            "from": payload.from_date.isoformat(),
            "to": payload.to_date.isoformat(),
            "created": created,
            "skipped": skipped,
        },
    )
    await session.commit()
    return SlotGenerationResult(created=created, skipped=skipped)
