from sqlalchemy import select
from sqlalchemy.orm import Session

from wealthy_api.models.property_import import (
    PropertyImportRowLog,
    PropertyImportRun,
    PropertyImportStaging,
)


def create_run(session: Session, source_file: str, started_at: int) -> PropertyImportRun:
    run = PropertyImportRun(
        source_file=source_file,
        status="running",
        started_at=started_at,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def stage_rows(session: Session, run_id: int, rows: list[PropertyImportStaging]) -> None:
    session.add_all(rows)
    session.commit()


def get_staged_batch(
    session: Session, run_id: int, offset: int, limit: int
) -> list[PropertyImportStaging]:
    statement = (
        select(PropertyImportStaging)
        .where(PropertyImportStaging.run_id == run_id)
        .order_by(PropertyImportStaging.line_number)
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def log_rows(session: Session, rows: list[PropertyImportRowLog]) -> None:
    session.add_all(rows)


def get_run(session: Session, run_id: int) -> PropertyImportRun | None:
    return session.get(PropertyImportRun, run_id)
