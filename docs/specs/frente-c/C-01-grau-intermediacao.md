# [C-01] Grau e intermediação nas duas projeções

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Calcular as centralidades de grau e de intermediação sobre as projeções,
com a semântica do peso decidida e registrada.

## Contexto

**Cumpre:** `CentralityResult`.
**Consome:** `ProjectionBundle`.

A intermediação é a métrica que o objetivo declarado na Introdução
associa a "gargalos no fluxo educacional". Via
`nx.betweenness_centrality`, que usa Brandes (2001) internamente — não é
implementada à mão (ADR-0010: custo didático alto, retorno baixo).

Ver `docs/contratos/centrality.md`.

## Dependências

- Projeções da Frente A.
- **Neutralizada por:** as quatro projeções das fixtures.

## Escopo

### Incluído

- `DegreeCentrality.compute` com `normalized` e `weight`.
- `BetweennessCentrality.compute` com `normalized`, `weight_mode` e `k`.
- **Decidir e registrar `weight_mode`.** Em NetworkX, `weight` num
  caminho mínimo é *distância*: peso alto vira caminho longo. Nas
  projeções, peso alto significa *mais* afinidade — ou seja, distância
  *menor*. Passar `weight="weight"` direto **inverte a semântica**. As
  três opções (`none`, `inverse`, `raw`) estão no contrato; a escolha
  vira legenda de tabela, porque muda o ranking.
- Amostragem de pivôs (`k`, com `seed`) para grafos grandes, reportando
  que o valor é estimativa.
- Comandos `edugraph centrality compute` e `centrality all`.

### Fora de escopo

- Autovetor (C-02) e ranking de disciplinas (C-03).

## Critérios de aceite

- [x] Dado `tiny_v1`/`student_simple`, o grau bate com
      `expected/student_simple.centrality.csv`: S3 = 1,0; S1 = S2 = S6 =
      0,6; S4 = S5 = 0,4.
- [x] Dado o mesmo, a intermediação sem peso bate: S3 = 0,6, todos os
      outros 0 — S3 é o único vértice de corte.
- [x] Dado `synthetic_v1`/`discipline_simple`, **todos** os nós têm
      intermediação 0 e grau 1,0: a projeção é K₇. O teste **afirma a
      degeneração** (decisão D1), não a contorna.
- [x] `params` registra `normalized`, `weight_mode` e, se houver, `k` e
      `seed`.
- [x] `validate_centrality` passa, inclusive a faixa [0, 1] com
      `normalized=True`.
- [x] A escolha de `weight_mode` está em
      `docs/artigo/decisoes-metodologicas.md`.

## Testes exigidos

- **Contrato:** `scores` cobre exatamente os nós da projeção.
- **Unitários** (`tests/centrality/test_centralidades.py`, implementados e passando): grau e intermediação contra `expected/`; degeneração de
  `discipline_simple`.

## Arquivos criados ou alterados

- `src/edugraph/centrality/degree.py`, `betweenness.py`.
- `src/edugraph/centrality/cli.py`, `stage.py`.
- `tests/centrality/test_centralidades.py` — testes das métricas e dos casos degenerados.

## Impacto no artigo

**Decisão metodológica**: como o peso foi tratado no caminho mínimo.
Alimenta C-03 (disciplinas críticas) e C-06 (validação).
