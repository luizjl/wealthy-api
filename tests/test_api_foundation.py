from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from wealthy_api import security
from wealthy_api.config import Settings, get_settings
from wealthy_api.database import create_database_engine, get_session
from wealthy_api.main import app
from wealthy_api.models import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(firebase_allowed_uids="approved-user")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check_is_available_without_authentication(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_account_endpoint_requires_a_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_allowed_firebase_user_can_access_account(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "approved-user", "email": "owner@example.com"},
    )

    response = client.get("/api/v1/me", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json() == {"uid": "approved-user", "email": "owner@example.com"}


def test_authenticated_but_unapproved_user_is_forbidden(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "unapproved-user"},
    )

    response = client.get("/api/v1/me", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 403


def test_sqlalchemy_engine_connects_to_local_sqlite() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()


@pytest.fixture
def people_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_path = tmp_path / "people-test.db"
    engine = create_database_engine(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(engine)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(firebase_allowed_uids="approved-user")
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "approved-user"},
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_people_create_and_get(people_client: TestClient) -> None:
    create_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "  Ana Silva ", "tipo_documento": "CPF", "numero": "123"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert create_response.status_code == 201
    person = create_response.json()
    assert person["nome"] == "Ana Silva"
    assert person["contatos"] is None

    get_response = people_client.get(
        f"/api/v1/pessoas/{person['id']}", headers={"Authorization": "Bearer test-token"}
    )

    assert get_response.status_code == 200
    assert get_response.json() == person


def test_people_list_is_paginated(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    for index in range(3):
        people_client.post(
            "/api/v1/pessoas",
            json={"nome": f"Pessoa {index}", "tipo_documento": "CNPJ", "numero": str(index)},
            headers=headers,
        )

    response = people_client.get("/api/v1/pessoas?pagina=2&porPagina=2", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["pagina"] == 2
    assert response.json()["porPagina"] == 2
    assert len(response.json()["items"]) == 1


def test_people_duplicate_document_returns_conflict(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    payload = {"nome": "Pessoa", "tipo_documento": "CPF", "numero": "123"}
    people_client.post("/api/v1/pessoas", json=payload, headers=headers)

    response = people_client.post("/api/v1/pessoas", json=payload, headers=headers)

    assert response.status_code == 409


def test_people_patch_and_delete(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    create_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Pessoa", "tipo_documento": "CNPJ", "numero": "456"},
        headers=headers,
    )
    person_id = create_response.json()["id"]

    patch_response = people_client.patch(
        f"/api/v1/pessoas/{person_id}", json={"contatos": "email@example.com"}, headers=headers
    )
    delete_response = people_client.delete(f"/api/v1/pessoas/{person_id}", headers=headers)
    missing_response = people_client.get(f"/api/v1/pessoas/{person_id}", headers=headers)

    assert patch_response.status_code == 200
    assert patch_response.json()["contatos"] == "email@example.com"
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


def test_auction_file_is_deleted_with_its_auction(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    owner_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Proprietário", "tipo_documento": "CPF", "numero": "111"},
        headers=headers,
    )
    origin_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Órgão", "tipo_documento": "CNPJ", "numero": "222"},
        headers=headers,
    )
    auction_response = people_client.post(
        "/api/v1/leiloes",
        json={
            "titulo": "Casa em leilão",
            "tipo": "CASA",
            "id_proprietario": owner_response.json()["id"],
            "link": "https://example.com/leilao",
            "descricao": "Descrição",
            "cidade": "Goiânia",
            "estado": "go",
            "id_orgao_origem": origin_response.json()["id"],
            "datas": ["2026-10-01"],
        },
        headers=headers,
    )

    assert auction_response.status_code == 201
    auction = auction_response.json()
    assert auction["estado"] == "GO"
    assert auction["datas"] == ["2026-10-01"]

    file_response = people_client.post(
        f"/api/v1/leiloes/{auction['id']}/arquivos",
        json={"nome": "Edital", "link": "https://example.com/edital.pdf"},
        headers=headers,
    )
    file_id = file_response.json()["id"]
    delete_response = people_client.delete(f"/api/v1/leiloes/{auction['id']}", headers=headers)
    missing_file_response = people_client.get(f"/api/v1/arquivos/{file_id}", headers=headers)

    assert file_response.status_code == 201
    assert delete_response.status_code == 204
    assert missing_file_response.status_code == 404


def test_auction_rejects_people_with_wrong_document_types(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    first_person = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Pessoa", "tipo_documento": "CNPJ", "numero": "333"},
        headers=headers,
    )
    second_person = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Outra", "tipo_documento": "CPF", "numero": "444"},
        headers=headers,
    )

    response = people_client.post(
        "/api/v1/leiloes",
        json={
            "titulo": "Leilão",
            "tipo": "CASA",
            "id_proprietario": first_person.json()["id"],
            "link": "https://example.com",
            "descricao": "Descrição",
            "cidade": "Goiânia",
            "estado": "GO",
            "id_orgao_origem": second_person.json()["id"],
        },
        headers=headers,
    )

    assert response.status_code == 422
