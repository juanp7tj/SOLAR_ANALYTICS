from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import DEMO_AUTOLOAD
from app.db import get_db
from app.schemas import DemoStatus
from app.services.demo import demo_counts, remove_demo

router = APIRouter(prefix="/api/demo", tags=["Demonstração"])


@router.get("/status", response_model=DemoStatus)
def status(db: Session = Depends(get_db)):
    records, invoices = demo_counts(db)
    return DemoStatus(enabled=bool(records or invoices), demo_records=records, demo_invoices=invoices)


@router.delete("", response_model=dict)
def delete_demo(db: Session = Depends(get_db)):
    records, invoices = remove_demo(db)
    return {"removed_records": records, "removed_invoices": invoices, "message": "Dados fictícios removidos. A demonstração não será carregada automaticamente novamente."}
