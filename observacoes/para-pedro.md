# Observações para o Pedro — Frente A

Ver as regras em [`README.md`](README.md).

## Abertas

### A-OBS-09 · Revisar a mudança da Frente C na configuração do AVA

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `configs/oulad_vle_bbb_2013j.toml:87-101` (commit `c819046`)
- **O quê:** `weight_mode = "distance"` não existe no contrato
  (`none`/`inverse`/`raw`) e derrubava o estágio de centralidade. Foi trocado
  por `"inverse"`, que é a mesma intenção do comentário original (usar o
  peso porque a projeção é quase completa: densidade 1,000), com `k = 200` e
  `seed = 42`. A decisão está em `docs/artigo/decisoes-metodologicas.md`.
- **Como resolver:** conferir se concorda; se não, abrir observação para o
  Lucas.

### A-OBS-10 · Sugestão: bipartido por matrícula, sem limiar de nota

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** —
- **O quê:** a validação da C-06 tira a matrícula do bipartido com
  `score_threshold = 40`. Os 3.674 alunos sem nenhuma nota acima de 40 ficam
  fora, e são os que mais reprovam; a taxa absoluta sai subestimada. Um
  bipartido por matrícula, sem limiar, permitiria a validação sem esse viés.
- **Como resolver:** não é bloqueio. Se houver tempo, gerar o bipartido e
  avisar o Lucas.

## Resolvidas

### A-OBS-01 · Teste sem marcador de dataset quebra em vez de ser pulado

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `tests/data/test_scale.py:78`
  (`test_coorte_em_bipartido_por_modulo_aponta_para_a_a03`)
- **O quê:** o teste carrega `synthetic_v1`, mas não declara
  `@pytest.mark.dataset("synthetic_v1")`. Rodando
  `pytest tests --artifacts-root data/processed` (sem as fixtures na raiz),
  ele falha com `ArtifactNotFoundError` em vez de ser pulado, contrariando a
  regra de testes do `CLAUDE.md`. A CI não pega porque roda sobre as
  fixtures.
- **Como resolver:** acrescentar `@pytest.mark.dataset("synthetic_v1")` antes
  da função.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — `@pytest.mark.dataset("synthetic_v1")` acrescentado; com `--artifacts-root` vazio o teste é pulado.

### A-OBS-02 · Receita da rodada real não gera `discipline_resource_allocation`

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-a/README.md:53-55` (seção "Reproduzir a rodada
  real")
- **O quê:** a receita projeta só `--weighting simple` para
  `oulad_module_presentation`, mas `configs/oulad_module_presentation.toml`
  declara também `discipline_resource_allocation`. Quem segue a receita e
  depois roda `run ... --only centrality` recebe erro de artefato não
  encontrado. Conferido rodando a receita numa pasta temporária.
- **Como resolver:** acrescentar a linha com `--weighting resource_allocation`,
  ou trocar os dois passos por
  `python -m edugraph run configs/oulad_module_presentation.toml --only data`.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — os dois passos trocados por `run configs/oulad_module_presentation.toml --only data`, que gera as projeções que a configuração declara.

### A-OBS-03 · README cita `null0..2`, mas são cinco réplicas

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-a/README.md:83`
- **O quê:** diz `oulad_module_presentation_null0..2`; a receita usa
  `--replicas 5`, e o disco tem `null0` a `null4`.
- **Como resolver:** trocar para `null0..4`.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — trocado para `null0..4`.

### A-OBS-04 · Q = 0,77 atribuído à projeção inteira, mas veio de amostra

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-a/README.md:91`
- **O quê:** o texto atribui o Q real de 0,77 à "projeção aluno↔aluno de
  `oulad_module_presentation`". A A-08 (linha 33) registra que o número saiu
  de uma amostra de 3.000 alunos, porque a projeção inteira não cabe na
  memória.
- **Como resolver:** dizer que é a amostra de 3.000 alunos.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — o texto diz que o Q = 0,77 veio da amostra de 3.000 alunos.

### A-OBS-05 · Critério da A-04 ainda "Pendente", mas já foi medido

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-a/A-04-projecoes-manuais.md:62-63`
- **O quê:** o critério de tempo sobre uma coorte do OULAD continua `[ ]` e
  "Pendente", com a spec marcada como concluída. A A-06 (linha 63) já
  registra a medição: coorte BBB_2013J, estágio data, 22 s.
- **Como resolver:** marcar `[x]` e citar a medição da A-06.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — critério marcado `[x]`, citando a medição da A-06 (22 s).

### A-OBS-06 · Configuração cita arquivo que não existe

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `configs/oulad_module_presentation.toml:8` e `:25`
- **O quê:** a linha 8 menciona `oulad_module_baseline.toml`, que não existe
  em `configs/`. A linha 25 mantém a nota "conferir em A-02", já resolvida.
- **Como resolver:** criar a configuração ou tirar a menção; remover a nota
  antiga.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — menção a `oulad_module_baseline.toml` retirada (a degeneração fica registrada por `synthetic_v1`) e nota "conferir em A-02" removida.

### A-OBS-07 · `configs/README.md` não lista a configuração do AVA

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `configs/README.md`
- **O quê:** a tabela não tem `oulad_vle_bbb_2013j.toml`, que é a
  configuração das comunidades de alunos (A-09).
- **Como resolver:** acrescentar a linha.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — linha de `oulad_vle_bbb_2013j.toml` acrescentada à tabela.

### A-OBS-08 · Docstrings falam de stub e `xfail` que não existem mais

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `tests/data/test_projections.py:8` e
  `src/edugraph/data/synthetic.py:10-11`
- **O quê:** a primeira diz que o teste da A-05 "continua `xfail`"; a
  segunda fala dos "pontos marcados com `NotImplementedError("A-01")`". Não
  há mais nenhum dos dois no repositório.
- **Como resolver:** atualizar os dois textos.
- **Resolvida:** 30/10/2026 por Pedro, branch `a/entrega-revisao` — as duas docstrings descrevem o estado atual (A-05 sem `xfail`, A-01 fechada, sem `NotImplementedError`).
