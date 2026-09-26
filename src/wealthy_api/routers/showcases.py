from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from wealthy_api.database import get_session
from wealthy_api.schemas.showcase import (
    ShowcaseCreate,
    ShowcasePage,
    ShowcaseRead,
    ShowcaseUpdate,
)
from wealthy_api.security import get_current_user
from wealthy_api.services import showcases as showcase_service

router = APIRouter(
    prefix="/api/v1/vitrines",
    tags=["vitrines"],
    dependencies=[Depends(get_current_user)],
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")


def _read(showcase) -> ShowcaseRead:
    return ShowcaseRead(**showcase_service.to_showcase_read(showcase))


@router.post("", response_model=ShowcaseRead, status_code=status.HTTP_201_CREATED)
def create_showcase(
    payload: ShowcaseCreate, session: Session = Depends(get_session)
) -> ShowcaseRead:
    return _read(showcase_service.create_showcase(session, payload))


@router.get("", response_model=ShowcasePage)
def list_showcases(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    session: Session = Depends(get_session),
) -> ShowcasePage:
    showcases, total = showcase_service.list_showcases(session, pagina, por_pagina)
    return ShowcasePage(
        items=[_read(showcase) for showcase in showcases],
        pagina=pagina,
        porPagina=por_pagina,
        total=total,
    )


@router.get("/{showcase_id}", response_model=ShowcaseRead)
def read_showcase(showcase_id: int, session: Session = Depends(get_session)) -> ShowcaseRead:
    try:
        return _read(showcase_service.get_showcase(session, showcase_id))
    except showcase_service.ShowcaseNotFoundError as error:
        raise _not_found() from error


@router.patch("/{showcase_id}", response_model=ShowcaseRead)
def patch_showcase(
    showcase_id: int,
    payload: ShowcaseUpdate,
    session: Session = Depends(get_session),
) -> ShowcaseRead:
    try:
        return _read(showcase_service.update_showcase(session, showcase_id, payload))
    except showcase_service.ShowcaseNotFoundError as error:
        raise _not_found() from error


@router.put("/{showcase_id}", response_model=ShowcaseRead)
def replace_showcase(
    showcase_id: int,
    payload: ShowcaseCreate,
    session: Session = Depends(get_session),
) -> ShowcaseRead:
    try:
        full_update = ShowcaseUpdate.model_validate(payload.model_dump())
        return _read(showcase_service.update_showcase(session, showcase_id, full_update))
    except showcase_service.ShowcaseNotFoundError as error:
        raise _not_found() from error


@router.delete("/{showcase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_showcase(showcase_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        showcase_service.delete_showcase(session, showcase_id)
    except showcase_service.ShowcaseNotFoundError as error:
        raise _not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
