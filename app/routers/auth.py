from fastapi import APIRouter, HTTPException, Request

from app import config
from app.schemas import LoginRequest
from app.services.auth import clear_login_failures, credentials_match, login_is_rate_limited, record_login_failure

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


def _status_payload(request: Request) -> dict[str, bool]:
    authenticated = not config.AUTH_REQUIRED or request.session.get("solar_admin_authenticated") is True
    return {
        "auth_required": config.AUTH_REQUIRED,
        "authenticated": authenticated,
        "volatile_storage": config.VOLATILE_STORAGE,
    }


@router.get("/status")
def auth_status(request: Request):
    return _status_payload(request)


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    if not config.AUTH_REQUIRED:
        return _status_payload(request)
    if login_is_rate_limited(request):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.",
            headers={"Retry-After": "900"},
        )
    if not credentials_match(payload.username, payload.password):
        record_login_failure(request)
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
    clear_login_failures(request)
    request.session.clear()
    request.session["solar_admin_authenticated"] = True
    return _status_payload(request)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"authenticated": not config.AUTH_REQUIRED}
