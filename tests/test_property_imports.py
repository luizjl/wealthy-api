import json
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from wealthy_api import security
from wealthy_api.config import Settings, get_settings
from wealthy_api.database import create_database_engine, get_session
from wealthy_api.main import app
from wealthy_api.models import Base, Property, PropertyImportRowLog, PropertyImportStaging
from wealthy_api.services.property_imports import import_properties_csv

CSV_HEADER = (
    "numero;uf;cidade;bairro;endereco;preco;valorAvaliacao;desconto;"
    "financiamento;descricao;modalidade;link\n"
)


@pytest.fixture
def admin_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'admin-import.db'}")
    Base.metadata.create_all(engine)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        firebase_allowed_uids="approved-user",
        firebase_admin_uids="admin-user",
        import_max_bytes=4096,
    )
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "approved-user"},
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_csv_import_stages_validates_upserts_and_marks_reactivation(tmp_path) -> None:
    csv_file = tmp_path / "Lista_imoveis_geral.csv"
    first_load = (
        CSV_HEADER + "PROP-1;GO;Goiânia;Centro;Rua A;1.234,50;2.000,00;30,5%;Não;Casa;Venda;"
        "http://example.com/1\n"
        + "PROP-BAD;XX;Cidade;Bairro;Rua B;100,00;200,00;10%;Sim;Casa;Venda;"
        "http://example.com/2\n"
        + "PROP-1;GO;Goiânia;Centro;Rua C;999,00;1.000,00;20%;Sim;Casa;Venda;"
        "http://example.com/3\n"
    )
    csv_file.write_bytes(first_load.encode("cp1252"))

    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'import.db'}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            first_run = import_properties_csv(session, csv_file, batch_size=2)

            assert first_run.status == "completed"
            assert first_run.total_rows == 3
            assert first_run.inserted_rows == 1
            assert first_run.rejected_rows == 1
            assert first_run.duplicate_rows == 1

            property_ = session.get(Property, "PROP-1")
            assert property_ is not None
            assert property_.preco == 1234.5
            assert property_.valor_avaliacao == 2000.0
            assert property_.aceita_financiamento == "nao"
            assert property_.cidade == "Goiânia"

            property_.link_matricula = "http://registry.example/property/1"
            property_.vendido = True
            property_.data_denda = date(2026, 9, 1)
            property_.valor_venda = 1200.0
            property_.ativo = False
            session.commit()

            csv_file.write_bytes(
                (
                    CSV_HEADER + "PROP-1;GO;Goiânia;Centro;Rua Atualizada;1.500,00;2.100,00;25%;"
                    "Sim;Descrição atualizada;Venda;http://example.com/1\n"
                ).encode("cp1252")
            )
            second_run = import_properties_csv(session, csv_file, batch_size=1)

            assert second_run.status == "completed"
            assert second_run.updated_rows == 0
            assert second_run.reactivated_rows == 1
            session.refresh(property_)
            assert property_.preco == 1500.0
            assert property_.ativo is True
            assert property_.link_matricula == "http://registry.example/property/1"
            assert property_.vendido is True
            assert property_.data_denda == date(2026, 9, 1)
            assert property_.valor_venda == 1200.0

            staged_rows = session.query(PropertyImportStaging).filter_by(run_id=first_run.id).all()
            row_logs = session.query(PropertyImportRowLog).filter_by(run_id=first_run.id).all()
            assert len(staged_rows) == 3
            assert len(row_logs) == 3
            assert json.loads(staged_rows[0].raw_json)["cidade"] == "Goiânia"
            assert {row.status for row in row_logs} == {"imported", "rejected", "duplicate"}
    finally:
        engine.dispose()


def test_admin_import_endpoint_uploads_csv_and_returns_report(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_content = (
        CSV_HEADER + "API-1;GO;Goiânia;Centro;Rua A;1.234,50;2.000,00;30,5%;Não;Casa;Venda;"
        "http://example.com/1\n"
    ).encode("cp1252")
    upload = {"file": ("Lista_imoveis_geral.csv", csv_content, "text/csv")}

    denied = admin_client.post(
        "/api/v1/admin/imoveis/importacoes",
        files=upload,
        headers={"Authorization": "Bearer test-token"},
    )
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "admin-user"},
    )
    imported = admin_client.post(
        "/api/v1/admin/imoveis/importacoes",
        files=upload,
        data={"batch_size": "1"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert denied.status_code == 403
    assert imported.status_code == 200
    run = imported.json()
    assert run["status"] == "completed"
    assert run["source_file"] == "Lista_imoveis_geral.csv"
    assert run["inserted_rows"] == 1

    rows = admin_client.get(
        f"/api/v1/admin/imoveis/importacoes/{run['id']}/linhas?status=imported",
        headers={"Authorization": "Bearer test-token"},
    )

    assert rows.status_code == 200
    assert rows.json()["total"] == 1
    assert rows.json()["items"][0]["numero_imovel"] == "API-1"


def test_admin_import_endpoint_enforces_upload_size_limit(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        security,
        "verify_firebase_id_token",
        lambda token, settings: {"uid": "admin-user"},
    )
    response = admin_client.post(
        "/api/v1/admin/imoveis/importacoes",
        files={"file": ("too-large.csv", b"x" * 5000, "text/csv")},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 413
