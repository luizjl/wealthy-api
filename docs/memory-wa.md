# Wealthy API - Handoff de Execucao

Atualizado em 2026-09-27.

## Estado atual

- Projeto Python 3.14, FastAPI, SQLAlchemy, Oracle `python-oracledb` Thin e Alembic.
- API local configurada para Oracle Autonomous Database via wallet e TNS.
- Revisao Oracle aplicada: `12ffb387e11a` (`head`); `alembic check` sem drift.
- A quota no tablespace `DATA` foi ajustada pelo usuario depois de um `ORA-01950` na primeira migration.
- A wallet está em `src/conf/oracle_wallet`; o caminho no `.env.oracle` foi corrigido. `src/conf/` está no `.gitignore`.
- A conexao Oracle foi testada com `SELECT 1 FROM DUAL`. Smoke tests de inserts e FKs executaram em transacoes revertidas; nao deixaram dados de teste.
- Os migrations criam pessoas, leiloes, arquivos, processos, vitrines, imoveis, favoritos e tabelas de staging/log de importacao.
- O autogenerate foi configurado para ignorar `DBTOOLS$EXECUTION_HISTORY`; essa tabela foi preservada.
- Oracle e o unico backend: nao ha fallback, URL ou dependencias SQLite no runtime, testes ou migrations. Configuracoes locais antigas e bancos `.db` temporarios foram removidos.

## Recursos implementados

- Autenticacao Firebase Bearer com allowlist manual por UID.
- CRUD de pessoas, leiloes, arquivos, processos e vitrines.
- Imoveis: cadastro, consulta filtrada/paginada e acao explicita de inativacao; nao existe exclusao fisica.
- Favoritos idempotentes por UID autenticado, com snapshot e estado atual do imovel.
- Importador manual de CSV Caixa: Windows-1252, delimitador `;`, staging bruto, validacao por linha, processamento em batches, upsert, preservacao de `linkMatricula` e dados de venda ausentes do CSV, logs/contadores e destaque de reativacoes.
- CLI instalado: `wealthy-import-properties`; aceita CSV novo ou `--resume-run-id` para continuar staging de execução falha, processando apenas linhas sem log.
- Swagger UI: `/docs`; health check: `/health`.

## Configuracao Firebase

- `.env` recebeu `WEALTHY_FIREBASE_PROJECT_ID`, `WEALTHY_FIREBASE_ALLOWED_UIDS` e `WEALTHY_FIREBASE_CREDENTIALS_FILE`.
- O JSON de service account existe localmente sob `src/conf/`, ignorado pelo Git. Nunca copiar ou imprimir seu conteudo.
- O Project ID no `.env` foi alinhado ao `project_id` do JSON.
- `security.py` suporta arquivo local via `WEALTHY_FIREBASE_CREDENTIALS_FILE` e Google ADC via `GOOGLE_APPLICATION_CREDENTIALS`.
- Sem credenciais Firebase Admin, a API responde `503` (nao `500`); token ausente/invalido responde `401`, UID fora da allowlist responde `403`.

## Ultima verificacao

- Testes do importador: 6 passaram; Ruff limpo apos adicionar retomada de staging e gravacao em lote.
- Carga real Caixa run `121` concluida: 14.484 staged, 14.484 logs `imported`, 14.484 inseridos, zero rejeitados/duplicados/atualizados/reativados. Quota DATA efetiva 4 GiB; 171.704.320 bytes alocados na verificacao final.
- Health respondeu `200`; rota sem token responde `401`. Antes da credencial Admin ser configurada, token de teste respondeu `503` (nao `500`).
- O JSON de service account em `src/conf/` foi validado estruturalmente sem ler/imprimir a chave; o Project ID foi alinhado ao JSON e `WEALTHY_FIREBASE_CREDENTIALS_FILE` foi configurado em `.env`.
- A allowlist Firebase foi preenchida. Ainda nao foi testado um Firebase ID token real de usuario permitido.
- O Uvicorn foi encerrado para recarregar `.env`; a ultima tentativa de reinicio foi cancelada. Verificar/iniciar o servidor antes do proximo teste HTTP.

## Proximos passos

1. Iniciar Uvicorn em `127.0.0.1:8000` para carregar o `.env` atual.
2. Testar `/api/v1/imoveis` no Swagger com Firebase ID token real de UID permitido. Nao compartilhar o token.
3. Acompanhar o run `121` da carga real retomada e confirmar contadores/logs finais no Oracle antes de declarar conclusao.
4. Fazer uma revisao final de seguranca/contratos; deploy OCI continua adiado.

## Segredos e dados

Nunca versionar `.env`, `.env.oracle`, a wallet ou o JSON de service account. Nao incluir valores de senhas, tokens, UIDs privados ou chaves privadas neste arquivo.

## Registro cronologico do chat

Este registro cobre as decisoes e a execucao tecnica substantiva desta conversa; nao reproduz literalmente mensagens de ferramentas nem conteudo secreto.

