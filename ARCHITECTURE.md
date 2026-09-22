# Avela — Полное описание системы (инструкция для LLM-агентов и разработчиков)

> Этот документ — единый источник правды о проекте. Он написан так, чтобы
> нейросеть или новый разработчик мог понять систему без чтения всего кода.
> Если код и этот документ расходятся — верь коду и обнови документ.

---

## 1. Что такое Avela

Avela — Telegram-бот и Telegram Mini App для предварительной записи пациентов
к врачам в несколько медицинских сетей (multi-tenant). Одна установка
обслуживает несколько независимых сетей с разделением данных и прав.

**Статус**: работающий MVP в production-режиме на VPS.

**Стек (менять без обсуждения нельзя):**
- Backend: Python 3.12, FastAPI, aiogram 3, SQLAlchemy 2 (async), asyncpg, Pydantic Settings, APScheduler
- Frontend: React 18, TypeScript, Vite, TanStack Query, React Router, свой мини-i18n (ru/en/be-Latn), Vitest
- БД: Supabase PostgreSQL (внешняя), миграции — чистый SQL (Supabase CLI), Alembic НЕ используется
- Инфраструктура: Docker Compose, Nginx, Ubuntu 24.04 VPS, GitHub Actions, Cloudflare DNS
- Тесты: pytest + pytest-asyncio (бэкенд), Vitest (фронтенд)

---

## 2. Репозиторий

- **URL**: `https://github.com/jaraslaukunin/avela-telegram-bot`
- **SSH**: `github.com:jaraslaukunin/avela-telegram-bot`
- **Ветка**: `main` (единственная рабочая)
- **Локальный путь**: `/Users/jaraslaukunin/avela-telegram-bot`
- **venv**: `.venv` (Python 3.12)

### Как пушить изменения (строгий порядок)

```bash
cd /Users/jaraslaukunin/avela-telegram-bot
git add -A
git commit -m "feat: короткое описание"
git fetch origin main
git rebase origin/main
git push origin main
```

**Правило**: если `git rebase` дал конфликт — ОСТАНОВИТЬСЯ, ничего не пушить,
показать вывод владельцу. Push выполняется только после зелёного rebase.

### Проверки перед пушем (локально)

```bash
.venv/bin/ruff check .                      # линтер
.venv/bin/mypy app tests                    # типы (и app, и tests!)
.venv/bin/python -m pytest -q -p no:cacheprovider --no-header   # юнит-тесты (без БД)
```

Интеграционные тесты (нужна Postgres) запускаются в CI автоматически; локально
требуют `TEST_DATABASE_URL` (см. раздел 10).

---

## 3. Структура каталогов

