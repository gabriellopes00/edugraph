# [A-07] Estatísticas descritivas e figura do bipartido

**Frente:** A
**Status:** concluída sobre as fixtures (18/09/2026); a figura final do artigo sai da rodada do OULAD

## Objetivo

Produzir a tabela de estatísticas descritivas e a figura do grafo
bipartido que abrem a seção de dados do capítulo 3.

## Contexto

**Cumpre:** `results/tables/` e `results/figures/`.
**Consome:** `BipartiteBundle`.

Requisito que vem do artigo, não do software (briefing §9): refazer uma
figura na semana da entrega tem que ser um comando, não arqueologia.

## Dependências

- A-03, para ter um bipartido.
- **Neutralizada por:** as fixtures já têm bipartidos; dá para fechar a
  spec sobre elas e só trocar `--root` depois.

## Escopo

### Incluído

- `describe()` / `table_dataset_stats()`: nº de alunos, de disciplinas,
  de arestas, densidade, grau médio de cada lado, distribuição de grau.
- `figure_bipartite()`: os dois lados em colunas. Em grafos grandes,
  **amostrar ou agregar e dizer na legenda o que foi feito** — desenhar
  28 mil nós não comunica nada.
- Comando `edugraph data report --dataset X`.
- Geração do índice de figuras (`edugraph figures --index`), arquivo
  **gerado**, nunca editado à mão.

### Fora de escopo

- Figuras de comunidades (B-07) e de centralidade (C-07).

## Critérios de aceite

- [x] Dado `synthetic_v1`, quando rodar `describe`, então a tabela traz
      98 alunos, 7 disciplinas e 197 arestas.
- [x] Dado qualquer dataset, quando gerar a figura, então saem PNG e SVG
      em `results/figures/`, com o estilo de `reporting.figures.STYLE`.
- [x] Dado um grafo com mais de mil nós, quando gerar a figura, então a
      redução aplicada aparece na legenda.
- [x] Rodar duas vezes produz a mesma figura.
- [x] `docs/artigo/indice-figuras.md` é gerado, não editado.

## Testes exigidos

- **Unitários:** `tests/data/test_report.py`, 11 testes — `describe` em
  `tiny_v1` contra valores à mão (6, 3, 10; densidade 10/18) e em
  `synthetic_v1` (98, 7, 197); linha da tabela carrega a especificação;
  figura em PNG e SVG com legenda; **bytes idênticos em duas execuções**;
  grafo de 1.200 alunos amostrado com a legenda dizendo; índice cruza
  plano e disco, determinístico; comandos `data report` e
  `figures --index`.
- Sem teste de aparência — comparação de imagem é frágil e não paga.

## Arquivos criados ou alterados

- `src/edugraph/data/report.py`.
- `src/edugraph/reporting/figures.py` — `build_index` (a lista planejada
  vive em `PLANNED_FIGURES`, no código, para o `.md` poder ser regenerado);
  `save_figure` sem data nos metadados do SVG, para a figura ser
  reproduzível byte a byte.
- `src/edugraph/__main__.py` — comando `figures --index`.
- `src/edugraph/data/bipartite.py` — `describe`.
- `src/edugraph/data/cli.py` — `cmd_report`.
- `tests/data/test_report.py` (novo).

## Impacto no artigo

**Figura 2** (grafo bipartido) e a **tabela de estatísticas do dataset**,
ambas do capítulo 3.
