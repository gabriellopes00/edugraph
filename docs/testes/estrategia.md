# Estratégia de testes

Os testes de contrato **são** o mecanismo de paralelismo. Não é retórica:
são literalmente os mesmos testes que rodam hoje sobre `data/fixtures` e
amanhã sobre o OULAD em `data/processed`. Quando a Frente A entregar a
projeção de verdade, B e C funcionam sem alteração de código — e é a
suíte que prova isso (briefing §4.4).

## Como rodar

```bash
pytest                                            # sobre as fixtures (padrão)
pytest tests --artifacts-root data/processed      # sobre o que a Frente A gerou
pytest tests --artifacts-root data/processed --artifacts-root data/fixtures
pytest -m "not slow"                              # o que a CI roda
pytest tests/community                            # só uma frente
```

**O `tests` explícito importa quando se usa `--artifacts-root`**: o
`pytest_addoption` vive em `tests/conftest.py`, e o pytest só registra
opções dos conftests dos caminhos passados na linha de comando. Sem o
caminho, a opção não existe ainda e o comando falha com
`unrecognized arguments`. (Descoberto ao rodar a suíte sobre a saída da
Frente B, em 20/09/2026.)

Alternativa por ambiente, que não tem esse detalhe:
`EDUGRAPH_ROOTS="data/processed:data/fixtures"` (`;` no Windows).

Testes que dependem de um dataset específico declaram
`@pytest.mark.dataset("synthetic_v1")` e são **pulados**, não quebrados,
quando a raiz em uso não o contém.

## As camadas

| Camada | Onde | O que garante | Frente |
|---|---|---|---|
| Contrato | `tests/contract/` | validadores sobre todo artefato da raiz; round-trip; escrita canônica; nenhum rótulo em `nodes.csv`; nenhum import cruzado; nenhuma dependência de ML; implementações registradas satisfazem os protocolos | `[T]` |
| Unitário A | `tests/data/` | pesos de `tiny_v1` batem com `expected/`; manual = NetworkX até 1e-9; ETL sobre `oulad_mini`; critério e granularidade mudam o grafo | `[A]` |
| Unitário B | `tests/community/` | **91 testes, todos passando.** Louvain recupera os 2 grupos de `tiny_v1` e as 3 áreas de `synthetic_v1`; mesma seed, mesma partição; orçamento estourado devolve `timeout`/`skipped` sem exceção; Q à mão = NetworkX e = forma ingênua; 100 mil arestas em 80 ms; NMI ≥ 0,8 contra o grupo plantado; a tabela comparativa é idempotente; as figuras saem determinísticas | `[B]` |
| Unitário C | `tests/centrality/` | valores exatos em `tiny_v1`; iteração de potência = NetworkX; fallback sem exceção; empate na projeção degenerada; discordância entre métricas | `[C]` |
| API | `tests/api/` | cada rota responde 200 sobre a fixture e valida no schema; 404 para inexistente | `[C]` |
| Lentos | marcador `slow` | Girvan-Newman completo, OULAD inteiro. Fora da CI, sob demanda | todos |

## Estado atual da suíte

**358 testes passando, 1 pulado, 0 `xfail`, 1 desmarcado e nenhuma falha**
(20/10/2026, `pytest -m "not slow" -q`, sobre as fixtures). O teste
pulado depende de `oulad_module_presentation`, ausente nas fixtures; o
filtro exclui o único teste `slow`. A execução emitiu 1 aviso de
depreciação do TestClient/HTTPX.

As specs da Frente C estão implementadas; não há marcadores `xfail`
restantes. Para futuras specs abertas, o procedimento continua sendo
`raises=NotImplementedError, strict=True`, com o id no `reason`:
quando a implementação passa, a CI exige remover o marcador.

O único teste `slow` é o Girvan-Newman completo sobre `synthetic_v1`
(34 s): é ele que mede o custo relativo ao Louvain, o número que vai
para o capítulo 3. Roda sob demanda, com `pytest -m slow`.

## Os quatro testes que protegem o trabalho

Se um dia a suíte tiver de ser reduzida, estes ficam:

1. **`test_import_boundaries.py`** — nenhuma frente importa outra. É a
   fronteira do briefing §4.3 como código executável.
