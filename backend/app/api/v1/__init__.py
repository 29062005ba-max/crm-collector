from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.debtors import router as debtors_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.operations import (
    promises_router,
    payments_router,
    calls_router,
    csi_router,
)
from app.api.v1.endpoints.dashboard import dashboard_router, import_router
from app.api.v1.endpoints.management import router as management_router
from app.api.v1.endpoints.zadarma import router as zadarma_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(debtors_router)
api_router.include_router(contracts_router)
api_router.include_router(promises_router)
api_router.include_router(payments_router)
api_router.include_router(calls_router)
api_router.include_router(csi_router)
api_router.include_router(dashboard_router)
api_router.include_router(import_router)
api_router.include_router(management_router)
api_router.include_router(zadarma_router)

# SaaS feature routers
from app.api.v1.endpoints.saas import (
    tasks_router,
    notifications_router,
    activity_router,
    schedules_router,
    dashboard_kpi_router,
    workflow_router,
)
api_router.include_router(tasks_router)
api_router.include_router(notifications_router)
api_router.include_router(activity_router)
api_router.include_router(schedules_router)
api_router.include_router(dashboard_kpi_router)
api_router.include_router(workflow_router)

# Pack 2: Tasks extended endpoints (stats, created, status PATCH, list with filters)
from app.api.v1.endpoints.tasks_extra import router as tasks_extra_router
api_router.include_router(tasks_extra_router)

# Multi-tenancy
from app.api.v1.endpoints.companies import router as companies_router
api_router.include_router(companies_router)

# Admin & observability
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.metrics import router as metrics_router
api_router.include_router(admin_router)
api_router.include_router(metrics_router)

# GDPR
from app.api.v1.endpoints.gdpr import router as gdpr_router
api_router.include_router(gdpr_router)

# Billing
from app.api.v1.endpoints.billing import router as billing_router
api_router.include_router(billing_router)

# === v2: Call Queue (auto-dial) ===
from app.api.v1.endpoints.call_queue import router as call_queue_router
api_router.include_router(call_queue_router)

# === v2: Scoring ===
from app.api.v1.endpoints.scoring import router as scoring_router
api_router.include_router(scoring_router)

# === v3: My Day (план менеджера) ===
from app.api.v1.endpoints.my_day import router as my_day_router
api_router.include_router(my_day_router)

# === v3: Analytics (контрольная панель руководителя) ===
from app.api.v1.endpoints.analytics import router as analytics_router
api_router.include_router(analytics_router)
