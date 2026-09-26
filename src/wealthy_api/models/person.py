from enum import StrEnum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from wealthy_api.models.base import Base


class TipoDocumento(StrEnum):
    CPF = "CPF"
    CNPJ = "CNPJ"


class Person(Base):
    __tablename__ = "pessoas"
    __table_args__ = (UniqueConstraint("numero", name="uq_pessoas_numero"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        SqlEnum(TipoDocumento, native_enum=False, length=4), nullable=False
    )
    numero: Mapped[str] = mapped_column(String(32), nullable=False)
    contatos: Mapped[str | None] = mapped_column(String(2000), nullable=True)
