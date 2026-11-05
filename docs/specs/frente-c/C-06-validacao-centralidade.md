# [C-06] Validação a posteriori da centralidade

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Verificar se as disciplinas que a topologia aponta como gargalo têm, de
fato, taxa de reprovação acima da base — e se a centralidade do aluno se
relaciona com o desfecho dele.

## Contexto

**Cumpre:** tabela e figura de validação.
**Consome:** `CentralityResult`, `Outcomes`.

**Único módulo da Frente C autorizado a ler `outcomes.csv`** (ADR-0008),
mesma regra do `evaluate.py` da Frente B.

## Dependências

- C-01, C-02 e C-03.
- `outcomes.csv`, que já existe nas fixtures.

## Escopo

### Incluído

- `failure_rate_by_discipline(ranking, outcomes, enrollment)` — taxa de
  reprovação nas disciplinas críticas **contra a taxa da base**.
- `outcome_by_centrality(result, outcomes, quantiles)` — distribuição de
  desfechos por quartil de centralidade do aluno.
- Comando `edugraph centrality evaluate`.
- Tratar o caso sem `planted_group` (OULAD).

### Fora de escopo

- Usar o desfecho como entrada de qualquer cálculo de centralidade.
- Teste de significância estatística.

## Critérios de aceite

- [x] Dada a fixture, quando avaliar, então a tabela traz a taxa de
      reprovação das disciplinas críticas e a da base, lado a lado.
- [x] Dada a centralidade dos alunos, então a distribuição de desfechos
      por quartil sai com uma linha por quartil.
- [x] Dado `synthetic_v1`, onde a intermediação das disciplinas é toda
      zero (K₇), então a spec **reporta isso** em vez de produzir um
      ranking sem sentido — a validação só é informativa com
      granularidade mais fina.
- [x] Nenhum rótulo alimenta cálculo: `test_outcomes_isolation` verde.

## Testes exigidos

- **Contrato:** `test_outcomes_isolation`.
- **Unitários:** taxa da base calculada corretamente sobre `tiny_v1`;
  quartis cobrem todos os alunos.

## Arquivos criados ou alterados

- `src/edugraph/centrality/evaluate.py`.
- `src/edugraph/centrality/cli.py` — `cmd_evaluate`.
- `tests/centrality/test_validacao.py` (novo).

## Impacto no artigo

**Tabela + figura.** E, se a relação não aparecer, isso é resultado: o
artigo reporta que centralidade estrutural e desempenho histórico são
dimensões independentes — o que, aliás, reforça que a centralidade não é
um proxy disfarçado do desfecho.

## Como ficou (25/09/2026)

- `python -m edugraph centrality evaluate --root data/processed --dataset <ds>
  --metric <m> --tables results/tables --figures results/figures`.
- **Não conclusão = `Fail` + `Withdrawn`**; `rate_Fail` fica na tabela
  para a reprovação estrita. Taxas sobre os alunos com desfecho conhecido
  (`n_labeled`).
- **Tabela 8** (`tab8-reprovacao-<ds>-<métrica>.csv`): cada disciplina do
  top-N, o conjunto delas (`critical_all`), as demais (`others`) e a base,
  com o excesso sobre a base. **Tabela 8b**
  (`tab8b-desfecho-faixa-<ds>-<métrica>.csv`) e **figura 8**: desfecho por
  quartil de centralidade do aluno, por posição no ranking.
- **Métrica degenerada** (tudo igual, como a intermediação em K₇) não gera
  tabela: sai uma nota explicando a decisão D1.
- Só `evaluate.py` chama `load_outcomes`; o relatório (C-07) recebe as
  taxas agregadas da função `evaluate`.
- Resultados e as duas ressalvas (desfecho por aluno; matrícula com limiar
  de nota 40) em `docs/artigo/decisoes-metodologicas.md`.
