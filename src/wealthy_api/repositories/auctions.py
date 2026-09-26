from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wealthy_api.models.auction import Auction, AuctionFile
from wealthy_api.models.person import Person


def find_auction(session: Session, auction_id: int) -> Auction | None:
    return session.get(Auction, auction_id)


def find_file(session: Session, file_id: int) -> AuctionFile | None:
    return session.get(AuctionFile, file_id)


def find_person(session: Session, person_id: int) -> Person | None:
    return session.get(Person, person_id)


def list_auctions(session: Session, offset: int, limit: int) -> tuple[list[Auction], int]:
    total = session.scalar(select(func.count()).select_from(Auction)) or 0
    auctions = session.scalars(
        select(Auction).order_by(Auction.id).offset(offset).limit(limit)
    ).all()
    return list(auctions), total


def list_files(session: Session, auction_id: int) -> list[AuctionFile]:
    statement = (
        select(AuctionFile).where(AuctionFile.leilao_id == auction_id).order_by(AuctionFile.id)
    )
    return list(session.scalars(statement).all())
