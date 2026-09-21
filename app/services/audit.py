"""Аудит административных и критичных действий."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, User


def write_audit(
    session: AsyncSession,
    actor: User,
    action: str,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    network_id: uuid.UUID | None = None,
    details: dict[str, object] | None = None,
) -> None:
    """Добавляет запись аудита в текущую транзакцию.

    Фиксация происходит вместе с самой операцией (commit делает вызывающий),
    поэтому аудит не может «отстать» от действия.
    """
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            network_id=network_id,
            details=details or {},
        )
    )
