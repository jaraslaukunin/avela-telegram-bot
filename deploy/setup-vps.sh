#!/usr/bin/env bash
# Первый запуск Avela на VPS (Ubuntu 24.04 LTS).
#
# Запускать НА СЕРВЕРЕ:
#   bash setup-vps.sh
#
# Скрипт идемпотентен: повторный запуск пропускает уже сделанное.
set -euo pipefail

echo "== 1. Docker + Compose plugin =="
if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
  echo "docker уже установлен"
fi

echo "== 2. Swap 1G (у VPS всего 2 ГБ ОЗУ — защита от OOM при сборке) =="
if swapon --show | grep -q .; then
  echo "swap уже есть"
else
  fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "swap создан"
fi

echo "== 3. Код =="
APP_DIR=${1:-/opt/avela}
if [ ! -d "$APP_DIR/.git" ]; then
  git clone https://github.com/jaraslaukunin/avela-telegram-bot.git "$APP_DIR"
fi
cd "$APP_DIR"

echo "== 4. Настройки =="
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "Создан $APP_DIR/.env — заполни его и запусти скрипт ещё раз."
  echo "Минимум: BOT_TOKEN, DATABASE_URL (Supabase session pooler, драйвер asyncpg),"
  echo "JWT_SECRET (свой, от 32 символов), CORS_ORIGINS."
  echo "WEBHOOK_MODE оставь false до настройки DNS и сертификатов."
  exit 0
fi

echo "== 5. Каталог сертификатов =="
mkdir -p deploy/certs

echo "== 6. Сборка и запуск =="
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps

echo ""
echo "Проверка:"
echo "  curl http://127.0.0.1:8000/health   (или снаружи: http://IP/health не будет —"
echo "                                       80-й порт отдаёт nginx; пока DNS не настроен,"
echo "                                       проверяй локально на сервере)"
echo "  docker compose -f docker-compose.prod.yml exec api curl -fsS http://127.0.0.1:8000/ready"
echo ""
echo "Демо-данные для первой записи:"
echo "  docker compose -f docker-compose.prod.yml exec api python -m app.cli seed-demo"
