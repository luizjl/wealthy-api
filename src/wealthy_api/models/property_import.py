from sqlalchemy import ForeignKey, Integer, Sequence, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from wealthy_api.models.base import Base


class PropertyImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, Sequence("import_runs_id_seq"), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[int] = mapped_column(Integer, nullable=False)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reactivated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class PropertyImportStaging(Base):
    __tablename__ = "imoveis_import_staging"
    __table_args__ = (UniqueConstraint("run_id", "line_number", name="uq_imp_stage_run_line"),)

    id: Mapped[int] = mapped_column(
        Integer, Sequence("imoveis_import_stg_id_seq"), primary_key=True
    )
    run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


class PropertyImportRowLog(Base):
    __tablename__ = "imoveis_import_rows"
    __table_args__ = (UniqueConstraint("run_id", "line_number", name="uq_imp_row_run_line"),)

    id: Mapped[int] = mapped_column(
        Integer, Sequence("imoveis_import_row_id_seq"), primary_key=True
    )
    run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_imovel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(2000), nullable=True)
