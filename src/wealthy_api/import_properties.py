import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from wealthy_api.database import get_engine
from wealthy_api.models.property_import import PropertyImportRowLog
from wealthy_api.services.property_imports import import_properties_csv, resume_import_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa manualmente o CSV de imóveis da Caixa")
    parser.add_argument("csv_path", nargs="?", help="Caminho para Lista_imoveis_geral.csv")
    parser.add_argument("--resume-run-id", type=int, help="Retoma o staging de uma execução falha")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    if args.resume_run_id is not None and args.csv_path is not None:
        parser.error("informe csv_path ou --resume-run-id, não ambos")
    if args.resume_run_id is None and args.csv_path is None:
        parser.error("informe csv_path ou --resume-run-id")

    with Session(get_engine()) as session:
        if args.resume_run_id is not None:
            run = resume_import_run(session, args.resume_run_id, batch_size=args.batch_size)
        else:
            run = import_properties_csv(
                session,
                args.csv_path,
                batch_size=args.batch_size,
            )
        logs = session.scalars(
            select(PropertyImportRowLog)
            .where(
                PropertyImportRowLog.run_id == run.id,
                PropertyImportRowLog.status.in_(["rejected", "reactivated"]),
            )
            .order_by(PropertyImportRowLog.line_number)
        ).all()

        print(f"Execução: {run.id} ({run.status})")
        print(f"Linhas: {run.total_rows}")
        print(f"Inseridos: {run.inserted_rows}")
        print(f"Atualizados: {run.updated_rows}")
        print(f"Rejeitados: {run.rejected_rows}")
        print(f"Duplicados: {run.duplicate_rows}")
        print(f"Reativações: {run.reactivated_rows}")
        for row in logs:
            if row.status == "reactivated":
                print(f"REATIVADO linha {row.line_number}: imóvel {row.numero_imovel}")
            else:
                print(f"REJEITADO linha {row.line_number}: {row.detail}")
        if run.error_message:
            print(f"Falha: {run.error_message}", file=sys.stderr)
        return 0 if run.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
