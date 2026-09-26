from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wealthy_api.models.base import Base


class Property(Base):
    __tablename__ = "imoveis"

    numero: Mapped[str] = mapped_column(String(64), primary_key=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(300), nullable=True)
    endereco: Mapped[str | None] = mapped_column(Text, nullable=True)
    preco: Mapped[float | None] = mapped_column(Float, nullable=True)
    valor_avaliacao: Mapped[float | None] = mapped_column(Float, nullable=True)
    desconto: Mapped[float | None] = mapped_column(Float, nullable=True)
    aceita_financiamento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    modalidade: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vendido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_denda: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_venda: Mapped[float | None] = mapped_column(Float, nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_matricula: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    favoritos: Mapped[list["Favorite"]] = relationship(back_populates="imovel")


class Favorite(Base):
    __tablename__ = "favoritos"
    __table_args__ = (Index("ix_favoritos_numero_imovel", "numero_imovel"),)

    usuario_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    numero_imovel: Mapped[str] = mapped_column(ForeignKey("imoveis.numero"), primary_key=True)
    imovel_json: Mapped[str] = mapped_column(Text, nullable=False)
    favoritado_em: Mapped[int] = mapped_column(Integer, nullable=False)

    imovel: Mapped[Property] = relationship(back_populates="favoritos")
