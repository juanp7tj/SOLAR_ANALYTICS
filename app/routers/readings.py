from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EnergyRecord
from app.schemas import EnergyRecordCreate, EnergyRecordOut

router = APIRouter(prefix="/api/readings", tags=["Medições"])


@router.get("", response_model=list[EnergyRecordOut])
def list_readings(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(EnergyRecord).order_by(EnergyRecord.record_date.desc(), EnergyRecord.id.desc())
    if start_date:
        query = query.where(EnergyRecord.record_date >= start_date)
    if end_date:
        query = query.where(EnergyRecord.record_date <= end_date)
    return db.scalars(query.limit(2000)).all()


@router.post("", response_model=EnergyRecordOut, status_code=status.HTTP_201_CREATED)
def create_reading(payload: EnergyRecordCreate, db: Session = Depends(get_db)):
    row = EnergyRecord(**payload.model_dump(), is_demo=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(record_id: int, db: Session = Depends(get_db)):
    row = db.get(EnergyRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Medição não encontrada.")
    db.delete(row)
    db.commit()
    return None
