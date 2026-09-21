"""Генерация слотов из регулярных шаблонов расписания."""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import ScheduleTemplate, Slot


class SchedulingError(Exception):
    """Ошибка расписания — текст можно показывать администратору."""


async def generate_slots_for_template(
    session: AsyncSession,
    template: ScheduleTemplate,
    from_date: date,
    to_date: date,
) -> tuple[int, int]:
    """Генерирует слоты по шаблону на интервал дат включительно.

    Возвращает (создано, пропущено). Пропуски — это слоты, которые
    пересеклись с уже существующими: пересечения врача запрещены в БД,
    поэтому повторная генерация идемпотентна, а не падает.
    """
    if to_date < from_date:
        raise SchedulingError("Конец периода раньше начала")

    service = await session.get(Service, template.service_id)
    if service is None:
        raise SchedulingError("Услуга шаблона не найдена")

    branch = await session.scalar(
        select(Branch)
        .join(Doctor, Doctor.branch_id == Branch.id)
        .where(Doctor.id == template.doctor_id)
    )
    if branch is None:
        raise SchedulingError("Врач шаблона не найден")

    generated = template.generate_slots(
        from_date, to_date, service.duration_minutes, branch.tz()
    )
    if not generated:
        return 0, 0

    rows: list[dict[str, object]] = []
    generated_ids: list[uuid.UUID] = []
    for slot in generated:
        slot_id = uuid.uuid4()
        generated_ids.append(slot_id)
        rows.append(
            {
                "id": slot_id,
                "doctor_id": slot.doctor_id,
                "service_id": slot.service_id,
                "starts_at": slot.starts_at,
                "ends_at": slot.ends_at,
            }
        )

    # ON CONFLICT DO NOTHING без цели: пропускает любые конфликты,
    # включая exclusion constraint на пересечения у врача.
    await session.execute(pg_insert(Slot).values(rows).on_conflict_do_nothing())
    await session.flush()

    inserted = set(
        (
            await session.execute(select(Slot.id).where(Slot.id.in_(generated_ids)))
        ).scalars().all()
    )
    return len(inserted), len(generated_ids) - len(inserted)
