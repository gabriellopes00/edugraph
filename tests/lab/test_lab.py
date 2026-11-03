"""Laboratório ao vivo  ``[T]`` — ADR-0013.

O que a tela anima precisa ser o que o algoritmo fez. Três garantias:

1. o Girvan-Newman com rastro dá **a mesma partição** do algoritmo
   registrado, e o Louvain com rastro fica a menos de 0,02 de Q do
   ``python-louvain`` e recupera as áreas plantadas quando não há ruído;
2. reproduzir os movimentos guardados leva ao resultado final;
3. a API recusa o que não cabe, com mensagem que diz o que mudar.
"""

from __future__ import annotations

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from edugraph.api.app import create_app
from edugraph.community.modularity import groups_of, modularity
from edugraph.contracts.registry import COMMUNITIES, PROJECTIONS, load_builtin_implementations
from edugraph.contracts.types import ProjectionBundle, ProjectionSpec
from edugraph.lab import demo, insight
from edugraph.lab.trace import girvan_newman_trace, louvain_trace


@pytest.fixture(scope="module", autouse=True)
def _registros() -> None:
    load_builtin_implementations()


def _projecao(students: int = 45, seed: int = 12, noise: float = 0.2) -> ProjectionBundle:
    dados = demo.build_demo(students, seed, noise)
    algoritmo = PROJECTIONS.get("manual_simple")
    return algoritmo.project(  # type: ignore[attr-defined, no-any-return]
        dados.bipartite, ProjectionSpec(side="student", weighting="simple")
    )


def _grupos(membership: dict[str, int]) -> set[frozenset[str]]:
    return {frozenset(g) for g in groups_of(membership).values()}


# ---------------------------------------------------------------------
# Turma de demonstração
# ---------------------------------------------------------------------


def test_mesma_semente_gera_a_mesma_turma() -> None:
    a = demo.build_demo(45, 12, 0.2)
    b = demo.build_demo(45, 12, 0.2)
    assert sorted(a.bipartite.graph.edges) == sorted(b.bipartite.graph.edges)
    assert a.student_area == b.student_area


def test_semente_diferente_gera_outra_turma() -> None:
    a = demo.build_demo(45, 12, 0.2)
    b = demo.build_demo(45, 13, 0.2)
    assert sorted(a.bipartite.graph.edges) != sorted(b.bipartite.graph.edges)


def test_disciplinas_da_demo_tem_nome_de_computacao_e_alunos_tem_nome_proprio() -> None:
    dados = demo.build_demo(45, 12, 0.2)
    rotulos = {d["label"] for _, d in dados.bipartite.graph.nodes(data=True)}
    assert {"Algoritmos", "Banco de Dados", "Redes de Computadores"} <= rotulos
    alunos = [dados.bipartite.graph.nodes[s]["label"] for s in dados.bipartite.students]
    assert all(any(c.isalpha() for c in nome) for nome in alunos)
    assert len(alunos) == len(set(alunos)), "dois alunos com o mesmo nome confundem a tela"


def test_demo_recusa_tamanho_fora_dos_limites() -> None:
    with pytest.raises(ValueError, match="entre"):
        demo.build_demo(demo.MAX_STUDENTS + 1, 1, 0.2)


def test_area_plantada_nao_entra_no_grafo() -> None:
    dados = demo.build_demo(30, 1, 0.2)
    for _, atributos in dados.bipartite.graph.nodes(data=True):
        assert set(atributos) == {"kind", "label"}, "o nó só pode ter kind e label (ADR-0008)"


# ---------------------------------------------------------------------
# Rastro do Girvan-Newman
# ---------------------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 12])
def test_girvan_newman_com_rastro_da_a_mesma_particao_do_algoritmo_registrado(seed: int) -> None:
    projecao = _projecao(30, seed, 0.1)
    rastro = girvan_newman_trace(projecao.graph, time_budget_s=30)
    registrado = COMMUNITIES.get("girvan_newman").run(  # type: ignore[attr-defined]
        projecao, time_budget_s=30
    )
    assert _grupos(rastro.membership) == _grupos(registrado.membership)
    assert rastro.q == pytest.approx(registrado.modularity)


