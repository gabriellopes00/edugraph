# [B-04] Comparação Louvain × Girvan-Newman × ponderação

**Frente:** B
**Status:** concluída (20/09/2026)

## Objetivo

Produzir `metrics/communities.csv`: a **tabela principal do capítulo 3**.

## Contexto

**Cumpre:** `metrics/communities.csv`.
**Consome:** `Partition`.

O briefing §9 pede comparações, não só resultados. A arquitetura torna
trivial rodar as variantes: cada uma é uma linha desta tabela.

Ver `docs/contratos/metrics.md`.

## Dependências

- B-01 e B-02, para ter partições a comparar.

## Escopo

### Incluído

- `to_metrics_row()` e `compare()` no formato de `METRICS_COLUMNS`.
- **Incluir as linhas com `status="timeout"`.** Uma execução que não
  coube no orçamento é dado do artigo; omiti-la seria esconder o
  resultado que o briefing §8 manda reportar.
- `agreement()` — NMI e índice de Rand ajustado entre duas partições do
  mesmo grafo. São medidas de teoria da informação entre partições
  conhecidas, não aprendizado de máquina.
- Comando `edugraph community compare --dataset X`.

### Fora de escopo

- Validação contra o desfecho — é a B-06.
- Figuras — são a B-07.

## Critérios de aceite

- [x] Dadas as partições de `synthetic_v1`, quando comparar, então a
      tabela tem uma linha por (projeção, algoritmo), com as colunas de
      `METRICS_COLUMNS`.
- [x] Rodar duas vezes **atualiza** as linhas em vez de duplicá-las.
- [x] Uma partição com `status="timeout"` aparece na tabela, com o
      status visível. (Coberto por teste; na rodada de `synthetic_v1`
      todas as execuções couberam no orçamento e saíram `ok`.)
- [x] `agreement()` entre uma partição e ela mesma dá NMI = 1.
- [x] A tabela permite responder, sem cálculo adicional: qual algoritmo
      deu maior Q, qual foi mais rápido, e quanto.
- [x] A comparação entre as duas **ponderações** aparece — não só entre
      os dois algoritmos.

## Testes exigidos

- **Contrato:** idempotência por `(dataset, projection_id, algorithm)`;
  mudar as colunas levanta `ContractError`.
- **Unitários:** NMI de uma partição consigo mesma é 1; linha com timeout
  entra na tabela.

## Arquivos criados ou alterados

- `src/edugraph/community/compare.py`.
- `src/edugraph/community/cli.py` — `cmd_compare`.
- `tests/community/test_comparacao.py` (novo).

## A tabela, como ela sai hoje (20/09/2026, `synthetic_v1`)

```
dataset,projection_id,algorithm,modularity,n_communities,largest_community,runtime_s,status,params
```

| projeção | algoritmo | Q | k | maior | tempo | status |
|---|---|---:|---:|---:|---:|---|
| `discipline_resource_allocation` | louvain | 0,3715 | 3 | 3 | 0,068 s | ok |
| `discipline_simple` | girvan_newman | 0,0331 | 4 | 4 | 0,003 s | ok |
| `discipline_simple` | louvain | 0,3143 | 3 | 3 | 0,067 s | ok |
| `student_resource_allocation` | louvain | 0,4596 | 3 | 38 | 0,088 s | ok |
| `student_simple` | girvan_newman | 0,4174 | 3 | 42 | 34,623 s | ok |
| `student_simple` | louvain | 0,4666 | 3 | 39 | 0,087 s | ok |

As três perguntas que ela responde sem cálculo adicional: **o Louvain
deu o maior Q** (0,4666 contra 0,4174 na mesma projeção), **foi o mais
rápido** (por três ordens de grandeza) e **a ponderação muda pouco o Q
do lado aluno** (0,4666 contra 0,4596) e bastante o do lado disciplina
(0,3143 contra 0,3715).

Os tempos desta tabela saem da CLI e incluem, na primeira execução, o
custo de importar a biblioteca. O número limpo do custo relativo —
1.453× — está na B-02, medido com as duas no mesmo processo.

**Concordância entre os algoritmos** (`agreement`), sobre a mesma projeção:

| projeção | NMI | Rand ajustado |
|---|---:|---:|
| `student_simple` | 0,7737 | 0,8076 |
| `discipline_simple` | 0,6117 | 0,1404 |

O contraste é resultado: em `student_simple` os dois acham
essencialmente a mesma partição por caminhos diferentes; em
`discipline_simple`, com 7 nós, o Girvan-Newman quebra três nós em
comunidades unitárias e o Rand ajustado despenca, mesmo com o NMI ainda
em 0,61 — duas medidas que discordam são o melhor argumento para
reportar as duas.

## Impacto no artigo

**A tabela principal do capítulo 3**, mais a figura de Q × tempo por
algoritmo (B-07).
