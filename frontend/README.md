# `frontend/` — visualização interativa  `[C]`

React + Vite + Cytoscape.js (decisão **D3**, registrada na ADR-0005).
Consome a API somente leitura do FastAPI e é compilado para
`src/edugraph/api/static/`, de onde o próprio FastAPI o serve em `/`.

## Requisitos

**Node.js `^20.19.0 || ^22.13.0 || >=24`.** A faixa vem do ESLint 10, que o
branch `c/pendencias-frente-c` adiciona e declara em `engines` no
`package.json`; o Vite 5 sozinho roda em versões mais antigas, mas o projeto
passa a exigir esta faixa. Confira com `node --version`; se estiver fora dela,
instale o LTS atual.

## Comandos

```bash
cd frontend
npm install

npm run dev        # servidor de desenvolvimento em :5173, com proxy para :8000
npm run build      # compila para ../src/edugraph/api/static/
npm run typecheck  # tsc sem emitir
npm run lint       # eslint, sem avisos
npm test           # cliente da API e lógica da animação
```

Em desenvolvimento, suba os dois:

```bash
python -m edugraph api serve --root data/fixtures   # terminal 1
npm run dev                                          # terminal 2
```

O Vite encaminha `/health`, `/datasets` e `/openapi.json` para a API, de
modo que o front usa caminhos relativos nos dois modos e não precisa
saber onde está rodando.

## Laboratório ao vivo e leitura dos resultados (ADR-0013)

A aba **Laboratório ao vivo** chama `POST /lab/run`, que monta a rede na
hora e devolve o grafo **com o rastro do algoritmo**; a tela anima o que
aconteceu. A lógica da animação é pura e testada
(`src/lab/frames.ts`, `tests/frames.test.mjs`); o canvas só liga e
desliga classes (`components/LabCanvas.tsx`).

| Etapa | O que aparece | De onde vem |
|---|---|---|
| 1 · Matrículas | alunos à esquerda, disciplinas à direita, ligações surgindo | `bipartite` |
| 2 · Projeção | disciplinas somem; alunos se ligam por disciplinas em comum | `projection` |
| 3 · Algoritmo | Louvain: cada nó escolhe um grupo; Girvan–Newman: ligações-ponte somem em vermelho; Q ao vivo | `louvain.moves` / `girvan_newman.removed` |
| 4 · Resultado | grupos com nome e contorno, papéis, **perfis dos alunos (risco de evasão, talentos)**, revelações | `insight`, `insight.signals`, `reveal` |

**A rede só roda ao apertar ▶** (decisão do grupo): abrir a tela não
chama o servidor, e mudar um controle depois de montar apenas mostra
"Você mudou a configuração" até o próximo ▶, porque o visitante costuma
mexer em mais de um antes de querer rodar de novo
(`src/lab/pedido.ts`: `acaoDoTocar`).

Controles: espaço (tocar/pausar, ou montar), ← → (quadro a quadro),
Home/End, `+` `-` `0` (zoom), **F** (apresentação).
`prefers-reduced-motion` pula direto para o resultado.

**Clicar num nó** (`components/selecao.ts`, no laboratório e no explorador):
o nó cresce e ganha um halo, as ligações dele ficam grossas e na cor de
destaque (mais grossas quanto maior o peso), os vizinhos ganham contorno e
só os 12 de ligação mais forte mostram o nome; o resto esmaece e a câmera
enquadra o nó com os vizinhos. Soltar a seleção volta ao grafo inteiro.

### Tour de boas-vindas

`src/tour/`: `Tour.tsx` escurece a tela, acende o alvo (`data-tour="..."`)
e explica num balão; no celular vira uma folha no pé da tela. Os textos e
alvos estão todos em `passos.ts`; a lógica pura (visto/não visto, passos
com alvo, posição do balão), em `estado.ts`, testada em
`tests/tour.test.mjs`.

| Tour | Quando abre | Passos |
|---|---|---|
| `lab` | na primeira visita ao laboratório | boas-vindas, abas, turma, rede, algoritmo, etapas, grafo, narração, ▶ |
| `resultado` | convite no painel do **primeiro** resultado; depois, pelo botão *Entender o resultado* | resumo, grupos, perfis, revelar |
| `explorador` | na primeira visita ao explorador | boas-vindas, dados, projeção, comunidades, leitura, grafo |

