# Regras deste repositório

TCC Grupo 16 — UniAnchieta. Análise topológica de redes educacionais
bipartidas. Leia [`docs/README.md`](docs/README.md) para o mapa completo.

## Antes de qualquer trabalho: leia `observacoes/`

A pasta [`observacoes/`](observacoes/README.md) guarda os recados que uma
frente deixa para outra. **No começo de toda sessão**, antes de propor ou
alterar qualquer coisa:

1. Descubra quem está trabalhando: pergunte, ou use `git config user.name`
   e o nome do branch. Pedro = Frente A (`para-pedro.md`), Gabriel =
   Frente B (`para-gabriel.md`), Lucas = Frente C (`para-lucas.md`).
2. Leia a seção **Abertas** do arquivo dessa pessoa e do `para-todos.md`,
   e avise o usuário das observações abertas antes de seguir com o pedido
   dele — em especial das que tocam nos arquivos que ele vai mexer.

### Manter a pasta em dia é automático — ninguém precisa pedir

Anotar e fechar observações faz parte de toda tarefa, como rodar os
testes. **Não espere o usuário pedir e não pergunte se deve fazer.**

- **Fechar.** Antes de cada commit, confira se algum arquivo alterado
  aparece numa observação aberta (de qualquer pessoa, não só de quem está
  trabalhando) e se a mudança resolve o que ela pede — mesmo que a tarefa
  fosse outra. Se resolve, mova o item para **Resolvidas** no mesmo commit,
  com a linha `- **Resolvida:** data por <pessoa>, commit/branch — o que foi
  feito`. Se resolve só em parte, atualize o texto do item e deixe-o em
  **Abertas**. Nunca apague itens: "tirar" é mover para **Resolvidas**.
- **Anotar.** Achou um problema num arquivo de outra frente, ou uma
  pendência que depende de outra pessoa? Se a correção é pequena e você
  está com a mão no arquivo, corrija e avise; se depende de decisão do
  dono, **registre** no arquivo dele, no formato de
  [`observacoes/README.md`](observacoes/README.md), com caminho, linha,
  evidência e correção sugerida. Pendência da própria pessoa que ficou para
  depois também vira observação no arquivo dela.
- **Avisar.** Ao terminar, diga ao usuário quais observações foram abertas
  ou fechadas na tarefa.

**Desde 30/10/2026, os três podem mexer em qualquer parte do sistema**
(decisão do grupo, registrada na [ADR-0013](docs/adr/ADR-0013-laboratorio-ao-vivo.md)):
as frentes, os contratos e este arquivo foram montados para a fase de
arquitetura. Ao mexer em arquivo que outra pessoa mantém, deixe uma
observação avisando o dono do que mudou.

## As três regras que não se negociam

### 1. Sem IA, sem aprendizado de máquina

Nenhum componente pode usar ML, embeddings de grafo ou qualquer modelo
treinado com dados rotulados. Está fora de escopo, sem exceção:
`sklearn`, `tensorflow`, `torch`, `node2vec`, k-means, DBSCAN,
classificadores de qualquer natureza.

Foi exigência explícita do orientador e é o diferencial declarado do
trabalho. **Em caso de dúvida, escolha a alternativa clássica de Teoria
dos Grafos.**

Verificado por `tests/contract/test_no_ml.py`.

### 2. Rótulos históricos ficam fora do grafo

O desfecho da matrícula (`final_result`), notas e atributos demográficos
vivem em `bipartite/outcomes.csv`, **separados** de `nodes.csv`, e só
podem ser lidos por módulos chamados `evaluate.py`.

`nodes.csv` tem exatamente três colunas: `id`, `kind`, `label`.

Verificado por `tests/contract/test_outcomes_isolation.py`. ADR-0008.

### 3. Nenhuma frente importa outra

`edugraph.data`, `edugraph.community`, `edugraph.centrality` e
`edugraph.api` **não se importam**. Elas se comunicam por artefatos em
disco, através de `edugraph.contracts`.

`edugraph.lab` e `edugraph.reporting` **não são frentes**: compõem as
frentes pelo registro. A API chama `lab`, nunca uma frente diretamente.

Só dois arquivos são isentos: `edugraph/__main__.py` e
`edugraph/contracts/registry.py`. Acrescentar um terceiro exige ADR.

Verificado por `tests/contract/test_import_boundaries.py`. ADR-0003.

## Contratos

