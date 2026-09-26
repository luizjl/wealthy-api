# Plano de API REST - Wealthy

## 1. Objetivo

Disponibilizar uma API REST versionada para cadastrar, atualizar, consultar e excluir os dados do Wealthy, persistidos em Oracle Autonomous Database (OCI). A API deve documentar seus contratos e permitir testes interativos pelo Swagger UI.

Este documento é uma proposta para validação. Não inclui implementação nem provisionamento de recursos OCI.

## 2. Stack proposta

- **Python 3.12** como versão inicial de referência; confirmar a versão suportada pelo ambiente de deploy escolhido.
- **FastAPI** para endpoints REST e geração automática de OpenAPI/Swagger UI.
- **Pydantic v2** para contratos de entrada/saída e validação de payloads.
- **SQLAlchemy 2.x** para acesso relacional e transações.
- **python-oracledb** como driver Oracle, conectado ao Autonomous Database com configuração de conexão segura e wallet/credenciais conforme o modo aprovado para OCI.
- **Alembic** para versionar e aplicar alterações de schema.
- **pytest** e **httpx** para testes unitários e de integração da API.

A aplicação deve separar rotas, serviços/regras de negócio, repositórios/acesso a dados e modelos de transporte. As rotas não devem concentrar SQL nem regras de validação de domínio.

## 3. Contrato geral da API

- Prefixo e versão: `/api/v1`.
- JSON em requisições e respostas; datas e horários da API em ISO 8601 com timezone explícito. Manter compatibilidade com os formatos legados onde necessário, convertendo-os na camada de integração.
- Swagger UI em `/docs` e especificação OpenAPI em `/openapi.json`; ReDoc pode ficar disponível em `/redoc`.
- Respostas de erro consistentes: `400` para filtros/payloads inválidos, `401/403` para autenticação/autorização, `404` para registro ausente e `409` para conflito de unicidade ou integridade.
- Paginação de coleções com `pagina` e `porPagina`, inicialmente preservando os limites das regras de imóveis: página mínima 1, tamanho entre 1 e 100. Definir o mesmo padrão para as demais listas.
- Parâmetros SQL sempre vinculados/parametrizados; não montar SQL por concatenação de entradas.
- Usar transações para operações que alterem várias tabelas, incluindo exclusão de leilão e seus arquivos.

## 4. Recursos e endpoints propostos

Todos os caminhos abaixo ficam sob `/api/v1`. O contrato final (campos, verbos de atualização e acesso público/administrativo) deve ser confirmado antes da implementação.

| Entidade | Endpoints principais | Regras e observações |
|---|---|---|
| Imóveis | `GET /imoveis`, `GET /imoveis/{numero}`, `POST /imoveis`, `PUT/PATCH /imoveis/{numero}` | Busca com paginação, UF multi-seleção, cidade, cidades excluídas, bairro, modalidade, financiamento e faixa de preço. Validar UFs e financiamento. `linkMatricula`, quando informado, exige protocolo HTTP, sem restrição de host. Consultas incluem imóveis ativos e inativos; o frontend controla a exibição e apresenta inativos com aspecto desativado. Não permitir exclusão física: a ação explícita "Inativar" altera `ativo` para `false`. Escrita/importação deve ser autorizada; a origem principal é o CSV da Caixa. |
| Pessoas | `GET/POST /pessoas`, `GET/PUT/PATCH/DELETE /pessoas/{id}` | Exigir nome, tipo de documento e número; tipo `CPF` ou `CNPJ`; `numero` único; contatos opcional. Restringir exclusão quando houver referências por leilões ou processos. |
| Leilões | `GET/POST /leiloes`, `GET/PUT/PATCH/DELETE /leiloes/{id}` | Validar tipo, campos obrigatórios, UF, links HTTP(S) e até seis datas. Proprietário deve ser pessoa CPF e órgão de origem pessoa CNPJ. Exclusão remove arquivos vinculados em cascata. |
| Arquivos | `GET/POST /leiloes/{leilaoId}/arquivos`, `GET/PUT/PATCH/DELETE /arquivos/{id}` | Exigir nome, link HTTP(S) e leilão existente. Exclusão do leilão deve apagar seus arquivos em cascata. |
| Processos | `GET/POST /processos`, `GET/PUT/PATCH/DELETE /processos/{id}` | Exigir pessoa vinculada, número e assunto; pessoa deve existir. Resumo e observação opcionais; valor default `0.0`. |
| Favoritos | `GET /me/favoritos`, `PUT/DELETE /me/favoritos/{numeroImovel}` | Chave composta por identidade do usuário e número do imóvel; incluir/desincluir deve ser idempotente. `favoritadoEm` é preenchido pelo servidor ao criar o favorito. Preservar snapshot do imóvel para exibição offline. A identidade deve vir da autenticação, não de um `usuarioId` arbitrário no corpo. |
| Vitrines | `GET/POST /vitrines`, `GET/PUT/PATCH/DELETE /vitrines/{id}` | Exigir nome e URL HTTP(S); descrição opcional. `criadoEm` é preservado em edição e `atualizadoEm` atualizado pelo servidor. |

