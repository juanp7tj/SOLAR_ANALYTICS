from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import CORS_ORIGINS, DATABASE_PATH, DEMO_AUTOLOAD, DISABLE_API_DOCS, ROOT_DIR, TRUSTED_HOSTS, TRUSTED_WRITE_ORIGINS
from app.db import Base, SessionLocal, engine
from app.routers import dashboard, data_tools, demo, goodwe, invoices, readings, settings
from app.services.demo import seed_demo_if_first_run


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_application()
    yield


app = FastAPI(
    title="SOLAR ANALYTICS API",
    description="Monitoramento local de geração solar, consumo e faturas Neoenergia.",
    version="1.0.0",
    docs_url=None if DISABLE_API_DOCS else "/docs",
    redoc_url=None if DISABLE_API_DOCS else "/redoc",
    openapi_url=None if DISABLE_API_DOCS else "/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    origin = request.headers.get("origin")
    is_mutating_api = request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if is_mutating_api and origin is not None and origin not in TRUSTED_WRITE_ORIGINS:
        response = JSONResponse(status_code=403, content={"detail": "Origem não autorizada para esta operação."})
    else:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(TRUSTED_HOSTS))

for router in (dashboard.router, readings.router, invoices.router, settings.router, goodwe.router, demo.router, data_tools.router):
    app.include_router(router)


def initialize_application() -> None:
    Base.metadata.create_all(bind=engine)
    if os.name == "posix" and DATABASE_PATH.exists():
        os.chmod(DATABASE_PATH, 0o600)
    with SessionLocal() as db:
        seed_demo_if_first_run(db, DEMO_AUTOLOAD)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok", "application": "SOLAR ANALYTICS", "storage": "SQLite local"}


static_dir = ROOT_DIR / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
