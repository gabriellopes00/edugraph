# Observações para o grupo

Ver as regras em [`README.md`](README.md). Aqui entra o que envolve mais de
uma frente ou precisa de decisão conjunta.

## Abertas

### T-OBS-01 · `oulad_bbb_2013j` sem comunidades e sem centralidades

- **De:** Lucas (Frente C) · **Data:** 26/09/2026
- **Onde:** `data/processed/oulad_bbb_2013j` (fora do git)
- **O quê:** o dataset da coorte por avaliação (1.706 alunos) foi gerado pela
  Frente A, mas nenhuma frente rodou comunidades nem centralidades nele. No
  front, ele aparece sem cor e sem tamanho. Segundo o README da Frente C, é o
  grafo menor pensado para a comparação Louvain × Girvan-Newman.
- **Como resolver:** a Frente B decide se roda as comunidades
  (`run configs/oulad_cohort_bbb_2013j.toml --only community --root data/processed`)
  e a Frente C roda as centralidades em seguida
  (`--only centrality`). Ou o grupo decide que ele fica de fora.

- **Atualização:** auditoria de 20/10/2026 confirmou que os três TOMLs
  OULAD (`configs/oulad_cohort_bbb_2013j.toml:11`,
  `configs/oulad_module_presentation.toml:14` e
  `configs/oulad_vle_bbb_2013j.toml:18`) já têm
  `stages = ["data", "community", "centrality"]`: a falta registrada é
  só de execução, não de configuração. A execução real não é verificável
  nesta máquina, sem dados brutos OULAD nem `data/processed`.
- **Atualização:** 30/10/2026 por Pedro, revisão de entrega — rodei
  `run configs/oulad_cohort_bbb_2013j.toml` do zero. `data` levou ~15 s e o
  Louvain em `student_simple`, ~6 s; interrompi no Girvan-Newman. Medido à
  parte: na amostra de 400 alunos (`sample_nodes = 400`), a projeção tem
  25.650 arestas e **uma** intermediação de arestas leva 1,75 s. O
  orçamento de 3.600 s comporta ~2.000 remoções, menos de 8% das arestas:
  a rodada passa de 2 h (duas projeções de aluno) e corre o risco de
  terminar em `skipped` ou `timeout` com poucos cortes. Antes de rodar, a
  Frente B deveria reduzir `sample_nodes` (100 a 150) ou o orçamento. A intermediação exata
  da Frente C nessa coorte é barata: ~2 min por projeção de aluno.
- **Atualização:** 30/10/2026 por Pedro — `oulad_bbb_2013j` foi completado
  só com Louvain e centralidade (`community louvain` nas quatro projeções
  e `centrality all --k 200`, 85 s no total; `validate` ok, 22 artefatos).
  Falta o Girvan–Newman da coorte, que continua levando > 2 h com a
  configuração atual.

### T-OBS-02 · Pipeline mistura rodadas quando a raiz antiga precede a saída

- **De:** auditoria AUD-01 · **Data:** 20/10/2026
- **Onde:** `src/edugraph/__main__.py:128`,
  `src/edugraph/__main__.py:141`,
  `src/edugraph/community/stage.py:63` e
  `src/edugraph/centrality/stage.py:110`.
- **O quê:** com `--root` diferente de `--out` e o mesmo dataset nas duas
  raízes, A grava uma nova rodada em `--out`, mas B e C resolvem artefatos
  por `[*roots, out]` e leem primeiro a raiz antiga. Na AUD-01b, uma cópia
  temporária do TOML sintético com dataset `tiny_v1`, só Louvain e degree,
  executada por `python -m edugraph run <config-temporária> --root
  <cópia-das-fixtures> --out <saída-temporária>` terminou com exit 0.
  Porém, `python -m edugraph validate --root <saída-temporária>` falhou
  (exit 1): `membership cobre 3 nós, mas a projeção
  'discipline_resource_allocation' tem 7`. A reprodução isolando os
  estágios A e C também mostrou `A output nodes=98; C output scores=6;
  same nodes=False`. O pipeline com leitura e escrita na mesma raiz passou;
  a quebra exige a colisão entre raiz antiga e saída distinta.
- **Como resolver:** o runner deve promover a saída da etapa executada à
  primeira raiz das etapas seguintes, preservando a precedência esperada
  de execuções isoladas; acrescentar teste de colisão de dataset entre
  entrada antiga e saída regenerada. O runner é arquivo compartilhado:
  a alteração exige aprovação dos três. B e C devem revisar em conjunto
  a resolução de raízes; não mudar o contrato congelado para contornar
  o problema.

### T-OBS-04 · Decisões de entrega que precisam dos três

- **De:** Pedro (Frente A), revisão de entrega · **Data:** 30/10/2026
- **Onde:** [`docs/entrega.md`](../docs/entrega.md)
- **O quê:** a revisão de entrega (clone limpo, instalação, testes,
  pipeline sintético, API e rodada do OULAD) deixou três decisões que
  nenhuma frente toma sozinha: (1) limpar o histórico do git das imagens
  pesadas, o que exige *force push* em `main`; (2) entregar o front-end
  já compilado, porque sem Node o professor vê só um JSON em `/`;
  (3) T-OBS-02 (mistura de rodadas no runner) antes da entrega ou como
  limitação documentada. Os números e os comandos estão no documento.
- **Como resolver:** decidir em conjunto e registrar a decisão aqui.
- **Atualização:** 30/10/2026 por Pedro — o laboratório ao vivo e o cache
  da API foram implementados (ver a seção 8 de
  [`docs/entrega.md`](../docs/entrega.md) e a ADR-0013). A decisão (2) sobre
  o front compilado ficou mais importante: **sem Node a banca não vê o
  laboratório**, só um JSON em `/`. Também: o `CLAUDE.md` deixou de exigir
  contrato congelado e ownership por frente, a pedido do grupo.
- **Atualização:** 31/10/2026 por Pedro — o grupo decidiu que as figuras saem do
  repositório (ver `docs/entrega.md`, seção 6): `results/figures/` foi apagada
  da árvore e ignorada. Isso resolve o peso **na árvore** (15 MB) e a ZIP do
  GitHub, mas o **histórico** continua com as versões antigas (14,5 MB de PNG e
  SVG): só a reescrita do histórico, com *force push* em `main`, diminui o
  clone. Essa reescrita **não foi feita**; precisa dos três (decisão 1).
  O sistema também foi verificado sem `data/processed/`: com ou sem ela, a
  API sobe, o laboratório monta a turma de Computação e o explorador lista
  as fixtures (`tests/api/test_raiz_ausente.py`).

## Resolvidas

### T-OBS-03 · Informativo: CI do frontend executa lint e testes

- **De:** correção FIX-C2, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `.github/workflows/ci.yml:96` e `frontend/package.json:14`.
- **O quê:** o job do frontend usa o lockfile como chave de cache e
  instala por `npm ci`; além de tipos e build, passa a executar
  `npm run lint` e `npm test`. A sequência local
  `npm ci && npm run lint && npm test && npm run build` passou, com
  seis testes do cliente. O caráter informativo do job foi preservado.
- **Como resolver:** aviso ao grupo; manter o lockfile e os testes do
  frontend atualizados nas próximas alterações.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c —
  CI atualizada e comandos verificados localmente; item informativo.
