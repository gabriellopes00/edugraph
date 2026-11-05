# ADR-0006: Girvan-Newman com orçamento de tempo, reportado como resultado

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [B]

## Contexto

O Girvan-Newman recalcula a intermediação de todas as arestas a cada
remoção: O(m²n). O starter kit mediu, sobre 120 nós sintéticos, **645×**
o tempo do Louvain para chegar ao mesmo número de comunidades com Q
menor. Sobre o OULAD completo, não termina.

O briefing (§8) antecipa isso e é explícito: o plano precisa prever
amostragem, subgrafo ou limite de tempo, e tratar a limitação **como
resultado a reportar, não como falha**.

## Decisão

`GirvanNewmanAlgorithm.run` recebe `time_budget_s` e verifica o relógio a
cada corte. Ao estourar, devolve uma `Partition` com `status="timeout"` e
a melhor partição obtida até ali. Se nem o primeiro corte couber,
devolve `status="skipped"` com a partição trivial.

**O contrato proíbe levantar exceção nesse caso.** Um estouro de
orçamento é dado do capítulo 3, não erro de execução.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Só citar a complexidade teórica na Fundamentação | Perde o dado empírico, que é mais convincente que a notação assintótica |
| Rodar em máquina maior | Empurra o problema; O(m²n) sobre 28 mil estudantes não cabe em máquina nenhuma que o grupo tenha |
| Abandonar o algoritmo | A Introdução já entregue cita "Louvain ou Girvan-Newman" nominalmente; a comparação entre os dois é resultado esperado |
| Levantar `TimeoutError` | Transformaria em falha de pipeline o que é achado do trabalho |

## Consequências

**Boas.** A comparação Louvain × Girvan-Newman acontece sempre, com o
recorte que couber, e a linha da tabela diz qual foi. O custo do
algoritmo vira número medido, que é exatamente o tipo de resultado que a
seção 6.2 do briefing pede.

**Ruins.** Uma partição com `status="timeout"` não é comparável com uma
`ok` em pé de igualdade, e o texto precisa dizer isso — a tabela do
capítulo 3 carrega a coluna `status` justamente para não deixar a
comparação parecer mais limpa do que é.

**O que muda no código.** `edugraph/community/girvan_newman.py`;
`RunStatus` em `contracts/types.py`; o campo `status` no `meta.json` da
partição; `configs/oulad_cohort_bbb_2013j.toml`.

## Impacto no artigo

Decisão metodológica registrada em
`docs/artigo/decisoes-metodologicas.md`, e coluna `status` na tabela
principal do capítulo 3 (spec B-04).
