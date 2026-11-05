# ADR-0011: Determinismo — seeds fixas, escrita canônica, versões pinadas

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

O briefing (§9) trata rastreabilidade como requisito funcional: refazer
uma figura na semana da entrega tem que ser um comando, não uma
arqueologia. E a restrição da §2 exige que toda inferência seja
"determinística e rastreável até a estrutura do grafo".

O Louvain é estocástico na ordem de visita dos nós. O starter kit relata
~25 comunidades com Q ≈ 0,47; sem semente fixa, duas execuções dão
partições diferentes, e nenhum número do artigo se sustenta.

## Decisão

Quatro regras, todas verificadas por teste:

1. **Seed explícita** em todo algoritmo estocástico, gravada em `params`
   no `meta.json`. Nenhum código usa o gerador global do módulo `random`.
2. **Escrita canônica**: nós e arestas ordenados, extremos de aresta em
   ordem lexicográfica, floats no `repr` mais curto que retorna ao mesmo
   valor, `\n` e UTF-8 explícito.
3. **Fixtures com metadados congelados**: `created_at` fixo e
   `runtime_s = 0`. Tempo é medido nas rodadas reais, em
   `data/processed`, que é de onde as tabelas do artigo saem.
4. **Versões pinadas** em `requirements.txt`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Aceitar variação e reportar médias de n execuções | Multiplica o custo de cada rodada — proibitivo com Girvan-Newman em jogo — e não resolve a reprodutibilidade, só a descreve |
| Seed fixa sem escrita canônica | A partição seria estável, mas o arquivo mudaria de ordem entre execuções e o diff da fixture viraria ruído |
| Versões livres | Uma atualização de `networkx` no meio do trabalho moveria números já escritos no artigo |

## Consequências

**Boas.** `python scripts/make_fixtures.py --force` regrava as fixtures
**byte a byte idênticas** — verificado. Um diff em `data/fixtures/` passa
a ser sinal confiável de que algo mudou de verdade. E qualquer número do
artigo pode ser refeito a partir do TOML que o gerou.

**Ruins.** Seed fixa dá uma falsa sensação de robustez: um resultado que
só vale para a seed 42 não é resultado. A mitigação está nos testes, que
comparam **faixas** e não igualdade exata — um teste que exige Q = 0,4712
quebra na primeira troca de versão da biblioteca sem que nada esteja
errado. Onde a estabilidade importa de verdade (valores de `tiny_v1`), os
esperados foram derivados no papel, não copiados da saída da biblioteca.

**Um limite descoberto na prática: seed fixa não basta entre versões do
Python.** Regenerar `synthetic_v1` sob Python 3.11 e sob 3.13 dá Q
diferente nas projeções de peso fracionário — não nas de peso inteiro. A
causa, isolada por instrumentação: `python-louvain.induced_graph()`
itera `set(partition.values())`, e a ordem de iteração de `set` **não é
parte do contrato de linguagem** do Python — ao contrário de `dict`
(ordem de inserção garantida desde a 3.7), sets são documentados como
não ordenados, e a implementação interna do CPython pode (e mudou) variar
entre versões. Empates reais de ganho — mais comuns com pesos
fracionários que com pesos inteiros — acabam desempatados por essa
ordem, e o desempate se propaga para o resto do algoritmo.

Isso não é bug nosso e não dá para corrigir sem reescrever a parte
interna da biblioteca. A mitigação é de processo: **as fixtures
commitadas são geradas e regeneradas sob uma única versão fixa (Python
3.13)**, documentada em `scripts/make_fixtures.py` e
`data/fixtures/README.md`, e o job `fixtures-deterministicas` da CI fixa
essa mesma versão — de propósito, ele não é uma matriz como o job
`qualidade`, que só lê fixtures já commitadas e por isso não é afetado.

**O que muda no código.** `contracts/io.py` (escrita canônica);
`scripts/make_fixtures.py` (`FIXTURE_CREATED_AT`, `FIXTURE_RUNTIME_S`);
`DEFAULT_SEED` em `community/louvain.py`; `requirements.txt`;
`tests/contract/test_roundtrip.py`.

## Impacto no artigo

Sustenta a afirmação de reprodutibilidade e permite que a seção de
limitações declare com honestidade o que depende da semente.
