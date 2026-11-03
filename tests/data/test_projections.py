"""Projeções à mão  ``[A]`` — specs A-04 (fechada) e A-05.

Os valores esperados vêm de ``data/fixtures/tiny_v1/expected/``, que foi
derivado no papel (ver o README de lá). Comparar a implementação com a
fixture gerada pelo NetworkX seria comparar duas bibliotecas; comparar
com a derivação à mão é verificar o algoritmo.

A A-05 está fechada: a comparação com o NetworkX roda sem ``xfail``.
"""

from __future__ import annotations

import csv
from pathlib import Path

import networkx as nx
import pytest

from edugraph.contracts import io
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.types import BipartiteBundle, ProjectionSpec
from edugraph.contracts.validate import validate_projection
from edugraph.data.projection.manual import (
    PRODUCER,
    ResourceAllocationProjection,
    SimpleProjection,
)

pytestmark = pytest.mark.dataset("tiny_v1")


def _expected_edges(path: Path) -> dict[tuple[str, str], float]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            (row["source"], row["target"]): float(row["weight"]) for row in csv.DictReader(handle)
        }


def _edges_of(bundle) -> dict[tuple[str, str], float]:
    return {tuple(sorted((u, v))): d["weight"] for u, v, d in bundle.graph.edges(data=True)}


# ---------------------------------------------------------------------
# A-04 — valores derivados no papel
# ---------------------------------------------------------------------


def test_projecao_simples_aluno_bate_com_o_calculo_a_mao(
    tiny_bipartite: BipartiteBundle, tiny_expected: Path
) -> None:
    """Pesos de ``student_simple`` = nº de disciplinas em comum."""
    spec = ProjectionSpec(side="student", weighting="simple")
    bundle = SimpleProjection().project(tiny_bipartite, spec)

    esperado = _expected_edges(tiny_expected / "student_simple.csv")
    assert _edges_of(bundle) == pytest.approx(esperado)


def test_alocacao_de_recursos_bate_com_o_calculo_a_mao(
    tiny_bipartite: BipartiteBundle, tiny_expected: Path
) -> None:
    """Cada vizinho comum contribui com ``1/grau`` (Zhou et al., 2007)."""
    spec = ProjectionSpec(side="student", weighting="resource_allocation")
    bundle = ResourceAllocationProjection().project(tiny_bipartite, spec)

    esperado = _expected_edges(tiny_expected / "student_resource_allocation.csv")
    assert _edges_of(bundle) == pytest.approx(esperado)


def test_projecao_disciplina_disciplina_existe(
    tiny_bipartite: BipartiteBundle, tiny_expected: Path
) -> None:
    """A projeção do lado das disciplinas — a seção 13 do briefing avisa
    que é fácil esquecer dela, e é ela que responde às disciplinas críticas."""
    spec = ProjectionSpec(side="discipline", weighting="simple")
    bundle = SimpleProjection().project(tiny_bipartite, spec)

    esperado = _expected_edges(tiny_expected / "discipline_simple.csv")
    assert _edges_of(bundle) == pytest.approx(esperado)


def test_alocacao_de_recursos_no_lado_disciplina(
    tiny_bipartite: BipartiteBundle, tiny_expected: Path
) -> None:
    """DA-DB = 1/2 + 1/2 + 1/3: S1 e S2 (grau 2) pesam mais que S3 (grau 3)."""
    spec = ProjectionSpec(side="discipline", weighting="resource_allocation")
    bundle = ResourceAllocationProjection().project(tiny_bipartite, spec)

    esperado = _expected_edges(tiny_expected / "discipline_resource_allocation.csv")
    assert _edges_of(bundle) == pytest.approx(esperado)


