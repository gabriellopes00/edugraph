"""Rotas da API  ``[C]``.

``/health`` e ``/datasets`` vieram prontas no dia 0; as rotas de dados
são a **spec C-04**. Nenhuma calcula nada: todas leem artefatos pelo
``contracts.io`` (ADR-0004), e por isso a API não importa
``edugraph.data``, ``edugraph.community`` nem ``edugraph.centrality``.

Toda rota lê de :class:`~edugraph.contracts.paths.ArtifactRoots` e
devolve 404 com a lista de raízes consultadas quando não encontra — o
engano mais comum em desenvolvimento é esquecer o ``--root``.
"""

from __future__ import annotations

import heapq
from typing import Annotated, Any, Literal, get_args

import networkx as nx
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request

from edugraph import __version__
from edugraph.api.projection_cache import load_projection_cached, remember
from edugraph.api.schemas import (
    CentralityResponse,
    DatasetListResponse,
    DatasetSummary,
    EdgeOut,
    GraphResponse,
    HealthResponse,
    MetricsResponse,
    NodeOut,
    PartitionResponse,
    TruncationInfo,
)
from edugraph.contracts import io
from edugraph.contracts.errors import ArtifactNotFoundError
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.types import SCHEMA_VERSION, CentralityMetricName

router = APIRouter()

#: As três métricas do contrato, na ordem das tabelas.
CENTRALITY_METRICS: tuple[str, ...] = get_args(CentralityMetricName)


def _roots(request: Request) -> ArtifactRoots:
    """Raízes configuradas na criação da aplicação."""
    roots: ArtifactRoots = request.app.state.roots
    return roots


# ---------------------------------------------------------------------
# Dia 0 — prontas
# ---------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health(request: Request) -> HealthResponse:
    """Diz que a API está de pé e sobre que raízes ela está olhando."""
    roots = _roots(request)
    return HealthResponse(
        version=__version__,
        schema_version=SCHEMA_VERSION,
        roots=[str(r) for r in roots],
    )


@router.get("/datasets", response_model=DatasetListResponse, tags=["meta"])
def list_datasets(request: Request) -> DatasetListResponse:
    """Lista os datasets visíveis e o que cada um já tem calculado.

    É o que permite ao front-end montar os seletores sem conhecer
    antecipadamente nenhum nome de dataset ou de projeção.
    """
    roots = _roots(request)
    summaries = [
        DatasetSummary(
            dataset=dataset,
            has_bipartite=roots.has(dataset, "bipartite", "meta.json"),
            projections=roots.projections(dataset),
            partitions=roots.partitions(dataset),
            centralities=roots.centralities(dataset),
        )
        for dataset in roots.datasets()
    ]
    return DatasetListResponse(datasets=summaries)


# ---------------------------------------------------------------------
# Spec C-04 — rotas de dados
# ---------------------------------------------------------------------

#: Arestas por resposta quando o cliente não pede outro limite. O front
#: avisa a partir de 3.000 (``MAX_EDGES_CONFORTAVEL``); 5.000 deixa folga
#: para o aviso aparecer antes do corte.
DEFAULT_MAX_EDGES = 5000

#: Teto que nem o cliente pode passar: acima disto a transferência já
#: custa mais do que qualquer interface consegue mostrar.
HARD_MAX_EDGES = 50_000


EdgeCut = Literal["backbone", "top_weight"]


def _top_weight(
    edges: list[tuple[str, str, float]], max_edges: int
) -> list[tuple[str, str, float]]:
    """As ``max_edges`` arestas de maior peso do grafo inteiro."""
    return heapq.nsmallest(max_edges, edges, key=lambda e: (-e[2], e[0], e[1]))


