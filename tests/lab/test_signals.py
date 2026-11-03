"""Sinais por aluno  ``[T]`` — risco de evasão e possíveis talentos (ADR-0013).

Os valores esperados dos casos pequenos foram derivados no papel, não
copiados da saída: um aluno com uma matrícula só e nota baixa, numa turma
em que todos cursam três disciplinas com nota boa, tem carga e intensidade
muito abaixo da média (z < -2 nos dois), e portanto risco ≥ 0,70; o aluno
oposto não tem componente de risco algum.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from edugraph.api.app import create_app
from edugraph.community.evaluate import outcomes_by_group, rank_auc
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.types import Meta, Outcomes
from edugraph.lab import signals
from edugraph.lab.service import run_lab, signal_validation

DISCIPLINAS = {"D1": "Algoritmos", "D2": "Redes", "D3": "Banco de Dados", "D4": "Segurança"}


def _turma(pesos_planos: bool = False) -> tuple[nx.Graph, nx.Graph, dict[str, int]]:
    """12 alunos. ``s11`` cursa uma disciplina com nota 52; ``s12`` cursa as quatro com 95."""
    bip: nx.Graph = nx.Graph()
    proj: nx.Graph = nx.Graph()
    for d, nome in DISCIPLINAS.items():
        bip.add_node(d, kind="discipline", label=nome)
    for i in range(1, 11):
        s = f"s{i}"
        bip.add_node(s, kind="student", label=f"Aluno {i}")
        for d in list(DISCIPLINAS)[(i % 2) : (i % 2) + 3]:
            bip.add_edge(s, d, weight=1.0 if pesos_planos else 70.0)
    bip.add_node("s11", kind="student", label="Aluno 11")
    bip.add_edge("s11", "D1", weight=1.0 if pesos_planos else 52.0)
    bip.add_node("s12", kind="student", label="Aluno 12")
    for d in DISCIPLINAS:
        bip.add_edge("s12", d, weight=1.0 if pesos_planos else 95.0)
    membership = {f"s{i}": 0 for i in range(1, 13)}
    for s in membership:
        proj.add_node(s, kind="student", label=bip.nodes[s]["label"])
    return proj, bip, membership


def _sinais(**kwargs: Any) -> dict[str, Any]:
    proj, bip, membership = _turma(kwargs.pop("pesos_planos", False))
    membership.update(kwargs.pop("membership", {}))
    return signals.student_signals(
        proj, bip, membership, {}, criterion=kwargs.pop("criterion", "score_threshold")
    )


def test_aluno_com_uma_matricula_e_nota_baixa_tem_risco_alto_e_o_oposto_nao_tem() -> None:
    alunos = _sinais()["students"]
    assert alunos["s11"]["tier"] == "alto"
    assert alunos["s11"]["risk"] >= 0.70
    assert alunos["s11"]["profile"] == "risco"
    assert alunos["s12"]["tier"] == "baixo"
    assert alunos["s12"]["risk"] == 0.0


def test_o_porque_do_risco_diz_a_carga_e_a_nota() -> None:
    why = _sinais()["students"]["s11"]["why"]
    assert any(f.startswith("cursa só 1 disciplina") for f in why)
    assert any("nota média 52" in f for f in why)


def test_aluno_de_alta_nota_vira_talento_e_lidera_a_lista() -> None:
    resultado = _sinais()
    s12 = resultado["students"]["s12"]
    assert s12["talent"] and s12["profile"] == "talento"
    assert "desempenho" in s12["tags"]
    assert resultado["talents"][0] == "s12"
    assert resultado["attention"][0] == "s11"


def test_aluno_em_risco_nunca_e_talento() -> None:
    for entrada in _sinais()["students"].values():
        assert not (entrada["talent"] and entrada["tier"] != "baixo")


def test_sem_variacao_de_peso_a_intensidade_nao_entra_na_conta() -> None:
    resultado = _sinais(pesos_planos=True, criterion="vle_activity")
    assert resultado["flat_intensity"] is True
    # Só a carga conta: s11 (1 disciplina) segue sinalizado; s12 (4) não.
    assert resultado["students"]["s11"]["tier"] != "baixo"
    assert resultado["students"]["s12"]["tier"] == "baixo"
    assert not any("nota" in f for f in resultado["students"]["s11"].get("why", []))


def test_aluno_num_grupo_so_dele_ganha_o_componente_de_vinculo_inteiro() -> None:
    resultado = _sinais(membership={"s11": 1})
    assert any("grupo só dele" in f for f in resultado["students"]["s11"]["why"])


def test_turma_de_menos_de_tres_alunos_nao_tem_sinais() -> None:
    proj, bip, _ = _turma()
    assert signals.student_signals(proj, bip, {"s1": 0, "s2": 0}, {}) == {}


def test_os_sinais_saem_iguais_para_a_mesma_turma() -> None:
    raizes = ArtifactRoots(["data/fixtures"])
    a = run_lab(roots=raizes, source="demo", students=45, seed=12, noise=0.2)
    b = run_lab(roots=raizes, source="demo", students=45, seed=12, noise=0.2)
    assert a["insight"]["signals"] == b["insight"]["signals"]


# ---------------------------------------------------------------------
# Conferência com o desfecho (evaluate.py)
# ---------------------------------------------------------------------


def _desfechos(final_result: dict[str, str]) -> Outcomes:
    return Outcomes(final_result=final_result, planted_group={}, meta=Meta(producer="teste"))


def test_auc_perfeito_quando_o_maior_risco_e_quem_desistiu() -> None:
    saida = _desfechos({"a": "Withdrawn", "b": "Pass", "c": "Pass"})
    assert rank_auc({"a": 3.0, "b": 2.0, "c": 1.0}, saida) == 1.0
    assert rank_auc({"a": 1.0, "b": 2.0, "c": 3.0}, saida) == 0.0


def test_auc_com_empate_total_e_acaso() -> None:
    saida = _desfechos({"a": "Fail", "b": "Pass", "c": "Pass", "d": "Distinction"})
    assert rank_auc(dict.fromkeys("abcd", 1.0), saida) == 0.5


def test_auc_sem_um_dos_lados_nao_existe() -> None:
    assert rank_auc({"a": 1.0, "b": 2.0}, _desfechos({"a": "Pass", "b": "Pass"})) is None


def test_desfecho_por_grupo_conta_so_quem_tem_rotulo() -> None:
    saida = _desfechos({"a": "Fail", "b": "Pass", "c": "Withdrawn"})
    r = outcomes_by_group({"a": "x", "b": "x", "c": "y", "d": "y"}, saida)
    assert r["groups"]["x"]["n"] == 2 and r["groups"]["x"]["rates"]["Fail"] == 0.5
    assert r["groups"]["y"]["n"] == 2 and r["groups"]["y"]["n_labeled"] == 1
    assert r["groups"]["y"]["rates"]["Withdrawn"] == 1.0
    assert r["base"]["n_labeled"] == 3


def test_validacao_dos_sinais_confere_risco_e_talento_contra_o_desfecho() -> None:
    saida = _desfechos(
        {**{f"s{i}": "Pass" for i in range(1, 11)}, "s11": "Withdrawn", "s12": "Distinction"}
    )
    v = signal_validation(_sinais(), saida)
    assert v is not None
    assert v["risk"]["groups"]["alto"]["rates"]["Withdrawn"] == 1.0
    assert v["talent"]["groups"]["talento"]["rates"]["Distinction"] == 1.0
    assert v["auc_withdrawn"] == 1.0


# ---------------------------------------------------------------------
# O que a tela e a API recebem
# ---------------------------------------------------------------------


def test_laboratorio_devolve_sinais_para_cada_aluno_e_a_conferencia_so_na_revelacao() -> None:
    run = run_lab(
        roots=ArtifactRoots(["data/fixtures"]), source="demo", students=60, seed=1, noise=0.35
    )
    sinais = run["insight"]["signals"]
    assert set(sinais["students"]) == {n["id"] for n in run["projection"]["nodes"]}
    assert sinais["counts"]["total"] == len(sinais["students"])
    assert "risk" in run["reveal"]["signals"]
    # A conferência fica na revelação, nunca dentro da leitura (ADR-0008).
    assert "auc" not in str(run["insight"])


def test_projecao_de_disciplinas_nao_tem_sinais_de_aluno() -> None:
    run = run_lab(
        roots=ArtifactRoots(["data/fixtures"]),
        source="demo",
        students=45,
        seed=12,
        side="discipline",
    )
    assert run["insight"]["signals"] is None
    assert "signals" not in run["reveal"]


@pytest.mark.dataset("synthetic_v1")
def test_api_devolve_sinais_na_leitura_e_a_conferencia_so_no_desfecho(artifact_roots) -> None:
    client = TestClient(create_app(artifact_roots))
    base = "/datasets/synthetic_v1/communities/louvain__student_simple"
    leitura = client.get(f"{base}/insight").json()
    assert leitura["signals"]["counts"]["total"] > 0
    assert "Withdrawn" not in str(leitura["signals"])
    desfecho = client.get(f"{base}/outcomes").json()
    assert set(desfecho["signals"]["risk"]["groups"]) <= {"alto", "atencao", "baixo"}
