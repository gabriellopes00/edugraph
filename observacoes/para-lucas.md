# Observações para o Lucas — Frente C

Ver as regras em [`README.md`](README.md).

## Abertas

### C-OBS-01 · Decidir se os relatórios internos entram no repositório

- **De:** revisão final (Claude, sessão do Lucas) · **Data:** 26/09/2026
- **Onde:** `results/relatorio-interno-oulad_module_presentation.md` e
  `results/relatorio-interno-oulad_vle_bbb_2013j.md` (fora do git)
- **O quê:** são a saída obrigatória da C-07 e se regeneram idênticos com
  `python -m edugraph centrality report --root data/processed --dataset <ds>`.
  Trazem só agregados de dados públicos, mas cada um diz "uso exclusivamente
  interno", e o repositório é público.
- **Como resolver:** decidir com o grupo; se entrarem, fazer o commit dos
  dois arquivos.

### C-OBS-03 · Tabela de sensibilidade e modo do peso não estão nas tabelas finais

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `docs/artigo/decisoes-metodologicas.md:500`,
  `docs/artigo/decisoes-metodologicas.md:504`,
  `results/tables/tab6-criticas-oulad_module_presentation-discipline_simple.csv:1`
  e `docs/artigo/indice-tabelas.md:27`.
- **O quê:** o texto promete uma tabela de sensibilidade comparando os modos
  da intermediação, mas ela não existe em `results/tables/` nem no índice.
  A tabela `tab6-criticas-*.csv` tem o cabeçalho
  `dataset,projection_id,metric,rank,node_id,label,score`, sem `weight_mode`.
  A regra do índice exige identificar a configuração, e a decisão metodológica
  exige dizer qual modo foi usado. A auditoria conferiu os arquivos com
  `rg --files results/tables` e `rg -n 'weight_mode' results/tables` (sem
  ocorrência), além do cabeçalho do CSV.
- **Como resolver:** gerar e indexar a comparação de sensibilidade e identificar
  o modo do peso nas tabelas finais ou nas respectivas legendas, com a origem
  dos números. Preservar o contrato congelado; se a solução exigir mudá-lo,
  seguir ADR e aprovação dos três.
- **Atualização:** 20/10/2026 por Lucas, branch c/pendencias-frente-c —
  geração de tab6/tab7 inclui `weight_mode`, `k`, `estimate` e `seed`,
  com legendas; comando `centrality sensitivity` compara `none` e
  `inverse` sem sobrescrever artefatos principais. Testado em cópias de
  `tiny_v1` e `synthetic_v1`, incluindo idempotência, configuração amostrada
  e preservação das entradas. Contratos e fixtures não foram alterados.
  Permanece aberta a regeneração das tabelas OULAD: executar, para cada
  dataset, os comandos abaixo em máquina com `data/processed`:
  `python -m edugraph centrality critical --root data/processed --dataset oulad_module_presentation --out data/processed --tables results/tables`;
  `python -m edugraph centrality sensitivity --root data/processed --dataset oulad_module_presentation --tables results/tables`;
  `python -m edugraph centrality critical --root data/processed --dataset oulad_vle_bbb_2013j --out data/processed --tables results/tables`;
  `python -m edugraph centrality sensitivity --root data/processed --dataset oulad_vle_bbb_2013j --tables results/tables`.
  Não houve regeneração de `results/tables/` nesta máquina sem OULAD.
- **Atualização:** revisão FIX-C2 de 20/10/2026 por Lucas, branch
  c/pendencias-frente-c — legendas próprias para ranking, discordância e
  sensibilidade, sem referências cruzadas. Acrescentado teste com ponte
  ponderada em `tmp_path`: DC passa de score 0 para 2/3 e do rank 3 para 2
  ao trocar `none` por `inverse`; valores derivados à mão no comentário.
  Mutação temporária fazendo ambos os cálculos por `none`, com os rótulos
  preservados, fez o teste falhar: DC obtido 0, esperado 2/3; fonte
  restaurada e teste passando. A pendência OULAD acima continua aberta.
