import json
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wealthy_api.models.property import Favorite, Property
from wealthy_api.repositories import properties as property_repository
from wealthy_api.schemas.property import (
    FavoriteRead,
    PropertyCreate,
    PropertyRead,
    PropertyUpdate,
)


class PropertyNotFoundError(Exception):
    pass


class PropertyConflictError(Exception):
    pass


def _get_property(session: Session, numero: str) -> Property:
    property_ = property_repository.find_property(session, numero)
    if property_ is None:
        raise PropertyNotFoundError
    return property_


def list_properties(
    session: Session,
    pagina: int,
    por_pagina: int,
    **filters,
) -> tuple[list[Property], int]:
    return property_repository.list_properties(
        session, (pagina - 1) * por_pagina, por_pagina, **filters
    )


def get_property(session: Session, numero: str) -> Property:
    return _get_property(session, numero)


def create_property(session: Session, payload: PropertyCreate) -> Property:
    values = payload.model_dump()
    if values["link_matricula"] is not None:
        values["link_matricula"] = str(values["link_matricula"])
    property_ = Property(**values)
    session.add(property_)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PropertyConflictError from error
    session.refresh(property_)
    return property_


def update_property(session: Session, numero: str, payload: PropertyUpdate) -> Property:
    property_ = _get_property(session, numero)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "link_matricula" and value is not None:
            value = str(value)
        setattr(property_, field, value)
    session.commit()
    session.refresh(property_)
    return property_


def inactivate_property(session: Session, numero: str) -> Property:
    property_ = _get_property(session, numero)
    property_.ativo = False
    session.commit()
    session.refresh(property_)
    return property_


def to_favorite_read(favorite: Favorite) -> FavoriteRead:
    snapshot = PropertyRead.model_validate_json(favorite.imovel_json)
    return FavoriteRead(
        numero_imovel=favorite.numero_imovel,
        favoritado_em=datetime.fromtimestamp(favorite.favoritado_em / 1000, tz=UTC),
        ativo_atual=favorite.imovel.ativo,
        imovel=snapshot,
    )


def list_favorites(
    session: Session, user_id: str, pagina: int, por_pagina: int
) -> tuple[list[FavoriteRead], int]:
    favorites, total = property_repository.list_favorites(
        session, user_id, (pagina - 1) * por_pagina, por_pagina
    )
    return [to_favorite_read(favorite) for favorite in favorites], total


def add_favorite(session: Session, user_id: str, numero: str) -> FavoriteRead:
    property_ = _get_property(session, numero)
    favorite = property_repository.find_favorite(session, user_id, numero)
    if favorite is None:
        snapshot = PropertyRead.model_validate(property_).model_dump(mode="json")
        favorite = Favorite(
            usuario_id=user_id,
            numero_imovel=numero,
            imovel_json=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
            favoritado_em=int(datetime.now(UTC).timestamp() * 1000),
        )
        session.add(favorite)
        session.commit()
        session.refresh(favorite)
    return to_favorite_read(favorite)


def remove_favorite(session: Session, user_id: str, numero: str) -> None:
    favorite = property_repository.find_favorite(session, user_id, numero)
    if favorite is not None:
        session.delete(favorite)
        session.commit()
