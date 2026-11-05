"""Tabela comparativa e concordância entre partições  ``[B]`` — spec B-04.

``metrics/communities.csv`` é a **tabela principal do capítulo 3**. O que
os testes protegem aqui é menos a aritmética e mais as três promessas
que ela faz ao leitor do artigo: as colunas são sempre as mesmas, rodar
de novo atualiza em vez de duplicar, e a execução que estourou o
orçamento **aparece**, com o status ao lado (ADR-0006).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edugraph.community.compare import (
    METRICS_COLUMNS,
    adjusted_rand_index,
    agreement,
    agreement_matrix,
    compare,
    normalized_mutual_information,
    to_metrics_row,
    write_metrics,
)
from edugraph.contracts import io
from edugraph.contracts.errors import ContractError
from edugraph.contracts.types import Meta, Partition


def _partition(
    algorithm: str = "louvain",
    projection_id: str = "student_simple",
    *,
    membership: dict[str, int] | None = None,
    status: str = "ok",
    modularity: float = 0.5,
    runtime_s: float = 1.0,
) -> Partition:
    """Partição de mentira, para testar a tabela sem rodar algoritmo."""
    membership = membership or {"S1": 0, "S2": 0, "S3": 1}
    return Partition(
        algorithm=algorithm,  # type: ignore[arg-type]
        projection_id=projection_id,
        membership=membership,
        modularity=modularity,
        n_communities=len(set(membership.values())),
        runtime_s=runtime_s,
        params={"seed": 42},
        status=status,  # type: ignore[arg-type]
        meta=Meta(producer="teste"),
    )


# ---------------------------------------------------------------------
# A linha e a tabela
# ---------------------------------------------------------------------


def test_linha_tem_exatamente_as_colunas_do_contrato() -> None:
    row = to_metrics_row(_partition(), "synthetic_v1")

    assert list(row) == list(METRICS_COLUMNS)
    assert row["largest_community"] == 2
    assert json.loads(row["params"]) == {"seed": 42}


def test_params_saem_em_json_estavel() -> None:
    """A célula precisa ser a mesma a cada execução, e voltar a ser dicionário."""
    partition = _partition()
    partition.params = {"seed": 42, "resolution": 1.0, "implementation": "python_louvain"}

    primeira = to_metrics_row(partition, "x")["params"]
    segunda = to_metrics_row(partition, "x")["params"]

    assert primeira == segunda
    assert json.loads(primeira)["implementation"] == "python_louvain"


def test_linha_com_timeout_entra_na_tabela() -> None:
    """Omiti-la seria esconder o resultado que o briefing §8 manda reportar."""
    rows = compare(
        [
            _partition("louvain", runtime_s=0.02),
            _partition("girvan_newman", status="timeout", modularity=0.1, runtime_s=300.0),
        ],
        "synthetic_v1",
    )

    assert len(rows) == 2
    status = {row["algorithm"]: row["status"] for row in rows}
    assert status == {"louvain": "ok", "girvan_newman": "timeout"}


def test_tabela_sai_ordenada_pela_chave() -> None:
    rows = compare(
        [
            _partition("louvain", "student_simple"),
            _partition("girvan_newman", "student_simple"),
            _partition("louvain", "discipline_simple"),
        ],
        "synthetic_v1",
    )
    assert [(r["projection_id"], r["algorithm"]) for r in rows] == [
        ("discipline_simple", "louvain"),
        ("student_simple", "girvan_newman"),
        ("student_simple", "louvain"),
    ]


def test_rodar_duas_vezes_atualiza_a_linha_em_vez_de_duplicar(tmp_path: Path) -> None:
    """Idempotência por ``(dataset, projection_id, algorithm)``."""
    write_metrics(compare([_partition(modularity=0.40)], "synthetic_v1"), tmp_path, "synthetic_v1")
    path = write_metrics(
        compare([_partition(modularity=0.47)], "synthetic_v1"), tmp_path, "synthetic_v1"
    )

    linhas = path.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 2, "cabeçalho + uma linha só"
    assert "0.47" in linhas[1]


def test_mudar_as_colunas_levanta_erro_de_contrato(tmp_path: Path) -> None:
    """Mudar o esquema da tabela do capítulo 3 exige subir SCHEMA_VERSION."""
    write_metrics(compare([_partition()], "synthetic_v1"), tmp_path, "synthetic_v1")

    row = to_metrics_row(_partition(), "synthetic_v1")
    row["coluna_nova"] = 1
    del row["status"]

    with pytest.raises(ContractError):
        write_metrics([row], tmp_path, "synthetic_v1")


def test_linha_sem_coluna_obrigatoria_e_recusada(tmp_path: Path) -> None:
    row = to_metrics_row(_partition(), "synthetic_v1")
    del row["runtime_s"]

    with pytest.raises(ContractError, match="runtime_s"):
        write_metrics([row], tmp_path, "synthetic_v1")


# ---------------------------------------------------------------------
# Concordância entre partições
# ---------------------------------------------------------------------


def test_nmi_de_uma_particao_com_ela_mesma_e_um() -> None:
    partition = _partition(membership={"S1": 0, "S2": 0, "S3": 1, "S4": 2})
    assert agreement(partition, partition) == {"nmi": 1.0, "adjusted_rand": 1.0}


def test_renomear_comunidades_nao_muda_a_concordancia() -> None:
    """NMI e Rand comparam agrupamentos, não rótulos."""
    esquerda = {"S1": 0, "S2": 0, "S3": 1, "S4": 1}
    direita = {"S1": 5, "S2": 5, "S3": 9, "S4": 9}

    assert normalized_mutual_information(esquerda, direita) == pytest.approx(1.0)
    assert adjusted_rand_index(esquerda, direita) == pytest.approx(1.0)


def test_particoes_independentes_tem_concordancia_proxima_de_zero() -> None:
    """Metade para cada lado, sem relação: o Rand ajustado desconta o acaso."""
    nodes = [f"S{i}" for i in range(40)]
    esquerda = {node: index % 2 for index, node in enumerate(nodes)}
    direita = {node: (index // 20) for index, node in enumerate(nodes)}

    assert normalized_mutual_information(esquerda, direita) == pytest.approx(0.0, abs=1e-9)
    assert adjusted_rand_index(esquerda, direita) == pytest.approx(0.0, abs=0.05)


def test_particoes_triviais_sao_identicas_e_nao_zero_sobre_zero() -> None:
    """Entropia zero dos dois lados: a convenção é 1, não 0/0."""
    trivial = {"S1": 0, "S2": 0, "S3": 0}
    assert normalized_mutual_information(trivial, trivial) == 1.0
    assert adjusted_rand_index(trivial, trivial) == 1.0


def test_uma_trivial_e_outra_nao_da_concordancia_zero() -> None:
    trivial = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
    partida = {"S1": 0, "S2": 0, "S3": 1, "S4": 1}
    assert normalized_mutual_information(trivial, partida) == 0.0
    assert adjusted_rand_index(trivial, partida) == pytest.approx(0.0)


def test_comparar_particoes_de_grafos_diferentes_e_erro() -> None:
    """Um número calculado sobre conjuntos de nós diferentes não significaria nada."""
    esquerda = _partition(membership={"S1": 0, "S2": 1})
    direita = _partition(membership={"S1": 0, "S3": 1})

    with pytest.raises(ContractError, match="conjuntos de nós diferentes"):
        agreement(esquerda, direita)


def test_matriz_de_concordancia_so_cruza_a_mesma_projecao() -> None:
    partitions = [
        _partition("louvain", "student_simple"),
        _partition("girvan_newman", "student_simple"),
        _partition("louvain", "discipline_simple", membership={"D1": 0, "D2": 1, "D3": 1}),
    ]
    linhas = agreement_matrix(partitions)

    assert len(linhas) == 1
    assert linhas[0]["projection_id"] == "student_simple"
    assert {linhas[0]["left"], linhas[0]["right"]} == {"louvain", "girvan_newman"}


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------


@pytest.mark.dataset("synthetic_v1")
def test_compare_pela_cli_grava_a_tabela_principal(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """O caminho que a Frente B roda: louvain → compare → tabela."""
    from edugraph.__main__ import main

    assert main(["community", "louvain", "--root", "data/fixtures", "--dataset", "synthetic_v1",
                 "--projection", "student_simple", "--out", str(tmp_path)]) == 0  # fmt: skip
    capsys.readouterr()

    assert main(["community", "compare", "--root", str(tmp_path),
                 "--dataset", "synthetic_v1", "--out", str(tmp_path)]) == 0  # fmt: skip
    saida = capsys.readouterr().out

    path = tmp_path / "synthetic_v1" / "metrics" / "communities.csv"
    assert path.exists()
    assert path.read_text(encoding="utf-8").splitlines()[0].split(",")[:3] == [
        "dataset",
        "projection_id",
        "algorithm",
    ]
    assert "louvain" in saida

    rows = io.load_metrics([tmp_path], "synthetic_v1", "communities")
    assert len(rows) == 1 and rows[0]["status"] == "ok"


def test_compare_sem_particao_avisa_em_vez_de_quebrar(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    from edugraph.__main__ import main

    code = main(["community", "compare", "--root", str(tmp_path),
                 "--dataset", "vazio", "--out", str(tmp_path)])  # fmt: skip

    assert code == 1
    assert "nenhuma partição" in capsys.readouterr().out
