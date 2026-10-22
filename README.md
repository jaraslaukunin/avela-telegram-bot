<div align="center">

<img src="logo.svg" alt="Avela" width="110" />

# Avela — запись к врачу в Telegram

**Telegram Mini App и бот предварительной записи в медицинские сети: FastAPI, aiogram 3 и PostgreSQL с разделением по тенантам.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Telegram Mini App](https://img.shields.io/badge/Telegram_Mini_App-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/webapps)

[![License: Source-Available](https://img.shields.io/badge/License-Source--Available-orange?style=for-the-badge)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-avela--telegram--bot-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jaraslaukunin/avela-telegram-bot)

**[Возможности](#возможности)** · [Архитектура](#архитектура) · [Быстрый старт](#быстрый-старт) · [База данных](#база-данных-и-миграции) · [Уведомления](#уведомления-и-worker) · [Деплой](#деплой) · [Документация](#документация) · [Лицензия](#лицензия)

</div>

---

## О проекте

**Avela** — сервис предварительной записи к врачу, который живёт целиком в Telegram: пациент открывает
Mini App, выбирает специалиста, филиал и свободное время, а бот присылает талон и напоминания.
Одна установка обслуживает **несколько независимых медицинских сетей** — данные, роли и видимость
жёстко разделены по сети и филиалу.

Бот намеренно не ведёт диалог о записи: вся логика — в Mini App и API, а чат остаётся каналом
уведомлений. Так сценарий записи существует в одном месте и не расходится между двумя интерфейсами.

**Статус:** работающий MVP. В репозитории собраны бот, FastAPI-API, worker уведомлений,
Mini App на React, SQL-миграции, тесты, CI и обвязка деплоя на VPS. Выкат на сервер — ручной
workflow с обязательным подтверждением, поэтому «живой» инстанс зависит от настроенных
GitHub Secrets, а не от самого репозитория.

> ⚠️ Сервис предназначен только для **предварительной записи**. Он не является медицинским изделием,
> не ставит диагнозы, не заменяет врача, регистратуру и экстренную помощь. При угрозе жизни или
> здоровью — обращайтесь в экстренные службы.

## Возможности

### Telegram Mini App (пациент)

- поиск специалиста сразу **по всем сетям**: город, цена приёма и расстояние до филиала
  (формула гаверсинуса), ближайшее свободное время;
- запись по шагам: услуга → филиал → врач **или «любой свободный врач»** → слот → подтверждение;
  если телефона нет, бот сначала просит поделиться номером и только потом показывает кнопку приложения;
- «Мои записи»: отмена и перенос — не позже чем за **2 часа** до приёма по времени филиала,
  с подтверждением действия;
- **несколько пациентов на один Telegram-аккаунт** (например, родитель записывает себя и детей);
  пересечения приёмов считаются на уровне пациента, а не аккаунта;
- профиль, удаление аккаунта по запросу, интерфейс на русском, English и беларускай лацінцы.

### Telegram-бот

- `/start`: знакомство, добровольная передача номера кнопкой `request_contact`;
- меню: «📱 Открыть Avela» (кнопка WebApp) и «ℹ️ Информация»;
- любой другой текст или callback ведут в приложение — бот не изображает диалог записи;
- присылает **талон-картинку** (PNG: дата, услуга, врач, филиал, адрес, цена, код записи)
  и напоминания о приёме.

### API и backend

- `POST /auth/telegram` — валидация Telegram Mini App initData (HMAC-SHA256, constant-time
  сравнение, срок годности `auth_date`) и выдача короткоживущего JWT Avela; `GET /auth/me` — профиль;
- каталог: сети, филиалы, услуги, врачи, свободные слоты; поиск предложений по специалисту и городу
  с ценой и расстоянием;
- записи: создание, список своих, отмена, перенос; защита от гонки за слот и от пересечений;
- админ-API `/admin/*`: сети, филиалы, услуги, врачи, шаблоны расписания с генерацией слотов,
  календарь врача, отмена и перенос записей, сообщение пациенту от имени бота, аудит действий;
- пациенты аккаунта: `GET/POST /patients`, `DELETE /patients/{id}`;
- `POST /privacy/delete-me` — анонимизация аккаунта;
- `GET /health`, `GET /ready`, публичный `GET /status` (состояние API, БД, воркера и доставки Telegram);
- `POST /telegram/webhook` с проверкой `X-Telegram-Bot-Api-Secret-Token` (включается `WEBHOOK_MODE=true`);
- защита: строгий CORS, rate limiting, security headers, request id в логах и ответах.

### Уведомления

- очередь в таблице `notifications`, дедупликация уникальным индексом `(appointment_id, kind)`;
- виды: `booking_created`, `reminder_24h`, `reminder_2h`, `cancelled`, `rescheduled`;
- отправка — отдельным singleton-процессом воркера, а не из web-процесса;
- напоминания отменённых и перенесённых записей переводятся в `skipped`;
- heartbeat воркера питает публичную status page (`status/index.html`, обновление раз в 30 секунд;
  публичный JSON — `GET /status`), которая не раскрывает секреты, строки подключения и данные пациентов.

## Архитектура

Модульный монолит: FastAPI и aiogram webhook живут в одном процессе, напоминания — в отдельном
контейнере worker. Бизнес-логика вынесена в сервисный слой, а не в хендлеры.

```text
app/
  main.py         # FastAPI: lifespan, webhook, middleware
  config.py       # настройки (pydantic-settings)
  api/            # роутеры: auth, catalog, offers, appointments, patients, admin, privacy, health
  core/           # security (initdata, jwt), deps, middleware, rate_limit, logging, roles
  services/       # use cases: booking, scheduling, notifications, messaging, privacy, audit, permissions
  models/         # SQLAlchemy: каталог, расписание, записи, пациенты, уведомления, аудит
  bot/            # aiogram: webhook-роутер, хендлеры, клавиатуры, рендер талона
  worker/         # APScheduler: отправка уведомлений, heartbeat
frontend/         # Telegram Mini App (React + TypeScript + Vite)
status/           # публичная status page (статика)
supabase/         # SQL-миграции и config.toml
deploy/           # Nginx-конфиг, setup-vps.sh, пошаговая инструкция
.github/workflows # ci.yml и deploy.yml
```

Время в БД — **UTC**, часовой пояс филиала — IANA identifier (по умолчанию `Europe/Moscow`).
Самостоятельная отмена и перенос — не позже чем за 2 часа до приёма. Пересечения слотов врача и
приёмов пациента запрещены на уровне PostgreSQL (exclusion constraint, частичный уникальный индекс,
триггер), а не только в коде.

## Стек

- **Backend:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy 2 (async) + asyncpg, Pydantic Settings,
  APScheduler, Pillow (рендер талона), PyJWT.
- **Frontend:** React 18, TypeScript 5.7, Vite 5, React Router, TanStack Query, собственный мини-i18n
  (ru / en / be-Latn), Vitest + Testing Library.
- **База:** Supabase PostgreSQL; миграции — только SQL-файлы Supabase CLI, Alembic не используется.
- **Инфраструктура:** Docker Compose, Nginx, Ubuntu 24.04 VPS, GitHub Actions, Cloudflare DNS.

## Быстрый старт

### Требования

- Python **3.12**;
- Node.js 20 (для Mini App; в CI используется 20);
- Docker — только если нужна локальная Postgres (можно работать сразу с Supabase).

### Backend

```bash
git clone https://github.com/jaraslaukunin/avela-telegram-bot.git
cd avela-telegram-bot

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # вписать BOT_TOKEN, DATABASE_URL, JWT_SECRET
python -m app.main
```

Команда поднимает uvicorn на `127.0.0.1:8000`: там `/health`, `/ready`, `/status` и webhook-роут.
Параллельно бот работает на polling (при старте webhook удаляется — удобно для разработки).
В production (`WEBHOOK_MODE=true`) обновления принимает webhook через Nginx.

### Worker и Mini App

```bash
python -m app.worker.main          # уведомления и напоминания — ровно один процесс!

cd frontend
cp .env.example .env               # VITE_API_URL=http://127.0.0.1:8000
npm install
npm run dev                        # Mini App на 127.0.0.1:5173
```

### Переменные окружения

Полный список — в `.env.example`; секреты живут только в `.env` и в секретах сервера.

| Переменная | Назначение |
| --- | --- |
| `BOT_TOKEN` | Токен бота от @BotFather (обязателен) |
| `WEBHOOK_MODE` | `false` — polling, `true` — webhook |
| `WEBHOOK_SECRET` | Секрет заголовка `X-Telegram-Bot-Api-Secret-Token` (обязателен при webhook) |
| `WEBHOOK_BASE_URL` | Публичный префикс API, например `https://avela.jaraslau.dev/api` |
| `API_HOST`, `API_PORT` | Адрес и порт uvicorn (по умолчанию `127.0.0.1:8000`) |
| `DATABASE_URL` | Строка подключения с драйвером asyncpg |
| `TEST_DATABASE_URL` | БД для интеграционных тестов |
| `JWT_SECRET` | Секрет JWT, минимум 32 символа |
| `JWT_TTL_SECONDS` | Время жизни JWT Avela (по умолчанию 604800 = 7 дней) |
| `CORS_ORIGINS` | Разрешённые домены Mini App через запятую |
| `NOTIFIER_INTERVAL_SECONDS` | Как часто worker проверяет очередь (по умолчанию 30) |
| `MINI_APP_URL` | Публичный адрес Mini App для кнопки WebApp в боте |
| `SUPABASE_URL` | Адрес проекта Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Ключ service role — только серверным компонентам |
| `VITE_API_URL` | Адрес API для фронтенда (в `frontend/.env.example`) |

## База данных и миграции

Схема управляется только SQL-миграциями в `supabase/migrations/` (Supabase CLI).

**Локальная Postgres в Docker:**

```bash
docker compose -f docker-compose.dev.yml up -d db
for file in supabase/migrations/*.sql; do
  docker compose -f docker-compose.dev.yml exec -T db \
    psql -U avela -d avela -v ON_ERROR_STOP=1 -f "/migrations/$(basename "$file")"
done
TEST_DATABASE_URL=postgresql+asyncpg://avela:avela@localhost:5432/avela pytest -q
```

**Сразу с облачным Supabase (без локальной БД):**

```bash
supabase login
supabase link --project-ref nctnayzkbcgobanxyabv
supabase db push

# строку подключения взять в дашборде: Connect → Session pooler (драйвер asyncpg)
# DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<пароль>@aws-0-eu-west-2.pooler.supabase.com:5432/postgres
```

RLS включён на всех таблицах по принципу deny-by-default: backend ходит как владелец схемы,
прямой доступ через Supabase REST/anon не видит ничего. Ключ `service_role` не попадает
в браузер никогда.

## Первые шаги в пустой базе

Свежая база пустая: сеть, филиал, услугу, врача и слоты создают администраторы через API.
Первого администратора Avela через API назначить нельзя — он появляется служебной командой:

```bash
python -m app.cli show-state                  # что уже есть в базе
python -m app.cli grant-admin <telegram_id>   # роль avela_admin (после первого входа)
python -m app.cli seed-demo                   # демо-сеть, врач и слоты на 2 недели
```

`grant-admin` требует, чтобы пользователь уже существовал: пусть он один раз откроет Mini App
или напишет боту `/start`. `seed-demo` идемпотентен — повторный запуск не дублирует данные.

## Роли и доступ

| Роль | Зона видимости |
| --- | --- |
| `patient` | Свои записи и пациенты аккаунта |
| `branch_admin` | Только назначенные филиалы |
| `network_admin` | Только своя сеть |
| `avela_admin` | Все сети, аудит, системные настройки |

Права проверяются на backend для каждого защищённого действия; ресурс вне зоны видимости отдаёт
404, чтобы не раскрывать чужие данные. Каждое административное изменение пишется в `audit_logs`.

## Уведомления и worker

- уведомления не отправляются из web-процесса: сервисный слой только кладёт их в `notifications`
  со статусом `pending`;
- `python -m app.worker.main` каждые `NOTIFIER_INTERVAL_SECONDS` секунд забирает готовые и отправляет;
- «Запись за час до приёма» не получит напоминание за 24 часа — такое уведомление сразу помечается
  `skipped`, а не висит в очереди;
- worker отмечает heartbeat в `service_heartbeats` — это и есть источник данных для status page.

## Приватность и удаление данных

`POST /privacy/delete-me` (авторизованный пациент) выполняет:

1. отмену всех активных записей — пациент удаляет данные, приёмы не остаются в силе;
2. перевод незакрытых уведомлений в `skipped`;
3. затирание персональных полей (имя, username, телефон, язык);
4. замену `telegram_id` на служебный отрицательный — новое обращение создаст новый аккаунт;
5. деактивацию аккаунта и запись `user.anonymize` в `audit_logs`.

Клинические данные (диагнозы, исследования) сервис не хранит вообще, поэтому анонимизация ПДн
и есть удаление. Юридическое соответствие требованиям законодательства требует отдельной проверки
юристом.

## Разработка и качество

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q          # без TEST_DATABASE_URL интеграционные тесты пропускаются
ruff check .       # lint
mypy app tests     # проверка типов

cd frontend
npm run typecheck  # tsc
npm run test       # vitest
npm run build      # сборка Mini App
```

- CI (GitHub Actions): `lint`, `typecheck`, `tests` с сервисом Postgres 16 и применением миграций,
  отдельная джоба `frontend` (typecheck → vitest → build);
- в репозитории 107 тестовых функций в 20 файлах `tests/` и 14 тестов фронтенда: initData, JWT, права
  и tenant isolation, бронирование и гонка за слот, пересечения приёмов, лимит 2 часов, уведомления
  и дедупликация, worker, приватность, rate limiting, i18n и API-клиент;
- падение pytest печатает хвост лога в аннотациях check-run — видно без доступа к логам.

## Документация

- [ARCHITECTURE.md](ARCHITECTURE.md) — полное описание системы: домен, слои, инварианты, решения.
- [CODE.md](CODE.md) — карта кода: что где лежит и зачем.
- [deploy/README.md](deploy/README.md) — пошаговое первое развёртывание на VPS.

## Деплой

- VPS Ubuntu 24.04 LTS, Docker Compose: `api`, `worker`, статика Mini App, Nginx;
- БД и Storage — внешний Supabase, локальная Postgres в production не поднимается;
- один домен `avela.jaraslau.dev`: Mini App — `/`, API — `/api/*`, status page — `/status/`;
- DNS — Cloudflare, TLS Full (strict), сертификаты в `deploy/certs`.

```bash
# на сервере, в каталоге репозитория
cp .env.example .env          # BOT_TOKEN, DATABASE_URL, JWT_SECRET, WEBHOOK_*
mkdir -p deploy/certs         # fullchain.pem и privkey.pem
docker compose -f docker-compose.prod.yml up -d --build
```

- `deploy/nginx/avela.conf` — TLS и маршрутизация одного origin (CORS внутри домена не нужен);
- `docker-compose.prod.yml` — api, worker, web, nginx;
- `.github/workflows/deploy.yml` — `workflow_dispatch` с обязательным `confirm=yes`; шаг выката
  включается только при переменной репозитория `DEPLOY_ENABLED=true` и секретах `DEPLOY_HOST`,
  `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`;
- `deploy/setup-vps.sh` — установка Docker и swap, клонирование репозитория в `/opt/avela`.

## Лицензия

Проект **source-available** по [Avela Source-Available License 1.0](LICENSE): код можно
просматривать, скачивать и запускать для личного некоммерческого ознакомления.
Изменение, распространение, публикация, хостинг и коммерческое использование — только
с письменного разрешения правообладателя. Гарантий нет, ПО поставляется «как есть».

Пул-реквесты и патчи принимаются только по согласованию с владельцем: отправляя вклад,
вы соглашаетесь с условиями лицензии. Автор — **Jaraslau Kunin**
([@jaraslaukunin](https://github.com/jaraslaukunin)).

---

<div align="center">

**[github.com/jaraslaukunin/avela-telegram-bot](https://github.com/jaraslaukunin/avela-telegram-bot)** — поставьте ⭐, если проект оказался полезен.

</div>
