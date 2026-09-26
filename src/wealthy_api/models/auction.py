from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, Sequence, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wealthy_api.models.base import Base
from wealthy_api.models.person import Person


class TipoLeilao(StrEnum):
    CASA = "CASA"
    APARTAMENTO = "APARTAMENTO"
    TERRENO = "TERRENO"
    VEICULO = "VEICULO"
    MOTO = "MOTO"


class Auction(Base):
    __tablename__ = "leiloes"

    id: Mapped[int] = mapped_column(Integer, Sequence("leiloes_id_seq"), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tipo: Mapped[TipoLeilao] = mapped_column(
        SqlEnum(TipoLeilao, native_enum=False, length=20), nullable=False
    )
    url_matricula: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    id_proprietario: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    cidade: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    id_orgao_origem: Mapped[int] = mapped_column(ForeignKey("pessoas.id"), nullable=False)
    datas: Mapped[str | None] = mapped_column(String(65), nullable=True, default=None)
    criado_em: Mapped[int] = mapped_column(Integer, nullable=False)

    proprietario: Mapped[Person] = relationship(foreign_keys=[id_proprietario])
    orgao_origem: Mapped[Person] = relationship(foreign_keys=[id_orgao_origem])
    arquivos: Mapped[list["AuctionFile"]] = relationship(
        back_populates="leilao", cascade="all, delete-orphan", passive_deletes=True
    )


class AuctionFile(Base):
    __tablename__ = "arquivos"

    id: Mapped[int] = mapped_column(Integer, Sequence("arquivos_id_seq"), primary_key=True)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    leilao_id: Mapped[int] = mapped_column(
        ForeignKey("leiloes.id", ondelete="CASCADE"), nullable=False
    )

    leilao: Mapped[Auction] = relationship(back_populates="arquivos")