def test_girvan_newman_remove_uma_aresta_por_vez_ate_esgotar_o_dendrograma() -> None:
    projecao = _projecao(24, 3, 0.1)
    rastro = girvan_newman_trace(projecao.graph, time_budget_s=30)
    assert len(rastro.removed) == projecao.graph.number_of_edges()
    assert rastro.splits[-1].k == projecao.graph.number_of_nodes()
    # cada corte só aparece depois de mais remoções que o anterior
    remocoes = [s.n_removed for s in rastro.splits]
    assert remocoes == sorted(remocoes)


def test_orcamento_estourado_devolve_timeout_e_nao_excecao() -> None:
    projecao = _projecao(45, 12, 0.2)
    rastro = girvan_newman_trace(projecao.graph, time_budget_s=1e-6)
    assert rastro.status in {"timeout", "skipped"}
    assert rastro.membership, "mesmo sem terminar, devolve a melhor partição vista"


def test_grafo_sem_arestas_nao_tem_o_que_cortar() -> None:
    grafo: nx.Graph = nx.Graph()
    grafo.add_nodes_from(["a", "b"])
    rastro = girvan_newman_trace(grafo)
    assert rastro.stop_reason == "no_edges"
    assert rastro.splits == []


# ---------------------------------------------------------------------
# Rastro do Louvain
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("students", "seed", "noise"), [(45, 7, 0.35), (60, 3, 0.35), (30, 1, 0.2)]
)
def test_louvain_com_rastro_fica_perto_do_q_da_biblioteca(
    students: int, seed: int, noise: float
) -> None:
    projecao = _projecao(students, seed, noise)
    rastro = louvain_trace(projecao.graph, seed=42)
    biblioteca = COMMUNITIES.get("louvain").run(projecao, seed=42)  # type: ignore[attr-defined]
    assert abs(rastro.q - biblioteca.modularity) < 0.02


