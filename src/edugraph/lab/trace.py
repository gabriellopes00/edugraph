"""Louvain e Girvan-Newman com rastro do passo a passo  ``[T]``.

A tela do laboratório anima o que o algoritmo fez: no Louvain, cada troca
de comunidade; no Girvan-Newman, a ordem das arestas removidas e o Q em
cada corte. Os algoritmos registrados (``community.louvain`` e
``community.girvan_newman``) devolvem só o resultado final; aqui o
cálculo roda guardando o caminho.

* **Girvan-Newman:** é o mesmo cálculo do registrado (mesma biblioteca,
  mesma regra de desempate), e um teste confere que a partição final é
  idêntica.
* **Louvain:** é uma implementação própria, porque a biblioteca não expõe
  os movimentos. Um teste confere que o Q dela fica a menos de 0,02 do
  ``python-louvain`` e que ela recupera as áreas plantadas quando não há
  ruído; a tela mostra os dois Q lado a lado.

O Q sai sempre da implementação à mão (``community.modularity``, spec
B-03), como nas tabelas do artigo.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from edugraph.community.modularity import membership_of, modularity

#: Orçamento padrão do Girvan-Newman ao vivo, em segundos.
DEFAULT_BUDGET_S = 20.0

#: Cortes com no máximo tantas comunidades levam o ``membership`` completo
#: na resposta; acima disso só o Q (a curva) — o resto não é desenhado.
MAX_K_WITH_MEMBERSHIP = 14


# ---------------------------------------------------------------------
# Louvain
# ---------------------------------------------------------------------


@dataclass
class Move:
    """Um movimento do Louvain: nós que trocam de comunidade."""

    #: Índices (em ``LouvainTrace.nodes``) dos nós que se movem; mais de um
    #: quando o movimento é de uma comunidade inteira, acima do primeiro nível.
    members: list[int]
    #: Id da comunidade de destino: o índice do primeiro nó que a formou.
    to: int
    #: Q do grafo inteiro logo depois deste movimento.
    q: float
    level: int


@dataclass
class LevelEnd:
    """Fim de um nível: as fusões daquele nível já foram feitas."""

    level: int
    #: Quantos movimentos (de ``LouvainTrace.moves``) existem até aqui.
    n_moves: int
    q: float
    n_communities: int


@dataclass
class LouvainTrace:
    #: Ordem dos nós; no começo, o nó ``i`` está sozinho na comunidade ``i``.
    nodes: list[str]
    moves: list[Move]
    levels: list[LevelEnd]
    membership: dict[str, int]
    q: float
    runtime_s: float


def louvain_trace(
    graph: nx.Graph[Any],
    *,
    seed: int = 42,
    resolution: float = 1.0,
    weight: str | None = "weight",
    max_levels: int = 10,
) -> LouvainTrace:
    """Louvain (Blondel et al., 2008) guardando cada movimento.

    A biblioteca ``python-louvain`` devolve só a hierarquia pronta (em
    redes pequenas, dois níveis: cada nó sozinho e o resultado), e não há
    o que animar. Aqui o algoritmo é escrito de modo que cada troca de
    comunidade seja um evento:

    1. **Movimento local.** Cada nó, numa ordem sorteada pela semente,
       vai para a comunidade vizinha que mais aumenta Q, se aumentar;
       repete até ninguém mais se mover.
    2. **Agregação.** Cada comunidade vira um nó e o passo 1 recomeça.
       Para quando um nível inteiro passa sem mover ninguém.

    O ganho de Q ao inserir o nó ``i`` na comunidade ``c`` é, a menos de
    constante, ``w_ic − γ · tot_c · k_i / 2m``.
    """
    start = time.perf_counter()
    attr = weight or "weight"
    nodes = sorted(graph.nodes)
    n = len(nodes)
    index = {node: i for i, node in enumerate(nodes)}

    adjacency: list[dict[int, float]] = [{} for _ in range(n)]
    for u, v, w in graph.edges(data=attr, default=1.0):
        if u == v:
            continue
        iu, iv = index[u], index[v]
        adjacency[iu][iv] = adjacency[iu].get(iv, 0.0) + float(w)
        adjacency[iv][iu] = adjacency[iv].get(iu, 0.0) + float(w)

    strength = [sum(a.values()) for a in adjacency]
    two_m = sum(strength)
    if two_m == 0:
        singleton = {node: i for i, node in enumerate(nodes)}
        return LouvainTrace(nodes, [], [], singleton, 0.0, time.perf_counter() - start)
    m = two_m / 2

    rng = random.Random(seed)
    moves: list[Move] = []
    levels: list[LevelEnd] = []

    # Estado do nível: cada super-nó tem membros originais, força, laço
    # (peso interno já agregado) e o id de exibição da sua comunidade.
    members: list[list[int]] = [[i] for i in range(n)]
    loops = [0.0] * n
    ids = list(range(n))
    adj = adjacency
    k = strength
    original_comm = list(range(n))

    for level in range(1, max_levels + 1):
        size = len(members)
        comm = list(range(size))
        total = k[:]
        inside = loops[:]

        def current_q(total: list[float] = total, inside: list[float] = inside) -> float:
            return sum(
                inside[c] / m - resolution * (total[c] / two_m) ** 2
                for c in range(len(total))
                if total[c] > 0
            )

        moved_in_level = 0
        while True:
            moved = 0
            order = list(range(size))
            rng.shuffle(order)
            for s in order:
                old = comm[s]
                weights: dict[int, float] = {}
                for t, w in adj[s].items():
                    weights[comm[t]] = weights.get(comm[t], 0.0) + w
                total[old] -= k[s]
                w_old = weights.get(old, 0.0)
                best, best_gain = old, w_old - resolution * total[old] * k[s] / two_m
                for c in sorted(weights):
                    if c == old:
                        continue
                    gain = weights[c] - resolution * total[c] * k[s] / two_m
                    if gain > best_gain + 1e-12:
                        best, best_gain = c, gain
                total[best] += k[s]
                if best != old:
                    inside[old] -= w_old + loops[s]
                    inside[best] += weights.get(best, 0.0) + loops[s]
                    comm[s] = best
                    moved += 1
                    moves.append(Move(list(members[s]), ids[best], current_q(), level))
            moved_in_level += moved
            if moved == 0:
                break
        if moved_in_level == 0:
            break

        # Agregação: cada comunidade vira um super-nó.
        groups: dict[int, list[int]] = {}
        for s, c in enumerate(comm):
            groups.setdefault(c, []).append(s)
        new_index = {c: i for i, c in enumerate(sorted(groups))}
        new_members: list[list[int]] = []
        new_ids: list[int] = []
        new_loops: list[float] = []
        new_k: list[float] = []
        for c in sorted(groups):
            joined = [orig for s in groups[c] for orig in members[s]]
            new_members.append(joined)
            new_ids.append(ids[c])
            new_loops.append(inside[c])
            new_k.append(total[c])
            for orig in joined:
                original_comm[orig] = ids[c]
        new_adj: list[dict[int, float]] = [{} for _ in new_members]
        for s, neighbours in enumerate(adj):
            cs = new_index[comm[s]]
            for t, w in neighbours.items():
                ct = new_index[comm[t]]
                if cs != ct:
                    new_adj[cs][ct] = new_adj[cs].get(ct, 0.0) + w
        members, loops, ids, adj, k = new_members, new_loops, new_ids, new_adj, new_k

        level_membership = {nodes[i]: original_comm[i] for i in range(n)}
        levels.append(
            LevelEnd(
                level=level,
                n_moves=len(moves),
                q=modularity(graph, level_membership, weight=weight, resolution=resolution),
                n_communities=len(set(original_comm)),
            )
        )

    membership = {nodes[i]: original_comm[i] for i in range(n)}
    runtime = time.perf_counter() - start
    return LouvainTrace(
        nodes=nodes,
        moves=moves,
        levels=levels,
        membership=membership,
        q=modularity(graph, membership, weight=weight, resolution=resolution),
        runtime_s=runtime,
    )


# ---------------------------------------------------------------------
# Girvan-Newman
# ---------------------------------------------------------------------


@dataclass
class Split:
    """Um corte do dendrograma do Girvan-Newman."""

    k: int
    q: float
    #: Quantas arestas já tinham sido removidas quando este corte apareceu.
    n_removed: int
    membership: dict[str, int] | None


@dataclass
class GirvanNewmanTrace:
    splits: list[Split]
    #: Todas as arestas removidas, na ordem (pares de ids de nó).
    removed: list[tuple[str, str]]
    #: Índice (em ``splits``) do corte de maior Q; -1 se não houve corte.
    best: int
    membership: dict[str, int]
    q: float
    runtime_s: float
    status: str = "ok"
    stop_reason: str = "dendrogram_exhausted"
    extra: dict[str, Any] = field(default_factory=dict)


class _BudgetExceededError(Exception):
    """Sinal interno: o orçamento acabou no meio de um corte."""


def girvan_newman_trace(
    graph: nx.Graph[Any],
    *,
    time_budget_s: float = DEFAULT_BUDGET_S,
    weight: str | None = "weight",
) -> GirvanNewmanTrace:
    """Roda o Girvan-Newman guardando as arestas removidas e o Q de cada corte.

    A aresta removida é a de maior intermediação **sem peso**, com
    desempate pelo id — a mesma regra de ``community.girvan_newman``
    (ADR-0006). O Q usa o peso. A melhor partição é a de maior Q, com
    empate no corte mais raso.
    """
    removed: list[tuple[str, str]] = []
    start = time.perf_counter()
    deadline = start + time_budget_s

    def most_valuable_edge(g: nx.Graph[Any]) -> tuple[Any, Any]:
        if time.perf_counter() > deadline:
            raise _BudgetExceededError
        betweenness = nx.edge_betweenness_centrality(g, weight=None)
        edge = min(betweenness, key=lambda e: (-betweenness[e], e))
        removed.append((str(edge[0]), str(edge[1])))
        return edge  # type: ignore[no-any-return]

    if graph.number_of_edges() == 0:
        return GirvanNewmanTrace(
            splits=[],
            removed=[],
            best=-1,
            membership=_components(graph),
            q=0.0,
            runtime_s=0.0,
            stop_reason="no_edges",
        )

    splits: list[Split] = []
    best_index = -1
    best_q = -math.inf
    best_membership: dict[str, int] = {}
    status = "ok"
    stop_reason = "dendrogram_exhausted"

    try:
        for communities in nx.community.girvan_newman(graph, most_valuable_edge=most_valuable_edge):
            membership = membership_of([sorted(c) for c in communities])
            q = modularity(graph, membership, weight=weight)
            k = len(communities)
            splits.append(
                Split(
                    k=k,
                    q=q,
                    n_removed=len(removed),
                    membership=membership if k <= MAX_K_WITH_MEMBERSHIP else None,
                )
            )
            if q > best_q:
                best_q, best_index, best_membership = q, len(splits) - 1, membership
                # O melhor corte leva o membership mesmo com k grande.
                splits[-1].membership = membership
            if time.perf_counter() > deadline:
                status, stop_reason = "timeout", "time_budget"
                break
            if k >= graph.number_of_nodes():
                break
    except _BudgetExceededError:
        status, stop_reason = ("timeout" if splits else "skipped"), "time_budget"

    runtime = time.perf_counter() - start
    if not splits:
        best_membership, best_q = _components(graph), 0.0
    return GirvanNewmanTrace(
        splits=splits,
        removed=removed,
        best=best_index,
        membership=best_membership,
        q=best_q,
        runtime_s=runtime,
        status=status,
        stop_reason=stop_reason,
    )


def _components(graph: nx.Graph[Any]) -> dict[str, int]:
    return membership_of([sorted(c) for c in nx.connected_components(graph)])
