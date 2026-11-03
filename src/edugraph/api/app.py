"""Aplicação FastAPI  ``[C]`` — spec C-04.

Fábrica em vez de instância global: os testes criam a aplicação apontada
para a fixture, e ``edugraph api serve`` a cria apontada para as raízes
que vierem da linha de comando. Nenhum caminho fica embutido no módulo.

Sobe com::

    python -m edugraph api serve --root data/processed --root data/fixtures
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from edugraph import __version__
from edugraph.api.lab_routes import router as lab_router
from edugraph.api.routes import router
from edugraph.contracts.errors import ArtifactNotFoundError, ContractError
from edugraph.contracts.paths import ArtifactRoots, as_roots

#: Onde o build do front-end (``frontend/``, Vite) é copiado. Fica fora
#: do git: ``npm run build`` regenera (ver ADR-0005).
STATIC_DIR = Path(__file__).parent / "static"

#: Origens liberadas no CORS durante o desenvolvimento — o Vite sobe em
#: 5173 e conversa com a API em 8000. Em produção o front é servido pelo
#: próprio FastAPI e a lista fica vazia.
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def create_app(
    roots: ArtifactRoots | Iterable[str | Path] | None = None,
    *,
    dev_cors: bool = True,
) -> FastAPI:
    """Monta a aplicação sobre as raízes de artefatos dadas.

    Parameters
    ----------
    roots
        Raízes consultadas em ordem. O padrão vem de
        ``EDUGRAPH_ROOTS`` ou de ``data/processed`` + ``data/fixtures``.
    dev_cors
        Libera as origens do Vite. Deixar ligado só em desenvolvimento.
    """
    app = FastAPI(
        title="edugraph — análise topológica de redes educacionais",
        version=__version__,
        description=(
            "API sobre artefatos pré-computados (ADR-0004), com um laboratório que "
            "monta redes pequenas na hora (ADR-0013). O cálculo pesado continua "
            "na CLI; esta API serve o que está em disco e roda só o que cabe em "
            "segundos. Uso interno da instituição."
        ),
    )
    app.state.roots = as_roots(roots)

    if dev_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(DEV_ORIGINS),
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    app.include_router(router)
    app.include_router(lab_router)
    _install_exception_handlers(app)
    _mount_frontend(app)
    return app


def _install_exception_handlers(app: FastAPI) -> None:
    """Erro de contrato vira resposta HTTP legível, não stack trace."""

    @app.exception_handler(ArtifactNotFoundError)
    async def _artifact_not_found(request: object, exc: ArtifactNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ContractError)
    async def _contract_error(request: object, exc: ContractError) -> JSONResponse:
        # 409: o artefato existe mas viola o contrato — problema de dado,
        # não de requisição. Distinguir isso de 404 poupa depuração.
        return JSONResponse(status_code=409, content={"detail": str(exc)})


def _mount_frontend(app: FastAPI) -> None:
    """Serve o build do Vite em ``/``, quando ele existir.

    Sem build, a API continua de pé e ``/`` explica como gerar um — é o
    estado normal no dia 0 e logo depois de um clone.
    """
    if STATIC_DIR.is_dir() and (STATIC_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
        return

    @app.get("/", include_in_schema=False)
    def _no_frontend() -> JSONResponse:
        return JSONResponse(
            {
                "detail": (
                    "Front-end não compilado. Rode 'cd frontend && npm install && "
                    "npm run build' para gerar src/edugraph/api/static/, ou "
                    "'npm run dev' para o servidor de desenvolvimento em :5173."
                ),
                "api_docs": "/docs",
                "health": "/health",
            }
        )


#: Instância padrão para ``uvicorn edugraph.api.app:app``. Usa as raízes
#: do ambiente; prefira ``python -m edugraph api serve`` para passar
#: ``--root`` explicitamente.
app = create_app()
