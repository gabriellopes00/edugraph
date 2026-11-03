"""Serviço do laboratório  ``[T]`` — de uma requisição a um grafo montado.

``run_lab`` faz, na hora e com o algoritmo de verdade, o que a tela vai
animar: gera a turma (ou amostra um dataset real), projeta, roda Louvain
ou Girvan-Newman guardando o passo a passo, e lê o resultado em
linguagem de gente. ``analyze`` é a parte de leitura, reaproveitada pela
API para os datasets já calculados em disco.

Rótulos históricos: o desfecho só é lido por ``community.evaluate``
(ADR-0008); aqui chamamos as funções dele, nunca ``load_outcomes``.
"""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

import networkx as nx
import numpy as np

from edugraph.community.evaluate import (
    load_labels,
    normalized_mutual_information,
    outcome_profile,
    outcomes_by_group,
    purity,
    rank_auc,
)
from edugraph.contracts import io
from edugraph.contracts.errors import ArtifactNotFoundError
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.registry import (
    CENTRALITIES,
    COMMUNITIES,
    PROJECTIONS,
    load_builtin_implementations,
)
from edugraph.contracts.types import (
    BipartiteBundle,
    Meta,
    Outcomes,
    Partition,
    ProjectionBundle,
    ProjectionSpec,
)
from edugraph.data.scale import prune_by_weight, sample_students
from edugraph.lab import demo, insight, signals
from edugraph.lab.trace import (
    GirvanNewmanTrace,
    LouvainTrace,
    girvan_newman_trace,
    louvain_trace,
)

#: ``source`` que pede a turma gerada na hora.
DEMO_SOURCE = "demo"

#: Projeções maiores que isto não cabem na tela nem no orçamento do laboratório.
MAX_NODES = 150
#: O Girvan-Newman recalcula a intermediação a cada aresta removida.
MAX_EDGES_GIRVAN_NEWMAN = 1500
MAX_EDGES = 4000
#: Acima disto a projeção é uma bola de linhas; o laboratório sugere um corte.
SUGGEST_CUT_ABOVE_EDGES = 450

OUTCOME_LABELS: dict[str, str] = {
    "Distinction": "Com distinção",
    "Pass": "Aprovados",
    "Fail": "Reprovados",
    "Withdrawn": "Desistentes",
}


class LabError(Exception):
    """Pedido que o laboratório não consegue atender (vira HTTP 422)."""


# ---------------------------------------------------------------------
# Leitura do resultado (também usada pela API para datasets em disco)
# ---------------------------------------------------------------------


def analyze(
    graph: nx.Graph[Any],
    membership: dict[str, int],
    q: float,
    bipartite: nx.Graph[Any] | None = None,
    *,
    granularity: str | None = None,
    criterion: str | None = None,
) -> dict[str, Any]:
    """Nomes das comunidades, papéis dos nós, sinais por aluno e frases-resumo."""
    communities = insight.name_communities(graph, membership, bipartite, granularity=granularity)
    roles = insight.node_roles(graph, membership)
    student_signals = (
        signals.student_signals(
            graph, bipartite, membership, roles, criterion=criterion, granularity=granularity
        )
        if bipartite is not None
        else {}
    )
    counts: dict[str, int] = dict.fromkeys(insight.ROLE_LABELS, 0)
    for info in roles.values():
        counts[info.role] += 1
    return {
        "communities": [asdict(c) for c in communities],
        "roles": {
            node: {"role": r.role, "z": round(r.z, 3), "p": round(r.p, 3)}
            for node, r in roles.items()
        },
        "role_counts": counts,
        "role_labels": insight.ROLE_LABELS,
        "role_help": insight.ROLE_HELP,
        "signals": student_signals or None,
        "summary": insight.summarize(graph, q, communities, roles, student_signals or None),
    }


def outcome_rows(partition: Partition, outcomes: Outcomes) -> list[dict[str, Any]]:
    """Desfecho por comunidade, em taxas, para a revelação da tela."""
    rows = outcome_profile(partition, outcomes)
    out = []
    for row in rows:
        labeled = int(row["n_labeled"])
        out.append(
            {
                "community": int(row["community"]),
                "size": int(row["size"]),
                "n_labeled": labeled,
                "rates": {k: float(row[f"rate_{k}"]) for k in OUTCOME_LABELS},
                "base_rates": {k: float(row[f"base_rate_{k}"]) for k in OUTCOME_LABELS},
                "counts": {k: int(row[f"n_{k}"]) for k in OUTCOME_LABELS},
            }
        )
    return out


