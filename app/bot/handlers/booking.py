"""Запись на приём прямо в чате бота.

Хэндлеры не содержат бизнес-логики: только собирают выбор пользователя
и вызывают сервисный слой (app.services.booking).
"""
import logging
import uuid
from collections.abc import Sequence

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from app.bot.formatting import format_booked_message
from app.bot.helpers import (
    build_slots_keyboard,
    fetch_free_slots,
    get_bot_user,
    parse_uuid,
)
from app.bot.keyboards.main_menu import get_main_menu
from app.db import get_session_factory
from app.models.catalog import Branch, Doctor, DoctorService, Network, Service
from app.services.booking import (
    BookingError,
    SlotUnavailableError,
    book_slot,
    get_appointment_context,
)

logger = logging.getLogger(__name__)

router = Router(name=__name__)


class BookingStates(StatesGroup):
    choosing_network = State()
    choosing_service = State()
    choosing_branch = State()
    choosing_doctor = State()
    choosing_slot = State()


@router.message(F.text == "🏥 Записаться на приём")
async def start_booking(message: Message, state: FSMContext) -> None:
    user = await get_bot_user(message)
    if user is None:
        return
    await state.clear()

    factory = get_session_factory()
    async with factory() as session:
        networks = (
            await session.execute(
                select(Network)
                .where(Network.is_active.is_(True))
                .order_by(Network.name)
            )
        ).scalars().all()

    if not networks:
        await message.answer(
            "Пока в базе нет ни одной клиники — загляните позже.",
            reply_markup=get_main_menu(),
        )
        return

    await state.set_state(BookingStates.choosing_network)
    await message.answer("Выберите клинику:", reply_markup=_network_keyboard(networks))


