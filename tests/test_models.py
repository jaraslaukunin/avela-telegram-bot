"""Инварианты ORM-моделей (без БД)."""
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import DateTime

import app.models.appointment  # noqa: F401
import app.models.catalog  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.schedule  # noqa: F401
import app.models.service  # noqa: F401
import app.models.user  # noqa: F401
from app.models.base import Base

ROOT = Path(__file__).resolve().parents[1]


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


def test_importing_models_package_registers_all_mappers() -> None:
    """Импорта `app.models` достаточно, чтобы мапперы собрались.

    Регрессия: без всех моделей в `app/models/__init__.py` строковые ссылки
    в relationship не разрешаются и `configure_mappers()` падает — именно
    это ломало CLI на сервере (`python -m app.cli show-state`).
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("BOT_TOKEN", "test-token")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.models; "
            "from sqlalchemy.orm import configure_mappers; "
            "configure_mappers(); "
            "print('ok')",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