def signal_validation(student_signals: dict[str, Any], outcomes: Outcomes) -> dict[str, Any] | None:
    """Confere os sinais contra o desfecho real — a revelação a posteriori.

    Os sinais foram calculados sem olhar ``outcomes`` (ADR-0008); aqui se
    pergunta se quem foi sinalizado de fato reprovou ou desistiu mais, e se
    os talentos foram mais aprovados.
    """
    entries: dict[str, dict[str, Any]] = student_signals.get("students", {})
    if not entries:
        return None
    risk = outcomes_by_group({s: e["tier"] for s, e in entries.items()}, outcomes)
    talent = outcomes_by_group(
        {s: "talento" if e["talent"] else "demais" for s, e in entries.items()}, outcomes
    )
    if not risk["base"]["n_labeled"]:
        return None
    scores = {s: float(e["risk"]) for s, e in entries.items()}
    return {
        "risk": risk,
        "talent": talent,
        "auc_negative": rank_auc(scores, outcomes, ("Fail", "Withdrawn")),
        "auc_withdrawn": rank_auc(scores, outcomes, ("Withdrawn",)),
    }


def signal_validation_for_dataset(
    roots: ArtifactRoots, dataset: str, student_signals: dict[str, Any] | None
) -> dict[str, Any] | None:
    """:func:`signal_validation` sobre o ``outcomes.csv`` de um dataset em disco."""
    if not student_signals:
        return None
    try:
        outcomes = load_labels(roots, dataset)
    except ArtifactNotFoundError:
        return None
    return signal_validation(student_signals, outcomes)


def outcomes_for_dataset(
    roots: ArtifactRoots, dataset: str, partition: Partition
) -> list[dict[str, Any]]:
    """Desfecho por comunidade de uma partição em disco; vazio sem ``outcomes.csv``."""
    try:
        outcomes = load_labels(roots, dataset)
    except ArtifactNotFoundError:
        return []
    rows = outcome_rows(partition, outcomes)
    return rows if any(r["n_labeled"] for r in rows) else []


# ---------------------------------------------------------------------
# Passos da montagem
# ---------------------------------------------------------------------


def _bipartite_payload(bundle: BipartiteBundle) -> dict[str, Any]:
    graph = bundle.graph
    students = sorted(bundle.students)
    disciplines = sorted(bundle.disciplines)
    edges = []
    for u, v, w in graph.edges(data="weight", default=1.0):
        student, discipline = (u, v) if graph.nodes[u].get("kind") == "student" else (v, u)
        edges.append([student, discipline, round(float(w), 2)])
    edges.sort()
    return {
        "students": [{"id": s, "label": graph.nodes[s].get("label", s)} for s in students],
        "disciplines": [{"id": d, "label": graph.nodes[d].get("label", d)} for d in disciplines],
        "edges": edges,
    }


def _project(bundle: BipartiteBundle, side: str, weighting: str) -> ProjectionBundle:
    load_builtin_implementations()
    algorithm: Any = PROJECTIONS.get(f"manual_{weighting}")
    spec = ProjectionSpec(side=side, weighting=weighting)  # type: ignore[arg-type]
    return algorithm.project(bundle, spec)  # type: ignore[no-any-return]


def _centralities(projection: ProjectionBundle) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name in ("degree", "betweenness", "eigenvector"):
        try:
            metric: Any = CENTRALITIES.get(name)
            out[name] = {n: float(v) for n, v in metric.compute(projection).scores.items()}
        except Exception:
            continue
    return out


