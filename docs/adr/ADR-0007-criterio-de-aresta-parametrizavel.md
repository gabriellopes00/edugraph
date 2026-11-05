# ADR-0007: Critério de aresta e granularidade do nó disciplina como parâmetros

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [A]

## Contexto

O briefing (§8) deixa explicitamente em aberto o que define a existência
de uma aresta no bipartido — nota mínima? resultado final aprovado?
participação no AVA? — e diz que o critério precisa ser **parametrizável,
porque o grupo vai testar mais de uma configuração e comparar no capítulo
de Resultados**.

O starter kit fixa `SCORE_THRESHOLD = 60.0` como constante de módulo.

Some-se a decisão **D1**: o OULAD tem só 7 módulos, e com V = módulo a
projeção disciplina↔disciplina degenera. A granularidade do nó disciplina
é tão variável quanto o critério de aresta.

## Decisão

`BipartiteSpec` carrega `granularity`, `edge_criterion`, `threshold`,
`cohort` e `seed`. Nenhum desses valores existe como constante no código
de construção do grafo. Cada combinação vive num TOML de `configs/` e
vira uma linha das tabelas comparativas.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Fixar nota ≥ 60 (starter kit) | O briefing pede comparação entre critérios; uma constante impede |
| Um módulo por critério | Triplica o código e o teste, e ainda assim não permite variar granularidade e coorte junto |
| Parâmetros só na linha de comando | Não ficam versionados junto com o resultado que produziram, e a rastreabilidade do briefing §9 se perde |

## Consequências

**Boas.** Rodar uma variante é copiar um TOML e mudar um campo. Cada
artefato grava a `BipartiteSpec` que o gerou no `meta.json`, então
qualquer número do artigo é rastreável até a configuração. A decisão D1
deixa de ser uma escolha irreversível e passa a ser um parâmetro a
comparar.

**Ruins.** O espaço de configurações cresce rápido (granularidade ×
critério × coorte × ponderação × algoritmo) e é fácil gerar mais
combinações do que se consegue interpretar. `configs/` traz três arquivos
nomeados de propósito, e acrescentar um é decisão consciente.

**Atenção metodológica.** O critério `final_result_pass` usa um rótulo
histórico. Ele é legítimo como **definição declarada de aresta**,
registrada em `BipartiteSpec` — não é entrada de algoritmo de inferência.
A distinção precisa aparecer no texto, porque a banca vai perguntar; está
em `docs/artigo/decisoes-metodologicas.md`.

**O que muda no código.** `contracts/types.py`;
`edugraph/data/bipartite.py`; `configs/`.

## Impacto no artigo

A escolha do critério de aresta é parágrafo de justificativa da
Fundamentação, e a comparação entre critérios é tabela do capítulo 3.
