"""Служебные команды Avela: первый администратор и демо-данные.

Работают напрямую с БД (без HTTP и без проверки ролей), поэтому запускать
их должен только оператор — локально или на сервере рядом с `.env`.

    python -m app.cli show-state
    python -m app.cli grant-admin <telegram_id>
    python -m app.cli seed-demo
"""
import argparse
import asyncio
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import exists, func, select

from app.core.roles import ROLE_AVELA_ADMIN
from app.db import get_session_factory
from app.models.appointment import Appointment
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.models.schedule import ScheduleTemplate, Slot
from app.models.user import User
from app.services.scheduling import generate_slots_for_template

DEMO_NETWORK_SLUG = "demo"
DEMO_SERVICE_NAME = "Приём терапевта"
DEMO_DOCTOR_NAME = "Иванов Иван Иванович"
DEMO_BRANCH_NAME = "Центральный филиал"


async def grant_admin(telegram_id: int) -> None:
    """Выдаёт роль администратора Avela.

    Первого администратора иначе не создать: роль не назначается через API,
    и без неё нельзя завести ни одной сети.
    """
    factory = get_session_factory()
    async with factory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            print(
                f"Пользователь telegram_id={telegram_id} не найден.\n"
                "Пусть он один раз войдёт в Mini App (или напишет боту /start), "
                "после этого повтори команду."
            )
            raise SystemExit(1)

        user.role = ROLE_AVELA_ADMIN
        user.is_active = True
        await session.commit()
        print(f"Роль avela_admin выдана: telegram_id={telegram_id}, user_id={user.id}")


async def show_state() -> None:
    """Показывает, что уже есть в базе — чтобы понять, чего не хватает."""
    factory = get_session_factory()
    async with factory() as session:
        users = await session.scalar(select(func.count()).select_from(User))
        networks = await session.scalar(select(func.count()).select_from(Network))
        branches = await session.scalar(select(func.count()).select_from(Branch))
        services = await session.scalar(select(func.count()).select_from(Service))
        doctors = await session.scalar(select(func.count()).select_from(Doctor))
        slots = await session.scalar(select(func.count()).select_from(Slot))
        appointments = await session.scalar(select(func.count()).select_from(Appointment))
        free_slots = await session.scalar(
            select(func.count())
            .select_from(Slot)
            .where(
                Slot.starts_at > datetime.now(UTC),
                ~exists(
                    select(Appointment.id).where(
                        Appointment.slot_id == Slot.id,
                        Appointment.status == "active",
                    )
                ),
            )
        )

        print("Что сейчас в базе:")
        print(f"  пользователи:        {users}")
        print(f"  сети:                {networks}")
        print(f"  филиалы:             {branches}")
        print(f"  услуги:              {services}")
        print(f"  врачи:               {doctors}")
        print(f"  слоты:               {slots}")
        print(f"  записи:              {appointments}")
        print(f"  свободные слоты:     {free_slots}")

        if not free_slots:
            print(
                "\nЗаписаться пока некуда: нет свободных слотов.\n"
                "Запусти `python -m app.cli seed-demo`, чтобы создать демо-данные."
            )


async def seed_demo(days: int = 14) -> None:
    """Создаёт демо-сеть, филиал, услугу, врача и слоты на ближайшие дни.

    Идемпотентно: повторный запуск не дублирует данные, а добирает слоты.
    """
    factory = get_session_factory()
    async with factory() as session:
        network = await session.scalar(
            select(Network).where(Network.slug == DEMO_NETWORK_SLUG)
        )
        if network is None:
            network = Network(slug=DEMO_NETWORK_SLUG, name="Демо-клиника Avela")
            session.add(network)
            await session.flush()
            print(f"Создана сеть: {network.name}")
        else:
            print(f"Сеть уже есть: {network.name}")

        branch = await session.scalar(
            select(Branch).where(
                Branch.network_id == network.id, Branch.name == DEMO_BRANCH_NAME
            )
        )
        if branch is None:
            branch = Branch(
                network_id=network.id,
                name=DEMO_BRANCH_NAME,
                city="Минск",
                region="Минская область",
                address="ул. Примерная, 1",
                phone="+375 17 000-00-00",
                timezone="Europe/Minsk",
            )
            session.add(branch)
            await session.flush()
            print(f"Создан филиал: {branch.name} (timezone={branch.timezone})")

        service = await session.scalar(
            select(Service).where(
                Service.network_id == network.id, Service.name == DEMO_SERVICE_NAME
            )
        )
        if service is None:
            service = Service(
                network_id=network.id,
                name=DEMO_SERVICE_NAME,
                duration_minutes=30,
            )
            session.add(service)
            await session.flush()
            print(f"Создана услуга: {service.name} ({service.duration_minutes} мин)")

        doctor = await session.scalar(
            select(Doctor).where(
                Doctor.branch_id == branch.id, Doctor.full_name == DEMO_DOCTOR_NAME
            )
        )
        if doctor is None:
            doctor = Doctor(
                branch_id=branch.id,
                full_name=DEMO_DOCTOR_NAME,
                specialty="Терапевт",
            )
            session.add(doctor)
            await session.flush()
            session.add(DoctorService(doctor_id=doctor.id, service_id=service.id))
            print(f"Создан врач: {doctor.full_name}")

        today = datetime.now(UTC).date()
        until = today + timedelta(days=max(days, 1) - 1)

        created_total = 0
        skipped_total = 0
        for weekday in range(7):
            template = await session.scalar(
                select(ScheduleTemplate).where(
                    ScheduleTemplate.doctor_id == doctor.id,
                    ScheduleTemplate.service_id == service.id,
                    ScheduleTemplate.weekday == weekday,
                )
            )
            if template is None:
                template = ScheduleTemplate(
                    doctor_id=doctor.id,
                    service_id=service.id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(13, 0),
                    valid_from=today,
                    valid_until=None,
                )
                session.add(template)
                await session.flush()

            created, skipped = await generate_slots_for_template(
                session, template, today, until
            )
            created_total += created
            skipped_total += skipped

        await session.commit()
        print(f"\nСлоты на {days} дн. (09:00–13:00 по времени филиала): {created_total}")
        print(f"Уже были раньше: {skipped_total}")
        print("Готово. Открывай Mini App и пробуй записаться.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Служебные команды Avela",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    grant = subparsers.add_parser(
        "grant-admin", help="Выдать роль администратора Avela по telegram_id"
    )
    grant.add_argument("telegram_id", type=int, help="Telegram ID пользователя")

    subparsers.add_parser("show-state", help="Показать, что есть в базе")

    seed = subparsers.add_parser(
        "seed-demo", help="Создать демо-сеть, филиал, услугу, врача и слоты"
    )
    seed.add_argument("--days", type=int, default=14, help="На сколько дней вперёд")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "grant-admin":
        asyncio.run(grant_admin(args.telegram_id))
    elif args.command == "show-state":
        asyncio.run(show_state())
    elif args.command == "seed-demo":
        asyncio.run(seed_demo(args.days))


if __name__ == "__main__":
    main()
