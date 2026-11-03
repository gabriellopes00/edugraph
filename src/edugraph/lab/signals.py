"""Sinais por aluno  ``[T]`` — risco de evasão e possíveis talentos.

Dois indicadores, **calculados só com o grafo** (matrículas, projeção e
comunidades): nenhum rótulo histórico entra (CLAUDE.md, regra 2) e nenhum
modelo é treinado (regra 1). São contas de estatística descritiva sobre
medidas clássicas de rede, e cada sinal vem com a frase que o explica.

**Risco de evasão.** Três sinais de afastamento, cada um medido contra a
turma em desvios-padrão (z):

* *carga*: quantas disciplinas (ou recursos, no AVA) o aluno cursa;
* *intensidade*: quanto vale cada matrícula dele frente à média da
  disciplina (a nota média, quando a matrícula exige nota mínima; a
  atividade, no AVA);
* *vínculo*: o quanto ele está ligado ao próprio grupo (o *z* de
  Guimerà e Amaral) — ou se ficou num grupo só dele.

O componente de risco de cada sinal é ``clip(−z, 0, 2) / 2``: z ≥ 0 não
pesa, z = −2 pesa tudo. O risco é a média ponderada dos componentes
(0,35 / 0,35 / 0,30). **Em atenção** a partir de 0,25 e **alto** a partir
de 0,5 — por exemplo, os três sinais em z ≈ −1. Os limiares são
convenções legíveis, não ajustados aos desfechos; a tela os confere
*depois*, contra o ``outcomes.csv`` (ADR-0008).

**Possíveis talentos.** Alunos com intensidade acima da turma
(z ≥ 1), ou que se destacam numa disciplina (z ≥ 1,5 só nela), ou que
ligam grupos diferentes sem perder desempenho — e que não estão em risco.
Quem é referência no próprio grupo ganha o selo de apoio a colegas.

Nada disso é previsão individual: é um **indicador estrutural** de quem,
no grafo, se parece com quem se afasta (ou se destaca).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import networkx as nx
import numpy as np

from edugraph.lab.insight import RoleInfo, _dec, _has_meaning, _quant

#: Pesos dos três sinais de afastamento.
W_LOAD = 0.35
W_INTENSITY = 0.35
W_GROUP = 0.30

#: Cortes do risco (0 a 1).
RISK_ALTO = 0.50
RISK_ATENCAO = 0.25

#: Um sinal só entra na explicação a partir de z ≤ -1.
Z_REASON = -1.0

#: Cortes dos talentos.
Z_DESEMPENHO = 1.0
Z_ESPECIALISTA = 1.5
#: Disciplina com menos alunos que isto não tem "melhor da turma".
MIN_DISCIPLINE_STUDENTS = 6
#: Quantos alunos cada lista da tela mostra.
LIST_SIZE = 8

TIER_LABELS = {
    "alto": "Risco alto",
    "atencao": "Em atenção",
    "baixo": "Sem sinais",
}

PROFILE_LABELS = {
    "risco": "Risco de evasão",
    "atencao": "Em atenção",
    "talento": "Possível talento",
    "referencia": "Referência do grupo",
    "ponte": "Ponte entre grupos",
    "regular": "Dentro do esperado",
}

PROFILE_HELP = {
    "risco": "Poucas matrículas, desempenho abaixo da turma e pouco vínculo com o grupo.",
    "atencao": "Um ou dois sinais de afastamento — vale acompanhar.",
    "talento": "Desempenho acima da turma, ou destaque numa disciplina, sem sinais de risco.",
    "referencia": "Muito ligado ao próprio grupo; os colegas se organizam em torno dele.",
    "ponte": "Liga grupos diferentes; circula entre áreas.",
    "regular": "Nem sinais de afastamento nem destaque.",
}


def _z(values: np.ndarray) -> tuple[np.ndarray, bool]:
    """z-score e se a medida é degenerada (todos iguais, sem como comparar)."""
    std = float(values.std())
    if std < 1e-9:
        return np.zeros_like(values, dtype=float), True
    return (values - values.mean()) / std, False


def _component(z: float) -> float:
    return float(min(max(-z, 0.0), 2.0) / 2.0)


def _tag_labels(criterion: str | None) -> dict[str, str]:
    performance = (
        "Notas acima da turma" if criterion == "score_threshold" else "Atividade acima da turma"
    )
    return {
        "desempenho": performance,
        "especialista": "Destaque numa disciplina",
        "polimata": "Liga áreas diferentes",
        "apoio": "Pode apoiar colegas",
    }


def student_signals(
    projection: nx.Graph[Any],
    bipartite: nx.Graph[Any],
    membership: dict[str, int],
    roles: dict[str, RoleInfo],
    *,
    criterion: str | None = None,
    granularity: str | None = None,
) -> dict[str, Any]:
    """Risco, talentos e perfil de cada aluno da partição.

    Parameters
    ----------
    projection
        Projeção aluno↔aluno (só para os rótulos).
    bipartite
        Matrículas: o peso da aresta é a nota média ou a atividade.
    membership
        Aluno → comunidade.
    roles
        Papéis de :func:`edugraph.lab.insight.node_roles`.
    criterion, granularity
        ``spec.edge_criterion`` e ``spec.granularity`` do bipartido; só
        trocam a redação (nota × atividade, disciplina × recurso).
    """
    students = sorted(s for s in membership if s in bipartite)
    if len(students) < 3:
        return {}
    vle = granularity in ("vle_site", "vle_activity_type")
    unit = ("recurso do ambiente", "recursos do ambiente") if vle else ("disciplina", "disciplinas")
    index = {s: i for i, s in enumerate(students)}

    degree = np.array([bipartite.degree(s) for s in students], dtype=float)
    load_z, _ = _z(np.log1p(degree))

    # Intensidade: cada matrícula frente à média da própria disciplina.
    sums: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for s in students:
        for d, w in bipartite[s].items():
            sums[d] += float(w.get("weight", 1.0))
            counts[d] += 1
    mean_of = {d: sums[d] / counts[d] for d in counts}
    ratio = np.zeros(len(students))
    weight_mean = np.zeros(len(students))
    for s in students:
        values = [
            (float(w.get("weight", 1.0)), mean_of[d])
            for d, w in bipartite[s].items()
            if mean_of[d] > 0
        ]
        ratio[index[s]] = float(np.mean([w / m for w, m in values])) if values else 1.0
        weight_mean[index[s]] = float(np.mean([w for w, _ in values])) if values else 0.0
    intensity_z, flat = _z(np.log(np.clip(ratio, 1e-6, None)))
    class_weight = float(np.mean(weight_mean[weight_mean > 0])) if (weight_mean > 0).any() else 0.0

    # Disciplinas com nome e alunos suficientes: "melhor da turma em…".
    labels = {d: str(bipartite.nodes[d].get("label", d)) for d in counts if d in bipartite}
    named = len(labels) <= 60 and sum(_has_meaning(v) for v in labels.values()) >= 0.6 * max(
        len(labels), 1
    )
    stds: dict[str, float] = {}
    if named:
        for d, n in counts.items():
            if n >= MIN_DISCIPLINE_STUDENTS:
                values = [float(w.get("weight", 1.0)) for _, _, w in bipartite.edges(d, data=True)]
                stds[d] = float(np.std(values))

    sizes = Counter(membership.values())
    weights = (
        (W_LOAD, W_INTENSITY, W_GROUP)
        if not flat
        else (W_LOAD + W_INTENSITY / 2, 0.0, W_GROUP + W_INTENSITY / 2)
    )
    tag_labels = _tag_labels(criterion)
    verb = "usa" if vle else "cursa"

    out: dict[str, dict[str, Any]] = {}
    for s in students:
        i = index[s]
        role = roles.get(s)
        group_size = sizes[membership[s]]
        alone = group_size <= 2
        group_z = role.z if role else 0.0
        parts = (
            _component(load_z[i]),
            _component(intensity_z[i]),
            1.0 if alone else _component(group_z),
        )
        risk = sum(w * p for w, p in zip(weights, parts, strict=True))
        tier = "alto" if risk >= RISK_ALTO else "atencao" if risk >= RISK_ATENCAO else "baixo"

        why: list[str] = []
        if load_z[i] <= Z_REASON:
            n = int(degree[i])
            mean = float(degree.mean())
            why.append(
                f"{'usa' if vle else 'cursa'} só {_quant(n, *unit)} "
                f"(média da turma: {_dec(mean) if mean < 10 else f'{mean:.0f}'})"
            )
        if not flat and intensity_z[i] <= Z_REASON:
            if criterion == "score_threshold" and class_weight > 0:
                why.append(f"nota média {weight_mean[i]:.0f}, abaixo da turma ({class_weight:.0f})")
            else:
                why.append(
                    f"atividade {round(100 * (1 - ratio[i]))}% abaixo do típico de cada item"
                )
        if alone:
            why.append("ficou num grupo só dele: ninguém com o mesmo perfil de matrículas")
        elif group_z <= Z_REASON:
            why.append("pouco ligado ao próprio grupo")

        # Talentos.
        tags: list[str] = []
        top_discipline: str | None = None
        if (not flat and intensity_z[i] >= Z_DESEMPENHO) or (flat and load_z[i] >= Z_DESEMPENHO):
            tags.append("desempenho")
        best_z = 0.0
        for d, w in bipartite[s].items():
            std = stds.get(d)
            if std and std > 0:
                z = (float(w.get("weight", 1.0)) - mean_of[d]) / std
                if z >= Z_ESPECIALISTA and z > best_z:
                    best_z, top_discipline = z, labels[d]
        if top_discipline:
            tags.append("especialista")
        solid = flat or intensity_z[i] >= 0.5
        if role and role.role in ("ponte", "conector") and solid and load_z[i] >= 0:
            tags.append("polimata")
        talent = bool(tags) and tier == "baixo"
        if (
            talent
            and role
            and role.role in ("referencia", "conector")
            and (flat or intensity_z[i] >= 0)
        ):
            tags.append("apoio")
        talent_why: list[str] = []
        if talent:
            if "desempenho" in tags:
                if flat:
                    talent_why.append(f"{verb} {_quant(int(degree[i]), *unit)}, bem acima da turma")
                elif criterion == "score_threshold" and class_weight > 0:
                    talent_why.append(
                        f"nota média {weight_mean[i]:.0f}, acima da turma ({class_weight:.0f})"
                    )
                else:
                    times = _dec(float(ratio[i])) if ratio[i] >= 2 else None
                    talent_why.append(
                        f"atividade {times}× o típico de cada item"
                        if times
                        else f"atividade {round(100 * (ratio[i] - 1))}% acima do típico"
                    )
            if top_discipline:
                talent_why.append(f"se destaca em {top_discipline}")
            if "polimata" in tags:
                talent_why.append("liga grupos diferentes sem perder desempenho")
            if "apoio" in tags:
                talent_why.append("é referência no próprio grupo: pode apoiar colegas como monitor")

        if tier == "alto":
            profile = "risco"
        elif talent:
            profile = "talento"
        elif tier == "atencao":
            profile = "atencao"
        elif role and role.role in ("referencia", "conector"):
            profile = "referencia"
        elif role and role.role == "ponte":
            profile = "ponte"
        else:
            profile = "regular"

        entry: dict[str, Any] = {
            "risk": round(float(risk), 3),
            "tier": tier,
            "profile": profile,
            "talent": talent,
            "strength": round(
                float(max(intensity_z[i], 0.0) + 0.5 * max(load_z[i], 0.0) + 0.5 * len(tags)),
                3,
            ),
        }
        if talent:
            entry["tags"] = tags
            entry["why"] = talent_why
        elif tier != "baixo":
            entry["why"] = why
        out[s] = entry

    label_of = {s: str(projection.nodes[s].get("label", s)) for s in students if s in projection}
    profile_counts = Counter(e["profile"] for e in out.values())
    tier_counts = Counter(e["tier"] for e in out.values())
    by_community: dict[str, dict[str, int]] = {}
    for s, entry in out.items():
        row = by_community.setdefault(
            str(membership[s]), {"n": 0, "alto": 0, "atencao": 0, "talentos": 0}
        )
        row["n"] += 1
        if entry["tier"] in ("alto", "atencao"):
            row[entry["tier"]] += 1
        if entry["talent"]:
            row["talentos"] += 1

    attention = sorted(
        (s for s, e in out.items() if e["tier"] != "baixo"),
        key=lambda s: (-out[s]["risk"], label_of.get(s, s), s),
    )
    talents = sorted(
        (s for s, e in out.items() if e["talent"]),
        key=lambda s: (-out[s]["strength"], label_of.get(s, s), s),
    )
    return {
        "students": out,
        "counts": {
            "alto": tier_counts["alto"],
            "atencao": tier_counts["atencao"],
            "talentos": sum(1 for e in out.values() if e["talent"]),
            "total": len(out),
        },
        "profile_counts": {p: profile_counts.get(p, 0) for p in PROFILE_LABELS},
        "profile_labels": PROFILE_LABELS,
        "profile_help": PROFILE_HELP,
        "tier_labels": TIER_LABELS,
        "tag_labels": tag_labels,
        "attention": attention[:LIST_SIZE],
        "talents": talents[:LIST_SIZE],
        "by_community": by_community,
        "performance": "notas" if criterion == "score_threshold" else "atividade",
        "flat_intensity": flat,
    }
