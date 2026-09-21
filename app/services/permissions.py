"""Границы видимости администраторов (tenant isolation).

Правило: администратор ниже по иерархии не видит и не изменяет данные
чужой сети/филиала. Проверка выполняется на backend для каждого действия;
скрытие кнопок во frontend ничего не гарантирует.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import ROLE_AVELA_ADMIN, ROLE_NETWORK_ADMIN
from app.models.catalog import Branch
from app.models.user import BranchAdmin, User


async def scoped_branch_ids(session: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """Филиалы, доступные администратору.

    None — без ограничений (администратор Avela). Пустое множество —
    доступа нет ни к одному филиалу.
    """
    if user.role == ROLE_AVELA_ADMIN:
        return None

    if user.role == ROLE_NETWORK_ADMIN:
        if user.network_id is None:
            return set()
        rows = await session.execute(
            select(Branch.id).where(Branch.network_id == user.network_id)
        )
        return set(rows.scalars().all())

    rows = await session.execute(
        select(BranchAdmin.branch_id).where(BranchAdmin.user_id == user.id)
    )
    return set(rows.scalars().all())


async def scoped_network_ids(session: AsyncSession, user: User) -> set[uuid.UUID] | None:
    """Сети, данные которых администратор может видеть. None — без ограничений."""
    if user.role == ROLE_AVELA_ADMIN:
        return None

    if user.role == ROLE_NETWORK_ADMIN:
        return {user.network_id} if user.network_id is not None else set()

    rows = await session.execute(
        select(Branch.network_id)
        .join(BranchAdmin, BranchAdmin.branch_id == Branch.id)
        .where(BranchAdmin.user_id == user.id)
    )
    return set(rows.scalars().all())


def can_access_branch(allowed: set[uuid.UUID] | None, branch_id: uuid.UUID) -> bool:
    return allowed is None or branch_id in allowed


def can_access_network(allowed: set[uuid.UUID] | None, network_id: uuid.UUID) -> bool:
    return allowed is None or network_id in allowed


def can_manage_network(user: User, network_id: uuid.UUID) -> bool:
    """Право изменять сеть (создавать филиалы и услуги): только своя сеть."""
    if user.role == ROLE_AVELA_ADMIN:
        return True
    return user.role == ROLE_NETWORK_ADMIN and user.network_id == network_id
