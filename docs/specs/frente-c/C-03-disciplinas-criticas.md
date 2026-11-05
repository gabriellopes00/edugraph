# [C-03] Disciplinas críticas e discordância entre métricas

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Identificar as disciplinas críticas no fluxo curricular, via centralidade
sobre os nós de **disciplina**, e mostrar onde as três métricas
discordam.

## Contexto

**Cumpre:** `metrics/centrality_top.csv`.
**Consome:** `CentralityResult`.

**Saída obrigatória** (briefing §6.2), e a que a seção 13 do briefing
avisa ser fácil de esquecer: a centralidade precisa ser aplicada sobre os
nós de disciplina, na projeção disciplina↔disciplina, **não só sobre
alunos**.

Um nó de alta intermediação na projeção disciplina↔disciplina é um ponto
por onde passa a ligação entre partes do currículo que, de outro modo,
estariam distantes — um gargalo estrutural. Nada disso depende de
desfecho: o gargalo é topológico.

## Dependências

- C-01 e C-02, para ter as três métricas.

## Escopo

### Incluído

- `rank_disciplines(results, top_n)` → linhas de `METRICS_COLUMNS`.
- **Desempate determinístico por `node_id`.** Não é detalhe: na projeção
  disciplina↔disciplina de `synthetic_v1`, que é K₇, *todos* empatam. Sem
  desempate, a tabela do artigo muda de uma execução para outra.
- `critical_set(results, top_n)` — conjunto por métrica, para o relatório
  interno.
- `disagreement(results, top_n)` — os quatro conjuntos: só grau, só
  intermediação, só autovetor, e as três.
- `rank_correlation()` — Spearman entre dois rankings. Estatística
  descritiva sobre rankings conhecidos, não modelo.
- Comando `edugraph centrality critical`.

### Fora de escopo

- Cruzar com a taxa de reprovação — é a C-06. Aqui o critério é
  **puramente topológico**, e é isso que dá sentido à validação depois.

## Critérios de aceite

- [x] Dado `synthetic_v1`/`discipline_simple`, quando ranquear duas
      vezes, então o resultado é **idêntico** — mesmo com todos os nós
      empatados.
- [x] `metrics/centrality_top.csv` tem as colunas de `METRICS_COLUMNS` e
      é idempotente por `(dataset, projection_id, metric, rank)`.
- [x] Dado um `top_n` maior que o número de disciplinas, então devolve o
      ranking inteiro sem erro — com 7 ou 22 disciplinas, esse é o caso
      desejável.
- [x] `disagreement` devolve os quatro conjuntos, ordenados.
- [x] Dada uma granularidade mais fina (`module_presentation`), então o
      ranking **discrimina** — se continuar empatando tudo, a decisão D1
      precisa ser revisitada e isso vira achado.

## Testes exigidos

- **Contrato:** idempotência de `metrics/centrality_top.csv`.
- **Unitários** (já escritos como `xfail`): determinismo do ranking sob
  empate total; discordância sobre um caso construído onde grau e
  intermediação divergem.

## Arquivos criados ou alterados

- `src/edugraph/centrality/critical_disciplines.py`, `disagreement.py`.
- `src/edugraph/centrality/cli.py` — `cmd_critical`.
- `tests/centrality/test_centralidades.py`.

## Impacto no artigo

**Saída obrigatória** + tabela de disciplinas críticas. A discordância
entre métricas é o material da discussão: um nó no topo da intermediação
mas não do grau é ponte sem ser popular — exatamente o perfil de uma
disciplina-gargalo que poucos cursam mas que conecta áreas.
