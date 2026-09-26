import json
from datetime import date

from sqlalchemy.orm import Session

from wealthy_api.database import create_database_engine
from wealthy_api.models import Base, Property, PropertyImportRowLog, PropertyImportStaging
from wealthy_api.services.property_imports import import_properties_csv

CSV_HEADER = (
    "numero;uf;cidade;bairro;endereco;preco;valorAvaliacao;desconto;"
    "financiamento;descricao;modalidade;link\n"
)


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