```
avela-telegram-bot/
├── app/                        # Backend (FastAPI + aiogram)
│   ├── main.py                 # сборка приложения, lifespan, CORS/middleware, uvicorn
│   ├── config.py               # Settings (pydantic-settings, читает .env)
│   ├── db.py                   # ленивый async-движок, get_session, get_session_factory,
│   │                           #   keep_database_warm (прогрев соединения с Supabase)
│   ├── schemas.py              # ВСЕ pydantic-схемы API
│   ├── cli.py                  # CLI: grant-admin, seed-demo, show-state
│   ├── api/                    # HTTP-роуты (тонкие: проверка прав + вызов сервисов)
│   │   ├── health.py           # /health /ready /status (публичные)
│   │   ├── auth.py             # вход через initData → JWT, /auth/me
│   │   ├── catalog.py          # сети/филиалы/услуги/врачи/слоты (публичный каталог, TTL-кэш)
│   │   ├── offers.py           # поиск: /catalog/services /catalog/cities /catalog/offers
│   │   ├── patients.py         # пациенты аккаунта (CRUD)
│   │   ├── appointments.py     # запись/отмена/перенос пациента
│   │   ├── privacy.py          # удаление аккаунта (анонимизация)
│   │   ├── admin_catalog.py    # админ: сети, филиалы, услуги, врачи, шаблоны, генерация слотов, календарь врача
│   │   └── admin_appointments.py  # админ: записи, отмена, перенос, сообщение пациенту
│   ├── core/
│   │   ├── deps.py             # get_current_user (Bearer JWT → User из БД), require_roles
│   │   ├── roles.py            # константы ролей
│   │   ├── rate_limit.py       # in-memory rate limiter (скользящее окно)
│   │   ├── middleware.py       # request-id + security headers
│   │   ├── logging.py          # единый формат логов с request_id
│   │   ├── cache.py            # ttl_cache декоратор (для каталога)
│   │   └── security/
│   │       ├── initdata.py     # валидация Telegram initData (HMAC-SHA256, constant-time, auth_date)
│   │       └── jwt.py          # JWT HS256 (create/decode session)
│   ├── models/                 # SQLAlchemy-модели (ООП-сущности)
│   │   ├── __init__.py         # ИМПОРТИРУЕТ ВСЕ МОДЕЛИ (обязательно! иначе мапперы не соберутся)
│   │   ├── base.py             # Base (DeclarativeBase)
│   │   ├── catalog.py          # Network, Branch, Doctor, Service, DoctorService (+ методы tz/deadline)
│   │   ├── schedule.py         # ScheduleTemplate.generate_slots(), Slot.overlaps()
│   │   ├── appointment.py      # Appointment (+ cancel(), is_cancellable_by_patient())
│   │   ├── notification.py     # Notification (очередь уведомлений)
│   │   ├── patient.py          # Patient (профиль пациента аккаунта)
│   │   ├── service.py          # ServiceHeartbeat (для status page)
│   │   └── user.py             # User, BranchAdmin, AuditLog
│   ├── services/               # БИЗНЕС-ЛОГИКА (use cases)
│   │   ├── booking.py          # book_slot, cancel, reschedule, list_available_slots, контексты
│   │   ├── scheduling.py       # генерация слотов из шаблона (со снимком цены)
│   │   ├── notifications.py    # очередь уведомлений + render_message
│   │   ├── users.py            # get_or_create_user, get_or_create_default_patient
│   │   ├── privacy.py          # anonymize_user
│   │   ├── messaging.py        # сообщение пациенту из админки (через бота)
│   │   ├── audit.py            # write_audit
│   │   └── permissions.py      # scoped_network_ids/scoped_branch_ids/can_manage_network
│   ├── bot/                    # Telegram-бот
│   │   ├── client.py           # get_bot() — один экземпляр Bot на процесс
│   │   ├── render.py           # PNG-талон (Pillow, переносы текста, DejaVu/Arial fallback)
│   │   ├── formatting.py       # format_price и тексты (чистые функции, тестируются)
│   │   ├── errors.py           # глобальный обработчик ошибок бота
│   │   ├── webhook.py          # POST /api/telegram/webhook (secret-token)
│   │   ├── keyboards/main_menu.py  # кнопка «📱 Открыть Avela» (web_app) + «ℹ️ Информация»
│   │   └── handlers/           # start.py (приветствие), fallback.py (всё → в Mini App)
│   │                           # booking.py/appointments.py/profile.py — ПУСТЫЕ НАМЕРЕННО
│   └── worker/                 # Singleton-worker уведомлений (ОТДЕЛЬНЫЙ процесс!)
│       ├── main.py             # APScheduler, run_once
│       └── notifier.py         # dispatch_pending_notifications, write_heartbeat
├── frontend/                   # Telegram Mini App
│   ├── index.html              # SDK telegram-web-app.js + inline-скрипт тёмной темы
│   ├── public/logo.svg         # логотип
│   ├── src/
│   │   ├── main.tsx, App.tsx   # вход, роуты, таббар с иконками, авторизация
│   │   ├── telegram.ts         # типизированный window.Telegram.WebApp
│   │   ├── api/client.ts       # fetch-обёртка, JWT в заголовке, sessionStorage
│   │   ├── api/types.ts        # все типы ответов
│   │   ├── format.ts           # даты, цена, возраст, дедлайн (чистые функции)
│   │   ├── i18n/index.ts       # словари ru/en/be-Latn (+ тест на полноту ключей)
│   │   ├── i18n/context.tsx    # LocaleProvider, useT, useLocale, useSetLocale
│   │   ├── components/         # Patients (карточки), SlotCalendar, DoctorCalendar, Icon
│   │   └── screens/            # Home, Booking, MyAppointments, Reschedule, Patients,
│   │       │                   # Profile, Landing (для не-Telegram), admin/* (7 экранов)
├── supabase/migrations/        # SQL-миграции (порядок = имя файла)
├── deploy/                     # nginx/avela.conf, README.md (инструкция по VPS)
├── status/index.html           # публичная status page
├── docker-compose.prod.yml     # api, worker, web, nginx
├── Dockerfile                  # backend-образ
└── .github/workflows/          # ci.yml, deploy.yml
```

