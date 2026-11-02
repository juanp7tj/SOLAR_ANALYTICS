from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Invoice
from app.schemas import InvoiceCreate, InvoiceOut, PdfExtractOut
from app.services.pdf_parser import extract_invoice_fields

router = APIRouter(prefix="/api/invoices", tags=["Faturas Neoenergia"])
MAX_PDF_BYTES = 20 * 1024 * 1024


@router.get("", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    query = select(Invoice).order_by(Invoice.billing_period_end.desc().nullslast(), Invoice.created_at.desc())
    return db.scalars(query.limit(500)).all()


@router.post("/extract", response_model=PdfExtractOut)
async def extract_pdf(file: UploadFile = File(...)):
    filename = (file.filename or "fatura.pdf").replace("\\", "/").split("/")[-1][:255]
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Selecione um arquivo PDF.")
    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="O PDF ultrapassa o limite de 20 MB.")
    try:
        fields = extract_invoice_fields(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PdfExtractOut(**fields, file_name=filename, source_filename=filename, payment_status="pending")


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    row = Invoice(**payload.model_dump(), is_demo=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    row = db.get(Invoice, invoice_id)
    if not row:
        raise HTTPException(status_code=404, detail="Fatura não encontrada.")
    db.delete(row)
    db.commit()
    return None
