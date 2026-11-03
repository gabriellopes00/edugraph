"""Cache de uma projeção  ``[T]`` — ADR-0013.

O que se promete: o segundo pedido pelo mesmo grafo não relê o CSV; um
grafo diferente ocupa o lugar do anterior (o teto de memória é uma
projeção); e regenerar o arquivo invalida a entrada.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from edugraph.api import projection_cache
from edugraph.contracts.paths import ArtifactRoots

DATASET = "synthetic_v1"


@pytest.fixture
def raiz(tmp_path: Path, artifact_roots: ArtifactRoots) -> ArtifactRoots:
    """Cópia descartável de um dataset: o teste mexe no mtime de um arquivo."""
    origem = artifact_roots.find(DATASET, "projections", "student_simple", "edges.csv").parents[3]
    shutil.copytree(origem / DATASET, tmp_path / DATASET)
    projection_cache.clear()
    yield ArtifactRoots([tmp_path])
    projection_cache.clear()


@pytest.mark.dataset("synthetic_v1")
def test_segundo_pedido_pelo_mesmo_grafo_devolve_o_mesmo_objeto(raiz: ArtifactRoots) -> None:
    a = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    b = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    assert a is b


@pytest.mark.dataset("synthetic_v1")
def test_outro_grafo_toma_o_lugar_do_anterior(raiz: ArtifactRoots) -> None:
    a = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    projection_cache.load_projection_cached(raiz, DATASET, "discipline_simple")
    de_novo = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    assert de_novo is not a, "só uma projeção fica em memória"


@pytest.mark.dataset("synthetic_v1")
def test_regenerar_o_arquivo_invalida_a_entrada(raiz: ArtifactRoots) -> None:
    a = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    arquivo = raiz.find(DATASET, "projections", "student_simple", "edges.csv")
    antes = arquivo.stat().st_mtime_ns
    os.utime(arquivo, ns=(antes + 5_000_000_000, antes + 5_000_000_000))
    b = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    assert b is not a


@pytest.mark.dataset("synthetic_v1")
def test_resultado_caro_e_guardado_enquanto_a_projecao_esta_em_cache(raiz: ArtifactRoots) -> None:
    projecao = projection_cache.load_projection_cached(raiz, DATASET, "student_simple")
    chamadas: list[int] = []

    def caro() -> str:
        chamadas.append(1)
        return "esqueleto"

    assert projection_cache.remember(projecao, ("k", 1), caro) == "esqueleto"
    assert projection_cache.remember(projecao, ("k", 1), caro) == "esqueleto"
    assert len(chamadas) == 1

    projection_cache.load_projection_cached(raiz, DATASET, "discipline_simple")
    projection_cache.remember(projecao, ("k", 1), caro)
    assert len(chamadas) == 2, "trocar de projeção descarta o que foi guardado da anterior"


@pytest.mark.dataset("synthetic_v1")
def test_grafo_inexistente_continua_dando_artefato_nao_encontrado(raiz: ArtifactRoots) -> None:
    from edugraph.contracts.errors import ArtifactNotFoundError

    with pytest.raises(ArtifactNotFoundError):
        projection_cache.load_projection_cached(raiz, DATASET, "nao_existe")
