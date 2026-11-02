from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

ROOT_DIR = Path(__file__).resolve().parents[1]


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
_data_dir = Path(os.getenv("SOLAR_DATA_DIR", "./data"))
DATA_DIR = (_data_dir if _data_dir.is_absolute() else ROOT_DIR / _data_dir).resolve()
BACKUP_DIR = ROOT_DIR / "backups"
DATABASE_PATH = DATA_DIR / "solar_analytics.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
DEMO_AUTOLOAD = os.getenv("SOLAR_DEMO_AUTOLOAD", "true").strip().lower() in {"1", "true", "yes", "on"}
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SOLAR_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
TRUSTED_WRITE_ORIGINS = set(CORS_ORIGINS)
TRUSTED_WRITE_ORIGINS.update({"http://localhost:8000", "http://127.0.0.1:8000"})
TRUSTED_WRITE_ORIGINS.update(
    origin.strip()
    for origin in os.getenv("SOLAR_TRUSTED_WRITE_ORIGINS", "").split(",")
    if origin.strip()
)
TRUSTED_HOSTS = {"localhost", "127.0.0.1", "::1"}
for trusted_origin in TRUSTED_WRITE_ORIGINS:
    hostname = urlsplit(trusted_origin).hostname
    if hostname:
        TRUSTED_HOSTS.add(hostname)
DISABLE_API_DOCS = os.getenv("SOLAR_DISABLE_API_DOCS", "false").strip().lower() in {"1", "true", "yes", "on"}

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
if os.name == "posix":
    os.chmod(DATA_DIR, 0o700)
    os.chmod(BACKUP_DIR, 0o700)
