# ADR-0004: API somente leitura sobre artefatos pré-computados

**Status:** aceita; substituída em parte pela [ADR-0013](ADR-0013-laboratorio-ao-vivo.md) (o laboratório monta redes pequenas na hora; o cálculo pesado segue só pela CLI)
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [C]

## Contexto

O starter kit calcula por requisição: `GET /communities/girvan_newman`
dispara o Girvan-Newman inteiro. Sobre 120 nós sintéticos isso responde
em segundos. Sobre uma coorte real do OULAD, o algoritmo é O(m²n) e a
requisição não termina — nem com timeout generoso.

Além disso, uma API que calcula precisa importar `community` e
`centrality`, o que derruba a fronteira da ADR-0003 no primeiro endpoint.

## Decisão

A API serve o que está em disco e nada mais. O cálculo acontece pela CLI
(`python -m edugraph run configs/x.toml`). Toda rota é um `GET` sobre um
artefato já gravado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Cálculo por requisição (starter kit) | Girvan-Newman não termina em tempo de HTTP; e obriga a API a importar duas frentes |
| Fila de tarefas (Celery, RQ) | Infraestrutura pesada, proibida pelo briefing §13; complexidade que não vira parágrafo no artigo |
| `POST /runs` disparando o registro de estágios | Viável e compatível com os contratos, mas fora do escopo inicial: pode ser acrescentado depois sem mudar nada do que já existe |

## Consequências

**Boas.** A API sobe em milissegundos e responde em milissegundos.
Funciona no dia 0 sobre `data/fixtures` e **não sabe** se a partição veio
da Frente B ou da biblioteca de referência — é essa ignorância que
permite à Frente C construir a aplicação inteira antes de B existir. Cada
resposta é reprodutível, porque vem de um artefato com `meta.json`.

**Ruins.** Não dá para explorar interativamente uma configuração nova
pela interface: mudar limiar ou resolução exige rodar a CLI e recarregar.
Para o uso previsto — apresentar resultados de um conjunto fechado de
configurações — isso é aceitável, e é o que a seção 6.2 do briefing pede
ao falar em relatórios de uso interno.

**O que muda no código.** `edugraph/api/` inteiro; `tests/api/`.

## Impacto no artigo

Justifica, no capítulo 3, por que a limitação de custo do Girvan-Newman é
tratada na arquitetura e não escondida atrás de um spinner.
