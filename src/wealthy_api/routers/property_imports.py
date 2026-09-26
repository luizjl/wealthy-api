from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from wealthy_api.config import Settings, get_settings
from wealthy_api.database import get_session
from wealthy_api.schemas.property_import import (
    ImportRowStatus,
    PropertyImportRowPage,
    PropertyImportRunRead,
)
from wealthy_api.security import get_current_admin
from wealthy_api.services import property_imports as import_service

router = APIRouter(
    prefix="/api/v1/admin/imoveis/importacoes",
    tags=["importacao de imoveis"],
    dependencies=[Depends(get_current_admin)],
)


def _run_response(run) -> PropertyImportRunRead:
    return PropertyImportRunRead(
        id=run.id,
        source_file=run.source_file,
        status=run.status,
        started_at=datetime.fromtimestamp(run.started_at / 1000, tz=UTC),
        finished_at=(
            datetime.fromtimestamp(run.finished_at / 1000, tz=UTC)
            if run.finished_at is not None
            else None
        ),
        total_rows=run.total_rows,
        inserted_rows=run.inserted_rows,
        updated_rows=run.updated_rows,
        rejected_rows=run.rejected_rows,
        duplicate_rows=run.duplicate_rows,
        reactivated_rows=run.reactivated_rows,
        error_message=run.error_message,
    )


@router.post("", response_model=PropertyImportRunRead)
def import_properties(
    file: Annotated[UploadFile, File()],
    batch_size: Annotated[int, Form(ge=1, le=10000)] = 500,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> PropertyImportRunRead:
    filename = (file.filename or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Envie um arquivo CSV")

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(prefix="wealthy-import-", suffix=".csv", delete=False) as target:
            temporary_path = Path(target.name)
            total_bytes = 0
            while chunk := file.file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.import_max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Arquivo excede o limite configurado para importação",
                    )
                target.write(chunk)

        run = import_service.import_properties_csv(
            session,
            temporary_path,
            batch_size=batch_size,
            source_label=filename,
        )
        return _run_response(run)
    finally:
        file.file.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.get("/{run_id}", response_model=PropertyImportRunRead)
def read_import_run(run_id: int, session: Session = Depends(get_session)) -> PropertyImportRunRead:
    run = import_service.get_import_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execução de importação não encontrada")
    return _run_response(run)


@router.get("/{run_id}/linhas", response_model=PropertyImportRowPage)
def list_import_rows(
    run_id: int,
    row_status: ImportRowStatus | None = Query(default=None, alias="status"),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=100, alias="porPagina", ge=1, le=500),
    session: Session = Depends(get_session),
) -> PropertyImportRowPage:
    result = import_service.get_import_rows(
        session,
        run_id,
        pagina,
        por_pagina,
        row_status=row_status,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Execução de importação não encontrada")
    rows, total = result
    return PropertyImportRowPage(
        items=rows,
        pagina=pagina,
        porPagina=por_pagina,
        total=total,
    )
