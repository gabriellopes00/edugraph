# [C-02] Centralidade de autovetor por iteração de potência

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Implementar a centralidade de autovetor à mão, com fallback e registro de
convergência, e compará-la com o NetworkX.

## Contexto

**Cumpre:** `CentralityResult`.
**Consome:** `ProjectionBundle`.

Terceira implementação à mão do projeto (ADR-0010). Um nó é central se
está ligado a nós centrais: `x = (1/λ) A x`, resolvido iterando
`x ← A x / ‖A x‖`.

## Dependências

- Projeções da Frente A.
- **Neutralizada por:** as fixtures.

## Escopo

### Incluído

- `power_iteration(matrix, max_iter, tol)` → `(vetor, convergiu, n_iter)`,
  separada para o teste unitário.
- `EigenvectorCentrality.compute` com `implementation`, `max_iter`,
  `tol`, `weight`.
- **Vetor inicial uniforme `1/n`**, não aleatório — reprodutibilidade.
- Normalização L2 a cada passo; parada quando a variação L1 cai abaixo de
  `tol · n`.
- **Ao estourar `max_iter`: `converged=False` e fallback por
  decomposição espectral.** Nunca exceção: grafo desconexo é o caso
  normal na projeção aluno↔aluno do OULAD.
- Garantir componentes não negativas (Perron-Frobenius).
- Comparação com `nx.eigenvector_centrality`.

### Fora de escopo

- PageRank, Katz e outras variantes: a Introdução cita intermediação e
  autovetor nominalmente.

## Critérios de aceite

- [x] Dado `tiny_v1`/`discipline_simple` (triângulo ponderado DA-DB = 3,
      DA-DC = DB-DC = 1), então os scores batem com a **forma fechada**:
      λ = (3+√17)/2, DA = DB ≈ 0,6571923, DC ≈ 0,3690482, com erro
      < 1e-8. É verificação de verdade — o esperado sai da álgebra, não
      da biblioteca.
- [x] Dado `synthetic_v1`/`student_simple`, os scores batem com o
      NetworkX com erro < 1e-6.
- [x] Dado um grafo desconexo e `max_iter=5`, então devolve scores para
      **todos** os nós, todos não negativos, **sem levantar exceção**.
- [x] `converged` reflete o que aconteceu, e o fallback fica registrado
      em `params`.
- [x] `validate_centrality` recusa autovetor com componente negativa.

## Testes exigidos

- **Unitários** (implementados e passando): forma fechada em `tiny_v1`;
  igualdade com o NetworkX; não-convergência vira fallback.
- Acrescentar: `power_iteration` sobre uma matriz de autovetor conhecido.

## Arquivos criados ou alterados

- `src/edugraph/centrality/eigenvector.py`.
- `tests/centrality/test_centralidades.py`.

## Impacto no artigo

**Algoritmo implementado à mão** — método na Fundamentação e tabela de
validação contra o NetworkX. Se houver fallback em alguma configuração,
vira nota de rodapé.