---

## 4. Инфраструктура и сервер

### Сервер
- **SSH**: `ssh root@31.128.40.18` (доступ по ключу, StrictHostKeyChecking=accept-new)
- **Каталог приложения**: `/opt/avela` (git-клон репозитория)
- **Контейнеры**: `docker compose -f docker-compose.prod.yml` → сервисы: `api`, `worker`, `web`, `nginx`
- **.env на сервере**: `/opt/avela/.env` (chmod 600, секреты только там)
- **Сертификаты**: `/opt/avela/deploy/certs/{fullchain,privkey}.pem` (Cloudflare Origin CA), монтируются в nginx как `/etc/nginx/certs/`
- **Полезные скрипты на сервере**: `/root/avela-set-db-password.sh` (безопасная смена пароля БД), `/root/avela-set-certs.sh` (вставка сертификатов)

### Supabase (внешняя БД + Storage)
- **Project ref**: `nctnayzkbcgobanxyabv`
- **URL**: `https://nctnayzkbcgobanxyabv.supabase.co`
- **Session pooler**: `aws-0-eu-west-2.pooler.supabase.com:5432`, пользователь `postgres.nctnayzkbcgobanxyabv`
- **Миграции**: `supabase db push` (Supabase CLI, на машине владельца)
- **RLS**: включён на ВСЕХ таблицах, политики НЕ создаются (deny-by-default). Backend ходит как владелец схемы (service role), поэтому RLS его не ограничивает. Прямой доступ через Supabase REST/anon ничего не видит.

### Домены (Cloudflare, проксирование включено, TLS Full strict)
| Домен/путь | Назначение |
|---|---|
| `avela.jaraslau.dev/` | Mini App (статический SPA из контейнера web) |
| `avela.jaraslau.dev/api/*` | FastAPI (nginx срезает префикс `/api`) |
| `avela.jaraslau.dev/api/telegram/webhook` | webhook бота |
| `avela.jaraslau.dev/statuspage/` | status page (и legacy `/status/`) |

### Контейнеры
- **api**: `python -m app.main` (FastAPI + polling бота в одном процессе)
- **worker**: `python -m app.worker.main` (напоминания — ОТДЕЛЬНЫЙ singleton, чтобы не дублировались)
- **web**: nginx со статикой Mini App (сборка Vite внутри образа)
- **nginx**: TLS-терминация и маршрутизация

### Выкат на сервер (полный цикл)
```bash
# 1) локально: push (раздел 2)
# 2) на сервере:
ssh root@31.128.40.18 'cd /opt/avela && git pull --ff-only && \
  docker compose -f docker-compose.prod.yml build api worker web && \
  docker compose -f docker-compose.prod.yml up -d api worker web'
# 3) проверка:
ssh root@31.128.40.18 'cd /opt/avela && \
  docker compose -f docker-compose.prod.yml ps && \
  docker compose -f docker-compose.prod.yml exec -T api curl -fsS http://127.0.0.1:8000/ready'
curl -fsS https://avela.jaraslau.dev/api/status
```

---

## 5. Переменные окружения (.env)

