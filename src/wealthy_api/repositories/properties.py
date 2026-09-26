from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wealthy_api.models.property import Favorite, Property


def find_property(session: Session, numero: str) -> Property | None:
    return session.get(Property, numero)


def find_favorite(session: Session, user_id: str, numero: str) -> Favorite | None:
    return session.get(Favorite, {"usuario_id": user_id, "numero_imovel": numero})


def list_properties(
    session: Session,
    offset: int,
    limit: int,
    *,
    ufs: list[str] | None = None,
    cidade: str | None = None,
    cidades_excluir: list[str] | None = None,
    bairro: str | None = None,
    modalidade: str | None = None,
    financiamento: str | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
) -> tuple[list[Property], int]:
    filters = []
    if ufs:
        filters.append(Property.uf.in_(ufs))
    if cidade:
        filters.append(func.upper(func.trim(Property.cidade)).contains(cidade.upper()))
    if cidades_excluir:
        filters.append(func.upper(func.trim(Property.cidade)).notin_(cidades_excluir))
    if bairro:
        filters.append(func.upper(func.trim(Property.bairro)).contains(bairro.upper()))
    if modalidade:
        filters.append(func.upper(func.trim(Property.modalidade)).contains(modalidade.upper()))
    if financiamento:
        filters.append(func.lower(func.trim(Property.aceita_financiamento)) == financiamento)
    if preco_min is not None:
        filters.append(Property.preco >= preco_min)
    if preco_max is not None:
        filters.append(Property.preco <= preco_max)

    where_clause = select(Property)
    if filters:
        where_clause = where_clause.where(*filters)
    count_query = select(func.count()).select_from(Property)
    if filters:
        count_query = count_query.where(*filters)

    total = session.scalar(count_query) or 0
    properties = session.scalars(
        where_clause.order_by(Property.numero).offset(offset).limit(limit)
    ).all()
    return list(properties), total


def list_favorites(
    session: Session, user_id: str, offset: int, limit: int
) -> tuple[list[Favorite], int]:
    statement = select(Favorite).where(Favorite.usuario_id == user_id)
    total = (
        session.scalar(
            select(func.count()).select_from(Favorite).where(Favorite.usuario_id == user_id)
        )
        or 0
    )
    favorites = session.scalars(
        statement.order_by(Favorite.favoritado_em.desc(), Favorite.numero_imovel)
        .offset(offset)
        .limit(limit)
    ).all()
    return list(favorites), total