def test_as_duas_ponderacoes_ordenam_pares_de_forma_diferente(
    tiny_bipartite: BipartiteBundle,
) -> None:
    """O ponto da alocação de recursos, em um teste.

    Em ``tiny_v1``, S1-S6 e S3-S4 empatam em 1 na projeção simples. Na
    alocação de recursos, S1-S6 = 0,25 e S3-S4 = 1/3: a disciplina rara
    (DC, grau 3) vale mais que a popular (DA, grau 4). Se este teste
    passar a falhar, a correção de viés se perdeu.
    """
    simples = SimpleProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    ra = ResourceAllocationProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="resource_allocation")
    )

    assert simples.graph["S1"]["S6"]["weight"] == simples.graph["S3"]["S4"]["weight"]
    assert ra.graph["S1"]["S6"]["weight"] < ra.graph["S3"]["S4"]["weight"]


# ---------------------------------------------------------------------
# A-04 — contrato e coerência com a fixture
# ---------------------------------------------------------------------


@pytest.mark.parametrize("side", ["student", "discipline"])
@pytest.mark.parametrize("weighting", ["simple", "resource_allocation"])
def test_projecao_passa_no_validador_de_contrato(
    tiny_bipartite: BipartiteBundle, side: str, weighting: str
) -> None:
    """Sem laço, um só lado, peso finito e positivo."""
    algorithm = SimpleProjection() if weighting == "simple" else ResourceAllocationProjection()
    bundle = algorithm.project(tiny_bipartite, ProjectionSpec(side=side, weighting=weighting))  # type: ignore[arg-type]
    validate_projection(bundle)
    assert bundle.meta.producer == PRODUCER
    assert bundle.source == tiny_bipartite.spec


@pytest.mark.dataset("synthetic_v1")
@pytest.mark.parametrize("side", ["student", "discipline"])
@pytest.mark.parametrize("weighting", ["simple", "resource_allocation"])
def test_reproduz_a_fixture_synthetic_v1(
    artifact_roots: ArtifactRoots, side: str, weighting: str
) -> None:
    """A implementação da frente produz o mesmo grafo que a referência do dia 0.

    É o critério que permite aposentar ``project_reference`` de
    ``scripts/make_fixtures.py`` quando a A-03 fechar: se os dois
    concordam em 98 nós e 1.971 arestas com pesos fracionários, o
    algoritmo está certo além do caso conferível à mão.
    """
    bipartite = io.load_bipartite(artifact_roots, "synthetic_v1")
    spec = ProjectionSpec(side=side, weighting=weighting)  # type: ignore[arg-type]
    algorithm = SimpleProjection() if weighting == "simple" else ResourceAllocationProjection()
    produzido = algorithm.project(bipartite, spec)
    fixture = io.load_projection(artifact_roots, "synthetic_v1", spec.projection_id)

    assert set(produzido.graph.nodes) == set(fixture.graph.nodes)
    assert _edges_of(produzido) == pytest.approx(_edges_of(fixture), abs=1e-12)


def test_no_isolado_permanece_na_projecao() -> None:
    """Um aluno que não compartilha disciplina com ninguém continua sendo nó.

    Ele existe no bipartido, então existe na projeção — só não tem
    aresta. Removê-lo mudaria ``n_nodes`` entre bipartido e projeção e
    quebraria o cruzamento que o validador de partição faz.
    """
    from edugraph.contracts.types import BipartiteSpec

    graph = nx.Graph()
    graph.add_node("S1", kind="student", label="1")
    graph.add_node("S2", kind="student", label="2")
    graph.add_node("S3", kind="student", label="3")
    graph.add_node("DA", kind="discipline", label="A")
    graph.add_node("DB", kind="discipline", label="B")
    graph.add_edge("S1", "DA", weight=70.0)
    graph.add_edge("S2", "DA", weight=70.0)
    graph.add_edge("S3", "DB", weight=70.0)  # S3 está sozinho em DB

    bundle = SimpleProjection().project(
        BipartiteBundle(graph=graph, spec=BipartiteSpec(dataset="t")),
        ProjectionSpec(side="student", weighting="simple"),
    )
    assert set(bundle.graph.nodes) == {"S1", "S2", "S3"}
    assert bundle.graph.degree("S3") == 0
    assert bundle.graph["S1"]["S2"]["weight"] == 1.0