1. Revisado `docs/plano-api-rest.md` junto com as regras de negocio e modelo. Decisoes confirmadas: API privada, app inicialmente unico em varios dispositivos, favoritos por conta; login Google via Firebase Authentication; novos usuarios autorizados manualmente; contrato JSON novo; importacao do CSV manual por causa do antibot da Caixa; reativacao de imoveis reaparecidos deve ser destacada; imoveis apenas inativados, nunca excluidos fisicamente; consultas incluem ativos e inativos para o frontend decidir exibicao.
2. Regras de upsert confirmadas: valores de `linkMatricula`, `dataDenda` e `valorVenda` comecam nulos; `vendido=false` e `ativo=true`; campos ausentes do CSV preservam valores existentes. `numero` e obrigatorio, os demais campos vindos do CSV podem ser nulos. `favoritadoEm` e definido pelo servidor. `linkMatricula` aceita HTTP sem restricao de host. Exclusao de pessoas referenciadas deve ser restrita. Deploy OCI fica para depois.
3. Criada a fundacao FastAPI/SQLAlchemy/Firebase/Alembic, health check e CRUD de pessoas; inicialmente havia backend SQLite local.
4. Adicionado suporte Oracle Thin, TNS alias e wallet em `.env.oracle` (ignorado pelo Git). A wallet real fica em `src/conf/oracle_wallet`; a conexao foi validada com `SELECT 1 FROM DUAL`.
5. Primeira migration Oracle encontrou `ORA-01950` por quota no tablespace `DATA`. Depois da quota ser concedida, a tabela `pessoas` parcial foi inspecionada, estava vazia e consistente, e a revisao foi registrada. Nenhum dado de usuario foi removido.
6. Implementados CRUD de leiloes e arquivos, validacao CPF/CNPJ, URLs/UF/datas, cascade de arquivos e sequences Oracle. O autogenerate detectou `DBTOOLS$EXECUTION_HISTORY`; a migration foi corrigida para preservar a tabela. Revision `f6cc3e2d182a` aplicada e smoke test com rollback passou.
7. Implementados processos e vitrines. Smoke test Oracle revelou que strings vazias sao gravadas como NULL; os campos opcionais foram tornados nullable e normalizados para vazio na API. Revisions `ee8929b84670` e `d2a3d8b067a6` aplicadas; `alembic check` sem drift.
8. Implementados imoveis, filtros/paginacao, inativacao, favoritos idempotentes por UID e snapshot. Removida exclusao fisica de imoveis da API. FK de favoritos recebe indice. Revision `4c9726cb96d7` aplicada; smoke test com rollback passou.
9. Implementado importador manual da Caixa: Windows-1252, `;`, staging cru, validacao linha a linha, batches, logs, upsert preservando campos fora do CSV e destaque de reativacao. Cada persistencia por linha usa savepoint: erro de integridade vira rejeicao daquela linha e o batch continua. Adicionado comando `wealthy-import-properties` e endpoint administrativo multipart. Parser ignora linhas vazias/metadados e aceita aliases Caixa como `N° do imóvel`, `Valor de avaliação`, `Modalidade de venda` e `Link de acesso`. O CSV `C:\Users\luiz.jose\Downloads\Lista_imoveis_geral (1).csv` teve cabecalho encontrado na linha 3 e todas as 12 colunas mapeadas. Um smoke test de uma linha real foi revertido. A carga completa de `C:\Projetos\imoveis\public\Lista_imoveis_geral.csv` iniciou, mas falhou com `ORA-01536` durante processamento/staging. O run `121` conservou 14.484 linhas staged. Revision `12ffb387e11a` aplicada.
10. Swagger inicialmente servia processo antigo sem as rotas de imoveis. Confirmado que o codigo e OpenAPI atual continham as rotas; Uvicorn foi reiniciado com reload somente de `src`. OpenAPI passou a listar os endpoints.
11. Investigado erro `500` autenticado: faltava `WEALTHY_FIREBASE_PROJECT_ID`. O handler foi ajustado para `503` em configuracao ausente; sem token continua `401`.
12. Configurado service account local em `src/conf/`, diretorio ignorado. O Project ID estava como numero e foi corrigido para o identificador textual contido no JSON. O JSON foi validado sem revelar sua chave. A variavel `WEALTHY_FIREBASE_CREDENTIALS_FILE` aponta para esse arquivo local.
13. A ultima tentativa de reiniciar Uvicorn depois dessa configuracao foi cancelada. Proxima acao: iniciar servidor, testar `/api/v1/imoveis` com token Firebase real de UID permitido e confirmar a resposta de negocio. O deploy e a importacao do CSV real ainda nao foram realizados.
14. A pedido do usuario, SQLite foi removido completamente do codigo, configuracao, testes, migrations e documentacao ativa. Engine e migrations usam apenas Oracle; testes de integracao conectam ao ADB e revertem as escritas em transacao. Nenhum banco `.db` local foi mantido.
15. O importador passou a capturar `IntegrityError` por linha via savepoint, registrar a linha como rejeitada e seguir com as outras linhas do batch. Teste simulado confirmou a continuidade.
16. Usuario aumentou a quota de `DB_USER_WEALTHY` para 4 GiB; API confirmou a quota efetiva. Implementado `resume_import_run` e CLI `--resume-run-id`, restrito a runs `failed` com staging completo; pula linhas com log e recompõe contadores a partir dos logs existentes. Consultas de imóveis para upsert são feitas em lote, com um flush por batch e fallback por linha se houver erro de integridade. Testes de importacao passaram (6) e Ruff passou. O run `121` foi retomado sem recarregar o CSV nem criar outro run e concluiu: 14.484 linhas importadas, nenhum erro; Oracle confirmou 14.484 staging, 14.484 logs `imported` e 14.484 imóveis.
