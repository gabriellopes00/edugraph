"""CLI da Frente B  ``[B]`` — grupo de comandos ``edugraph community``.

O ponto de partida da Frente B (§5.2 do plano de arquitetura)::

    python -m edugraph community louvain \\
        --root data/fixtures --dataset synthetic_v1 --projection student_simple
    python -m edugraph community girvan-newman \\
        --root data/fixtures --dataset synthetic_v1 --projection student_simple \\
        --time-budget 60

Quando o OULAD chegar: ``--root data/processed --dataset oulad_bbb_2013j``.
Nada mais muda.

Depois de rodar os algoritmos, o resto da frente sai daqui::

    python -m edugraph community characterize --dataset synthetic_v1 \\
        --partition louvain__student_simple
    python -m edugraph community compare --dataset synthetic_v1
    python -m edugraph community evaluate --dataset synthetic_v1 \\
        --partition louvain__student_simple
    python -m edugraph community figures --dataset synthetic_v1

Todo comando escreve em ``--out`` (por padrão ``data/processed``) e lê
das raízes de ``--root`` — nunca no lugar de onde leu, para que uma
fixture nunca seja sobrescrita por uma execução.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - só para anotação
    from edugraph.contracts.types import Partition

#: Onde as figuras da frente são gravadas por padrão.
DEFAULT_FIGURES_DIR = Path("results/figures")


def register(subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser) -> None:
    """Acrescenta o grupo ``community`` ao parser principal."""
    group = subparsers.add_parser(
        "community",
        parents=[parent],
        help="[B] detecção de comunidades",
        description="Frente B — Louvain, Girvan-Newman, modularidade e caracterização.",
    )
    actions = group.add_subparsers(dest="action", required=True)

    louvain = actions.add_parser("louvain", parents=[parent], help="Louvain sobre uma projeção")
    _add_common(louvain)
    louvain.add_argument("--seed", type=int, default=42)
    louvain.add_argument("--resolution", type=float, default=1.0)
    louvain.add_argument(
        "--implementation", choices=["python_louvain", "networkx"], default="python_louvain"
    )
    louvain.add_argument(
        "--compare-implementations",
        action="store_true",
        dest="compare_implementations",
        help="roda as duas bibliotecas e registra a diferença (spec B-01)",
    )
    louvain.set_defaults(func=cmd_louvain)

    gn = actions.add_parser(
        "girvan-newman", parents=[parent], help="Girvan-Newman com orçamento de tempo"
    )
    _add_common(gn)
    gn.add_argument("--time-budget", type=float, default=300.0, dest="time_budget_s")
    gn.add_argument("--target-communities", type=int, default=None, dest="target_communities")
    gn.add_argument("--sample-nodes", type=int, default=None, dest="sample_nodes")
    gn.add_argument("--seed", type=int, default=42)
    gn.set_defaults(func=cmd_girvan_newman)

    characterize = actions.add_parser(
        "characterize", parents=[parent], help="perfil das comunidades (profile.csv)"
    )
    characterize.add_argument("--dataset", required=True)
    characterize.add_argument("--partition", required=True, help="<algoritmo>__<projection_id>")
    characterize.add_argument("--top-k", type=int, default=3, dest="top_k")
    characterize.add_argument("--out", type=Path, default=Path("data/processed"))
    characterize.set_defaults(func=cmd_characterize)

    compare = actions.add_parser(
        "compare", parents=[parent], help="tabela comparativa (metrics/communities.csv)"
    )
    compare.add_argument("--dataset", required=True)
    compare.add_argument("--out", type=Path, default=Path("data/processed"))
    compare.add_argument(
        "--figures",
        type=Path,
        default=None,
        help="diretório da figura Q × tempo (padrão: nenhuma)",
    )
    compare.set_defaults(func=cmd_compare)

    evaluate = actions.add_parser(
        "evaluate", parents=[parent], help="validação a posteriori contra outcomes.csv"
    )
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--partition", required=True)
    evaluate.add_argument(
        "--null-baseline",
        action="store_true",
        dest="null_baseline",
        help="compara o Q com o das réplicas nulas da spec A-08",
    )
    evaluate.add_argument(
        "--out",
        type=Path,
        default=None,
        help="grava o desfecho por comunidade em <out>/tables (padrão: só imprime)",
    )
    evaluate.set_defaults(func=cmd_evaluate)

    figures = actions.add_parser("figures", parents=[parent], help="figuras de comunidades (B-07)")
    figures.add_argument("--dataset", required=True)
    figures.add_argument(
        "--partition",
        action="append",
        default=None,
        dest="partitions",
        help="restringe a estas partições; repita. Padrão: todas as do dataset",
    )
    figures.add_argument(
        "--layout", choices=["spring", "kamada_kawai", "circular"], default="spring"
    )
    figures.add_argument("--out", type=Path, default=DEFAULT_FIGURES_DIR)
    figures.set_defaults(func=cmd_figures)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--projection", required=True, help="ex.: student_simple")
    parser.add_argument("--out", type=Path, default=Path("data/processed"))


# ---------------------------------------------------------------------
# Auxiliares comuns aos handlers
# ---------------------------------------------------------------------


def _print_partition(partition: Partition, prefix: str = "[community]") -> None:
    """Resumo de uma partição, na mesma forma em todos os comandos."""
    from edugraph.community.characterize import describe_partition

    resumo = describe_partition(partition)
    print(
        f"{prefix} {partition.artifact_id}: Q = {partition.modularity:.4f}, "
        f"k = {partition.n_communities} (maior {resumo['largest_community']}, "
        f"{resumo['n_singletons']} unitárias), {partition.runtime_s:.3f}s, "
        f"status {partition.status}"
    )


def _save(partition: Partition, out: Path, dataset: str) -> None:
    """Grava a partição e avisa onde."""
    from edugraph.contracts import io

    path = io.save_partition(partition, out, dataset)
    print(f"[community] gravado: {path}")


# ---------------------------------------------------------------------
# Handlers — cada um fecha com a sua spec
# ---------------------------------------------------------------------


def cmd_louvain(args: argparse.Namespace) -> int:
    """Roda o Louvain sobre uma projeção e grava a partição (spec B-01)."""
    from edugraph.community.louvain import LouvainAlgorithm, compare_implementations
    from edugraph.contracts import io

    projection = io.load_projection(args.roots, args.dataset, args.projection)
    partition = LouvainAlgorithm().run(
        projection,
        seed=args.seed,
        resolution=args.resolution,
        implementation=args.implementation,
    )

    if args.compare_implementations:
        linha = compare_implementations(projection, seed=args.seed, resolution=args.resolution)
        print(
            f"[community] python-louvain: Q = {linha['modularity_python_louvain']:.6f}, "
            f"k = {linha['n_communities_python_louvain']}, "
            f"{linha['runtime_python_louvain_s']:.3f}s"
        )
        print(
            f"[community] networkx:       Q = {linha['modularity_networkx']:.6f}, "
            f"k = {linha['n_communities_networkx']}, {linha['runtime_networkx_s']:.3f}s"
        )
        print(
            f"[community] diferença de Q = {linha['abs_diff']:.2e}; NMI = {linha['nmi']:.4f}; "
            f"Rand ajustado = {linha['adjusted_rand']:.4f}; "
            f"partições idênticas: {'sim' if linha['identical'] else 'não'}"
        )
        # Fica no artefato: a spec B-01 pede a comparação registrada, e
        # meta.stats é o lugar de metadado livre (docs/contratos).
        partition.meta = partition.meta.with_stats(implementation_comparison=linha)

    _print_partition(partition)
    _save(partition, args.out, args.dataset)
    return 0


def cmd_girvan_newman(args: argparse.Namespace) -> int:
    """Roda o Girvan-Newman com orçamento e grava a partição (spec B-02).

    Estouro de orçamento **não** é erro: a partição sai com
    ``status="timeout"`` (ou ``"skipped"``) e o comando devolve 0, porque
    isso é resultado a reportar no capítulo 3 (ADR-0006).
    """
    from edugraph.community.girvan_newman import GirvanNewmanAlgorithm
    from edugraph.contracts import io

    projection = io.load_projection(args.roots, args.dataset, args.projection)
    partition = GirvanNewmanAlgorithm().run(
        projection,
        time_budget_s=args.time_budget_s,
        target_communities=args.target_communities,
        sample_nodes=args.sample_nodes,
        seed=args.seed,
    )

    _print_partition(partition)
    print(
        f"[community] {partition.params['n_cuts']} cortes; parada: "
        f"{partition.params['stop_reason']}"
    )
    if partition.status != "ok":
        print(
            f"[community] atenção: orçamento de {args.time_budget_s:g}s não bastou. "
            "A linha da tabela sai com o status visível (ADR-0006)."
        )
    if partition.projection_id != args.projection:
        print(
            f"[community] amostragem ativa: o artefato vale para "
            f"{partition.projection_id!r}, não para a projeção inteira."
        )
    _save(partition, args.out, args.dataset)
    return 0


def cmd_characterize(args: argparse.Namespace) -> int:
    """Grava ``profile.csv`` com o perfil de cada comunidade (spec B-05)."""
    from edugraph.community.characterize import PROFILE_COLUMNS, characterize
    from edugraph.contracts import io

    partition = io.load_partition(args.roots, args.dataset, args.partition)
    bipartite = io.load_bipartite(args.roots, args.dataset)

    lados = {
        bipartite.graph.nodes[node].get("kind")
        for node in partition.membership
        if node in bipartite.graph
    }
    if lados != {"student"}:
        print(
            "[community] atenção: esta partição não é do lado aluno; a coluna "
            "top_disciplines vai listar nós do lado oposto (ver a spec B-05)."
        )

    rows = characterize(partition, bipartite, top_k=args.top_k)
    path = io.save_profile(rows, args.out, args.dataset, args.partition)

    print(f"[community] {'comunidade':>10} {'tam.':>5} {'dens.':>6}  disciplinas predominantes")
    for row in rows:
        print(
            f"[community] {row['community']:>10} {row['size']:>5} "
            f"{row['internal_density']:>6.3f}  {row['top_disciplines']}"
        )
    print(f"[community] colunas: {', '.join(PROFILE_COLUMNS)}")
    print(f"[community] gravado: {path}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Monta ``metrics/communities.csv`` com todas as partições (spec B-04).

    Lê **todas** as partições do dataset sob as raízes — inclusive as com
    ``status="timeout"``, que são dado do artigo — e grava a tabela
    principal do capítulo 3 em ``--out``. Com ``--figures``, gera também
    a figura de Q × tempo.
    """
    from edugraph.community.compare import agreement_matrix, compare, write_metrics
    from edugraph.contracts import io
    from edugraph.contracts.paths import as_roots

    roots = as_roots(args.roots)
    artifact_ids = roots.partitions(args.dataset)
    if not artifact_ids:
        print(f"[community] nenhuma partição em {args.dataset}; rode louvain/girvan-newman antes")
        return 1

    partitions = [io.load_partition(roots, args.dataset, aid) for aid in artifact_ids]
    rows = compare(partitions, args.dataset)
    path = write_metrics(rows, args.out, args.dataset)

    print(
        f"[community] {'projeção':<34} {'algoritmo':<14} {'Q':>8} {'k':>4} "
        f"{'maior':>6} {'tempo':>9} status"
    )
    for row in rows:
        print(
            f"[community] {row['projection_id']:<34} {row['algorithm']:<14} "
            f"{row['modularity']:>8.4f} {row['n_communities']:>4} "
            f"{row['largest_community']:>6} {row['runtime_s']:>8.3f}s {row['status']}"
        )
    print(f"[community] gravado: {path}")

    referencia = [p.artifact_id for p in partitions if p.meta.producer == "reference"]
    if referencia:
        # As partições de referência das fixtures existem para destravar
        # a Frente C no dia 0 e gravam runtime_s = 0. Misturá-las com
        # execuções reais na tabela do artigo sem dizer seria enganoso.
        print(
            f"[community] atenção: {len(referencia)} linhas vêm de partições de "
            f"referência das fixtures (sem tempo medido): {', '.join(referencia)}"
        )

    for linha in agreement_matrix(partitions):
        print(
            f"[community] concordância em {linha['projection_id']}: "
            f"{linha['left']} × {linha['right']} — NMI {linha['nmi']:.4f}, "
            f"Rand ajustado {linha['adjusted_rand']:.4f}"
        )

    if args.figures is not None:
        from edugraph.community.report import figure_q_vs_time

        figura = figure_q_vs_time(partitions, args.figures, dataset=args.dataset)
        print(f"[community] figura: {figura}  (+ .svg, .caption.txt)")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Validação a posteriori de uma partição (spec B-06).

    NMI e pureza só quando o dataset traz o grupo plantado; no OULAD,
    onde ele não existe, o comando reporta só o perfil de desfecho — e
    isso não é erro.
    """
    from edugraph.community.evaluate import (
        OUTCOME_COLUMNS,
        load_labels,
        normalized_mutual_information,
        null_baseline,
        outcome_profile,
        purity,
        unknown_outcomes,
    )
    from edugraph.contracts import io

    partition = io.load_partition(args.roots, args.dataset, args.partition)
    outcomes = load_labels(args.roots, args.dataset)

    print(
        f"[community] {partition.artifact_id}: Q = {partition.modularity:.4f}, "
        f"k = {partition.n_communities}"
    )

    if outcomes.planted_group:
        nmi = normalized_mutual_information(partition, outcomes.planted_group)
        pureza = purity(partition, outcomes.planted_group)
        print(f"[community] contra o grupo plantado: NMI = {nmi:.4f}, pureza = {pureza:.4f}")
    else:
        print(
            "[community] sem grupo plantado neste dataset (é o caso do OULAD): "
            "NMI e pureza não se aplicam."
        )

    if args.null_baseline:
        base = null_baseline(
            args.roots,
            args.dataset,
            partition.projection_id,
            partition.modularity,
            seed=int(partition.params.get("seed", 42)),
            resolution=float(partition.params.get("resolution", 1.0)),
        )
        print(
            f"[community] linha de base nula: {base['n_replicas']} réplicas, "
            f"Q nulo = {base['q_null_mean']:.4f} ± {base['q_null_sd']:.4f}, "
            f"z = {base['z']:.2f} → {base['verdict']}"
        )
        if base["skipped"]:
            print(
                f"[community] réplicas sem a projeção {partition.projection_id!r}: "
                f"{', '.join(base['skipped'])}"
            )

    rows = outcome_profile(partition, outcomes)
    sem_rotulo = unknown_outcomes(partition, outcomes)
    cabecalho = "  ".join(f"{r:>12}" for r in ("Distinction", "Pass", "Fail", "Withdrawn"))
    print(f"[community] {'comunidade':>10} {'tam.':>5} {cabecalho}   mais acima da base")
    for row in rows:
        taxas = "  ".join(
            f"{row[f'rate_{r}']:>11.1%}" for r in ("Distinction", "Pass", "Fail", "Withdrawn")
        )
        print(
            f"[community] {row['community']:>10} {row['size']:>5}  {taxas}   "
            f"{row['top_excess_outcome']} ({row['top_excess']:+.1%})"
        )
    base_row = rows[0]
    base_taxas = "  ".join(
        f"{base_row[f'base_rate_{r}']:>11.1%}" for r in ("Distinction", "Pass", "Fail", "Withdrawn")
    )
    print(f"[community] {'base':>10} {'':>5}  {base_taxas}")
    if sem_rotulo:
        print(f"[community] {sem_rotulo} nós sem desfecho conhecido (fora das taxas acima)")

    if args.out is not None:
        from edugraph.reporting.tables import write_table

        path = write_table(
            f"tab5-validacao-{args.dataset}-{args.partition}",
            rows,
            out_dir=args.out / "tables",
            columns=list(OUTCOME_COLUMNS),
        )
        print(f"[community] gravado: {path}")
    return 0


def cmd_figures(args: argparse.Namespace) -> int:
    """Gera as figuras de comunidades do capítulo 3 (spec B-07).

    Uma figura de grafo por partição, mais a distribuição de tamanhos e
    o Q × tempo do conjunto. Regenera o índice quando ``--out`` é o
    ``results/figures`` do repositório.
    """
    from edugraph.community.report import (
        figure_communities,
        figure_q_vs_time,
        figure_size_distribution,
    )
    from edugraph.contracts import io
    from edugraph.contracts.paths import as_roots
    from edugraph.reporting.figures import FIGURES_DIR, build_index

    roots = as_roots(args.roots)
    artifact_ids = args.partitions or roots.partitions(args.dataset)
    if not artifact_ids:
        print(f"[community] nenhuma partição em {args.dataset}; rode louvain/girvan-newman antes")
        return 1

    partitions = []
    for artifact_id in artifact_ids:
        partition = io.load_partition(roots, args.dataset, artifact_id)
        partitions.append(partition)
        if not roots.has(args.dataset, "projections", partition.projection_id, "meta.json"):
            # Partição de recorte (Girvan-Newman com --sample-nodes): não
            # há projeção em disco com esse id, e a figura de grafo
            # precisa dela. As outras duas figuras continuam valendo.
            print(
                f"[community] {artifact_id}: sem projeção {partition.projection_id!r} em disco; "
                "figura de grafo pulada"
            )
            continue
        projection = io.load_projection(roots, args.dataset, partition.projection_id)
        figura = figure_communities(partition, projection, args.out, layout=args.layout)
        print(f"[community] figura: {figura}  (+ .svg, .caption.txt)")

    tamanhos = figure_size_distribution(partitions, args.out, dataset=args.dataset)
    print(f"[community] figura: {tamanhos}  (+ .svg, .caption.txt)")
    q_tempo = figure_q_vs_time(partitions, args.out, dataset=args.dataset)
    print(f"[community] figura: {q_tempo}  (+ .svg, .caption.txt)")

    if args.out.resolve() == FIGURES_DIR.resolve():
        print(f"[community] índice: {build_index()}")
    return 0