| Переменная | Обязательна | Описание |
|---|---|---|
| `BOT_TOKEN` | да | токен бота от BotFather |
| `DATABASE_URL` | да | `postgresql+asyncpg://postgres.<ref>:<пароль>@aws-0-eu-west-2.pooler.supabase.com:5432/postgres` (пароль URL-encoded!) |
| `JWT_SECRET` | да (≥32 симв.) | секрет JWT-сессий Avela |
| `JWT_TTL_SECONDS` | нет (604800) | срок жизни JWT |
| `WEBHOOK_MODE` | нет (false) | true = webhook вместо polling |
| `WEBHOOK_SECRET` | при webhook | secret token для X-Telegram-Bot-Api-Secret-Token |
| `WEBHOOK_BASE_URL` | при webhook | `https://avela.jaraslau.dev/api` |
| `MINI_APP_URL` | нет | `https://avela.jaraslau.dev` — кнопка «Открыть Avela» в боте |
| `CORS_ORIGINS` | нет | домены через запятую (в проде не нужен — same-origin) |
| `NOTIFIER_INTERVAL_SECONDS` | нет (30) | период проверки очереди уведомлений |
| `API_HOST` / `API_PORT` | нет | 127.0.0.1 / 8000 локально, 0.0.0.0 в контейнере |
| `SUPABASE_URL` | нет | для будущих интеграций Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | нет | только серверу, никогда в браузер |
| `TEST_DATABASE_URL` | для интеграционных тестов | строка локальной/тестовой Postgres |
| `VITE_API_URL` (frontend) | при сборке | `https://avela.jaraslau.dev/api` или `http://127.0.0.1:8000` локально |

---

## 6. База данных

### Таблицы (все в одной схеме public)
- **networks** — сети (slug уникальный, is_active)
- **branches** — филиалы (network_id FK, timezone IANA, city/region/address/phone, latitude/longitude)
- **services** — услуги (network_id FK, name, duration_minutes, is_active)
- **doctor_services** — связка врач+услуга (PK = doctor_id+service_id, **price numeric** — цена именно здесь)
- **doctors** — врачи (branch_id FK, full_name, specialty, photo_path, is_active)
- **schedule_templates** — шаблоны расписания (doctor_id, service_id, weekday 0-6, start_time/end_time, valid_from/valid_until)
- **slots** — слоты (doctor_id, service_id, starts_at/ends_at timestamptz UTC, **price — снимок цены на момент генерации**)
- **users** — пользователи (telegram_id unique, role, network_id для админа сети, is_active)
- **patients** — профили пациентов (user_id FK, full_name, birth_date) — один аккаунт может вести несколько пациентов
- **branch_admins** — назначения админов филиалов (user_id, branch_id)
- **appointments** — записи (patient_id=user, patient_profile_id=patient, slot_id, status: active/cancelled/completed/rescheduled, rescheduled_from_id, cancelled_by/cancelled_at, patient_full_name)
- **notifications** — очередь уведомлений (user_id, appointment_id, kind, scheduled_for, status, UNIQUE(appointment_id, kind) — дедупликация на уровне БД)
- **audit_logs** — аудит административных действий (actor_user_id, action, entity_type/id, network_id, details JSONB)
- **service_heartbeats** — heartbeat worker'а (name PK, updated_at)

### Защита целостности (уровень PostgreSQL, не только код)
- `slots`: EXCLUDE USING gist (doctor_id =, tstzrange(starts_at, ends_at) &&) — нельзя пересекающиеся интервалы одного врача
- `appointments`: UNIQUE(slot_id) WHERE status='active' — один активный на слот
- Триггер на INSERT в appointments: пересечение активных записей одного **пациента** (patient_profile_id) запрещено даже у разных врачей
- CHECK: users.role, appointment.status, notification.kind/status, cancelled_by

### Миграции
- Файлы: `supabase/migrations/*.sql` в порядке имени (20260921120000_init.sql, ...30000_service_heartbeats.sql, ...090000_patients_prices_geo.sql)
- Применение: `supabase link --project-ref nctnayzkbcgobanxyabv && supabase db push`

---

## 7. Аутентификация и роли

### Вход (Mini App)
1. Telegram передаёт `initData` строкой.
2. Backend проверяет подпись по официальному алгоритму: HMAC-SHA256(secret=HMAC_SHA256("WebAppData", bot_token), data_check_string), constant-time сравнение, срок `auth_date` (24ч), обязательное наличие user (`app/core/security/initdata.py`, используется aiogram).
3. `POST /auth/telegram` → находит/создаёт User по telegram_id → возвращает JWT (HS256, issuer "avela", sub=user_id, telegram_id, role, exp).
4. Frontend хранит токен в sessionStorage и шлёт в заголовке `Authorization: Bearer ...`.
5. `get_current_user` при каждом запросе: декодирует JWT, **роль берёт из БД** (заблокированный/удалённый сразу теряет доступ).

