from datetime import UTC, datetime

from sqlalchemy.orm import Session

from wealthy_api.models.showcase import Showcase
from wealthy_api.repositories import showcases as showcase_repository
from wealthy_api.schemas.showcase import ShowcaseCreate, ShowcaseUpdate


class ShowcaseNotFoundError(Exception):
    pass


def _get_showcase(session: Session, showcase_id: int) -> Showcase:
    showcase = showcase_repository.find_showcase(session, showcase_id)
    if showcase is None:
        raise ShowcaseNotFoundError
    return showcase


def _now_milliseconds() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def list_showcases(session: Session, pagina: int, por_pagina: int) -> tuple[list[Showcase], int]:
    return showcase_repository.list_showcases(session, (pagina - 1) * por_pagina, por_pagina)


def get_showcase(session: Session, showcase_id: int) -> Showcase:
    return _get_showcase(session, showcase_id)


def create_showcase(session: Session, payload: ShowcaseCreate) -> Showcase:
    created_at = _now_milliseconds()
    showcase = Showcase(
        **payload.model_dump(exclude={"link"}),
        link=str(payload.link),
        criado_em=created_at,
        atualizado_em=created_at,
    )
    session.add(showcase)
    session.commit()
    session.refresh(showcase)
    return showcase


def update_showcase(session: Session, showcase_id: int, payload: ShowcaseUpdate) -> Showcase:
    showcase = _get_showcase(session, showcase_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "link":
            value = str(value)
        setattr(showcase, field, value)
    showcase.atualizado_em = max(_now_milliseconds(), showcase.criado_em + 1)
    session.commit()
    session.refresh(showcase)
    return showcase


def delete_showcase(session: Session, showcase_id: int) -> None:
    showcase = _get_showcase(session, showcase_id)
    session.delete(showcase)
    session.commit()


def to_showcase_read(showcase: Showcase) -> dict:
    return {
        "id": showcase.id,
        "nome": showcase.nome,
        "link": showcase.link,
        "descricao": showcase.descricao.strip() if showcase.descricao else "",
        "criado_em": datetime.fromtimestamp(showcase.criado_em / 1000, tz=UTC),
        "atualizado_em": datetime.fromtimestamp(showcase.atualizado_em / 1000, tz=UTC),
    }
