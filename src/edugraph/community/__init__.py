"""Frente B — Detecção de Comunidades  ``[B]``.

Louvain, Girvan-Newman, modularidade Q implementada à mão, comparação de
qualidade e custo, e caracterização das comunidades encontradas.

**Produz** ``communities/`` (partição, perfil, Q, tempo, status) e
``metrics/communities.csv``. **Consome** ``projections/`` e
``bipartite/``; lê ``outcomes.csv`` apenas em :mod:`~edugraph.community.evaluate`.

Fronteira (ADR-0003): este subpacote não importa ``edugraph.data``,
``edugraph.centrality`` nem ``edugraph.api``. No dia 0 ele trabalha
sobre ``data/fixtures/synthetic_v1`` e ``tiny_v1``, sem executar uma
linha da Frente A.
"""

from __future__ import annotations

from typing import Any

from edugraph.contracts.errors import ContractError


def check_params(params: dict[str, Any], accepted: frozenset[str], where: str) -> None:
    """Recusa parâmetro desconhecido, nomeando os aceitos.

    Único utilitário compartilhado pelos dois algoritmos da frente, e
    mora aqui por isso. Os parâmetros chegam do TOML de ``configs/``,
    onde ninguém checa ortografia: ``resolucao = 2`` em vez de
    ``resolution = 2`` seria silenciosamente ignorado e produziria uma
    linha da tabela do capítulo 3 com o parâmetro que ninguém pediu.

    Raises
    ------
    ContractError
        Se ``params`` tiver alguma chave fora de ``accepted``.
    """
    unknown = sorted(set(params) - accepted)
    if unknown:
        raise ContractError(
            f"{where}: parâmetro desconhecido {unknown}. Aceitos: {sorted(accepted)}."
        )