- **Atualização:** 30/10/2026 por Pedro, revisão de entrega — com o OULAD
  baixado e as três configurações rodadas do zero, o código atual já
  resolve a parte de código: `centrality critical` grava `weight_mode`, `k`,
  `estimate` e `seed` nas tab6/tab7, e `centrality sensitivity` gera
  `tab6-sensibilidade-oulad_module_presentation-*.csv` em 1 s. Os valores
  batem com os versionados (mesmo ranking; diferenças só no 16º dígito do
  autovetor). Falta só regenerar `results/tables/` e o índice com os
  comandos acima e fazer o commit.

### C-OBS-11 · Baixa prioridade: referências históricas a xfail, TODO e handler 501

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `docs/specs/frente-c/C-01-grau-intermediacao.md:70`,
  `docs/specs/frente-c/C-01-grau-intermediacao.md:77`,
  `docs/specs/frente-c/C-02-autovetor.md:65`,
  `docs/specs/frente-c/C-04-api.md:69`,
  `docs/specs/frente-c/C-04-api.md:77`,
  `docs/specs/frente-c/C-05-frontend.md:81` e
  `src/edugraph/api/app.py:90`.
- **O quê:** as specs concluídas ainda falam em testes escritos como
  `xfail`, remoção futura desses marcadores e `TODO C-05`. A API mantém
  o handler de `NotImplementedError` que devolve 501, remanescente dos
  stubs já implementados. A auditoria não encontrou `xfail` na execução
  atual da suíte. No checkout de `main`, as linhas 93–96 da C-04
  descrevem o corte de arestas; os textos antigos de `xfail` estão nas
  linhas 69 e 77, referenciadas acima.
- **Como resolver:** atualizar os textos para o estado concluído e revisar
  a necessidade do handler 501 sem alterar o tratamento dos erros de
  contrato. Prioridade baixa; preservar o histórico relevante.
- **Atualização:** 20/10/2026 por Lucas, branch c/pendencias-frente-c —
  handler 501 removido após confirmar que nenhuma rota levanta
  `NotImplementedError`; textos de C-01, C-02 e C-04 atualizados.
  Permanece aberta somente a referência `TODO C-05` em
  `docs/specs/frente-c/C-05-frontend.md:81`, reservada ao branch do redesign;
  `frontend/README.md` também não foi alterado.

### C-OBS-12 · Auditoria npm aponta vulnerabilidades no Vite e esbuild existentes

- **De:** correção FIX-C, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `frontend/package.json:31` e `frontend/package-lock.json:1`.
- **O quê:** após instalar as dependências no worktree, `npm audit --json`
  retornou exit 1 e `total: 2`, com `moderate: 1` (`esbuild`, transitivo)
  e `high: 1` (`vite`, direto). A árvore instalada mantém Vite 5.4.21 e
  esbuild 0.21.5, anteriores à adição do lint. Entre os avisos constam
  GHSA-67mh-4wv8-2f99 (esbuild) e GHSA-fx2h-pf6j-xcff (Vite).
  O npm propõe Vite 8.3.4 com `isSemVerMajor: true`; typecheck, lint e
  build passaram, mas não corrigem esses avisos das ferramentas de desenvolvimento.
- **Como resolver:** planejar atualização do Vite, do plugin React e da
  dependência transitiva em tarefa própria, verificando compatibilidade
  com o redesign e repetindo captura, typecheck, lint e build. Não aplicar
  `npm audit fix --force` sem revisar a migração de versão principal.

## Resolvidas

### C-OBS-13 · Capturas da interface são 60% do peso do repositório

- **De:** Pedro (Frente A), revisão de entrega · **Data:** 30/10/2026
- **Onde:** `results/figures/ui-1..4-*.png` e `frontend/scripts/` (`npm run capture`)
- **O quê:** as quatro capturas têm 3200×2000 px em PNG e somam 9,1 MB na
  árvore e 8,8 dos 14,6 MB do histórico do git. Compressão PNG sem perdas
  só tira 4%. Medido sobre os arquivos atuais: JPEG qualidade 88 dá
  2,1 MB no total (−77%); PNG a 1600×1000 dá 3,4 MB (−63%). Como a
  C-OBS-05 já pede refazer as quatro capturas depois do redesign, dá para
  resolver as duas coisas juntas.
