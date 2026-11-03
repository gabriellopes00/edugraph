# Decisões de arquitetura (ADRs)

Formato MADR curto: contexto, decisão, alternativas consideradas,
consequências, impacto no artigo. O template está em
[`template.md`](template.md).

**Quando escrever uma ADR.** Só decisões que divergem ou detalham as
seções 2, 4 e 7 do briefing. Divergir do starter kit não precisa de ADR —
ele é prova de conceito, não base a preservar.

O critério prático é o da seção 11 do briefing: se alguém do grupo
precisar responder "por que fizemos assim?" três semanas depois, ou na
banca, a resposta está aqui.

| # | Decisão | Frente |
|---|---|---|
| [0001](ADR-0001-contratos-em-disco.md) | Contratos em disco como única fronteira entre as frentes | [T] |
| [0002](ADR-0002-bundle-csv-meta.md) | Artefatos como bundle CSV + `meta.json`, com `schema_version` | [T] |
| [0003](ADR-0003-pacote-unico-fronteira-testada.md) | Pacote único, um subpacote por frente, fronteira verificada por teste | [T] |
| [0004](ADR-0004-api-somente-leitura.md) | API somente leitura sobre artefatos pré-computados | [C] |
| [0005](ADR-0005-frontend-react-vite.md) | Front-end em React + Vite com Cytoscape.js (**decisão D3**) | [C] |
| [0006](ADR-0006-girvan-newman-orcamento.md) | Girvan-Newman com orçamento de tempo, reportado como resultado | [B] |
| [0007](ADR-0007-criterio-de-aresta-parametrizavel.md) | Critério de aresta e granularidade como parâmetros | [A] |
| [0008](ADR-0008-rotulos-fora-do-grafo.md) | Rótulos históricos fora do grafo, em `outcomes.csv` | [T] |
| [0009](ADR-0009-trunk-based-prs-por-spec.md) | Trunk-based com PRs curtas por spec | [T] |
| [0010](ADR-0010-implementacoes-a-mao.md) | Três implementações à mão, comparadas com o NetworkX | [A][B][C] |
| [0011](ADR-0011-determinismo.md) | Determinismo: seeds, escrita canônica, versões pinadas | [T] |
| [0012](ADR-0012-granularidades-do-comportamento.md) | Granularidades do comportamento: o bipartido pelo AVA | [A] |
| [0013](ADR-0013-laboratorio-ao-vivo.md) | Laboratório ao vivo e leitura dos resultados em linguagem de gente (substitui em parte a 0004) | [T] |

## As que sustentam o paralelismo

Se alguém tiver tempo para ler só três, são estas: **0001** (a fronteira
é o disco), **0003** (a fronteira é testada) e **0008** (o rótulo não
entra no grafo). As duas primeiras são o que permite três pessoas
trabalharem ao mesmo tempo; a terceira é o que protege o diferencial
declarado do trabalho.

## Decisões que ainda não viraram ADR

As quatro decisões abertas do plano de arquitetura (D1 a D4) foram
resolvidas assim:

- **D1** (granularidade do nó disciplina no OULAD) — recomendação
  aceita: `module_presentation` como padrão, `module` como comparação.
  Materializada como parâmetro na ADR-0007, e **confirmada
  empiricamente** na fixture `synthetic_v1`, onde a projeção
  disciplina↔disciplina com V = módulo é o grafo completo K₇ (ver
  `data/fixtures/synthetic_v1/REFERENCE.md`).
- **D2** (nome do pacote e idioma) — recomendação aceita: pacote
  `edugraph`, código em inglês, documentação em português. Não precisa de
  ADR.
- **D3** (front-end) — **o grupo escolheu diferente da recomendação**:
  React + Vite em vez de página estática. ADR-0005.
- **D4** (API somente leitura) — recomendação aceita. ADR-0004.