def test_min_weight_e_honrado_quando_declarado(tiny_bipartite: BipartiteBundle) -> None:
    """Com ``min_weight`` na spec, nenhuma aresta abaixo sobrevive.

    A estratégia de escala é a A-06; aqui só se garante que um
    ``ProjectionSpec`` com corte nunca gera artefato inválido.
    """
    spec = ProjectionSpec(side="student", weighting="simple", min_weight=2.0)
    bundle = SimpleProjection().project(tiny_bipartite, spec)

    assert all(d["weight"] >= 2.0 for _, _, d in bundle.graph.edges(data=True))
    assert bundle.graph.number_of_edges() == 3  # só S1-S2, S1-S3, S2-S3
    validate_projection(bundle)


def test_algoritmo_recusa_ponderacao_errada(tiny_bipartite: BipartiteBundle) -> None:
    """``manual_simple`` não aceita uma spec de alocação de recursos, e vice-versa."""
    with pytest.raises(ValueError, match="simple"):
        SimpleProjection().project(
            tiny_bipartite, ProjectionSpec(side="student", weighting="resource_allocation")
        )
    with pytest.raises(ValueError, match="resource_allocation"):
        ResourceAllocationProjection().project(
            tiny_bipartite, ProjectionSpec(side="student", weighting="simple")
        )


# ---------------------------------------------------------------------
# A-05 — à mão × NetworkX
# ---------------------------------------------------------------------


def test_manual_e_networkx_batem_ate_1e9(tiny_bipartite: BipartiteBundle) -> None:
    """A comparação que vira tabela do capítulo 3 (ADR-0010)."""
    from edugraph.data.projection.compare import TOLERANCE, compare
    from edugraph.data.projection.networkx_ref import NetworkXSimpleProjection

    spec = ProjectionSpec(side="student", weighting="simple")
    resultado = compare(
        SimpleProjection().project(tiny_bipartite, spec),
        NetworkXSimpleProjection().project(tiny_bipartite, spec),
    )
    assert resultado["max_abs_diff"] < TOLERANCE
    assert resultado["equal_within_tolerance"] is True


@pytest.mark.dataset("synthetic_v1")
@pytest.mark.parametrize("side", ["student", "discipline"])
@pytest.mark.parametrize("weighting", ["simple", "resource_allocation"])
def test_as_quatro_projecoes_batem_com_a_referencia(
    artifact_roots: ArtifactRoots, side: str, weighting: str
) -> None:
    """Em synthetic_v1 (98 nós, 1.971 arestas), as duas implementações concordam."""
    from edugraph.data.projection.compare import TOLERANCE, compare_implementations

    bipartite = io.load_bipartite(artifact_roots, "synthetic_v1")
    row = compare_implementations(bipartite, ProjectionSpec(side=side, weighting=weighting))  # type: ignore[arg-type]

    assert row["equal_within_tolerance"] is True
    assert row["max_abs_diff"] < TOLERANCE
    assert row["n_edges_manual"] == row["n_edges_networkx"]
    assert row["runtime_manual_s"] >= 0 and row["runtime_networkx_s"] >= 0


def test_collaboration_do_networkx_nao_e_alocacao_de_recursos(
    tiny_bipartite: BipartiteBundle,
) -> None:
    """Newman (1/(k−1)) ≠ Zhou (1/k): a spec A-05 exigia verificar, não supor.

    Em ``tiny_v1``, DA tem grau 4: contribui 1/3 por Newman e 1/4 por
    Zhou. Se este teste um dia passar a falhar, é porque o NetworkX mudou
    a fórmula — e a documentação precisa ser revista.
    """
    from edugraph.data.projection.networkx_ref import newman_collaboration_projection

    spec = ProjectionSpec(side="student", weighting="resource_allocation")
    zhou = ResourceAllocationProjection().project(tiny_bipartite, spec)
    newman = newman_collaboration_projection(tiny_bipartite, spec)

    # S1-S6 só compartilham DA (grau 4)
    assert zhou.graph["S1"]["S6"]["weight"] == pytest.approx(1 / 4)
    assert newman.graph["S1"]["S6"]["weight"] == pytest.approx(1 / 3)
    assert _edges_of(zhou) != pytest.approx(_edges_of(newman))