`src/edugraph/contracts/` entrou em `main` no dia 0 e ficou **congelado**
durante a fase de arquitetura. O congelamento acabou em 30/10/2026: mudar
um contrato não exige mais ADR nem a aprovação dos três.

O que continua valendo, porque as fixtures e os artefatos em disco
dependem disso: mudar layout, nome de coluna ou semântica de campo
**sobe `SCHEMA_VERSION`** e regenera as fixtures (versão nova, como em
`synthetic_v2`). Os testes de `tests/contract/` seguem rodando e protegem
as três regras acima.

Antes de mudar o contrato, confira se o que você precisa não cabe em
`params` ou em `meta.stats` — os dois são dicionários livres e existem
para isso.

## Fixtures são imutáveis

`data/fixtures/` é versionado e **nunca muda**. Quem precisar de outra
cria uma versão nova (`synthetic_v2`).

`scripts/make_fixtures.py` recusa sobrescrever sem `--force`, e a
regeneração é byte a byte idêntica (metadados congelados, ADR-0011). Um
diff em `data/fixtures/` significa que algo mudou de verdade.

## Comandos

```bash
pip install -e ".[dev]"

python -m edugraph validate --root data/fixtures
python -m edugraph api serve --root data/processed --root data/fixtures
#   com o front compilado (cd frontend && npm install && npm run build),
#   http://127.0.0.1:8000/ abre o laboratório ao vivo e o explorador
python -m edugraph run configs/synthetic_v1.toml --dry-run
python scripts/make_fixtures.py

pytest                                         # sobre as fixtures
pytest tests --artifacts-root data/processed   # sobre o OULAD
pytest -m "not slow"                           # o que a CI roda

ruff check . && ruff format --check . && mypy src/edugraph/contracts
```

**Nada de `make`:** o grupo trabalha em Windows. Todo comando é
`python -m edugraph`.

## Convenções de código

- **Idioma (decisão D2):** código, nomes de coluna e chaves JSON em
  **inglês**, sem acentos, coerentes com NetworkX e pandas. Docstrings,
  comentários, documentação, specs, ADRs, commits e artigo em
  **português**.
- Só `pathlib`; nunca concatenação de caminho com `/` literal.
- **UTF-8 explícito** em toda leitura e escrita. Console: chamar
  `edugraph.console.configure()` nos pontos de entrada — o Windows usa
  `cp1252` por padrão e imprimir um acento levanta exceção.
- Toda escrita de artefato passa por `contracts.io`. Nenhum módulo de
  frente abre um CSV de artefato por conta própria.
- Todo algoritmo estocástico recebe `seed` explícita, gravada em
  `params`.
- Stub de spec ainda aberta levanta
  `NotImplementedError("A-04: ver docs/specs/...")` — **com o id da
  spec**, sempre.

## Testes

- Nomes em português, descrevendo o comportamento:
  `test_orcamento_estourado_devolve_timeout_e_nao_excecao`.
- `xfail` de spec aberta usa
  `@pytest.mark.xfail(reason="A-04 não implementada", raises=NotImplementedError, strict=True)`.
  `strict=True` é proposital: quando a spec fecha e o teste passa, a CI
  quebra — é o aviso de remover o marcador.
- Teste que depende de um dataset declara `@pytest.mark.dataset("nome")`
  e é pulado, não quebrado, quando ele não existe.
- Escrita só em `tmp_path`. Nenhum teste escreve em `data/fixtures`.
- Valores esperados de `tiny_v1` foram **derivados no papel** (ver
  `docs/testes/estrategia.md`). Não substitua por saída da biblioteca:
  isso transformaria a verificação em tautologia.

## Git

- `main` protegida, só por PR com CI verde.
- Uma spec, um branch, um PR: `a/A-04-projecao-manual`.
- Commits em português com o id da spec:
  `B-03: modularidade à mão e comparação com NetworkX`.
- PR que toca `contracts/`, `tests/contract/`, `data/fixtures/`,
  `__main__.py`, `pyproject.toml` ou `requirements*.txt` precisa da
  aprovação dos outros dois.

## Ao escrever para o artigo

Toda escolha não-óbvia vira parágrafo de justificativa e pergunta de
banca. Se você tomou uma decisão que pode surpreender outra pessoa do
grupo, ela vai para uma ADR ou para
`docs/artigo/decisoes-metodologicas.md` — no mesmo PR.
