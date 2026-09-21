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

- бот в чате: `/start`, «Записаться на приём» (клиника → услуга → филиал →
  врач или «любой свободный врач» → слот → подтверждение), «Мои записи»
  (отмена и перенос с дедлайном 2 часа), понятные ответы, когда данных или
  свободных слотов нет, и заглушка на нераспознанные сообщения;
- FastAPI: `/health`, `/ready`, публичный `/status` (состояние компонентов);
- webhook-роут `/telegram/webhook` с проверкой
  `X-Telegram-Bot-Api-Secret-Token` (включается через `WEBHOOK_MODE=true`);
- серверная валидация Telegram Mini App initData: HMAC-SHA256,
  constant-time сравнение, срок годности `auth_date`, разбор пользователя
  (`app/core/security/initdata.py`);
- вход через initData → короткоживущий JWT Avela, профиль `/auth/me`;
- каталог: сети, филиалы, услуги, врачи, свободные слоты;
- записи пациента: создание, свои записи, отмена и перенос с дедлайном
  2 часа (в часовом поясе филиала), защита от гонок и пересечений;
- админ-API `/admin/*`: роли, изоляция сетей, врачи, шаблоны расписания
  с генерацией слотов, отмена записей администратором, аудит действий;
- worker уведомлений: очередь в БД, дедупликация, отправка сразу после
  записи, напоминания за 24ч и 2ч, гашение напоминаний отменённых записей,
  heartbeat для status page;
- удаление аккаунта по запросу пациента: отмена активных записей,
  анонимизация ПДн, запись в аудит (`POST /privacy/delete-me`);
- защита API: строгий CORS, rate limiting, security headers, request id
  в логах и ответах;
- Telegram Mini App (React + TypeScript): запись, мои записи, перенос,
  профиль, i18n ru/en/be-Latn;
- status page: `status/index.html`, читает `/status`.

## Админ-API

Все `/admin/*` требуют роль администратора (проверяется на backend
для каждого действия):

- сети: создание (только администратор Avela), просмотр, переименование,
  активация и блокировка;
- филиалы: создание в своей сети, обновление, назначение администратора
  филиала; часовой пояс филиала — IANA identifier (по умолчанию
  `Europe/Moscow`);
- услуги: создание и обновление в своей сети (длительность приёма — из услуги);
- врачи: создание в своём филиале, привязка услуг;
- расписание: регулярные шаблоны (день недели + интервал) и генерация
  слотов на период (повторная генерация идемпотентна);
- записи: просмотр по своим филиалам, отмена администратором (без лимита
  2 часов).

Границы видимости: администратор филиала — только свои филиалы,
администратор сети — только своя сеть, администратор Avela — всё.
Ресурс вне зоны видимости отдаёт 404, чтобы не раскрывать чужие данные.
Каждое административное изменение пишется в `audit_logs`.

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

- React, TypeScript, Vite, Telegram Web Apps SDK (типы `window.Telegram.WebApp`
  объявлены локально — внешний npm-пакет не нужен);
- React Router, TanStack Query;
- i18n: русский, English, беларуская лацінка (be-Latn);
- Vitest (React Testing Library подключена для компонентных тестов).

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
  main.py         # FastAPI: lifespan, webhook, middleware
  config.py       # настройки (pydantic-settings)
  api/            # роутеры: auth, catalog, appointments, admin, privacy, health
  core/           # security (initdata, jwt), deps, middleware, rate_limit, logging, roles
  services/       # use cases: booking, scheduling, notifications, privacy, audit, permissions
  models/         # SQLAlchemy: каталог, расписание, записи, уведомления, аудит
  bot/            # aiogram: webhook-роутер, хендлеры, клавиатуры
  worker/         # APScheduler: отправка уведомлений и напоминаний
frontend/         # Telegram Mini App (React + TypeScript + Vite)
status/           # публичная status page (статика)
supabase/         # SQL-миграции, RLS, config.toml
deploy/           # Nginx-конфиг, сертификаты
.github/workflows # CI и ручной деплой
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
`/health`, `/ready`, `/status` и webhook-роут. Параллельно бот работает
на polling (webhook удаляется при старте — удобно для разработки).
В production (`WEBHOOK_MODE=true`) обновления принимает webhook на Nginx.

