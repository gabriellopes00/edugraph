# [A-04] Projeções implementadas à mão: simples e alocação de recursos

**Frente:** A
**Status:** concluída (18/09/2026)

## Objetivo

Implementar as duas ponderações de projeção, para os dois lados, **sem
usar as funções prontas do NetworkX**.

## Contexto

**Cumpre:** `ProjectionBundle`.
**Consome:** `BipartiteBundle`.

É a implementação à mão obrigatória do briefing §7 e o centro da
ADR-0010: "demonstra domínio na banca, não apenas uso de ferramenta".

`simple` conta vizinhos compartilhados; `resource_allocation` soma
`1/grau` de cada vizinho comum (Zhou et al., 2007), corrigindo o viés a
favor de nós de alto grau.

Ver `docs/contratos/projection.md`.

## Dependências

- A-03, para ter um bipartido.
- **Neutralizada por:** `data/fixtures/tiny_v1/bipartite/` e
  `synthetic_v1/bipartite/` já existem — dá para fechar esta spec inteira
  antes da A-03.

## Escopo

### Incluído

- `SimpleProjection.project` e `ResourceAllocationProjection.project`.
- Os dois lados: `student` e `discipline`. **Não esquecer o lado
  disciplina** (briefing §13).
- Percurso pelos nós do lado oposto acumulando pares — **não** montar a
  matriz densa, que no OULAD não cabe em memória.
- Comando `edugraph data project`.

### Fora de escopo

- Comparação com o NetworkX — é a A-05.
- Corte por peso mínimo e demais reduções — são a A-06.

## Critérios de aceite

- [x] Dado `tiny_v1`, quando projetar `student_simple`, então os pesos
      batem com `expected/student_simple.csv` (derivado no papel).
- [x] Dado `tiny_v1`, quando projetar `student_resource_allocation`,
      então os pesos batem com `expected/student_resource_allocation.csv`.
- [x] Dado `tiny_v1`, os pares S1-S6 e S3-S4 **empatam** na projeção
      simples e **se separam** na alocação de recursos (0,25 < 1/3) — é o
      contraexemplo do viés de grau.
- [x] Dado `discipline_simple` sobre `tiny_v1`, os pesos batem com
      `expected/discipline_simple.csv`.
- [x] Dado `synthetic_v1`, a projeção produzida é idêntica à da fixture.
- [x] Dado o resultado, `validate_projection` passa.
- [x] Sobre a projeção aluno↔aluno de uma coorte do OULAD, a execução
      termina em tempo aceitável — **medido na A-06** (18/09/2026): coorte
      BBB_2013J, estágio `data` inteiro (bipartido e projeções) em 22 s.
      A implementação é O(nº de arestas da projeção), não O(|S|²).

## Testes exigidos

- **Contrato:** artefatos passam em `validate_dataset`.
- **Unitários** (`tests/data/test_projections.py`, já escritos como
  `xfail`): quatro testes contra `expected/`, incluindo o da separação de
  ordenação entre as ponderações.

## Arquivos criados ou alterados

- `src/edugraph/data/projection/manual.py`.
- `src/edugraph/data/cli.py` — `cmd_project`.
- `src/edugraph/data/stage.py` — *ficou para a A-03: o estágio `data` precisa
  do bipartido construído a partir do TOML antes de projetar.*
- `tests/data/test_projections.py` — `xfail` removidos; +12 testes (lado
  disciplina em alocação de recursos, contrato, reprodução da fixture
  `synthetic_v1`, nó isolado, `min_weight`, ponderação errada).

## Impacto no artigo

É o algoritmo implementado à mão que o trabalho apresenta. Rende a
descrição do método na Fundamentação (com a fórmula de Zhou et al.) e
alimenta a A-05.
