# ADR-0010: Três implementações à mão, sempre comparadas com o NetworkX

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [A] [B] [C]

## Contexto

O briefing (§7) é direto: usar NetworkX é legítimo e citável, mas o plano
deve prever **pelo menos um algoritmo implementado à mão** — a projeção
bipartida é a candidata natural — para comparação com a implementação da
biblioteca. "Isso demonstra domínio na banca, não apenas uso de
ferramenta."

## Decisão

Três implementações à mão, uma por frente, cada uma comparada
numericamente com a referência do NetworkX:

| Implementação | Frente | Spec | Comparada com |
|---|---|---|---|
| Projeções (simples e alocação de recursos) | [A] | A-04 / A-05 | `nx.bipartite.*` |
| Modularidade Q | [B] | B-03 | `nx.community.modularity` |
| Centralidade de autovetor (iteração de potência) | [C] | C-02 | `nx.eigenvector_centrality` |

A projeção é a obrigatória do briefing; as outras duas foram escolhidas
por serem as de melhor relação entre esforço e valor didático.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Só a projeção | Cumpre o mínimo, mas deixa cada uma das outras duas frentes sem nada próprio a defender na banca |
| Brandes (intermediação) à mão | Caro de implementar e depurar, e o algoritmo é difícil de explicar em 18 páginas; o retorno didático não paga |
| Louvain à mão | Muito trabalho, e a otimização gulosa é onde bugs sutis se escondem; o risco de entregar uma partição errada é alto demais |
| Tudo à mão | Não cabe no prazo, e o artigo não tem espaço para descrever cinco implementações |

## Consequências

**Boas.** Cada pessoa tem um algoritmo próprio para defender. A
comparação com a biblioteca vira tabela do capítulo 3 e, de quebra, é o
melhor teste possível das implementações: uma divergência acima da
tolerância aponta um bug real.

**Ruins.** Mais código para manter e testar, e duas implementações de
cada coisa para manter em sincronia. A tolerância da comparação (1e-9)
precisa ser escolhida com cuidado: apertada demais falha por acúmulo de
ponto flutuante, frouxa demais deixa passar bug.

**Um cuidado registrado.** As funções prontas do NetworkX para projeção
ponderada **não são todas equivalentes** à alocação de recursos de Zhou
et al. A spec A-05 exige verificar qual corresponde e, se nenhuma
corresponder exatamente, documentar a diferença em vez de forçar a
comparação.

**O que muda no código.** `data/projection/manual.py` e
`networkx_ref.py`; `community/modularity.py`;
`centrality/eigenvector.py`; os testes correspondentes contra
`data/fixtures/tiny_v1/expected/`.

## Impacto no artigo

Três tabelas de validação no capítulo 3 e o parágrafo da Fundamentação
sobre alocação de recursos (Zhou et al., 2007).
