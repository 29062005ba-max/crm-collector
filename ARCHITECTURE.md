# CRM Collector — SaaS Architecture

## ROADMAP

### ✅ Этап 1: Foundation
- [x] Миграция 0003: tasks, notifications, activity_logs, payment_schedules, kanban_status
- [x] SaaS endpoints: /tasks, /notifications, /activity-logs, /schedules, /kanban, /dashboard-kpi, /workflow
- [x] Workflow Engine (APScheduler hourly)
- [x] Frontend: Канбан, Задачи, Уведомления-колокольчик, расширенный Dashboard
- [x] Activity Log с auto kanban-переходами

### ✅ Этап 1.5: Multi-tenancy + Backups (этот этап)
- [x] **Миграция 0004**: companies, company_id во все основные таблицы, soft delete (deleted_at), audit v2 (old_value/new_value)
- [x] **Модели**: Company, TenantMixin, SoftDeleteMixin
- [x] **Companies API**: CRUD + /me со статистикой использования
- [x] **Tenant isolation в КАЖДОМ endpoint**:
  - debtors (5 endpoints)
  - contracts (5 endpoints)
  - promises (6 endpoints)
  - payments (6 endpoints)  
  - calls (2 endpoints)
  - csi (3 endpoints)
  - tasks (6 endpoints)
  - notifications (4 endpoints)
  - activity-logs (2 endpoints)
  - schedules (3 endpoints)
  - kanban (3 endpoints)
  - dashboard-kpi (2 endpoints)
  - workflow (1 endpoint)
- [x] **Services tenant-aware**: DebtorService, ContractService, PromiseService, PaymentService, CallLogService, TaskService, NotificationService, ActivityLogService, PaymentScheduleService, WorkflowService, DashboardKPIService
- [x] **Workflow Engine** обрабатывает все компании отдельно
- [x] **Soft delete** для debtors/contracts/promises/payments/tasks
- [x] **Тарифные лимиты**: проверка max_debtors при создании
- [x] **Backup сервис** (Docker контейнер):
  - Cron @ 03:00 Almaty time
  - pg_dump + gzip
  - Хранение 30 дней
  - Автоматическая очистка старых
  - Скрипт восстановления
- [x] **entrypoint.sh** создаёт default company + admin с company_id=1

### ⏳ Этап 2: Production Hardening
- [ ] Unit-тесты (pytest)
- [ ] Integration-тесты (TestClient)
- [ ] Sentry для error tracking
- [ ] Prometheus + Grafana
- [ ] structlog для structured logging
- [ ] CI/CD (GitHub Actions)
- [ ] Off-site бэкапы (S3/Backblaze)
- [ ] Rate limiting (slowapi)

### ⏳ Этап 3: Scale & Monetization
- [ ] PostgreSQL read replicas
- [ ] Celery + Redis вместо APScheduler
- [ ] CDN для статики
- [ ] Billing (Stripe/Kaspi)
- [ ] Webhook API
- [ ] Mobile app (React Native)
- [ ] Frontend для управления компаниями (admin panel)

## Tenant Isolation Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Request                        │
│              Authorization: Bearer <JWT>                 │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────▼───────────────┐
        │  get_current_user(token)      │
        │  → User { id, company_id }    │
        └───────────────┬───────────────┘
                        │
        ┌───────────────▼────────────────┐
        │  get_current_company()         │
        │  → Company { id, tariff, ... } │
        └───────────────┬────────────────┘
                        │
        ┌───────────────▼─────────────────────┐
        │  Endpoint                            │
        │   service = Service(db,              │
        │            company_id=company.id)    │
        │   → all queries filtered by tenant   │
        └──────────────────────────────────────┘
```

## RBAC матрица

| Действие | Admin | Head | Manager |
|----------|-------|------|---------|
| Просмотр всех должников своей компании | ✓ | ✓ | свои (assigned) |
| Создание должников (в пределах лимита) | ✓ | ✓ | ✗ |
| Назначение менеджеров | ✓ | ✓ | ✗ |
| Workflow trigger вручную | ✓ | ✓ | ✗ |
| Управление компаниями (все tenants) | ✓ | ✗ | ✗ |
| Управление пользователями | ✓ | ✗ | ✗ |
| Создание/удаление tenants | ✓ | ✗ | ✗ |

## Безопасность

1. **JWT** access (30 мин) + refresh (7 дней)
2. **bcrypt** salt rounds 10
3. **HTTPS** Nginx termination
4. **Tenant isolation** на каждом endpoint и в каждом сервисе
5. **Soft delete** для финансовых данных (нельзя физически удалить)
6. **Audit Log v2** с old_value/new_value (JSONB)
7. **IP + User-Agent логирование** в activity_logs
8. **Foreign keys ON DELETE RESTRICT** для company_id (нельзя удалить компанию с данными)
9. **Тарифные лимиты** проверяются на уровне API
