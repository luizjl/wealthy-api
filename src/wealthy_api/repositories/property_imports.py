from sqlalchemy import func, select
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


def list_run_rows(
    session: Session,
    run_id: int,
    offset: int,
    limit: int,
    row_status: str | None = None,
) -> tuple[list[PropertyImportRowLog], int]:
    statement = select(PropertyImportRowLog).where(PropertyImportRowLog.run_id == run_id)
    count_statement = (
        select(func.count())
        .select_from(PropertyImportRowLog)
        .where(PropertyImportRowLog.run_id == run_id)
    )
    if row_status:
        statement = statement.where(PropertyImportRowLog.status == row_status)
        count_statement = count_statement.where(PropertyImportRowLog.status == row_status)
    rows = session.scalars(
        statement.order_by(PropertyImportRowLog.line_number).offset(offset).limit(limit)
    ).all()
    total = session.scalar(count_statement) or 0
    return list(rows), total