### Importação de imóveis

Prever uma operação administrativa de importação em lote executada manualmente (não agendada), devido ao sistema antibot do site da Caixa. Ela deve ler `Lista_imoveis_geral.csv` com encoding Windows-1252 e delimitador `;`. A importação deve validar colunas e UFs, converter tipos, registrar linhas inválidas e usar upsert pela chave `numero`.

## Estratégia em 4 camadas - Importação

Tabela de staging — carrega o CSV cru primeiro, sem validar nada. Se o processo falhar, você nunca perde o dado original.
Tabela de log de execução — registra cada "run" da importação (início, fim, status, contadores, incluindo imóveis reativados).
Log linha a linha — para cada registro, guarda se foi importado, rejeitado, duplicado ou reativado, com o motivo do erro quando aplicável.
Processamento em lote (batch) — insere em blocos (ex.: 500 linhas) com commit por lote, para que um erro no meio não force recomeçar do zero e você saiba exatamente até onde chegou.
O fluxo fica assim: CSV → staging → validação/transformação → tabela final, com todo erro capturado e registrado no caminho.


Na criação/importação inicial, campos que não existem no CSV começam vazios ou nulos: `linkMatricula`, `dataDenda` e `valorVenda`; `vendido` começa `false` e `ativo`, `true`. Os campos do CSV podem ser nulos, exceto `numero`, obrigatório como chave natural. Nas reimportações, campos ausentes no CSV, incluindo `linkMatricula` e dados de venda, não sobrescrevem os valores já existentes. Se um imóvel inativo reaparecer no CSV, poderá ser reativado; a execução deve destacar essas reativações nos resultados/logs. Imóveis não podem ser excluídos fisicamente; a inativação é lógica e feita pela ação explícita "Inativar".

## 5. Persistência e modelo Oracle

- Criar tabelas relacionais correspondentes às sete entidades e mapear explicitamente os nomes de colunas, tipos, nulabilidade, valores default e restrições.
- Usar chave natural `imoveis.numero`; IDs gerados para pessoas, leilões, arquivos, processos e vitrines; chave composta `(usuario_id, numero_imovel)` para favoritos.
- Criar unicidade para `pessoas.numero` e índices para FKs e filtros frequentes de imóveis. Confirmar estratégia de índices após conhecer volume e consultas reais.
- Definir FKs: leilões para pessoas, processos para pessoas, arquivos para leilões e favoritos para imóveis, com política de exclusão explícita. `arquivos -> leiloes` deve ter cascade conforme as regras.
- Mapear `imovelJson` como JSON/JSON armazenado em CLOB, conforme compatibilidade e versão/configuração do Oracle Autonomous DB.
- Usar migrations Alembic em todos os ambientes; não reproduzir o `fallbackToDestructiveMigration` do Room, pois não é apropriado para banco central com dados persistentes.
- Guardar credenciais e material de conexão OCI em mecanismo de segredos, nunca no repositório. Separar configurações de desenvolvimento, teste e produção.

