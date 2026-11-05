# Entrega — o que está pronto e o que falta

Revisão de entrega feita em **30/10/2026** (Frente A), simulando o
caminho de quem avalia: clone limpo, instalação, testes, pipeline
sintético, API e a receita real do OULAD. Os números abaixo foram medidos
nesta revisão, num Windows 11 com Python 3.14, sem Node instalado.

## Resumo

- **O núcleo está pronto e é reproduzível.** As 23 specs estão fechadas.
  Num clone limpo, `pip install -e ".[dev]"` funciona, as fixtures validam,
  `pytest` passa inteiro (359 testes, 1 pulado) e o pipeline sintético roda
  de ponta a ponta em ~70 s com a validação de contrato verde.
- **Os resultados do artigo se reproduzem do zero.** Com o OULAD baixado
  nesta revisão, as duas configurações que alimentam as tabelas rodaram
  em ~14 min, `validate` passou, e as tabelas 8 e 8b saíram idênticas às
  versionadas (a 6 com o mesmo ranking; diferenças só no 16º dígito).
- **A arquitetura se sustenta.** As três regras não negociáveis (sem ML,
  rótulos fora do grafo, frentes sem import cruzado) são verificadas por
  teste, e passam. Há um defeito conhecido no runner (T-OBS-02) e nenhum
  defeito novo de arquitetura.
- **O que falta é de entrega, não de método:** a interface não abre sem
  Node, as capturas da interface estão desatualizadas e pesam 60% do
  repositório, duas tabelas versionadas estão defasadas do código, a
  configuração da coorte leva horas, e algumas decisões precisam dos três
  (seções 5 e 6, T-OBS-04).

## 1. O que foi verificado

| Passo | Comando | Resultado | Tempo |
|---|---|---|---:|
| Clone | `git clone …` | **falha em pasta funda no Windows** (`Filename too long`); ok em caminho curto | — |
| Instalação | `pip install -e ".[dev]"` | ok, versões fixadas resolvem no Python 3.14 | ~50 s |
| Fixtures | `python -m edugraph validate --root data/fixtures` | 3 datasets ok (22 + 22 + 6 artefatos) | 1 s |
| Testes da CI | `pytest -m "not slow"` | 358 passam, 1 pulado, 1 desmarcado | 17 s |
| Testes completos | `pytest` | 359 passam, 1 pulado | 59 s |
| Qualidade | `ruff check`, `ruff format --check`, `mypy src/edugraph/contracts` | tudo limpo | — |
| Pipeline sintético | `run configs/synthetic_v1.toml --out <pasta>` + `validate` | 26 artefatos, validação ok | 71 s |
| API | `api serve --root data/fixtures` | `/health`, `/datasets`, `/docs` e projeção com partição: 200 | — |
| Interface | `GET /` sem o front compilado | **JSON pedindo `npm run build`** | — |
| OULAD | receita da Frente A (download → etl → três `run`) | ver seção 4 | — |

O teste pulado depende de `oulad_module_presentation`, que só existe
depois do download do OULAD: é o comportamento previsto.

**Uma instabilidade observada:** na primeira execução de `pytest`, logo
depois de criar a venv, `test_custo_relativo_do_girvan_newman_esta_medido`
estourou o orçamento de 600 s. Nas três execuções seguintes levou 28 a
36 s e passou. Não se reproduziu; fica o registro caso volte a acontecer
numa máquina mais lenta ou carregada.

## 2. Como o professor provavelmente vai testar

O caminho mais provável é o do README: clonar, instalar, rodar os testes,
subir a API e abrir a interface. Os tropeços que ele vai encontrar, em
ordem:

1. **Caminho longo no Windows.** O caminho mais longo do repositório tem
   93 caracteres. Clonar ou extrair o ZIP do GitHub em
   `C:\Users\<nome>\Downloads\TCC.bipartite-network-analysis-main\…` passa
   perto do limite de 260; numa pasta mais funda, a árvore fica incompleta
   e os testes de contrato falham com `FileNotFoundError`. **Corrigido no
   README** (aviso e `core.longpaths`).
2. **`pytest` puro.** Leva ~1 min por causa do Girvan-Newman completo. O
   README agora mostra as duas formas, com o tempo de cada uma.