def _louvain_payload(trace: LouvainTrace, reference: Partition) -> dict[str, Any]:
    ours = {
        frozenset(n for n, c in trace.membership.items() if c == k)
        for k in set(trace.membership.values())
    }
    theirs = {frozenset(g) for g in reference.groups().values()}
    return {
        "nodes": trace.nodes,
        "moves": [
            {"members": m.members, "to": m.to, "q": round(m.q, 5), "level": m.level}
            for m in trace.moves
        ],
        "levels": [
            {
                "level": lv.level,
                "n_moves": lv.n_moves,
                "q": round(lv.q, 5),
                "n_communities": lv.n_communities,
            }
            for lv in trace.levels
        ],
        "reference": {
            "library": "python-louvain",
            "q": round(reference.modularity, 5),
            "n_communities": reference.n_communities,
            "same_partition": ours == theirs,
        },
    }


def _girvan_newman_payload(trace: GirvanNewmanTrace, nodes: list[str]) -> dict[str, Any]:
    index = {n: i for i, n in enumerate(nodes)}
    return {
        "nodes": nodes,
        "removed": [[index[u], index[v]] for u, v in trace.removed],
        "splits": [
            {"k": s.k, "q": round(s.q, 5), "n_removed": s.n_removed, "membership": s.membership}
            for s in trace.splits
        ],
        "best": trace.best,
        "stop_reason": trace.stop_reason,
    }


# ---------------------------------------------------------------------
# A requisição inteira
# ---------------------------------------------------------------------


def _load_source(
    source: str, students: int, seed: int, noise: float, roots: ArtifactRoots
) -> tuple[BipartiteBundle, Outcomes | None, demo.DemoData | None, dict[str, Any]]:
    if source == DEMO_SOURCE:
        data = demo.build_demo(students, seed, noise)
        info = {
            "id": demo.DEMO_DATASET,
            "title": "Turma de Computação (dados fictícios)",
            "fictional": True,
        }
        return data.bipartite, data.outcomes, data, info
    try:
        full = io.load_bipartite(roots, source)
    except ArtifactNotFoundError as error:
        raise LabError(f"dataset {source!r} não tem bipartido em disco: {error}") from error
    bundle = sample_students(full, students, seed=seed)
    try:
        outcomes: Outcomes | None = load_labels(roots, source)
    except ArtifactNotFoundError:
        outcomes = None
    info = {
        "id": source,
        "title": f"{source} (amostra de {students} alunos)",
        "fictional": False,
    }
    return bundle, outcomes, None, info


