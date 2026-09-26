from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from wealthy_api.database import get_session
from wealthy_api.schemas.person import PersonCreate, PersonPage, PersonRead, PersonUpdate
from wealthy_api.security import get_current_user
from wealthy_api.services import people as people_service

router = APIRouter(
    prefix="/api/v1/pessoas",
    tags=["pessoas"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, session: Session = Depends(get_session)) -> PersonRead:
    try:
        return people_service.create_person(session, payload)
    except people_service.PersonConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma pessoa com esse número de documento",
        ) from error


@router.get("", response_model=PersonPage)
def list_people(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    session: Session = Depends(get_session),
) -> PersonPage:
    people, total = people_service.list_people(session, pagina, por_pagina)
    return PersonPage(items=people, pagina=pagina, porPagina=por_pagina, total=total)


@router.get("/{person_id}", response_model=PersonRead)
def read_person(person_id: int, session: Session = Depends(get_session)) -> PersonRead:
    try:
        return people_service.get_person(session, person_id)
    except people_service.PersonNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada"
        ) from error


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(
    person_id: int,
    payload: PersonUpdate,
    session: Session = Depends(get_session),
) -> PersonRead:
    try:
        return people_service.update_person(session, person_id, payload)
    except people_service.PersonNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada"
        ) from error
    except people_service.PersonConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma pessoa com esse número de documento",
        ) from error


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        people_service.delete_person(session, person_id)
    except people_service.PersonNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa não encontrada"
        ) from error
    except people_service.PersonConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pessoa possui vínculos e não pode ser excluída",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
