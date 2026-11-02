from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import TariffConfig
from app.schemas import TariffOut, TariffUpdate

router = APIRouter(prefix="/api/settings", tags=["Configurações"])


@router.get("/tariffs", response_model=TariffOut)
def get_tariffs(db: Session = Depends(get_db)):
    row = db.get(TariffConfig, 1)
    if row is None:
        row = TariffConfig(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.put("/tariffs", response_model=TariffOut)
def update_tariffs(payload: TariffUpdate, db: Session = Depends(get_db)):
    row = db.get(TariffConfig, 1)
    if row is None:
        row = TariffConfig(id=1)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
