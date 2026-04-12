from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.batch import router as batch_router
from app.routers.hazard import router as hazard_router
from app.routers.health import router as health_router
from app.routers.inspect import router as inspect_router
from app.routers.zoning import router as zoning_router

app = FastAPI(
    title="REAPI",
    description="土地調査統合 API プラットフォーム",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(inspect_router)
app.include_router(batch_router)
app.include_router(hazard_router)
app.include_router(zoning_router)
