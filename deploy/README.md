# Деплой Avela на VPS — поэтапно

VPS: Ubuntu 24.04 LTS, 2 vCPU / 2 GB RAM / 30 GB NVMe.
БД и Storage — внешний Supabase (на VPS базы нет).
Домен: `jaraslau.dev` в Cloudflare.

Каждый этап можно проверить до перехода к следующему — никаких
«выкатил всё сразу».

## Этап 1. Базовый сервер

На сервере (root):

```bash
curl -fsSL https://raw.githubusercontent.com/jaraslaukunin/avela-telegram-bot/main/deploy/setup-vps.sh -o setup-vps.sh
bash setup-vps.sh
```

Первый прогон ставит Docker и swap, клонирует репозиторий в `/opt/avela`
и создаёт `.env`. Заполнить `.env` и прогнать скрипт ещё раз.

Что писать в `.env` на сервере:

```ini
BOT_TOKEN=...                          # токен @avela_med_bot
WEBHOOK_MODE=false                     # СНАЧАЛА false — запускаемся на polling
DATABASE_URL=postgresql+asyncpg://postgres.nctnayzkbcgobanxyabv:ПАРОЛЬ@aws-0-eu-west-2.pooler.supabase.com:5432/postgres
JWT_SECRET=<свой длинный секрет 32+ символов>
CORS_ORIGINS=https://avela.jaraslau.dev,https://staging.avela.jaraslau.dev
NOTIFIER_INTERVAL_SECONDS=30
```

Строку подключения взять: дашборд Supabase → Connect → Session pooler
(хост пулера для этого проекта — `aws-0-eu-west-2.pooler.supabase.com`).

## Этап 2. Проверка API и worker'а без доменов

```bash
docker compose -f docker-compose.prod.yml exec api curl -fsS http://127.0.0.1:8000/ready
#   {"status":"ok","checks":{"database":"ok"}}  ← связь с Supabase есть
docker compose -f docker-compose.prod.yml exec api python -m app.cli seed-demo
#   демо-клиника, врач и слоты на 14 дней
```

На этом этапе бот уже работает на polling: можно открыть @avela_med_bot,
нажать «Записаться» и пройти весь флоу — данные и запись живут в облаке.

## Этап 3. DNS в Cloudflare

A-записи на IP VPS (проксирование включено):

| Запись | Значение |
| --- | --- |
| avela | IP VPS |
| api | IP VPS |
| bot | IP VPS |
| status | IP VPS |
| staging | IP VPS |
| api.staging | IP VPS |

## Этап 4. TLS-сертификаты и webhook

1. Cloudflare → SSL/TLS → Origin Server → Create Certificate (или
   Let's Encrypt) — положить `fullchain.pem` и `privkey.pem` в
   `deploy/certs/` на сервере.
2. В `.env`: `WEBHOOK_MODE=true`, `WEBHOOK_SECRET=<случайная строка>`,
   `WEBHOOK_BASE_URL=https://avela.jaraslau.dev/api`.
3. `docker compose -f docker-compose.prod.yml up -d --build`
4. Проверить: `curl https://avela.jaraslau.dev/api/status`

## Этап 5. Mini App

1. Сборка уже идёт с `VITE_API_URL=https://avela.jaraslau.dev/api`
   (значение по умолчанию в docker-compose.prod.yml).
2. В BotFather для @avela_med_bot: Bot Settings → Menu Button →
   URL = `https://avela.jaraslau.dev`.
3. Открыть бота → кнопка → Mini App → «Записаться».

## Этап 6. Приёмка

- запись из Mini App и из чата бота;
- «Мои записи», отмена и перенос;
- уведомления приходят в чат (worker);
- `https://avela.jaraslau.dev/status/` показывает api/database/worker.

## Полезное

```bash
cd /opt/avela
docker compose -f docker-compose.prod.yml ps            # что запущено
docker compose -f docker-compose.prod.yml logs -f api   # логи API
docker compose -f docker-compose.prod.yml logs -f worker
git pull --ff-only && docker compose -f docker-compose.prod.yml up -d --build  # обновление
```
