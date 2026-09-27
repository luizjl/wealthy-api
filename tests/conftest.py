from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Connection

from wealthy_api.database import create_configured_database_engine


@pytest.fixture
def oracle_connection() -> Iterator[Connection]:
    engine = create_configured_database_engine()
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()
