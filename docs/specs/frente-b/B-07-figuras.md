# [B-07] Figuras de comunidades

**Frente:** B
**Status:** concluída (20/09/2026) sobre `synthetic_v1`; a figura final do artigo sai da rodada do OULAD

## Objetivo

Gerar as figuras de comunidades do capítulo 3: o grafo com cor por
comunidade e a distribuição de tamanhos.

## Contexto

**Cumpre:** `results/figures/`.
**Consome:** `Partition`, `ProjectionBundle`.

Briefing §9: refazer uma figura na semana da entrega tem que ser um
comando.

## Dependências

- B-01 e B-02, para ter partições.
- **Neutralizada por:** as partições de referência das fixtures.

## Escopo

### Incluído

- `figure_communities(partition, projection, out, layout)` — cor por
  comunidade.
- **Em grafos grandes, agregar**: um nó por comunidade, área proporcional
  ao tamanho, aresta proporcional ao número de ligações entre
  comunidades. Desenhar dois mil pontos não comunica nada.
- `figure_size_distribution(partitions, out)` — um painel por algoritmo.
- Figura de Q × tempo por algoritmo (alimenta a B-04).
- Estilo comum de `reporting.figures.STYLE`; PNG e SVG.

### Fora de escopo

- Visualização interativa — é a C-05.
- Escolher paleta própria: usar uma escala qualitativa acessível e
  registrar qual.

## Critérios de aceite

- [x] Dada uma partição de `synthetic_v1`, quando gerar, então saem PNG e
      SVG em `results/figures/`.
- [x] Dado um grafo com mais de 500 nós, então a figura é agregada e a
      legenda diz isso.
- [x] Rodar duas vezes produz a mesma figura (layout com seed fixa).
- [x] As cores distinguem as comunidades também em escala de cinza — o
      artigo pode ser impresso em preto e branco.
- [x] `docs/artigo/indice-figuras.md` é regenerado e inclui as novas.

## Testes exigidos

- **Unitários:** os dois arquivos são escritos; `community_sizes` sobre
  `tiny_v1` bate com valores à mão.
- Sem teste de aparência.

## Arquivos criados ou alterados

- `src/edugraph/community/report.py` — `figure_communities`,
  `figure_size_distribution`, `figure_q_vs_time` e `sizes_table`.
- `src/edugraph/community/cli.py` — `cmd_figures` (`edugraph community
  figures`), e `--figures` em `community compare`.
- `tests/community/test_figuras.py` (novo).
- `results/figures/` e `docs/artigo/indice-figuras.md` (regenerado).

## O que foi gerado (20/09/2026)

Em `results/figures/` (**não versionado desde 31/10/2026**: a pasta está no
`.gitignore` e as figuras saem sob demanda) e no índice regenerado:

| figura | arquivo | o que mostra |
|---|---|---|
| 4 | `fig4-comunidades-synthetic_v1-louvain__student_simple` | as três áreas plantadas, Q = 0,4666 |
| 4 | `fig4-comunidades-synthetic_v1-girvan_newman__student_simple` | as mesmas três, por outro caminho, Q = 0,4174 |
| 5 | `fig5-tamanhos-synthetic_v1` | um painel por algoritmo, tamanhos em ordem |
| 6 | `fig6-q-tempo-synthetic_v1` | Louvain acima e à esquerda; Girvan-Newman 399× à direita |

Ter as duas versões da figura 4 lado a lado é o argumento visual de que
o achado é da estrutura, não do algoritmo.

## Escolhas registradas

- **Paleta `cividis`**, amostrada em k pontos: desenhada para daltonismo
  e com luminância monotônica, o que garante cinzas distintos na
  impressão em preto e branco. A **forma do marcador** alterna junto, de
  modo que cor e forma digam a mesma coisa duas vezes.
- **Agregação acima de 500 nós**: uma bolha por comunidade, área
  proporcional ao tamanho, espessura da aresta proporcional ao peso
  entre comunidades. A legenda declara que a figura é agregada.
- **Arestas em `LineCollection`**, não uma chamada por aresta: o SVG de
  1.971 arestas cai de 480 kB para 372 kB. Rasterizar a camada foi
  testado e descartado — a 300 dpi o PNG embutido ficou maior que os
  vetores.
- **Partição sem tempo medido não entra na figura 6.** As partições de
  referência das fixtures gravam `runtime_s = 0`; colocá-las em 1e-6 no
  eixo logarítmico faria a figura afirmar que rodaram num microssegundo.
  Quantas ficaram de fora está na legenda.

## Impacto no artigo

**Duas figuras do capítulo 3**: grafo com comunidades e distribuição de
tamanhos.
