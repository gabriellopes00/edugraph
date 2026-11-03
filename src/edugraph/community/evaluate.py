"""Validação a posteriori das comunidades  ``[B]`` — spec B-06.

**Este é o único módulo da Frente B autorizado a ler ``outcomes.csv``.**
A restrição da seção 2 do briefing é a seguinte: rótulos históricos
entram só na validação, nunca como entrada de algoritmo. Um teste de
contrato (``tests/contract/test_outcomes_isolation.py``) falha se
:func:`edugraph.contracts.io.load_outcomes` for chamada de qualquer
módulo que não seja um ``evaluate.py``.

O que se valida aqui não é acurácia de um modelo — não há modelo. É se
uma estrutura descoberta **apenas pela topologia** guarda relação com o
desfecho conhecido. Se guardar, é achado; se não guardar, também é
achado, e o artigo reporta.

As três perguntas
-----------------
1. **A partição recupera o grupo plantado?** (:func:`normalized_mutual_information`,
   :func:`purity`) Só faz sentido no sintético, onde o grupo plantado
   existe. É o que autoriza a afirmar que o método funciona.
2. **O Q encontrado é maior que o do acaso?** (:func:`null_baseline`) A
   modularidade acha "comunidades" em qualquer grafo esparso; sem a
   linha de base das réplicas nulas da spec A-08, um Q sozinho não é
   evidência de nada.
3. **As comunidades diferem no desfecho?** (:func:`outcome_profile`) É a
   tabela de gestão pedagógica: uma comunidade que concentra
   ``Withdrawn`` muito acima da base é um achado obtido sem nenhum
   classificador.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from edugraph.community.compare import normalized_mutual_information as _nmi_of_dicts
from edugraph.contracts import io
from edugraph.contracts.errors import ContractError
from edugraph.contracts.paths import ArtifactRoots, as_roots
from edugraph.contracts.types import Outcomes, Partition

#: Id da spec, para as mensagens desta etapa.
PRODUCER = "B-06"

#: Os quatro desfechos do OULAD, na ordem em que aparecem na tabela do
#: artigo: do melhor para o pior.
FINAL_RESULTS: tuple[str, ...] = ("Distinction", "Pass", "Fail", "Withdrawn")

#: Colunas de :func:`outcome_profile`, montadas a partir de
#: :data:`FINAL_RESULTS` para que acrescentar um desfecho não exija
#: editar duas listas.
OUTCOME_COLUMNS: tuple[str, ...] = (
    "community",
    "size",
    "n_labeled",
    *[f"{prefix}_{result}" for result in FINAL_RESULTS for prefix in ("n", "rate", "base_rate")],
    "top_excess_outcome",
    "top_excess",
)

#: Quantos desvios o Q real precisa estar acima do Q das réplicas nulas
#: para que o trabalho afirme que há estrutura. Abaixo disso, o texto
#: reporta "indistinguível do acaso" — que também é resultado (A-08).
#:
#: Três é a convenção usual para "fora do acaso" em ciência de redes, e
#: é folgada o bastante para não depender do número de réplicas: em
#: ``synthetic_v1`` o z medido é +15.
Z_THRESHOLD = 3.0

#: Mínimo de réplicas para que o desvio-padrão signifique alguma coisa.
#: A nota da Frente A na spec B-06 sugere cinco; abaixo disso o veredito
#: sai como ``"poucas réplicas"``.
MIN_REPLICAS = 5


# ---------------------------------------------------------------------
# 1. Contra o grupo plantado
# ---------------------------------------------------------------------


def _common_nodes(partition: Partition, planted_group: dict[str, int]) -> list[str]:
    """Nós presentes na partição **e** no grupo plantado.

    A interseção existe porque a partição pode ser de um recorte (uma
    amostra, uma coorte) e porque o grupo plantado cobre só os alunos.
    Comparar sobre a interseção é o único jeito de a medida significar
    alguma coisa; se ela for vazia, é erro de chamada.
    """
    common = sorted(node for node in partition.membership if node in planted_group)
    if not common:
        raise ContractError(
            f"{PRODUCER}: a partição {partition.artifact_id!r} e o grupo plantado não "
            "têm nó em comum. Partição e outcomes.csv precisam ser do mesmo dataset."
        )
    return common


def normalized_mutual_information(partition: Partition, planted_group: dict[str, int]) -> float:
    """NMI entre a partição encontrada e o grupo plantado.

    Só faz sentido no dataset sintético, onde o grupo plantado existe.
    A fixture ``synthetic_v1`` traz três grupos de 40 alunos com ruído
    de 35%, e a spec B-06 espera NMI ≥ 0,8 na projeção aluno↔aluno.

    Medida de teoria da informação entre duas partições conhecidas —
    não é aprendizado de máquina. A conta está em
    :func:`edugraph.community.compare.normalized_mutual_information`, a
    mesma que compara Louvain com Girvan-Newman; aqui ela só recebe o
    grupo plantado no lugar da segunda partição.
    """
    common = _common_nodes(partition, planted_group)
    return _nmi_of_dicts(
        {node: partition.membership[node] for node in common},
        {node: planted_group[node] for node in common},
    )


def purity(partition: Partition, planted_group: dict[str, int]) -> float:
    """Pureza: fração de nós que caem na maioria plantada da sua comunidade.

    Para cada comunidade, conta quantos nós pertencem ao grupo plantado
    majoritário dentro dela; soma e divide pelo total. Vale 1 quando
    cada comunidade é feita de um grupo só — inclusive quando a partição
    é mais fina que o *ground truth*, e é por isso que a pureza sozinha
    não basta e vem sempre ao lado do NMI.
    """
    common = _common_nodes(partition, planted_group)
    por_comunidade: defaultdict[int, defaultdict[int, int]] = defaultdict(lambda: defaultdict(int))
    for node in common:
        por_comunidade[partition.membership[node]][planted_group[node]] += 1
    acertos = sum(max(grupos.values()) for grupos in por_comunidade.values())
    return acertos / len(common)


# ---------------------------------------------------------------------
# 2. Contra o acaso — as réplicas nulas da spec A-08
# ---------------------------------------------------------------------


def is_null_replica(dataset_meta_stats: dict[str, Any], source_dataset: str | None = None) -> bool:
    """``True`` se o ``meta.stats`` for de uma réplica do modelo nulo.

    Mesmo critério de ``edugraph.data.nullmodel.is_null``, **sem
    importá-lo**: a Frente B não importa a Frente A (ADR-0003). O que
    atravessa a fronteira é o artefato, e o artefato carrega
    ``meta.stats["null_model"]`` — é por isso que o critério não depende
    do nome do dataset.
    """
    null_model = dataset_meta_stats.get("null_model")
    if not isinstance(null_model, dict):
        return False
    if source_dataset is None:
        return True
    return str(null_model.get("source_dataset", "")) == source_dataset


def null_replicas_of(
    roots: ArtifactRoots | list[str | Path] | str | Path | None, dataset: str
) -> list[str]:
    """Nomes dos datasets que são réplicas nulas de ``dataset``.

    Varre as raízes e pergunta a cada bipartido se ele se declara
    réplica do dataset em questão. Nenhuma convenção de nome é assumida.
    """
    resolved = as_roots(roots)
    found = []
    for candidate in resolved.datasets():
        if candidate == dataset or not resolved.has(candidate, "bipartite", "meta.json"):
            continue
        bundle = io.load_bipartite(resolved, candidate)
        if is_null_replica(bundle.meta.stats, dataset):
            found.append(candidate)
    return sorted(found)


def modularity_z_score(observed: float, null_values: list[float]) -> dict[str, Any]:
    """Quantos desvios o Q observado está acima do Q das réplicas nulas.

    Returns
    -------
    dict
        ``q_real``, ``q_null_mean``, ``q_null_sd``, ``n_replicas``,
        ``z`` e ``verdict``.

    Notes
    -----
    Desvio amostral (divide por ``n − 1``): as réplicas são uma amostra
    do que o acaso produziria, não a população. Com menos de duas
    réplicas não há desvio, e o veredito é ``"poucas réplicas"`` em vez
    de um z que não significaria nada.

    **Não é teste de significância estatística** — a spec B-06 põe isso
    explicitamente fora de escopo. É a distância, em desvios, entre o
    valor medido e a distribuição do acaso; serve para dizer "muito
    acima" ou "indistinguível", não para calcular um p-valor.
    """
    n = len(null_values)
    if n == 0:
        return {
            "q_real": observed,
            "q_null_mean": math.nan,
            "q_null_sd": math.nan,
            "n_replicas": 0,
            "z": math.nan,
            "verdict": "sem réplicas",
        }

    mean = sum(null_values) / n
    if n < 2:
        sd = math.nan
        z = math.nan
    else:
        variance = sum((value - mean) ** 2 for value in null_values) / (n - 1)
        sd = math.sqrt(variance)
        if sd == 0.0:
            # Réplicas idênticas: o z é infinito por construção, e dizer
            # isso é mais honesto que devolver um número inventado.
            z = math.inf if observed > mean else (-math.inf if observed < mean else 0.0)
        else:
            z = (observed - mean) / sd

    if n < MIN_REPLICAS:
        verdict = "poucas réplicas"
    elif z >= Z_THRESHOLD:
        verdict = "estrutura"
    else:
        verdict = "indistinguível do acaso"

    return {
        "q_real": observed,
        "q_null_mean": mean,
        "q_null_sd": sd,
        "n_replicas": n,
        "z": z,
        "verdict": verdict,
    }


def null_baseline(
    roots: ArtifactRoots | list[str | Path] | str | Path | None,
    dataset: str,
    projection_id: str,
    observed_modularity: float,
    *,
    seed: int = 42,
    resolution: float = 1.0,
) -> dict[str, Any]:
    """Compara o Q observado com o das réplicas nulas do mesmo grafo.

    Roda o **mesmo** Louvain, com os mesmos parâmetros, sobre a projeção
    homóloga de cada réplica encontrada por :func:`null_replicas_of`.
    Réplica sem aquela projeção em disco é pulada e contada em
    ``skipped`` — não dá para comparar o que não existe, e inventar um
    zero rebaixaria a média do nulo e inflaria o z.

    A comparação é **desta spec**, não da A-08: a Frente A só gera o
    artefato nulo (ADR-0003).
    """
    from edugraph.community.louvain import LouvainAlgorithm

    resolved = as_roots(roots)
    algorithm = LouvainAlgorithm()
    values: list[float] = []
    used: list[str] = []
    skipped: list[str] = []

    for replica in null_replicas_of(resolved, dataset):
        if not resolved.has(replica, "projections", projection_id, "meta.json"):
            skipped.append(replica)
            continue
        projection = io.load_projection(resolved, replica, projection_id)
        partition = algorithm.run(projection, seed=seed, resolution=resolution)
        values.append(partition.modularity)
        used.append(replica)

    result = modularity_z_score(observed_modularity, values)
    result.update(
        {
            "dataset": dataset,
            "projection_id": projection_id,
            "replicas": used,
            "skipped": skipped,
            "seed": seed,
            "resolution": resolution,
        }
    )
    return result


# ---------------------------------------------------------------------
# 3. Contra o desfecho histórico
# ---------------------------------------------------------------------


def outcome_profile(partition: Partition, outcomes: Outcomes) -> list[dict[str, Any]]:
    """Distribuição de desfechos por comunidade.

    A tabela de validação do capítulo 3: se uma comunidade concentra
    ``Withdrawn`` muito acima da base, isso é um achado de gestão
    pedagógica obtido sem nenhum classificador.

    Returns
    -------
    list of dict
        Uma linha por comunidade, no formato de :data:`OUTCOME_COLUMNS`:
        tamanho, quantos nós têm desfecho conhecido, a contagem e a taxa
        de cada desfecho, **a taxa da base ao lado** e qual desfecho
        está mais acima dela (``top_excess_outcome``, ``top_excess``).

    Notes
    -----
    As taxas são calculadas sobre ``n_labeled``, não sobre ``size``: nem
    todo nó tem desfecho (uma partição do lado disciplina não tem
    nenhum, e no OULAD um aluno pode faltar em ``outcomes.csv``).
    Misturar as duas bases faria uma comunidade parecer ter menos
    reprovação só por ter mais nós sem rótulo.

    A base é a **própria partição**, pela mesma razão da spec B-05: é a
    população que foi dividida, e é contra ela que "acima da base" quer
    dizer alguma coisa.
    """
    final_result = outcomes.final_result
    base_counts: defaultdict[str, int] = defaultdict(int)
    base_total = 0
    for node in partition.membership:
        result = final_result.get(node)
        if result is not None:
            base_counts[result] += 1
            base_total += 1

    base_rates = {
        result: (base_counts[result] / base_total if base_total else 0.0)
        for result in FINAL_RESULTS
    }

    rows: list[dict[str, Any]] = []
    for community, nodes in partition.groups().items():
        counts: defaultdict[str, int] = defaultdict(int)
        labeled = 0
        for node in nodes:
            result = final_result.get(node)
            if result is not None:
                counts[result] += 1
                labeled += 1

        row: dict[str, Any] = {
            "community": community,
            "size": len(nodes),
            "n_labeled": labeled,
        }
        excesses: dict[str, float] = {}
        for result in FINAL_RESULTS:
            rate = counts[result] / labeled if labeled else 0.0
            row[f"n_{result}"] = counts[result]
            row[f"rate_{result}"] = rate
            row[f"base_rate_{result}"] = base_rates[result]
            excesses[result] = rate - base_rates[result]

        if labeled:
            # Desempate pela ordem de FINAL_RESULTS, que é fixa.
            top = max(
                FINAL_RESULTS,
                key=lambda result: (excesses[result], -FINAL_RESULTS.index(result)),
            )
            row["top_excess_outcome"] = top
            row["top_excess"] = excesses[top]
        else:
            row["top_excess_outcome"] = ""
            row["top_excess"] = 0.0
        rows.append(row)
    return rows


def outcomes_by_group(groups: dict[str, str], outcomes: Outcomes) -> dict[str, Any]:
    """Distribuição de desfechos por **grupo qualquer** de nós, não só comunidade.

    Serve à validação a posteriori dos sinais do laboratório (risco de
    evasão, talentos): os grupos vêm de uma regra sobre o grafo, e aqui
    se confere o que aconteceu de fato com quem caiu em cada um. As taxas
    são sobre ``n_labeled``, como em :func:`outcome_profile`.

    Parameters
    ----------
    groups
        nó → nome do grupo. Nós sem desfecho conhecido contam em ``n``,
        mas não nas taxas.
    outcomes
        Desfechos carregados por :func:`load_labels`.

    Returns
    -------
    dict
        ``{"base": {...}, "groups": {nome: {...}}}``; cada bloco tem
        ``n``, ``n_labeled``, ``counts`` e ``rates`` por desfecho de
        :data:`FINAL_RESULTS`. ``base`` é a população inteira de ``groups``.
    """

    def block(nodes: list[str]) -> dict[str, Any]:
        counts: dict[str, int] = dict.fromkeys(FINAL_RESULTS, 0)
        labeled = 0
        for node in nodes:
            result = outcomes.final_result.get(node)
            if result in counts:
                counts[result] += 1
                labeled += 1
        return {
            "n": len(nodes),
            "n_labeled": labeled,
            "counts": counts,
            "rates": {r: (counts[r] / labeled if labeled else 0.0) for r in FINAL_RESULTS},
        }

    members: dict[str, list[str]] = {}
    for node, group in groups.items():
        members.setdefault(group, []).append(node)
    return {
        "base": block(list(groups)),
        "groups": {name: block(nodes) for name, nodes in members.items()},
    }


def rank_auc(
    scores: dict[str, float],
    outcomes: Outcomes,
    positive: tuple[str, ...] = ("Fail", "Withdrawn"),
) -> float | None:
    """AUC de uma nota contra um desfecho: a chance de um positivo ter nota maior.

    É a estatística de Mann-Whitney, por postos com empate pela média.
    0,5 é o acaso; 1 é separação perfeita. Devolve ``None`` se faltar um
    dos dois lados (ninguém ou todos são positivos).
    """
    nodes = [n for n in scores if n in outcomes.final_result]
    if not nodes:
        return None
    values = np.array([scores[n] for n in nodes], dtype=float)
    is_positive = np.array([outcomes.final_result[n] in positive for n in nodes])
    n_pos = int(is_positive.sum())
    n_neg = len(nodes) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values))
    sorted_values = values[order]
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2 + 1
        i = j + 1
    rank_sum = float(ranks[is_positive].sum())
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def unknown_outcomes(partition: Partition, outcomes: Outcomes) -> int:
    """Quantos nós da partição não têm desfecho conhecido.

    Vai para a saída da CLI porque é o número que qualifica a tabela:
    uma validação sobre 30% dos nós não diz o mesmo que uma sobre 100%.
    """
    return sum(1 for node in partition.membership if node not in outcomes.final_result)


def load_labels(
    roots: ArtifactRoots | list[str | Path] | str | Path | None, dataset: str
) -> Outcomes:
    """Carrega ``outcomes.csv``.

    **A única chamada a ``load_outcomes`` de toda a Frente B**, e por
    isso ela mora aqui: o teste de contrato
    ``test_outcomes_isolation.py`` procura essa chamada fora dos
    ``evaluate.py`` e quebra a CI se achar (ADR-0008).
    """
    return io.load_outcomes(roots, dataset)
