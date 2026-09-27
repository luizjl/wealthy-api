from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from wealthy_api import security
from wealthy_api.config import Settings, get_settings
from wealthy_api.database import create_configured_database_engine, get_session
from wealthy_api.main import app


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


def test_missing_firebase_project_is_service_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_for_missing_project(token, settings):
        raise security.FirebaseConfigurationError("project ID missing")

    monkeypatch.setattr(security, "verify_firebase_id_token", fail_for_missing_project)

    response = client.get("/api/v1/imoveis", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Autenticação Firebase não configurada no servidor"


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


def test_sqlalchemy_engine_connects_to_oracle() -> None:
    engine = create_configured_database_engine()
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1 FROM DUAL")).scalar_one() == 1
    finally:
        engine.dispose()


@pytest.fixture
def people_client(
    oracle_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        with Session(bind=oracle_connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        firebase_allowed_uids="approved-user",
        firebase_admin_uids="admin-user",
    )
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "approved-user"},
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_people_create_and_get(people_client: TestClient) -> None:
    document_number = uuid4().hex
    create_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "  Ana Silva ", "tipo_documento": "CPF", "numero": document_number},
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
    baseline = people_client.get("/api/v1/pessoas?pagina=1&porPagina=1", headers=headers).json()[
        "total"
    ]
    document_prefix = uuid4().hex[:16]
    create_responses = []
    for index in range(3):
        create_responses.append(
            people_client.post(
                "/api/v1/pessoas",
                json={
                    "nome": f"Pessoa {index}",
                    "tipo_documento": "CNPJ",
                    "numero": f"{document_prefix}-{index}",
                },
                headers=headers,
            )
        )

    pagina = (baseline + 1) // 2 + 1
    response = people_client.get(f"/api/v1/pessoas?pagina={pagina}&porPagina=2", headers=headers)

    assert response.status_code == 200
    assert all(created.status_code == 201 for created in create_responses)
    assert response.json()["total"] == baseline + 3
    assert response.json()["pagina"] == pagina
    assert response.json()["porPagina"] == 2
    assert len(response.json()["items"]) == 2


def test_people_duplicate_document_returns_conflict(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    payload = {"nome": "Pessoa", "tipo_documento": "CPF", "numero": uuid4().hex}
    people_client.post("/api/v1/pessoas", json=payload, headers=headers)

    response = people_client.post("/api/v1/pessoas", json=payload, headers=headers)

    assert response.status_code == 409


def test_people_patch_and_delete(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    create_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Pessoa", "tipo_documento": "CNPJ", "numero": uuid4().hex},
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
    number_prefix = uuid4().hex[:16]
    owner_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Proprietário", "tipo_documento": "CPF", "numero": number_prefix},
        headers=headers,
    )
    origin_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Órgão", "tipo_documento": "CNPJ", "numero": number_prefix + "0"},
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
    number_prefix = uuid4().hex[:16]
    first_person = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Pessoa", "tipo_documento": "CNPJ", "numero": number_prefix},
        headers=headers,
    )
    second_person = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Outra", "tipo_documento": "CPF", "numero": number_prefix + "0"},
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


def test_process_requires_existing_person_and_restricts_person_delete(
    people_client: TestClient,
) -> None:
    headers = {"Authorization": "Bearer test-token"}
    number = uuid4().hex
    missing_person_response = people_client.post(
        "/api/v1/processos",
        json={"id_pessoa": 2_147_483_000, "numero": "100", "assunto": "Cobrança"},
        headers=headers,
    )
    person_response = people_client.post(
        "/api/v1/pessoas",
        json={"nome": "Parte", "tipo_documento": "CPF", "numero": number},
        headers=headers,
    )
    process_response = people_client.post(
        "/api/v1/processos",
        json={
            "id_pessoa": person_response.json()["id"],
            "numero": "100",
            "assunto": "Cobrança",
        },
        headers=headers,
    )
    person_delete_response = people_client.delete(
        f"/api/v1/pessoas/{person_response.json()['id']}", headers=headers
    )

    assert missing_person_response.status_code == 404
    assert process_response.status_code == 201
    assert process_response.json()["resumo"] == ""
    assert process_response.json()["valor"] == 0.0
    assert process_response.json()["obs"] == ""
    assert person_delete_response.status_code == 409


