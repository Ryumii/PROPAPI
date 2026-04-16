from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_settings
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.batch import router as batch_router
from app.routers.billing import router as billing_router
from app.routers.dashboard import router as dashboard_router
from app.routers.hazard import router as hazard_router
from app.routers.health import router as health_router
from app.routers.inspect import router as inspect_router
from app.routers.zoning import router as zoning_router

validate_settings()

app = FastAPI(
    title="PropAPI",
    description="土地調査統合 API プラットフォーム",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(inspect_router)
app.include_router(batch_router)
app.include_router(hazard_router)
app.include_router(zoning_router)
app.include_router(billing_router)
