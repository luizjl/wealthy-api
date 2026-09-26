# Regras de Negocio - Wealthy Android

## 1) Origem e tratamento de imoveis
- A fonte oficial dos imoveis é um CSV da Caixa, Lista_imoveis_geral.csv (encoding windows-1252, 
delimitador ";").
- O campo linkMatricula e inicializado como vazio na carga do CSV.
- Layout de colunas esperado: numero;uf;cidade;bairro;endereco;preco;valorAvaliacao;desconto;
  financiamento;descricao;modalidade;link.
- UFs validas sao restritas ao conjunto oficial brasileiro (AC..TO).

## 2) Consulta de imoveis (tela Imóveis)
- Filtro por UF e multi-selecao (checkbox em dropdown); UF invalida lanca ValidationException.
- Filtros textuais suportados: cidade, cidadesExcluir (lista separada por vírgula, cada item e
  normalizado com trim + uppercase antes de comparar), bairro, modalidade.
- Filtro de financiamento aceita apenas sim, nao ou não.
- Filtros numericos: precoMin e precoMax (campos "Preço mín." e "Preço máx.", ambos reativados na UI).
- Paginacao com regras:
  - pagina minima: 1
  - porPagina minimo: 1
  - porPagina maximo: 100
  - porPagina default: 20 (a tela usa 100 itens por pagina)
- Painel de filtros e recolhível (toggle "Filtros" com ícone expand/collapse) e usa `FlowRow` para
  quebrar linha em telas estreitas/retrato, evitando que campos fiquem inacessíveis fora da tela.

## 3) Validacao de links
- Links de detalhe/matrícula do imóvel (`salvarLinkMatricula`) só são aceitos se: protocolo HTTPS e
  host exatamente `venda-imoveis.caixa.gov.br`; link inválido lança ValidationException.
- Demais links do app (leilão, URL da matrícula do leilão, arquivo vinculado ao leilão, vitrine)
  exigem apenas protocolo http/https (`^https?://.+`), sem restrição de host.

## 4) Favoritos
- Escopo de favoritos é por `usuarioId`, gerado uma vez por `UsuarioIdProvider`: tenta recuperar de
  SharedPreferences; se não existir, gera um UUID novo; se o storage falhar, cai para "usuario-anonimo".
- Alternar favorito (`ImoveisViewModel.alternarFavorito`) insere/remove diretamente no Room; a lista de
  favoritos é observada via Flow reativo (sem necessidade de rollback manual, pois não há chamada de rede).
- Favorito guarda um snapshot JSON do imóvel no momento em que foi marcado, para exibição offline mesmo
  se o imóvel sair da base local.

## 5) Pessoas
- Tipos de documento permitidos: CPF ou CNPJ.
- Cadastro de pessoa exige nome, tipoDocumento e numero preenchidos; contatos é opcional.
- numero é único em banco (índice único); duplicidade lança ValidationException.
- No formulário de nova pessoa, o "Tipo de documento" já vem pré-selecionado como CPF.
- Formulário tem botões "Salvar pessoa" e "Cancelar" (volta para a lista sem salvar).

## 6) Leilões
- Tipos permitidos: CASA, APARTAMENTO, TERRENO, VEICULO, MOTO.
- Campos obrigatórios para criar/atualizar: titulo, tipo, idProprietario, link, descricao, cidade,
  estado e idOrgaoOrigem. urlMatricula e datas são opcionais.
- link e urlMatricula (quando informada) exigem http(s); estado exige exatamente 2 caracteres.
- datas aceita no máximo 6 itens (sem mínimo obrigatório), formato dd/MM/yyyy, escolhidas via
  DatePickerDialog e exibidas como chips removíveis.
- estado é selecionado em dropdown com a mesma lista de UFs da tela Imóveis, e vem pré-selecionado
  como "GO" ao cadastrar um novo leilão; é sempre persistido em maiúsculas.
- Campo "Proprietário" só lista pessoas com tipoDocumento = CPF; campo "Órgão de origem" só lista
  pessoas com tipoDocumento = CNPJ.
- Cada um desses campos tem um botão "+" que abre um diálogo de cadastro rápido de pessoa (nome,
  tipo de documento pré-preenchido conforme o campo, número, contatos) sem sair da tela de leilão;
  ao salvar, a pessoa criada é selecionada automaticamente no campo.
- ativo default true quando não informado.
- Formulário tem botões "Salvar leilão" e "Cancelar".
- Exclusão de leilão exige confirmação explícita do usuário (AlertDialog) e também exclui os
  arquivos vinculados (ON DELETE CASCADE).

## 7) Arquivos vinculados ao leilão
- Cadastro de arquivo exige: nome, link válido (http/https) e leilaoId.
- Regra de relacionamento em banco: arquivos.leilaoId referencia leiloes.id, ON DELETE CASCADE.

## 8) Processos
- Campos obrigatórios: idPessoa (vínculo com uma pessoa) e numero e assunto do processo.
- resumo, valor e obs são opcionais (valor default 0.0).
- Formulário tem botões "Salvar processo" e "Cancelar"; exclusão exige confirmação explícita.

## 9) Vitrine
- Entidade simples para divulgação de links: nome, link e descricao (opcional).
- Campos obrigatórios: nome e link; link deve ser uma URL http(s) válida.
- Campos de controle criadoEm/atualizadoEm são preenchidos automaticamente pelo repositório
  (criadoEm preservado em edições; atualizadoEm sempre atualizado ao salvar).
- Na lista, tocar no card abre o link diretamente no navegador (ícone de "abrir" mantido apenas
  como indicação visual); ícones de editar/excluir ficam à parte, sem disparar a navegação do card.

## 10) Integridade relacional no banco
- leiloes.id_proprietario e leiloes.id_orgao_origem referenciam pessoas(id).
- processos.idPessoa referencia pessoas(id).
- arquivos.leilaoId referencia leiloes(id) com ON DELETE CASCADE.
- favoritos.numeroImovel referencia imoveis(numero).
- Ao mudar o schema Room, o banco usa fallbackToDestructiveMigration (sem Migration classes);
  todo dado local é perdido em upgrade de versão.

## 11) Regras de UI/UX gerais
- Todos os formulários de cadastro (Pessoa, Leilão, Processo, Vitrine) têm botão "Cancelar" ao lado
  do "Salvar", que descarta a edição e volta para a lista.
- Títulos de formulário usam "Cadastrando <entidade>" ao criar e "Editar <entidade>" ao editar.
- Formulários ficam dentro de uma Column com verticalScroll, e a tela aplica imePadding no
  container principal, para que o teclado não esconda campos em telas em modo retrato.
- Menu de navegação lateral (NavigationRail) fica fixado no topo (slot "header"), sem inset de
  status bar duplicado, para não sobrar espaço em branco acima do primeiro item.
- Na tela Utilitários, tocar no card abre o link (ícone mantido só como indicação visual).