Отдельно запускаются worker и Mini App:

```bash
python -m app.worker.main        # уведомления и напоминания (один процесс!)

cd frontend && npm install && npm run dev   # Mini App на 127.0.0.1:5173
```

## Разработка

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q          # тесты (без TEST_DATABASE_URL интеграционные пропускаются)
ruff check .       # lint
mypy app           # проверка типов

cd frontend
npm run typecheck  # tsc
npm run test       # vitest
npm run build      # сборка Mini App
```

## Локальная база данных

```bash
docker compose -f docker-compose.dev.yml up -d db
for file in supabase/migrations/*.sql; do
  docker compose -f docker-compose.dev.yml exec -T db \
    psql -U avela -d avela -v ON_ERROR_STOP=1 -f "/migrations/$(basename "$file")"
done
TEST_DATABASE_URL=postgresql+asyncpg://avela:avela@localhost:5432/avela pytest -q
```

Схема управляется только SQL-миграциями в `supabase/migrations/`
(Supabase CLI; Alembic не используем). Пересечения слотов врача и записей
пациента запрещены на уровне PostgreSQL (exclusion constraint, частичный
уникальный индекс, триггер), а не только в коде.

## Подключение Supabase

Проект: `nctnayzkbcgobanxyabv` (`https://nctnayzkbcgobanxyabv.supabase.co`).

Миграции схемы — SQL-файлы в `supabase/migrations/`, применяются Supabase CLI
(Alembic не используем). Разово на машине разработчика:

```bash
brew install supabase/tap/supabase   # если CLI ещё не установлен
supabase login
supabase link --project-ref nctnayzkbcgobanxyabv
supabase db push
```

Ключи (`anon`, `service_role`) — в дашборде Supabase → Settings → API.
`service_role` живёт только в окружении backend (`.env`/секреты сервера)
и никогда не попадает в браузер. Строка подключения к production БД —
дашборд → Connect → Session pooler.

RLS включён на всех таблицах deny-by-default: backend ходит как владелец
схемы, прямой доступ через Supabase REST/anon ничего не видит.

## Работа без локальной БД (сразу с Supabase)

Docker и локальная Postgres не обязательны: приложение умеет работать прямо
с облачным Supabase.

```bash
# 1. Применить миграции (из корня репозитория)
supabase link --project-ref nctnayzkbcgobanxyabv
supabase db push

# 2. Взять строку подключения: дашборд → Connect → Session pooler
#    и прописать её в .env (важно: драйвер asyncpg)
#    DATABASE_URL=postgresql+asyncpg://postgres.nctnayzkbcgobanxyabv:ПАРОЛЬ@aws-0-eu-west-2.pooler.supabase.com:5432/postgres

# 3. Запустить приложение — оно пойдёт в облако
python -m app.main
python -m app.worker.main
```

`service_role` key — только серверным компонентам (backend и worker).
В frontend он не попадает никогда. Публикуемый ключ (`sb_publishable_...`)
для клиента в MVP не нужен: Mini App общается только с нашим API.

## Первые шаги в пустой базе

Свежая база пустая: сеть, филиал, услугу, врача и слоты создают администраторы
через API. Первого администратора Avela через API назначить нельзя — он
появляется служебной командой:

```bash
python -m app.cli show-state                  # что уже есть в базе
python -m app.cli grant-admin <telegram_id>   # роль avela_admin (после первого входа)
python -m app.cli seed-demo                   # демо-сеть, врач и слоты на 2 недели
```

`grant-admin` требует, чтобы пользователь уже существовал в базе: пусть он один
раз войдёт в Mini App (или напишет боту `/start`), и роль выдаётся по его
`telegram_id`. `seed-demo` идемпотентен: повторный запуск не дублирует данные,
а добирает недостающие слоты.

## Уведомления и worker

- уведомления не отправляются из web-процесса: сервисный слой только кладёт
  их в таблицу `notifications` со статусом `pending`;
- отдельный singleton-процесс `python -m app.worker.main` каждые
  `NOTIFIER_INTERVAL_SECONDS` секунд забирает готовые и отправляет;
- виды: `booking_created`, `reminder_24h`, `reminder_2h`, `cancelled`,
  `rescheduled`; дедупликация — уникальный индекс `(appointment_id, kind)`;
- напоминания отменённых и перенесённых записей переводятся в `skipped`,
  чтобы пациент не получил напоминание об отменённом приёме;
- worker отмечает heartbeat в `service_heartbeats` — это питает status page.

## Приватность и удаление данных

`POST /privacy/delete-me` (авторизованный пациент) выполняет:

1. отмену всех активных записей (пациент удаляет данные — приёмы не остаются в силе);
2. перевод незакрытых уведомлений в `skipped`;
3. затирание персональных полей (имя, username, телефон, язык);
4. замену `telegram_id` на служебный отрицательный — новое обращение создаст
   новый аккаунт;
5. деактивацию аккаунта и запись `user.anonymize` в `audit_logs`.

Клинические данные (диагнозы, исследования) мы не храним вообще, поэтому
анонимизация ПДн и есть удаление. Юридическое соответствие требованиям
законодательства требует отдельной проверки юристом.

## Status page

`status/index.html` — статика для `status.avela.jaraslau.dev`. Показывает
состояние API, БД, worker'а и способа доставки Telegram, обновляется каждые
30 секунд. Публичный JSON — `GET /status`. Страница не раскрывает секреты,
строки подключения, внутренние адреса и данные пациентов.

## Переменные окружения

См. `.env.example`. Секреты (BOT_TOKEN, ключи Supabase, webhook secret)
живут только в `.env` и в секретах окружения — в репозиторий не попадают.

Ключевые переменные: `BOT_TOKEN`, `DATABASE_URL` (asyncpg), `JWT_SECRET`
(минимум 32 символа), `JWT_TTL_SECONDS`, `WEBHOOK_MODE` + `WEBHOOK_SECRET` +
`WEBHOOK_BASE_URL`, `CORS_ORIGINS` (домены Mini App через запятую),
`NOTIFIER_INTERVAL_SECONDS`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Качество и CI

- lint (ruff), type-check (mypy), тесты — GitHub Actions; отдельная джоба
  фронтенда: `npm run typecheck`, `vitest`, `npm run build`;
- автоматизированные тест-кейсы: валидация initData, JWT-сессии, права
  и tenant isolation, бронирование и гонка за слот, пересечения записей
  пациента, лимит 2 часов, уведомления и дедупликация, worker, приватность,
  middleware и rate limiting, i18n и API-клиент Mini App;
- падение pytest печатает вывод в аннотациях check-run — видно без доступа
  к логам;
- staging/production deploy — только вручную и после подтверждения.

## Деплой

- VPS Ubuntu 24.04, Docker Compose: backend, worker, статика Mini App, Nginx;
- БД и Storage — Supabase (локальная БД в production не поднимается);
- webhook: `POST https://bot.avela.jaraslau.dev/telegram/webhook`;
- Mini App: `avela.jaraslau.dev`, API: `api.avela.jaraslau.dev`,
  status page: `status.avela.jaraslau.dev`;
- DNS — Cloudflare, TLS Full (strict).

```bash
# на сервере, в каталоге репозитория
cp .env.example .env          # заполнить секреты (BOT_TOKEN, DATABASE_URL, JWT_SECRET, WEBHOOK_*)
mkdir -p deploy/certs         # положить fullchain.pem и privkey.pem
docker compose -f docker-compose.prod.yml up -d --build
```

- `deploy/nginx/avela.conf` — TLS и маршрутизация доменов;
- `docker-compose.prod.yml` — api, worker, web, nginx;
- `.github/workflows/deploy.yml` — ручной выкат (workflow_dispatch) с
  подтверждением `confirm=yes`; по умолчанию шаг деплоя выключен, пока не
  задана переменная репозитория `DEPLOY_ENABLED=true` и секреты
  `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.

Деплой выполняется только после отдельного согласования: VPS, DNS,
сертификаты и GitHub Secrets настраиваются вручную.

## Автор

**Jaraslau Kunin** — Python-разработчик, GitHub: [@jaraslaukunin](https://github.com/jaraslaukunin)

## Лицензия

Проект source-available: код можно просматривать и скачивать, но изменение,
распространение и коммерческое использование — только с письменного
согласия владельца. Подробности в `LICENSE`.

Изменения принимаются только после согласования с владельцем.
