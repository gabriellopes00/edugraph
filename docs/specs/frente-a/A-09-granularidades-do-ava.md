# [A-09] Granularidades do comportamento: o bipartido pelo AVA

**Frente:** A
**Status:** concluída (18/09/2026)

## Objetivo

Trocar o critério de aresta de "cursou o módulo" para "interagiu com o
recurso do ambiente virtual", para que a projeção aluno↔aluno passe a
carregar informação relacional e as Frentes B e C tenham o que analisar.

## Contexto

**Cumpre:** `BipartiteBundle`, `Projection` (dataset `oulad_vle_bbb_2013j`).
**Consome:** CSV bruto do OULAD (`studentVle`, `vle`).

Como a A-08, esta spec não estava no plano. Ela nasceu do resultado da
A-08: a linha de base mostrou que o bipartido por matrícula não sustenta
comunidades de alunos, e esta spec é a saída medida.

**O problema, em um número.** 91,8% dos alunos do OULAD cursam um único
módulo. Com grau 1, a projeção aluno↔aluno é uma união de cliques quase
disjuntas; o Q de 0,7728 que ela produz é **menor** que o de réplicas
embaralhadas (0,781). Não há estrutura a reportar.

**A saída, em outro número.** No AVA o grau mediano do aluno é **40**.

| nó do lado V | grau mediano do aluno |
|---|---:|
| módulo | 1 |
| módulo × apresentação | 1 |
| avaliação (coorte) | 10, mas todos fazem as mesmas → densidade 0,997 |
| **recurso do AVA** | **40** |
| **tipo de atividade** | **7** |

**Não é mudança de escopo.** O tema aprovado descreve o bipartido como
"Aluno → Comportamento"; o briefing §8 já listava "participação no AVA"
entre os critérios candidatos; `EdgeCriterion` já continha
`vle_activity`. Faltava só o valor correspondente em `Granularity` —
ADR-0012.

## Dependências

- A-02, para o ETL e o esquema das tabelas.
- A-03, para `build_bipartite` e `discipline_ids`.
- A-08, que é o motivo de a spec existir e a linha de base da validação.

## Escopo

### Incluído

- `Granularity` ganha `vle_site` e `vle_activity_type` (ADR-0012).
- `studentVle` passa a ler `id_site`.
- `etl.normalize_vle(raw_dir, *, cache_dir, chunksize, cohort)` — uma
  linha por (aluno, recurso), com `cohort` aplicada **durante** a leitura
  em blocos.
- `discipline_ids` trata as duas granularidades novas.
- `_INCOMPATIVEIS` em `bipartite.py`: combinações que dariam grafo vazio
  em silêncio levantam `ContractError` nomeando a causa.
- `configs/oulad_vle_bbb_2013j.toml`.
- Artefatos em `data/processed`, mais 5 réplicas nulas.

### Fora de escopo

- Calcular Q e comparar com o nulo — é da spec B-06.
- Renomear o lado V. `kind="discipline"` marca o lado, não a natureza do
  nó; mudar isso quebraria B e C sem ganho real (ADR-0012).
- Rodar a base inteira pelo AVA. `studentVle` tem 10,6 M linhas e a
  projeção aluno↔aluno da base toda não cabe em memória (A-06). A coorte
  é a unidade.

## Critérios de aceite

- [x] `normalize_vle` devolve uma linha por (aluno, recurso), com os
      cliques somados e o tipo de atividade vindo de `vle.csv`.
- [x] `score_media` vem nula, e a tabela tem a mesma forma das outras
      duas — quem consome não precisa saber de qual ETL veio.
- [x] `granularity="vle_site"` põe o recurso no lado V; o grau do aluno
      é maior que na granularidade por matrícula.
- [x] `granularity="vle_activity_type"` agrega recursos do mesmo tipo em
      **uma** aresta, com os cliques somados.
- [x] `score_threshold` sobre a tabela do AVA levanta `ContractError`
      nomeando a causa, em vez de devolver grafo vazio.
- [x] `vle_activity` sobre a tabela por avaliação idem.
- [x] Granularidade do AVA sobre a tabela por matrícula falha exigindo
      a coluna que falta.
- [x] Os artefatos passam em `edugraph validate`.

## Testes exigidos

- **Unitários:** `tests/data/test_vle.py`, 15 testes sobre
  `tests/data/oulad_mini/`, com os valores **derivados à mão** das duas
  tabelas da fixture.
- **Contrato:** os existentes continuam passando sem alteração — é a
  prova de que a mudança é aditiva.

## Arquivos criados ou alterados

- `src/edugraph/contracts/types.py` — `Granularity`.
- `src/edugraph/data/oulad/schema.py` — `id_site` em `studentVle`.
- `src/edugraph/data/oulad/etl.py` — `normalize_vle`, `VLE_COLUMNS`,
  `VLE_KEY`, `_CACHE_VLE`.
- `src/edugraph/data/bipartite.py` — `discipline_ids`, `_INCOMPATIVEIS`.
- `src/edugraph/data/pipeline.py` — escolha da tabela por granularidade.
- `configs/oulad_vle_bbb_2013j.toml`.
- `tests/data/test_vle.py`.
- `docs/adr/ADR-0012-granularidades-do-comportamento.md`.

## Números medidos (18/09/2026, coorte BBB 2013J)

Bipartido: 1.870 alunos × 320 recursos, 67.531 arestas. Grau do aluno:
mediana 33, média 36,1, máximo 182. Projeção aluno↔aluno: 1.746.901
arestas, densidade 0,9996, um componente.

| ponderação | Q real | Q nulo | razão |
|---|---:|---:|---:|
| contagem simples | 0,0393 | 0,0090 | 4,4× |
| alocação de recursos | 0,0825 | 0,0158 | 5,2× |

Confirmado em FFF 2013J (9,2×) e DDD 2014J (7,0×), três sementes cada.

## Impacto no artigo

**Tabela comparativa entre critérios de aresta** e o parágrafo que
justifica ter escolhido o critério *depois* de medir. Vai junto o achado
sobre ponderação: sob extração de espinha a contagem simples cai abaixo
do nulo e a alocação de recursos não, porque a primeira premia volume de
cliques. Registrado em `docs/artigo/decisoes-metodologicas.md`.

**Limitação a reportar.** O Q absoluto é baixo (0,05 a 0,08) e a projeção
é quase completa: o sinal está nos pesos, não na topologia. Aplicar
limiar fragmenta o grafo em centenas de componentes de nó isolado.
