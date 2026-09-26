from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wealthy_api.models.person import Person


def find_person(session: Session, person_id: int) -> Person | None:
    return session.get(Person, person_id)


def list_people(session: Session, offset: int, limit: int) -> tuple[list[Person], int]:
    total = session.scalar(select(func.count()).select_from(Person)) or 0
    people = session.scalars(select(Person).order_by(Person.id).offset(offset).limit(limit)).all()
    return list(people), total
