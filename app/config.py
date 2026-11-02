from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

ROOT_DIR = Path(__file__).resolve().parents[1]


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

IS_RENDER = _truthy(os.getenv("RENDER"))
AUTH_REQUIRED = _truthy(os.getenv("SOLAR_AUTH_REQUIRED"), default=IS_RENDER)
ADMIN_USERNAME = os.getenv("SOLAR_ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD = os.getenv("SOLAR_ADMIN_PASSWORD", "")
COOKIE_SECURE = _truthy(os.getenv("SOLAR_COOKIE_SECURE"), default=IS_RENDER)
VOLATILE_STORAGE = _truthy(os.getenv("SOLAR_VOLATILE_STORAGE"))
DISABLE_API_DOCS = _truthy(os.getenv("SOLAR_DISABLE_API_DOCS"), default=IS_RENDER)
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60

SESSION_SECRET = os.getenv("SOLAR_SESSION_SECRET", "")
if AUTH_REQUIRED:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError("Login obrigatório sem SOLAR_ADMIN_USERNAME e SOLAR_ADMIN_PASSWORD configurados.")
    if len(ADMIN_PASSWORD) < 16:
        raise RuntimeError("SOLAR_ADMIN_PASSWORD deve ter pelo menos 16 caracteres.")
    if len(SESSION_SECRET) < 32:
        raise RuntimeError("SOLAR_SESSION_SECRET deve conter pelo menos 32 caracteres aleatórios.")
if IS_RENDER and not AUTH_REQUIRED:
    raise RuntimeError("Autenticação é obrigatória para disponibilizar o SOLAR ANALYTICS no Render.")
if IS_RENDER and not COOKIE_SECURE:
    raise RuntimeError("SOLAR_COOKIE_SECURE deve estar habilitado em HTTPS no Render.")
if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_urlsafe(48)

_data_dir = Path(os.getenv("SOLAR_DATA_DIR", "./data"))
DATA_DIR = (_data_dir if _data_dir.is_absolute() else ROOT_DIR / _data_dir).resolve()
_backup_dir = Path(os.getenv("SOLAR_BACKUP_DIR", "./backups"))
BACKUP_DIR = (_backup_dir if _backup_dir.is_absolute() else ROOT_DIR / _backup_dir).resolve()
DATABASE_PATH = DATA_DIR / "solar_analytics.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
DEMO_AUTOLOAD = _truthy(os.getenv("SOLAR_DEMO_AUTOLOAD"), default=True)

_default_cors = "" if IS_RENDER else "http://localhost:3000,http://127.0.0.1:3000"
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("SOLAR_CORS_ORIGINS", _default_cors).split(",")
    if origin.strip()
]
TRUSTED_WRITE_ORIGINS = set(CORS_ORIGINS)
if not IS_RENDER:
    TRUSTED_WRITE_ORIGINS.update({"http://localhost:8000", "http://127.0.0.1:8000"})
TRUSTED_WRITE_ORIGINS.update(
    origin.strip().rstrip("/")
    for origin in os.getenv("SOLAR_TRUSTED_WRITE_ORIGINS", "").split(",")
    if origin.strip()
)

# Render supplies its canonical public URL at runtime; use it without trusting localhost in production.
render_origin = os.getenv("RENDER_EXTERNAL_URL", "").strip()
if render_origin:
    TRUSTED_WRITE_ORIGINS.add(render_origin.rstrip("/"))

TRUSTED_HOSTS = set() if IS_RENDER else {"localhost", "127.0.0.1", "::1"}
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname:
    TRUSTED_HOSTS.add(render_hostname)
for trusted_origin in TRUSTED_WRITE_ORIGINS:
    hostname = urlsplit(trusted_origin).hostname
    if hostname:
        TRUSTED_HOSTS.add(hostname)

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
if os.name == "posix":
    os.chmod(DATA_DIR, 0o700)
    os.chmod(BACKUP_DIR, 0o700)
