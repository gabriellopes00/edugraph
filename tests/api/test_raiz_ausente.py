"""Sistema sem os resultados do OULAD  ``[T]``.

Quem recebe o repositório costuma rodar só o sintético: os resultados do
OULAD (``data/processed/``) levam horas para gerar e ficam fora do git. O
sistema precisa funcionar do mesmo jeito sem essa pasta: a API sobe, o
laboratório monta a turma de Computação e o explorador lista só as
fixtures. Aqui a primeira raiz **não existe**, como no caso de um clone
limpo com ``--root data/processed --root data/fixtures``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from edugraph.api.app import create_app
from edugraph.contracts.paths import ArtifactRoots

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    sem_oulad = tmp_path / "data" / "processed"  # nunca criada
    assert not sem_oulad.exists()
    return TestClient(create_app([sem_oulad, FIXTURES]))


def test_api_sobe_e_lista_so_as_fixtures_quando_a_raiz_do_oulad_nao_existe(
    client: TestClient,
) -> None:
    assert client.get("/health").status_code == 200
    ids = {d["dataset"] for d in client.get("/datasets").json()["datasets"]}
    assert ids >= {"synthetic_v1", "synthetic_v2", "tiny_v1"}
    assert not any(i.startswith("oulad") for i in ids)


def test_laboratorio_oferece_a_demo_e_as_fixtures_sem_o_oulad(client: TestClient) -> None:
    fontes = [s["id"] for s in client.get("/lab/options").json()["sources"]]
    assert fontes[0] == "demo"
    assert "synthetic_v1" in fontes
    assert not any(f.startswith("oulad") for f in fontes)


def test_laboratorio_monta_a_turma_de_computacao_sem_o_oulad(client: TestClient) -> None:
    resposta = client.post("/lab/run", json={"students": 30, "seed": 3})
    assert resposta.status_code == 200
    assert resposta.json()["result"]["n_communities"] >= 2


def test_raiz_inexistente_sozinha_nao_quebra_a_listagem(tmp_path: Path) -> None:
    assert ArtifactRoots([tmp_path / "nada"]).datasets() == []
