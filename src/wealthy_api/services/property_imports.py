import csv
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
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
HEADER_ALIASES = {
    "n do imovel": "numero",
    "no do imovel": "numero",
    "numero do imovel": "numero",
    "valor de avaliacao": "valoravaliacao",
    "modalidade de venda": "modalidade",
    "link de acesso": "link",
}


def _now_milliseconds() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lstrip("\ufeffï»¿"))
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def _map_headers(columns: list[str]) -> tuple[dict[str, str], set[str]]:
    mapped = {}
    duplicates = set()
    for column in columns:
        normalized = _normalize_header(column)
        canonical = HEADER_ALIASES.get(normalized, normalized)
        if canonical not in CSV_FIELDS:
            continue
        if canonical in mapped:
            duplicates.add(canonical)
        else:
            mapped[canonical] = column
    return mapped, duplicates


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


def get_import_run(session: Session, run_id: int) -> PropertyImportRun | None:
    return import_repository.get_run(session, run_id)


def get_import_rows(
    session: Session,
    run_id: int,
    pagina: int,
    por_pagina: int,
    row_status: str | None = None,
):
    if import_repository.get_run(session, run_id) is None:
        return None
    rows, total = import_repository.list_run_rows(
        session,
        run_id,
        (pagina - 1) * por_pagina,
        por_pagina,
        row_status,
    )
    return rows, total


def _process_staged_rows(
    session: Session,
    run_id: int,
    batch_size: int,
    headers: dict[str, str],
    *,
    resuming: bool = False,
) -> PropertyImportRun:
    counts = import_repository.get_run_row_counts(session, run_id) if resuming else {}
    inserted = counts.get("imported", 0)
    updated = counts.get("updated", 0)
    rejected = counts.get("rejected", 0)
    duplicates = counts.get("duplicate", 0)
    reactivated = counts.get("reactivated", 0)
    seen_numbers: set[str] = set()
    if resuming:
        for staged in import_repository.get_logged_staged_rows(session, run_id):
            row = json.loads(staged.raw_json)
            if "__column_count__" in row:
                continue
            try:
                payload = _property_payload(row, headers)
            except (ValidationError, ValueError):
                continue
            seen_numbers.add(payload.numero)

    while True:
        staged_rows = import_repository.get_unprocessed_staged_batch(session, run_id, batch_size)
        if not staged_rows:
            break

        candidate_numbers = set()
        for staged in staged_rows:
            row = json.loads(staged.raw_json)
            raw_number = row.get(headers["numero"])
            if raw_number and "__column_count__" not in row:
                candidate_numbers.add(raw_number.strip())
        properties_by_number = property_repository.find_properties(session, candidate_numbers)

        logs = []
        prepared_rows = []
        for staged in staged_rows:
            row = json.loads(staged.raw_json)
            raw_number = row.get(headers["numero"])
            numero = raw_number.strip() if raw_number else None
            if "__column_count__" in row:
                rejected += 1
                logs.append(
                    _row_log(
                        run_id,
                        staged.line_number,
                        "rejected",
                        numero,
                        "Número de colunas da linha difere do cabeçalho",
                    )
                )
                continue
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
                logs.append(_row_log(run_id, staged.line_number, "rejected", numero, str(error)))
                continue

            seen_numbers.add(payload.numero)
            property_ = properties_by_number.get(payload.numero)
            was_inactive = property_ is not None and not property_.ativo
            prepared_rows.append((staged, payload, property_, was_inactive))

        try:
            with session.begin_nested():
                for _, payload, property_, was_inactive in prepared_rows:
                    if property_ is None:
                        session.add(Property(**payload.model_dump()))
                        continue
                    values = payload.model_dump(include=set(CSV_PROPERTY_FIELDS))
                    for field, value in values.items():
                        setattr(property_, field, value)
                    if was_inactive:
                        property_.ativo = True
                session.flush()
        except IntegrityError:
            session.expire_all()
            for staged, payload, _, _ in prepared_rows:
                property_ = property_repository.find_property(session, payload.numero)
                was_inactive = property_ is not None and not property_.ativo
                try:
                    with session.begin_nested():
                        if property_ is None:
                            session.add(Property(**payload.model_dump()))
                            row_status = "imported"
                        else:
                            values = payload.model_dump(include=set(CSV_PROPERTY_FIELDS))
                            for field, value in values.items():
                                setattr(property_, field, value)
                            if was_inactive:
                                property_.ativo = True
                                row_status = "reactivated"
                            else:
                                row_status = "updated"
                        session.flush()
                except IntegrityError as error:
                    rejected += 1
                    oracle_code = getattr(error.orig, "code", None)
                    detail = (
                        f"Falha de integridade ao persistir a linha ({oracle_code})"
                        if oracle_code
                        else "Falha de integridade ao persistir a linha"
                    )
                    logs.append(
                        _row_log(run_id, staged.line_number, "rejected", payload.numero, detail)
                    )
                    continue

                if row_status == "imported":
                    inserted += 1
                elif row_status == "reactivated":
                    reactivated += 1
                else:
                    updated += 1
                logs.append(_row_log(run_id, staged.line_number, row_status, payload.numero, None))
        else:
            for staged, payload, property_, was_inactive in prepared_rows:
                if property_ is None:
                    row_status = "imported"
                    inserted += 1
                elif was_inactive:
                    row_status = "reactivated"
                    reactivated += 1
                else:
                    row_status = "updated"
                    updated += 1
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

    run = import_repository.get_run(session, run_id)
    if run is None:
        raise RuntimeError("Registro da execução de importação não encontrado")
    run.inserted_rows = inserted
    run.updated_rows = updated
    run.rejected_rows = rejected
    run.duplicate_rows = duplicates
    run.reactivated_rows = reactivated
    return _finish_run(session, run, "completed")


