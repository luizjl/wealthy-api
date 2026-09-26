from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ImportRowStatus = Literal["imported", "updated", "rejected", "duplicate", "reactivated"]


class PropertyImportRunRead(BaseModel):
    id: int
    source_file: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    total_rows: int
    inserted_rows: int
    updated_rows: int
    rejected_rows: int
    duplicate_rows: int
    reactivated_rows: int
    error_message: str | None


class PropertyImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_number: int
    numero_imovel: str | None
    status: ImportRowStatus
    detail: str | None


class PropertyImportRowPage(BaseModel):
    items: list[PropertyImportRowRead]
    pagina: int
    porPagina: int
    total: int
