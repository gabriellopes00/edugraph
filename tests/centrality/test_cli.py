"""Integração do estágio e da CLI da Frente C, sem escrever nas fixtures."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from edugraph.__main__ import load_config, main
from edugraph.centrality.stage import CentralityStage
from edugraph.contracts import io
from edugraph.contracts.paths import as_roots
from edugraph.contracts.registry import load_builtin_implementations

pytestmark = [pytest.mark.dataset("tiny_v1"), pytest.mark.dataset("synthetic_v1")]


@pytest.fixture
def copia_fixtures(tmp_path: Path, repo_root: Path) -> Path:
    """A CLI recebe uma raiz própria, mesmo quando só faz leituras."""
    return Path(shutil.copytree(repo_root / "data/fixtures", tmp_path / "fixtures"))


def linhas(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("dataset", ["tiny_v1", "synthetic_v1"])
def test_estagio_cobre_nos_e_atualiza_metricas_sem_duplicar(
    dataset: str, copia_fixtures: Path, tmp_path: Path, repo_root: Path
) -> None:
    load_builtin_implementations()
    config = load_config(repo_root / "configs/synthetic_v1.toml")
    config.bipartite = replace(config.bipartite, dataset=dataset)
    out = tmp_path / "out"
    stage = CentralityStage()
    stage.run([copia_fixtures], out, config)
    roots = as_roots([copia_fixtures])
    for projection_id in roots.projections(dataset):
        nodes = set(io.load_projection(roots, dataset, projection_id).graph)
        for metric in ("degree", "betweenness", "eigenvector"):
            result = io.load_centrality([out], dataset, projection_id, metric)
            assert set(result.scores) == nodes
            assert result.meta.schema_version == "1.0"
            assert (
                (out / dataset / "centrality" / projection_id / f"{metric}.csv")
                .read_text(encoding="utf-8")
                .startswith("node_id,score\n")
            )
    table = out / dataset / "metrics/centrality_top.csv"
    before = table.read_bytes()
    stage.run([copia_fixtures], out, config)
    assert table.read_bytes() == before
    rows = linhas(table)
    assert len(rows) == (18 if dataset == "tiny_v1" else 42)
    assert set(rows[0]) == {
        "dataset",
        "projection_id",
        "metric",
        "rank",
        "node_id",
        "label",
        "score",
    }


@pytest.mark.parametrize("dataset", ["tiny_v1", "synthetic_v1"])
def test_comando_all_grava_as_tres_metricas_sem_alterar_entrada(
    dataset: str, copia_fixtures: Path, tmp_path: Path
) -> None:
    before = {
        p.relative_to(copia_fixtures): p.read_bytes()
        for p in copia_fixtures.rglob("*")
        if p.is_file()
    }
    out = tmp_path / "out"
    assert (
        main(
            [
                "centrality",
                "all",
                "--root",
                str(copia_fixtures),
                "--dataset",
                dataset,
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert len(list((out / dataset / "centrality").rglob("*.csv"))) == 12
    assert before == {
        p.relative_to(copia_fixtures): p.read_bytes()
        for p in copia_fixtures.rglob("*")
        if p.is_file()
    }


def test_comando_compute_preserva_parametros_e_cobertura(
    copia_fixtures: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    assert (
        main(
            [
                "centrality",
                "compute",
                "--root",
                str(copia_fixtures),
                "--dataset",
                "tiny_v1",
                "--projection",
                "student_simple",
                "--metric",
                "betweenness",
                "--weight-mode",
                "inverse",
                "--k",
                "3",
                "--seed",
                "7",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    result = io.load_centrality([out], "tiny_v1", "student_simple", "betweenness")
    assert set(result.scores) == {"S1", "S2", "S3", "S4", "S5", "S6"}
    assert result.params == {
        "normalized": True,
        "weight_mode": "inverse",
        "k": 3,
        "estimate": True,
        "seed": 7,
    }


def test_comando_critical_exporta_tabelas_e_metricas_idempotentes(
    copia_fixtures: Path, tmp_path: Path
) -> None:
    out, tables = tmp_path / "out", tmp_path / "tables"
    args = [
        "centrality",
        "critical",
        "--root",
        str(copia_fixtures),
        "--dataset",
        "synthetic_v1",
        "--out",
        str(out),
        "--tables",
        str(tables),
    ]
    assert main(args) == 0
    files = sorted(tables.glob("*.csv"))
    assert len(files) == 4
    assert all({"dataset", "projection_id"} <= set(linhas(p)[0]) for p in files)
    before = {p: p.read_bytes() for p in files}
    metrics = out / "synthetic_v1/metrics/centrality_top.csv"
    metric_bytes = metrics.read_bytes()
    assert main(args) == 0
    assert before == {p: p.read_bytes() for p in files}
    assert metrics.read_bytes() == metric_bytes


def test_comando_evaluate_exporta_quartis_sem_inventar_ranking_degenerado(
    copia_fixtures: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "centrality",
                "evaluate",
                "--root",
                str(copia_fixtures),
                "--dataset",
                "synthetic_v1",
                "--tables",
                str(tmp_path / "tables"),
            ]
        )
        == 0
    )
    assert "não há disciplina crítica a validar" in capsys.readouterr().out
    files = list((tmp_path / "tables").glob("*.csv"))
    assert len(files) == 1
    rows = linhas(files[0])
    assert [r["quantile"] for r in rows] == ["1", "2", "3", "4"]
    assert sum(int(r["n_students"]) for r in rows) == 98
    assert "rate_not_passed" in rows[0]


def test_comando_report_gera_relatorio_agregado(copia_fixtures: Path, tmp_path: Path) -> None:
    out = tmp_path / "report"
    assert (
        main(
            [
                "centrality",
                "report",
                "--root",
                str(copia_fixtures),
                "--dataset",
                "synthetic_v1",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    text = (out / "relatorio-interno-synthetic_v1.md").read_text(encoding="utf-8")
    assert "## Comunidades" in text
    assert "## Disciplinas críticas" in text
    assert "## Relação com o desfecho histórico" in text
    assert "S100055" not in text
    assert list((out / "figures").glob("*.png"))


def test_comando_openapi_imprime_json_com_rotas_de_leitura(
    copia_fixtures: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["api", "openapi", "--root", str(copia_fixtures)]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert "/datasets/{dataset}/centrality/{projection_id}/{metric}" in schema["paths"]
    metodos = {caminho: set(m) for caminho, m in schema["paths"].items()}
    # A única rota que não lê: o laboratório monta redes pequenas na hora (ADR-0013).
    assert metodos.pop("/lab/run") == {"post"}
    assert all(m == {"get"} for m in metodos.values()), "fora do laboratório, a API só lê"


@pytest.mark.parametrize("reload", [False, True])
def test_comando_serve_configura_raizes_sem_deixar_servidor_ativo(
    copia_fixtures: Path, monkeypatch: pytest.MonkeyPatch, reload: bool
) -> None:
    import os

    import uvicorn

    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append((app, kwargs)))
    monkeypatch.setenv("EDUGRAPH_ROOTS", "origem-anterior")
    args = ["api", "serve", "--root", str(copia_fixtures), "--host", "127.0.0.1", "--port", "8765"]
    if reload:
        args.append("--reload")
    assert main(args) == 0
    app, kwargs = calls[0]
    assert kwargs["port"] == 8765
    assert kwargs["host"] == "127.0.0.1"
    if reload:
        assert app == "edugraph.api.app:app"
        assert os.environ["EDUGRAPH_ROOTS"] == str(copia_fixtures)
    else:
        assert list(app.state.roots) == [copia_fixtures]


def test_tabelas_finais_identificam_intermediacao_amostrada(
    copia_fixtures: Path, tmp_path: Path
) -> None:
    assert (
        main(
            [
                "centrality",
                "all",
                "--root",
                str(copia_fixtures),
                "--dataset",
                "tiny_v1",
                "--k",
                "2",
                "--seed",
                "7",
                "--weight-mode",
                "inverse",
                "--out",
                str(copia_fixtures),
            ]
        )
        == 0
    )
    tables = tmp_path / "tables"
    assert (
        main(
            [
                "centrality",
                "critical",
                "--root",
                str(copia_fixtures),
                "--dataset",
                "tiny_v1",
                "--out",
                str(tmp_path / "out"),
                "--tables",
                str(tables),
            ]
        )
        == 0
    )
    for table in tables.glob("*.csv"):
        rows = linhas(table)
        assert {"weight_mode", "k", "estimate", "seed"} <= set(rows[0])
        selected = (
            rows
            if table.name.startswith("tab7")
            else [r for r in rows if r["metric"] == "betweenness"]
        )
        assert all(
            (r["weight_mode"], r["k"], r["estimate"], r["seed"]) == ("inverse", "2", "True", "7")
            for r in selected
        )
        caption = table.with_suffix(".caption.txt").read_text(encoding="utf-8")
        assert "weight_mode" in caption
        if table.name.startswith("tab7"):
            assert "Discordância entre métricas" in caption
            assert "Spearman" in caption
            assert "linhas de outras métricas" not in caption
        else:
            assert "Disciplinas críticas por métrica" in caption
            assert "Spearman" not in caption
        assert "tab7" not in caption
        assert "sensibilidade" not in caption.lower()


@pytest.mark.parametrize("dataset", ["tiny_v1", "synthetic_v1"])
def test_sensibilidade_compara_modos_sem_sobrescrever_artefatos(
    dataset: str, copia_fixtures: Path, tmp_path: Path
) -> None:
    if dataset == "tiny_v1":
        assert (
            main(
                [
                    "centrality",
                    "all",
                    "--root",
                    str(copia_fixtures),
                    "--dataset",
                    dataset,
                    "--out",
                    str(copia_fixtures),
                ]
            )
            == 0
        )
    before = {p: p.read_bytes() for p in copia_fixtures.rglob("*") if p.is_file()}
    tables = tmp_path / "tables"
    args = [
        "centrality",
        "sensitivity",
        "--root",
        str(copia_fixtures),
        "--dataset",
        dataset,
        "--tables",
        str(tables),
    ]
    assert main(args) == 0
    files = list(tables.glob("*.csv"))
    assert len(files) == 2
    for path in files:
        caption = path.with_suffix(".caption.txt").read_text(encoding="utf-8")
        assert "Sensibilidade da intermediação" in caption
        assert "Spearman" not in caption
        assert "outras métricas" not in caption
        assert "tab7" not in caption
        rows = linhas(path)
        assert {r["weight_mode"] for r in rows} == {"none", "inverse"}
        assert all(r["metric"] == "betweenness" for r in rows)
        assert {r["estimate"] for r in rows} == {"False"}
        assert len(rows) == (6 if dataset == "tiny_v1" else 14)
        for mode in ("none", "inverse"):
            selected = [r for r in rows if r["weight_mode"] == mode]
            assert [int(r["rank"]) for r in selected] == list(range(1, len(selected) + 1))
            assert len({r["node_id"] for r in selected}) == len(selected)
    exported = {p: p.read_bytes() for p in tables.iterdir()}
    assert main(args) == 0
    assert exported == {p: p.read_bytes() for p in tables.iterdir()}
    assert before == {p: p.read_bytes() for p in copia_fixtures.rglob("*") if p.is_file()}


def test_sensibilidade_distingue_ponte_ponderada_com_calculo_a_mao(tmp_path: Path) -> None:
    import networkx as nx

    from edugraph.centrality.stage import compute_metric
    from edugraph.contracts.types import BipartiteSpec, ProjectionBundle, ProjectionSpec

    graph = nx.Graph()
    graph.add_weighted_edges_from(
        [("DA", "DB", 1), ("DA", "DC", 4), ("DC", "DB", 4), ("DB", "DD", 4)]
    )
    for node in graph:
        graph.nodes[node].update(kind="discipline", label=node)
    projection = ProjectionBundle(
        graph=graph,
        spec=ProjectionSpec(side="discipline", weighting="simple"),
        source=BipartiteSpec(dataset="ponte_ponderada"),
    )
    root = tmp_path / "artifacts"
    io.save_projection(projection, root)
    load_builtin_implementations()
    io.save_centrality(
        compute_metric(projection, "betweenness", {"weight_mode": "none"}), root, "ponte_ponderada"
    )
    tables = tmp_path / "tables"
    assert (
        main(
            [
                "centrality",
                "sensitivity",
                "--root",
                str(root),
                "--dataset",
                "ponte_ponderada",
                "--tables",
                str(tables),
            ]
        )
        == 0
    )
    rows = linhas(tables / "tab6-sensibilidade-ponte_ponderada-discipline_simple.csv")
    scores = {
        mode: {r["node_id"]: float(r["score"]) for r in rows if r["weight_mode"] == mode}
        for mode in ("none", "inverse")
    }
    # Cálculo à mão: triângulo A-B-C com folha D ligada a B.
    # Sem peso, B é interno somente nos pares {A,D} e {C,D}; C nunca
    # é interno. Com 4 nós, a normalização divide por C(3,2)=3: B=2/3.
    # Em inverse, d(A,B)=1 e d(A,C)+d(C,B)=1/4+1/4=1/2.
    # Logo C passa a ser interno em {A,B} e {A,D}: C=2/3.
    # B continua interno nos mesmos dois pares. Não há empates de caminhos;
    # A e D não são internos em nenhum par, em ambos os modos.
    assert scores["none"] == pytest.approx({"DA": 0, "DB": 2 / 3, "DC": 0, "DD": 0})
    assert scores["inverse"] == pytest.approx({"DA": 0, "DB": 2 / 3, "DC": 2 / 3, "DD": 0})
    ranks = {
        mode: {r["node_id"]: int(r["rank"]) for r in rows if r["weight_mode"] == mode}
        for mode in ("none", "inverse")
    }
    # Empates por id: sem peso, A antecede C entre os zeros; com peso,
    # C empata no topo com B e vem logo depois dele.
    assert ranks["none"]["DC"] == 3
    assert ranks["inverse"]["DC"] == 2
