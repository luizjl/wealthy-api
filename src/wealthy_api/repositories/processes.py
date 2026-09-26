from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wealthy_api.models.person import Person
from wealthy_api.models.process import LegalProcess


def find_process(session: Session, process_id: int) -> LegalProcess | None:
    return session.get(LegalProcess, process_id)


def find_person(session: Session, person_id: int) -> Person | None:
    return session.get(Person, person_id)


def list_processes(session: Session, offset: int, limit: int) -> tuple[list[LegalProcess], int]:
    total = session.scalar(select(func.count()).select_from(LegalProcess)) or 0
    processes = session.scalars(
        select(LegalProcess).order_by(LegalProcess.id).offset(offset).limit(limit)
    ).all()
    return list(processes), total