O "já visto" fica no `localStorage` (`edugraph.tour.v1.<nome>`); sem ele
(janela privada) o tour só aparece de novo. `?tour` força o do
laboratório; `?semtour` desliga todos — `npm run capture` o usa, para as
capturas da figura 9 saírem sem o tour por cima.

No explorador, a **Leitura** (`/datasets/{d}/communities/{id}/insight`)
dá nome às comunidades e papel aos nós; passar o mouse na legenda destaca
o grupo, e *Revelar o desfecho* cruza o grupo com `outcomes.csv`
(`/outcomes`) — o grafo nunca o viu (ADR-0008).

### Roteiro de apresentação (≈ 8 minutos)

1. **Laboratório, turma padrão, Louvain.** Abra com `?tour` se quiser
   mostrar o tour; aperte ▶ e deixe tocar: matrículas → projeção →
   grupos nascendo, com o Q subindo. Aponte as três cores.
2. **Resultado.** Leia os nomes ("o algoritmo não sabia das áreas").
   Marque *As áreas que o gerador plantou*: "acertou X% dos alunos".
3. **Girvan–Newman**, mesma turma. Compare tempo e Q na tabela "mesma
   turma, os dois algoritmos".
4. **Mistura entre áreas** a 50%, e *Sortear nova turma*: mostre que os
   grupos ficam difíceis de achar e que o Girvan–Newman se perde primeiro.
5. **Fonte:** `oulad_vle_bbb_2013j`. Q ≈ 0: "o comportamento real é
   parecido; o método diz isso com honestidade". Use *Manter só as 30%
   mais fortes*.
6. **Explorar resultados.** O AVA inteiro, *Revelar o desfecho*: o grupo
   "Pouco engajados" concentra 72% de reprovados e desistentes.
7. **Perfis dos alunos.** Em qualquer resultado de alunos: *Quem merece
   atenção* e *Possíveis talentos*, cada um com o porquê. Clique num
   perfil para ver no grafo e em *Revelar o desfecho* para conferir: no
   AVA, 92% dos de risco alto reprovaram ou desistiram (42% da turma).

## O que a interface faz (spec C-05)

- **Cor por comunidade**, com a paleta de Okabe & Ito (acessível para
  daltonismo) **e uma forma por comunidade** — em escala de cinza, é a
  forma que separa os grupos (`src/palette.ts`). A maior comunidade fica
  sempre com a primeira cor, então o mesmo grafo sai com as mesmas cores.
- **Tamanho por centralidade** (grau, intermediação ou autovetor). Trocar
  a métrica anima o tamanho dos nós sem recarregar nem refazer o layout.
- **Seletor de partição**, com Q, número de comunidades e legenda.
  Trocar a partição só recolore: o grafo não é redesenhado.
- **Painel do nó**: comunidade, as três métricas com a posição no ranking
  e os vizinhos do mais forte ao mais fraco — clicar num vizinho o
  seleciona. A vizinhança do nó selecionado fica em destaque no grafo.
- **Transição entre projeções**: os nós em comum partem da posição em
  que estavam.
- **Rótulos**: disciplinas sempre com nome, quando o zoom deixa ler; alunos
  (números de matrícula) só em grafos de até 40 nós. Acima disso, o nome
  aparece sob o mouse, no nó selecionado e nos vizinhos dele quando são até
  15 — com mais, a lista fica no painel.
- **Grafos grandes**: a API corta a resposta em 5.000 arestas por padrão
  pelo **esqueleto** (as k ligações mais fortes de cada nó, com o maior
  k que cabe), e a interface diz que cortou. Acima de
  `MAX_EDGES_CONFORTAVEL` (3.000) o desenho é simplificado e há aviso.

Figuras do artigo **não** saem daqui: saem de `reporting/figures.py`.
As capturas da interface são material complementar do capítulo 3.

## Aparência, tema e acessibilidade

**Direção A · Editorial científico** (REBRAND-02, 20/10/2026): implementação
do protótipo `TCC-design-direcoes/direcao-a-editorial-cientifico.html`
escolhido pelo usuário. A tela funciona como uma página de periódico:
coluna de métodos, figura numerada e nota lateral do nó, separadas por
filetes. O título curto da aplicação e os três autores foram preservados.

- **Claro padrão:** papel `#FBFAF7`, tinta `#1A1915`, folha branca.
  **Escuro:** grafite quente `#161512`, folha `#1C1B18`, tinta `#ECE8DF`.
  O script inline define o tema antes da primeira pintura, usando a escolha
  salva em `localStorage` (`edugraph-tema`) ou o claro padrão. O botão
  continua alternando os temas sem recriar o grafo nem perder a seleção.
