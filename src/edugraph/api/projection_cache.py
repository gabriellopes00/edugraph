"""Cache de uma projeção só  ``[T]`` — ADR-0013.

Ler o CSV de uma projeção e montar o grafo é o custo dominante da API:
~5 s e ~1 GB para a projeção de alunos do AVA do OULAD (1,75 M de
arestas), medido em 30/10/2026. A tela pede o grafo e, logo depois, a
leitura dos resultados (nomes, papéis), que precisa do mesmo grafo — e
relia o CSV inteiro.

A C-04 descartou o cache porque manter várias projeções grandes na
memória não compensava. Aqui guardamos **uma** só, a última lida: o
teto de memória é o de uma projeção, e o segundo pedido pelo mesmo grafo
(e a volta a ele) sai da memória. A chave inclui data e tamanho do
arquivo, então regenerar o artefato invalida o cache.

O grafo devolvido é **compartilhado**: quem o recebe não pode alterá-lo.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from edugraph.contracts import io
from edugraph.contracts.paths import ArtifactRoots
from edugraph.contracts.types import ProjectionBundle

_lock = threading.Lock()
_entry: tuple[tuple[object, ...], ProjectionBundle] | None = None
#: Resultados caros derivados da projeção em cache (o esqueleto de arestas),
#: descartados junto com ela.
_extras: dict[Any, Any] = {}


def load_projection_cached(
    roots: ArtifactRoots, dataset: str, projection_id: str
) -> ProjectionBundle:
    """``io.load_projection`` com cache de uma entrada.

    Duas requisições simultâneas pelo mesmo grafo leem o CSV **uma vez**: a
    segunda espera a primeira terminar e usa o resultado dela.
    """
    global _entry
    edges = roots.find(dataset, "projections", projection_id, "edges.csv")
    stat = edges.stat()
    key = (tuple(str(r) for r in roots), dataset, projection_id, stat.st_mtime_ns, stat.st_size)
    with _lock:
        if _entry is not None and _entry[0] == key:
            return _entry[1]
        bundle = io.load_projection(roots, dataset, projection_id)
        _entry = (key, bundle)
        _extras.clear()
        return bundle


def remember(bundle: ProjectionBundle, chave: Any, compute: Callable[[], Any]) -> Any:
    """Guarda o resultado de ``compute`` enquanto ``bundle`` for a projeção em cache.

    Serve ao esqueleto de arestas, que custa ~3 s no AVA e só depende do
    grafo, do limite e do critério de corte. Se ``bundle`` não é (mais) o
    da entrada, apenas calcula, sem guardar.
    """
    with _lock:
        vigente = _entry is not None and _entry[1] is bundle
        if vigente and chave in _extras:
            return _extras[chave]
    valor = compute()
    with _lock:
        if _entry is not None and _entry[1] is bundle:
            _extras[chave] = valor
    return valor


def clear() -> None:
    """Esvazia o cache (testes e regeneração de artefatos)."""
    global _entry
    with _lock:
        _entry = None
        _extras.clear()
