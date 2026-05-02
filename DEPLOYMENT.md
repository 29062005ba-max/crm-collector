# Production Deployment Guide

Пошаговая инструкция как развернуть CRM Collector на VPS для production использования.

---

## 1. Покупка VPS и домена

### VPS
**Hetzner Cloud CX22** — оптимально для старта:
- 2 vCPU
- 4 GB RAM
- 40 GB SSD
- Цена: ~5€/мес

Альтернативы: DigitalOcean, Vultr, Selectel (Россия), PS.kz (Казахстан).

**Локация:** для пользователей в РК выбирайте Falkenstein (Германия) — задержка ~50ms.

### Домен
Купите домен .kz или .com:
- ps.kz, hoster.kz — для .kz (~3500₸/год)
- Namecheap — для .com (~$10/год)

В DNS создайте A-запись:
```
crm.example.kz   A   <IP-адрес-VPS>
```

---

## 2. Настройка сервера (Ubuntu 24)

```bash
# Подключиться к VPS
ssh root@<IP>

# Обновить пакеты
apt update && apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com | sh

# Установить Docker Compose
apt install docker-compose-plugin -y

# Создать non-root пользователя
adduser crm
usermod -aG docker crm
usermod -aG sudo crm

# Настроить firewall
apt install ufw -y
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP (для Let's Encrypt)
ufw allow 443/tcp    # HTTPS
ufw enable
```

---

## 3. Загрузить проект

```bash
su - crm
mkdir crm-collector
cd crm-collector

# Загрузить zip через scp с локальной машины:
# scp crm-collector.zip crm@<IP>:/home/crm/

unzip crm-collector.zip
cd crm-collector
```

---

## 4. Настройка Let's Encrypt SSL

Замените self-signed сертификаты на настоящие.

```bash
# Установить certbot
sudo apt install certbot -y

# Получить сертификат (порт 80 должен быть свободен)
sudo certbot certonly --standalone -d crm.example.kz

# Скопировать сертификаты в проект
sudo cp /etc/letsencrypt/live/crm.example.kz/fullchain.pem infra/ssl/cert.pem
sudo cp /etc/letsencrypt/live/crm.example.kz/privkey.pem infra/ssl/key.pem
sudo chown crm:crm infra/ssl/*.pem
```

### Автоматическое обновление сертификата (раз в 60 дней)

```bash
sudo crontab -e
```
Добавить:
```
0 3 * * 1 certbot renew --deploy-hook "cp /etc/letsencrypt/live/crm.example.kz/*.pem /home/crm/crm-collector/infra/ssl/ && cd /home/crm/crm-collector/infra && docker-compose restart nginx"
```

---

## 5. Изменить production-настройки

### `infra/.env`
```env
# Database
DATABASE_URL=postgresql+asyncpg://crm:STRONG_PASSWORD_HERE@postgres:5432/crm_db
DATABASE_URL_SYNC=postgresql+psycopg2://crm:STRONG_PASSWORD_HERE@postgres:5432/crm_db
POSTGRES_USER=crm
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE
POSTGRES_DB=crm_db

# Auth
JWT_SECRET=GENERATE_WITH_openssl_rand_base64_32
JWT_ALGORITHM=HS256

# CORS
CORS_ORIGINS=["https://crm.example.kz"]

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Sentry (optional but recommended)
SENTRY_DSN=https://<project>@sentry.io/<project-id>
ENVIRONMENT=production

# App
DEBUG=false
APP_NAME=CRM Collector
APP_VERSION=1.0.0
```

### `infra/nginx.conf`
Замените `localhost` и `192.168.8.222` на ваш домен:
```
server_name crm.example.kz;
```

### `infra/docker-compose.yml`
Закройте порт 5432 от внешнего доступа — удалите `ports: 5432:5432` из postgres.
То же для Flower (если не нужен публичный доступ).

---

## 6. Запуск

```bash
cd infra
docker-compose up --build -d

# Проверить что все контейнеры здоровы
docker ps

# Логи
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

Откройте: `https://crm.example.kz`

Логин: `admin@crm.local` / `Admin1234!` — **ПОМЕНЯЙТЕ ПАРОЛЬ ЧЕРЕЗ UI СРАЗУ!**

