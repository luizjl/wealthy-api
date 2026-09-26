from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wealthy_api.models.process import LegalProcess
from wealthy_api.repositories import processes as process_repository
from wealthy_api.schemas.process import ProcessCreate, ProcessUpdate


class ProcessNotFoundError(Exception):
    pass


class ProcessPersonNotFoundError(Exception):
    pass


class ProcessConflictError(Exception):
    pass


def _get_process(session: Session, process_id: int) -> LegalProcess:
    process = process_repository.find_process(session, process_id)
    if process is None:
        raise ProcessNotFoundError
    return process


def _ensure_person_exists(session: Session, person_id: int) -> None:
    if process_repository.find_person(session, person_id) is None:
        raise ProcessPersonNotFoundError


def list_processes(
    session: Session, pagina: int, por_pagina: int
) -> tuple[list[LegalProcess], int]:
    return process_repository.list_processes(session, (pagina - 1) * por_pagina, por_pagina)


def get_process(session: Session, process_id: int) -> LegalProcess:
    return _get_process(session, process_id)


def create_process(session: Session, payload: ProcessCreate) -> LegalProcess:
    _ensure_person_exists(session, payload.id_pessoa)
    process = LegalProcess(**payload.model_dump())
    session.add(process)
    session.commit()
    session.refresh(process)
    return process


def update_process(session: Session, process_id: int, payload: ProcessUpdate) -> LegalProcess:
    process = _get_process(session, process_id)
    updates = payload.model_dump(exclude_unset=True)
    if "id_pessoa" in updates:
        _ensure_person_exists(session, updates["id_pessoa"])
    for field, value in updates.items():
        setattr(process, field, value)
    session.commit()
    session.refresh(process)
    return process


def delete_process(session: Session, process_id: int) -> None:
    process = _get_process(session, process_id)
    session.delete(process)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ProcessConflictError from error
