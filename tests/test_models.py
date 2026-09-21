"""Инварианты ORM-моделей (без БД)."""
from sqlalchemy import DateTime

import app.models.appointment  # noqa: F401
import app.models.catalog  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.schedule  # noqa: F401
import app.models.user  # noqa: F401
from app.models.base import Base


def test_all_datetime_columns_are_timezone_aware() -> None:
    """Все DateTime-колонки обязаны быть timezone-aware.

    Колонки в БД — timestamptz; naive-тип в ORM (TIMESTAMP WITHOUT TIME ZONE)
    ломает вставку aware-дат: asyncpg DataError «can't subtract offset-naive
    and offset-aware datetimes». Этот инвариант ловит регрессию без Postgres.
    """
    naive = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    ]

    assert naive == []