### Роли (проверяются на backend при КАЖДОМ защищённом действии)
| Роль | Возможности |
|---|---|
| `patient` | запись, свои записи, отмена/перенос (дедлайн 2ч), свои пациенты, удаление аккаунта |
| `branch_admin` | только свои филиалы: врачи, услуги (создание/изменение), расписания, записи (отмена/перенос), сообщения пациентам. Филиалы и сети НЕ создаёт |
| `network_admin` | своя сеть (users.network_id): всё из branch_admin + филиалы, назначение админов филиалов |
| `avela_admin` | все сети: создание/блокировка сетей, назначение админов сетей, весь аудит |

### Как выдавать права
```bash
# админ Avela (первый раз; пользователь должен сначала открыть бота/Mini App):
ssh root@31.128.40.18 'cd /opt/avela && docker compose -f docker-compose.prod.yml exec -T api python -m app.cli grant-admin <telegram_id>'
# админ сети:  POST /admin/networks/{network_id}/admins   {"telegram_id": N}  (только avela_admin)
# админ филиала: POST /admin/branches/{branch_id}/admins   {"telegram_id": N}  (avela_admin или network_admin)
# В Mini App это делает вкладка «Администраторы» (админ → Администраторы).
```

---

## 8. HTTP API (полный список)

Все даты — UTC ISO. Ошибки: `{"detail": "..."}`. 404 используется для чужих
ресурсов (не раскрывает существование). Всё защищённое — через Bearer JWT.

### Публичные (без токена)
- `GET /health` — liveness
- `GET /ready` — `{"status","checks":{"database"}}`
- `GET /status` — компоненты для status page (api/database/worker/telegram_delivery)
- `GET /api/telegram/webhook` обрабатывается отдельно (webhook бота)

### Auth
- `POST /auth/telegram` — body `{"init_data": "..."}` → `{"access_token","token_type","user"}` (rate limit 10/мин)
- `GET /auth/me` — текущий пользователь

### Каталог (пациент)
- `GET /networks` — активные сети
- `GET /networks/{id}/branches`
- `GET /services?network_id=...`
- `GET /branches/{id}/doctors[?service_id=...]`
- `GET /slots/available?service_id=&[branch_id=&doctor_id=&from=&to=]` — свободные слоты (по умолчанию 14 дней)

### Поиск (offers)
- `GET /catalog/services` — уникальные названия специальностей (+длительность)
- `GET /catalog/cities` — города филиалов
- `GET /catalog/offers?service_name=&[city=&latitude=&longitude=]` — предложения: врач+филиал+цена+ближайший слот+расстояние

### Пациенты аккаунта
- `GET /patients` — мои пациенты
- `POST /patients` — `{"full_name","birth_date"?}` → 201
- `DELETE /patients/{id}` — 204 (409, если есть активные записи)

### Записи (пациент)
- `GET /appointments` — мои записи (rescheduled скрыты)
- `POST /appointments` — `{"slot_id","patient_id"?}` (без patient_id — пациент по умолчанию)
- `POST /appointments/{id}/cancel` — дедлайн 2ч (409 с телефоном клиники)
- `POST /appointments/{id}/reschedule` — `{"new_slot_id"}`

### Приватность
- `POST /privacy/delete-me` — анонимизация: отмена активных записей, гашение уведомлений, затирание ПДн, telegram_id → отрицательный, is_active=false, аудит

