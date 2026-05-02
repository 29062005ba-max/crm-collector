# Enterprise Architecture Upgrade — Этап 2

## Что сделано

### ✅ Background Workers (Celery + Redis)
- **APScheduler удалён** из `main.py`
- Workflow перенесён в **Celery tasks** с разделением по очередям:
  - `workflow_queue` — обработка просрочек обещаний, fan-out по компаниям
  - `notification_queue` — отправка уведомлений (быстрая очередь для responsive UI)
  - `schedule_queue` — пересчёт статусов графиков
  - `kpi_queue` — heavy-aggregations для дашборда
  - `default` — служебные (cleanup и т.п.)
- **Celery Beat** — планировщик cron-задач:
  - `process-overdue-promises` — каждый час
  - `process-overdue-schedules` — каждый час (+5 мин offset)
  - `recalculate-daily-kpi` — ежедневно в 02:00
  - `process-pending-events` — каждые 30 мин (event log catch-up)
  - `cleanup-idempotency-keys` — ежедневно в 04:00
- **Flower** — UI мониторинга на порту `5555` (admin/Admin1234!)

### ✅ Event-Driven Architecture
- `app/events/` — domain events + EventBus
- Доменные события:
  - `debtor.created`, `payment.created`, `promise.created`
  - `payment.missed`, `schedule.overdue`, `task.created`, `status.changed`
- Каждое событие:
  1. Сохраняется в `event_log` (event sourcing)
  2. Запускает sync handlers (в той же транзакции)
  3. Триггерит Celery task для async handlers

### ✅ Idempotency (защита от дублей)
- Таблица `idempotency_keys` — TTL 24h
- Helper `app/core/idempotency.py`:
  - `check_idempotency()` — проверка `Idempotency-Key` header
  - `save_idempotency_response()` — сохранение результата
- При повторе с тем же ключом → возвращается сохранённый response
- При том же ключе но другом теле → 409 Conflict

### ✅ Concurrency Safety
- `app/core/locking.py`:
  - `get_for_update()` — `SELECT ... FOR UPDATE`
  - `increment_version()` — optimistic locking
- Колонка `version` добавлена в: debtors, contracts, promises, payments, payment_schedules

### ✅ Observability
- **Structured JSON logging** (`app/core/logging_config.py`)
- Таблица `background_jobs` — tracking всех Celery задач:
  - status (pending/running/success/failed/retry)
  - attempts
  - args/result/error
  - timestamps
- `correlation_id` в activity_logs — связь между событиями одной операции

### ✅ Retry + Failure Handling
- Все задачи: `autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=5`
- `acks_late=True` — ack только после успешного выполнения
- `task_reject_on_worker_lost=True` — переотправка при падении worker
- Catch-up job `process_pending_events` — ловит unprocessed events

## Архитектура

```
┌────────────────────────────────────────────────────┐
│                   Nginx (HTTPS)                     │
└──────────────────────┬─────────────────────────────┘
                       │
            ┌──────────▼───────────┐
            │   FastAPI Backend     │  ← только HTTP API
            │   (main.py)           │
            └──┬─────────────┬──────┘
               │             │
       publish event    enqueue task
               │             │
            ┌──▼─────────────▼──┐
            │      REDIS         │  ← broker
            └──┬─────────────────┘
               │
       ┌───────▼─────────┐
       │  Celery Worker   │  ← consumes 5 queues
       │  Celery Beat     │  ← cron scheduler
       └──┬───────────────┘
          │
   ┌──────▼──────┐
   │ PostgreSQL  │  ← state + event_log + jobs
   └─────────────┘
```

## Управление

### Запуск всех сервисов
```cmd
cd infra
docker-compose up -d
```

Сервисы:
- `crm_postgres` — БД
- `crm_redis` — broker
- `crm_backend` — FastAPI (HTTPS через nginx)
- `crm_celery_worker` — обработчик задач
- `crm_celery_beat` — планировщик
- `crm_flower` — мониторинг (http://localhost:5555)
- `crm_frontend` — Next.js
- `crm_nginx` — SSL termination
- `crm_backup` — pg_dump cron

### Просмотр Celery
```cmd
REM Все воркеры
docker exec crm_celery_worker celery -A app.celery_app inspect active

REM Зарегистрированные задачи
docker exec crm_celery_worker celery -A app.celery_app inspect registered

REM UI
http://localhost:5555 (admin / Admin1234!)
```

### Ручной запуск задачи
```cmd
docker exec crm_backend python -c "
from app.tasks.workflow import process_overdue_promises_for_company
process_overdue_promises_for_company.delay(1)
"
```

### Логи
```cmd
docker logs crm_celery_worker --tail 50
docker logs crm_celery_beat --tail 30
```

## API Idempotency

Для critical operations используйте header:
```
POST /api/v1/payments/
Idempotency-Key: payment-2026-04-25-12345
Content-Type: application/json

{...}
```

Повторный POST с тем же ключом и телом → вернёт сохранённый ответ без создания дубля.
Повторный POST с тем же ключом но другим телом → 409 Conflict.

## Что осталось для Production

- [ ] Sentry интеграция (есть hook в logging)
- [ ] Prometheus metrics endpoint
- [ ] Dead Letter Queue (Celery `task_reject_on_worker_lost` частично решает)
- [ ] Multi-worker setup (по очередям на разные машины)
- [ ] Redis Sentinel для HA
- [ ] PostgreSQL replica для read queries в KPI
