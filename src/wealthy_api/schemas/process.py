from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProcessCreate(BaseModel):
    id_pessoa: int = Field(gt=0)
    numero: str = Field(min_length=1, max_length=100)
    assunto: str = Field(min_length=1, max_length=500)
    resumo: str = Field(default="", max_length=10000)
    valor: float = 0.0
    obs: str = Field(default="", max_length=10000)

    @field_validator("numero", "assunto")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value


class ProcessUpdate(BaseModel):
    id_pessoa: int | None = Field(default=None, gt=0)
    numero: str | None = Field(default=None, min_length=1, max_length=100)
    assunto: str | None = Field(default=None, min_length=1, max_length=500)
    resumo: str | None = Field(default=None, max_length=10000)
    valor: float | None = None
    obs: str | None = Field(default=None, max_length=10000)

    @field_validator("numero", "assunto")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value

    @model_validator(mode="after")
    def validate_patch(self) -> "ProcessUpdate":
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Informe campos válidos para atualizar")
        return self


class ProcessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_pessoa: int
    numero: str
    assunto: str
    resumo: str
    valor: float
    obs: str

    @field_validator("resumo", "obs", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str:
        return value.strip() if value else ""


class ProcessPage(BaseModel):
    items: list[ProcessRead]
    pagina: int
    porPagina: int
    total: int