### Админ (роль ≥ branch_admin, scope по роли)
- `GET /admin/scope` — `{"role","can_access_all","network_ids","branch_ids"}`
- `GET /admin/networks` / `POST /admin/networks` / `PATCH /admin/networks/{id}`
- `POST /admin/networks/{id}/admins` (только avela_admin)
- `GET /admin/branches[?network_id]` / `POST /admin/networks/{id}/branches` (network_admin+) / `PATCH /admin/branches/{id}` / `POST /admin/branches/{id}/admins`
- `GET /admin/services[?network_id]` / `POST /admin/networks/{id}/services` (network_admin+) / `PATCH /admin/services/{id}`
- `GET /admin/branches/{id}/doctors` / `POST /admin/branches/{id}/doctors` / `PATCH /admin/doctors/{id}` / `PUT /admin/doctors/{id}/services`
- `POST /admin/doctors/{id}/schedule-templates` / `POST /admin/schedule-templates/{id}/generate-slots`
- `GET /admin/doctors/{id}/calendar?start=&end=` — календарь врача (state: free/booked/none)
- `GET /admin/appointments[?branch_id=&limit]` / `POST /admin/appointments/{id}/cancel` / `POST /admin/appointments/{id}/reschedule` / `POST /admin/appointments/{id}/message` (сообщение пациенту в Telegram)

Rate limits: auth 10/мин, запись 30/мин, админ 120/мин, privacy 5/мин, status 120/мин (in-memory, один процесс).

---

## 9. Telegram-бот и worker

### Бот (в процессе api)
- `/start` — приветствие и меню
- Кнопка «📱 Открыть Avela» — web_app-кнопка на `MINI_APP_URL` (открывает Mini App с initData)
- «ℹ️ Информация»; всё остальное → fallback «вся запись в приложении»
- Глобальный обработчик ошибок: пользователь всегда получает ответ, трейсбек — только в логи
- **Запись в чате удалена намеренно**: модули booking/appointments/profile в bot/handlers пустые

### Worker (`python -m app.worker.main`)
- APScheduler, интервал `NOTIFIER_INTERVAL_SECONDS`
- `dispatch_pending_notifications`: берёт pending с `scheduled_for <= now` (до 100), шлёт по одному
- **booking_created → талон-картинка** (PNG, Pillow) с подписью; напоминания/отмена/перенос → текст
- Напоминания отменённых/перенесённых записей → skipped (не спамить)
- Ошибки Telegram: TelegramForbiddenError → failed «не открывал бота»
- `write_heartbeat` — пишет `service_heartbeats` (status page показывает worker: ok, если свежее 5 минут)

### Виды уведомлений (kind)
`booking_created`, `reminder_24h`, `reminder_2h`, `cancelled`, `rescheduled`.
Напоминания, чьё время уже прошло на момент записи, помечаются skipped сразу при постановке.

---

## 10. Бизнес-правила (важно!)

- **Дедлайн 2 часа**: самостоятельная отмена/перенос строго раньше чем за 2 часа до приёма **в таймзоне филиала** (IANA). После дедлайна — только через клинику (в ответе даётся телефон).
- **Пересечения считаются по ЧЕЛОВЕКУ**: два разных пациента одного аккаунта могут записаться на одно время; один пациент — нет, даже у разных врачей/в разных сетях. Защита: код + триггер в БД.
- **Один слот — одна активная запись**: partial unique index + предварительная проверка + IntegrityError → «слот занят».
- **«Любой свободный врач»** = выбор слота без doctor_id; бронь атомарна.
- **Перенос** = новая запись active + старая status='rescheduled' (+rescheduled_from_id). Пациенту rescheduled НЕ показываются (ни в API, ни в боте).
- **Цены** на связке врач+услуга (`doctor_services.price`); при генерации слотов цена снимается в `slots.price`, при брони — используется цена слота.
- **Время**: в БД всё UTC (timestamptz), отображение и дедлайны — в таймзоне филиала. Все DateTime-колонки в моделях — `DateTime(timezone=True)` (есть тест-инвариант).
- **Атомарность**: бронь/перенос внутри транзакции с flush + IntegrityError-обработкой гонок.
- **Кэш каталога**: 20 сек TTL на бэке; фронт: staleTime 5 мин у каталога, 10-30 сек у слотов/записей; токен сессии — в sessionStorage.

---

## 11. Mini App (frontend)

### Сборка и проверки
```bash
cd frontend
npm install
npm run typecheck   # tsc --noEmit (строгий режим, noUnusedLocals)
npm run test        # vitest (i18n-полнота, format, client)
npm run build       # typecheck + vite build → dist/
npm run dev         # локально, VITE_API_URL=http://127.0.0.1:8000
```

