from sqlalchemy import Float, ForeignKey, Integer, Sequence, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wealthy_api.models.base import Base
from wealthy_api.models.person import Person


class LegalProcess(Base):
    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(Integer, Sequence("processos_id_seq"), primary_key=True)
    id_pessoa: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), nullable=False)
    numero: Mapped[str] = mapped_column(String(100), nullable=False)
    assunto: Mapped[str] = mapped_column(String(500), nullable=False)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    valor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    obs: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    pessoa: Mapped[Person] = relationship()
