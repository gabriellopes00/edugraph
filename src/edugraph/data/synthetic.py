"""Gerador de dados sintéticos com comunidades plantadas  ``[A]`` — spec A-01.

Porta fiel do gerador do starter kit, que é a base secundária declarada
na seção 8 do briefing: comunidades plantadas de propósito servem de
*ground truth* para verificar se Louvain e Girvan-Newman recuperam
estrutura conhecida.

É o gerador usado por ``scripts/make_fixtures.py`` para produzir
``synthetic_v1`` e ``synthetic_v2``. A spec A-01 (fechada) o estendeu com
esparsidade tipo OULAD e número de grupos configurável.

O starter kit foi removido do repositório; ``reference/README.md``
registra o que ele era e como recuperá-lo do histórico do git.

**Determinismo.** Todo sorteio passa por uma instância própria de
``random.Random(seed)``; nada usa o gerador global do módulo ``random``.
Duas execuções com a mesma ``SyntheticSpec`` produzem byte a byte o
mesmo CSV (ADR-0011).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

#: Áreas do gerador do starter kit. Cada área é uma comunidade plantada:
#: alunos do grupo cursam preferencialmente os módulos da sua área.
DEFAULT_GROUPS: dict[str, tuple[str, ...]] = {
    "exatas": ("AAA", "BBB", "CCC"),
    "sistemas": ("DDD", "EEE"),
    "humanas": ("FFF", "GGG"),
}

DEFAULT_PRESENTATIONS: tuple[str, ...] = ("2024J", "2024B")

#: Colunas da tabela gerada — mesmo esquema reduzido do ``studentInfo.csv``
#: do OULAD que o ETL da spec A-02 produzirá a partir da base real.
ENROLLMENT_COLUMNS: tuple[str, ...] = (
    "id_student",
    "code_module",
    "code_presentation",
    "final_result",
    "score_media",
)


@dataclass(frozen=True)
class SyntheticSpec:
    """Parâmetros do gerador.

    Os valores padrão reproduzem exatamente o starter kit: 3 grupos de 40
    alunos sobre 7 módulos, 30% em risco, 35% de chance de um módulo de
    fora do grupo como ruído.
    """

    seed: int = 42
    students_per_group: int = 40
    groups: dict[str, tuple[str, ...]] = field(default_factory=lambda: dict(DEFAULT_GROUPS))
    presentations: tuple[str, ...] = DEFAULT_PRESENTATIONS
    risk_rate: float = 0.30
    cross_group_prob: float = 0.35
    first_student_id: int = 100000
    #: Fração de alunos reduzidos a **uma** matrícula, para imitar a
    #: esparsidade do OULAD (decisão D1). ``None`` reproduz o starter kit.
    #: Ver :func:`_apply_sparsity`.
    sparsity: float | None = None

    @property
    def all_modules(self) -> list[str]:
        return [m for modules in self.groups.values() for m in modules]


@dataclass(frozen=True)
class SyntheticDataset:
    """Saída do gerador: matrículas, desfechos e o grupo plantado.

    ``planted_group`` é o *ground truth* — vai para ``outcomes.csv``, ao
    lado de ``final_result``, e **nunca** para dentro do grafo (ADR-0008).
    Ele existe para a validação a posteriori das specs B-06 e C-06.
    """

    enrollments: list[dict[str, object]]
    final_result: dict[str, str]
    planted_group: dict[str, int]

    @property
    def n_students(self) -> int:
        return len(self.planted_group)


def generate(spec: SyntheticSpec | None = None) -> SyntheticDataset:
    """Gera o dataset sintético determinístico.

    Parameters
    ----------
    spec
        Parâmetros do gerador. O padrão reproduz o starter kit.

    Returns
    -------
    SyntheticDataset
        Matrículas no esquema de ``ENROLLMENT_COLUMNS``, desfecho por
        aluno e grupo plantado por aluno.

    Raises
    ------
    ValueError
        Se ``spec.sparsity`` estiver fora de ``[0, 1]``.
    """
    spec = spec or SyntheticSpec()
    if spec.sparsity is not None and not 0.0 <= spec.sparsity <= 1.0:
        raise ValueError(f"sparsity deve estar em [0, 1]; recebeu {spec.sparsity!r}")

    rng = random.Random(spec.seed)
    enrollments: list[dict[str, object]] = []
    final_result: dict[str, str] = {}
    planted_group: dict[str, int] = {}

    student_id = spec.first_student_id
    for group_index, modules in enumerate(spec.groups.values()):
        for _ in range(spec.students_per_group):
            student_id += 1
            at_risk = rng.random() < spec.risk_rate
            rows = _generate_student(rng, student_id, modules, at_risk, spec)
            rows = _apply_sparsity(rng, rows, spec)
            enrollments.extend(rows)

            key = f"S{student_id}"
            planted_group[key] = group_index
            # O desfecho do aluno é o da sua primeira matrícula: o gerador
            # do starter kit sorteia um por linha, mas a validação a
            # posteriori raciocina por aluno (specs B-06 e C-06).
            final_result[key] = str(rows[0]["final_result"])

    return SyntheticDataset(
        enrollments=enrollments,
        final_result=final_result,
        planted_group=planted_group,
    )


def _generate_student(
    rng: random.Random,
    student_id: int,
    group_modules: tuple[str, ...],
    at_risk: bool,
    spec: SyntheticSpec,
) -> list[dict[str, object]]:
    """Matrículas de um aluno, enviesadas para o seu grupo."""
    chosen: list[str] = []

    # 2 a 4 módulos do próprio grupo: é daqui que vem a comunidade.
    n_in_group = rng.randint(2, min(4, len(group_modules)))
    chosen.extend(rng.sample(list(group_modules), k=n_in_group))

    # 0 ou 1 módulo de fora: o ruído que impede comunidades perfeitas e
    # torna o teste de recuperação honesto.
    if rng.random() < spec.cross_group_prob:
        outros = [m for m in spec.all_modules if m not in group_modules]
        chosen.append(rng.choice(outros))

    rows: list[dict[str, object]] = []
    for module in chosen:
        presentation = rng.choice(list(spec.presentations))
        score, result = _sample_performance(rng, at_risk)
        rows.append(
            {
                "id_student": student_id,
                "code_module": module,
                "code_presentation": presentation,
                "final_result": result,
                "score_media": round(score, 1),
            }
        )
    return rows


def _sample_performance(rng: random.Random, at_risk: bool) -> tuple[float, str]:
    """Nota e desfecho de uma matrícula.

    Aluno em risco tende a nota mais baixa e a mais abandono — é o que
    dá ao ``outcomes.csv`` sinal suficiente para a validação a
    posteriori encontrar alguma coisa.
    """
    if at_risk:
        score = max(0.0, min(100.0, rng.gauss(48, 14)))
        result = rng.choices(["Pass", "Fail", "Withdrawn"], weights=[0.35, 0.30, 0.35])[0]
    else:
        score = max(0.0, min(100.0, rng.gauss(72, 12)))
        result = rng.choices(
            ["Pass", "Distinction", "Fail", "Withdrawn"],
            weights=[0.55, 0.20, 0.15, 0.10],
        )[0]
    return score, result


def _apply_sparsity(
    rng: random.Random, rows: list[dict[str, object]], spec: SyntheticSpec
) -> list[dict[str, object]]:
    """Esparsidade tipo OULAD: parte dos alunos fica com **uma** matrícula só.

    No OULAD, a maior parte dos ~28,8 mil alunos aparece em uma única
    matrícula (decisão D1). O gerador do starter kit não mostra isso —
    todo aluno cursa de 2 a 4 módulos — e é por isso que ``synthetic_v1``
    tem a projeção disciplina↔disciplina completa.

    Com probabilidade ``sparsity``, o aluno mantém só uma das suas
    matrículas, sorteada. O grupo plantado **não muda**: o aluno continua
    pertencendo à área, só deixa pouca evidência disso no grafo — que é
    exatamente o que torna a recuperação das comunidades mais difícil e
    mais parecida com a base real.

    Sem ``sparsity`` (``None``) nada é sorteado, e o fluxo do gerador fica
    **idêntico** ao do dia 0 — ``synthetic_v1`` continua reproduzível
    byte a byte.
    """
    if spec.sparsity is None or spec.sparsity <= 0.0:
        return rows
    if rng.random() < spec.sparsity:
        return [rng.choice(rows)]
    return rows


def make_groups(n_groups: int, modules_per_group: int) -> dict[str, tuple[str, ...]]:
    """Áreas sintéticas com módulos ``AAA``, ``BBB``, … distribuídos entre elas.

    >>> make_groups(2, 3)
    {'grupo_0': ('AAA', 'BBB', 'CCC'), 'grupo_1': ('DDD', 'EEE', 'FFF')}
    """
    if n_groups < 1 or modules_per_group < 1:
        raise ValueError("n_groups e modules_per_group precisam ser >= 1")
    if n_groups * modules_per_group > 26:
        raise ValueError("no máximo 26 módulos no total (códigos AAA…ZZZ)")
    codes = [chr(ord("A") + i) * 3 for i in range(n_groups * modules_per_group)]
    return {
        f"grupo_{g}": tuple(codes[g * modules_per_group : (g + 1) * modules_per_group])
        for g in range(n_groups)
    }