### Экраны
- **Home**: логотип, «Записаться», «Мои записи», «Профиль»
- **Booking** (5 шагов): специалист (город+услуга) → предложения (врач+филиал+цена+ближайшее время+км) → **календарь доступности** (зелёный день=есть время, серый=нет; внутри дня — слоты) → пациент (карточки с возрастом, добавление нового) → сводка и подтверждение
- **MyAppointments**: карточки записей, отмена (до дедлайна), перенос (через календарь), после дедлайна — телефон клиники
- **Patients**: список/добавление/удаление пациентов (возраст: взрослый/ребёнок)
- **Profile**: имя/телефон, язык (Рус/Eng/Бел), мои пациенты, удаление аккаунта
- **Landing**: для открывших не из Telegram (кнопка «Открыть в Telegram», статус сервисов)
- **Admin** (по роли): главная, записи (отмена/перенос-календарь/сообщение пациенту), врачи (создание+услуги+активность), расписание (шаблоны+генерация+календарь врача), услуги, филиалы, администраторы

### Ключевые детали
- Токен JWT: `Authorization: Bearer`, хранится в sessionStorage (`avela_token`), восстановление без повторного initData-раунда
- Тёмная тема: inline-скрипт в index.html (до отрисовки) + `data-theme` на `<html>`
- Язык: sessionStorage (`avela_locale`), по умолчанию из Telegram `language_code`
- Иконки таббара: NavLink + Icon (активная подсветка)
- Логотип: `/logo.svg?v=1` (кэш-бастер)

---

## 12. CI/CD

### ci.yml (на каждый push)
1. ruff check .
2. mypy app tests (ошибки → аннотации check-run через ::error::)
3. Postgres-сервис + применение ВСЕХ миграций + `pytest -q` с TEST_DATABASE_URL (интеграционные тесты)
4. frontend: npm install → typecheck → test → build

### deploy.yml (ручной)
- workflow_dispatch с выбором окружения (staging/production) и подтверждением `confirm=yes`
- Деплой выполняется только при `DEPLOY_ENABLED=true` (repo variable) + секретах DEPLOY_HOST/DEPLOY_USER/DEPLOY_SSH_KEY/DEPLOY_PATH
- В деплое: git pull --ff-only + docker compose build + up

---

## 13. Тесты

- Юнит (без БД): config, initdata, jwt, доменные методы (tz/deadline/generate_slots/overlaps), инварианты моделей (aware-даты, полнота app.models), форматирование бота, талон, health
- Интеграционные (Postgres, запускаются в CI): auth-API, бронирование (гонки за слот двумя сессиями!), пересечения пациентов, дедлайн, перенос, админ-API (роли, tenant isolation, назначение админов, перенос админом, сообщения), worker (талон-фото, гашение напоминаний, heartbeat), приватность, каталог, offers
- Frontend: i18n (одинаковые ключи во всех локалях, нет пустых), format, client

---

## 14. Секреты и запреты

- НИКОГДА не класть в код/frontend/Docker-образ/markdown/логи: BOT_TOKEN, пароль БД, SUPABASE_SERVICE_ROLE_KEY, JWT_SECRET, WEBHOOK_SECRET, SSH-ключи
- .env живёт только локально и на сервере (chmod 600); шаблон — .env.example без секретов
- Публикуемые ключи Supabase (sb_publishable_...) — не секрет, но проекту не нужны (всё через backend)
- Деплой, миграции, DNS, секреты GitHub, изменения на VPS — только с явным подтверждением владельца
- В логах не печатать пароли/токены; в ответах пользователю — не печатать содержимое .env

---

## 15. Известные ограничения (MVP) и план

- Rate limiting — в памяти процесса (при нескольких инстансах нужен Redis)
- Фото врачей: поле photo_path есть, загрузка в Supabase Storage и UI-загрузка — следующий шаг; заглушка — инициалы
- Форма «сети» для Avela-админа (создание сети) — в UI пока только API
- Компонентные тесты фронтенда (RTL) — пока только чистые функции
- Календарь пациента группирует дни по локальной таймзоне браузера (не филиала)
- Инциденты status page ведутся вручную в `status/index.html`