def run_lab(
    *,
    roots: ArtifactRoots,
    source: str = DEMO_SOURCE,
    students: int = 45,
    seed: int = 7,
    noise: float = 0.35,
    side: str = "student",
    weighting: str = "simple",
    algorithm: str = "louvain",
    min_weight: float | None = None,
    time_budget_s: float = 20.0,
) -> dict[str, Any]:
    """Monta a rede, roda o algoritmo e devolve tudo o que a tela anima."""
    started = time.perf_counter()
    try:
        bundle, outcomes, demo_data, source_info = _load_source(
            source, students, seed, noise, roots
        )
    except ValueError as error:
        raise LabError(str(error)) from error

    full_projection = _project(bundle, side, weighting)
    weights = [float(w) for _, _, w in full_projection.graph.edges(data="weight")]
    weight_range = [min(weights), max(weights)] if weights else [0.0, 0.0]
    # Rede quase completa (o AVA real): sugere manter só as ~30% mais fortes.
    suggested_cut = (
        round(float(np.percentile(weights, 70)), 2)
        if len(weights) > SUGGEST_CUT_ABOVE_EDGES and weight_range[1] > weight_range[0]
        else None
    )
    projection = prune_by_weight(full_projection, min_weight) if min_weight else full_projection
    graph = projection.graph

    if graph.number_of_nodes() > MAX_NODES:
        raise LabError(
            f"a projeção tem {graph.number_of_nodes()} nós; o laboratório aceita até {MAX_NODES}. "
            "Reduza o número de alunos ou projete os alunos."
        )
    if graph.number_of_edges() > MAX_EDGES:
        raise LabError(
            f"a projeção tem {graph.number_of_edges()} ligações; o laboratório aceita até "
            f"{MAX_EDGES}. Aumente o peso mínimo da ligação."
        )
    if algorithm == "girvan_newman" and graph.number_of_edges() > MAX_EDGES_GIRVAN_NEWMAN:
        raise LabError(
            f"o Girvan-Newman remove as {graph.number_of_edges()} ligações uma a uma e levaria "
            f"minutos; acima de {MAX_EDGES_GIRVAN_NEWMAN} ligações use o Louvain ou aumente "
            "o peso mínimo da ligação."
        )
    if graph.number_of_edges() == 0:
        raise LabError("com este peso mínimo não sobra nenhuma ligação; diminua o corte.")

    load_builtin_implementations()
    trace_payload: dict[str, Any]
    if algorithm == "louvain":
        l_trace = louvain_trace(graph, seed=42)
        lib: Any = COMMUNITIES.get("louvain")
        reference = lib.run(projection, seed=42)
        trace_payload = {"louvain": _louvain_payload(l_trace, reference)}
        membership, q, runtime, status = l_trace.membership, l_trace.q, l_trace.runtime_s, "ok"
        stop = None
    elif algorithm == "girvan_newman":
        g_trace = girvan_newman_trace(graph, time_budget_s=time_budget_s)
        trace_payload = {"girvan_newman": _girvan_newman_payload(g_trace, sorted(graph.nodes))}
        membership, q, runtime, status = (
            g_trace.membership,
            g_trace.q,
            g_trace.runtime_s,
            g_trace.status,
        )
        stop = g_trace.stop_reason
    else:
        raise LabError(f"algoritmo {algorithm!r} desconhecido")

    partition = Partition(
        algorithm=algorithm,
        projection_id=projection.projection_id,
        membership=membership,
        modularity=q,
        n_communities=len(set(membership.values())),
        runtime_s=runtime,
        params={"lab": True},
        status=status,  # type: ignore[arg-type]
        meta=Meta(producer="lab"),
    )

    reading = analyze(
        graph,
        membership,
        q,
        bundle.graph if side == "student" else None,
        granularity=bundle.spec.granularity,
        criterion=bundle.spec.edge_criterion,
    )

    reveal: dict[str, Any] = {}
    if demo_data is not None:
        areas = list(demo.CURRICULUM)
        if side == "student":
            planted = {s: areas.index(a) for s, a in demo_data.student_area.items() if s in graph}
            names = {s: demo_data.student_area[s] for s in planted}
        else:
            planted = {
                d: areas.index(a) for d, a in demo_data.discipline_area.items() if d in graph
            }
            names = {d: demo_data.discipline_area[d] for d in planted}
        reveal["planted"] = {
            "areas": [
                {"name": a, "disciplines": [label for _, label in mods]}
                for a, mods in demo.CURRICULUM.items()
            ],
            "node_area": names,
            "nmi": round(normalized_mutual_information(partition, planted), 4),
            "purity": round(purity(partition, planted), 4),
        }
    if outcomes is not None and side == "student":
        rows = outcome_rows(partition, outcomes)
        if any(r["n_labeled"] for r in rows):
            reveal["outcomes"] = {"rows": rows, "labels": OUTCOME_LABELS}
        validation = signal_validation(reading.get("signals") or {}, outcomes)
        if validation:
            reveal["signals"] = validation

    return {
        "request": {
            "source": source,
            "students": students,
            "seed": seed,
            "noise": noise,
            "side": side,
            "weighting": weighting,
            "algorithm": algorithm,
            "min_weight": min_weight,
        },
        "source": source_info,
        "bipartite": _bipartite_payload(bundle),
        "projection": {
            "side": side,
            "weighting": weighting,
            "nodes": [
                {"id": n, "label": d.get("label", n), "kind": d.get("kind", side)}
                for n, d in sorted(graph.nodes(data=True))
            ],
            "edges": [
                {"source": u, "target": v, "weight": round(float(w), 4)}
                for u, v, w in graph.edges(data="weight", default=1.0)
            ],
            "weight_range": [round(weight_range[0], 4), round(weight_range[1], 4)],
            "suggested_min_weight": suggested_cut,
            "min_weight": min_weight,
            "n_edges_before_cut": full_projection.graph.number_of_edges(),
        },
        **trace_payload,
        "result": {
            "membership": membership,
            "q": round(q, 5),
            "n_communities": partition.n_communities,
            "runtime_s": round(runtime, 4),
            "status": status,
            "stop_reason": stop,
        },
        "insight": reading,
        "centrality": _centralities(projection),
        "reveal": reveal,
        "timing": {"total_s": round(time.perf_counter() - started, 3)},
    }
