# [C-05] Front-end: grafo interativo com cor por comunidade

**Frente:** C
**Status:** concluída (25/09/2026), com o acabamento visual

## Objetivo

Entregar a visualização interativa: grafo com cor por comunidade, tamanho
por centralidade e filtros por projeção.

## Contexto

**Cumpre:** a visualização.
**Consome:** a API (C-04).

React + Vite + Cytoscape.js (decisão **D3**, ADR-0005). O grupo escolheu
esta stack em vez da página estática recomendada no plano porque a defesa
é uma apresentação, e transições controladas melhoram a legibilidade do
que está sendo mostrado na banca.

**Requisito de máquina:** Node.js `^20.19.0 || ^22.13.0 || >=24` (faixa exigida
pelo ESLint 10, adicionado pelo branch `c/pendencias-frente-c`).

## Dependências

- C-04, para as rotas de dados.
- **Neutralizada por:** o esqueleto do dia 0 já conecta em `/health` e
  `/datasets`, monta os seletores e trata o 501 da rota de projeção com
  um estado explícito ("aguardando C-04"). Dá para adiantar layout,
  estilo e interações com dados de exemplo.

## Escopo

### Incluído

- Cor por comunidade, com **escala qualitativa acessível** — precisa
  distinguir também em escala de cinza, porque as capturas podem ser
  impressas.
- Tamanho do nó por centralidade, com seletor de métrica.
- Seletor de partição (`communities/` disponíveis no dataset).
- Painel do nó selecionado: vizinhos, comunidade, scores das três
  métricas.
- Transição entre projeções preservando a posição dos nós comuns.
- Aviso quando o grafo passa de `MAX_EDGES_CONFORTAVEL` (3.000).

### Fora de escopo

- Edição de dados: a API é somente leitura.
- Exportação de figura pelo front — as figuras do artigo saem de
  `reporting/figures.py`, que garante estilo e resolução consistentes.
  Capturas de tela da interface são material **complementar**, não
  substituto.

## Critérios de aceite

- [x] Dado `synthetic_v1`, quando abrir, então o grafo aparece com os
      nós coloridos pela partição escolhida.
- [x] Dado um seletor de métrica, quando trocar, então o tamanho dos nós
      muda com transição, sem recarregar a página.
- [x] Dado um nó clicado, então o painel mostra comunidade, grau,
      intermediação e autovetor daquele nó.
- [x] Dado um grafo acima do limite, então o aviso aparece e a interface
      continua utilizável.
- [x] `npm run build` gera `src/edugraph/api/static/` e
      `python -m edugraph api serve` passa a servir a interface em `/`.
- [x] `npm run typecheck` passa — o front é tipado contra os schemas da
      API.
- [x] As cores distinguem comunidades em escala de cinza.

## Testes exigidos

- **Manual, documentado:** roteiro de verificação em `frontend/README.md`
  (abrir, trocar dataset, trocar projeção, clicar num nó).
- **Automatizado:** `npm run typecheck` na CI do front, se o grupo
  decidir criá-la. Teste de interface com navegador **não paga** o custo
  num TCC de três pessoas — registrar essa decisão é melhor do que
  fingir que ela não foi tomada.

## Arquivos criados ou alterados

- `frontend/src/components/GraphView.tsx` — apresentação do grafo, layout e zoom.
- `frontend/src/App.tsx` — seletores de partição e métrica.
- `frontend/src/components/NodePanel.tsx` (novo).
- `frontend/README.md` — roteiro de verificação.

Acrescentados durante a implementação:

- `frontend/src/palette.ts` — cores de Okabe & Ito, formas e leitura das
  cores do tema.
- `frontend/src/components/CommunityLegend.tsx`, `StatsBar.tsx`,
  `ErrorBoundary.tsx` (novos) — legenda, faixa de números e proteção do
  grafo.
- `frontend/src/api.ts`, `types.ts` — `availableMetrics` e o bloco
  `truncation` da API.
- `frontend/src/styles.css` — painel, legenda e acabamento; tokens dos temas
  claro e escuro, layout em grade (cabeçalho, lateral, palco, inspetor,
  rodapé) e as regras de `prefers-reduced-motion`.
- `frontend/src/components/Seletor.tsx` (novo) — seletor próprio no padrão
  WAI-ARIA *select-only combobox*, no lugar do menu nativo do `<select>`
  (que destoa do tema). Mantém um `<select>` nativo oculto e sincronizado,
  usado por `scripts/capture.mjs`; reconfirmar a opção já escolhida não
  chama `onChange` (como no `<select>`); o painel é renderizado no `<body>`
  com posição fixa e abre para cima quando não cabe.
