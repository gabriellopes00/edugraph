# Specs da Frente A — Dados e Modelagem  `[A]`

ETL do OULAD, gerador sintético, grafo bipartido e as duas projeções.

**Produz** `bipartite/`, `projections/`, `outcomes.csv` e
`metrics/projections.csv`. **Consome** apenas CSV bruto.

| ID | Spec | Consome | Cumpre | Artigo |
|---|---|---|---|---|
| [A-01](A-01-gerador-sintetico.md) | Gerador sintético determinístico | — | Bipartite, Outcomes | decisão metodológica (base secundária) |
| [A-02](A-02-etl-oulad.md) | ETL do OULAD | CSV bruto | tabela normalizada | estatísticas do dataset |
| [A-03](A-03-bipartido-parametrizavel.md) | Bipartido parametrizável | tabela normalizada | Bipartite | critério de aresta (ADR-0007) |
| [A-04](A-04-projecoes-manuais.md) | Projeções à mão | Bipartite | Projection | **algoritmo implementado à mão** |
| [A-05](A-05-comparacao-projecao.md) | Manual × NetworkX | Bipartite | `metrics/projections.csv` | tabela + figura |
| [A-06](A-06-escala.md) | Escala e rodada do OULAD | tabela normalizada | Bipartite, Projection | limitação reportada |
| [A-07](A-07-estatisticas-bipartido.md) | Estatísticas e figura | Bipartite | — | figura + tabela |
| [A-09](A-09-granularidades-do-ava.md) | **Granularidades do AVA** | CSV bruto | Bipartite, Projection | **tabela**: o critério de aresta escolhido depois de medir |

## Ordem sugerida

**Onda 1:** A-01, A-02 · **Onda 2:** A-03, A-04 · **Onda 3:** A-05, A-06
· **Onda 4:** A-07.

A-06 é a que **destrava as outras frentes de verdade**: quando
`data/processed` existir, B e C trocam `--root` e param de usar fixtures.

## Estado (18/09/2026)

| Spec | Estado |
|---|---|
| A-01 | concluída |
| A-02 | concluída, incluindo a rodada na base completa |
| A-03 | concluída |
| A-04 | concluída — na coorte real, mais rápida que o NetworkX |
| A-05 | concluída, com os números do OULAD |
| A-06 | concluída — reduções testadas e limite de escala medido |
| A-07 | concluída, com tabela e figura do OULAD |
| A-08 | concluída — modelo nulo (spec nova, nasceu da rodada real) |
| A-09 | concluída — granularidades do AVA (spec nova, nasceu da A-08) |

**As nove specs da Frente A estão fechadas.**

## Reproduzir a rodada real

O OULAD é download manual (~45 MB compactados, 450 MB extraídos) e fica
fora do git. Para refazer tudo numa máquina nova:

```bash
python scripts/download_oulad.py                     # espelho do UCI, com SHA-256 conferido
python -m edugraph data etl                          # 6 s, pico de 171 MB
python -m edugraph run configs/oulad_cohort_bbb_2013j.toml --only data     # 22 s
python -m edugraph run configs/oulad_module_presentation.toml --only data  # 4 s
# linha de base para a Frente B (A-08):
python -m edugraph data null --root data/processed \
    --dataset oulad_module_presentation --replicas 5
# o bipartido pelo AVA — o que tem sinal para comunidades (A-09):
python -m edugraph run configs/oulad_vle_bbb_2013j.toml --only data
python -m edugraph data null --root data/processed \
    --dataset oulad_vle_bbb_2013j --replicas 5
python -m edugraph validate --root data/processed
pytest tests/contract --artifacts-root data/processed
```

**Não rode a projeção aluno↔aluno de `module_presentation` sem
amostra**: são ~15,9 milhões de pares, passou de 5 GB sem terminar em
10 min (ver A-06). Use a coorte ou `data sample`.

`tests/data/oulad_mini/` continua sendo a fixture do ETL: sete tabelas em
miniatura com o esquema real — agora com cabeçalhos entre aspas e `?`
como ausente, como na distribuição do UCI.

## O que a Frente A entrega para B e C

Em `data/processed`, prontos para `--root`:

- `oulad_bbb_2013j` — coorte BBB 2013J por avaliação: 1.706 alunos,
  11 avaliações, projeções aluno↔aluno e disciplina↔disciplina. Sem
  corte, a projeção aluno↔aluno teria 1,45 M arestas; com o `min_weight`
  da configuração ficam 476.591 (simples) e 608.558 (alocação de
  recursos).
- `oulad_module_presentation` — base inteira, 22.425 alunos, 22
  disciplinas; projeções **de disciplina** (as de aluno não cabem).
- `oulad_module_presentation_null0..4` — réplicas nulas (A-08), a linha
  de base contra a qual a spec B-06 mede a modularidade.
- `oulad_vle_bbb_2013j` — coorte BBB 2013J **pelo AVA** (A-09): 1.870
  alunos × 320 recursos, projeção aluno↔aluno com 1.746.901 arestas. É o
  dataset com sinal para comunidades de alunos.
- `oulad_vle_bbb_2013j_null0..4` — réplicas nulas dele.

**Leia a A-08 antes de reportar qualquer Q.** Na projeção aluno↔aluno de
`oulad_module_presentation` (medida numa amostra de 3.000 alunos,
porque a projeção inteira não cabe na memória), o Q real (0,77) é menor
que o das réplicas embaralhadas — não há estrutura a reportar ali, e isso
é o resultado.
Para comunidades de alunos, use `oulad_vle_bbb_2013j` (A-09), onde o Q
real fica ~5× acima do nulo.
