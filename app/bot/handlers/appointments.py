"""Мои записи: список, отмена, перенос — прямо в чате."""
import logging
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.formatting import (
    format_appointment_card,
    format_rescheduled_message,
)
from app.bot.helpers import (
    build_slots_keyboard,
    fetch_free_slots,
    get_bot_user,
    parse_uuid,
    show_step,
)
from app.bot.keyboards.main_menu import get_main_menu
from app.db import get_session_factory
from app.services.booking import (
    AppointmentNotFoundError,
    BookingError,
    DeadlinePassedError,
    SlotUnavailableError,
    cancel_appointment,
    get_appointment_context,
    list_patient_appointments,
    reschedule_appointment,
)

logger = logging.getLogger(__name__)

router = Router(name=__name__)


class RescheduleStates(StatesGroup):
    choosing_new_slot = State()


@router.message(F.text == "📋 Мои записи")
async def show_appointments(message: Message) -> None:
    user = await get_bot_user(message)
    if user is None:
        return

    factory = get_session_factory()
    async with factory() as session:
        rows = await list_patient_appointments(session, user.id)

    if not rows:
        await message.answer(
            "У вас пока нет записей.\n\n"
            "Чтобы записаться, нажмите «🏥 Записаться на приём».",
            reply_markup=get_main_menu(),
        )
        return

    await message.answer("Ваши записи (активные вверху):")
    for appointment, slot, doctor, service, branch in rows:
        status = "" if appointment.is_active else f"\nСтатус: {appointment.status}"
        keyboard = _appointment_keyboard(appointment.id) if appointment.is_active else None
        await message.answer(
            format_appointment_card(slot, doctor, service, branch) + status,
            reply_markup=keyboard,
        )


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_appointment_callback(callback: CallbackQuery) -> None:
    if callback.message is None:
        return

    user = await get_bot_user(callback)
    if user is None:
        return

    appointment_id = parse_uuid(callback.data or "", "cancel:")
    if appointment_id is None:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    factory = get_session_factory()
    async with factory() as session:
        try:
            await cancel_appointment(session, user.id, appointment_id)
        except AppointmentNotFoundError:
            await callback.answer("Запись не найдена.", show_alert=True)
            return
        except DeadlinePassedError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        except BookingError as exc:
            await callback.answer(str(exc), show_alert=True)
            return

    await callback.answer("Запись отменена.")
    await show_step(callback, "✅ Запись отменена.")


@router.callback_query(F.data.startswith("move:"))
async def start_reschedule(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return

    user = await get_bot_user(callback)
    if user is None:
        return

    appointment_id = parse_uuid(callback.data or "", "move:")
    if appointment_id is None:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    factory = get_session_factory()
    async with factory() as session:
        context = await get_appointment_context(session, user.id, appointment_id)
        if context is None:
            await callback.answer("Запись не найдена.", show_alert=True)
            return
        appointment, _slot, doctor, service, branch = context
        slots, timezone_name = await fetch_free_slots(
            service.id, branch.id, doctor.id
        )

    if not slots:
        await callback.answer(
            "Для переноса нет свободных слотов у этого врача — попробуйте позже.",
            show_alert=True,
        )
        return

    await state.update_data(appointment_id=str(appointment_id))
    await state.set_state(RescheduleStates.choosing_new_slot)
    await show_step(
        callback,
        "Выберите новое время (тот же врач и услуга):",
        build_slots_keyboard(slots, timezone_name),
    )


@router.callback_query(
    RescheduleStates.choosing_new_slot, F.data.startswith("slot:")
)
async def choose_new_slot(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return

    user = await get_bot_user(callback)
    if user is None:
        return

    slot_id = parse_uuid(callback.data or "", "slot:")
    if slot_id is None:
        await callback.answer("Некорректные данные слота.", show_alert=True)
        return

    data = await state.get_data()
    appointment_raw = data.get("appointment_id")
    if appointment_raw is None:
        await callback.answer("Сессия переноса устарела — начните заново.", show_alert=True)
        await state.clear()
        return
    appointment_id = uuid.UUID(str(appointment_raw))

    factory = get_session_factory()
    async with factory() as session:
        try:
            new_appointment = await reschedule_appointment(
                session, user.id, appointment_id, slot_id
            )
        except AppointmentNotFoundError as exc:
            await callback.answer(str(exc), show_alert=True)
            await state.clear()
            return
        except DeadlinePassedError as exc:
            await callback.answer(str(exc), show_alert=True)
            await state.clear()
            return
        except (SlotUnavailableError, BookingError) as exc:
            await callback.answer(str(exc), show_alert=True)
            await state.clear()
            return

        context = await get_appointment_context(session, user.id, new_appointment.id)
        if context is None:
            await callback.answer("Не удалось получить детали записи.", show_alert=True)
            await state.clear()
            return
        _appointment, new_slot, doctor, service, branch = context
        text = format_rescheduled_message(new_slot, doctor, service, branch)

    await state.clear()
    await callback.answer("Запись перенесена!")
    await show_step(callback, text)


def _appointment_keyboard(appointment_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=f"cancel:{appointment_id}"
                ),
                InlineKeyboardButton(
                    text="🔄 Перенести", callback_data=f"move:{appointment_id}"
                ),
            ]
        ]
    )
