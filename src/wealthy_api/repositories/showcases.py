from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wealthy_api.models.showcase import Showcase


def find_showcase(session: Session, showcase_id: int) -> Showcase | None:
    return session.get(Showcase, showcase_id)


def list_showcases(session: Session, offset: int, limit: int) -> tuple[list[Showcase], int]:
    total = session.scalar(select(func.count()).select_from(Showcase)) or 0
    showcases = session.scalars(
        select(Showcase).order_by(Showcase.id).offset(offset).limit(limit)
    ).all()
    return list(showcases), total
