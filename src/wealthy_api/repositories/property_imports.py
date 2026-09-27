from sqlalchemy import func, select, update
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


def get_unprocessed_staged_batch(
    session: Session, run_id: int, limit: int
) -> list[PropertyImportStaging]:
    statement = (
        select(PropertyImportStaging)
        .where(
            PropertyImportStaging.run_id == run_id,
            ~select(PropertyImportRowLog.id)
            .where(
                PropertyImportRowLog.run_id == PropertyImportStaging.run_id,
                PropertyImportRowLog.line_number == PropertyImportStaging.line_number,
            )
            .exists(),
        )
        .order_by(PropertyImportStaging.line_number)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def get_logged_staged_rows(session: Session, run_id: int) -> list[PropertyImportStaging]:
    statement = (
        select(PropertyImportStaging)
        .join(
            PropertyImportRowLog,
            (PropertyImportRowLog.run_id == PropertyImportStaging.run_id)
            & (PropertyImportRowLog.line_number == PropertyImportStaging.line_number),
        )
        .where(PropertyImportStaging.run_id == run_id)
        .order_by(PropertyImportStaging.line_number)
    )
    return list(session.scalars(statement).all())


def get_run_row_counts(session: Session, run_id: int) -> dict[str, int]:
    statement = (
        select(PropertyImportRowLog.status, func.count())
        .where(PropertyImportRowLog.run_id == run_id)
        .group_by(PropertyImportRowLog.status)
    )
    return {status: count for status, count in session.execute(statement)}


def count_staged_rows(session: Session, run_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(PropertyImportStaging)
        .where(PropertyImportStaging.run_id == run_id)
    )
    return session.scalar(statement) or 0


def claim_failed_run(session: Session, run_id: int) -> bool:
    statement = (
        update(PropertyImportRun)
        .where(PropertyImportRun.id == run_id, PropertyImportRun.status == "failed")
        .values(status="running", finished_at=None, error_message=None)
    )
    claimed = session.execute(statement).rowcount == 1
    session.commit()
    session.expire_all()
    return claimed


def log_rows(session: Session, rows: list[PropertyImportRowLog]) -> None:
    session.add_all(rows)


def get_run(session: Session, run_id: int) -> PropertyImportRun | None:
    return session.get(PropertyImportRun, run_id)


def count_run_rows(session: Session, run_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(PropertyImportRowLog)
        .where(PropertyImportRowLog.run_id == run_id)
    )
    return session.scalar(statement) or 0


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