def import_properties_csv(
    session: Session,
    file_path: str | Path,
    *,
    batch_size: int = 500,
    source_label: str | None = None,
) -> PropertyImportRun:
    if batch_size < 1:
        raise ValueError("batch_size deve ser maior que zero")
    source_path = Path(file_path).expanduser()
    run = import_repository.create_run(
        session, source_label or str(source_path), _now_milliseconds()
    )
    run_id = run.id

    try:
        staged_count = 0
        with source_path.open("r", encoding="cp1252", newline="") as source:
            reader = csv.reader(source, delimiter=";")
            headers = {}
            header_fields = None
            best_headers = {}
            for fields in reader:
                if not fields or all(not field.strip() for field in fields):
                    continue
                candidate, duplicate_headers = _map_headers(fields)
                if len(candidate) > len(best_headers):
                    best_headers = candidate
                if not duplicate_headers and set(CSV_FIELDS).issubset(candidate):
                    headers = candidate
                    header_fields = fields
                    break

            if header_fields is None:
                missing_headers = sorted(set(CSV_FIELDS) - set(best_headers))
                raise ValueError(
                    "Cabeçalho CSV não encontrado; colunas ausentes: " + ", ".join(missing_headers)
                )

            batch = []
            for fields in reader:
                row_number = reader.line_num
                if not fields or all(not field.strip() for field in fields):
                    continue
                row = {
                    header: fields[index] if index < len(fields) else ""
                    for index, header in enumerate(header_fields)
                }
                if len(fields) != len(header_fields):
                    row["__column_count__"] = len(fields)
                    row["__extra_fields__"] = fields[len(header_fields) :]
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

        return _process_staged_rows(session, run_id, batch_size, headers)
    except Exception as error:
        session.rollback()
        run = import_repository.get_run(session, run_id)
        if run is None:
            raise
        return _finish_run(session, run, "failed", f"{type(error).__name__}: falha na importação")


def resume_import_run(
    session: Session,
    run_id: int,
    *,
    batch_size: int = 500,
) -> PropertyImportRun:
    if batch_size < 1:
        raise ValueError("batch_size deve ser maior que zero")

    run = import_repository.get_run(session, run_id)
    if run is None:
        raise ValueError(f"Execução de importação {run_id} não encontrada")
    if run.status != "failed":
        raise ValueError("Somente execuções com status failed podem ser retomadas")
    staged_count = import_repository.count_staged_rows(session, run_id)
    logged_count = import_repository.count_run_rows(session, run_id)
    if staged_count == 0 or staged_count != run.total_rows or logged_count > staged_count:
        raise ValueError("O staging está vazio ou incompleto; não é possível retomar")

    first_staged = import_repository.get_staged_batch(session, run_id, 0, 1)
    row = json.loads(first_staged[0].raw_json)
    headers, duplicate_headers = _map_headers(list(row))
    if duplicate_headers or not set(CSV_FIELDS).issubset(headers):
        raise ValueError("Não foi possível identificar todas as colunas no staging")
    if not import_repository.claim_failed_run(session, run_id):
        raise ValueError("A execução já foi retomada por outro processo")

    try:
        return _process_staged_rows(session, run_id, batch_size, headers, resuming=True)
    except Exception as error:
        session.rollback()
        run = import_repository.get_run(session, run_id)
        if run is None:
            raise
        return _finish_run(session, run, "failed", f"{type(error).__name__}: falha na retomada")
