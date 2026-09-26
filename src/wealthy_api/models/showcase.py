from sqlalchemy import Integer, Sequence, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from wealthy_api.models.base import Base


class Showcase(Base):
    __tablename__ = "vitrines"

    id: Mapped[int] = mapped_column(Integer, Sequence("vitrines_id_seq"), primary_key=True)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    criado_em: Mapped[int] = mapped_column(Integer, nullable=False)
    atualizado_em: Mapped[int] = mapped_column(Integer, nullable=False)
