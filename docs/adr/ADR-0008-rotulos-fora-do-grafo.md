# ADR-0008: Rótulos históricos fora do grafo, em `outcomes.csv`

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

A restrição inegociável do briefing (§2): nenhum componente pode usar IA
ou aprendizado de máquina, e **rótulos históricos entram apenas na etapa
de validação a posteriori, nunca como entrada de algoritmo**. Foi
exigência explícita do orientador e é o diferencial declarado do
trabalho.

O risco não é alguém decidir treinar um classificador — é vazamento por
descuido. Se `final_result` viajar como atributo de nó, ele fica a uma
linha de distância de entrar num cálculo, e ninguém percebe até a banca
perguntar.

## Decisão

Desfechos, notas e atributos demográficos vivem em
`bipartite/outcomes.csv`, **separados** de `nodes.csv`. `nodes.csv` tem
exatamente três colunas: `id`, `kind`, `label`.

Duas verificações automáticas:

1. `validate_node_file` recusa qualquer `nodes.csv` que contenha uma
   coluna da lista `FORBIDDEN_NODE_COLUMNS`, e roda sobre todo artefato
   nos testes de contrato.
2. `tests/contract/test_outcomes_isolation.py` analisa o código com `ast`
   e falha se `load_outcomes` for chamada fora de um `evaluate.py`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Desfecho como atributo de nó | É exatamente o vazamento que a restrição quer impedir; fica invisível numa revisão de código |
| Coluna na tabela normalizada, sem separação em disco | A tabela normalizada é interna à Frente A; B e C leriam o desfecho junto com o grafo |
| Só convenção documentada | Mesma objeção da ADR-0003: sem teste, é boa intenção |

## Consequências

**Boas.** O vazamento vira erro de CI. A afirmação "nenhum algoritmo viu
o desfecho" deixa de depender da palavra de quem implementou e passa a
ser verificável por qualquer pessoa que rode a suíte — inclusive pelo
orientador.

**Ruins.** A validação a posteriori fica um pouco mais trabalhosa: é
preciso carregar dois artefatos e cruzá-los por id. É um custo pequeno,
pago num punhado de funções, todas em arquivos chamados `evaluate.py`.

**O que muda no código.** `Outcomes` e `FORBIDDEN_NODE_COLUMNS` em
`contracts/types.py`; `validate_node_file`; `community/evaluate.py` e
`centrality/evaluate.py`; `tests/contract/test_outcomes_isolation.py`.

## Impacto no artigo

Sustenta a afirmação central da Introdução e da Conclusão: os
agrupamentos e os rankings vêm **apenas** da topologia. Registrado em
`docs/artigo/decisoes-metodologicas.md`.
