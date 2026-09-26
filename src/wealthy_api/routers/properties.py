from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from wealthy_api.database import get_session
from wealthy_api.schemas.auction import UF_CODES
from wealthy_api.schemas.property import (
    FavoritePage,
    PropertyCreate,
    PropertyPage,
    PropertyRead,
    PropertyUpdate,
)
from wealthy_api.security import get_current_user
from wealthy_api.services import properties as property_service

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])


def _property_not_found(error: Exception | None = None) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado")


def _validate_filters(
    ufs: list[str] | None,
    financiamento: str | None,
    preco_min: float | None,
    preco_max: float | None,
) -> tuple[list[str] | None, str | None]:
    normalized_ufs = [uf.strip().upper() for uf in ufs] if ufs else None
    if normalized_ufs and any(uf not in UF_CODES for uf in normalized_ufs):
        raise HTTPException(status_code=400, detail="Filtro contém UF inválida")

    normalized_financing = None
    if financiamento is not None:
        normalized_financing = financiamento.strip().lower()
        if normalized_financing not in {"sim", "nao", "não"}:
            raise HTTPException(status_code=400, detail="Financiamento deve ser sim, nao ou não")
        if normalized_financing == "não":
            normalized_financing = "nao"

    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(status_code=400, detail="Preço mínimo não pode superar preço máximo")
    return normalized_ufs, normalized_financing


@router.post(
    "/imoveis", response_model=PropertyRead, status_code=status.HTTP_201_CREATED, tags=["imoveis"]
)
def create_property(
    payload: PropertyCreate, session: Session = Depends(get_session)
) -> PropertyRead:
    try:
        return property_service.create_property(session, payload)
    except property_service.PropertyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um imóvel com esse número",
        ) from error


@router.get("/imoveis", response_model=PropertyPage, tags=["imoveis"])
def list_properties(
    uf: list[str] | None = Query(default=None),
    cidade: str | None = None,
    cidades_excluir: str | None = Query(default=None, alias="cidadesExcluir"),
    bairro: str | None = None,
    modalidade: str | None = None,
    financiamento: str | None = None,
    preco_min: float | None = Query(default=None, alias="precoMin", ge=0),
    preco_max: float | None = Query(default=None, alias="precoMax", ge=0),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    session: Session = Depends(get_session),
) -> PropertyPage:
    normalized_ufs, normalized_financing = _validate_filters(
        uf, financiamento, preco_min, preco_max
    )
    excluded_cities = (
        [city.strip().upper() for city in cidades_excluir.split(",") if city.strip()]
        if cidades_excluir
        else None
    )
    properties, total = property_service.list_properties(
        session,
        pagina,
        por_pagina,
        ufs=normalized_ufs,
        cidade=cidade.strip() if cidade else None,
        cidades_excluir=excluded_cities,
        bairro=bairro.strip() if bairro else None,
        modalidade=modalidade.strip() if modalidade else None,
        financiamento=normalized_financing,
        preco_min=preco_min,
        preco_max=preco_max,
    )
    return PropertyPage(items=properties, pagina=pagina, porPagina=por_pagina, total=total)


@router.get("/imoveis/{numero}", response_model=PropertyRead, tags=["imoveis"])
def read_property(numero: str, session: Session = Depends(get_session)) -> PropertyRead:
    try:
        return property_service.get_property(session, numero)
    except property_service.PropertyNotFoundError as error:
        raise _property_not_found(error) from error


@router.patch("/imoveis/{numero}", response_model=PropertyRead, tags=["imoveis"])
def update_property(
    numero: str,
    payload: PropertyUpdate,
    session: Session = Depends(get_session),
) -> PropertyRead:
    try:
        return property_service.update_property(session, numero, payload)
    except property_service.PropertyNotFoundError as error:
        raise _property_not_found(error) from error


@router.post("/imoveis/{numero}/inativar", response_model=PropertyRead, tags=["imoveis"])
def inactivate_property(numero: str, session: Session = Depends(get_session)) -> PropertyRead:
    try:
        return property_service.inactivate_property(session, numero)
    except property_service.PropertyNotFoundError as error:
        raise _property_not_found(error) from error


@router.get("/me/favoritos", response_model=FavoritePage, tags=["favoritos"])
def list_favorites(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, alias="porPagina", ge=1, le=100),
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FavoritePage:
    favorites, total = property_service.list_favorites(session, claims["uid"], pagina, por_pagina)
    return FavoritePage(items=favorites, pagina=pagina, porPagina=por_pagina, total=total)


@router.put(
    "/me/favoritos/{numero_imovel}",
    response_model=property_service.FavoriteRead,
    tags=["favoritos"],
)
def add_favorite(
    numero_imovel: str,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> property_service.FavoriteRead:
    try:
        return property_service.add_favorite(session, claims["uid"], numero_imovel)
    except property_service.PropertyNotFoundError as error:
        raise _property_not_found(error) from error


@router.delete(
    "/me/favoritos/{numero_imovel}", status_code=status.HTTP_204_NO_CONTENT, tags=["favoritos"]
)
def remove_favorite(
    numero_imovel: str,
    claims: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    property_service.remove_favorite(session, claims["uid"], numero_imovel)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
