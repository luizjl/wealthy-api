from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from wealthy_api.database import get_session
from wealthy_api.schemas.auction import (
    AuctionCreate,
    AuctionFileCreate,
    AuctionFileRead,
    AuctionFileUpdate,
    AuctionPage,
    AuctionRead,
    AuctionUpdate,
)
from wealthy_api.security import get_current_user
from wealthy_api.services import auctions as auction_service

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])


def _auction_not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leilão não encontrado")


def _file_not_found(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado")


def _invalid_person(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Proprietário deve ser CPF e órgão de origem deve ser CNPJ",
    )


@router.post(
    "/leiloes", response_model=AuctionRead, status_code=status.HTTP_201_CREATED, tags=["leiloes"]
)
def create_auction(payload: AuctionCreate, session: Session = Depends(get_session)) -> AuctionRead:
    try:
        auction = auction_service.create_auction(session, payload)
        return AuctionRead(**auction_service.to_auction_read(auction))
    except auction_service.RelatedPersonInvalidError as error:
        raise _invalid_person(error) from error


@router.get("/leiloes", response_model=AuctionPage, tags=["leiloes"])
def list_auctions(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    session: Session = Depends(get_session),
) -> AuctionPage:
    auctions, total = auction_service.list_auctions(session, pagina, por_pagina)
    items = [AuctionRead(**auction_service.to_auction_read(item)) for item in auctions]
    return AuctionPage(items=items, pagina=pagina, porPagina=por_pagina, total=total)


@router.get("/leiloes/{auction_id}", response_model=AuctionRead, tags=["leiloes"])
def read_auction(auction_id: int, session: Session = Depends(get_session)) -> AuctionRead:
    try:
        auction = auction_service.get_auction(session, auction_id)
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error
    return AuctionRead(**auction_service.to_auction_read(auction))


@router.patch("/leiloes/{auction_id}", response_model=AuctionRead, tags=["leiloes"])
def patch_auction(
    auction_id: int,
    payload: AuctionUpdate,
    session: Session = Depends(get_session),
) -> AuctionRead:
    try:
        auction = auction_service.update_auction(session, auction_id, payload)
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error
    except auction_service.RelatedPersonInvalidError as error:
        raise _invalid_person(error) from error
    return AuctionRead(**auction_service.to_auction_read(auction))


@router.put("/leiloes/{auction_id}", response_model=AuctionRead, tags=["leiloes"])
def replace_auction(
    auction_id: int,
    payload: AuctionCreate,
    session: Session = Depends(get_session),
) -> AuctionRead:
    try:
        auction = auction_service.update_auction(
            session, auction_id, AuctionUpdate.model_validate(payload.model_dump())
        )
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error
    except auction_service.RelatedPersonInvalidError as error:
        raise _invalid_person(error) from error
    return AuctionRead(**auction_service.to_auction_read(auction))


@router.delete("/leiloes/{auction_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["leiloes"])
def delete_auction(auction_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        auction_service.delete_auction(session, auction_id)
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error
    except auction_service.RelatedRecordConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leilão possui vínculos e não pode ser excluído",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/leiloes/{auction_id}/arquivos",
    response_model=AuctionFileRead,
    status_code=status.HTTP_201_CREATED,
    tags=["arquivos"],
)
def create_auction_file(
    auction_id: int,
    payload: AuctionFileCreate,
    session: Session = Depends(get_session),
) -> AuctionFileRead:
    try:
        return auction_service.create_auction_file(session, auction_id, payload)
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error


@router.get(
    "/leiloes/{auction_id}/arquivos", response_model=list[AuctionFileRead], tags=["arquivos"]
)
def list_auction_files(
    auction_id: int, session: Session = Depends(get_session)
) -> list[AuctionFileRead]:
    try:
        return auction_service.list_auction_files(session, auction_id)
    except auction_service.AuctionNotFoundError as error:
        raise _auction_not_found(error) from error


@router.get("/arquivos/{file_id}", response_model=AuctionFileRead, tags=["arquivos"])
def read_auction_file(file_id: int, session: Session = Depends(get_session)) -> AuctionFileRead:
    try:
        return auction_service.get_auction_file(session, file_id)
    except auction_service.AuctionFileNotFoundError as error:
        raise _file_not_found(error) from error


@router.patch("/arquivos/{file_id}", response_model=AuctionFileRead, tags=["arquivos"])
def patch_auction_file(
    file_id: int,
    payload: AuctionFileUpdate,
    session: Session = Depends(get_session),
) -> AuctionFileRead:
    try:
        return auction_service.update_auction_file(session, file_id, payload)
    except auction_service.AuctionFileNotFoundError as error:
        raise _file_not_found(error) from error


@router.put("/arquivos/{file_id}", response_model=AuctionFileRead, tags=["arquivos"])
def replace_auction_file(
    file_id: int,
    payload: AuctionFileCreate,
    session: Session = Depends(get_session),
) -> AuctionFileRead:
    try:
        return auction_service.update_auction_file(
            session, file_id, AuctionFileUpdate.model_validate(payload.model_dump())
        )
    except auction_service.AuctionFileNotFoundError as error:
        raise _file_not_found(error) from error


@router.delete("/arquivos/{file_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["arquivos"])
def delete_auction_file(file_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        auction_service.delete_auction_file(session, file_id)
    except auction_service.AuctionFileNotFoundError as error:
        raise _file_not_found(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