def test_showcase_update_preserves_created_at_and_advances_updated_at(
    people_client: TestClient,
) -> None:
    headers = {"Authorization": "Bearer test-token"}
    create_response = people_client.post(
        "/api/v1/vitrines",
        json={"nome": "Oportunidades", "link": "https://example.com/"},
        headers=headers,
    )
    showcase = create_response.json()

    update_response = people_client.patch(
        f"/api/v1/vitrines/{showcase['id']}",
        json={"descricao": "Links úteis"},
        headers=headers,
    )
    invalid_link_response = people_client.post(
        "/api/v1/vitrines",
        json={"nome": "Inválida", "link": "ftp://example.com/resource"},
        headers=headers,
    )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert update_response.json()["criado_em"] == showcase["criado_em"]
    assert update_response.json()["atualizado_em"] > showcase["atualizado_em"]
    assert update_response.json()["descricao"] == "Links úteis"
    assert invalid_link_response.status_code == 422


def test_property_filters_include_inactive_properties(people_client: TestClient) -> None:
    headers = {"Authorization": "Bearer test-token"}
    property_prefix = uuid4().hex[:16]
    first_number = f"PROP-{property_prefix}-1"
    second_number = f"PROP-{property_prefix}-2"
    first_city = f"Test City {property_prefix}"
    second_city = f"Other Test City {property_prefix}"
    first = people_client.post(
        "/api/v1/imoveis",
        json={
            "numero": first_number,
            "uf": "go",
            "cidade": first_city,
            "bairro": "Centro",
            "preco": 150,
            "aceita_financiamento": "não",
            "modalidade": "Casa",
            "link_matricula": "http://registry.example/property/1",
        },
        headers=headers,
    )
    second = people_client.post(
        "/api/v1/imoveis",
        json={
            "numero": second_number,
            "uf": "SP",
            "cidade": second_city,
            "preco": 250,
        },
        headers=headers,
    )

    assert first.status_code == 201
    assert first.json()["ativo"] is True
    assert first.json()["vendido"] is False
    assert first.json()["aceita_financiamento"] == "nao"
    assert (
        people_client.post(f"/api/v1/imoveis/{first_number}/inativar", headers=headers).json()[
            "ativo"
        ]
        is False
    )

    response = people_client.get("/api/v1/imoveis", headers=headers)
    filtered = people_client.get(
        "/api/v1/imoveis",
        params=[
            ("uf", "GO"),
            ("uf", "SP"),
            ("cidade", second_city),
            ("cidadesExcluir", first_city),
            ("precoMin", "200"),
            ("precoMax", "300"),
        ],
        headers=headers,
    )
    invalid_filter = people_client.get("/api/v1/imoveis?uf=XX", headers=headers)
    invalid_matricula_link = people_client.post(
        "/api/v1/imoveis",
        json={
            "numero": f"PROP-{property_prefix}-HTTPS",
            "link_matricula": "https://example.com/registry",
        },
        headers=headers,
    )

    assert second.status_code == 201
    assert response.status_code == 200
    result_numbers = {item["numero"] for item in response.json()["items"]}
    assert {first_number, second_number}.issubset(result_numbers)
    assert (
        next(item for item in response.json()["items"] if item["numero"] == first_number)["ativo"]
        is False
    )
    assert filtered.status_code == 200
    assert [item["numero"] for item in filtered.json()["items"]] == [second_number]
    assert invalid_filter.status_code == 400
    assert invalid_matricula_link.status_code == 422


def test_favorites_are_idempotent_uid_scoped_and_keep_snapshot(
    people_client: TestClient,
) -> None:
    headers = {"Authorization": "Bearer test-token"}
    property_number = "FAV-" + uuid4().hex[:16]
    created = people_client.post(
        "/api/v1/imoveis",
        json={"numero": property_number, "cidade": "Sao Paulo", "uf": "SP"},
        headers=headers,
    )
    favorite_url = f"/api/v1/me/favoritos/{property_number}"

    first_put = people_client.put(favorite_url, headers=headers)
    second_put = people_client.put(favorite_url, headers=headers)
    inactivated = people_client.post(f"/api/v1/imoveis/{property_number}/inativar", headers=headers)
    favorites = people_client.get("/api/v1/me/favoritos", headers=headers)
    first_delete = people_client.delete(favorite_url, headers=headers)
    second_delete = people_client.delete(favorite_url, headers=headers)

    assert created.status_code == 201
    assert first_put.status_code == 200
    assert second_put.json()["favoritado_em"] == first_put.json()["favoritado_em"]
    assert inactivated.status_code == 200
    favorite = next(
        item for item in favorites.json()["items"] if item["numero_imovel"] == property_number
    )
    assert favorite["imovel"]["ativo"] is True
    assert favorite["ativo_atual"] is False
    assert first_delete.status_code == 204
    assert second_delete.status_code == 204
