"""Estratégia de escala  ``[A]`` — spec A-06.

As quatro reduções (coorte, corte por peso, amostra, núcleo-k) sobre as
fixtures. A rodada completa do OULAD — e a medição de tempo e memória —
é o passo manual que fica para depois do download.

O que todo teste aqui confere, além do resultado: **nenhuma redução é
silenciosa**. Cada uma deixa uma entrada em
``meta.stats["reductions"]`` do artefato, com parâmetros e contagens.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from edugraph.contracts import io
from edugraph.contracts.errors import ContractError
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.types import BipartiteSpec, ProjectionSpec
from edugraph.contracts.validate import validate_bipartite, validate_dataset, validate_projection
from edugraph.data.bipartite import build_bipartite
from edugraph.data.projection.manual import SimpleProjection
from edugraph.data.scale import (
    PRODUCER,
    filter_cohort,
    k_core,
    k_core_projection,
    prune_by_weight,
    reductions_of,
    sample_students,
)
from edugraph.data.synthetic import SyntheticSpec, generate

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def bipartite_por_apresentacao():
    """Bipartido sintético com ``granularity="module_presentation"``.

    O gerador sorteia apresentações 2024J e 2024B, então cada módulo
    aparece como duas disciplinas — o que a coorte precisa para recortar.
    """
    dataset = generate(SyntheticSpec(seed=42))
    spec = BipartiteSpec(dataset="sp", granularity="module_presentation", threshold=60.0)
    return build_bipartite(pd.DataFrame(dataset.enrollments), spec)


# ---------------------------------------------------------------------
# 1. Coorte
# ---------------------------------------------------------------------


def test_coorte_por_apresentacao_de_modulo(bipartite_por_apresentacao) -> None:
    coorte = filter_cohort(bipartite_por_apresentacao, "AAA_2024J")

    assert coorte.disciplines == {"DAAA_2024J"}
    assert all(coorte.graph.has_edge(s, "DAAA_2024J") for s in coorte.students)
    assert coorte.spec.cohort == "AAA_2024J"
    validate_bipartite(coorte)

    (entrada,) = reductions_of(coorte.meta)
    assert entrada["kind"] == "filter_cohort" and entrada["producer"] == PRODUCER
    assert entrada["n_students_after"] == len(coorte.students)
    assert entrada["n_disciplines_before"] == len(bipartite_por_apresentacao.disciplines)


def test_coorte_por_periodo_mantem_todos_os_modulos_do_periodo(bipartite_por_apresentacao) -> None:
    periodo = filter_cohort(bipartite_por_apresentacao, "2024J")
    assert periodo.disciplines
    assert all(d.endswith("_2024J") for d in periodo.disciplines)
    assert not any(d.endswith("_2024B") for d in periodo.disciplines)


@pytest.mark.dataset("synthetic_v1")
def test_coorte_em_bipartido_por_modulo_aponta_para_a_a03(artifact_roots: ArtifactRoots) -> None:
    """Com granularity='module' a apresentação já se perdeu; a mensagem diz o que fazer."""
    bundle = io.load_bipartite(artifact_roots, "synthetic_v1")
    with pytest.raises(ContractError, match="BipartiteSpec\\(cohort=\\.\\.\\.\\)"):
        filter_cohort(bundle, "AAA_2024J")


def test_coorte_inexistente_lista_exemplos(bipartite_por_apresentacao) -> None:
    with pytest.raises(ContractError, match="nenhuma disciplina casa"):
        filter_cohort(bipartite_por_apresentacao, "ZZZ_1999J")


# ---------------------------------------------------------------------
# 2. Corte por peso
# ---------------------------------------------------------------------


@pytest.mark.dataset("tiny_v1")
def test_corte_por_peso_e_auditavel(tiny_projection) -> None:
    """min_weight=2 em tiny/student_simple: sobram S1-S2, S1-S3, S2-S3; nós ficam."""
    projection = tiny_projection("student_simple")
    podada = prune_by_weight(projection, 2.0)

    assert podada.graph.number_of_edges() == 3
    assert podada.graph.number_of_nodes() == 6  # isolados permanecem
    assert podada.spec.min_weight == 2.0
    validate_projection(podada)  # o validador confere o corte

    (entrada,) = reductions_of(podada.meta)
    assert entrada == {
        "producer": PRODUCER,
        "kind": "prune_by_weight",
        "min_weight": 2.0,
        "n_edges_before": 9,
        "n_edges_after": 3,
        "n_edges_removed": 6,
    }


@pytest.mark.dataset("tiny_v1")
def test_corte_nao_positivo_e_recusado(tiny_projection) -> None:
    with pytest.raises(ContractError, match="positivo"):
        prune_by_weight(tiny_projection("student_simple"), 0.0)


# ---------------------------------------------------------------------
# 3. Amostra
# ---------------------------------------------------------------------


@pytest.mark.dataset("synthetic_v1")
def test_amostra_e_deterministica(artifact_roots: ArtifactRoots) -> None:
    bundle = io.load_bipartite(artifact_roots, "synthetic_v1")
    a = sample_students(bundle, 30, seed=7)
    b = sample_students(bundle, 30, seed=7)
    c = sample_students(bundle, 30, seed=8)

    assert a.students == b.students and len(a.students) == 30
    assert a.students != c.students
    validate_bipartite(a)

    (entrada,) = reductions_of(a.meta)
    assert entrada["kind"] == "sample_students"
    assert (entrada["n"], entrada["seed"]) == (30, 7)
    assert entrada["n_students_before"] == 98


@pytest.mark.dataset("synthetic_v1")
def test_amostra_maior_que_o_total_nao_muda_nada(artifact_roots: ArtifactRoots) -> None:
    bundle = io.load_bipartite(artifact_roots, "synthetic_v1")
    igual = sample_students(bundle, 10_000, seed=1)
    assert igual.students == bundle.students
    assert reductions_of(igual.meta)[0]["n_students_after"] == 98


@pytest.mark.dataset("tiny_v1")
def test_amostra_remove_disciplina_que_ficou_sem_aluno(tiny_bipartite) -> None:
    """Amostrando só S4 e S5, DA e DB ficam órfãs e saem."""
    # seed escolhida por tentativa para cair em {S4, S5}: o teste fixa o
    # conjunto em vez de depender da seed, forçando via n=2 sobre um
    # bipartido reduzido a esses dois alunos.
    sub = tiny_bipartite.graph.subgraph(["S4", "S5", "DA", "DB", "DC"]).copy()
    from edugraph.contracts.types import BipartiteBundle

    pequeno = BipartiteBundle(graph=sub, spec=tiny_bipartite.spec)
    amostra = sample_students(pequeno, 2, seed=0)

    assert amostra.students == {"S4", "S5"}
    assert amostra.disciplines == {"DC"}
    assert reductions_of(amostra.meta)[0]["n_disciplines_removed"] == 2


# ---------------------------------------------------------------------
# 4. Núcleo-k
# ---------------------------------------------------------------------


@pytest.mark.dataset("tiny_v1")
def test_nucleo_k_remove_o_triangulo_pendente(tiny_projection) -> None:
    """K4 em {S1,S2,S3,S6} sobrevive a k=3; S4 e S5 (grau 2) saem."""
    projection = tiny_projection("student_simple")
    core = k_core_projection(projection, 3)

    assert set(core.graph.nodes) == {"S1", "S2", "S3", "S6"}
    assert core.graph.number_of_edges() == 6
    validate_projection(core)

    (entrada,) = reductions_of(core.meta)
    assert entrada["kind"] == "k_core" and entrada["k"] == 3
    assert entrada["n_nodes_removed"] == 2


@pytest.mark.dataset("tiny_v1")
def test_nucleo_k_devolve_copia_e_recusa_k_invalido(tiny_projection) -> None:
    graph = tiny_projection("student_simple").graph
    core = k_core(graph, 1)
    core.remove_node("S1")
    assert "S1" in graph  # a original não foi tocada
    with pytest.raises(ContractError, match="k precisa"):
        k_core(graph, 0)


# ---------------------------------------------------------------------
# Reduções encadeadas ficam todas no histórico
# ---------------------------------------------------------------------


@pytest.mark.dataset("synthetic_v1")
def test_reducoes_encadeadas_acumulam_no_meta(artifact_roots: ArtifactRoots) -> None:
    bundle = sample_students(io.load_bipartite(artifact_roots, "synthetic_v1"), 40, seed=3)
    projection = SimpleProjection().project(
        bundle, ProjectionSpec(side="student", weighting="simple")
    )
    reduzida = k_core_projection(prune_by_weight(projection, 2.0), 2)

    kinds = [r["kind"] for r in reductions_of(reduzida.meta)]
    assert kinds == ["prune_by_weight", "k_core"]  # a amostra ficou no bipartido
    assert reduzida.meta.producer == "A-04"  # proveniência original preservada


# ---------------------------------------------------------------------
# Pipeline e CLI
# ---------------------------------------------------------------------


def test_pipeline_aplica_amostra_e_nucleo_k_do_toml(tmp_path: Path) -> None:
    from edugraph.contracts.types import RunConfig
    from edugraph.data.pipeline import run_data_stage

    config = RunConfig.from_dict(
        {
            "name": "t",
            "source": {"kind": "synthetic", "seed": 42, "sample_students": 50,
                       "sample_seed": 5, "k_core": 2},
            "bipartite": {"dataset": "t", "threshold": 60.0},
            "projections": [{"side": "student", "weighting": "simple"}],
        }
    )  # fmt: skip
    run_data_stage(config, tmp_path)

    bipartite = io.load_bipartite([tmp_path], "t")
    projection = io.load_projection([tmp_path], "t", "student_simple")
    assert len(bipartite.students) == 50
    assert reductions_of(bipartite.meta)[0]["kind"] == "sample_students"
    assert reductions_of(projection.meta)[0]["kind"] == "k_core"
    assert all(d >= 2 for _, d in projection.graph.degree)
    assert set(io.load_outcomes([tmp_path], "t").final_result) == bipartite.students
    validate_dataset([tmp_path], "t")


def test_data_sample_grava_dataset_novo_com_outcomes(tmp_path: Path) -> None:
    from edugraph.__main__ import main

    code = main(["data", "sample", "--root", "data/fixtures", "--dataset", "synthetic_v1",
                 "--n", "25", "--seed", "9", "--as", "amostra", "--out", str(tmp_path)])  # fmt: skip
    assert code == 0
    bundle = io.load_bipartite([tmp_path], "amostra")
    assert len(bundle.students) == 25
    assert set(io.load_outcomes([tmp_path], "amostra").final_result) == bundle.students
    validate_dataset([tmp_path], "amostra")


def test_data_cohort_e_project_k_core_pela_cli(tmp_path: Path, bipartite_por_apresentacao) -> None:
    from edugraph.__main__ import main

    io.save_bipartite(bipartite_por_apresentacao, tmp_path)  # dataset "sp", sem outcomes
    code = main(["data", "cohort", "--root", str(tmp_path), "--dataset", "sp",
                 "--cohort", "2024J", "--as", "sp_2024j", "--out", str(tmp_path)])  # fmt: skip
    assert code == 0
    coorte = io.load_bipartite([tmp_path], "sp_2024j")
    assert all(d.endswith("_2024J") for d in coorte.disciplines)

    code = main(["data", "project", "--root", str(tmp_path), "--dataset", "sp_2024j",
                 "--side", "student", "--weighting", "simple", "--k-core", "2",
                 "--out", str(tmp_path)])  # fmt: skip
    assert code == 0
    projection = io.load_projection([tmp_path], "sp_2024j", "student_simple")
    assert reductions_of(projection.meta)[0]["kind"] == "k_core"
