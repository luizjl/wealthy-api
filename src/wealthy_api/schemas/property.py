from datetime import date, datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from wealthy_api.schemas.auction import UF_CODES


class PropertyCreate(BaseModel):
    numero: str = Field(min_length=1, max_length=64)
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    cidade: str | None = Field(default=None, max_length=200)
    bairro: str | None = Field(default=None, max_length=300)
    endereco: str | None = None
    preco: float | None = None
    valor_avaliacao: float | None = None
    desconto: float | None = None
    aceita_financiamento: str | None = Field(default=None, max_length=20)
    descricao: str | None = None
    modalidade: str | None = Field(default=None, max_length=200)
    vendido: bool = False
    data_denda: date | None = None
    valor_venda: float | None = None
    link: str | None = None
    link_matricula: AnyHttpUrl | None = None
    ativo: bool = True

    @field_validator("numero")
    @classmethod
    def strip_number(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O número do imóvel não pode ficar vazio")
        return value

    @field_validator("uf")
    @classmethod
    def normalize_uf(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().upper()
        if value not in UF_CODES:
            raise ValueError("Informe uma UF brasileira válida")
        return value

    @field_validator("aceita_financiamento")
    @classmethod
    def normalize_financing(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in {"sim", "nao", "não"}:
            raise ValueError("Financiamento deve ser sim, nao ou não")
        return "nao" if normalized == "não" else normalized

    @field_validator("link_matricula")
    @classmethod
    def require_http_matricula(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and value.scheme != "http":
            raise ValueError("Link da matrícula deve usar protocolo HTTP")
        return value


class PropertyUpdate(BaseModel):
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    cidade: str | None = Field(default=None, max_length=200)
    bairro: str | None = Field(default=None, max_length=300)
    endereco: str | None = None
    preco: float | None = None
    valor_avaliacao: float | None = None
    desconto: float | None = None
    aceita_financiamento: str | None = Field(default=None, max_length=20)
    descricao: str | None = None
    modalidade: str | None = Field(default=None, max_length=200)
    vendido: bool | None = None
    data_denda: date | None = None
    valor_venda: float | None = None
    link: str | None = None
    link_matricula: AnyHttpUrl | None = None

    @field_validator("uf")
    @classmethod
    def normalize_uf(cls, value: str | None) -> str | None:
        return PropertyCreate.normalize_uf(value)

    @field_validator("aceita_financiamento")
    @classmethod
    def normalize_financing(cls, value: str | None) -> str | None:
        return PropertyCreate.normalize_financing(value)

    @field_validator("link_matricula")
    @classmethod
    def require_http_matricula(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        return PropertyCreate.require_http_matricula(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "PropertyUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        return self


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: str
    uf: str | None
    cidade: str | None
    bairro: str | None
    endereco: str | None
    preco: float | None
    valor_avaliacao: float | None
    desconto: float | None
    aceita_financiamento: str | None
    descricao: str | None
    modalidade: str | None
    vendido: bool
    data_denda: date | None
    valor_venda: float | None
    link: str | None
    link_matricula: str | None
    ativo: bool


class PropertyPage(BaseModel):
    items: list[PropertyRead]
    pagina: int
    porPagina: int
    total: int


class FavoriteRead(BaseModel):
    numero_imovel: str
    favoritado_em: datetime
    ativo_atual: bool
    imovel: PropertyRead


class FavoritePage(BaseModel):
    items: list[FavoriteRead]
    pagina: int
    porPagina: int
    total: int