3. **Interface.** Sem Node 20+, `http://127.0.0.1:8000/` mostra um JSON.
   É o ponto mais visível da apresentação e hoje depende de o professor
   instalar Node e rodar `npm install` e `npm run build`. Ver seção 5.
4. **OULAD.** Os dados reais exigem download (~45 MB, 19 s) e a rodada das
   três configurações. Sem isso, a API e a interface mostram só os
   datasets sintéticos. Ver seção 4 para os tempos.

**Roteiro sugerido para a apresentação** (cabe em 10 minutos e não
depende de internet além do clone):

```bash
git clone https://github.com/luctmc/TCC.bipartite-network-analysis C:\tcc
cd C:\tcc
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m edugraph validate --root data/fixtures
pytest -m "not slow"
python -m edugraph run configs/synthetic_v1.toml --out saida-teste
python -m edugraph api serve --root saida-teste --root data/fixtures
```

## 3. Revisão da arquitetura

**O que está bom e vale defender na banca:**

- Fronteira entre frentes pelo disco, com contratos congelados e
  validadores. `tests/contract/` garante sem ML, rótulos isolados em
  `evaluate.py` e nenhum import cruzado — e passa.
- Determinismo: fixtures regeneram byte a byte (job próprio na CI).
- Algoritmos centrais implementados à mão (projeções A-04, modularidade
  B-03, autovetor C-02) e conferidos contra valores derivados no papel.
- API somente leitura (ADR-0004): nada de cálculo pesado por requisição.

**O que está frágil:**

| Ponto | Onde | Efeito | Registro |
|---|---|---|---|
| Runner mistura rodadas quando uma raiz antiga tem o mesmo dataset da saída | `src/edugraph/__main__.py:128`, `:141` | B e C leem a rodada antiga; `validate` acusa | T-OBS-02 |
| ~~API relê o CSV inteiro a cada requisição~~ **corrigido** (seção 8) | `src/edugraph/api/projection_cache.py` | era ~10 s por `GET` na maior projeção (1,75 M arestas); agora 0 s a partir do 2º pedido | seção 8 |
| Comandos da Frente B gravam em `data/processed` mesmo lendo das fixtures | `src/edugraph/community/cli.py` | quem segue o README cria pastas sem perceber | B-OBS-04 |
| Girvan-Newman da coorte com amostra de 400 e orçamento de 1 h | `configs/oulad_cohort_bbb_2013j.toml:70-75` | a rodada passa de 2 h, com risco de sair sem corte útil | seção 4, T-OBS-01 |

Nenhum deles invalida resultado já publicado nas tabelas; o primeiro é o
único que pode produzir artefato inconsistente, e só com `--root` antigo
e `--out` diferente apontando para o mesmo dataset.

## 4. Rodada do OULAD

Receita de [`specs/frente-a/README.md`](specs/frente-a/README.md),
executada nesta revisão do zero:

| Etapa | Tempo |
|---|---:|
| `python scripts/download_oulad.py` (com SHA-256 conferido) | 19 s |
| `python -m edugraph data etl` | 7 s |
| `run configs/oulad_module_presentation.toml` (data → community → centrality) | 5 s |
| `run configs/oulad_vle_bbb_2013j.toml` — `data` | 43 s |
| idem — `community` (Louvain sobre 1,75 M arestas) | 62 s |
| idem — `centrality` (intermediação com 200 pivôs, ~5,5 min por projeção de aluno) | 11,5 min |
| `validate --root data/processed` | 26 s, ok |
| `run configs/oulad_cohort_bbb_2013j.toml` | **> 2 h estimadas; interrompida** |

**A coorte por avaliação é o problema.** O estágio `data` leva ~15 s e o
Louvain ~6 s, mas o Girvan-Newman roda numa amostra de 400 alunos com
orçamento de **3.600 s por projeção**, e há duas projeções de aluno.
Medido: nessa amostra (25.650 arestas), uma única intermediação de
arestas leva 1,75 s, então o orçamento comporta ~2.000 remoções — menos
de 8% das arestas. A rodada passa de 2 h e corre o risco de terminar em
`skipped` ou `timeout` com poucos cortes. A intermediação exata da Frente
C ali é barata (~2 min por projeção). Registrado em T-OBS-01: a Frente B
deveria reduzir `sample_nodes` (100 a 150) ou o orçamento antes de rodar.

