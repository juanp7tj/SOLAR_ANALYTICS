from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import GoodWeConfig
from app.schemas import GoodWeConfigOut, GoodWeCredentialsUpdate
from app.services.goodwe import app_secret_is_configured, delete_app_secret, save_app_secret

router = APIRouter(prefix="/api/goodwe", tags=["GoodWe SEMS+"])
WAITING = "Aguardando credenciais da API GoodWe"


def _secret_configured() -> bool:
    return app_secret_is_configured()


def _status(db: Session) -> GoodWeConfigOut:
    config = db.get(GoodWeConfig, 1)
    secret_configured = _secret_configured()
    return GoodWeConfigOut(
        app_id=config.app_id if config else None,
        plant_id=config.plant_id if config else None,
        secret_configured=secret_configured,
        status=WAITING,
    )


@router.get("/status", response_model=GoodWeConfigOut)
def get_status(db: Session = Depends(get_db)):
    return _status(db)


@router.put("/credentials", response_model=GoodWeConfigOut)
def save_credentials(payload: GoodWeCredentialsUpdate, db: Session = Depends(get_db)):
    config = db.get(GoodWeConfig, 1)
    if config is None:
        config = GoodWeConfig(id=1)
        db.add(config)
    config.app_id = payload.app_id.strip()
    config.plant_id = payload.plant_id.strip()
    if payload.app_secret:
        try:
            save_app_secret(payload.app_secret)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail="Não foi possível gravar o AppSecret no cofre de credenciais do sistema. Nenhum segredo foi salvo no banco SQLite.") from exc
    db.commit()
    db.refresh(config)
    return _status(db)


@router.delete("/credentials")
def clear_credentials(db: Session = Depends(get_db)):
    try:
        delete_app_secret()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Não foi possível remover as credenciais do cofre do sistema.") from exc
    config = db.get(GoodWeConfig, 1)
    if config:
        config.app_id = None
        config.plant_id = None
        db.commit()
    return {"cleared": True, "status": WAITING}


@router.post("/sync")
def sync_not_implemented():
    raise HTTPException(status_code=501, detail="A integração oficial GoodWe SEMS+ ainda não foi conectada. Nenhuma autenticação, consulta ou sincronização foi realizada.")
