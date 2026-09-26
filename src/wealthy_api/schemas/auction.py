from datetime import date, datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from wealthy_api.models.auction import TipoLeilao

UF_CODES = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


class AuctionCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    tipo: TipoLeilao
    id_proprietario: int = Field(gt=0)
    link: AnyHttpUrl
    descricao: str = Field(min_length=1)
    cidade: str = Field(min_length=1, max_length=200)
    estado: str = Field(min_length=2, max_length=2)
    id_orgao_origem: int = Field(gt=0)
    url_matricula: AnyHttpUrl | None = None
    datas: list[date] = Field(default_factory=list, max_length=6)
    ativo: bool = True

    @field_validator("titulo", "descricao", "cidade")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value

    @field_validator("estado")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in UF_CODES:
            raise ValueError("Informe uma UF brasileira válida")
        return value


class AuctionUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=300)
    tipo: TipoLeilao | None = None
    id_proprietario: int | None = Field(default=None, gt=0)
    link: AnyHttpUrl | None = None
    descricao: str | None = Field(default=None, min_length=1)
    cidade: str | None = Field(default=None, min_length=1, max_length=200)
    estado: str | None = Field(default=None, min_length=2, max_length=2)
    id_orgao_origem: int | None = Field(default=None, gt=0)
    url_matricula: AnyHttpUrl | None = None
    datas: list[date] | None = Field(default=None, max_length=6)
    ativo: bool | None = None

    @field_validator("titulo", "descricao", "cidade")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio")
        return value

    @field_validator("estado")
    @classmethod
    def normalize_optional_state(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return AuctionCreate.normalize_state(value)

    @model_validator(mode="after")
    def validate_patch_fields(self) -> "AuctionUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        nullable_fields = {"url_matricula", "datas"}
        for field in self.model_fields_set - nullable_fields:
            if getattr(self, field) is None:
                raise ValueError(f"O campo {field} não aceita null")
        return self


class AuctionRead(BaseModel):
    id: int
    titulo: str
    ativo: bool
    tipo: TipoLeilao
    url_matricula: str | None
    id_proprietario: int
    link: str
    descricao: str
    cidade: str
    estado: str
    id_orgao_origem: int
    datas: list[date]
    criado_em: datetime


class AuctionPage(BaseModel):
    items: list[AuctionRead]
    pagina: int
    porPagina: int
    total: int


class AuctionFileCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=300)
    link: AnyHttpUrl

    @field_validator("nome")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio")
        return value


class AuctionFileUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=300)
    link: AnyHttpUrl | None = None

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
    def require_at_least_one_field(self) -> "AuctionFileUpdate":
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Informe campos válidos para atualizar")
        return self


class AuctionFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    link: str
    leilao_id: int
