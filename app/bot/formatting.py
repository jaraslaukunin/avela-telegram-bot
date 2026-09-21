"""Форматирование сообщений бота — чистые функции, тестируются без БД."""
from app.models.catalog import Branch, Doctor, Service
from app.models.schedule import Slot
from app.services.notifications import format_local_time


def slot_button_label(slot: Slot, timezone_name: str) -> str:
    """Кнопка слота: «25.09 12:00» (время клиники)."""
    date_part, time_part = format_local_time(slot.starts_at, timezone_name).split(" ", 1)
    return f"{date_part.rsplit('.', 1)[0]} {time_part}"


def format_booked_message(slot: Slot, doctor: Doctor, service: Service, branch: Branch) -> str:
    """Подтверждение записи."""
    when = format_local_time(slot.starts_at, branch.timezone)
    return (
        "✅ <b>Вы записаны!</b>\n\n"
        f"{service.name}, {doctor.full_name}\n"
        f"{branch.name}\n"
        f"🗓 {when} (время клиники)\n\n"
        "Напомним за 24 часа и за 2 часа до приёма.\n"
        "Отменить или перенести запись можно не позднее чем за 2 часа до приёма."
    )


def format_rescheduled_message(
    slot: Slot, doctor: Doctor, service: Service, branch: Branch
) -> str:
    """Подтверждение переноса записи."""
    when = format_local_time(slot.starts_at, branch.timezone)
    return (
        "🔄 <b>Запись перенесена</b>\n\n"
        f"{service.name}, {doctor.full_name}\n"
        f"{branch.name}\n"
        f"🗓 {when} (время клиники)\n\n"
        "Напомним за 24 часа и за 2 часа до приёма."
    )


def format_appointment_card(
    slot: Slot, doctor: Doctor, service: Service, branch: Branch
) -> str:
    """Карточка записи в «Моих записях»."""
    when = format_local_time(slot.starts_at, branch.timezone)
    where = f"{branch.name}, {branch.address}" if branch.address else branch.name
    phone = f"\nТел.: {branch.phone}" if branch.phone else ""
    return (
        f"🗓 <b>{when}</b> (время клиники)\n"
        f"{service.name} — {doctor.full_name}\n"
        f"{where}{phone}"
    )
