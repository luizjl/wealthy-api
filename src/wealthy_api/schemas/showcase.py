from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


class ShowcaseCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=300)
    link: AnyHttpUrl
    descricao: str = Field(default="", max_length=10000)

    @field_validator("nome")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio")
        return value


class ShowcaseUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=300)
    link: AnyHttpUrl | None = None
    descricao: str | None = Field(default=None, max_length=10000)

    @field_validator("nome")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio")
        return value

    @model_validator(mode="after")
    def validate_patch(self) -> "ShowcaseUpdate":
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Informe campos válidos para atualizar")
        return self


class ShowcaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    link: str
    descricao: str
    criado_em: datetime
    atualizado_em: datetime


class ShowcasePage(BaseModel):
    items: list[ShowcaseRead]
    pagina: int
    porPagina: int
    total: int