- **Fontes locais, aprovadas sob SIL OFL 1.1:** Source Serif 4 (normal e
  itálico variáveis, com tamanho óptico) nos títulos, números e legenda;
  Source Sans 3 variável na interface e nos rótulos do canvas; Source Code
  Pro Regular nos ids. Obtidas dos repositórios oficiais da Adobe:
  [source-serif](https://github.com/adobe-fonts/source-serif),
  [source-sans](https://github.com/adobe-fonts/source-sans) e
  [source-code-pro](https://github.com/adobe-fonts/source-code-pro).
  Os WOFF2 reduzidos, as três licenças OFL e os URLs imutáveis com os commits
  de origem estão em [public/fonts/README.md](public/fonts/README.md).
  O subset latino com português soma 588.068 bytes (42,3% menor), com
  `unicode-range` e eixos variáveis preservados. O script de regeneração usa
  fonttools/Brotli em venv temporário, sem dependências novas no projeto.
  Não há CDN nem requisição externa de fonte em runtime.
- **Métodos em quatro passos:** Dados, Projeção, Comunidades e Centralidade.
  Ids e callbacks continuam iguais; opções de tamanho têm aparência de
  rádios 2×2 e explicação da métrica ativa. A modularidade usa notação
  matemática (*Q* = 0,3715); a legenda das comunidades usa linhas de tabela.
- **Figura 1:** faixa de números no topo do palco; legenda editorial sob
  o grafo ensina forma/cor, tamanho e peso. Nós chapados e rótulos com halo;
  contorno de tinta no claro, recorte de papel no escuro e seleção por
  anel na própria forma. Arestas neutras, sólidas, com largura de 0,75 a
  4,75 px conforme o peso em grafos pequenos. A direção A original usa
  linhas sólidas; não foi adotado o tracejado da direção C. Nenhum vidro,
  gradiente, reflexo SVG ou acento verde da moldura anterior permanece.
  Okabe & Ito e as formas de `palette.ts` continuam intactos.
- **Painel do nó:** nome em serifa, comunidade, scores com quatro casas,
  pontos de posição e texto exato como "3º de 7". Até 15 pontos por métrica;
  em redes maiores as marcas são proporcionais, com a posição exata em
  texto e nome acessível. Vizinhos mantêm ordem por peso, limite de 12,
  clique para selecionar e aviso de truncamento, com barras finas neutras.
- **Seletor:** mantém ARIA, teclado/type-ahead, portal com abertura para cima,
  reconfirmação sem `onChange` e `<select>` nativo oculto do `capture.mjs`.
  O menu usa o mesmo papel e os mesmos filetes dos campos.
- **Responsividade:** três colunas em 1440; métodos e inspetor mais estreitos
  em 1024; em 390, cabeçalho, figura, painel, controles e rodapé nessa ordem.
  Status e raízes da API ficam visíveis também no celular: raízes em 7ch,
  com reticências e caminho completo no `title`. O DOM segue figura/painel
  antes dos métodos, como no celular; o grid mantém métodos | figura | nota
  no desktop. Tab segue a ordem do DOM nos dois tamanhos.
  Zoom permanece por ref (`aproximar`, `afastar`, `centralizar`) e atalhos
  `+`, `−`, `0`; o desenho grande mantém estilo fixo, zoom quantizado e
  cleanup. A câmera inicial e Centralizar usam a mesma folga: 36 px no
  desktop e 28 px quando o canvas tem menos de 600 px, com zoom de
  enquadramento até 3,6 e rótulos incluídos na caixa. Ao redimensionar uma
  figura já aberta, Centralizar refaz o fit. No celular, os botões ocupam
  uma linha própria abaixo do canvas. O menu tem largura mínima de cerca
  de 20rem limitada à viewport; ids ficam em uma linha com reticências e
  texto completo no `title`, enquanto rótulos podem quebrar entre palavras.
- **Estados e acessibilidade:** vazio com filete tracejado, carregamento com
  fio de progresso e erro textual legível; foco visível azul, contraste de
  tinta e papel e cor/forma redundantes. `MotionConfig reducedMotion="user"`
  e CSS de `prefers-reduced-motion` preservados; entradas por opacidade,
  sem deslocamento decorativo. Rodapé em texto com link do repositório.

As capturas da figura 9 anteriores ao REBRAND-02 estão desatualizadas.
Refazê-las com `npm run capture` e regenerar o índice de figuras depois
da integração; as telas OULAD exigem seus artefatos reais.

## Roteiro de verificação manual

Teste de interface com navegador não paga o custo num TCC de três
pessoas (decisão registrada na spec C-05); este roteiro substitui.
Rode a API com o build (`npm run build` antes) e abra
`http://127.0.0.1:8000`:

```bash
python -m edugraph api serve --root data/processed --root data/fixtures
```

1. **Abrir** e escolher o dataset `synthetic_v1` (com `data/processed` na
   raiz, a tela abre no primeiro dataset do OULAD que tiver partição). Ele aparece com a projeção colorida
   pela partição Louvain e a legenda com três comunidades.
2. **Trocar a projeção** para `student_simple`. O grafo é redesenhado;
   a partição acompanha (`louvain__student_simple`, Q ≈ 0,4666).
3. **Trocar a métrica** de Grau para Intermediação. Os nós mudam de
   tamanho com transição, sem recarregar; os que ligam as comunidades
   crescem.
4. **Clicar num nó.** O painel mostra comunidade, grau, intermediação e
   autovetor, com a posição de cada um; clicar num vizinho troca a
   seleção. Clicar no fundo limpa.
5. **Trocar a partição** para "sem cor por comunidade" e voltar. Só as
   cores mudam; as posições ficam.
6. **Grafo grande.** Com o OULAD em `data/processed`, abrir
   `oulad_vle_bbb_2013j` / `student_simple` (1,75 M arestas). A faixa de
   aviso diz que é o esqueleto (k = 2, 3.732 arestas) e que todos os
   1.870 nós estão presentes; a interface continua respondendo.
7. **Escala de cinza.** No console do navegador,
   `document.documentElement.style.filter = "grayscale(1)"`: as
   comunidades continuam distinguíveis pela forma.
8. `npm run typecheck` passa.

## Capturas para o artigo (figura 9)

`npm run capture` gera as capturas da interface em `results/figures/`
(pasta ignorada pelo git desde 31/10/2026: as capturas não são versionadas)
(`ui-*.png`, 3200 × 2000, com a legenda em `ui-*.caption.txt`). O script
(`scripts/capture.mjs`) abre a interface num Edge ou Chrome headless, monta
cada cena pelos próprios controles da tela e fotografa. Não instala nada: usa
o WebSocket nativo do Node 22+.

```bash
python -m edugraph api serve --root data/processed --root data/fixtures   # terminal 1
npm run capture                                                           # terminal 2
python -m edugraph figures --index                                        # atualiza o índice
```

Para apontar outro navegador Chromium (por exemplo o Brave, se não houver
Edge nem Chrome), use `EDUGRAPH_BROWSER`; para fotografar o servidor de
desenvolvimento em vez do build servido pela API, `--url http://127.0.0.1:5173`.
Para não sobrescrever `results/figures`, passe `--out` com outro diretório.

As cenas seguem o roteiro acima: comunidades em `synthetic_v1`, a mesma rede
por intermediação com um nó selecionado, as disciplinas críticas do OULAD e
os alunos do AVA pelo esqueleto. Sem o OULAD em `data/processed`, as duas
últimas são puladas. Refaça as capturas sempre que a interface mudar. Elas
não são reproduzíveis byte a byte (o layout anima), ao contrário das figuras
de `reporting/figures.py`.

## Limite de escala

`MAX_EDGES_CONFORTAVEL` em `GraphView.tsx` é 3.000. Acima disso o
navegador engasga e a figura deixa de comunicar. O corte é
responsabilidade da API (spec C-04, parâmetros `max_edges` e `cut`); o
componente confia no que recebe, mas avisa quando o número passa.


## Contraste dos controles (REBRAND-02)

Bordas indicativas usam `--rule-control`; filetes decorativos mantêm `--rule-2`.
Contrastes calculados pela luminância relativa sRGB (WCAG):

| Tema / borda | Contra papel | Contra folha |
| --- | ---: | ---: |
| Claro `#807A6C` | `#FBFAF7`: **4,091:1** | `#FFFFFF`: **4,270:1** |
| Escuro `#787266` | `#161512`: **3,823:1** | `#1C1B18`: **3,606:1** |

O token identifica gatilhos e menu do Seletor, rádios inativos, botão de tema
e bordas/divisórias do zoom. Todos superam 3:1 nos dois fundos do tema.
