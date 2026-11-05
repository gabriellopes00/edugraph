# [B-03] Modularidade Q implementada à mão

**Frente:** B
**Status:** concluída (20/09/2026)

## Objetivo

Implementar a modularidade Q sem usar `nx.community.modularity`, e
comparar as duas.

## Contexto

**Cumpre:** nada em disco — alimenta `Partition.modularity`.
**Consome:** `ProjectionBundle`, `Partition`.

Segunda implementação à mão do projeto (ADR-0010), ao lado da projeção
(A) e da iteração de potência (C).

Q = (1/2m) Σᵢⱼ (Aᵢⱼ − kᵢkⱼ/2m) δ(cᵢ, cⱼ). Em grafo ponderado, Aᵢⱼ é o
peso, kᵢ a força do nó e m metade da soma de todos os pesos.

## Dependências

- Nenhuma de outra frente: as fixtures trazem projeções **e** partições
  de referência.

## Escopo

### Incluído

- `modularity(graph, membership, weight, resolution)`.
- **Usar a forma fechada por comunidade**, `Q = Σ_c (m_c/m − γ(K_c/2m)²)`,
  que é O(m). A forma ingênua O(n²) pode ficar nos testes, sobre
  `tiny_v1`, como verificação cruzada.
- `compare_with_networkx()` — os dois valores e a diferença.
- `densify()` — renumeração determinística para `0..k-1`, usada pela
  B-01 e pela B-02.

### Fora de escopo

- Modularidade para grafos bipartidos (Barber) — o trabalho calcula Q
  sobre as **projeções**, não sobre o bipartido.
- Modularidade dirigida.

## Critérios de aceite

- [x] Dada a partição trivial (tudo numa comunidade), então Q = 0.
- [x] Dada a partição de referência de `synthetic_v1`, então o Q à mão
      difere do NetworkX em menos de 1e-9.
- [x] Dado o mesmo grafo com e sem peso, então os valores diferem e
      ambos estão em [−0,5, 1].
- [x] Dada uma partição com ids esparsos, então `densify` devolve
      `0..k-1` preservando os agrupamentos, de forma determinística.
- [x] Dado um grafo de 100 mil arestas, então o cálculo termina em tempo
      linear — **medir**, para provar que a forma fechada foi usada.

## Testes exigidos

- **Unitários** (já escritos como `xfail`): Q da partição trivial é zero;
  Q à mão bate com o NetworkX.
- Acrescentar: forma fechada = forma ingênua sobre `tiny_v1`;
  determinismo de `densify`.

## Arquivos criados ou alterados

- `src/edugraph/community/modularity.py` — `modularity`,
  `compare_with_networkx`, `densify` e os dois utilitários que a B-01 e
  a B-02 usam para converter entre `membership` e lista de comunidades.
- `tests/community/test_modularidade.py` (novo), com a forma ingênua
  escrita no próprio teste.

## Números medidos (20/09/2026)

**Contra o NetworkX**, nas quatro projeções de `synthetic_v1` com a
partição do Louvain:

| projeção | Q à mão | `nx.community.modularity` | diferença |
|---|---:|---:|---:|
| `student_simple` | 0,4665532051 | 0,4665532051 | 0 |
| `student_resource_allocation` | 0,4595772030 | 0,4595772030 | 3,2e-15 |
| `discipline_simple` | 0,3143096286 | 0,3143096286 | 5,6e-17 |
| `discipline_resource_allocation` | 0,3714629460 | 0,3714629460 | 5,6e-17 |

Todas abaixo da tolerância de 1e-9. As diferenças não nulas são ruído de
ponto flutuante — as duas implementações somam na mesma ordem de
grandeza, mas não na mesma ordem.

**Contra a forma ingênua** `O(n²)`, escrita no teste direto da fórmula:
igualdade até 1e-9 em `tiny_v1`, para três partições (a natural, a de
singletons e uma deliberadamente ruim) e com e sem peso.

**Custo**, que é o critério de aceite que prova a forma fechada:

| arestas | tempo |
|---:|---:|
| 25 mil | 15 ms |
| 100 mil | 80 ms |
| 400 mil | 334 ms |

Quadruplicar as arestas quadruplica o tempo: é O(m). A forma ingênua
sobre o grafo de 100 mil arestas percorreria 20 mil × 20 mil pares — não
é questão de constante, é de ordem.

## Impacto no artigo

**Algoritmo implementado à mão** — descrição do método na Fundamentação e
tabela de validação contra o NetworkX.
