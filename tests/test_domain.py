import uuid
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.models.appointment import Appointment
from app.models.catalog import Branch
from app.models.schedule import ScheduleTemplate, Slot
from app.models.user import User


def test_branch_cancel_deadline_in_moscow_tz() -> None:
    branch = Branch(name="Филиал", timezone="Europe/Moscow")
    starts_at = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)  # 15:00 в Москве

    deadline = branch.cancel_deadline(starts_at, deadline_hours=2)

    assert deadline == datetime(2026, 9, 25, 10, 0, tzinfo=UTC)  # 13:00 в Москве


def test_branch_local_to_utc() -> None:
    branch = Branch(name="Филиал", timezone="Europe/Moscow")

    utc = branch.local_to_utc(datetime(2026, 9, 25, 9, 0))

    assert utc == datetime(2026, 9, 25, 6, 0, tzinfo=UTC)


def test_generate_slots_respects_weekday_and_timezone() -> None:
    template = ScheduleTemplate(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        weekday=0,  # понедельник
        start_time=time(9, 0),
        end_time=time(10, 0),
        valid_from=date(2026, 9, 21),
        valid_until=None,
    )

    slots = template.generate_slots(
        from_date=date(2026, 9, 21),
        to_date=date(2026, 9, 27),
        duration_minutes=30,
        tz=ZoneInfo("Europe/Moscow"),
    )

    # 2026-09-21 — понедельник; в интервал попадает ровно один рабочий день.
    assert len(slots) == 2
    assert slots[0].starts_at == datetime(2026, 9, 21, 6, 0, tzinfo=UTC)
    assert slots[0].ends_at == datetime(2026, 9, 21, 6, 30, tzinfo=UTC)
    assert slots[1].starts_at == datetime(2026, 9, 21, 6, 30, tzinfo=UTC)
    assert slots[0].doctor_id == template.doctor_id
    assert slots[0].service_id == template.service_id


def test_generate_slots_respects_valid_until() -> None:
    template = ScheduleTemplate(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        weekday=0,
        start_time=time(9, 0),
        end_time=time(9, 30),
        valid_from=date(2026, 9, 21),
        valid_until=date(2026, 9, 21),
    )

    slots = template.generate_slots(
        from_date=date(2026, 9, 21),
        to_date=date(2026, 10, 21),
        duration_minutes=30,
        tz=ZoneInfo("Europe/Moscow"),
    )

    assert len(slots) == 1


def test_slot_overlaps() -> None:
    base = Slot(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        starts_at=datetime(2026, 9, 25, 10, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 10, 30, tzinfo=UTC),
    )
    overlapping = Slot(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        starts_at=datetime(2026, 9, 25, 10, 15, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 10, 45, tzinfo=UTC),
    )
    adjacent = Slot(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        starts_at=datetime(2026, 9, 25, 10, 30, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 11, 0, tzinfo=UTC),
    )

    assert base.overlaps(overlapping) is True
    assert base.overlaps(adjacent) is False


def test_patient_can_cancel_before_deadline() -> None:
    branch = Branch(name="Филиал", timezone="Europe/Moscow")
    slot = Slot(
        doctor_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        starts_at=datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 9, 25, 12, 30, tzinfo=UTC),
    )
    appointment = Appointment(patient_id=uuid.uuid4(), slot_id=slot.id, status="active")
    appointment.slot = slot

    three_hours_before = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
    one_hour_before = datetime(2026, 9, 25, 11, 0, tzinfo=UTC)

    assert appointment.is_cancellable_by_patient(branch, three_hours_before) is True
    assert appointment.is_cancellable_by_patient(branch, one_hour_before) is False


def test_cancel_records_who_and_when() -> None:
    appointment = Appointment(
        patient_id=uuid.uuid4(), slot_id=uuid.uuid4(), status="active"
    )
    now = datetime.now(UTC)

    appointment.cancel(by="patient", at=now)

    assert appointment.status == "cancelled"
    assert appointment.cancelled_by == "patient"
    assert appointment.cancelled_at == now
    assert appointment.is_active is False


def test_user_roles() -> None:
    patient = User(telegram_id=1, role="patient")
    admin = User(telegram_id=2, role="network_admin")

    assert patient.is_patient is True
    assert patient.is_admin is False
    assert admin.is_patient is False
    assert admin.is_admin is True
