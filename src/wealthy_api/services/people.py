from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wealthy_api.models.person import Person
from wealthy_api.repositories import people as people_repository
from wealthy_api.schemas.person import PersonCreate, PersonUpdate


class PersonNotFoundError(Exception):
    pass


class PersonConflictError(Exception):
    pass


def create_person(session: Session, payload: PersonCreate) -> Person:
    person = Person(**payload.model_dump())
    session.add(person)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersonConflictError from error
    session.refresh(person)
    return person


def list_people(session: Session, pagina: int, por_pagina: int) -> tuple[list[Person], int]:
    offset = (pagina - 1) * por_pagina
    return people_repository.list_people(session, offset, por_pagina)


def get_person(session: Session, person_id: int) -> Person:
    person = people_repository.find_person(session, person_id)
    if person is None:
        raise PersonNotFoundError
    return person


def update_person(session: Session, person_id: int, payload: PersonUpdate) -> Person:
    person = get_person(session, person_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersonConflictError from error
    session.refresh(person)
    return person


def delete_person(session: Session, person_id: int) -> None:
    person = get_person(session, person_id)
    session.delete(person)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersonConflictError from error
