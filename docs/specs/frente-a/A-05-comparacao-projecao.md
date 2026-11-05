# [A-05] Projeção de referência via NetworkX e comparação

**Frente:** A
**Status:** concluída (18/09/2026)

## Objetivo

Comparar a implementação à mão com a do NetworkX: igualdade numérica,
tempo e distribuição de pesos.

## Contexto

**Cumpre:** `metrics/projections.csv`.
**Consome:** `BipartiteBundle`, `ProjectionBundle`.

A comparação é o que sustenta a afirmação de domínio do algoritmo
(ADR-0010) e é, de quebra, o melhor teste possível da A-04: uma
divergência acima da tolerância aponta bug real.

## Dependências

- A-04, para ter o que comparar.

## Escopo

### Incluído

- `NetworkXSimpleProjection` e `NetworkXResourceAllocationProjection`.
- `compare()` → uma linha de `metrics/projections.csv`.
- `weight_distribution()` → histograma para a figura.
- **Verificar qual função do NetworkX corresponde de fato à alocação de
  recursos de Zhou et al.** As funções prontas não são todas
  equivalentes; se nenhuma corresponder exatamente, **documentar a
  diferença** em vez de forçar a comparação.

### Fora de escopo

- Otimizar a implementação à mão para ganhar do NetworkX. O objetivo é
  demonstrar correção, não competir em desempenho — e reportar que a
  biblioteca é mais rápida é resultado honesto.

## Critérios de aceite

- [x] Dadas as duas implementações sobre `tiny_v1`, quando comparar,
      então `max_abs_diff < 1e-9` e `equal_within_tolerance` é verdadeiro.
- [x] Dadas as duas sobre `synthetic_v1`, idem.
- [x] Dada uma aresta presente em uma e ausente na outra, quando
      comparar, então a diferença é `inf` — **não pode ser silenciada**.
- [x] `metrics/projections.csv` tem as colunas de `METRICS_COLUMNS` e é
      idempotente por `(dataset, projection_id)`.
- [x] Se `collaboration_weighted_projected_graph` não for equivalente à
      alocação de recursos, isso está escrito em
      `docs/artigo/decisoes-metodologicas.md`. *Não é: é Newman (2001),
      `1/(grau−1)`; Zhou é `1/grau`. Não há alocação de recursos pronta no
      NetworkX — a referência usa `generic_weighted_projected_graph` com a
      fórmula de Zhou fornecida por nós, e um teste prova a não
      equivalência (em `tiny_v1`, DA contribui 1/3 vs 1/4).*

## Testes exigidos

- **Unitários:** `xfail` removido; +8 testes — as 4 projeções de `synthetic_v1`
  batem até 1e-9; Newman ≠ Zhou; aresta faltante é diferença infinita;
  projeções incomparáveis são recusadas; tabela idempotente; histograma
  soma as arestas; figura gravada; comando `data compare`.
- **Contrato:** `metrics/projections.csv` é idempotente.

## Arquivos criados ou alterados

- `src/edugraph/data/projection/networkx_ref.py`, `compare.py`.
- `src/edugraph/data/report.py` — `figure_weight_distributions` (PNG + SVG,
  estilo de `reporting.figures`).
- `src/edugraph/data/cli.py` — comando `data compare --dataset X [--figures DIR]`.
- `tests/data/test_projections.py`.

## Impacto no artigo

**Tabela** de validação (manual × NetworkX: diferença máxima, tempos) e
**figura** comparando as distribuições de peso das duas ponderações —
que é onde o efeito de Zhou et al. fica visível.
