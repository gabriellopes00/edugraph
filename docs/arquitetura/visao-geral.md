# Visão geral da arquitetura

## O problema que a arquitetura resolve

O starter kit provou que o pipeline fecha ponta a ponta: 120 alunos, 7
disciplinas, 197 arestas, Louvain com Q ≈ 0,47, Girvan-Newman 645× mais
lento. Ele foi removido do repositório depois de cumprir esse papel; o
registro do que ele mediu e de onde cada conclusão foi parar está em
[`../../reference/README.md`](../../reference/README.md).

Mas ele amarrava as frentes: a API importava comunidade e centralidade, e
cada script pressupunha que o anterior rodou e deixou um `.gml` num
caminho fixo. Foi escrito por uma pessoa, em sequência. Três pessoas
trabalhando ao mesmo tempo nele ficariam bloqueadas.

## As seis decisões

1. **A fronteira entre frentes é o disco.** Nenhuma frente importa outra.
   Cada uma lê e escreve artefatos num layout fixo, validado por código,
   e um teste automatizado falha se aparecer import cruzado. (ADR-0001,
   ADR-0003)

2. **Contratos primeiro e congelados.** `edugraph.contracts` entrou em
   `main` no dia 0. Mudança exige ADR e aprovação dos três.

3. **Fixtures versionadas e completas.** `data/fixtures/synthetic_v1` já
   traz o bipartido, as quatro projeções, partições e centralidades de
   referência. B e C rodam, testam e sobem a API **sem executar uma linha
   da Frente A**.

4. **Trocar de fonte, não de código.** Todo comando e todo teste aceita
   `--root`. Quando as projeções do OULAD existirem em `data/processed`,
   B e C mudam só o argumento.

5. **API somente leitura sobre artefatos pré-computados.** O cálculo
   acontece pela CLI. Girvan-Newman não roda por requisição HTTP.
   (ADR-0004)

6. **Tudo o que o artigo compara é parâmetro.** Granularidade, critério
   de aresta, ponderação, algoritmo e orçamento de tempo vivem num TOML
   de `configs/`. Cada configuração vira uma linha das tabelas do
   capítulo 3. (ADR-0007)

## Mapa do repositório

| Caminho | Frente | O que é |
|---|---|---|
| `src/edugraph/contracts/` | `[T]` | tipos, protocolos, io, validadores — **congelado** |
| `src/edugraph/data/` | `[A]` | ETL, gerador sintético, bipartido, projeções |
| `src/edugraph/community/` | `[B]` | Louvain, Girvan-Newman, Q, caracterização |
| `src/edugraph/centrality/` | `[C]` | grau, intermediação, autovetor, disciplinas críticas |
| `src/edugraph/api/` | `[C]` | FastAPI somente leitura |
| `src/edugraph/reporting/` | `[T]` | tabelas e figuras do artigo |
| `src/edugraph/__main__.py` | `[T]` | raiz de composição — o único arquivo que vê as três frentes |
| `frontend/` | `[C]` | React + Vite + Cytoscape.js (ADR-0005) |
| `configs/` | todos | uma configuração de experimento por arquivo |
| `data/fixtures/` | `[T]` | commitado, imutável — nova versão é nova pasta |
| `tests/contract/` | `[T]` | o que sustenta o paralelismo |
| `docs/` | todos | ADRs, contratos, specs, material do artigo |
| `results/` | todos | tabelas e figuras que foram para o texto |
| `reference/` | — | registro da prova de conceito, citada nas ADRs |

## Camadas e quem conhece quem

```
            ┌─────────────────────────────┐
            │      __main__.py  [T]       │  ← única composição
            └──────────────┬──────────────┘
                           │ resolve por nome no registro
     ┌──────────┬──────────┼──────────┬──────────┐
     ▼          ▼          ▼          ▼          ▼
  data [A]  community [B]  centrality [C]  api [C]  reporting [T]
     │          │          │          │
     └──────────┴────┬─────┴──────────┘
                     ▼
            ┌─────────────────────────────┐
            │       contracts  [T]        │  ← ninguém abaixo
            └─────────────────────────────┘
```

Duas regras, as duas testadas:

- **Nenhuma seta horizontal.** `data`, `community`, `centrality` e `api`
  não se importam.
- **`contracts` não sobe.** Ele não importa frente nenhuma.

## Documentos relacionados

- [Diagrama do capítulo 3](diagrama-cap3.md) — a figura que abre o
  capítulo de Resultados.
- [Paralelismo](paralelismo.md) — as dependências reais e o que as
  neutraliza; a segunda-feira de cada frente.
- [Branches e merge](branches-e-merge.md) — o fluxo de trabalho.
- [ADRs](../adr/README.md) — por que cada decisão foi tomada.
- [Contratos](../contratos/README.md) — o que atravessa a fronteira.