- **Como resolver:** ao refazer as capturas, gravar em JPEG (qualidade
  ~88) ou com `deviceScaleFactor` 1, e ajustar as legendas e o índice de
  figuras. Se o grupo decidir limpar o histórico antes da entrega (ver
  `docs/entrega.md` e T-OBS-04), as capturas antigas saem dele também.
- **Resolvida:** 31/10/2026 por Pedro, branch `a/entrega-revisao` — as quatro capturas `ui-*.png` (9,1 MB) saíram da árvore junto com as demais figuras. O que resta do peso está no histórico do git (T-OBS-04, decisão 2).

### C-OBS-05 · Figura 9 precisa acompanhar o redesign da interface

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `docs/artigo/indice-figuras.md:18`,
  `docs/artigo/indice-figuras.md:44`,
  `results/figures/ui-1-comunidades-synthetic_v1.caption.txt:1`,
  `results/figures/ui-2-intermediacao-synthetic_v1.caption.txt:1`,
  `results/figures/ui-3-disciplinas-criticas-oulad_module_presentation.caption.txt:1`
  e `results/figures/ui-4-alunos-ava-oulad_vle_bbb_2013j.caption.txt:1`.
- **O quê:** as quatro capturas `ui-1..4` e suas legendas representam a
  interface anterior ao redesign do branch `c/C-05-redesign-visual`.
  O índice ainda marca a figura 9 como presente com esses arquivos. A
  resolução histórica de C-OBS-02 continua válida para a captura original;
  este item registra a atualização necessária após o novo visual.
- **Como resolver:** depois do merge do redesign, refazer as quatro capturas
  com `npm run capture`, revisar as legendas e regenerar o índice com
  `python -m edugraph figures --index`, usando uma máquina com os artefatos
  necessários para as telas OULAD.
- **Atualização:** 30/10/2026 por Pedro, implementação do laboratório
  (ADR-0013) — a interface mudou de novo: ganhou a aba *Laboratório ao
  vivo* (a padrão) e a *Leitura* no explorador (nomes, papéis, contornos).
  `frontend/scripts/capture.mjs` agora abre em `#explorar`, para que as
  cenas da figura 9 continuem escolhendo os seletores certos. Vale
  acrescentar uma cena do laboratório (resultado, com as áreas plantadas
  reveladas) às quatro `ui-*`, e refazer tudo uma vez só, em JPEG
  (C-OBS-13).
- **Atualização:** 31/10/2026 por Pedro — o resultado ganhou a seção
  *Perfis dos alunos* (risco de evasão e possíveis talentos,
  `frontend/src/components/Sinais.tsx`) e a legenda das comunidades passou
  a contar alunos em risco e talentos por grupo. Para a figura 9, uma cena
  boa é o resultado do laboratório com *Revelar o desfecho* ligado
  (tabela "Conferindo com o que aconteceu").
- **Atualização:** 31/10/2026 por Pedro — a interface ganhou um tour de
  boas-vindas que abre na primeira visita e cobriria as capturas.
  `frontend/scripts/capture.mjs` agora navega para `/?semtour#explorar`
  (`?semtour` desliga o tour). Quem usar outro script de captura deve
  fazer o mesmo.
- **Resolvida:** 31/10/2026 por Pedro, branch `a/entrega-revisao` — decisão do grupo: as figuras e capturas deixam de ser versionadas (`results/figures/` apagada e no `.gitignore`, índice gerado removido). A figura 9 não será refeita; os resultados se mostram na interface. `npm run capture` continua funcionando e grava em `results/figures/`, pasta ignorada.

### C-OBS-06 · Documentação ainda anuncia 275 testes e 11 xfail da Frente C

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `README.md:40`, `README.md:41` e
  `docs/testes/estrategia.md:46`.
