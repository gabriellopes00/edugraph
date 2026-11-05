"""Estágio ``community`` do comando ``run``  ``[B]``.

Satisfaz :class:`~edugraph.contracts.protocols.Stage`.

O que ele faz, para cada configuração de ``configs/``: roda os
algoritmos de ``[community] algorithms`` sobre as projeções de
``[[projections]]``, grava as partições, o ``profile.csv`` de cada uma
(spec B-05) e as linhas de ``metrics/communities.csv`` (spec B-04).

Ele **não** falha quando um algoritmo estoura o orçamento: a partição
sai com ``status="timeout"`` e vira linha da tabela (ADR-0006). Falha só
quando falta artefato de entrada ou quando um parâmetro do TOML não
existe — as duas coisas que quem mantém a configuração precisa corrigir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Registro das implementações da frente (ver nota em data/stage.py).
from edugraph.community import girvan_newman, louvain  # noqa: F401
from edugraph.contracts import io
from edugraph.contracts.errors import ContractError
from edugraph.contracts.paths import ArtifactRoots, as_roots
from edugraph.contracts.registry import COMMUNITIES, STAGES
from edugraph.contracts.types import Partition, RunConfig

#: Algoritmos rodados quando o TOML não diz quais.
DEFAULT_ALGORITHMS: tuple[str, ...] = ("louvain",)


def _algorithms(config: RunConfig) -> list[str]:
    """Nomes dos algoritmos a rodar, na ordem do TOML."""
    declared = config.community.get("algorithms", list(DEFAULT_ALGORITHMS))
    if isinstance(declared, str):  # `algorithms = "louvain"` é engano comum
        declared = [declared]
    return [str(name) for name in declared]


def _params(config: RunConfig, algorithm: str) -> dict[str, Any]:
    """Bloco ``[community.<algoritmo>]`` do TOML, ou vazio."""
    params = config.community.get(algorithm, {})
    if not isinstance(params, dict):
        raise ContractError(
            f"[community.{algorithm}] precisa ser uma tabela do TOML; recebeu {params!r}"
        )
    return dict(params)


class CommunityStage:
    """Roda os algoritmos de comunidade configurados sobre as projeções."""

    name = "community"

    def run(self, roots: list[Path], out: Path, config: RunConfig) -> list[Path]:
        """Executa a Frente B para uma configuração.

        Lê as projeções das ``roots`` — que podem ser fixtures, e é isso
        que permite rodar este estágio sozinho (``run --only community``)
        antes de a Frente A ter gerado qualquer coisa.
        """
        resolved = as_roots([*roots, out] if roots else [out])
        dataset = config.bipartite.dataset
        written: list[Path] = []
        partitions: list[Partition] = []

        projection_ids = [spec.projection_id for spec in config.projections]
        if not projection_ids:
            projection_ids = resolved.projections(dataset)
        if not projection_ids:
            raise ContractError(
                f"estágio 'community': nenhuma projeção declarada em {config.name!r} nem "
                f"encontrada para o dataset {dataset!r}. Rode o estágio 'data' antes."
            )

        for projection_id in projection_ids:
            projection = io.load_projection(resolved, dataset, projection_id)
            for algorithm_name in _algorithms(config):
                algorithm = COMMUNITIES.get(algorithm_name)
                partition = algorithm.run(  # type: ignore[attr-defined]
                    projection, **_params(config, algorithm_name)
                )
                partitions.append(partition)
                written.append(io.save_partition(partition, out, dataset))
                written.extend(self._profile(resolved, out, dataset, partition, config))

        written.append(self._metrics(out, dataset, partitions))
        return written

    @staticmethod
    def _profile(
        roots: ArtifactRoots, out: Path, dataset: str, partition: Partition, config: RunConfig
    ) -> list[Path]:
        """Grava o ``profile.csv`` da partição, quando o bipartido existir.

        A caracterização é saída obrigatória (spec B-05), mas depende do
        bipartido: se ele não estiver nas raízes — caso de quem rodou só
        as projeções —, o estágio segue sem ele em vez de quebrar.
        """
        from edugraph.community.characterize import characterize

        if not roots.has(dataset, "bipartite", "meta.json"):
            return []
        bipartite = io.load_bipartite(roots, dataset)
        if not set(partition.membership) <= set(bipartite.graph.nodes):
            # Partição de recorte (Girvan-Newman com sample_nodes sobre
            # outro dataset) ou de lado incompatível: não há perfil a
            # calcular, e inventar um seria pior que não ter.
            return []
        top_k = int(config.community.get("top_k", 3))
        rows = characterize(partition, bipartite, top_k=top_k)
        return [io.save_profile(rows, out, dataset, partition.artifact_id)]

    @staticmethod
    def _metrics(out: Path, dataset: str, partitions: list[Partition]) -> Path:
        """Acrescenta as linhas de ``metrics/communities.csv`` (spec B-04)."""
        from edugraph.community.compare import compare, write_metrics

        return write_metrics(compare(partitions, dataset), out, dataset)


STAGES.register("community", CommunityStage())