---

## 7. Off-site бэкапы в S3

Локальные бэкапы в `infra/backups/` — это хорошо, но если VPS умрёт, всё потеряется.

### Backblaze B2 (дешевле S3)
1. Зарегистрироваться на backblaze.com (бесплатно 10GB)
2. Создать bucket `crm-backups`
3. Создать application key

### Cron задача для синхронизации
```bash
# Установить b2 CLI
pip install b2

# Авторизация
b2 authorize-account <KEY_ID> <APP_KEY>

# Cron task (ежедневно в 04:00)
crontab -e
```
Добавить:
```
0 4 * * * cd /home/crm/crm-collector/infra/backups && /usr/local/bin/b2 sync . b2://crm-backups/
```

---

## 8. Мониторинг

### Uptime Robot (бесплатно)
- Зарегистрироваться на uptimerobot.com
- Добавить мониторинг `https://crm.example.kz/health`
- Алерты в Telegram/Email при падении

### Sentry (Error tracking)
- Зарегистрироваться на sentry.io (бесплатно до 5000 событий/мес)
- Создать проект FastAPI
- Скопировать DSN в `.env` (SENTRY_DSN=...)
- Restart docker-compose

### Логи в файл
```bash
# Создать systemd сервис который сохраняет логи
sudo tee /etc/systemd/system/crm-logs.service << 'EOF2'
[Unit]
Description=CRM Logs Collector
After=docker.service

[Service]
Type=simple
User=crm
WorkingDirectory=/home/crm/crm-collector/infra
ExecStart=/bin/bash -c 'docker-compose logs -f --tail=100 > /var/log/crm.log 2>&1'

[Install]
WantedBy=multi-user.target
EOF2

sudo systemctl enable crm-logs
sudo systemctl start crm-logs

# Ротация логов
sudo tee /etc/logrotate.d/crm << 'EOF2'
/var/log/crm.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
EOF2
```

---

## 9. Безопасность production

- [ ] Отключить root SSH вход (`PermitRootLogin no` в `/etc/ssh/sshd_config`)
- [ ] Использовать SSH ключи вместо паролей
- [ ] Установить fail2ban (`apt install fail2ban`)
- [ ] **Сменить admin пароль** через UI после первого логина
- [ ] Закрыть порты 5432 (PostgreSQL) и 5555 (Flower) от внешнего доступа
- [ ] Поставить лимит на admin аккаунты (RBAC)
- [ ] Регулярно `apt upgrade`
- [ ] Включить unattended-upgrades для security patches

---

## 10. Создание тестов

Перед production обязательно прогнать тесты:

```bash
docker exec crm_backend pytest tests/ -v
```

---

## 11. Smoke test чек-лист

После деплоя проверьте:
- [ ] `https://crm.example.kz` открывается
- [ ] Логин админа работает
- [ ] Создание должника
- [ ] Импорт Excel
- [ ] Создание платежа
- [ ] Канбан загружается
- [ ] Уведомления (колокольчик)
- [ ] Бэкап работает: `docker logs crm_backup`
- [ ] Celery beat запускается: `docker logs crm_celery_beat`
- [ ] Flower доступен: `https://crm.example.kz:5555` (admin / Admin1234!)
- [ ] `/api/v1/admin/jobs` показывает задачи
- [ ] `/api/v1/metrics` возвращает данные

---

## 12. Аварийное восстановление

### Если VPS упал
1. Развернуть новый VPS
2. Восстановить из off-site бэкапа (Backblaze):
```bash
b2 sync b2://crm-backups/ ./backups/
```
3. Запустить контейнеры
4. Восстановить БД:
```bash
docker exec crm_backup /usr/local/bin/restore.sh crm_backup_LATEST.sql.gz
```

### Если потерялся пароль admin
```bash
docker exec -it crm_postgres psql -U crm crm_db
UPDATE users SET hashed_password = '<bcrypt-hash>' WHERE email = 'admin@crm.local';
```

### Если БД повреждена
```bash
# Восстановить из последнего бэкапа
ls infra/backups/
docker exec crm_backup /usr/local/bin/restore.sh <filename>
```
