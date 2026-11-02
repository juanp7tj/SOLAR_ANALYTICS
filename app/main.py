from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import (
    BACKUP_DIR,
    COOKIE_SECURE,
    CORS_ORIGINS,
    DATABASE_PATH,
    DEMO_AUTOLOAD,
    DISABLE_API_DOCS,
    ROOT_DIR,
    SESSION_MAX_AGE_SECONDS,
    SESSION_SECRET,
    TRUSTED_HOSTS,
)
from app.db import Base, SessionLocal, engine
from app.middleware import RequestSecurityMiddleware
from app.routers import auth, dashboard, data_tools, demo, goodwe, invoices, readings, settings
from app.services.auth import require_authenticated_admin
from app.services.demo import seed_demo_if_first_run


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_application()
    yield


app = FastAPI(
    title="SOLAR ANALYTICS API",
    description="Monitoramento de geração solar, consumo e faturas Neoenergia.",
    version="1.1.0",
    docs_url=None if DISABLE_API_DOCS else "/docs",
    redoc_url=None if DISABLE_API_DOCS else "/redoc",
    openapi_url=None if DISABLE_API_DOCS else "/openapi.json",
    lifespan=lifespan,
)

# Starlette composes middleware in reverse registration order. Session must wrap
# RequestSecurityMiddleware so the latter can verify the signed session before
# FastAPI reads multipart bodies; TrustedHost is placed outside that gate.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.add_middleware(RequestSecurityMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(TRUSTED_HOSTS))
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="solar_analytics_session",
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site="none" if COOKIE_SECURE else "lax",
    https_only=COOKIE_SECURE,
)

app.include_router(auth.router)
protected_routers = (
    dashboard.router,
    readings.router,
    invoices.router,
    settings.router,
    goodwe.router,
    demo.router,
    data_tools.router,
)
for router in protected_routers:
    app.include_router(router, dependencies=[Depends(require_authenticated_admin)])


def initialize_application() -> None:
    Base.metadata.create_all(bind=engine)
    if os.name == "posix" and DATABASE_PATH.exists():
        os.chmod(DATABASE_PATH, 0o600)
    if os.name == "posix" and BACKUP_DIR.exists():
        os.chmod(BACKUP_DIR, 0o700)
    with SessionLocal() as db:
        seed_demo_if_first_run(db, DEMO_AUTOLOAD)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok", "application": "SOLAR ANALYTICS", "storage": "SQLite"}


static_dir = ROOT_DIR / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
