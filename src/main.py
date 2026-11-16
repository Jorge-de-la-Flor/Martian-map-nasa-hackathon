import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routes.boxwork import router as boxwork_router
from api.routes.health import router as health_router
from api.routes.mission import router as mission_router
from core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Mars exploration and terrain-aware route-planning API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(mission_router, prefix="/api")
app.include_router(boxwork_router, prefix="/api")


# En producción (Docker) el mismo servidor entrega el frontend ya compilado: un solo link.
# Solo se activa si se define MARTIAN_MAP_FRONTEND_DIST (lo hace el Dockerfile);
# en desarrollo y en los tests "/" sigue devolviendo el estado de la API.
FRONTEND_DIST = os.getenv("MARTIAN_MAP_FRONTEND_DIST")

if FRONTEND_DIST and (Path(FRONTEND_DIST) / "index.html").is_file():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
        }