def test_aresta_faltante_e_diferenca_infinita(tiny_bipartite: BipartiteBundle) -> None:
    """Uma aresta presente em uma e ausente na outra não pode virar 'peso zero'."""
    from edugraph.data.projection.compare import compare

    spec = ProjectionSpec(side="student", weighting="simple")
    a = SimpleProjection().project(tiny_bipartite, spec)
    b = SimpleProjection().project(tiny_bipartite, spec)
    b.graph.remove_edge("S4", "S5")

    row = compare(a, b)
    assert row["max_abs_diff"] == float("inf")
    assert row["equal_within_tolerance"] is False
    assert row["n_edges_manual"] == row["n_edges_networkx"] + 1


def test_compare_recusa_projecoes_incomparaveis(tiny_bipartite: BipartiteBundle) -> None:
    from edugraph.contracts.errors import ContractError
    from edugraph.data.projection.compare import compare

    student = SimpleProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    discipline = SimpleProjection().project(
        tiny_bipartite, ProjectionSpec(side="discipline", weighting="simple")
    )
    with pytest.raises(ContractError, match="incompar"):
        compare(student, discipline)


def test_metrics_projections_e_idempotente(tiny_bipartite: BipartiteBundle, tmp_path: Path) -> None:
    """Rodar duas vezes atualiza as 4 linhas em vez de duplicá-las."""
    from edugraph.data.projection.compare import METRICS_COLUMNS, compare_all, write_metrics

    rows = compare_all(tiny_bipartite)
    write_metrics(rows, tmp_path, "tiny_v1")
    write_metrics(rows, tmp_path, "tiny_v1")

    lidas = io.load_metrics([tmp_path], "tiny_v1", "projections")
    assert len(lidas) == 4
    assert set(lidas[0]) == set(METRICS_COLUMNS)
    assert {r["projection_id"] for r in lidas} == {
        "student_simple",
        "student_resource_allocation",
        "discipline_simple",
        "discipline_resource_allocation",
    }
    assert all(r["equal_within_tolerance"] == "true" for r in lidas)


def test_weight_distribution_soma_as_arestas(tiny_bipartite: BipartiteBundle) -> None:
    from edugraph.data.projection.compare import weight_distribution

    bundle = ResourceAllocationProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="resource_allocation")
    )
    hist = weight_distribution(bundle, bins=5)
    assert len(hist["bin_edges"]) == 6
    assert sum(hist["counts"]) == bundle.graph.number_of_edges() == 9


def test_figura_das_ponderacoes_e_gravada(tiny_bipartite: BipartiteBundle, tmp_path: Path) -> None:
    """PNG e SVG saem com o nome canônico; sem teste de aparência."""
    from edugraph.data.report import figure_weight_distributions

    simple = SimpleProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    ra = ResourceAllocationProjection().project(
        tiny_bipartite, ProjectionSpec(side="student", weighting="resource_allocation")
    )
    png = figure_weight_distributions(simple, ra, tmp_path)

    assert png.name == "fig3-ponderacoes-tiny_v1-student.png"
    assert png.exists() and png.stat().st_size > 0
    assert png.with_suffix(".svg").exists()


def test_data_compare_grava_tabela_e_figura(tmp_path: Path) -> None:
    from edugraph.__main__ import main

    code = main(["data", "compare", "--root", "data/fixtures", "--dataset", "tiny_v1",
                 "--out", str(tmp_path), "--figures", str(tmp_path / "fig")])  # fmt: skip
    assert code == 0
    assert (tmp_path / "tiny_v1" / "metrics" / "projections.csv").exists()
    assert (tmp_path / "fig" / "fig3-ponderacoes-tiny_v1-student.png").exists()
    assert (tmp_path / "fig" / "fig3-ponderacoes-tiny_v1-discipline.png").exists()