- **O quê:** README e estratégia de testes anunciam 275 testes passando e
  11 `xfail`, atribuídos a specs abertas da Frente C. Na auditoria,
  `.venv/bin/python -m pytest -m 'not slow' -q -p no:cacheprovider`
  (com `--basetemp` temporário) retornou
  `343 passed, 1 skipped, 1 deselected, 1 warning in 15.72s`, sem `xfail`.
  O skip é o dataset `oulad_module_presentation` ausente nas fixtures;
  não é falha de implementação.
- **Como resolver:** atualizar os números, a data e a descrição das specs
  concluídas; distinguir os marcadores históricos do estado atual da suíte.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — README e estratégia atualizados com medição final no worktree: pytest -m "not slow" -q retornou 357 passed, 1 skipped (OULAD ausente), 0 xfail, 1 deselected e 1 warning; specs da Frente C descritas como implementadas. Contagem renovada na FIX-C2 após o teste ponderado: 358 passed, 1 skipped, 0 xfail, 1 deselected e 1 warning; documentação sincronizada.


### C-OBS-10 · README não avisa que a coorte por avaliação está sem métricas

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `docs/specs/frente-c/README.md:73` e
  `observacoes/para-todos.md:8`.
- **O quê:** a tabela apresenta `oulad_bbb_2013j` como o grafo menor para
  comparar Louvain × Girvan-Newman, sem avisar da falta de comunidades e
  centralidades registrada em T-OBS-01. A auditoria confirmou que os
  TOMLs já declaram as etapas, mas não pôde verificar a execução real:
  esta máquina não tem `data/processed` nem os dados brutos OULAD.
- **Como resolver:** acrescentar o aviso e a referência a T-OBS-01 enquanto
  a execução estiver pendente; atualizar o texto depois da rodada ou da
  decisão de excluir o dataset.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — README da Frente C avisa da rodada pendente para oulad_bbb_2013j, referencia T-OBS-01 e distingue configuração existente de execução não verificável sem OULAD.


### C-OBS-08 · Lockfile ignorado impede reproduzir as dependências do frontend

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `.gitignore:41` e `frontend/package.json:15`.
- **O quê:** `.gitignore` ignora `frontend/package-lock.json`, enquanto
  as dependências e devDependencies usam faixas `^`, por exemplo
  `react: ^18.3.1` e `vite: ^5.4.10`. O manifesto não fixa as versões
  transitivas nem garante a mesma árvore em instalações futuras.
- **Como resolver:** versionar o lockfile e adotar instalação reproduzível,
  ou registrar explicitamente a decisão do grupo e suas limitações.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — frontend/package-lock.json gerado por npm install no worktree e versionado; linha de exclusão removida do .gitignore. Lockfile v3 confere com dependências, devDependencies e engines do manifesto, permitindo npm ci.


### C-OBS-07 · Script lint chama ESLint ausente das dependências

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `frontend/package.json:12` e `frontend/package.json:22`.
- **O quê:** o script `lint` executa `eslint src --ext .ts,.tsx`, mas
  `eslint` não consta nas dependências ou devDependencies. A auditoria
  AUD-01 registrou falha de `npm run lint` por ESLint inexistente; uma
  instalação baseada no manifesto não fornece o executável prometido.
- **Como resolver:** Lucas decide entre remover o script ou adicionar e
  configurar ESLint. A segunda opção altera dependências e requer a
  autorização correspondente; não instalar pacotes apenas para esconder
  a inconsistência local.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — ESLint 10.13.0, typescript-eslint 8.72.0 e eslint-plugin-react-hooks 7.1.1 fixados; flat config verifica TypeScript e regras/dependências de hooks; npm run lint passou sem alterar componentes. Manifesto e README explicitam as versões de Node compatíveis.


### C-OBS-09 · Erro 422 da API pode aparecer como [object Object] no frontend

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `frontend/src/api.ts:47`, `frontend/src/api.ts:52` e
  `src/edugraph/api/routes.py:366`.
