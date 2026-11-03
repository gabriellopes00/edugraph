"""Rotas do laboratório e da leitura dos resultados  ``[T]``.

Duas famílias de rota, as duas fora do "somente leitura" original da
ADR-0004 (a ADR-0013 registra a mudança):

* ``POST /lab/run`` monta a rede na hora — gera a turma de demonstração
  ou amostra um dataset real, projeta, roda Louvain ou Girvan-Newman e
  devolve o grafo com o passo a passo. É limitada em tamanho (75 alunos,
  1.500 ligações no Girvan-Newman) e em tempo (60 s), para que um
  clique não trave o servidor.
* ``GET /datasets/{d}/communities/{id}/insight`` e ``…/outcomes`` leem
  uma partição que já está em disco e a explicam: nome das comunidades,
  papel dos nós, frases-resumo, desfecho por comunidade.

A API importa ``edugraph.lab``, que reúne as frentes; nunca uma frente
diretamente (ADR-0003).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from edugraph.api.projection_cache import load_projection_cached
from edugraph.contracts import io
from edugraph.contracts.errors import ArtifactNotFoundError
from edugraph.contracts.paths import ArtifactRoots
from edugraph.lab import demo
from edugraph.lab.service import (
    DEMO_SOURCE,
    MAX_EDGES_GIRVAN_NEWMAN,
    OUTCOME_LABELS,
    LabError,
    analyze,
    outcomes_for_dataset,
    run_lab,
    signal_validation_for_dataset,
)

router = APIRouter()


def _roots(request: Request) -> ArtifactRoots:
    roots: ArtifactRoots = request.app.state.roots
    return roots


# ---------------------------------------------------------------------
# Esquemas
# ---------------------------------------------------------------------


class LabRequest(BaseModel):
    """O que a tela pede ao laboratório."""

    source: str = Field(DEMO_SOURCE, description="``demo`` ou o id de um dataset com bipartido")
    students: int = Field(45, ge=demo.MIN_STUDENTS, le=demo.MAX_STUDENTS)
    seed: int = Field(12, ge=0, le=99999, description="Muda a turma sorteada")
    noise: float = Field(0.2, ge=0.0, le=1.0, description="Mistura entre áreas (só na demo)")
    side: Literal["student", "discipline"] = "student"
    weighting: Literal["simple", "resource_allocation"] = "simple"
    algorithm: Literal["louvain", "girvan_newman"] = "louvain"
    min_weight: float | None = Field(None, gt=0, description="Corta ligações mais fracas")
    time_budget_s: float = Field(20.0, ge=1.0, le=60.0)


class LabRunResponse(BaseModel):
    """A rede montada. Os blocos internos são descritos em ``frontend/src/lab.ts``."""

    model_config = ConfigDict(extra="allow")

    request: dict[str, Any]
    source: dict[str, Any]
    bipartite: dict[str, Any]
    projection: dict[str, Any]
    louvain: dict[str, Any] | None = None
    girvan_newman: dict[str, Any] | None = None
    result: dict[str, Any]
    insight: dict[str, Any]
    centrality: dict[str, dict[str, float]]
    reveal: dict[str, Any]
    timing: dict[str, float]


class LabSource(BaseModel):
    id: str
    title: str
    fictional: bool


class LabOptionsResponse(BaseModel):
    """Limites e fontes do laboratório, para montar os controles sem números fixos."""

    sources: list[LabSource]
    min_students: int
    max_students: int
    max_edges_girvan_newman: int
    areas: list[dict[str, Any]]


class InsightResponse(BaseModel):
    """Leitura de uma partição em disco."""

    dataset: str
    artifact_id: str
    communities: list[dict[str, Any]]
    roles: dict[str, dict[str, Any]]
    role_counts: dict[str, int]
    role_labels: dict[str, str]
    role_help: dict[str, str]
    summary: list[str]
    #: Risco e talentos por aluno; ``None`` nas partições de disciplinas.
    signals: dict[str, Any] | None = None


class OutcomesResponse(BaseModel):
    """Desfecho por comunidade; ``rows`` vazio quando o dataset não tem rótulos."""

    dataset: str
    artifact_id: str
    labels: dict[str, str]
    rows: list[dict[str, Any]]
    #: Os sinais de risco e talento conferidos contra o desfecho real.
    signals: dict[str, Any] | None = None


# ---------------------------------------------------------------------
# Laboratório
# ---------------------------------------------------------------------


@router.get("/lab/options", response_model=LabOptionsResponse, tags=["laboratório"])
def lab_options(request: Request) -> LabOptionsResponse:
    """Fontes disponíveis e limites do laboratório."""
    roots = _roots(request)
    sources = [
        LabSource(id=DEMO_SOURCE, title="Turma de Computação (dados fictícios)", fictional=True)
    ]
    for dataset in roots.datasets():
        if "_null" in dataset or not roots.has(dataset, "bipartite", "meta.json"):
            continue
        sources.append(LabSource(id=dataset, title=dataset, fictional=False))
    return LabOptionsResponse(
        sources=sources,
        min_students=demo.MIN_STUDENTS,
        max_students=demo.MAX_STUDENTS,
        max_edges_girvan_newman=MAX_EDGES_GIRVAN_NEWMAN,
        areas=[
            {"name": area, "disciplines": [label for _, label in modules]}
            for area, modules in demo.CURRICULUM.items()
        ],
    )


@router.post("/lab/run", response_model=LabRunResponse, tags=["laboratório"])
def lab_run(body: LabRequest, request: Request) -> LabRunResponse:
    """Monta a rede na hora e devolve o grafo com o passo a passo do algoritmo."""
    try:
        payload = run_lab(roots=_roots(request), **body.model_dump())
    except LabError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return LabRunResponse(**payload)


# ---------------------------------------------------------------------
# Leitura de partições em disco
# ---------------------------------------------------------------------

#: Resultados já lidos: carregar a projeção do AVA leva ~5 s, e a leitura
#: dela custa mais ~2 s. Guardamos só o resultado (poucos KB), não o grafo.
_CACHE_SIZE = 8
_insight_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()


def _cache_key(roots: ArtifactRoots, dataset: str, artifact_id: str) -> tuple[Any, ...]:
    path = roots.find(dataset, "communities", artifact_id, "membership.csv")
    return (tuple(str(r) for r in roots), dataset, artifact_id, path.stat().st_mtime)


def _insight_payload(roots: ArtifactRoots, dataset: str, artifact_id: str) -> dict[str, Any]:
    """A leitura de uma partição em disco, com cache (ver ``_cache_key``)."""
    key = _cache_key(roots, dataset, artifact_id)
    cached = _insight_cache.get(key)
    if cached is not None:
        _insight_cache.move_to_end(key)
        return cached

    partition = io.load_partition(roots, dataset, artifact_id)
    # Partição de amostra (``__sample<N>``) vale sobre um recorte da projeção.
    projection_id = partition.projection_id.split("__sample")[0]
    projection = load_projection_cached(roots, dataset, projection_id)
    graph = projection.graph
    if len(partition.membership) < graph.number_of_nodes():
        graph = graph.subgraph(partition.membership)

    bipartite = None
    granularity = None
    criterion = None
    try:
        bundle = io.load_bipartite(roots, dataset)
        bipartite, granularity = bundle.graph, bundle.spec.granularity
        criterion = bundle.spec.edge_criterion
    except ArtifactNotFoundError:
        pass

    reading = analyze(
        graph,
        partition.membership,
        partition.modularity,
        bipartite if projection.spec.side == "student" else None,
        granularity=granularity,
        criterion=criterion,
    )
    payload = {"dataset": dataset, "artifact_id": artifact_id, **reading}
    _insight_cache[key] = payload
    while len(_insight_cache) > _CACHE_SIZE:
        _insight_cache.popitem(last=False)
    return payload


@router.get(
    "/datasets/{dataset}/communities/{artifact_id}/insight",
    response_model=InsightResponse,
    tags=["comunidades"],
)
def get_insight(dataset: str, artifact_id: str, request: Request) -> InsightResponse:
    """Nome das comunidades, papel dos nós, sinais por aluno e frases-resumo."""
    return InsightResponse(**_insight_payload(_roots(request), dataset, artifact_id))


@router.get(
    "/datasets/{dataset}/communities/{artifact_id}/outcomes",
    response_model=OutcomesResponse,
    tags=["comunidades"],
)
def get_outcomes(dataset: str, artifact_id: str, request: Request) -> OutcomesResponse:
    """Desfecho (aprovado, reprovado…) por comunidade — a revelação a posteriori.

    O grafo nunca viu estes rótulos (ADR-0008): eles só são cruzados com a
    partição **depois** de pronta.
    """
    roots = _roots(request)
    partition = io.load_partition(roots, dataset, artifact_id)
    rows = outcomes_for_dataset(roots, dataset, partition)
    validation = None
    if rows:
        reading = _insight_payload(roots, dataset, artifact_id)
        validation = signal_validation_for_dataset(roots, dataset, reading.get("signals"))
    return OutcomesResponse(
        dataset=dataset,
        artifact_id=artifact_id,
        labels=OUTCOME_LABELS,
        rows=rows,
        signals=validation,
    )