@router.callback_query(BookingStates.choosing_network, F.data.startswith("net:"))
async def choose_network(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message is None:
        return

    network_id = parse_uuid(callback.data or "", "net:")
    if network_id is None:
        await callback.message.answer("Некорректные данные — начните заново.")
        await state.clear()
        return

    factory = get_session_factory()
    async with factory() as session:
        network = await session.get(Network, network_id)
        if network is None or not network.is_active:
            await callback.message.answer("Эта клиника больше недоступна.")
            await state.clear()
            return

        services = (
            await session.execute(
                select(Service)
                .where(Service.network_id == network.id, Service.is_active.is_(True))
                .order_by(Service.name)
            )
        ).scalars().all()
        branches = (
            await session.execute(
                select(Branch)
                .where(Branch.network_id == network.id, Branch.is_active.is_(True))
                .order_by(Branch.name)
            )
        ).scalars().all()

    if not services:
        await callback.message.answer(
            "У этой клиники пока нет услуг — загляните позже.",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return
    if not branches:
        await callback.message.answer(
            "У этой клиники пока нет филиалов — загляните позже.",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return

    await state.update_data(network_id=str(network_id))
    await state.set_state(BookingStates.choosing_service)
    await callback.message.answer(
        "Выберите услугу:", reply_markup=_service_keyboard(services)
    )


@router.callback_query(BookingStates.choosing_service, F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message is None:
        return

    service_id = parse_uuid(callback.data or "", "svc:")
    if service_id is None:
        await callback.message.answer("Некорректные данные — начните заново.")
        await state.clear()
        return

    data = await state.get_data()
    network_id = uuid.UUID(str(data.get("network_id")))

    factory = get_session_factory()
    async with factory() as session:
        service = await session.get(Service, service_id)
        if service is None or service.network_id != network_id:
            await callback.message.answer("Услуга не найдена. Начните заново.")
            await state.clear()
            return

        branches = (
            await session.execute(
                select(Branch)
                .where(Branch.network_id == network_id, Branch.is_active.is_(True))
                .order_by(Branch.name)
            )
        ).scalars().all()

    if not branches:
        await callback.message.answer(
            "У этой клиники пока нет филиалов — загляните позже.",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return

    await state.update_data(service_id=str(service_id))
    await state.set_state(BookingStates.choosing_branch)
    await callback.message.answer(
        "Выберите филиал:", reply_markup=_branch_keyboard(branches)
    )


@router.callback_query(BookingStates.choosing_branch, F.data.startswith("br:"))
async def choose_branch(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message is None:
        return

    branch_id = parse_uuid(callback.data or "", "br:")
    if branch_id is None:
        await callback.message.answer("Некорректные данные — начните заново.")
        await state.clear()
        return

    data = await state.get_data()
    service_id = uuid.UUID(str(data.get("service_id")))

    factory = get_session_factory()
    async with factory() as session:
        branch = await session.get(Branch, branch_id)
        if branch is None or not branch.is_active:
            await callback.message.answer("Филиал не найден. Начните заново.")
            await state.clear()
            return

        doctors = (
            await session.execute(
                select(Doctor)
                .join(DoctorService, DoctorService.doctor_id == Doctor.id)
                .where(
                    Doctor.branch_id == branch.id,
                    Doctor.is_active.is_(True),
                    DoctorService.service_id == service_id,
                )
                .order_by(Doctor.full_name)
            )
        ).scalars().all()

    await state.update_data(branch_id=str(branch_id))
    await state.set_state(BookingStates.choosing_doctor)
    await callback.message.answer(
        "Выберите врача (или доверьтесь нам — «Любой свободный врач»):",
        reply_markup=_doctor_keyboard(doctors),
    )


@router.callback_query(BookingStates.choosing_doctor, F.data.startswith("doc:"))
async def choose_doctor(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message is None:
        return

    raw = (callback.data or "").removeprefix("doc:")
    doctor_id: uuid.UUID | None = None
    if raw != "any":
        doctor_id = parse_uuid(raw, "")
        if doctor_id is None:
            await callback.message.answer("Некорректные данные — начните заново.")
            await state.clear()
            return

    await state.update_data(doctor_id=str(doctor_id) if doctor_id else None)
    await state.set_state(BookingStates.choosing_slot)

    data = await state.get_data()
    raw_service = data.get("service_id")
    raw_branch = data.get("branch_id")
    if not raw_service or not raw_branch:
        await callback.message.answer(
            "Данные выбора устарели — начните заново.", reply_markup=get_main_menu()
        )
        await state.clear()
        return
    service_id = uuid.UUID(str(raw_service))
    branch_id = uuid.UUID(str(raw_branch))

    slots, timezone_name = await fetch_free_slots(service_id, branch_id, doctor_id)
    if not slots:
        await callback.message.answer(
            "Свободных слотов на ближайшие две недели нет.\n"
            "Попробуйте другого врача или загляните позже.",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return

    await callback.message.answer(
        f"Ближайшие свободные слоты (показаны первые {len(slots)}):",
        reply_markup=build_slots_keyboard(slots, timezone_name),
    )


@router.callback_query(BookingStates.choosing_slot, F.data.startswith("slot:"))
async def choose_slot(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return

    user = await get_bot_user(callback)
    if user is None:
        return

    slot_id = parse_uuid(callback.data or "", "slot:")
    if slot_id is None:
        await callback.answer("Некорректные данные слота.", show_alert=True)
        return

    factory = get_session_factory()
    async with factory() as session:
        try:
            appointment = await book_slot(session, user, slot_id)
        except SlotUnavailableError as exc:
            await callback.answer(str(exc), show_alert=True)
            data = await state.get_data()
            raw_service = data.get("service_id")
            raw_branch = data.get("branch_id")
            if raw_service and raw_branch:
                service_id = uuid.UUID(str(raw_service))
                branch_id = uuid.UUID(str(raw_branch))
                doctor_raw = data.get("doctor_id")
                doctor_id = uuid.UUID(str(doctor_raw)) if doctor_raw else None
                slots, timezone_name = await fetch_free_slots(
                    service_id, branch_id, doctor_id
                )
                if not slots:
                    await callback.message.answer("Свободных слотов больше нет.")
                    await state.clear()
                else:
                    await callback.message.answer(
                        "Этот слот только что заняли. Выберите другой:",
                        reply_markup=build_slots_keyboard(slots, timezone_name),
                    )
            else:
                await state.clear()
                await callback.message.answer(
                    "Начните заново.", reply_markup=get_main_menu()
                )
            return
        except BookingError as exc:
            await callback.answer(str(exc), show_alert=True)
            await state.clear()
            return

        context = await get_appointment_context(session, user.id, appointment.id)
        if context is None:
            await callback.answer("Не удалось получить детали записи.", show_alert=True)
            await state.clear()
            return
        _appointment, slot, doctor, service, branch = context
        text = format_booked_message(slot, doctor, service, branch)

    await state.clear()
    await callback.answer("Вы записаны!")
    await callback.message.answer(text, reply_markup=get_main_menu())


@router.message(F.text == "❌ Отменить действие")
async def cancel_flow(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer(
            "Сейчас нет активного действия — вы в главном меню.",
            reply_markup=get_main_menu(),
        )
        return

    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


def _network_keyboard(networks: Sequence[Network]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=network.name, callback_data=f"net:{network.id}")]
            for network in networks
        ]
    )


def _service_keyboard(services: Sequence[Service]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=service.name, callback_data=f"svc:{service.id}")]
            for service in services
        ]
    )


def _branch_keyboard(branches: Sequence[Branch]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=branch.name, callback_data=f"br:{branch.id}")]
            for branch in branches
        ]
    )


def _doctor_keyboard(doctors: Sequence[Doctor]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🙋 Любой свободный врач", callback_data="doc:any")]
    ]
    rows.extend(
        [InlineKeyboardButton(text=doctor.full_name, callback_data=f"doc:{doctor.id}")]
        for doctor in doctors
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
