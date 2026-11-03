"""O resultado em linguagem de gente  ``[T]``.

Três leituras de uma partição, todas por contagem e limiar fixo — sem
modelo treinado (CLAUDE.md, regra 1):

1. **Nome das comunidades.** Do lado dos alunos, pelas disciplinas que o
   grupo cursa acima da média da turma; quando as disciplinas só têm
   número (recursos do AVA do OULAD), pelo nível de engajamento. Do lado
   das disciplinas, pelos nomes ou módulos que o grupo reúne.
2. **Papel de cada nó**, pela classificação de Guimerà e Amaral (2005):
   o grau dentro da própria comunidade (*z*) e quanto as ligações se
   espalham por outras (coeficiente de participação, *P*).
3. **Frases-resumo**, geradas por regra a partir de 1 e 2.

Os limiares de 2 são **adaptados** ao que o projeto tem: o artigo
original trabalha com redes grandes e esparsas (z ≥ 2,5, P fixo); aqui
as projeções são densas e têm de 7 a 1.870 nós. z ≥ 1 já separa os nós
mais ligados do grupo, e o P é comparado com o do próprio grupo (com
margem mínima), porque com limiar fixo quase todo nó de uma projeção
densa viraria "ponte" (medido: 1.585 de 1.870 no AVA). A adaptação está
justificada na ADR-0013.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import numpy as np

#: z a partir do qual o nó é "referência" do próprio grupo.
Z_HUB = 1.0

#: P mínimo para o nó contar como alguém que se liga a outros grupos.
P_CONNECT = 0.30

#: Além do mínimo, o nó precisa estar acima da média de P do próprio grupo
#: por pelo menos este desvio-padrão *e* por esta margem absoluta. Em
#: projeção densa quase todo nó tem P parecido (no AVA do OULAD, 0,65 a
#: 0,66), e sem a margem o selo "ponte" iria para quem difere em 0,01.
P_SPREAD_Z = 1.0
P_SPREAD_MARGIN = 0.05

#: Rótulos em português dos quatro papéis.
ROLE_LABELS: dict[str, str] = {
    "referencia": "Referência do grupo",
    "conector": "Conector",
    "ponte": "Ponte",
    "periferico": "Periférico",
}

#: O que cada papel quer dizer, para a legenda da tela.
ROLE_HELP: dict[str, str] = {
    "referencia": "Muito ligado dentro do próprio grupo e quase sem ligações para fora.",
    "conector": "Muito ligado no próprio grupo e também a outros grupos.",
    "ponte": "Pouco central no próprio grupo, mas liga-se a outros grupos.",
    "periferico": "Poucas ligações, quase todas dentro do próprio grupo.",
}

#: Uma disciplina "marca" um grupo se pelo menos esta fração dele a cursa…
MIN_SHARE = 0.35
#: …e se isso é pelo menos esta vez a fração da turma inteira.
MIN_LIFT = 1.25

_MODULE_RE = re.compile(r"^([A-Za-z]{2,4})_\d{4}[A-Za-z]?$")


@dataclass
class CommunityInfo:
    id: int
    name: str
    size: int
    share: float
    description: str
    #: Itens que definem o grupo: ``{"label", "share", "lift"}``.
    top: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RoleInfo:
    role: str
    z: float
    p: float


def node_kind(graph: nx.Graph[Any]) -> str:
    """``student`` ou ``discipline``, o que a maioria dos nós for."""
    kinds = Counter(d.get("kind", "student") for _, d in graph.nodes(data=True))
    return str(kinds.most_common(1)[0][0]) if kinds else "student"


def plural(kind: str) -> str:
    return "alunos" if kind == "student" else "disciplinas"


def _substantivo(kind: str) -> tuple[str, str, str]:
    """Singular, plural e "nenhum(a)" do tipo de nó, para frases que concordam."""
    if kind == "student":
        return "aluno", "alunos", "Nenhum aluno"
    return "disciplina", "disciplinas", "Nenhuma disciplina"


def _has_meaning(label: str) -> bool:
    """Rótulo com letra diz algo; um número de recurso do AVA, não."""
    return any(ch.isalpha() for ch in label)


def _pct(value: float) -> str:
    return f"{round(100 * value)}%"


def _num(value: float) -> str:
    return f"{value:.0f}"


def _quant(n: int, singular: str, plural: str) -> str:
    """``1 aluno``, ``2 alunos``."""
    return f"{n} {singular if n == 1 else plural}"


def _dec(value: float) -> str:
    """Duas casas, com vírgula, como o resto da interface."""
    return f"{value:.2f}".replace(".", ",")


# ---------------------------------------------------------------------
# 1. Nome das comunidades
# ---------------------------------------------------------------------


def _unique(names: list[str]) -> list[str]:
    seen: Counter[str] = Counter()
    out = []
    for name in names:
        seen[name] += 1
        out.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return out


def _engagement_names(k: int, vle: bool) -> list[str] | None:
    """Nomes dos ``k`` grupos, do menos ao mais ativo; ``None`` se forem muitos."""
    if k == 1:
        return ["Todos juntos"]
    if vle:
        tiers = {
            2: ["Menos engajados", "Mais engajados"],
            3: ["Pouco engajados", "Engajados", "Muito engajados"],
            4: ["Pouco engajados", "Engajamento moderado", "Engajados", "Muito engajados"],
        }
    else:
        tiers = {
            2: ["Poucas disciplinas", "Muitas disciplinas"],
            3: ["Poucas disciplinas", "Carga média", "Muitas disciplinas"],
            4: ["Poucas disciplinas", "Carga baixa", "Carga alta", "Muitas disciplinas"],
        }
    return tiers.get(k)


def _name_students(
    graph: nx.Graph[Any],
    groups: dict[int, list[str]],
    bipartite: nx.Graph[Any],
    granularity: str | None,
) -> dict[int, tuple[str, str, list[dict[str, Any]]]]:
    """Nome, descrição e itens-marca de cada grupo de alunos."""
    n_students = sum(len(m) for m in groups.values())
    discipline_labels = {
        n: str(d.get("label", n))
        for n, d in bipartite.nodes(data=True)
        if d.get("kind") == "discipline"
    }
    meaningful = (
        bool(discipline_labels)
        and len(discipline_labels) <= 60
        and sum(_has_meaning(v) for v in discipline_labels.values()) >= 0.6 * len(discipline_labels)
    )
    base = {
        d: sum(1 for s in bipartite.neighbors(d) if s in graph) / max(n_students, 1)
        for d in discipline_labels
    }
    mean_degree_all = float(
        np.mean([bipartite.degree(s) for m in groups.values() for s in m if s in bipartite] or [0])
    )

    out: dict[int, tuple[str, str, list[dict[str, Any]]]] = {}
    activity: dict[int, float] = {}
    marks: dict[int, list[dict[str, Any]]] = {}
    for community, members in groups.items():
        counts: Counter[str] = Counter()
        for student in members:
            if student in bipartite:
                counts.update(d for d in bipartite.neighbors(student) if d in discipline_labels)
        scored = []
        for discipline, count in counts.items():
            share = count / len(members)
            lift = share / base[discipline] if base.get(discipline) else 0.0
            scored.append({"label": discipline_labels[discipline], "share": share, "lift": lift})
        scored.sort(key=lambda item: (-item["share"], item["label"]))
        marks[community] = [i for i in scored if i["share"] >= MIN_SHARE and i["lift"] >= MIN_LIFT]
        activity[community] = float(
            np.mean([bipartite.degree(s) for s in members if s in bipartite] or [0])
        )

    vle = granularity in ("vle_site", "vle_activity_type")
    if meaningful and all(marks[c] for c in groups):
        for community, members in groups.items():
            top = marks[community]
            name = " · ".join(i["label"] for i in top[:2])
            if len(top) > 2:
                name += f" +{len(top) - 2}"
            shown = ", ".join(f"{i['label']} ({_pct(i['share'])})" for i in top[:3])
            out[community] = (
                name,
                f"{_quant(len(members), 'aluno', 'alunos')} · cursam sobretudo {shown}",
                top[:3],
            )
    else:
        order = sorted(groups, key=lambda c: (activity[c], c))
        names = _engagement_names(len(order), vle)
        by_size = sorted(groups, key=lambda c: (-len(groups[c]), c))
        what = "recursos do ambiente virtual" if vle else "disciplinas"
        for position, community in enumerate(order):
            members = groups[community]
            description = (
                f"{_quant(len(members), 'aluno', 'alunos')} · usam em média "
                f"{_num(activity[community])} {what} "
                f"(turma toda: {_num(mean_degree_all)})"
            )
            name = names[position] if names else f"Grupo {by_size.index(community) + 1}"
            out[community] = (name, description, [])

    # Grupo de 1 ou 2 alunos não tem "perfil": leva o nome de quem está nele.
    for community, members in groups.items():
        if len(members) <= 2:
            labels = [str(graph.nodes[s].get("label", s)) for s in sorted(members)]
            name, description, top = out[community]
            out[community] = (" e ".join(labels), description, top)
    return out


def _name_disciplines(
    graph: nx.Graph[Any], groups: dict[int, list[str]]
) -> dict[int, tuple[str, str, list[dict[str, Any]]]]:
    out: dict[int, tuple[str, str, list[dict[str, Any]]]] = {}
    for community, members in groups.items():
        strength = {
            n: sum(w for _, _, w in graph.edges(n, data="weight", default=1.0)) for n in members
        }
        ordered = sorted(members, key=lambda n: (-strength[n], n))
        labels = [str(graph.nodes[n].get("label", n)) for n in ordered]
        modules = [m.group(1) for m in map(_MODULE_RE.match, labels) if m]
        if modules and len(modules) == len(labels):
            count = Counter(modules)
            top = [code for code, _ in count.most_common(2)]
            if len(count) == 1:
                name = f"Módulo {top[0]}"
            else:
                name = (
                    "Módulos " + " · ".join(top) + (f" +{len(count) - 2}" if len(count) > 2 else "")
                )
        else:
            name = " · ".join(labels[:2]) + (f" +{len(labels) - 2}" if len(labels) > 2 else "")
        listed = ", ".join(labels[:4]) + (" …" if len(labels) > 4 else "")
        out[community] = (
            name,
            f"{_quant(len(members), 'disciplina', 'disciplinas')} · {listed}",
            [],
        )
    return out


def name_communities(
    graph: nx.Graph[Any],
    membership: dict[str, int],
    bipartite: nx.Graph[Any] | None = None,
    *,
    granularity: str | None = None,
) -> list[CommunityInfo]:
    """Nome e descrição de cada comunidade, das maiores para as menores."""
    groups: dict[int, list[str]] = {}
    for node, community in membership.items():
        groups.setdefault(community, []).append(node)
    total = max(len(membership), 1)

    if node_kind(graph) == "discipline":
        named = _name_disciplines(graph, groups)
    elif bipartite is not None:
        named = _name_students(graph, groups, bipartite, granularity)
    else:
        named = {
            c: (f"Grupo {i + 1}", f"{len(m)} alunos", [])
            for i, (c, m) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])))
        }

    order = sorted(groups, key=lambda c: (-len(groups[c]), c))
    names = _unique([named[c][0] for c in order])
    return [
        CommunityInfo(
            id=c,
            name=names[i],
            size=len(groups[c]),
            share=len(groups[c]) / total,
            description=named[c][1],
            top=named[c][2],
        )
        for i, c in enumerate(order)
    ]


# ---------------------------------------------------------------------
# 2. Papel de cada nó (Guimerà e Amaral, 2005)
# ---------------------------------------------------------------------


def node_roles(
    graph: nx.Graph[Any],
    membership: dict[str, int],
    *,
    z_hub: float = Z_HUB,
    p_connect: float = P_CONNECT,
) -> dict[str, RoleInfo]:
    """Papel de cada nó pelo grau no próprio grupo (z) e pela participação (P).

    Com força (soma dos pesos) no lugar de grau: nas projeções densas, o
    número de vizinhos é quase o mesmo para todos, e é o peso que
    discrimina. Para o nó ``i`` na comunidade ``s``::

        z_i = (k_is − média de k_js em s) / desvio de k_js em s
        P_i = 1 − Σ_c (k_ic / k_i)²

    com ``k_ic`` a força de ``i`` nas ligações com a comunidade ``c``.
    """
    nodes = list(graph.nodes)
    if not nodes:
        return {}
    index = {n: i for i, n in enumerate(nodes)}
    comm = np.array([membership.get(n, -1) for n in nodes])
    labels = sorted(set(comm.tolist()))
    column = {c: j for j, c in enumerate(labels)}
    col = np.array([column[c] for c in comm])

    edges = list(graph.edges(data="weight", default=1.0))
    strength = np.zeros((len(nodes), len(labels)))
    if edges:
        us = np.array([index[u] for u, _, _ in edges])
        vs = np.array([index[v] for _, v, _ in edges])
        ws = np.array([float(w) for _, _, w in edges])
        np.add.at(strength, (us, col[vs]), ws)
        np.add.at(strength, (vs, col[us]), ws)

    total = strength.sum(axis=1)
    inside = strength[np.arange(len(nodes)), col]
    with np.errstate(divide="ignore", invalid="ignore"):
        fractions = np.where(total[:, None] > 0, strength / total[:, None], 0.0)
    participation = 1.0 - (fractions**2).sum(axis=1)
    participation = np.where(total > 0, participation, 0.0)

    z = np.zeros(len(nodes))
    for j in range(len(labels)):
        in_group = col == j
        if in_group.sum() > 2:
            values = inside[in_group]
            std = values.std()
            if std > 0:
                z[in_group] = (values - values.mean()) / std

    # P comparado com o do próprio grupo: média e desvio por comunidade.
    spread_floor = np.full(len(nodes), np.inf)
    for j in range(len(labels)):
        in_group = col == j
        values = participation[in_group]
        floor = values.mean() + max(P_SPREAD_Z * values.std(), P_SPREAD_MARGIN)
        spread_floor[in_group] = max(floor, p_connect)

    roles: dict[str, RoleInfo] = {}
    for i, node in enumerate(nodes):
        hub = z[i] >= z_hub
        spread = participation[i] >= spread_floor[i]
        role = (
            ("conector" if spread else "referencia")
            if hub
            else ("ponte" if spread else "periferico")
        )
        roles[node] = RoleInfo(role=role, z=float(z[i]), p=float(participation[i]))
    return roles


# ---------------------------------------------------------------------
# 3. Frases-resumo
# ---------------------------------------------------------------------


def modularity_reading(q: float) -> str:
    """O que um valor de Q quer dizer, em uma frase (Newman, 2004)."""
    if q >= 0.5:
        return "grupos muito bem definidos"
    if q >= 0.3:
        return "grupos bem definidos"
    if q >= 0.1:
        return "separação fraca entre os grupos"
    return "quase nenhuma separação: o comportamento é parecido entre todos"


def summarize(
    graph: nx.Graph[Any],
    q: float,
    communities: list[CommunityInfo],
    roles: dict[str, RoleInfo],
    signals: dict[str, Any] | None = None,
) -> list[str]:
    """Três a cinco frases sobre o resultado, geradas por regra."""
    kind = plural(node_kind(graph))
    k = len(communities)
    if not communities:
        return []
    biggest = communities[0]
    lines = [
        f"Foram encontrados {_quant(k, 'grupo', 'grupos')} entre {len(graph)} {kind}. "
        f"O maior, «{biggest.name}», reúne {biggest.size} ({_pct(biggest.share)}).",
        f"Modularidade Q = {_dec(q)}: {modularity_reading(q)}.",
    ]
    counts = Counter(r.role for r in roles.values())
    bridges = counts["ponte"] + counts["conector"]
    unico, varios, nenhum = _substantivo(node_kind(graph))
    if k > 1 and roles:
        if bridges:
            top = sorted(
                (n for n, r in roles.items() if r.role in ("ponte", "conector")),
                key=lambda n: (-roles[n].p, n),
            )[0]
            label = graph.nodes[top].get("label", top)
            verbo = "faz" if bridges == 1 else "fazem"
            lines.append(
                f"{_quant(bridges, unico, varios)} {verbo} ponte entre grupos; "
                f"quem mais espalha as ligações é {str(label).rstrip('.')}."
            )
        elif q < 0.1:
            lines.append(
                f"{nenhum} se destaca como ponte: todos se ligam aos grupos de forma parecida."
            )
        else:
            lines.append(f"{nenhum} se destaca como ponte entre os grupos.")
    refs = counts["referencia"] + counts["conector"]
    if refs:
        verbo = "é" if refs == 1 else "são"
        lines.append(f"{_quant(refs, unico, varios)} {verbo} referência no próprio grupo.")
    if signals:
        lines.extend(_signal_lines(graph, communities, signals))
    return lines


def _signal_lines(
    graph: nx.Graph[Any], communities: list[CommunityInfo], signals: dict[str, Any]
) -> list[str]:
    """Frases sobre risco de evasão e talentos (ver ``edugraph.lab.signals``)."""
    lines: list[str] = []
    counts = signals["counts"]
    flagged = counts["alto"] + counts["atencao"]
    if flagged:
        names = {c.id: c.name for c in communities}
        by_community = signals["by_community"]
        worst = max(
            by_community, key=lambda c: (by_community[c]["alto"] + by_community[c]["atencao"], c)
        )
        n_worst = by_community[worst]["alto"] + by_community[worst]["atencao"]
        where = (
            f"; {n_worst} deles estão em «{names.get(int(worst), worst)}»"
            if len(by_community) > 1 and n_worst < flagged
            else ""
        )
        lines.append(
            f"{_quant(flagged, 'aluno tem', 'alunos têm')} sinais de afastamento "
            f"({counts['alto']} com risco alto){where}."
        )
    else:
        lines.append("Nenhum aluno mostra sinais de afastamento.")
    if counts["talentos"]:
        top = signals["talents"][0]
        label = str(graph.nodes[top].get("label", top)).rstrip(".")
        lines.append(
            f"{_quant(counts['talentos'], 'possível talento', 'possíveis talentos')}; "
            f"o mais destacado é {label}."
        )
    return lines