**Reprodução das tabelas do artigo.** Regenerei numa pasta temporária as
tabelas 6, 7, 8 e 8b e comparei com `results/tables/`:

- tab8 (seis arquivos) e tab8b (grau, intermediação): **idênticas byte a
  byte**; tab8b do autovetor difere só no 16º dígito;
- tab6 e tab7: mesmo ranking e mesmos valores, mas o código atual grava
  quatro colunas a mais (`weight_mode`, `k`, `estimate`, `seed`), que as
  versionadas não têm, e a tabela de sensibilidade (`tab6-sensibilidade-*`)
  sai em 1 s e não está versionada. É a C-OBS-03: falta só regenerar e
  fazer o commit.

## 5. O que precisamos para chegar a 100%

### Interface interativa

O front (React + Vite + Cytoscape.js, C-05) está implementado e tem CI
própria. O que falta é **chegar à tela de quem avalia**:

1. **Entregar o front compilado.** Hoje `src/edugraph/api/static/` está no
   `.gitignore`, então o clone não traz a interface. Opções, da mais
   simples para a mais limpa:
   - commitar o build só no commit de entrega (tirar do `.gitignore`
     exige acordo dos três, e cada rebuild soma ao histórico);
   - publicar o build como anexo de uma *release* do GitHub, com instrução
     de extrair em `src/edugraph/api/static/`;
   - gerar o build na CI e publicá-lo como artefato.
   **Recomendação:** release do GitHub com o build e o `data/processed`
   das configurações do artigo, porque não muda o repositório e dá ao
   professor os dados reais sem rodar nada. Medido nesta revisão:
   `oulad_module_presentation` e `oulad_vle_bbb_2013j` ocupam 103 MB em
   disco e **26 MB num zip** — cabe folgado numa release (limite de 2 GB
   por arquivo), e a rodada que ele evita leva ~14 min. As réplicas nulas
   (`data null --replicas 5`) não foram geradas nesta revisão e entrariam
   à parte.
2. **Refazer as quatro capturas** (`npm run capture`) depois do redesign,
   já em JPEG (C-OBS-05 e C-OBS-13).
3. **Atualizar Vite e esbuild** (C-OBS-12): os avisos são das ferramentas
   de desenvolvimento, não do código servido, mas aparecem para quem roda
   `npm install`.

### Banco de dados / armazenamento melhorado

**Não recomendo trocar CSV por um banco (SQLite, Parquet, Postgres) a esta
altura.** O CSV com `meta.json` é o contrato congelado (ADR-0002): trocar
exige ADR, aprovação dos três, `SCHEMA_VERSION` novo, refazer as fixtures e
todos os leitores. E o problema medido não é o formato: é que a API relê e
reconstrói o grafo a cada requisição.

O que resolve, sem mudar contrato:

- **Cache em memória na API** — *feito, ver seção 8.* Guarda **uma**
  projeção (a última lida), com chave de data e tamanho do arquivo. A C-04
  tinha descartado o cache pelo custo de memória (~1 GB por projeção); com
  uma entrada só, o teto é o de uma projeção.
- Se ainda for preciso, um **esqueleto pré-calculado** (o `backbone` que a
  API já calcula) gravado pela CLI em `metrics/`, que é dicionário livre e
  não exige ADR.