def _backbone(
    edges: list[tuple[str, str, float]], max_edges: int
) -> tuple[list[tuple[str, str, float]], int]:
    """Esqueleto: as ``k`` arestas mais fortes de **cada nó**, com o maior ``k`` que cabe.

    O corte global por peso concentra as arestas em poucos nós muito
    ligados e deixa o resto solto — no AVA do OULAD, as 5.000 mais pesadas
    tocam uma fração pequena dos 1.870 alunos. Aqui cada aresta recebe o
    posto dela na vizinhança de cada ponta (0 = a mais forte daquele nó),
    fica com o menor dos dois, e entram todas as de posto menor que ``k``.
    Assim todo nó que tinha vizinho continua com pelo menos um.

    Se nem ``k = 1`` couber, fica com as de posto 0 de maior peso e devolve
    ``k = 0``: aí nem todo nó conserva um vizinho, e a resposta diz isso.
    Desempates por id: a mesma requisição devolve o mesmo subconjunto.
    """
    ids = sorted({n for u, v, _ in edges for n in (u, v)})
    index = {node: i for i, node in enumerate(ids)}
    u = np.array([index[e[0]] for e in edges], dtype=np.int64)
    v = np.array([index[e[1]] for e in edges], dtype=np.int64)
    w = np.array([e[2] for e in edges], dtype=float)

    # Cada aresta aparece duas vezes, uma por ponta; ordena por (nó, −peso, vizinho).
    node = np.concatenate([u, v])
    other = np.concatenate([v, u])
    weight = np.concatenate([w, w])
    edge_id = np.concatenate([np.arange(len(edges)), np.arange(len(edges))])
    order = np.lexsort((other, -weight, node))
    sorted_node = node[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_node)) + 1]
    group_start = np.repeat(starts, np.diff(np.r_[starts, len(sorted_node)]))
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(len(order)) - group_start

    edge_rank = np.full(len(edges), np.iinfo(np.int64).max)
    np.minimum.at(edge_rank, edge_id, rank)

    counts = np.bincount(edge_rank)
    cumulative = np.cumsum(counts)  # cumulative[k-1] = arestas com posto < k
    fits = np.flatnonzero(cumulative <= max_edges)
    if fits.size == 0:
        # Nem uma aresta por nó cabe: ficam as mais pesadas entre as
        # "melhores de cada nó", e k = 0 diz que a garantia não vale.
        firsts = [edges[i] for i in np.flatnonzero(edge_rank == 0)]
        return _top_weight(firsts, max_edges), 0
    k = int(fits[-1]) + 1
    return [edges[i] for i in np.flatnonzero(edge_rank < k)], k


def _graph_payload(
    graph: nx.Graph[Any], max_edges: int, cut: EdgeCut = "backbone"
) -> tuple[list[NodeOut], list[EdgeOut], TruncationInfo]:
    """Nós, arestas (cortadas se passarem do limite) e a declaração do corte.

    Os nós nunca são cortados: são eles que carregam comunidade e
    centralidade. Ver :func:`_backbone` e :func:`_top_weight`.
    """
    nodes = [
        NodeOut(id=str(n), kind=data["kind"], label=str(data.get("label", n)))
        for n, data in sorted(graph.nodes(data=True), key=lambda item: str(item[0]))
    ]
    edges: list[tuple[str, str, float]] = []
    for a_node, b_node, data in graph.edges(data=True):
        a, b = sorted((str(a_node), str(b_node)))
        edges.append((a, b, float(data["weight"])))
    total = len(edges)
    truncated = total > max_edges
    k: int | None = None
    if truncated:
        if cut == "backbone":
            edges, k = _backbone(edges, max_edges)
        else:
            edges = _top_weight(edges, max_edges)
    edges.sort(key=lambda e: (e[0], e[1]))

    info = TruncationInfo(
        truncated=truncated,
        max_edges=max_edges,
        n_nodes=len(nodes),
        n_edges_total=total,
        n_edges_returned=len(edges),
        criterion=cut,
        k_per_node=k,
    )
    return nodes, [EdgeOut(source=a, target=b, weight=w) for a, b, w in edges], info


Cut = Annotated[
    EdgeCut,
    Query(
        description=(
            "Como cortar acima de max_edges: backbone (as k mais fortes de cada nó) "
            "ou top_weight (as mais pesadas do grafo inteiro)"
        )
    ),
]


def _split_metrics(metrics: list[str] | None) -> list[str]:
    """Aceita ``?metrics=a,b`` e ``?metrics=a&metrics=b``, sem repetir."""
    names: list[str] = []
    for chunk in metrics or []:
        for raw in chunk.split(","):
            name = raw.strip()
            if not name:
                continue
            if name not in CENTRALITY_METRICS:
                raise HTTPException(
                    status_code=422,
                    detail=f"métrica {name!r} não existe; use {', '.join(CENTRALITY_METRICS)}",
                )
            if name not in names:
                names.append(name)
    return names


