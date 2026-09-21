# 🩺 Avela — Telegram-бот предварительной записи к врачу

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram%20Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Status](https://img.shields.io/badge/Status-In%20Development-F59E0B?style=for-the-badge)]()
[![Repository](https://img.shields.io/badge/GitHub-avela--telegram--bot-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jaraslaukunin/avela-telegram-bot)

Avela — Telegram-бот и Telegram Mini App для предварительной записи пациентов
в несколько медицинских сетей. Одна установка обслуживает несколько
независимых сетей (multi-tenant), поэтому данные и права строго разделены
по сети и филиалу.

**Статус:** ранний прототип. Сейчас в репозитории — каркас aiogram-бота
(polling, профиль в памяти). FastAPI API, webhook, БД, Mini App, CI/CD и
деплой — в плане ниже.

## Что уже работает

- `/start` — приветствие и главное меню;
- профиль: просмотр, сохранение номера телефона через кнопку Telegram
  (с проверкой, что контакт принадлежит отправителю);
- хранение профилей — в памяти (только для прототипа, заменим на БД);
- FastAPI: `/health` и `/ready`;
- webhook-роут `/telegram/webhook` с проверкой
  `X-Telegram-Bot-Api-Secret-Token` (включается через `WEBHOOK_MODE=true`);
- серверная валидация Telegram Mini App initData: HMAC-SHA256,
  constant-time сравнение, срок годности `auth_date`, разбор пользователя
  (`app/core/security/initdata.py`).

## Роли

- Пациент — запись к врачу, свои записи, уведомления;
- Администратор филиала — только свои филиалы;
- Администратор сети — только своя сеть;
- Администратор Avela — все сети, аудит, системные настройки.

Права проверяются на backend при каждом защищённом действии.

## Использование и ограничения

Avela предназначен исключительно для **предварительной записи** на приём к врачу.

- бот не является медицинским изделием;
- бот не заменяет врача, регистратуру или экстренную медицинскую помощь;
- информация в боте не является медицинской консультацией;
- при угрожающем жизни или здоровью состоянии — обращайтесь в экстренные службы;
- запись через бота может требовать подтверждения медицинской организацией.

## Стек

Backend (Python 3.12):

- FastAPI — HTTP API и Telegram webhook в одном приложении;
- aiogram 3 — webhook и уведомления;
- SQLAlchemy 2 (async) + asyncpg;
- Pydantic Settings;
- APScheduler — напоминания, отдельный singleton worker;
- pytest, pytest-asyncio, httpx.

Frontend (монорепозиторий, каталог `frontend/`):

- React, TypeScript, Vite, Telegram Web Apps SDK;
- React Router, TanStack Query;
- i18n: русский, English, беларуская лацінка (be-Latn);
- Vitest + React Testing Library.

Инфраструктура:

- Supabase: PostgreSQL, Storage (фото врачей), CLI SQL-миграции;
- Docker Compose, Nginx, Ubuntu 24.04 LTS VPS;
- GitHub Actions; DNS — Cloudflare.

Миграции схемы — только SQL-файлы Supabase CLI (Alembic не используем).
Авторизация — Telegram Mini App initData (не Supabase Auth).

## Архитектура

Модульный монолит. FastAPI и aiogram webhook живут в одном процессе,
напоминания — в отдельном singleton-контейнере worker. Бизнес-логика —
в сервисном слое, а не в хендлерах.

```text
app/
  main.py         # FastAPI: lifespan, маршрут webhook
  config.py       # настройки (pydantic-settings)
  api/            # HTTP-роутеры
  core/           # security, auth/роли, audit, логирование
  services/       # use cases: бронирование, расписание, уведомления
  models/         # SQLAlchemy
  repositories/
  bot/            # aiogram: webhook-роутер, уведомления
  worker/         # APScheduler: напоминания 24ч / 2ч
frontend/         # Telegram Mini App
supabase/         # SQL-миграции, RLS
deploy/           # Docker Compose, Nginx
.github/workflows # CI
```

Время в БД — UTC; часовой пояс филиала — IANA identifier (по умолчанию
Europe/Moscow). Самостоятельная отмена/перенос записи — не позже чем
за 2 часа до приёма по времени филиала.

## Локальный запуск

Нужен Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # вписать BOT_TOKEN
python -m app.main
```

Команда поднимает FastAPI (uvicorn) на `127.0.0.1:8000` — там живут
`/health`, `/ready` и webhook-роут. Параллельно бот работает на polling
(webhook удаляется при старте — удобно для разработки). В production
(`WEBHOOK_MODE=true`) обновления принимает webhook на Nginx.

## Разработка

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q          # тесты
ruff check .       # lint
mypy app           # проверка типов
```

## Локальная база данных

```bash
docker compose -f docker-compose.dev.yml up -d db
docker compose -f docker-compose.dev.yml exec db \
  psql -U avela -d avela -f /migrations/20260921120000_init.sql
TEST_DATABASE_URL=postgresql+asyncpg://avela:avela@localhost:5432/avela pytest -q
```

Схема управляется только SQL-миграциями в `supabase/migrations/`
(Supabase CLI; Alembic не используем). Пересечения слотов врача и записей
пациента запрещены на уровне PostgreSQL (exclusion constraint, частичный
уникальный индекс, триггер), а не только в коде.

## Переменные окружения

См. `.env.example`. Секреты (BOT_TOKEN, ключи Supabase, webhook secret)
живут только в `.env` и в секретах окружения — в репозиторий не попадают.

## Качество и CI (план)

- lint (ruff), type-check (mypy), тесты — GitHub Actions;
- автоматизированные тест-кейсы: права и tenant isolation, бронирование
  и гонки, лимит 2 часов, уведомления;
- staging/production deploy — только после отдельного согласования.

Пока автоматизированных тестов в репозитории нет — добавятся в ближайших
итерациях.

## Деплой (план)

- VPS Ubuntu 24.04, Docker Compose: backend, worker, frontend-статика, Nginx;
- БД и Storage — Supabase;
- webhook: `POST https://bot.avela.jaraslau.dev/telegram/webhook`;
- Mini App: `avela.jaraslau.dev`, API: `api.avela.jaraslau.dev`,
  status page: `status.avela.jaraslau.dev`;
- DNS — Cloudflare, TLS Full (strict).

## Автор

**Jaraslau Kunin** — Python-разработчик, GitHub: [@jaraslaukunin](https://github.com/jaraslaukunin)

## Лицензия

Проект source-available: код можно просматривать и скачивать, но изменение,
распространение и коммерческое использование — только с письменного
согласия владельца. Подробности в `LICENSE`.

Изменения принимаются только после согласования с владельцем.
