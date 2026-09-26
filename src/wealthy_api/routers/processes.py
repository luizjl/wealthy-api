from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from wealthy_api.database import get_session
from wealthy_api.schemas.process import ProcessCreate, ProcessPage, ProcessRead, ProcessUpdate
from wealthy_api.security import get_current_user
from wealthy_api.services import processes as process_service

router = APIRouter(
    prefix="/api/v1/processos",
    tags=["processos"],
    dependencies=[Depends(get_current_user)],
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado")


def _person_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada")


@router.post("", response_model=ProcessRead, status_code=status.HTTP_201_CREATED)
def create_process(payload: ProcessCreate, session: Session = Depends(get_session)) -> ProcessRead:
    try:
        return process_service.create_process(session, payload)
    except process_service.ProcessPersonNotFoundError as error:
        raise _person_not_found() from error


@router.get("", response_model=ProcessPage)
def list_processes(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    session: Session = Depends(get_session),
) -> ProcessPage:
    processes, total = process_service.list_processes(session, pagina, por_pagina)
    return ProcessPage(items=processes, pagina=pagina, porPagina=por_pagina, total=total)


@router.get("/{process_id}", response_model=ProcessRead)
def read_process(process_id: int, session: Session = Depends(get_session)) -> ProcessRead:
    try:
        return process_service.get_process(session, process_id)
    except process_service.ProcessNotFoundError as error:
        raise _not_found() from error


@router.patch("/{process_id}", response_model=ProcessRead)
def patch_process(
    process_id: int,
    payload: ProcessUpdate,
    session: Session = Depends(get_session),
) -> ProcessRead:
    try:
        return process_service.update_process(session, process_id, payload)
    except process_service.ProcessNotFoundError as error:
        raise _not_found() from error
    except process_service.ProcessPersonNotFoundError as error:
        raise _person_not_found() from error


@router.put("/{process_id}", response_model=ProcessRead)
def replace_process(
    process_id: int,
    payload: ProcessCreate,
    session: Session = Depends(get_session),
) -> ProcessRead:
    try:
        full_update = ProcessUpdate.model_validate(payload.model_dump())
        return process_service.update_process(session, process_id, full_update)
    except process_service.ProcessNotFoundError as error:
        raise _not_found() from error
    except process_service.ProcessPersonNotFoundError as error:
        raise _person_not_found() from error


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process(process_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        process_service.delete_process(session, process_id)
    except process_service.ProcessNotFoundError as error:
        raise _not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