def _number(value: str) -> str | int | float:
    """Converte a célula do CSV em número quando ela é um."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


MaxEdges = Annotated[
    int,
    Query(
        ge=1,
        le=HARD_MAX_EDGES,
        description="Arestas por resposta; acima disso, a resposta é cortada (ver cut)",
    ),
]


@router.get(
    "/datasets/{dataset}/projections/{projection_id}",
    response_model=GraphResponse,
    tags=["grafo"],
)
def get_projection(
    dataset: str,
    projection_id: str,
    request: Request,
    partition: Annotated[
        str | None, Query(description="Partição a embutir: <algoritmo>__<projection_id>")
    ] = None,
    metrics: Annotated[
        list[str] | None, Query(description="Centralidades a embutir, separadas por vírgula")
    ] = None,
    max_edges: MaxEdges = DEFAULT_MAX_EDGES,
    cut: Cut = "backbone",
) -> GraphResponse:
    """Grafo da projeção, opcionalmente com comunidade e centralidade.

    ``partition`` e ``metrics`` embutem a partição e as centralidades na
    mesma resposta, para o front colorir e dimensionar sem uma segunda
    requisição. São leituras do disco, não cálculo (ADR-0004).
    """
    roots = _roots(request)
    names = _split_metrics(metrics)
    projection = load_projection_cached(roots, dataset, projection_id)
    nodes, edges, truncation = remember(
        projection,
        ("payload", max_edges, cut),
        lambda: _graph_payload(projection.graph, max_edges, cut),
    )

    community = None
    if partition:
        loaded = io.load_partition(roots, dataset, partition)
        if loaded.projection_id != projection_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"a partição {partition!r} é da projeção {loaded.projection_id!r}, "
                    f"não de {projection_id!r}"
                ),
            )
        community = loaded.membership

    centrality = None
    if names:
        centrality = {
            name: io.load_centrality(roots, dataset, projection_id, name).scores  # type: ignore[arg-type]
            for name in names
        }

    return GraphResponse(
        dataset=dataset,
        projection_id=projection_id,
        spec=projection.spec.to_dict(),
        nodes=nodes,
        edges=edges,
        truncation=truncation,
        community=community,
        centrality=centrality,
    )


@router.get(
    "/datasets/{dataset}/bipartite",
    response_model=GraphResponse,
    tags=["grafo"],
)
def get_bipartite(
    dataset: str,
    request: Request,
    max_edges: MaxEdges = DEFAULT_MAX_EDGES,
    cut: Cut = "backbone",
) -> GraphResponse:
    """Grafo bipartido do dataset.

    ``projection_id`` vem como ``"bipartite"``: o front usa a mesma forma
    de resposta para as duas vistas.
    """
    bipartite = io.load_bipartite(_roots(request), dataset)
    nodes, edges, truncation = _graph_payload(bipartite.graph, max_edges, cut)
    return GraphResponse(
        dataset=dataset,
        projection_id="bipartite",
        spec=bipartite.spec.to_dict(),
        nodes=nodes,
        edges=edges,
        truncation=truncation,
    )


@router.get(
    "/datasets/{dataset}/communities/{artifact_id}",
    response_model=PartitionResponse,
    tags=["comunidades"],
)
def get_partition(dataset: str, artifact_id: str, request: Request) -> PartitionResponse:
    """Uma partição, com Q, k, tempo e status."""
    partition = io.load_partition(_roots(request), dataset, artifact_id)
    return PartitionResponse(
        dataset=dataset,
        algorithm=partition.algorithm,
        projection_id=partition.projection_id,
        modularity=partition.modularity,
        n_communities=partition.n_communities,
        runtime_s=partition.runtime_s,
        status=partition.status,
        params=partition.params,
        membership=partition.membership,
    )


@router.get(
    "/datasets/{dataset}/centrality/{projection_id}/{metric}",
    response_model=CentralityResponse,
    tags=["centralidade"],
)
def get_centrality(
    dataset: str,
    projection_id: str,
    metric: CentralityMetricName,
    request: Request,
    top: Annotated[
        int | None, Query(ge=1, description="Só os N primeiros; padrão: o ranking inteiro")
    ] = None,
) -> CentralityResponse:
    """Ranking de uma métrica de centralidade sobre uma projeção.

    Ordenado do maior para o menor, com desempate por id — o mesmo de
    ``CentralityResult.top``, para que a API e as tabelas concordem.
    """
    result = io.load_centrality(_roots(request), dataset, projection_id, metric)
    return CentralityResponse(
        dataset=dataset,
        projection_id=projection_id,
        metric=metric,
        converged=result.converged,
        runtime_s=result.runtime_s,
        params=result.params,
        ranking=result.top(top or len(result.scores)),
    )


@router.get(
    "/datasets/{dataset}/metrics/{name}",
    response_model=MetricsResponse,
    tags=["métricas"],
)
def get_metrics(dataset: str, name: str, request: Request) -> MetricsResponse:
    """Tabela de ``metrics/<name>.csv`` como JSON.

    É por aqui que o front mostra a comparação Louvain × Girvan-Newman
    sem recalcular nada. As células numéricas chegam como número.
    """
    rows = io.load_metrics(_roots(request), dataset, name)
    return MetricsResponse(
        dataset=dataset,
        name=name,
        rows=[{column: _number(value) for column, value in row.items()} for row in rows],
    )


# ---------------------------------------------------------------------
# Tradução de erro de contrato em 404
# ---------------------------------------------------------------------


def not_found(error: ArtifactNotFoundError) -> HTTPException:
    """Converte a ausência de artefato em 404 com a mensagem do contrato."""
    return HTTPException(status_code=404, detail=str(error))
