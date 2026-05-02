# 📞 CRM Collector

> Multi-tenant SaaS-платформа для коллекторских агентств с auto-dial очередью, scoring должников, KPI-аналитикой и Event-driven backend.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Возможности

- 🔥 **Скоринг должников** — автоматический score (0-100) по 9 факторам, ежедневный пересчёт
- 📞 **Auto-dial очередь** — atomic SELECT FOR UPDATE SKIP LOCKED, lock 5 минут на менеджера
- 📅 **План на день** — агрегатор HOT-должников, обещаний на сегодня, просроченных
- 👑 **Контрольная панель** — KPI команды в real-time, leaderboard, виджет Leakage
- 🎯 **Auto-fulfilled Promise** — обещание автоматически закрывается при платеже ≥95% от суммы
- 🏢 **Multi-tenancy** — полная изоляция данных между компаниями
- 📊 **Аналитика** — KPI-снимки каждый час (Celery Beat), 30-дневные графики сборов
- 🎨 **Канбан** — drag&drop статусы в воронке (новый → контакт → обещание → оплачено)
- 🛡️ **JWT + RBAC** — Manager / Head / Admin, rate limiting через Redis

---

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────┐
│   Next.js 14    │────▶│   Nginx      │
│   (Frontend)    │     │   (Reverse)  │
└─────────────────┘     └──────┬───────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
          ┌──────────────┐         ┌──────────────┐
          │   FastAPI    │◀───────▶│    Redis     │
          │   (Async)    │         │  (Cache+MQ)  │
          └──────┬───────┘         └──────┬───────┘
                 │                        │
                 ▼                        ▼
         ┌──────────────┐          ┌─────────────┐
         │  PostgreSQL  │          │   Celery    │
         │   (Async)    │          │   Worker    │
         └──────────────┘          └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  Celery     │
                                   │  Beat       │
                                   └─────────────┘
```

**9 контейнеров:** nginx · frontend · backend · postgres · redis · celery_worker · celery_beat · flower · backup

---

## 🚀 Quick Start

### Требования

- Docker Desktop
- 4GB RAM минимум
- Windows 10+ / macOS / Linux

### Запуск

```bash
git clone https://github.com/Arsen0701/crm-collector.git
cd crm-collector
cp .env.example .env
docker-compose -f infra/docker-compose.yml up --build -d
```

Откройте https://localhost (self-signed cert).

**Default credentials:**
```
Email:    admin@crm.local
Password: Admin1234!
```

---

## 📁 Структура проекта

```
crm-collector/
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── api/v1/             # REST endpoints
│   │   ├── models/             # SQLAlchemy 2.0 ORM
│   │   ├── services/           # Business logic
│   │   ├── repositories/       # Data access
│   │   ├── events/             # Event Bus + handlers
│   │   ├── tasks/              # Celery tasks
│   │   └── core/               # Config, security
│   └── alembic/versions/       # Migrations
│
├── frontend/                   # Next.js 14 + TypeScript
│   ├── app/                    # Pages (App Router)
│   ├── components/             # React components
│   └── lib/                    # API client, auth
│
├── infra/                      # Docker, nginx, backup
└── README.md
```

---

## 🛠️ Стек

| Слой | Технология |
|---|---|
| Backend | FastAPI 0.111 + SQLAlchemy 2.0 (async) + Alembic |
| Frontend | Next.js 14 + TypeScript + Tailwind + Recharts |
| Database | PostgreSQL 16 (asyncpg driver) |
| Queue | Celery 5.3 + Redis 7 |
| Auth | JWT (access 30m + refresh 7d) + bcrypt |
| Monitoring | Flower (Celery UI) + Sentry skeleton |
| Deploy | Docker Compose + Nginx reverse proxy |

---

## 🧪 Бизнес-процессы

### 1. Цикл взыскания

```
Импорт должника → Scoring → Очередь обзвона → Звонок → Обещание → Платёж → Auto-fulfill
                     ↓                                                          ↓
                  Скрининг                                                  Audit log
                     ↓                                                          ↓
                  KPI snapshot ← ──── ─── ─── ─── ─── ─── ─── ─── ─── Контрольная панель
```

### 2. Атомарная очередь обзвона

`SELECT FOR UPDATE SKIP LOCKED` гарантирует что один должник попадёт **только одному** менеджеру одновременно. Lock 5 минут — если менеджер не успел, должник возвращается в очередь.

### 3. Auto-fulfill Promise

Когда менеджер регистрирует платёж:

1. Event Bus публикует `payment.created`
2. Handler `on_payment_auto_fulfill_promise` ищет ближайшее активное обещание по `contract_id`
3. Если `payment.amount >= 0.95 * promise.amount` → `Promise.status = "fulfilled"`
4. Идемпотентность через `Promise.fulfilled_by_payment_id`
5. Запись в `activity_logs` (audit)

---

## 📊 KPI и метрики

- **PTP Conversion %** — kept / given × 100
- **Promise Fulfillment Rate** — kept / (kept + broken) × 100
- **Auto-Fulfilled** — обещания закрытые системой автоматически
- **Reach Rate** — % дозвонов
- **Leakage** — сорванные обещания (потери)

KPI обновляются автоматически каждый час в `:15` (Celery Beat).

---

## 🛡️ Безопасность

- ✅ JWT + Refresh tokens
- ✅ Rate limiting (slowapi + Redis): 10 login/min, 200 общий
- ✅ Tenant isolation на уровне SQL (`company_id` фильтр)
- ✅ RBAC через `require_roles("ADMIN", "HEAD")`
- ✅ Bcrypt + 72-byte truncation
- ✅ Idempotency keys на критичных POST
- ✅ Audit log всех действий

---

## 🚧 Roadmap

- [x] Module 1: Auto-dial очередь
- [x] Module 2: Скоринг должников
- [x] Module 3: План на день
- [x] Module 4: Контрольная панель + KPI snapshots
- [ ] Module 5: SMS-кампании (Twilio integration)
- [ ] Module 6: AI-анализ записей звонков (transcription + sentiment)
- [ ] Module 7: Mobile app (React Native)

---

## 📝 Лицензия

MIT — см. файл [LICENSE](LICENSE)

---

## 👤 Автор

**Arsen Baiturbai** — [@Arsen0701](https://github.com/Arsen0701)

---

<p align="center">Made with ❤️ in Almaty</p>
