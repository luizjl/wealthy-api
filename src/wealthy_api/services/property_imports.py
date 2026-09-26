import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from wealthy_api.models.property import Property
from wealthy_api.models.property_import import (
    PropertyImportRowLog,
    PropertyImportRun,
    PropertyImportStaging,
)
from wealthy_api.repositories import properties as property_repository
from wealthy_api.repositories import property_imports as import_repository
from wealthy_api.schemas.property import PropertyCreate

CSV_FIELDS = {
    "numero": "numero",
    "uf": "uf",
    "cidade": "cidade",
    "bairro": "bairro",
    "endereco": "endereco",
    "preco": "preco",
    "valoravaliacao": "valor_avaliacao",
    "desconto": "desconto",
    "financiamento": "aceita_financiamento",
    "descricao": "descricao",
    "modalidade": "modalidade",
    "link": "link",
}
CSV_PROPERTY_FIELDS = tuple(CSV_FIELDS.values())


def _now_milliseconds() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _normalize_header(value: str) -> str:
    return value.strip().lstrip("\ufeffï»¿").casefold()


def _parse_number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().replace("R$", "").replace("%", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    return float(normalized)


def _validation_detail(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors(include_input=False)
    )[:2000]


def _row_log(run_id: int, row_number: int, status: str, number: str | None, detail: str | None):
    return PropertyImportRowLog(
        run_id=run_id,
        line_number=row_number,
        numero_imovel=number,
        status=status,
        detail=detail,
    )


def _property_payload(row: dict, headers: dict[str, str]) -> PropertyCreate:
    values = {}
    for csv_name, model_name in CSV_FIELDS.items():
        raw_value = row.get(headers[csv_name])
        if model_name in {"preco", "valor_avaliacao", "desconto"}:
            values[model_name] = _parse_number(raw_value)
        elif model_name == "numero":
            values[model_name] = raw_value
        else:
            normalized = raw_value.strip() if raw_value else ""
            values[model_name] = normalized or None
    return PropertyCreate.model_validate(values)


def _finish_run(session: Session, run: PropertyImportRun, status: str, error: str | None = None):
    run.status = status
    run.finished_at = _now_milliseconds()
    run.error_message = error[:2000] if error else None
    session.commit()
    session.refresh(run)
    return run


def import_properties_csv(
    session: Session,
    file_path: str | Path,
    *,
    batch_size: int = 500,
) -> PropertyImportRun:
    if batch_size < 1:
        raise ValueError("batch_size deve ser maior que zero")
    source_path = Path(file_path).expanduser()
    run = import_repository.create_run(session, str(source_path), _now_milliseconds())
    run_id = run.id

    try:
        staged_count = 0
        with source_path.open("r", encoding="cp1252", newline="") as source:
            reader = csv.DictReader(source, delimiter=";")
            headers = {
                _normalize_header(name): name
                for name in (reader.fieldnames or [])
                if name is not None
            }
            batch = []
            for row_number, row in enumerate(reader, start=2):
                batch.append(
                    PropertyImportStaging(
                        run_id=run_id,
                        line_number=row_number,
                        raw_json=json.dumps(row, ensure_ascii=False),
                    )
                )
                staged_count += 1
                if len(batch) >= batch_size:
                    import_repository.stage_rows(session, run_id, batch)
                    batch = []
            if batch:
                import_repository.stage_rows(session, run_id, batch)

        run = import_repository.get_run(session, run_id)
        if run is None:
            raise RuntimeError("Registro da execução de importação não encontrado")
        run.total_rows = staged_count
        session.commit()

        missing_headers = sorted(set(CSV_FIELDS) - set(headers))
        if missing_headers:
            raise ValueError("Colunas ausentes no CSV: " + ", ".join(missing_headers))

        inserted = updated = rejected = duplicates = reactivated = 0
        seen_numbers: set[str] = set()
        offset = 0
        while True:
            staged_rows = import_repository.get_staged_batch(session, run_id, offset, batch_size)
            if not staged_rows:
                break

            logs = []
            for staged in staged_rows:
                row = json.loads(staged.raw_json)
                raw_number = row.get(headers["numero"])
                numero = raw_number.strip() if raw_number else None
                if numero and numero in seen_numbers:
                    duplicates += 1
                    logs.append(
                        _row_log(
                            run_id,
                            staged.line_number,
                            "duplicate",
                            numero,
                            "Número repetido no CSV",
                        )
                    )
                    continue

                try:
                    payload = _property_payload(row, headers)
                except ValidationError as error:
                    rejected += 1
                    logs.append(
                        _row_log(
                            run_id,
                            staged.line_number,
                            "rejected",
                            numero,
                            _validation_detail(error),
                        )
                    )
                    continue
                except ValueError as error:
                    rejected += 1
                    logs.append(
                        _row_log(run_id, staged.line_number, "rejected", numero, str(error))
                    )
                    continue

                seen_numbers.add(payload.numero)
                property_ = property_repository.find_property(session, payload.numero)
                if property_ is None:
                    session.add(Property(**payload.model_dump()))
                    inserted += 1
                    row_status = "imported"
                else:
                    was_inactive = not property_.ativo
                    values = payload.model_dump(include=set(CSV_PROPERTY_FIELDS))
                    for field, value in values.items():
                        setattr(property_, field, value)
                    if was_inactive:
                        property_.ativo = True
                        reactivated += 1
                        row_status = "reactivated"
                    else:
                        updated += 1
                        row_status = "updated"
                logs.append(_row_log(run_id, staged.line_number, row_status, payload.numero, None))

            import_repository.log_rows(session, logs)
            run = import_repository.get_run(session, run_id)
            if run is None:
                raise RuntimeError("Registro da execução de importação não encontrado")
            run.inserted_rows = inserted
            run.updated_rows = updated
            run.rejected_rows = rejected
            run.duplicate_rows = duplicates
            run.reactivated_rows = reactivated
            session.commit()
            offset += len(staged_rows)

        run = import_repository.get_run(session, run_id)
        if run is None:
            raise RuntimeError("Registro da execução de importação não encontrado")
        run.inserted_rows = inserted
        run.updated_rows = updated
        run.rejected_rows = rejected
        run.duplicate_rows = duplicates
        run.reactivated_rows = reactivated
        return _finish_run(session, run, "completed")
    except Exception as error:
        session.rollback()
        run = import_repository.get_run(session, run_id)
        if run is None:
            raise
        return _finish_run(session, run, "failed", f"{type(error).__name__}: {error}")