- **O quê:** o cliente faz cast do corpo de erro para `{ detail?: string }`,
  mas o FastAPI devolve um array em erros de validação. Na API temporária
  da AUD-01b, `curl --fail-with-body` para
  `/datasets/synthetic_dev/centrality/student_simple/absent` retornou
  HTTP 422 (exit 22), com
  `{"detail":[{"type":"literal_error","loc":["path","metric"],"msg":"Input should be 'degree', 'betweenness' or 'eigenvector'",...}]}`.
  Passar esse array ao construtor de `Error` produz a mensagem
  `[object Object]`. Os endpoints válidos retornaram 200.
- **Como resolver:** tratar `detail` como `unknown`, preservar strings e
  formatar arrays de validação pelos campos `loc` e `msg`, com fallback
  para `statusText`; testar o corpo de erro 422.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — detail tratado como unknown; strings preservadas, arrays FastAPI formatados por loc/msg e fallback statusText para corpos malformados; seis testes Node passaram após reproduzir quatro falhas antes da correção.


### C-OBS-04 · Estágio e handlers de CLI da Frente C sem testes automatizados

- **De:** auditoria AUD-01, sessão do Lucas · **Data:** 20/10/2026
- **Onde:** `src/edugraph/centrality/stage.py:104`,
  `src/edugraph/centrality/cli.py:153`,
  `src/edugraph/centrality/cli.py:177`,
  `src/edugraph/centrality/cli.py:189`,
  `src/edugraph/centrality/cli.py:270`,
  `src/edugraph/centrality/cli.py:354`,
  `src/edugraph/api/cli.py:30` e `src/edugraph/api/cli.py:53`.
- **O quê:** a suíte testa algoritmos, relatórios e rotas, mas não exercita
  `CentralityStage.run`, os `cmd_*` de centralidade nem `api openapi/serve`
  pela CLI. A busca
  `rg -n 'CentralityStage|cmd_|openapi|api.*serve|centrality.stage|centrality.cli' tests`
  só encontra, para OpenAPI, testes do endpoint `/openapi.json` e de
  `client.app.openapi()`, não dos comandos. A execução manual da AUD-01b
  passou, mas não substitui regressão automatizada da composição e dos
  parâmetros de entrada.
- **Como resolver:** acrescentar testes de integração dos comandos e do estágio,
  com artefatos em `tmp_path`, cobrindo parâmetros, saída e erros. Para
  `serve`, testar a configuração do servidor sem deixar processo ativo;
  incluir o teste de colisão de raízes descrito em T-OBS-02.
- **Resolvida:** 20/10/2026 por Lucas, branch c/pendencias-frente-c — 14 casos originais em test_cli.py cobrem estágio, all/compute/critical/evaluate/report, api openapi e serve (incluindo reload), configuração e sensibilidade, com cópias das fixtures e saídas em tmp_path; verificam cobertura, parâmetros, colunas e idempotência. O teste de colisão de raízes ficou com T-OBS-02, pois pertence ao runner compartilhado. A FIX-C2 acrescentou o 15º caso, com ponte ponderada e prova de mutação para distinguir numericamente os modos de sensibilidade.


### C-OBS-02 · Figura 9: capturas da interface

- **De:** revisão final (Claude, sessão do Lucas) · **Data:** 26/09/2026
- **Onde:** `docs/artigo/indice-figuras.md` (figura 9, "pendente")
- **O quê:** a C-05 prevê capturas de tela da interface para o capítulo 3,
  com o prefixo `ui-` em `results/figures/`. Nenhuma foi gerada.
- **Como resolver:** capturar as telas do roteiro do `frontend/README.md` e
  regenerar o índice com `python -m edugraph figures --index`.
- **Resolvida:** 26/09/2026 por Lucas, branch `c/C-05-capturas` — quatro capturas
  geradas por `npm run capture` (`frontend/scripts/capture.mjs`) e índice
  regenerado; a figura 9 passou a "presente".
