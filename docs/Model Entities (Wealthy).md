# Model Entities (Wealthy)


### (tabela `imoveis`)
- numero: String — chave primária natural ("Nº do imóvel")
- uf: String
- cidade: String
- bairro: String
- endereco: String
- preco: Double
- valorAvaliacao: Double (`valor_avaliacao`)
- desconto: Double
- aceitaFinanciamento: String (`aceita_financiamento`)
- descricao: String
- modalidade: String
- vendido: Boolean, default false
- dataDenda: Date, default null
- valorVenda: Double
- link: String
- linkMatricula: String, default null
- ativo: Booelan, default true

### (tabela `pessoas`)
- id: Long, autoGenerate
- nome: String
- tipoDocumento: TipoDocumento (`tipo_documento`) — enum `CPF | CNPJ`
- numero: String — único (`Index(unique = true)`)
- contatos: String (opcional, sem validação)

### (tabela `leiloes`)
- id: Long, autoGenerate
- titulo: String
- ativo: Boolean, default `true`
- tipo: TipoLeilao — enum `CASA | APARTAMENTO | TERRENO | VEICULO | MOTO`
- urlMatricula: String, default `""` (`url_matricula`, opcional)
- idProprietario: Long — FK -> Pessoa.id (`id_proprietario`)
- link: String
- descricao: String
- cidade: String
- estado: String — UF, persistida em maiúsculas
- idOrgaoOrigem: Long — FK -> Pessoa.id (`id_orgao_origem`)
- datas: String — datas serializadas separadas por `|` (`dd/MM/yyyy`), 0 a 6 itens (opcional)
- criadoEm: Long, default `System.currentTimeMillis()` (`criado_em`)

### (tabela `arquivos`)
- id: Long, autoGenerate
- nome: String
- link: String
- leilaoId: Long — FK -> Leilao.id, `ON DELETE CASCADE`

### (tabela `processos`)
- id: Long, autoGenerate
- idPessoa: Long — FK -> Pessoa.id, `ON DELETE RESTRICT`
- numero: String
- assunto: String
- resumo: String, default `""`
- valor: Double, default `0.0`
- obs: String, default `""`

### (tabela `favoritos`, chave composta)
- usuarioId: String
- numeroImovel: String
- imovelJson: String — snapshot serializado do ImovelEntity no momento de favoritar
- favoritadoEm: Long
- PK(usuarioId, numeroImovel)

### (tabela `vitrines`)
- id: Long, autoGenerate
- nome: String
- link: String
- descricao: String, default `""` (opcional)
- criadoEm: Long, default `System.currentTimeMillis()` (`criado_em`)
- atualizadoEm: Long, default `System.currentTimeMillis()` (`atualizado_em`)


## Enums

- `TipoDocumento`: `CPF`, `CNPJ`
- `TipoLeilao`: `CASA`, `APARTAMENTO`, `TERRENO`, `VEICULO`, `MOTO`

## Relacionamentos

- `Leilao.idProprietario -> Pessoa.id` (1 Pessoa para muitos Leiloes; no formulário, só pessoas com `tipoDocumento = CPF` aparecem como opção)
- `Leilao.idOrgaoOrigem -> Pessoa.id` (1 Pessoa para muitos Leiloes; só pessoas com `tipoDocumento = CNPJ` aparecem como opção)
- `Arquivo.leilaoId -> Leilao.id` (1 Leilao para muitos Arquivos; exclusão de leilão exclui arquivos em cascata)
- `Processo.idPessoa -> Pessoa.id` (1 Pessoa para muitos Processos)
- `Favorito` é escopado por `usuarioId` (gerado/persistido em `SharedPreferences` via `UsuarioIdProvider`) e referencia um `Imovel` pelo `numero`
- `Vitrine` não tem relacionamento com outras entidades