- **REBRAND-02 · Direção A, editorial científico (20/10/2026).**
  `styles.css` reescrito a partir do protótipo escolhido pelo usuário:
  papel claro padrão `#FBFAF7`, grafite quente `#161512` no escuro,
  filetes, métodos à esquerda, Figura 1 ao centro e detalhe do nó à direita.
  Em 390 px, figura e painel precedem os controles; status da API visível.
- `frontend/public/fonts/` — subsets latinos dos WOFF2 oficiais Source Serif 4, Source Sans 3 e
  Source Code Pro, com licenças OFL e registro dos URLs/commits da Adobe em
  `README.md`. Fontes embutidas aprovadas pelo usuário, sem dependência npm.
- `frontend/src/components/NodePanel.tsx`, `StatsBar.tsx` — nome e números em
  serifa, métricas com pontos de posição e texto "3º de 7", vizinhos com
  barras finas; faixa numérica no topo da figura, sem ícones ou medidor do Q.
- `GraphView.tsx` — nós chapados na paleta original, contorno contrastante,
  anel de seleção na própria forma e arestas neutras sólidas por peso.
  Vidro, gradientes e SVG de reflexo removidos. Estilo de zoom quantizado,
  modo fixo grande, layout e cleanup preservados; nenhuma alteração em
  `palette.ts`, `api.ts` ou `types.ts`.
- `frontend/src/App.tsx` — legenda "Figura 1" sob o grafo, rádio 2×2 com
  explicação, notação matemática de Q e rodapé em texto. Estado, efeitos,
  requisições, números e callbacks preservados. `GraphViewHandle` mantém
  aproximar, afastar e centralizar e os atalhos de teclado.
- `frontend/index.html` — título curto e script de tema antes da primeira
  pintura, usando escolha salva ou claro padrão; `frontend/README.md`
  descreve a direção A, as fontes e a verificação. As capturas da figura 9
  devem ser refeitas após a integração; as cenas OULAD dependem dos dados.

- REBRAND-02, acabamento: bordas de controles com contraste mínimo 3:1 nos dois
  temas, raízes da API compactas no celular e DOM na ordem figura → métodos;
  grid desktop preservado. Fontes reduzidas em 42,3%, com português e licenças
  preservados; regeneração documentada em `frontend/public/fonts/README.md`.

## Impacto no artigo

**Capturas de tela do capítulo 3.** A escolha da stack vale uma frase na
seção de ferramentas — visualização é meio, não resultado.

## Como ficou (25/09/2026)

- **Cores em escala de cinza.** A paleta de Okabe & Ito é acessível para
  daltonismo, mas não separa todas as cores em cinza. Cada comunidade
  ganhou também uma **forma** (círculo, triângulo, quadrado…), e é a
  forma que garante o critério — conferido com `grayscale(1)` sobre
  `synthetic_v1`.
- **O Cytoscape não entende `var(--x)`.** O esqueleto passava as cores do
  tema como variáveis CSS, que o canvas ignora; agora elas são lidas do
  CSS no momento de montar o estilo (`themeColor` em `palette.ts`).
- **Partição à parte da projeção.** A projeção (cara) vem com as
  centralidades embutidas; a partição vem por `/communities/…`. Trocar a
  cor não redesenha o grafo.
- **Só as métricas que existem.** Antes de pedir o grafo, o front
  consulta cada métrica com `?top=1`; pedir as três com uma faltando
  daria 404 e perderia as outras.
- **Grafo grande.** O corte por peso global deixava 1.677 dos 1.870
  alunos do AVA soltos; a API passou a cortar pelo esqueleto (ver C-04).
- **Teste de interface.** Não automatizado, como a spec previa: roteiro
  manual em `frontend/README.md`, e `npm run typecheck`.
- **Capturas do capítulo 3 (26/09/2026).** `npm run capture`
  (`frontend/scripts/capture.mjs`) gera as quatro capturas da figura 9 em
  `results/figures/ui-*.png`. Fazê-las mostrou que os números de matrícula
  poluíam a rede de 98 alunos; desde então, rótulo de aluno só aparece em
  grafo de até 40 nós, sob o mouse, no nó selecionado e numa vizinhança de
  até 15 nós.