## 6. Segurança e operação

- Exigir autenticação em todos os endpoints privados usando Firebase Authentication com login Google; a API deve validar o Firebase ID token. Novos usuários devem ser autorizados manualmente, por lista de contas permitidas; operações de importação e administração também devem ser restritas.
- Aplicar autorização por recurso e obter a identidade dos favoritos do principal autenticado. O `usuarioId` hoje gerado no Android não deve, por si só, ser tratado como identidade confiável no servidor.
- Exigir HTTPS, limitar tamanho de payload e de importação, configurar CORS apenas para origens necessárias e não expor detalhes internos de exceções.
- Registrar logs estruturados sem tokens, credenciais ou dados pessoais desnecessários; incluir métricas, health check e alertas para falhas de conexão, latência e erros.
- Publicar a API em ambiente OCI escolhido (por exemplo, container em serviço gerenciado), com rede privada para o Autonomous DB quando aplicável, pool de conexões dimensionado e backups/retention configurados no banco.

## 7. Fases propostas

1. **Validar contrato e decisões restantes**: revisar pendências de deploy e fechar o contrato OpenAPI.
2. **Definir schema Oracle**: tabelas, constraints, índices, convenções de nomes e migrations iniciais.
3. **Construir fundação da API**: configuração OCI, sessão/transações, tratamento de erros, autenticação, health check e OpenAPI.
4. **Implementar entidades relacionais**: pessoas, leilões, arquivos, processos e vitrines, incluindo validações e integridade.
5. **Implementar imóveis e importação CSV**: filtros, paginação, upsert e política de preservação dos campos editáveis no app.
6. **Implementar favoritos**: chave composta, identidade autenticada e comportamento do snapshot.
7. **Testar e publicar**: testes unitários, integração com Oracle de teste, testes de contrato OpenAPI, migração e roteiro de deploy/observabilidade.

## 8. Critérios de aceite propostos

- Os sete recursos possuem operações de consulta e persistência documentadas no Swagger.
- Validações e restrições descritas nas regras de negócio são cobertas por testes.
- Consultas de imóveis suportam os filtros definidos, paginação e limites esperados.
- Integridade referencial e cascata de arquivos são verificadas em Oracle de teste.
- Importação CSV lida corretamente com Windows-1252 e `;`, e informa erros por linha sem corromper registros válidos.
- Migrations podem ser aplicadas em banco vazio e em atualização sem apagar dados existentes.
- Segredos não ficam no código e os endpoints de escrita estão protegidos conforme os perfis acordados.

## 9. Decisões consolidadas e pendências

1. **Autenticação e acesso**: API privada, consumida inicialmente pelo app em múltiplos dispositivos. Todos os endpoints exigem autenticação via Firebase Authentication com login Google; novos usuários serão autorizados manualmente. Favoritos são associados à conta autenticada.

2. **Inativação de imóveis**: a ação "Inativar" altera `ativo` para `false`; não há exclusão física. As consultas retornam ativos e inativos, e o frontend controla a exibição. Imóveis inativos que reapareçam na importação podem ser reativados, com destaque nos resultados/logs.
   
3. **Importação/upsert**: execução manual, sem agendamento, devido ao sistema antibot do site da Caixa. Na criação/importação inicial, `linkMatricula`, `dataDenda` e `valorVenda` começam nulos; `vendido` começa `false` e `ativo`, `true`. Campos ausentes no CSV preservam valores existentes em reimportações; imóvel inativo que reaparecer pode ser reativado, com destaque no relatório.
   
4. **Compatibilidade**: não é necessário manter os nomes ou formatos atuais do Android; será definido contrato JSON novo.

5. **Oracle/OCI**: conta, Autonomous Database e wallet já existem; volume esperado é baixo e o acesso será inicialmente apenas do proprietário. **Pendente:** escolher/configurar o serviço de deploy e os ambientes de execução.

