from __future__ import annotations

import sys
from datetime import datetime
from typing import Protocol

import keyring

SERVICE_NAME = "SOLAR ANALYTICS — GoodWe SEMS+"
APP_SECRET_USER = "sems-app-secret"


def _secure_keyring_available() -> bool:
    approved_modules = {
        "win32": ("keyring.backends.Windows",),
        "darwin": ("keyring.backends.macOS",),
        "linux": ("keyring.backends.SecretService",),
    }
    platform_key = "linux" if sys.platform.startswith("linux") else sys.platform
    prefixes = approved_modules.get(platform_key, ())
    try:
        module = type(keyring.get_keyring()).__module__
    except Exception:
        return False
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


class GoodWeSEMSAdapter(Protocol):
    """Contrato tipado para um futuro adaptador da API oficial.

    Isto é somente uma interface: não seleciona endpoints, não autentica e
    não produz leituras fictícias. Um adaptador real deve ser implementado e
    validado separadamente com a documentação oficial SEMS+.
    """

    async def authenticate(self, app_id: str, app_secret: str) -> None: ...

    async def fetch_generation(
        self, plant_id: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]: ...

    async def fetch_consumption(
        self, plant_id: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]: ...

    async def fetch_power(self, plant_id: str) -> dict[str, object]: ...

    async def synchronize(
        self, plant_id: str, start: datetime, end: datetime
    ) -> list[dict[str, object]]: ...


def save_app_secret(secret: str) -> None:
    if not secret:
        return
    if not _secure_keyring_available():
        raise RuntimeError("Nenhum cofre de credenciais aprovado está disponível neste sistema.")
    keyring.set_password(SERVICE_NAME, APP_SECRET_USER, secret)


def app_secret_is_configured() -> bool:
    if not _secure_keyring_available():
        return False
    try:
        return bool(keyring.get_password(SERVICE_NAME, APP_SECRET_USER))
    except Exception:
        return False


def delete_app_secret() -> None:
    if not _secure_keyring_available():
        raise RuntimeError("Nenhum cofre de credenciais aprovado está disponível neste sistema.")
    try:
        keyring.delete_password(SERVICE_NAME, APP_SECRET_USER)
    except keyring.errors.PasswordDeleteError:
        pass
