from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wealthy_api.models.auction import Auction, AuctionFile
from wealthy_api.models.person import Person, TipoDocumento
from wealthy_api.repositories import auctions as auction_repository
from wealthy_api.schemas.auction import (
    AuctionCreate,
    AuctionFileCreate,
    AuctionFileUpdate,
    AuctionUpdate,
)


class AuctionNotFoundError(Exception):
    pass


class AuctionFileNotFoundError(Exception):
    pass


class RelatedPersonInvalidError(Exception):
    pass


class RelatedRecordConflictError(Exception):
    pass


def _serialize_dates(values) -> str:
    serialized = "|".join(value.strftime("%d/%m/%Y") for value in values)
    return serialized or None


def _validate_person_type(person: Person | None, expected: TipoDocumento) -> None:
    if person is None or person.tipo_documento != expected:
        raise RelatedPersonInvalidError


def _validate_people(session: Session, proprietor_id: int, origin_id: int) -> None:
    _validate_person_type(auction_repository.find_person(session, proprietor_id), TipoDocumento.CPF)
    _validate_person_type(auction_repository.find_person(session, origin_id), TipoDocumento.CNPJ)


def _get_auction(session: Session, auction_id: int) -> Auction:
    auction = auction_repository.find_auction(session, auction_id)
    if auction is None:
        raise AuctionNotFoundError
    return auction


def _get_file(session: Session, file_id: int) -> AuctionFile:
    auction_file = auction_repository.find_file(session, file_id)
    if auction_file is None:
        raise AuctionFileNotFoundError
    return auction_file


def to_auction_read(auction: Auction) -> dict:
    dates = [
        datetime.strptime(value, "%d/%m/%Y").date()
        for value in (auction.datas or "").split("|")
        if value.strip()
    ]
    created_at = datetime.fromtimestamp(auction.criado_em / 1000, tz=UTC)
    return {
        "id": auction.id,
        "titulo": auction.titulo,
        "ativo": auction.ativo,
        "tipo": auction.tipo,
        "url_matricula": auction.url_matricula,
        "id_proprietario": auction.id_proprietario,
        "link": auction.link,
        "descricao": auction.descricao,
        "cidade": auction.cidade,
        "estado": auction.estado,
        "id_orgao_origem": auction.id_orgao_origem,
        "datas": dates,
        "criado_em": created_at,
    }


def list_auctions(session: Session, pagina: int, por_pagina: int) -> tuple[list[Auction], int]:
    return auction_repository.list_auctions(session, (pagina - 1) * por_pagina, por_pagina)


def get_auction(session: Session, auction_id: int) -> Auction:
    return _get_auction(session, auction_id)


def create_auction(session: Session, payload: AuctionCreate) -> Auction:
    _validate_people(session, payload.id_proprietario, payload.id_orgao_origem)
    values = payload.model_dump(exclude={"datas"})
    values["link"] = str(payload.link)
    values["url_matricula"] = str(payload.url_matricula) if payload.url_matricula else None
    auction = Auction(
        **values,
        datas=_serialize_dates(payload.datas),
        criado_em=int(datetime.now(UTC).timestamp() * 1000),
    )
    session.add(auction)
    session.commit()
    session.refresh(auction)
    return auction


def update_auction(session: Session, auction_id: int, payload: AuctionUpdate) -> Auction:
    auction = _get_auction(session, auction_id)
    updates = payload.model_dump(exclude_unset=True)
    proprietor_id = updates.get("id_proprietario", auction.id_proprietario)
    origin_id = updates.get("id_orgao_origem", auction.id_orgao_origem)
    _validate_people(session, proprietor_id, origin_id)

    for field, value in updates.items():
        if field == "datas":
            value = _serialize_dates(value or [])
        elif field in {"link", "url_matricula"} and value is not None:
            value = str(value)
        setattr(auction, field, value)
    session.commit()
    session.refresh(auction)
    return auction


def delete_auction(session: Session, auction_id: int) -> None:
    auction = _get_auction(session, auction_id)
    session.delete(auction)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise RelatedRecordConflictError from error


def list_auction_files(session: Session, auction_id: int) -> list[AuctionFile]:
    _get_auction(session, auction_id)
    return auction_repository.list_files(session, auction_id)


def create_auction_file(
    session: Session, auction_id: int, payload: AuctionFileCreate
) -> AuctionFile:
    _get_auction(session, auction_id)
    auction_file = AuctionFile(
        nome=payload.nome,
        link=str(payload.link),
        leilao_id=auction_id,
    )
    session.add(auction_file)
    session.commit()
    session.refresh(auction_file)
    return auction_file


def get_auction_file(session: Session, file_id: int) -> AuctionFile:
    return _get_file(session, file_id)


def update_auction_file(session: Session, file_id: int, payload: AuctionFileUpdate) -> AuctionFile:
    auction_file = _get_file(session, file_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "link":
            value = str(value)
        setattr(auction_file, field, value)
    session.commit()
    session.refresh(auction_file)
    return auction_file


def delete_auction_file(session: Session, file_id: int) -> None:
    auction_file = _get_file(session, file_id)
    session.delete(auction_file)
    session.commit()
