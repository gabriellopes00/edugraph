"""``scripts/iniciar.py --oulad``: instalar um ZIP de resultados do OULAD."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "iniciar.py"


@pytest.fixture
def iniciar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """O script carregado como módulo, com a raiz do repositório em ``tmp_path``."""
    spec = importlib.util.spec_from_file_location("iniciar", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "PROCESSED", tmp_path / "data" / "processed")
    return module


def _zip(path: Path, *names: str) -> Path:
    with zipfile.ZipFile(path, "w") as handle:
        for name in names:
            handle.writestr(name, "id,kind,label\n")
    return path


@pytest.mark.parametrize(
    "prefixo", ["", "processed/", "data/processed/", "entrega/data/processed/"]
)
def test_acha_o_dataset_em_qualquer_nivel_do_zip(
    iniciar: ModuleType, tmp_path: Path, prefixo: str
) -> None:
    arquivo = _zip(tmp_path / "r.zip", f"{prefixo}oulad_x/bipartite/nodes.csv")

    assert iniciar.instalar_oulad(arquivo) == ["oulad_x"]
    assert (tmp_path / "data/processed/oulad_x/bipartite/nodes.csv").is_file()


def test_nao_sobrescreve_dataset_que_ja_existe(iniciar: ModuleType, tmp_path: Path) -> None:
    existente = tmp_path / "data/processed/oulad_x/bipartite/nodes.csv"
    existente.parent.mkdir(parents=True)
    existente.write_text("original", encoding="utf-8")
    arquivo = _zip(tmp_path / "r.zip", "oulad_x/bipartite/nodes.csv")

    assert iniciar.instalar_oulad(arquivo) == ["oulad_x"]
    assert existente.read_text(encoding="utf-8") == "original"


def test_recusa_o_oulad_bruto(iniciar: ModuleType, tmp_path: Path) -> None:
    arquivo = _zip(tmp_path / "r.zip", "oulad/studentInfo.csv")

    assert iniciar.instalar_oulad(arquivo) == []
    assert not (tmp_path / "data/processed").exists()


def test_arquivo_ausente_ou_invalido_nao_instala_e_nao_quebra(
    iniciar: ModuleType, tmp_path: Path
) -> None:
    invalido = tmp_path / "ruim.zip"
    invalido.write_text("não é zip", encoding="utf-8")

    assert iniciar.instalar_oulad(tmp_path / "nao-existe.zip") == []
    assert iniciar.instalar_oulad(invalido) == []


def test_zip_sem_dataset_nao_instala_nada(iniciar: ModuleType, tmp_path: Path) -> None:
    arquivo = _zip(tmp_path / "r.zip", "leia-me.txt")

    assert iniciar.instalar_oulad(arquivo) == []


def test_nao_deixa_pasta_temporaria_em_data(iniciar: ModuleType, tmp_path: Path) -> None:
    iniciar.instalar_oulad(_zip(tmp_path / "r.zip", "oulad_x/bipartite/nodes.csv"))

    assert [p.name for p in (tmp_path / "data").iterdir()] == ["processed"]
