"""Dataset de demonstração  ``[T]`` — turma de Computação gerada na hora.

O laboratório precisa de um grafo que monte em menos de ~3 s com
Girvan-Newman e que mostre estrutura nítida. Amostras do OULAD real não
servem a isso: em 40 alunos a projeção é quase completa e o Louvain
acha Q ≈ 0 (medido em 30/10/2026). Aqui o gerador sintético (spec A-01)
planta três áreas de um curso de Computação, com o ruído (alunos que
cursam disciplinas fora da área) como parâmetro.

Os nomes são fictícios e o desfecho é sorteado: **nada daqui é dado de
aluno real**. A área plantada de cada aluno fica de fora do grafo e só
volta na revelação (``truth``), como o ``outcomes.csv`` das fixtures
(ADR-0008).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import networkx as nx

from edugraph.contracts.types import BipartiteBundle, BipartiteSpec, Meta, Outcomes
from edugraph.data.synthetic import SyntheticSpec, generate

#: Dataset fictício: o id que aparece nos artefatos e na tela.
DEMO_DATASET = "turma_computacao"

#: Nota média a partir da qual a matrícula vira aresta. As fixtures usam 60;
#: aqui 50, para quase nenhum aluno ficar sem matrícula.
THRESHOLD = 50.0

#: Limites do laboratório: acima de ~75 alunos o Girvan-Newman passa de 10 s.
MIN_STUDENTS = 24
MAX_STUDENTS = 75

#: Área plantada → (código da disciplina, nome por extenso).
CURRICULUM: dict[str, tuple[tuple[str, str], ...]] = {
    "Desenvolvimento de Software": (
        ("ALG", "Algoritmos"),
        ("EDA", "Estruturas de Dados"),
        ("WEB", "Programação Web"),
    ),
    "Infraestrutura e Redes": (
        ("RED", "Redes de Computadores"),
        ("SOP", "Sistemas Operacionais"),
        ("SEG", "Segurança da Informação"),
    ),
    "Dados": (
        ("BDA", "Banco de Dados"),
        ("MOD", "Modelagem de Dados"),
    ),
}

_NAMES = (
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Karen", "Lucas", "Mariana", "Nicolas", "Olívia", "Pedro",
    "Quésia", "Rafael", "Sofia", "Thiago", "Úrsula", "Vinícius", "Wanda", "Xavier",
    "Yasmin", "Zeca", "Alice", "Breno", "Camila", "Daniel", "Eduarda", "Fábio",
    "Giovana", "Hugo", "Inês", "Júlio", "Larissa", "Murilo", "Natália", "Otávio",
    "Paula", "Rodrigo", "Sabrina", "Tiago", "Valéria", "William", "Yara", "Caio",
)  # fmt: skip

_SURNAME_INITIALS = "ABCDEFGHIJLMNOPRSTV"


@dataclass(frozen=True)
class DemoData:
    """A turma gerada: grafo, desfecho e a verdade plantada."""

    bipartite: BipartiteBundle
    outcomes: Outcomes
    #: aluno → nome da área plantada (a "resposta certa" da revelação)
    student_area: dict[str, str]
    #: disciplina (id de nó) → nome da área
    discipline_area: dict[str, str]


def _student_label(index: int, rng: random.Random) -> str:
    first = _NAMES[index % len(_NAMES)]
    return f"{first} {rng.choice(_SURNAME_INITIALS)}."


def build_demo(students: int, seed: int, noise: float) -> DemoData:
    """Gera a turma.

    Parameters
    ----------
    students
        Total de alunos, repartido igualmente entre as três áreas
        (arredondado para baixo, em múltiplos de 3).
    seed
        Semente: a mesma turma sai sempre igual (ADR-0011).
    noise
        Probabilidade de um aluno cursar também uma disciplina de fora da
        área. 0 = áreas perfeitas; 0,35 = o padrão do gerador.
    """
    if not MIN_STUDENTS <= students <= MAX_STUDENTS:
        raise ValueError(f"students deve estar entre {MIN_STUDENTS} e {MAX_STUDENTS}")
    if not 0.0 <= noise <= 1.0:
        raise ValueError("noise deve estar em [0, 1]")

    code_to_name = {code: name for modules in CURRICULUM.values() for code, name in modules}
    spec = SyntheticSpec(
        seed=seed,
        students_per_group=max(students // len(CURRICULUM), 1),
        groups={area: tuple(code for code, _ in mods) for area, mods in CURRICULUM.items()},
        presentations=("2026A",),
        cross_group_prob=noise,
    )
    dataset = generate(spec)

    scores: dict[tuple[str, str], list[float]] = {}
    for row in dataset.enrollments:
        key = (f"S{row['id_student']}", f"D{row['code_module']}")
        scores.setdefault(key, []).append(float(str(row["score_media"])))

    # Rótulos: nome fictício por aluno, sorteado com a mesma semente.
    rng = random.Random(seed)
    student_ids = sorted({student for student, _ in scores})
    shuffled = list(range(len(student_ids)))
    rng.shuffle(shuffled)
    label_of = {sid: _student_label(shuffled[i], rng) for i, sid in enumerate(student_ids)}
    # Nome repetido (mesmo primeiro nome e inicial) ganha um número.
    seen: dict[str, int] = {}
    for sid in student_ids:
        base = label_of[sid]
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            label_of[sid] = f"{base[:-1]}{seen[base]}."

    graph: nx.Graph[str] = nx.Graph()
    for (student, discipline), values in scores.items():
        graph.add_node(student, kind="student", label=label_of[student])
        graph.add_node(discipline, kind="discipline", label=code_to_name[discipline[1:]])
        mean_score = sum(values) / len(values)
        if mean_score >= THRESHOLD:
            graph.add_edge(student, discipline, weight=mean_score)
    graph.remove_nodes_from([n for n, d in graph.degree if d == 0])

    areas = list(CURRICULUM)
    student_area = {s: areas[g] for s, g in dataset.planted_group.items() if s in graph}
    discipline_area = {f"D{code}": area for area, mods in CURRICULUM.items() for code, _ in mods}
    outcomes = Outcomes(
        final_result={s: r for s, r in dataset.final_result.items() if s in graph},
        planted_group={s: g for s, g in dataset.planted_group.items() if s in graph},
        meta=Meta(producer="lab", notes="desfecho sorteado; dado fictício"),
    )
    bundle = BipartiteBundle(
        graph=graph,
        spec=BipartiteSpec(
            dataset=DEMO_DATASET,
            granularity="module",
            edge_criterion="score_threshold",
            threshold=THRESHOLD,
            seed=seed,
        ),
        meta=Meta(producer="lab", notes="turma de demonstração; dado fictício"),
    )
    return DemoData(
        bipartite=bundle,
        outcomes=outcomes,
        student_area=student_area,
        discipline_area=discipline_area,
    )