Se o grupo quiser mesmo um banco para o artigo (por exemplo, "consultas
SQL sobre o resultado"), o caminho barato é um **exportador** à parte
(`edugraph export sqlite`) que lê os artefatos e grava um `.sqlite` —
sem tocar no contrato nem na API.

### Processamento mais rápido

Onde o tempo vai, medido:

| Etapa | Tempo | Observação |
|---|---:|---|
| Girvan-Newman em `synthetic_v1` (98 nós, 1.971 arestas) | 30–36 s | 2/3 do tempo até o melhor Q (k = 3, 20 s); o resto percorre o dendrograma até o fim |
| Louvain na mesma projeção | 0,01 s | ~3.000× mais rápido |
| `GET` da maior projeção na API | ~7 s | leitura do CSV (ver acima) |
| Centralidades de `oulad_vle_bbb_2013j` | 11,5 min | intermediação com 200 pivôs e Dijkstra (`weight_mode = "inverse"`) sobre 1,75 M arestas |
| Girvan-Newman na coorte `oulad_bbb_2013j` | > 2 h | orçamento de 3.600 s × 2 projeções de aluno (seção 4) |

- **Girvan-Newman ser lento é resultado, não defeito** (ADR-0006, B-04):
  é o que sustenta a comparação com o Louvain. Não vale acelerá-lo a ponto
  de apagar a diferença. Testei a otimização clássica de recalcular a
  intermediação só na componente afetada: **ficou mais lenta** (74 s
  contra 30 s), porque a projeção é densa e fica numa componente só até
  quase o fim. O único ganho barato é parar quando o Q cai muito abaixo do
  melhor já visto (~1/3 do tempo), e isso muda a semântica de "melhor Q do
  dendrograma" — só com acordo da Frente B e nota no artigo.
- **A configuração da coorte é o maior desperdício.** Reduzir
  `sample_nodes` ou `time_budget_s` em `oulad_cohort_bbb_2013j.toml` tira
  horas da rodada sem tocar em código (T-OBS-01, decisão da Frente B).
- **A intermediação do AVA** (11,5 min) já é amostrada; baixar `k` reduz o
  tempo na mesma proporção, mas muda os números das tabelas 8 e 8b. Não
  vale a pena a esta altura.
- **Para a demonstração**, o que acelera de verdade é não recalcular:
  entregar os artefatos já prontos (release, acima).

## 6. Limpeza do repositório

**Diagnóstico.** O repositório tem 14,6 MB no histórico do git e 15 MB
em `results/` na árvore. O peso não vem de teste: os testes escrevem só
em `tmp_path`, e `data/processed`, `data/raw`, `node_modules` e o build do
front já estão no `.gitignore`. O peso vem das **figuras do artigo**:

| O quê | Na árvore | No histórico |
|---|---:|---:|
| Capturas da interface `results/figures/ui-*.png` (3200×2000) | 9,1 MB | 8,8 MB |
| Demais PNG de `results/figures/` (300 dpi, com SVG equivalente) | 3,7 MB | 3,4 MB |
| Fontes do front (`frontend/public/fonts/`, duas versões) | 0,6 MB | 1,5 MB |
| Todo o resto (código, docs, fixtures, tabelas) | < 1 MB | < 1 MB |

**Decisão tomada (31/10/2026, a pedido do grupo): as figuras saem do
repositório.** O grupo vai mostrar os resultados na própria interface, e as
figuras do artigo não alteram nenhum resultado. `results/figures/` (42
arquivos, 14,9 MB) foi apagada da árvore e entrou no `.gitignore`, junto com
o índice gerado `docs/artigo/indice-figuras.md`. O código que as gera
(`python -m edugraph figures`, `community/centrality ... --figures`,
`npm run capture`) continua, e `results/tables/` (51 KB) fica versionada.
Com isso, as opções 1 e 3 abaixo ficam sem objeto (as capturas não serão
refeitas) e só resta a 2, o histórico do git.

**O que já foi feito nesta revisão:** README e documentação da Frente A
corrigidos (seção 7); `saida-teste/` no `.gitignore`, para que a rodada
sugerida ao professor não entre por engano num commit.

**O que precisa de decisão dos três** (T-OBS-04):

1. **Capturas em JPEG.** Ao refazê-las (C-OBS-05), JPEG qualidade 88 leva
   as quatro de 9,1 MB para 2,1 MB, medido sobre as atuais. Compressão PNG
   sem perdas só tira 4%.
2. **Apagar arquivo da árvore não diminui o clone.** O histórico continua
   com as versões antigas. Só diminui o ZIP do GitHub. Para o clone ficar
   leve, é preciso **reescrever o histórico**, uma vez, depois do último
   merge, com todos de acordo, porque exige *force push* em `main` e cada
   um precisa clonar de novo:

   ```bash
   pip install git-filter-repo
   git clone --mirror https://github.com/luctmc/TCC.bipartite-network-analysis tcc-mirror
   cd tcc-mirror
   git filter-repo --path-glob 'results/figures/ui-*.png' --invert-paths
   git push --force --mirror
   ```

   O comando apaga **todas** as versões de `ui-*.png`, inclusive a atual:
   rodar só depois que as capturas novas, em `.jpg`, estiverem em `main`.
   A proteção de `main` precisa ser desligada durante o *push* e religada
   em seguida. Estimativa: o histórico cai de 14,6 MB para ~6 MB; tirando
   também as PNG que têm SVG, para ~3 MB. Os hashes de todos os commits
   mudam, e as observações que citam hash ficam apontando para commits que
   não existem mais — registrar isso na própria decisão.
3. **Manter `results/tables/` e os SVG versionados.** São o que foi para o
   texto (e pesam 60 KB as tabelas); o professor precisa vê-los sem rodar
   o OULAD.

## 7. Observações abertas, por frente

| Id | Frente | Assunto | Bloqueia a entrega? |
|---|---|---|---|
| T-OBS-01 | todos | `oulad_bbb_2013j` sem comunidades e centralidades; a config leva > 2 h | não; ajustar a config ou deixar a coorte de fora |
| T-OBS-02 | todos | runner mistura rodadas com `--root` antigo | não; documentar como limitação ou corrigir |
| T-OBS-04 | todos | decisões de entrega desta revisão | **sim** |
| A-OBS-09 | A | revisar `weight_mode = "inverse"` na config do AVA | não |
| A-OBS-10 | A | bipartido por matrícula sem limiar (sugestão) | não |
| B-OBS-01..02 | B | `null0..2` e Q da amostra no README da Frente B | não (texto) |
| B-OBS-03 | B | z = +15,4 não se reproduz só com o repositório | **sim, se o número for para o artigo** |
| B-OBS-04 | B | comandos do README gravam em `data/processed` | não |
| C-OBS-01 | C | relatórios internos entram no repositório? | decisão |
| C-OBS-03 | C | tab6/tab7 defasadas e tabela de sensibilidade não versionada | **sim, se o texto a cita** — mas é regenerar (1 s) e commitar |
| C-OBS-05 | C | capturas anteriores ao redesign | **sim** (figura 9) |
| C-OBS-11 | C | textos históricos de `xfail` e handler 501 | não |
| C-OBS-12 | C | `npm audit`: Vite e esbuild | não |
| C-OBS-13 | C | capturas pesam 60% do repositório | junto com C-OBS-05 |

Fechadas nesta revisão: A-OBS-01 a A-OBS-08 (ver
[`observacoes/para-frente-a.md`](../observacoes/para-frente-a.md)).

## Ordem sugerida até a entrega

1. Decidir T-OBS-04 (front compilado, histórico, capturas) — reunião curta.
2. Frente C: refazer as capturas em JPEG e gerar o build do front.
3. Frente B: B-OBS-03 e a configuração da coorte (T-OBS-01); Frente C:
   C-OBS-03 — os números e tabelas que o texto cita e o repositório ainda
   não reproduz.
4. Rodar a receita do OULAD numa máquina (~14 min para as configurações do
   artigo; já rodada uma vez), empacotar `data/processed` e o
   build do front numa release.
5. Último merge; se decidido, reescrever o histórico; clonar de novo e
   repetir o roteiro da seção 2 do zero.

## 8. O que foi implementado depois desta revisão (30/10/2026, tarde)

A pedido do grupo ("deixar interativo, simples de visualizar", "montar as
projeções na hora"), a interface ganhou o **laboratório ao vivo** e a
leitura dos resultados em português. A decisão está na
[ADR-0013](adr/ADR-0013-laboratorio-ao-vivo.md); o uso, no
[README da raiz](../README.md) e em
[`frontend/README.md`](../frontend/README.md) (com um roteiro de 8
minutos).

| Pedido | O que ficou |
|---|---|
| Executar pela interface | `POST /lab/run`: turma de Computação gerada na hora (ou amostra de um dataset), Louvain **ou** Girvan–Newman de verdade, em 0,2–3 s |
| Ver como o grafo é montado | quatro etapas animadas (matrículas → projeção → algoritmo movimento a movimento → resultado), com Q ao vivo e controle de tempo |
| Ajustar o dataset para diminuir | nº de alunos, mistura entre áreas, projetar alunos ou disciplinas, ponderação, corte de ligações fracas (com sugestão "manter só as 30% mais fortes"), sortear nova turma |
| Comunidades com nome, não número | "Algoritmos · Estruturas de Dados", "Módulos BBB · GGG", "Pouco engajados" — por contagem, sem ML |
| Tipos de aluno | papéis de Guimerà e Amaral (referência, conector, ponte, periférico), com filtro |
| Resultado não técnico | frases-resumo, contornos nas comunidades, "revelar" as áreas plantadas e o desfecho dos alunos |
| Banco melhorado / mais rápido | cache de uma projeção: o grafo do AVA passou de ~10 s para 0 s a partir do 2º pedido; a leitura do AVA, de ~6 s disputando CPU para ~2 s |
| Apresentação | modo tela cheia (tecla **F**), letra maior, controle por teclado |
| Quem abre pela primeira vez | **tour de boas-vindas** (laboratório, resultado e explorador) e rede que **só roda ao apertar ▶**; mudar um controle espera o próximo ▶ |
| Análise útil, não só técnica | **risco de evasão** e **possíveis talentos** por aluno, cada um com o porquê em frase, filtro no grafo e conferência com o desfecho real (AUC 0,79 no AVA, 0,91 na coorte) — ver ADR-0013 |

**Verificado:** `pytest` completo (399 passam, 1 pulado), `ruff`, `mypy`,
`npm run typecheck`, `npm run lint`, `npm test` (17), `npm run build`, e as
telas conferidas num navegador (Edge headless) nos temas claro e escuro,
em 1600×1000 e em 390×844.

**Também feito:** `oulad_bbb_2013j` foi completado (Louvain e
centralidade, 85 s, `validate` ok) e deixou de aparecer vazio no
explorador, que agora abre num dataset completo.

**O que ainda falta para a entrega** (nada disso é código novo):

1. Refazer as capturas da figura 9 (`npm run capture`): a interface mudou
   duas vezes (redesign e laboratório). Já em JPEG — C-OBS-05 e C-OBS-13.
2. Decidir T-OBS-04: histórico do git, front compilado na release.
3. B-OBS-03 (z = +15,4 que o repositório não reproduz) e C-OBS-03
   (regenerar tab6/tab7 e a tabela de sensibilidade).
4. A configuração da coorte (`oulad_cohort_bbb_2013j.toml`) segue levando
   > 2 h por causa do Girvan–Newman (T-OBS-01).
5. Primeira leitura de um grafo grande a frio: o AVA leva ~10 s (5 s de
   leitura do CSV, 3 s do esqueleto de arestas). Depois, 0 s.

**Limites conhecidos do laboratório:** 75 alunos, 4.000 ligações (1.500 no
Girvan–Newman) e 60 s; o Louvain da tela é uma implementação própria,
conferida contra o `python-louvain` (Q a menos de 0,02, e a tela mostra os
dois); os papéis usam limiares adaptados a redes densas.

## 9. Comando único, OULAD à parte e hospedagem (04/11/2026)

Preparação da apresentação ao orientador
([`orientador/estudo-apresentacao-11-2026.md`](orientador/estudo-apresentacao-11-2026.md)).

### Um comando: `python scripts/iniciar.py`

Cria a `.venv`, instala o pacote, valida as fixtures, roda
`pytest -m "not slow"`, compila o front (se houver Node) e abre
http://127.0.0.1:8000/ no navegador. Cada passo já feito é pulado na
rodada seguinte (a instalação é refeita só se o `pyproject.toml` mudar).
Só biblioteca padrão, porque roda antes de o `edugraph` estar instalado.

| Situação | Tempo medido |
|---|---:|
| clone limpo, sem `.venv` e sem build do front (Windows 11, Python 3.14, Node 26) | **2 min 05 s** (418 testes passando, 1 pulado) |
| segunda vez, `--sem-testes` | ~2 s até o servidor responder |
| `--oulad <zip>` com os três datasets | +30 s (extração e `validate`) |

Opções: `--sem-testes`, `--oulad ZIP`, `--porta N`, `--sem-navegador`,
`--sem-servidor` (só as conferências; sai com 1 se algo falhou).

**O que ele não resolve:** sem Node, a interface continua sem build e `/`
mostra o JSON (decisão 2 da T-OBS-04). E num caminho fundo do Windows não
só o `git clone` falha: a criação da `.venv` também (`ensurepip` esbarra
no limite de 260 caracteres) — reproduzido nesta data, numa pasta
temporária de 130 caracteres.

### Entregar o OULAD separado

O sistema **já está preparado** para receber os dados à parte, sem
mudar código: as raízes padrão são `data/processed` + `data/fixtures`,
relativas à pasta de onde se roda o comando, e uma raiz ausente é só
ignorada (`tests/api/test_raiz_ausente.py`). O que pode dar errado é
**onde** o ZIP é extraído: uma pasta a mais por cima
(`data/processed/processed/oulad_vle_bbb_2013j/`) ou rodar a API de outra
pasta, e o dataset some da lista sem erro nenhum.

O `iniciar.py --oulad` tira esse risco: procura no ZIP toda pasta que
tenha `bipartite/nodes.csv`, qualquer que seja o nível, copia para
`data/processed/` (sem sobrescrever o que já existe), roda `validate` e
recusa com explicação o ZIP do OULAD **bruto**.

**Nós, para gerar o ZIP** (na máquina que tem `data/processed/`):

```powershell
Compress-Archive -Path data\processed\* -DestinationPath oulad-resultados.zip
```

Medido: 135 MB em disco viram **31,5 MB** (os três datasets:
`oulad_bbb_2013j`, `oulad_module_presentation`, `oulad_vle_bbb_2013j`).
As réplicas nulas (`*_null0..4`) **não estão** em `data/processed/` desta
máquina; sem elas o ZIP não sustenta o "5× acima do nulo" (A-OBS-11).

**O professor, com o ZIP:**

```bash
python scripts/iniciar.py --oulad caminho\para\oulad-resultados.zip
```

Ou à mão: extrair de modo que exista
`data/processed/oulad_vle_bbb_2013j/bipartite/nodes.csv`, rodar
`python -m edugraph validate --root data/processed` e subir a API **da
raiz do repositório**.

**Com o OULAD bruto** (se ele pedir para reprocessar): a receita de
[`specs/frente-a/README.md`](specs/frente-a/README.md). ~14 min para
`oulad_module_presentation` e `oulad_vle_bbb_2013j`; a coorte
`oulad_bbb_2013j` passa de 2 h por causa do Girvan–Newman (T-OBS-01).

### Hospedagem: Vercel só com os dados fictícios

**É possível, com adaptação; não é o caminho mais direto.** O que pesa:

| Ponto | Situação |
|---|---|
| Runtime | Vercel roda FastAPI como função Python. O limite de pacote passou para 500 MB descompactados em 2026 (era 250 MB). Medido: numpy + scipy + networkx + FastAPI ≈ 170 MB; com pandas e matplotlib, que o `pyproject.toml` também instala, ≈ 275 MB. Cabe |
| O que o servidor precisa | a API e o laboratório **não importam** pandas nem matplotlib e **não escrevem em disco** (conferido): servem bem a um ambiente só de leitura |
| Arquivos novos | um ponto de entrada (`app = create_app([<raiz>/data/fixtures], dev_cors=False)`), um `vercel.json` com o build do front (`cd frontend && npm ci && npm run build`) e a inclusão explícita de `data/fixtures/` no pacote (o exemplo da documentação da Vercel exclui pastas `fixtures`) |
| Partida a frio | cada instância nova paga o *import* de numpy/scipy/networkx (alguns segundos) na primeira requisição |
| Tempo | o laboratório tem teto de 60 s e o Girvan–Newman, orçamento de 20 s: dentro do limite das funções |
| OULAD | **fora**: a projeção do AVA ocupa ~1 GB no cache da API |
| Exposição | `POST /lab/run` consome CPU e não tem autenticação (ADR-0013 diz "uso interno"); num link público, aceitável só com dados fictícios |

**Alternativa sem adaptar nada:** um serviço que rode um contêiner com o
mesmo `python -m edugraph api serve` (Hugging Face Spaces em Docker,
Render). Serve o mesmo sistema que o professor roda localmente e, com
memória suficiente, até os resultados do OULAD. **Recomendação:** perguntar
ao orientador se o link ajuda (estudo da apresentação, pergunta 2) antes de investir; se
ajudar, o contêiner é o caminho de menos risco, e a Vercel serve se o grupo
já usa a conta.