2. **`test_no_ml.py`** — nenhum import, nenhuma dependência declarada de
   biblioteca de ML. É a restrição inegociável do briefing §2 como
   código executável. Um "só pra comparar" com `sklearn` quebra a CI
   antes de virar parágrafo que não se sustenta na banca.
3. **`test_outcomes_isolation.py`** — nenhum `nodes.csv` com rótulo;
   `load_outcomes` só em `evaluate.py`.
4. **`test_roundtrip.py`** — escrever → ler → escrever preserva tudo e
   produz os mesmos bytes. É o que torna um diff em `data/fixtures/` um
   sinal confiável.

## Por que `tiny_v1` tem `expected/`

Comparar a implementação à mão com a fixture gerada pelo NetworkX seria
comparar duas bibliotecas. `data/fixtures/tiny_v1/expected/` contém
valores **derivados no papel**, e é contra eles que as specs A-04, C-01 e
C-02 são verificadas.

A estrutura de `tiny_v1`: seis alunos, três disciplinas. Graus no
bipartido: DA = 4 (S1, S2, S3, S6), DB = 3 (S1, S2, S3), DC = 3 (S3, S4,
S5).

**Projeção aluno↔aluno simples** — número de disciplinas em comum:
S1-S2 = S1-S3 = S2-S3 = 2; todos os demais pares ligados = 1.

**Alocação de recursos** — DA contribui 1/4, DB e DC contribuem 1/3:

| Par | Simples | Alocação de recursos |
|---|---|---|
| S1-S2, S1-S3, S2-S3 | 2 | 1/4 + 1/3 = 0,5833… |
| S1-S6, S2-S6, S3-S6 | 1 | 1/4 = 0,25 |
| S3-S4, S3-S5, S4-S5 | 1 | 1/3 = 0,3333… |

Repare nas duas últimas linhas: **empatam em 1 na projeção simples e se
separam na alocação de recursos**. É o contraexemplo mínimo do viés de
grau, e tem um teste dedicado.

**Grau e intermediação.** O grafo é um K4 em {S1, S2, S3, S6} colado a um
triângulo {S3, S4, S5}. Grau normalizado por n−1 = 5: S3 = 1,0; S1 = S2 =
S6 = 0,6; S4 = S5 = 0,4.

Intermediação normalizada por (n−1)(n−2)/2 = 10: S3 é o **único** vértice
de corte, e os 6 pares {S1, S2, S6} × {S4, S5} passam por ele, então S3 =
6/10 = 0,6 e todos os outros = 0.

**Autovetor.** Sobre `discipline_simple` ponderado (DA-DB = 3, DA-DC =
DB-DC = 1). Por simetria, x = DA = DB e y = DC:

```
λx = 3x + y        λy = 2x
  ⇒  λ = 3 + 2/λ  ⇒  λ² − 3λ − 2 = 0  ⇒  λ = (3 + √17)/2 ≈ 3,5616
  ⇒  y = 2x/λ,  normalizado em L2:  x = 1/√(2 + 4/λ²)
```

Resultado: DA = DB ≈ 0,6571923, DC ≈ 0,3690482 — **conferido contra o
NetworkX na geração da fixture, com igualdade até a décima casa**.

## O que os testes deliberadamente não afirmam

**Não afirmam que uma disciplina específica lidera a intermediação em
`synthetic_v1`.** Com V = módulo, `discipline_simple` é o grafo completo
K₇: todas as disciplinas empatam em zero. O teste correto **afirma a
degeneração** — se um dia ele falhar, é porque a granularidade mudou e a
spec C-03 passou a ter o que ranquear. Ver a decisão D1 e
`data/fixtures/synthetic_v1/REFERENCE.md`.

**Não exigem igualdade exata de Q.** Louvain é estocástico. Um teste que
exige Q = 0,4712 quebra na primeira troca de versão da biblioteca sem que
nada esteja errado. As faixas ([0,40, 0,55]) são largas de propósito: elas
pegam regressão real, não flutuação.

## Convenções

- Nomes de teste em português, descrevendo o comportamento:
  `test_orcamento_estourado_devolve_timeout_e_nao_excecao`.
- Um `assert` por conceito; mensagem de erro que diga o que fazer.
- `tmp_path` para qualquer escrita — nenhum teste escreve em
  `data/fixtures`.
- Fixtures compartilhadas em `tests/conftest.py`; nada de caminho
  absoluto embutido num teste.
