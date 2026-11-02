from __future__ import annotations

import csv
import io
import os
import sqlite3
import tempfile
import unicodedata
import zipfile
import zlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BACKUP_DIR, DATA_DIR, DATABASE_PATH
from app.db import Base, SessionLocal, engine, get_db
from app.limits import MAX_BACKUP_BYTES
from app.models import EnergyRecord, Invoice

router = APIRouter(prefix="/api", tags=["Exportação e backup"])


def _safe_spreadsheet_text(value: str | None) -> str:
    if value is None:
        return ""
    first_significant = next(
        (character for character in value if not character.isspace() and unicodedata.category(character) not in {"Cc", "Cf", "Zs"}),
        "",
    )
    if first_significant in {"=", "+", "-", "@"}:
        return "'" + value
    return value


@router.get("/export.csv")
def export_csv(kind: str = "readings", db: Session = Depends(get_db)):
    if kind not in {"readings", "invoices"}:
        raise HTTPException(status_code=400, detail="O tipo deve ser 'readings' ou 'invoices'.")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    if kind == "readings":
        writer.writerow(["data", "producao_kwh", "consumo_kwh", "injetada_kwh", "compensada_kwh", "origem", "demonstracao", "observacoes"])
        rows = db.scalars(select(EnergyRecord).order_by(EnergyRecord.record_date.asc())).all()
        for row in rows:
            writer.writerow([row.record_date, row.production_kwh, row.consumption_kwh, row.injected_kwh, row.compensated_kwh, row.source, row.is_demo, _safe_spreadsheet_text(row.notes)])
    else:
        writer.writerow(["periodo_inicio", "periodo_fim", "vencimento", "data_pagamento", "consumo_faturado_kwh", "energia_injetada_kwh", "energia_compensada_kwh", "creditos_acumulados_kwh", "valor_total_brl", "valor_pago_brl", "situacao", "demonstracao", "arquivo_origem"])
        rows = db.scalars(select(Invoice).order_by(Invoice.billing_period_end.asc().nullslast())).all()
        for row in rows:
            writer.writerow([row.billing_period_start or "", row.billing_period_end or "", row.due_date or "", row.paid_date or "", row.billed_consumption_kwh, row.injected_kwh, row.compensated_kwh, row.accumulated_credits_kwh, row.total_amount_brl, row.paid_amount_brl, row.payment_status, row.is_demo, _safe_spreadsheet_text(row.source_filename)])
    content = "\ufeff" + stream.getvalue()
    filename = f"solar_analytics_{kind}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return StreamingResponse(iter([content]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/backup")
def create_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"solar_analytics_backup_{stamp}.zip"
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False, dir=DATA_DIR) as temporary:
        temporary_path = Path(temporary.name)
    try:
        source = sqlite3.connect(DATABASE_PATH)
        target = sqlite3.connect(temporary_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(temporary_path, arcname="solar_analytics.sqlite3")
        if os.name == "posix":
            os.chmod(backup_path, 0o600)
    finally:
        temporary_path.unlink(missing_ok=True)
    return FileResponse(backup_path, media_type="application/zip", filename=backup_path.name)


@router.post("/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    name = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not name.lower().endswith((".zip", ".sqlite3", ".db")):
        raise HTTPException(status_code=415, detail="Envie um backup .zip, .sqlite3 ou .db.")
    content = await file.read(MAX_BACKUP_BYTES + 1)
    if len(content) > MAX_BACKUP_BYTES:
        raise HTTPException(status_code=413, detail="O backup ultrapassa o limite de 100 MB.")

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False, dir=DATA_DIR) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        if content[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    entries = archive.infolist()
                    if len(entries) > 1000:
                        raise HTTPException(status_code=400, detail="O ZIP contém itens demais para ser restaurado.")
                    candidates = [info for info in entries if info.filename == "solar_analytics.sqlite3" and not info.is_dir()]
                    if len(candidates) != 1 or candidates[0].file_size > MAX_BACKUP_BYTES:
                        raise HTTPException(status_code=400, detail="O ZIP não contém um banco de backup reconhecido.")
                    info = candidates[0]
                    with archive.open(info) as member:
                        database_bytes = member.read(MAX_BACKUP_BYTES + 1)
                    if len(database_bytes) > MAX_BACKUP_BYTES or len(database_bytes) != info.file_size:
                        raise HTTPException(status_code=400, detail="O conteúdo descompactado não corresponde ao limite ou ao tamanho declarado.")
                    temp_path.write_bytes(database_bytes)
            except (zipfile.BadZipFile, RuntimeError, EOFError, NotImplementedError, zlib.error) as exc:
                raise HTTPException(status_code=400, detail="O arquivo ZIP está corrompido.") from exc
        else:
            if not content.startswith(b"SQLite format 3\x00"):
                raise HTTPException(status_code=400, detail="O arquivo não tem o formato de um banco SQLite válido.")
            temp_path.write_bytes(content)

        check = sqlite3.connect(temp_path)
        try:
            integrity = check.execute("PRAGMA quick_check").fetchone()
            table_names = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not integrity or integrity[0] != "ok" or not {"energy_records", "invoices"}.issubset(table_names):
                raise HTTPException(status_code=400, detail="O banco de backup está incompleto ou não passou na verificação de integridade.")
        finally:
            check.close()

        for session in list(SessionLocal.registry()) if hasattr(SessionLocal, "registry") else []:
            session.close()
        engine.dispose()
        os.replace(temp_path, DATABASE_PATH)
        Base.metadata.create_all(bind=engine)
        return {"restored": True, "message": "Backup restaurado. Atualize a página para recarregar os dados."}
    finally:
        temp_path.unlink(missing_ok=True)
