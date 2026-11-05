"""CLI da Frente C  ``[C]`` — grupo de comandos ``edugraph centrality``.

O ponto de partida da Frente C (§5.2 do plano de arquitetura)::

    python -m edugraph centrality all --root data/fixtures --dataset synthetic_v1
    python -m edugraph api serve --root data/processed --root data/fixtures
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - só para anotação
    from edugraph.contracts.types import CentralityResult


def register(subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser) -> None:
    """Acrescenta o grupo ``centrality`` ao parser principal."""
    group = subparsers.add_parser(
        "centrality",
        parents=[parent],
        help="[C] métricas de centralidade e disciplinas críticas",
        description="Frente C — grau, intermediação, autovetor e aplicação.",
    )
    actions = group.add_subparsers(dest="action", required=True)

    run_all = actions.add_parser(
        "all", parents=[parent], help="todas as métricas em todas as projeções do dataset"
    )
    run_all.add_argument("--dataset", required=True)
    run_all.add_argument("--projection", default=None, help="restringe a uma projeção")
    run_all.add_argument(
        "--metric",
        action="append",
        choices=["degree", "betweenness", "eigenvector"],
        default=None,
        dest="metrics",
        help="restringe a estas métricas; repita. Padrão: as três",
    )
    _add_metric_params(run_all)
    run_all.add_argument("--out", type=Path, default=Path("data/processed"))
    run_all.set_defaults(func=cmd_all)

    one = actions.add_parser("compute", parents=[parent], help="uma métrica em uma projeção")
    one.add_argument("--dataset", required=True)
    one.add_argument("--projection", required=True)
    one.add_argument("--metric", choices=["degree", "betweenness", "eigenvector"], required=True)
    _add_metric_params(one)
    one.add_argument("--out", type=Path, default=Path("data/processed"))
    one.set_defaults(func=cmd_compute)

    critical = actions.add_parser(
        "critical", parents=[parent], help="disciplinas críticas (metrics/centrality_top.csv)"
    )
    critical.add_argument("--dataset", required=True)
    critical.add_argument(
        "--projection", default=None, help="restringe a uma projeção discipline_*"
    )
    critical.add_argument("--top-n", type=int, default=10, dest="top_n")
    critical.add_argument("--out", type=Path, default=Path("data/processed"))
    critical.add_argument(
        "--tables",
        type=Path,
        default=None,
        help="grava as tabelas 6 e 7 do artigo nesta pasta (ex.: results/tables)",
    )
    critical.set_defaults(func=cmd_critical)

    sensitivity = actions.add_parser(
        "sensitivity", parents=[parent], help="sensibilidade da intermediação: none × inverse"
    )
    sensitivity.add_argument("--dataset", required=True)
    sensitivity.add_argument("--projection", default=None, help="restringe a discipline_*")
    sensitivity.add_argument("--top-n", type=int, default=10, dest="top_n")
    sensitivity.add_argument("--tables", type=Path, required=True)
    sensitivity.set_defaults(func=cmd_sensitivity)

    evaluate = actions.add_parser(
        "evaluate", parents=[parent], help="validação a posteriori contra outcomes.csv"
    )
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument(
        "--metric", choices=["degree", "betweenness", "eigenvector"], default="betweenness"
    )
    evaluate.add_argument(
        "--discipline-projection", default="discipline_simple", dest="discipline_projection"
    )
    evaluate.add_argument(
        "--student-projection", default="student_simple", dest="student_projection"
    )
    evaluate.add_argument("--top-n", type=int, default=5, dest="top_n")
    evaluate.add_argument("--quantiles", type=int, default=4)
    evaluate.add_argument(
        "--tables", type=Path, default=None, help="grava a tabela 8 nesta pasta (results/tables)"
    )
    evaluate.add_argument(
        "--figures", type=Path, default=None, help="grava a figura 8 nesta pasta (results/figures)"
    )
    evaluate.set_defaults(func=cmd_evaluate)

    report = actions.add_parser("report", parents=[parent], help="relatório interno consolidado")
    report.add_argument("--dataset", required=True)
    report.add_argument("--out", type=Path, default=Path("results"))
    report.set_defaults(func=cmd_report)


def _add_metric_params(parser: argparse.ArgumentParser) -> None:
    """Parâmetros que mudam o ranking — todos acabam em ``params``."""
    parser.add_argument(
        "--weight-mode",
        choices=["none", "inverse", "raw"],
        default="none",
        dest="weight_mode",
        help="peso como distância na intermediação (C-01). Padrão: none",
    )
    parser.add_argument(
        "--k", type=int, default=None, help="pivôs amostrados na intermediação (estimativa)"
    )
    parser.add_argument("--seed", type=int, default=42, help="semente da amostragem de pivôs")
    parser.add_argument(
        "--implementation",
        choices=["manual", "networkx"],
        default="manual",
        help="autovetor à mão ou pelo NetworkX (C-02)",
    )


# ---------------------------------------------------------------------
# Auxiliares comuns aos handlers
# ---------------------------------------------------------------------


def _metric_params(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    """Os argumentos da linha de comando, repartidos por métrica."""
    betweenness: dict[str, Any] = {"weight_mode": args.weight_mode}
    if args.k is not None:
        betweenness.update(k=args.k, seed=args.seed)
    return {
        "degree": {},
        "betweenness": betweenness,
        "eigenvector": {"implementation": args.implementation},
    }


def _print_result(result: CentralityResult) -> None:
    """Resumo de uma métrica, na mesma forma em todos os comandos."""
    top = ", ".join(f"{node} {score:.4f}" for node, score in result.top(3))
    nota = "" if result.converged else " (fallback: não convergiu)"
    print(
        f"[centrality] {result.projection_id}/{result.metric}: "
        f"{len(result.scores)} nós, {result.runtime_s:.3f}s{nota}; topo: {top}"
    )


# ---------------------------------------------------------------------
# Handlers — cada um fecha com a sua spec
# ---------------------------------------------------------------------


def cmd_all(args: argparse.Namespace) -> int:
    """Todas as métricas em todas as projeções do dataset (C-01, C-02)."""
    from edugraph.centrality.stage import DEFAULT_METRICS, compute_all
    from edugraph.contracts.errors import ArtifactNotFoundError
    from edugraph.contracts.paths import as_roots

    roots = as_roots(args.roots)
    projection_ids = [args.projection] if args.projection else roots.projections(args.dataset)
    if not projection_ids:
        raise ArtifactNotFoundError(
            f"nenhuma projeção do dataset {args.dataset!r} sob "
            f"{', '.join(str(r) for r in roots)}; confira o --root"
        )
    metrics = args.metrics or list(DEFAULT_METRICS)

    results = compute_all(
        roots, args.out, args.dataset, projection_ids, metrics, _metric_params(args)
    )
    for result in results:
        _print_result(result)
    print(f"[centrality] gravado em: {args.out / args.dataset / 'centrality'}")
    return 0


def cmd_compute(args: argparse.Namespace) -> int:
    """Uma métrica em uma projeção (C-01, C-02)."""
    from edugraph.centrality.stage import compute_metric
    from edugraph.contracts import io

    projection = io.load_projection(args.roots, args.dataset, args.projection)
    result = compute_metric(projection, args.metric, _metric_params(args)[args.metric])
    _print_result(result)
    print(f"[centrality] gravado: {io.save_centrality(result, args.out, args.dataset)}")
    return 0


def cmd_critical(args: argparse.Namespace) -> int:
    """Disciplinas críticas, discordância e correlação entre métricas (C-03)."""
    import math

    from edugraph.centrality.critical_disciplines import (
        is_discipline_projection,
        labels_of,
        load_results,
        rank_disciplines,
        write_metrics,
    )
    from edugraph.centrality.disagreement import DISAGREEMENT_COLUMNS, disagreement_rows
    from edugraph.centrality.tables import (
        CONFIG_COLUMNS,
        TABLE_COLUMNS,
        configuration,
        export_table,
        ranking_rows,
    )
    from edugraph.contracts import io
    from edugraph.contracts.errors import ArtifactNotFoundError
    from edugraph.contracts.paths import as_roots

    roots = as_roots(args.roots)
    candidates = [args.projection] if args.projection else roots.centralities(args.dataset)
    projection_ids = [p for p in candidates if is_discipline_projection(p)]
    if not projection_ids:
        raise ArtifactNotFoundError(
            f"nenhuma projeção discipline_* com centralidade em {args.dataset!r} sob "
            f"{', '.join(str(r) for r in roots)}; rode `centrality all` antes"
        )

    rows: list[dict[str, Any]] = []
    for projection_id in projection_ids:
        results = load_results(roots, args.dataset, projection_id)
        if not results:
            print(f"[centrality] {projection_id}: sem centralidades calculadas, pulando")
            continue
        labels = labels_of(io.load_projection(roots, args.dataset, projection_id))
        linhas = rank_disciplines(results, top_n=args.top_n, dataset=args.dataset, labels=labels)
        rows.extend(linhas)

        print(f"[centrality] disciplinas críticas — {args.dataset}/{projection_id}")
        for metric in dict.fromkeys(row["metric"] for row in linhas):
            topo = [r for r in linhas if r["metric"] == metric]
            print(
                f"  {metric:<12} " + ", ".join(f"{r['label']} {r['score']:.4f}" for r in topo[:5])
            )

        if all(m in results for m in ("degree", "betweenness", "eigenvector")):
            discordancia = disagreement_rows(
                results, top_n=min(args.top_n, 5), dataset=args.dataset, labels=labels
            )
            for linha in discordancia:
                valor = linha["value"]
                if isinstance(valor, float):
                    valor = (
                        "indefinida (ranking todo empatado)"
                        if math.isnan(valor)
                        else f"{valor:.3f}"
                    )
                print(f"  {linha['comparison']:<34} {valor or '—'}")
            if args.tables is not None:
                tabela = export_table(
                    f"tab7-discordancia-{args.dataset}-{projection_id}",
                    [{**row, **configuration(results["betweenness"])} for row in discordancia],
                    out=args.tables,
                    columns=[*DISAGREEMENT_COLUMNS, *CONFIG_COLUMNS],
                    kind="disagreement",
                )
                print(f"[centrality] gravado: {tabela}")

        if args.tables is not None:
            tabela = export_table(
                f"tab6-criticas-{args.dataset}-{projection_id}",
                ranking_rows(results, dataset=args.dataset, labels=labels, top_n=args.top_n),
                out=args.tables,
                columns=list(TABLE_COLUMNS),
                kind="critical",
            )
            print(f"[centrality] gravado: {tabela}")

    if not rows:
        return 1
    print(f"[centrality] gravado: {write_metrics(rows, args.out, args.dataset)}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Validação a posteriori contra ``outcomes.csv`` (C-06)."""
    from edugraph.centrality.evaluate import (
        FAILURE_COLUMNS,
        QUANTILE_COLUMNS,
        evaluate,
        figure_outcome_by_quantile,
    )
    from edugraph.reporting.tables import write_table

    resultado = evaluate(
        args.roots,
        args.dataset,
        discipline_projection=args.discipline_projection,
        student_projection=args.student_projection,
        metric=args.metric,
        top_n=args.top_n,
        quantiles=args.quantiles,
    )
    labels: dict[str, str] = resultado["labels"]

    print(f"[centrality] validação a posteriori — {args.dataset}, métrica {args.metric}")
    print("  não conclusão = Fail + Withdrawn; taxas sobre os alunos com vínculo no bipartido")
    disciplinas = resultado["disciplines"]
    if disciplinas is None:
        print(f"  disciplinas: {resultado['discipline_note']}")
    else:
        print(
            f"  {'grupo':<13} {'disciplina':<14} {'alunos':>7} "
            f"{'não concl.':>10} {'base':>7} {'excesso':>8}"
        )
        for row in disciplinas:
            nome = labels.get(row["node_id"], row["node_id"]) if row["node_id"] else ""
            print(
                f"  {row['group']:<13} {nome:<14} {row['n_students']:>7} "
                f"{row['rate_not_passed']:>10.1%} {row['base_rate_not_passed']:>7.1%} "
                f"{row['excess_not_passed']:>+8.1%}"
            )

    alunos = resultado["students"]
    if alunos is None:
        print(f"  alunos: {resultado['student_note']}")
    else:
        print(f"  {'faixa':<6} {'alunos':>7} {'score':>21} {'não concl.':>10} {'excesso':>8}")
        for row in alunos:
            faixa = f"{row['score_min']:.4g}–{row['score_max']:.4g}"
            print(
                f"  Q{row['quantile']:<5} {row['n_students']:>7} {faixa:>21} "
                f"{row['rate_not_passed']:>10.1%} {row['excess_not_passed']:>+8.1%}"
            )

    sufixo = f"{args.dataset}-{args.metric}"
    if args.tables is not None and disciplinas is not None:
        linhas = [
            {**row, "label": labels.get(row["node_id"], "") if row["node_id"] else ""}
            for row in disciplinas
        ]
        path = write_table(
            f"tab8-reprovacao-{sufixo}",
            linhas,
            out_dir=args.tables,
            columns=["group", "rank", "node_id", "label", *FAILURE_COLUMNS[3:]],
        )
        print(f"[centrality] gravado: {path}")
    if args.tables is not None and alunos is not None:
        path = write_table(
            f"tab8b-desfecho-faixa-{sufixo}",
            alunos,
            out_dir=args.tables,
            columns=list(QUANTILE_COLUMNS),
        )
        print(f"[centrality] gravado: {path}")
    if args.figures is not None and alunos is not None:
        for path in figure_outcome_by_quantile(
            alunos,
            dataset=args.dataset,
            projection_id=args.student_projection,
            metric=args.metric,
            out=args.figures,
        ):
            print(f"[centrality] gravado: {path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Relatório interno consolidado, em Markdown (C-07)."""
    from edugraph.centrality.report import build_internal_report
    from edugraph.contracts.paths import as_roots

    path = build_internal_report(args.dataset, list(as_roots(args.roots)), args.out)
    print(f"[centrality] relatório interno gravado: {path}")
    return 0


def cmd_sensitivity(args: argparse.Namespace) -> int:
    """Compara saltos e distância inversa sem gravar centralidades de fronteira."""
    from edugraph.centrality.critical_disciplines import is_discipline_projection, labels_of
    from edugraph.centrality.stage import compute_metric
    from edugraph.centrality.tables import TABLE_COLUMNS, export_table, ranking_rows
    from edugraph.contracts import io
    from edugraph.contracts.errors import ArtifactNotFoundError, ContractError
    from edugraph.contracts.paths import as_roots

    roots = as_roots(args.roots)
    candidates = [args.projection] if args.projection else roots.projections(args.dataset)
    projection_ids = [p for p in candidates if is_discipline_projection(p)]
    if not projection_ids:
        raise ArtifactNotFoundError("sensibilidade: nenhuma projeção discipline_* encontrada")
    if args.top_n < 1:
        raise ContractError("top_n precisa ser >= 1")
    for projection_id in projection_ids:
        projection = io.load_projection(roots, args.dataset, projection_id)
        primary = io.load_centrality(roots, args.dataset, projection_id, "betweenness")
        params = {
            key: value
            for key, value in primary.params.items()
            if key in {"normalized", "k", "seed"}
        }
        rows = []
        for mode in ("none", "inverse"):
            result = compute_metric(projection, "betweenness", {**params, "weight_mode": mode})
            rows.extend(
                ranking_rows(
                    {"betweenness": result},
                    dataset=args.dataset,
                    labels=labels_of(projection),
                    top_n=args.top_n,
                )
            )
        path = export_table(
            f"tab6-sensibilidade-{args.dataset}-{projection_id}",
            rows,
            out=args.tables,
            columns=list(TABLE_COLUMNS),
            kind="sensitivity",
        )
        print(f"[centrality] sensibilidade gravada: {path}")
    return 0
