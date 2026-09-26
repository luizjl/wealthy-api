from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wealthy_api.models.person import TipoDocumento


class PersonCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    tipo_documento: TipoDocumento
    numero: str = Field(min_length=1, max_length=32)
    contatos: str | None = Field(default=None, max_length=2000)

    @field_validator("nome", "numero")
    @classmethod
    def strip_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value


class PersonUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    tipo_documento: TipoDocumento | None = None
    numero: str | None = Field(default=None, min_length=1, max_length=32)
    contatos: str | None = Field(default=None, max_length=2000)

    @field_validator("nome", "numero")
    @classmethod
    def strip_nonblank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "PersonUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        return self


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo_documento: TipoDocumento
    numero: str
    contatos: str | None


class PersonPage(BaseModel):
    items: list[PersonRead]
    pagina: int
    porPagina: int
    total: int