def test_louvain_sem_ruido_recupera_as_areas_plantadas() -> None:
    dados = demo.build_demo(60, 5, 0.0)
    projecao = PROJECTIONS.get("manual_simple").project(  # type: ignore[attr-defined]
        dados.bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    rastro = louvain_trace(projecao.graph, seed=42)
    plantadas: dict[str, set[str]] = {}
    for aluno, area in dados.student_area.items():
        if aluno in projecao.graph:
            plantadas.setdefault(area, set()).add(aluno)
    obtidas = _grupos(rastro.membership)
    assert {frozenset(v) for v in plantadas.values()} == obtidas


def test_repetir_os_movimentos_guardados_chega_na_particao_final() -> None:
    rastro = louvain_trace(_projecao().graph, seed=42)
    comunidade = {indice: indice for indice in range(len(rastro.nodes))}
    for movimento in rastro.moves:
        for indice in movimento.members:
            comunidade[indice] = movimento.to
    refeita = {rastro.nodes[i]: c for i, c in comunidade.items()}
    assert _grupos(refeita) == _grupos(rastro.membership)


def test_q_do_ultimo_movimento_e_o_q_da_implementacao_a_mao() -> None:
    projecao = _projecao()
    rastro = louvain_trace(projecao.graph, seed=42)
    assert rastro.moves[-1].q == pytest.approx(rastro.q, abs=1e-9)
    assert rastro.q == pytest.approx(modularity(projecao.graph, rastro.membership))


def test_louvain_com_a_mesma_semente_refaz_os_mesmos_movimentos() -> None:
    grafo = _projecao().graph
    a = louvain_trace(grafo, seed=42)
    b = louvain_trace(grafo, seed=42)
    assert [(m.members, m.to) for m in a.moves] == [(m.members, m.to) for m in b.moves]


# ---------------------------------------------------------------------
# Nomes e papéis
# ---------------------------------------------------------------------


def test_comunidades_da_demo_levam_o_nome_das_disciplinas_que_reunem() -> None:
    dados = demo.build_demo(60, 5, 0.0)
    projecao = PROJECTIONS.get("manual_simple").project(  # type: ignore[attr-defined]
        dados.bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    rastro = louvain_trace(projecao.graph, seed=42)
    nomes = {
        c.name
        for c in insight.name_communities(projecao.graph, rastro.membership, dados.bipartite.graph)
    }
    assert any("Banco de Dados" in n for n in nomes)
    assert any("Redes de Computadores" in n or "Sistemas Operacionais" in n for n in nomes)
    assert not any(n.isdigit() for n in nomes)


def test_comunidades_sem_disciplina_com_nome_levam_o_nivel_de_engajamento() -> None:
    bip: nx.Graph = nx.Graph()
    proj: nx.Graph = nx.Graph()
    for i in range(6):
        bip.add_node(f"S{i}", kind="student", label=str(i))
        proj.add_node(f"S{i}", kind="student", label=str(i))
    for r in range(12):
        bip.add_node(f"D{r}", kind="discipline", label=str(7000 + r))
    for i in range(3):  # os três primeiros acessam 2 recursos; os outros, 10
        for r in range(2):
            bip.add_edge(f"S{i}", f"D{r}")
    for i in range(3, 6):
        for r in range(10):
            bip.add_edge(f"S{i}", f"D{r}")
    membership = {f"S{i}": 0 if i < 3 else 1 for i in range(6)}
    nomes = [
        c.name for c in insight.name_communities(proj, membership, bip, granularity="vle_site")
    ]
    assert sorted(nomes) == ["Mais engajados", "Menos engajados"]


def test_sem_ligacao_entre_grupos_ninguem_e_ponte() -> None:
    dados = demo.build_demo(60, 5, 0.0)
    projecao = PROJECTIONS.get("manual_simple").project(  # type: ignore[attr-defined]
        dados.bipartite, ProjectionSpec(side="student", weighting="simple")
    )
    rastro = louvain_trace(projecao.graph, seed=42)
    papeis = insight.node_roles(projecao.graph, rastro.membership)
    assert all(p.role in {"referencia", "periferico"} for p in papeis.values())


def test_com_mistura_entre_areas_aparecem_pontes() -> None:
    projecao = _projecao(60, 7, 0.35)
    rastro = louvain_trace(projecao.graph, seed=42)
    papeis = insight.node_roles(projecao.graph, rastro.membership)
    assert any(p.role in {"ponte", "conector"} for p in papeis.values())
    assert any(p.role == "referencia" for p in papeis.values())


def test_modularidade_baixa_e_descrita_como_falta_de_separacao() -> None:
    assert "quase nenhuma" in insight.modularity_reading(0.04)
    assert insight.modularity_reading(0.47) == "grupos bem definidos"


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------


@pytest.fixture
def client(artifact_roots) -> TestClient:
    return TestClient(create_app(artifact_roots))


def test_opcoes_do_laboratorio_listam_a_demo_e_os_limites(client: TestClient) -> None:
    corpo = client.get("/lab/options").json()
    assert corpo["sources"][0]["id"] == "demo"
    assert corpo["min_students"] == demo.MIN_STUDENTS
    assert corpo["max_students"] == demo.MAX_STUDENTS
    assert len(corpo["areas"]) == 3


@pytest.mark.parametrize("algoritmo", ["louvain", "girvan_newman"])
def test_laboratorio_monta_a_rede_e_devolve_o_passo_a_passo(
    client: TestClient, algoritmo: str
) -> None:
    resposta = client.post("/lab/run", json={"algorithm": algoritmo, "students": 30})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["result"]["n_communities"] >= 2
    assert set(corpo["result"]["membership"]) == {n["id"] for n in corpo["projection"]["nodes"]}
    assert corpo["bipartite"]["edges"], "o passo do bipartido precisa das matrículas"
    assert corpo["insight"]["communities"] and corpo["insight"]["summary"]
    assert corpo["reveal"]["planted"]["purity"] > 0.5
    assert (corpo["louvain"] is not None) == (algoritmo == "louvain")
    assert (corpo["girvan_newman"] is not None) == (algoritmo == "girvan_newman")


def test_laboratorio_louvain_mostra_o_q_da_biblioteca_ao_lado(client: TestClient) -> None:
    referencia = client.post("/lab/run", json={}).json()["louvain"]["reference"]
    assert referencia["library"] == "python-louvain"
    assert 0 <= referencia["q"] <= 1


def test_laboratorio_recusa_mais_alunos_que_o_limite(client: TestClient) -> None:
    resposta = client.post("/lab/run", json={"students": demo.MAX_STUDENTS + 1})
    assert resposta.status_code == 422


def test_corte_de_ligacoes_que_nao_deixa_nenhuma_diz_o_que_fazer(client: TestClient) -> None:
    resposta = client.post("/lab/run", json={"min_weight": 1e6})
    assert resposta.status_code == 422
    assert "diminua" in resposta.json()["detail"]


@pytest.mark.dataset("synthetic_v1")
def test_laboratorio_amostra_um_dataset_em_disco(client: TestClient) -> None:
    resposta = client.post(
        "/lab/run", json={"source": "synthetic_v1", "students": 30, "algorithm": "louvain"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["source"]["fictional"] is False
    assert len(resposta.json()["bipartite"]["students"]) == 30


@pytest.mark.dataset("synthetic_v1")
def test_leitura_de_particao_em_disco_nomeia_comunidades_e_papeis(client: TestClient) -> None:
    corpo = client.get("/datasets/synthetic_v1/communities/louvain__student_simple/insight").json()
    assert len(corpo["communities"]) == 3
    assert set(corpo["roles"]) >= {"S100001"}
    assert sum(corpo["role_counts"].values()) == len(corpo["roles"])
    assert corpo["summary"][0].startswith("Foram encontrados 3 grupos")


@pytest.mark.dataset("synthetic_v1")
def test_desfecho_por_comunidade_so_aparece_na_rota_de_revelacao(client: TestClient) -> None:
    corpo = client.get("/datasets/synthetic_v1/communities/louvain__student_simple/outcomes").json()
    assert len(corpo["rows"]) == 3
    for linha in corpo["rows"]:
        assert sum(linha["rates"].values()) == pytest.approx(1.0)
    leitura = client.get("/datasets/synthetic_v1/communities/louvain__student_simple/insight")
    assert "outcome" not in leitura.text.lower()


# ---------------------------------------------------------------------
# Texto e sugestão de corte
# ---------------------------------------------------------------------


def test_frases_concordam_em_numero_e_genero_com_disciplinas() -> None:
    grafo: nx.Graph = nx.Graph()
    for nome in "abc":
        grafo.add_node(nome, kind="discipline", label=nome.upper())
    grafo.add_edges_from([("a", "b", {"weight": 2.0}), ("b", "c", {"weight": 1.0})])
    papeis = {
        "a": insight.RoleInfo("referencia", 1.2, 0.0),
        "b": insight.RoleInfo("periferico", 0.0, 0.1),
        "c": insight.RoleInfo("periferico", 0.0, 0.1),
    }
    comunidades = insight.name_communities(grafo, {"a": 0, "b": 0, "c": 1})
    frases = insight.summarize(grafo, 0.3, comunidades, papeis)
    assert "1 disciplina é referência no próprio grupo." in frases
    assert any(f.startswith("Nenhuma disciplina se destaca como ponte") for f in frases)
    assert not any("1 disciplinas" in f for f in frases)


def test_grupo_de_um_aluno_leva_o_nome_dele_e_a_descricao_no_singular() -> None:
    bip: nx.Graph = nx.Graph()
    proj: nx.Graph = nx.Graph()
    for i, nome in enumerate(["Ana C.", "Bia D.", "Caio E."]):
        bip.add_node(f"S{i}", kind="student", label=nome)
        proj.add_node(f"S{i}", kind="student", label=nome)
    for d in ("Redes", "Dados"):
        bip.add_node(d, kind="discipline", label=d)
    bip.add_edges_from([("S0", "Redes"), ("S1", "Redes"), ("S2", "Dados")])
    comunidades = insight.name_communities(proj, {"S0": 0, "S1": 0, "S2": 1}, bip)
    sozinho = next(c for c in comunidades if c.size == 1)
    assert sozinho.name == "Caio E."
    assert sozinho.description.startswith("1 aluno ·")


def test_laboratorio_sugere_corte_em_rede_quase_completa_e_nao_em_rede_leve(
    artifact_roots,
) -> None:
    from edugraph.lab.service import run_lab

    leve = run_lab(roots=artifact_roots, students=30)
    assert leve["projection"]["suggested_min_weight"] is None


@pytest.mark.dataset("synthetic_v1")
def test_corte_sugerido_reduz_a_rede_sem_apagar_os_nos(artifact_roots) -> None:
    from edugraph.lab.service import run_lab

    cheia = run_lab(roots=artifact_roots, source="synthetic_v1", students=75)
    corte = cheia["projection"]["suggested_min_weight"]
    assert corte is not None
    cortada = run_lab(roots=artifact_roots, source="synthetic_v1", students=75, min_weight=corte)
    assert len(cortada["projection"]["edges"]) < len(cheia["projection"]["edges"])
    assert len(cortada["projection"]["nodes"]) == len(cheia["projection"]["nodes"])
