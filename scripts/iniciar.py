"""Sobe o projeto inteiro com um comando  ``[T]``.

    python scripts/iniciar.py                          # instala, confere, testa e abre a interface
    python scripts/iniciar.py --sem-testes             # pula o pytest (~20 s)
    python scripts/iniciar.py --oulad oulad-resultados.zip   # instala os resultados do OULAD antes
    python scripts/iniciar.py --porta 8001 --sem-navegador

Feito para quem avalia o trabalho: num clone recém-baixado, este script
cria a ``.venv``, instala o pacote, valida as fixtures, roda a suíte da
CI, compila o front-end (se houver Node) e abre o laboratório no
navegador. Cada passo já feito é pulado na rodada seguinte.

**Só biblioteca padrão**, de propósito: ele roda antes de o ``edugraph``
estar instalado. Todo o trabalho de verdade continua sendo
``python -m edugraph ...``, chamado pela ``.venv``.

Os resultados do OULAD (``--oulad``) chegam num ZIP à parte, porque
``data/processed/`` fica fora do git. O script aceita o ZIP com qualquer
pasta por cima (``data/processed/<dataset>/``, ``processed/<dataset>/``
ou ``<dataset>/`` direto): procura as pastas que têm ``bipartite/`` e as
copia para ``data/processed/``. Ver ``docs/entrega.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PROCESSED = ROOT / "data" / "processed"
FIXTURES = ROOT / "data" / "fixtures"
STATIC_INDEX = ROOT / "src" / "edugraph" / "api" / "static" / "index.html"
FRONTEND = ROOT / "frontend"

#: Grava o hash do ``pyproject.toml`` da última instalação: mudou, reinstala.
INSTALL_MARKER = VENV / ".edugraph-instalado"

MIN_PYTHON = (3, 11)


def passo(numero: int, total: int, texto: str) -> None:
    print(f"\n[iniciar] {numero}/{total} · {texto}", flush=True)


def aviso(texto: str) -> None:
    print(f"[iniciar] {texto}", flush=True)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def rodar(comando: list[str | Path], cwd: Path = ROOT) -> int:
    """Roda um comando mostrando a saída; devolve o código de saída."""
    return subprocess.call([str(c) for c in comando], cwd=cwd)


# ---------------------------------------------------------------------
# Passos
# ---------------------------------------------------------------------


def preparar_ambiente() -> bool:
    """Cria a ``.venv`` e instala o pacote, se ainda não estiver feito."""
    python = venv_python()
    if not python.exists():
        aviso(f"criando o ambiente em {VENV.name}/ …")
        if rodar([sys.executable, "-m", "venv", VENV]) != 0:
            aviso("não consegui criar a .venv.")
            return False

    assinatura = hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
    instalado = INSTALL_MARKER.exists() and (
        INSTALL_MARKER.read_text(encoding="utf-8").strip() == assinatura
    )
    if instalado and rodar([python, "-c", "import edugraph, pytest"]) == 0:
        aviso("ambiente já instalado.")
        return True

    aviso("instalando as dependências (~1 min na primeira vez) …")
    rodar([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    if rodar([python, "-m", "pip", "install", "--quiet", "-e", ".[dev]"]) != 0:
        aviso("a instalação falhou; veja a mensagem do pip acima.")
        return False
    INSTALL_MARKER.write_text(assinatura, encoding="utf-8")
    return True


def instalar_oulad(arquivo: Path) -> list[str]:
    """Copia os datasets de um ZIP de resultados para ``data/processed/``.

    Devolve os nomes dos datasets instalados (ou já presentes).
    """
    if not arquivo.is_file():
        aviso(f"arquivo não encontrado: {arquivo}")
        return []
    if not zipfile.is_zipfile(arquivo):
        aviso(f"não é um arquivo ZIP válido: {arquivo}")
        return []
    # Fora de data/processed/: a API listaria a pasta temporária como dataset.
    with tempfile.TemporaryDirectory(prefix=".extraindo-", dir=ROOT / "data") as tmp:
        destino_tmp = Path(tmp)
        with zipfile.ZipFile(arquivo) as zip_:
            nomes = zip_.namelist()
            if any(Path(n).name == "studentInfo.csv" for n in nomes):
                aviso(
                    "este ZIP é o OULAD bruto, não os resultados. Extraia-o em data/raw/oulad/ "
                    "e siga a receita de docs/specs/frente-a/README.md (~14 min)."
                )
                return []
            # extractall já recusa caminhos absolutos e com '..'.
            zip_.extractall(destino_tmp)

        datasets = sorted(
            {p.parent.parent for p in destino_tmp.rglob("bipartite/nodes.csv")}, key=str
        )
        if not datasets:
            aviso("nenhuma pasta <dataset>/bipartite/ dentro do ZIP; nada instalado.")
            return []

        PROCESSED.mkdir(parents=True, exist_ok=True)
        instalados: list[str] = []
        for origem in datasets:
            alvo = PROCESSED / origem.name
            if alvo.exists():
                aviso(f"{origem.name}: já existe em data/processed/; mantido (apague para trocar).")
            else:
                shutil.move(str(origem), str(alvo))
                aviso(f"{origem.name}: instalado em data/processed/.")
            instalados.append(origem.name)
    return instalados


def validar(raiz: Path, datasets: list[str] | None = None) -> bool:
    python = venv_python()
    if not datasets:
        return rodar([python, "-m", "edugraph", "validate", "--root", raiz]) == 0
    ok = True
    for dataset in datasets:
        comando = [python, "-m", "edugraph", "validate", "--root", raiz, "--dataset", dataset]
        ok = rodar(comando) == 0 and ok
    return ok


def testar() -> bool:
    comando = [venv_python(), "-m", "pytest", "-m", "not slow", "-q", "-p", "no:cacheprovider"]
    return rodar(comando) == 0


def compilar_front() -> bool:
    """Compila o front se o build não existir. Sem Node, só avisa."""
    if STATIC_INDEX.exists():
        aviso("interface já compilada.")
        return True
    npm = shutil.which("npm")
    if npm is None:
        aviso(
            "Node não encontrado: a API e /docs funcionam, mas http://127.0.0.1:<porta>/ "
            "mostra só um JSON. Instale o Node 20+ (https://nodejs.org) e rode de novo."
        )
        return False
    instalar = "ci" if (FRONTEND / "package-lock.json").exists() else "install"
    if rodar([npm, instalar, "--no-audit", "--no-fund"], cwd=FRONTEND) != 0:
        return False
    return rodar([npm, "run", "build"], cwd=FRONTEND) == 0


def servir(porta: int, abrir_navegador: bool) -> int:
    """Sobe a API (que serve o front) e abre o navegador quando ela responder."""
    url = f"http://127.0.0.1:{porta}/"
    comando = [str(venv_python()), "-m", "edugraph", "api", "serve", "--port", str(porta)]
    # Sem --root: o padrão é data/processed + data/fixtures, relativo ao cwd.
    processo = subprocess.Popen(comando, cwd=ROOT)

    def abrir_quando_pronto() -> None:
        limite = time.monotonic() + 60
        while time.monotonic() < limite and processo.poll() is None:
            try:
                with urllib.request.urlopen(url + "health", timeout=2):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            return
        aviso(f"pronto: {url}  (Ctrl+C para encerrar)")
        if abrir_navegador:
            webbrowser.open(url)

    threading.Thread(target=abrir_quando_pronto, daemon=True).start()
    try:
        return processo.wait()
    except KeyboardInterrupt:
        processo.terminate()
        processo.wait()
        aviso("servidor encerrado.")
        return 0


# ---------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # mesmo efeito de edugraph.console
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Instala, confere, testa e abre a interface do edugraph."
    )
    parser.add_argument("--sem-testes", action="store_true", help="pula o pytest")
    parser.add_argument(
        "--oulad", type=Path, default=None, metavar="ZIP", help="ZIP com os resultados do OULAD"
    )
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador")
    parser.add_argument(
        "--sem-servidor", action="store_true", help="faz as conferências e sai, sem subir a API"
    )
    args = parser.parse_args(argv)

    if sys.version_info < MIN_PYTHON:
        exigido = ".".join(map(str, MIN_PYTHON))
        aviso(f"o projeto pede Python {exigido}+; este é {sys.version.split()[0]}.")
        return 1

    total = 5
    problemas: list[str] = []

    passo(1, total, "ambiente Python")
    if not preparar_ambiente():
        return 1

    passo(2, total, "dados")
    if not validar(FIXTURES):
        problemas.append("as fixtures não validaram")
    if args.oulad is not None:
        instalados = instalar_oulad(args.oulad.resolve())
        if not instalados:
            problemas.append("os resultados do OULAD não foram instalados")
        elif not validar(PROCESSED, instalados):
            problemas.append("os resultados do OULAD não validaram")
    if PROCESSED.is_dir() and any(PROCESSED.iterdir()):
        nomes = ", ".join(sorted(p.name for p in PROCESSED.iterdir() if p.is_dir()))
        aviso(f"resultados do OULAD em data/processed/: {nomes}")
    else:
        aviso("sem data/processed/: a interface mostra só os dados fictícios (é o esperado).")

    passo(3, total, "testes (pytest -m 'not slow')")
    if args.sem_testes:
        aviso("pulados (--sem-testes).")
    elif not testar():
        problemas.append("algum teste falhou")

    passo(4, total, "interface")
    if not compilar_front():
        problemas.append("interface não compilada")

    if problemas:
        aviso("atenção: " + "; ".join(problemas) + ".")
    if args.sem_servidor:
        return 1 if problemas else 0

    passo(5, total, f"servidor em http://127.0.0.1:{args.porta}/")
    return servir(args.porta, not args.sem_navegador)


if __name__ == "__main__":
    raise SystemExit(main())
