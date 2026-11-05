# Decisões metodológicas — o que precisa estar no texto

O briefing (§9) trata rastreabilidade como requisito funcional: cada
escolha não-óbvia precisa estar registrada, porque vira parágrafo de
justificativa e **pergunta de banca**.

Este documento é a lista de coisas que o artigo precisa dizer, e onde
cada uma está resolvida no repositório. Ele é atualizado conforme as
specs fecham.

## Já decididas

### A restrição de não usar IA/ML

**O que dizer.** Nenhum componente usa aprendizado de máquina. Louvain e
Girvan-Newman são otimização combinatória e remoção iterativa de arestas
sobre a estrutura do grafo: não há treino, não há rótulo de entrada, e o
resultado é rastreável até as arestas.

NMI, pureza e correlação de Spearman, usados na validação, são medidas de
teoria da informação e estatística descritiva **entre partições e
categorias já conhecidas** — nenhuma delas treina nada.

**Onde está garantido.** ADR-0008; `tests/contract/test_no_ml.py` varre o
código e as dependências declaradas.

### Rótulos históricos fora do grafo

**O que dizer.** O desfecho de cada matrícula entra **apenas** na
validação a posteriori. Ele vive em `outcomes.csv`, separado do grafo, e
só módulos `evaluate.py` podem lê-lo.

**Onde está garantido.** ADR-0008;
`tests/contract/test_outcomes_isolation.py`.

### A ressalva do critério `final_result_pass`

**O que dizer — e é preciso dizer.** Uma das configurações de aresta
(`final_result_pass`) usa o desfecho para decidir se a aresta existe.
Isso não é um algoritmo inferindo a partir do rótulo: é uma **definição
declarada de aresta**, registrada em `BipartiteSpec` e visível no
`meta.json` do artefato.

A distinção é sutil, e a banca vai perguntar. Se o grupo preferir não se
expor à discussão, a alternativa é usar só `score_threshold` e
`vle_activity` e citar `final_result_pass` como configuração considerada
e descartada — o que também é uma resposta defensável.

**Onde está.** ADR-0007.

### Granularidade do nó disciplina (decisão D1)

**O que dizer.** O OULAD tem só 7 módulos. Com V = módulo, a projeção
disciplina↔disciplina degenera: qualquer par de disciplinas compartilha
algum aluno, o grafo vira completo, toda intermediação é zero e não há
gargalo a identificar.

**Isto foi verificado empiricamente, antes do OULAD.** Na fixture
`synthetic_v1`, `discipline_simple` tem 7 nós e 21 arestas — K₇ exato.
Registrado em `data/fixtures/synthetic_v1/REFERENCE.md`.

A saída é granularidade mais fina: `module_presentation` (22 nós) como
padrão, com `module` (7) como comparação, e `assessment` para as análises
por coorte. A comparação entre granularidades **é resultado**, não
detalhe de implementação.

**A base real, medida em 18/09/2026 — e a previsão estava meio errada.**
Com V = módulo, `discipline_simple` tem **12 de 21 arestas (57%)**, não o
grafo completo que a D1 previa: 91,8% dos alunos do OULAD cursam **um
único módulo**, e essa esparsidade impede a completude. Com V =
`module_presentation`, são **93 de 231 (40%)**. Em nenhuma das duas a
projeção disciplina↔disciplina degenera — a intermediação discrimina, e é
a configuração recomendada para a spec C-03.

O problema real de V = módulo é **do outro lado**: a projeção aluno↔aluno
daria ~52 milhões de pares (15,9 milhões com `module_presentation`), e
não cabe em memória. A decisão D1 acertou o diagnóstico — V = módulo é
inadequado — pela razão oposta à que supunha.

**Segundo achado, da spec A-01: a degeneração depende também da
esparsidade.** `synthetic_v2` tem os mesmos 7 módulos e a mesma seed de
`synthetic_v1`, mas 70% dos alunos reduzidos a uma única matrícula — o
perfil do OULAD. Nela, `discipline_simple` tem **16 de 21 arestas**: não
é mais completa, e a intermediação passa a discriminar. Isso muda o que
o texto deve dizer: com V = módulo, a projeção disciplina↔disciplina é
completa quando os alunos cursam muitas disciplinas (`synthetic_v1`) e
deixa de ser quando cursam poucas (`synthetic_v2`, OULAD). No OULAD real
as duas forças atuam: poucos módulos *e* poucas matrículas por aluno. O
número real só a A-02/A-06 dirão.

**Onde está.** ADR-0007; `configs/`;
`data/fixtures/synthetic_v2/REFERENCE.md`.

### Girvan-Newman e o orçamento de tempo

**O que dizer.** O algoritmo é O(m²n) e não termina sobre a base
completa. O trabalho o executa com orçamento de tempo declarado e
reporta, para cada configuração, se ela terminou (`status`). O custo
relativo ao Louvain é um resultado medido, não uma citação de notação
assintótica.

**Onde está.** ADR-0006; coluna `status` em `metrics/communities.csv`.

### Determinismo

**O que dizer.** Toda execução estocástica tem semente fixa, gravada no
artefato. Mesma configuração, mesmo resultado.

**A ressalva honesta:** um resultado que só vale para a seed 42 não é
resultado. Os testes usam faixas, não igualdade exata, e onde a
estabilidade importa (os valores de `tiny_v1`) os esperados foram
derivados no papel, não copiados da biblioteca.

**Onde está.** ADR-0011.

### Implementações à mão

**O que dizer.** Três algoritmos foram implementados sem usar a
biblioteca, e cada um é comparado numericamente com a implementação do
NetworkX: as projeções (A-04/A-05), a modularidade Q (B-03) e a
centralidade de autovetor por iteração de potência (C-02).

Brandes (intermediação) e Louvain **não** foram implementados à mão, e a
razão é registrável: custo alto e retorno didático baixo perto das outras
três.

**Onde está.** ADR-0010.

### Nós isolados removidos do bipartido

**O que dizer.** Alunos que não satisfazem o critério de aresta em
disciplina nenhuma viram nós de grau zero e são removidos. Em
`synthetic_v1`, o gerador produz 120 alunos e o bipartido tem 98.

**Consequência a reportar:** o starter kit relata ~25 comunidades; a
fixture tem 3. As ~22 extras eram esses nós isolados, cada um virando
comunidade de tamanho 1. Ao reportar `k` no artigo, **dizer quantas
comunidades são unitárias** — um `k` alto de singletons diz algo muito
diferente de um `k` alto de grupos reais.

### Agregação por (aluno, disciplina) — decidida na A-03

**O que dizer.** Quando um aluno tem mais de uma matrícula na mesma
disciplina (repetiu o módulo em outra apresentação e a granularidade é
`module`), as linhas são agregadas assim: **média** da nota, **soma** dos
cliques no AVA, e aprovado se **alguma** das matrículas foi `Pass` ou
`Distinction`. O peso da aresta é a grandeza que o critério de aresta
olhou — nota média, cliques ou 1,0 — e as projeções o ignoram: usam só a
existência da aresta.

**Onde está.** `edugraph.data.bipartite.normalize_table`;
`meta.stats["n_isolated_removed"]` registra quantos alunos saíram por não
satisfazer o critério em disciplina nenhuma (22 dos 120 em `synthetic_v1`).

### A referência NetworkX para a alocação de recursos — decidida na A-05

**O que dizer.** A projeção simples é comparada com
`nx.bipartite.weighted_projected_graph`, que é exatamente a contagem de
vizinhos em comum. Para a alocação de recursos **não existe função
pronta no NetworkX**: `collaboration_weighted_projected_graph` é a
ponderação de Newman (2001), em que cada vizinho comum contribui
`1/(grau − 1)`, e **não** a de Zhou et al. (2007), que contribui
`1/grau`. Em `tiny_v1` a disciplina DA (grau 4) contribui 1/3 por Newman
e 1/4 por Zhou — as duas divergem em toda aresta, e um teste garante que
isso continua sendo verdade.

A referência usada é `generic_weighted_projected_graph` com a fórmula de
Zhou fornecida por nós: a biblioteca faz a projeção (interseção de
vizinhanças, nós, atributos) e nós damos só o peso. É a comparação mais
independente possível, e o texto deve dizer isso em vez de afirmar que
"o NetworkX implementa a alocação de recursos".

**Resultado.** Nas quatro projeções de `synthetic_v1` (98 nós, 1.971
arestas), a implementação à mão e a referência concordam com diferença
máxima abaixo de 1e-9. Tabela em `metrics/projections.csv`.

**Na base real** (coorte BBB_2013J, 1.706 alunos, **1.449.841 arestas**),
as duas continuam concordando (diferença máxima 1,7e-18) e a
implementação à mão é **mais rápida**: 5,2 s contra 9,5 s do NetworkX na
projeção simples, e 5,2 s contra 22,5 s na alocação de recursos — porque
a referência precisa chamar a função de peso por par, enquanto a nossa
acumula num único percurso. É um número citável: a implementação didática
não custa desempenho.

**Onde está.** `edugraph.data.projection.networkx_ref`; ADR-0010.

### As três regras do ETL do OULAD — decididas na A-02

**O que dizer.**

1. **Nota da matrícula = média ponderada pelo `weight` da avaliação.**
   No OULAD as avaliações contínuas (TMA/CMA) somam 100 e o exame vale
   100 à parte; a média simples daria peso igual a um teste de 5% e ao
   exame. Quando todos os pesos das avaliações entregues são zero (só
   CMAs sem peso), a nota é a média simples, e a linha fica marcada
   (`score_weighted = false`) para que o texto possa dizer quantas são.
2. **Matrícula sem nota e sem clique no AVA é descartada.** Não há
   evidência de participação; ela não geraria aresta em critério nenhum.
   Reportar quantas foram descartadas.
3. **Um desfecho por aluno = o da apresentação mais recente**; empate na
   mesma apresentação, o módulo de código maior. É o "estado final" do
   aluno na base. A regra de desempate é arbitrária e por isso está
   escrita; alternativas (qualquer aprovação; o pior desfecho) mudariam
   a tabela de validação da B-06 e devem ser citadas como sensibilidade.

**O que o ETL não lê, de propósito.** Gênero, região, faixa etária,
escolaridade, IMD e deficiência de `studentInfo` não entram em
`usecols`. A forma mais segura de não vazar um atributo demográfico para
o grafo (ADR-0008) é não carregá-lo.

**Onde está.** `edugraph.data.oulad.etl` (docstring do módulo);
`edugraph.data.oulad.schema.SCHEMAS`; testes em `tests/data/test_etl.py`
sobre `oulad_mini`.

### Reduções de escala — decididas na A-06, números pendentes do OULAD

**O que dizer.** O Girvan-Newman é O(m²n) e a projeção aluno↔aluno de
uma coorte real chega a milhões de arestas. O trabalho usa quatro
reduções, sempre declaradas e sempre gravadas no artefato
(`meta.stats["reductions"]`, com parâmetros e contagens) — o texto pode
dizer, para cada tabela, exatamente sobre que recorte ela foi calculada:

1. **Coorte** (`BipartiteSpec.cohort` ou `edugraph data cohort`): uma
   apresentação de módulo. É a redução preferida, porque recorta por uma
   unidade com sentido pedagógico — uma turma — e não por conveniência.
2. **Corte por peso mínimo** (`ProjectionSpec.min_weight`): remove
   arestas fracas da projeção; não muda o conjunto de nós; o validador
   confere que foi aplicado.
3. **Amostra de alunos** com semente fixa (`sample_students`): muda quem
   está no grafo; reproduzível pela semente registrada.
4. **Núcleo-k** da projeção (`k_core`): muda a topologia de propósito;
   a partição ou centralidade calculada depois vale só para o núcleo, e
   o número de nós removidos é reportado.

**O que ainda falta e depende do download do OULAD (passo manual):** o
tamanho real de cada coorte, o tempo e o pico de memória da rodada
completa, e a escolha dos valores de `min_weight`, `sample_students` e
`k_core` para as configurações de `configs/`. Esses números viram a
seção de limitações do artigo, e a spec A-06 fica aberta até lá.

**Onde está.** `edugraph.data.scale`; `[source]` dos TOML de `configs/`.

### Q precisa de linha de base — o achado da A-08

**O que dizer, e é o mais importante desta rodada.** A modularidade
encontra "comunidades" em qualquer grafo esparso, inclusive em grafos sem
estrutura nenhuma (Guimerà et al., 2004). Por isso o trabalho compara todo
Q com o de **réplicas nulas**: os mesmos alunos, as mesmas disciplinas, os
mesmos graus, mas quem cursou o quê é sorteado.

Medido em 18/09/2026, projeção aluno↔aluno, Louvain com seed 42:

| dataset | Q real | Q nulo | veredito |
|---|---:|---|---|
| `synthetic_v1` | 0,4666 | 0,2079 ± 0,0168 (z = +15,4) | estrutura real |
| `synthetic_v2` | 0,5392 | 0,4611 ± 0,0202 (z = +3,9) | estrutura real, sinal fraco |
| OULAD `module_presentation` (amostra de 3.000) | 0,7728 | 0,7807 / 0,7816 | **indistinguível do acaso** |

Três coisas seguem disso, e todas vão para o texto:

1. **O método funciona.** No sintético, o Q real fica 15 desvios acima do
   nulo. Louvain recupera estrutura plantada — é o que valida o método e
   o que a Conclusão precisa para responder ao objetivo declarado.
2. **O OULAD não sustenta a afirmação.** O Q de 0,77 é *menor* que o das
   réplicas embaralhadas. Escrever "encontramos 15 comunidades de perfis
   de alunos" seria falso. O resultado negativo é o resultado.
3. **A esparsidade infla Q.** O Q nulo de `synthetic_v2` (0,46) é o dobro
   do de `synthetic_v1` (0,21), só por ter 70% dos alunos com uma
   matrícula. É o mesmo mecanismo que produz o 0,78 do OULAD, e explica
   *por que* a base real não discrimina: com grau mediano 1, quase não há
   informação relacional entre alunos.

**O que isso não quer dizer.** Não quer dizer que o OULAD não tenha
estrutura nenhuma — quer dizer que *esta* projeção, *nesta* granularidade,
não tem. Outras configurações (coorte, avaliação, critério de aresta) são
exatamente o que as tabelas comparativas do capítulo 3 existem para
explorar, e cada uma precisa da sua linha de base nula.

**Onde está.** Spec A-08; `edugraph.data.nullmodel`; a comparação é da
spec B-06.

### O critério de aresta muda de matrícula para interação no AVA

**O que dizer.** A seção anterior mostra que o critério "cursou o módulo"
não carrega informação relacional suficiente: 91,8% dos alunos do OULAD
cursam um único módulo, e a projeção aluno↔aluno resultante não se
distingue do acaso. O trabalho **troca o critério de aresta** para a
interação com recursos do ambiente virtual de aprendizagem.

Isto **não é mudança de tema nem de escopo**. O critério de aresta é
parâmetro desde o dia 0: o briefing §8 já listava "participação no AVA"
entre os critérios candidatos, a ADR-0007 o tornou configurável, e
`EdgeCriterion` já contém `vle_activity`. A fundamentação do tema
descreve o bipartido como **"Aluno → Comportamento"** e o peso da aresta
como "interseção de atributos compartilhados" — que é exatamente esta
configuração, e não a de matrícula.

**Por que funciona.** O grau muda de ordem de grandeza:

| nó do lado V | grau mediano do aluno |
|---|---:|
| módulo | 1 |
| módulo × apresentação | 1 |
| recurso do AVA | 40 |
| tipo de atividade | 7 |

Medido em três coortes independentes, projeção por alocação de recursos,
três sementes do Louvain cada:

| coorte | alunos × recursos | Q real | Q nulo | razão |
|---|---|---:|---:|---:|
| BBB 2013J | 1.870 × 320 | 0,0825 | 0,0158 | 5,2× |
| FFF 2013J | 2.098 × 526 | 0,0742 | 0,0081 | 9,2× |
| DDD 2014J | 1.647 × 361 | 0,0511 | 0,0073 | 7,0× |

As partições não são degeneradas: há sempre uma comunidade maior (50% a
69% dos alunos) e duas ou três menores com tamanho caracterizável. O Q é
estável entre sementes (variação na quarta casa decimal). Em DDD 2014J o
número de comunidades oscila entre 3 e 4 conforme a semente, sem alterar
o Q — limitação conhecida do Louvain, registrada como tal.

**Achado de método, e vale por si.** A escolha da ponderação decide se o
sinal aparece. Sob extração de espinha (mantendo só as arestas mais
pesadas), a **contagem simples inverte de lado** e o Q real cai *abaixo*
do nulo em todos os limiares testados; a **alocação de recursos** (Zhou
et al., 2007) se mantém acima em todos. A causa é interpretável: a
contagem simples premia volume de cliques, então as arestas mais pesadas
passam a ligar os alunos mais ativos entre si — efeito de volume, não de
afinidade. A alocação de recursos normaliza pelo grau e desfaz o viés.
Como o briefing exige as duas projeções implementadas à mão, o contraste
é resultado próprio do trabalho.

**O que a configuração antiga continua servindo.** O bipartido por módulo
**não sai do trabalho**. A projeção disciplina↔disciplina dele funciona
(93 de 231 arestas com `module_presentation`, intermediação discrimina) e
continua sendo a base da spec C-03, disciplinas críticas. As duas
configurações convivem em `configs/`, que é precisamente o que a ADR-0007
existe para permitir: uma serve à Frente B, outra à Frente C.

**Ressalvas que o texto precisa carregar.** O Q absoluto é baixo (0,05 a
0,08) — a estrutura é estatisticamente inequívoca, mas fraca. A projeção
fica quase completa (densidade 0,9996), então o sinal está nos **pesos**,
não na presença da aresta. Aplicar limiar fragmenta o grafo em centenas
de componentes de nó isolado, então o recorte honesto é a projeção cheia.

**Onde está.** ADR-0007; spec A-09; `docs/orientador/nota-01-criterio-de-aresta.md`.

### O papel do gerador sintético — e o que ele não deve fazer

**Não se misturam dados sintéticos com dados reais.** Não há aumento de
dados, não há preenchimento de lacunas, não há arestas geradas entrando no
grafo do OULAD. Qualquer número saído de um grafo misto seria ficção, e a
restrição da seção 2 do briefing deixaria de ser verificável.

O gerador agrega de três formas, todas separadas dos dados reais:

1. **Ground truth que o OULAD não tem.** A base real não traz comunidades
   conhecidas. Sem o sintético, não há como afirmar que o método recupera
   estrutura — só que ele produz um número.
2. **Linha de base nula** (A-08), que é o gerador calibrado no real *sem*
   estrutura plantada. É o que transforma um Q num resultado.
3. **Calibração da dificuldade.** `synthetic_v2` mostrou, antes do
   download, que a esparsidade derruba a detectabilidade — o que o OULAD
   depois confirmou.

**Onde está.** Specs A-01 e A-08.

### As comunidades: o que a Frente B mediu (specs B-01 a B-07)

**O método funciona, e o número que prova isso é o NMI.** Sobre
`synthetic_v1`, o Louvain parte a projeção aluno↔aluno em três
comunidades (39, 30 e 29 alunos) com Q = 0,4666, e essas três comunidades
**são** as três áreas plantadas pelo gerador: NMI = 0,8188 e pureza =
0,9490 contra o grupo plantado, apesar dos 35% de ruído. A caracterização
mostra a mesma coisa em prosa — sistemas (DDD-EEE), exatas (AAA-BBB-CCC)
e humanas (FFF-GGG), uma por comunidade.

**A comparação entre os dois algoritmos é o resultado mais citável.** Na
mesma projeção, o Girvan-Newman chega a três comunidades com Q = 0,4174
em **34,4 s**, contra 0,024 s do Louvain: **1.453× mais lento, com Q
menor**. É a mesma ordem de grandeza que o starter kit mediu (645× sobre
120 nós) e é o dado empírico que a ADR-0006 previa. As duas partições
concordam (NMI 0,774, Rand ajustado 0,808) — o achado é da estrutura, não
do algoritmo, e as duas figuras lado a lado mostram isso.

**Um k maior não é uma partição melhor.** Na projeção
disciplina↔disciplina, o Girvan-Newman devolve k = 4 com Q = 0,0331, e
**três** dessas quatro comunidades têm um nó só. Ao reportar k no texto,
dizer quantas comunidades são unitárias.

### Q implementada à mão, e por que a forma fechada (B-03)

**O que dizer.** A modularidade é calculada pela forma fechada por
comunidade, `Q = Σ_c (m_c/m − γ(K_c/2m)²)`, algebricamente idêntica à
soma dupla da definição e de custo O(m + n). Medido: 15 ms para 25 mil
arestas, 80 ms para 100 mil, 334 ms para 400 mil — linear. A forma
ingênua O(n²) existe **no teste**, escrita direto da fórmula, e é contra
ela (e contra o NetworkX) que a implementação é verificada.

**Resultado.** Nas quatro projeções de `synthetic_v1`, o Q à mão e o
`nx.community.modularity` diferem em no máximo 3,2e-15 — ruído de ponto
flutuante, três ordens abaixo da tolerância de 1e-9.

### Duas escolhas do Girvan-Newman que a banca pode perguntar (B-02)

1. **A intermediação que escolhe a aresta a remover é não ponderada; o Q
   reportado é ponderado.** Em NetworkX, peso em caminho mínimo é
   *distância*, e nas projeções peso alto significa afinidade — usá-lo
   inverteria o critério de remoção. Já o Q precisa ser ponderado para
   ser comparável com o do Louvain. As duas escolhas ficam gravadas em
   `params`, no artefato.
2. **O orçamento é verificado a cada remoção de aresta**, não só a cada
   corte como a ADR-0006 previa. O motivo é medido: o primeiro corte de
   `synthetic_v1` custa 15 s dos 34 s totais, então um orçamento de 1 s
   só seria notado 14 s depois. O comportamento observável é o da ADR —
   `status="timeout"` com a melhor partição vista, nunca exceção.

Quando o Girvan-Newman roda sobre uma **amostra** de nós, o
`projection_id` do artefato ganha o sufixo `__sample<N>`. Sem isso, uma
partição de 400 alunos poderia ser lida como a partição da projeção
inteira de 1.706 — e a tabela do capítulo 3 mentiria sobre o recorte.

### Pureza e NMI medem coisas diferentes, e o sintético mostra isso (B-06)

**O que dizer.** A validação contra o grupo plantado reporta as duas
medidas. Em `synthetic_v1` elas concordam (pureza 0,949, NMI 0,819). Em
`synthetic_v2` — mesmos grupos, 70% dos alunos com uma matrícula só — a
pureza quase não cai (0,864) e o **NMI cai pela metade (0,495)**: as
comunidades continuam homogêneas, mas deixaram de corresponder aos
grupos plantados, porque a partição ficou mais fina. Pureza sobe quando
se divide mais; NMI não. Reportar só a pureza sugeriria que o método
resiste à esparsidade, e ele não resiste.

É o mesmo mecanismo que a A-08 mediu pelo lado do Q, visto por outra
lente — e é o argumento de que o resultado negativo do OULAD não é falha
de implementação.

### O critério que separa estrutura de acaso (B-06)

**O que dizer.** Todo Q reportado é comparado com o de réplicas nulas
(spec A-08). O critério, decidido nesta spec: pelo menos **cinco**
réplicas, z = (Q real − média do nulo) / desvio do nulo, e **z ≥ 3** para
afirmar que há estrutura; abaixo disso o texto diz "indistinguível do
acaso". Com menos de cinco réplicas não há veredito.

Não é teste de significância estatística — a spec põe isso
explicitamente fora de escopo. É a distância, em desvios, até a
distribuição do acaso, e serve para separar "muito acima" de
"indistinguível".

Pelo critério, `synthetic_v1` (z = +15,4) tem estrutura e o OULAD
`module_presentation` (Q real **abaixo** do nulo) não tem — que é o
veredito que a A-08 já antecipava.

### Frequência em excesso, não em absoluto (B-05)

**O que dizer.** A disciplina que caracteriza uma comunidade é a de maior
`frequência na comunidade − frequência na base`, não a mais numerosa. A
disciplina obrigatória que todo mundo cursa apareceria em primeiro lugar
em todas as comunidades e não distinguiria nenhuma. O `profile.csv`
mostra as duas frequências lado a lado — em `synthetic_v1`, AAA aparece
em 62,1% da comunidade de exatas e em 5,1% da de sistemas, contra 23,5%
da base.

### NMI e Rand ajustado são medidas entre partições, não modelos

**O que dizer, porque a banca pode confundir.** A comparação entre duas
partições usa informação mútua normalizada (pela média aritmética das
entropias) e índice de Rand ajustado ao acaso, **implementados à mão**
sobre a tabela de contingência. São contas fechadas entre dois
agrupamentos já conhecidos: não há treino, não há rótulo de entrada e
nenhuma biblioteca de aprendizado é importada — `tests/contract/test_no_ml.py`
recusaria o import.

O mesmo vale para o uso do grupo plantado e do desfecho histórico: eles
entram **depois** de o algoritmo ter rodado, como categorias contra as
quais a estrutura é comparada, nunca como entrada.

### O peso na intermediação: caminho em saltos (C-01)

**Decisão.** A intermediação principal usa `weight_mode = "none"`: o
caminho mínimo é contado em saltos, ignorando o peso das arestas. O modo
`inverse` (distância `1/w`) é calculado e reportado como **análise de
sensibilidade**. O modo `raw` não é usado: em NetworkX o peso num caminho
mínimo é distância, e usar o número de alunos em comum como distância
inverteria a semântica da projeção (mais alunos em comum significaria
disciplinas mais *distantes*).

**Por que não `inverse` como principal.** Na projeção
disciplina↔disciplina de `oulad_module_presentation` (22 nós, 93
arestas), os pesos vão de 1 a 144 e são concentrados: a mediana das
arestas entre módulos diferentes é 2, e as cinco mais pesadas saem todas
de CCC, o módulo com mais matrículas. Com `1/w`, esse punhado de arestas
vira o atalho de quase todo caminho mínimo: **13 das 22 disciplinas ficam
com intermediação zero**, contra nenhuma no modo em saltos. O ranking
passa a medir sobretudo o tamanho do módulo — o que o grau já mede — em
vez da posição de ponte no currículo, que é o que a Introdução chama de
gargalo.

**O que muda no ranking (medido em 25/09/2026).** Correlação de Spearman
entre os dois modos: 0,56. No topo em saltos: FFF_2014B, DDD_2014J,
FFF_2014J. No topo com `1/w`: CCC_2014J, FFF_2014J, GGG_2013J. A tabela
de disciplinas críticas precisa dizer na legenda qual modo usou, e a de
sensibilidade compara os dois. A geração é feita por
`python -m edugraph centrality sensitivity --root data/processed --dataset oulad_module_presentation --tables results/tables`,
que recalcula `none` e `inverse` mantendo a configuração de amostragem e
normalização da centralidade principal, sem substituir esse artefato.
As tabelas finais e suas legendas identificam `weight_mode`, `k`,
`estimate` e `seed` (ver o índice de tabelas). Cada legenda descreve
apenas o objetivo e os campos da própria tabela: ranking, discordância
ou sensibilidade. A regeneração dos CSVs OULAD
permanece pendente de execução com os dados reais, conforme C-OBS-03.

**Pergunta de banca provável.** *"Por que jogar fora o peso?"* O peso não
é jogado fora: ele entra no grau ponderado (força) e no autovetor, que
usam afinidade no sentido certo. Só a intermediação o ignora, porque ali
o peso precisaria ser convertido em distância, e a conversão `1/w` deixa
o resultado refém de poucas arestas muito pesadas.

**A exceção: projeções quase completas usam `inverse`.** O modo em
saltos só discrimina se o grafo não for (quase) completo. Na projeção
aluno↔aluno de `oulad_vle_bbb_2013j`, a densidade é **1,000** (1.746.901
de 1.747.515 pares possíveis): todo par de alunos é vizinho, nenhum
caminho mínimo passa por um terceiro, e a intermediação em saltos dá
**zero para os 1.870 alunos**. Ali só o peso distingue, e a configuração
usa `inverse` (com 200 pivôs amostrados, porque a versão exata com peso
não termina em tempo razoável). A Frente A já tinha visto isso na A-09 e
escrito `"distance"`, que o contrato não aceita; o valor foi corrigido
para `inverse`, que é a mesma intenção. A regra, portanto: **`none` onde
a projeção é esparsa o bastante para haver caminhos de mais de um salto
(as disciplinas do `module_presentation`, com 40% de densidade); `inverse`
onde ela é quase completa.** A legenda de cada tabela diz qual foi usado.

**Amostragem de pivôs.** Com `k` menor que o número de nós, a
intermediação é estimada a partir de `k` pivôs sorteados com `seed`
fixa; o artefato registra `estimate = true`, e a tabela precisa dizer que
o valor é estimativa. Com `k` maior ou igual ao número de nós, o cálculo
é exato e o artefato diz isso — é o caso das 22 disciplinas do OULAD,
mesmo com o `k = 500` da configuração.

### Autovetor à mão: iteração sobre A + I (C-02)

**O que dizer.** A centralidade de autovetor é calculada por iteração de
potência implementada à mão, a partir do vetor uniforme `1/n` (não
aleatório, para ser reproduzível), com normalização L2 a cada passo e
parada quando a variação L1 entre iterações fica abaixo de `tol · n`,
com `tol = 1e-8`.

**A escolha não-óbvia: iterar sobre `A + I`, não sobre `A`.** Somar a
identidade não muda os autovetores — só desloca os autovalores em uma
unidade —, então o resultado é o mesmo autovetor principal. O que muda é
a convergência: num grafo bipartido, `A` tem `−λ` com o mesmo módulo de
`λ`, e a iteração pura oscila entre dois vetores sem nunca parar. O teste
`test_iteracao_sem_deslocamento_oscila_em_grafo_bipartido` mostra isso
numa estrela. É o mesmo recurso que o NetworkX usa internamente, e o
artefato registra `params.shift = 1.0`.

**Validação contra o NetworkX (medida em 25/09/2026).** Em `tiny_v1`, o
resultado bate com a forma fechada `λ = (3+√17)/2` com erro abaixo de
1e-8. Em `synthetic_v1`/`student_simple`, a implementação à mão fica a
7,7e-8 do autovetor exato (decomposição espectral), e o NetworkX com a
tolerância padrão dele (1e-6) fica a 7,0e-6: **a comparação só é justa
com o mesmo critério de parada dos dois lados**, e com ele as duas batem
abaixo de 1e-6.

**Convergência no OULAD.** Nenhuma projeção precisou do fallback:
43 iterações em `oulad_module_presentation`/`discipline_simple`, 45 em
`discipline_resource_allocation` e 7 na projeção aluno↔aluno de
`oulad_vle_bbb_2013j` (1.870 alunos). O fallback por decomposição
espectral existe e é testado, mas, se aparecer numa rodada, vira nota de
rodapé da tabela.

### Disciplinas críticas: o que a C-03 mediu

**O resultado (OULAD, `oulad_module_presentation`/`discipline_simple`,
22 disciplinas, 25/09/2026).** As três métricas apontam disciplinas
diferentes, e é isso que o artigo discute:

| Métrica | Topo 3 | O que mede |
|---|---|---|
| grau | DDD_2014J, FFF_2014J, CCC_2014B | com quantas disciplinas a disciplina compartilha alunos |
| intermediação | FFF_2014B, DDD_2014J, FFF_2014J | por onde passam os caminhos entre partes do currículo |
| autovetor | CCC_2014J, CCC_2014B, DDD_2013J | ligação com disciplinas que também são centrais |

Tabelas completas em `results/tables/tab6-criticas-*.csv` (ranking) e
`tab7-discordancia-*.csv` (conjuntos e correlações).

**A discordância é o achado.** No top 5, **FFF_2014B, FFF_2013J e
BBB_2014J aparecem só na intermediação**: são pontes sem ser populares —
o perfil de gargalo estrutural que a Introdução descreve. No outro
extremo, EEE_2013J e EEE_2014B aparecem só no autovetor, puxadas pela
vizinhança com CCC, o módulo com mais matrículas. Nenhuma disciplina está
no top 5 das três métricas. Spearman: grau × autovetor 0,84 (medem quase
o mesmo), grau × intermediação 0,53, intermediação × autovetor **0,21**
— ser ponte e estar num bloco central são dimensões diferentes.

**Duas ressalvas que a banca pode levantar.**

1. **Na alocação de recursos, grau e intermediação não mudam.** A
   projeção `discipline_resource_allocation` tem as mesmas 93 arestas
   que a `discipline_simple`; como a intermediação ignora o peso (C-01)
   e o grau é a contagem de vizinhos, só o autovetor difere entre as
   duas. Isso é consequência da decisão da C-01, não coincidência.
2. **Posição sob empate.** A chave de `centrality_top.csv` inclui a
   posição, então empates são desfeitos por `node_id`: DDD_2014J e
   FFF_2014J têm o mesmo grau (0,667) e ocupam as posições 1 e 2 por
   ordem alfabética. A tabela precisa ser lida com o score ao lado. Em
   `synthetic_v1` (K₇), a tabela inteira é ordem alfabética e o Spearman
   é **indefinido** (`nan`), não zero: todos os nós empatam.

**O que não afirmar.** Que as disciplinas de alta intermediação são
difíceis ou que reprovam mais — isso é a pergunta da C-06, respondida
a posteriori contra `outcomes.csv`, nunca premissa do ranking.

### A validação da centralidade: o que a C-06 mediu

**O método.** Depois de calculado o ranking — sem nenhum rótulo —, a
taxa de **não conclusão** (`Fail` + `Withdrawn`) dos alunos de cada
disciplina crítica é posta ao lado da taxa da base. `Withdrawn` entra
porque, para a gestão, desistir também é não concluir; `rate_Fail`
fica na tabela para quem quiser a reprovação estrita. Para os alunos, o
desfecho é distribuído por faixa de centralidade (quartis por posição).
Tudo descritivo: a spec deixa teste de significância fora de escopo.

**O resultado (OULAD, `oulad_module_presentation`, 22.425 alunos, base
37,6%, 25/09/2026).** O sinal é **fraco e depende da métrica**:

| Top 5 por | Não conclusão no conjunto | Excesso sobre a base |
|---|---|---|
| intermediação | 38,8% | **+1,2 p.p.** |
| grau | 40,0% | +2,4 p.p. |
| autovetor | 41,6% | +4,0 p.p. |

Individualmente, as disciplinas-ponte vão de FFF_2014B (+9,2 p.p.) a
BBB_2014J (**−6,4 p.p.**, abaixo da base). Tabelas em
`results/tables/tab8-reprovacao-*.csv`.

**Como ler, e o que dizer na banca.** A intermediação — a métrica que a
Introdução associa a gargalo — praticamente **não separa** as
disciplinas críticas pelo desfecho. A spec já previa essa leitura: se a
relação não aparece, o artigo reporta que centralidade estrutural e
desempenho histórico são dimensões **independentes**, e isso reforça
que a centralidade não é um proxy disfarçado da reprovação. Um gargalo
estrutural é um ponto de passagem no currículo, não uma disciplina
difícil.

**Os alunos no AVA: sinal forte, e a leitura cuidadosa que ele exige.**
Em `oulad_vle_bbb_2013j` (1.870 alunos, base 42,7%), o desfecho varia
muito com a centralidade do aluno na projeção aluno↔aluno:

| Faixa | Autovetor | Intermediação (`inverse`, k = 200) |
|---|---|---|
| Q1 (menor) | 89,3% | 71,5% |
| Q2 | 52,6% | 50,9% |
| Q3 | 18,4% | 33,4% |
| Q4 (maior) | **10,5%** | 15,0% |

(Taxas de não conclusão; tabelas em `tab8b-desfecho-faixa-*.csv`,
figura `fig8-validacao-*`.) O grau não serve aqui: a projeção é
completa, e três dos quatro quartis têm grau 1,0.

**O que isso não é.** Não é poder de previsão. O peso da aresta é o
número de recursos do AVA que os dois alunos acessaram, e **quem desiste
para de acessar**: tem menos recursos em comum com os outros e, por
construção, menor centralidade. Parte do sinal é mecânica — a
centralidade aqui mede sobretudo **volume de engajamento acumulado até
o fim da apresentação**, que o próprio desfecho trunca. Para afirmar que
a posição na rede antecipa o desfecho, seria preciso calcular a
centralidade só com a atividade das primeiras semanas, antes de qualquer
desistência — fica como trabalho futuro, e a banca provavelmente vai
perguntar.

**O que dá para dizer.** Que a estrutura de interação no AVA, obtida
sem nenhum rótulo, **separa** os alunos que concluem dos que não
concluem com nitidez (Q1 × Q4: 89% contra 11%), enquanto a estrutura
curricular (disciplinas do `module_presentation`) quase não separa. É a
mesma diferença que a A-08 encontrou para as comunidades: o sinal está
no comportamento, não na matrícula. Do lado dos recursos do AVA, a
tabela de "disciplinas" críticas não informa nada — os recursos centrais
são acessados por quase todos os alunos (1.866 dos 1.870 no primeiro),
então a taxa deles é a da base.

**Duas ressalvas que precisam ir para o texto.**

1. **Desfecho por aluno, não por matrícula.** O ETL guarda um desfecho
   por aluno, o da apresentação mais recente (A-02). Para 91,8% dos
   alunos do `module_presentation`, que cursaram uma só disciplina, é o
   daquela disciplina; para os demais, pode ser de outra.
2. **Matrícula vinda do bipartido com `score_threshold = 40`.** Só há
   aresta onde a nota passou do limiar: 3.674 alunos sem nenhuma nota
   acima de 40 ficaram fora do bipartido (A-03), e são justamente os que
   mais reprovam. A taxa **absoluta** fica subestimada; a comparação
   crítica × base continua válida como contraste, porque as duas são
   medidas sobre a mesma população. Uma validação sem esse viés
   precisaria de um bipartido por matrícula (sem limiar), que a Frente A
   pode gerar — fica como sugestão, não como bloqueio.

### Três escolhas da aplicação que a banca pode perguntar (C-04, C-05, C-07)

**O corte de arestas da API é um esqueleto, não as mais pesadas (C-04).**
Um grafo de 1,75 M arestas não se desenha; a API manda no máximo 5.000
por resposta. Ficar com as 5.000 de maior peso parecia o óbvio, mas na
projeção aluno↔aluno do AVA elas tocam só **193 dos 1.870 alunos**: o
resto aparece solto e a figura sugere uma estrutura que não existe. O
padrão passou a ser o **esqueleto** (`cut = backbone`): as k arestas mais
fortes de cada nó, com o maior k que cabe no limite (k = 2, 3.732
arestas, todos os alunos ligados). A resposta declara o critério e o k,
e a interface avisa. Consequência para o texto: capturas de tela de
grafo grande mostram o esqueleto, e a legenda precisa dizer isso. As
figuras do artigo não saem do front, e sim de `reporting/figures.py`.

**Cor e forma por comunidade (C-05).** A paleta é a de Okabe & Ito, feita
para quem tem daltonismo, mas ela não separa todas as cores em escala de
cinza, e as capturas podem ser impressas. Cada comunidade recebe também
uma forma (círculo, triângulo, quadrado…); em cinza, é a forma que
identifica o grupo. A maior comunidade fica sempre com a primeira cor,
para o mesmo grafo sair com as mesmas cores em qualquer execução.

**O relatório interno não traz o perfil das comunidades de disciplinas
(C-07).** O perfil da B-05 caracteriza cada comunidade pelo outro lado do
bipartido. Numa partição de disciplinas, esse lado são os **alunos**, e no
OULAD o rótulo do aluno é o número de matrícula. Publicar esse perfil
exporia alunos individualmente, que é o uso que o trabalho não se propõe
a habilitar. O relatório lista só as disciplinas de cada comunidade, e o
texto é varrido atrás de ids e rótulos de aluno antes de ser gravado.

## A decidir nas specs

| Pendência | Spec | Por que importa |
|---|---|---|
| ~~`weight_mode` da intermediação~~ | ~~C-01~~ | **decidido**: `none` em projeção esparsa, `inverse` em projeção quase completa (ver acima) |
| ~~Interpretação do resultado da validação a posteriori~~ | ~~B-06~~, ~~C-06~~ | **decidida** para as comunidades e para a centralidade (ver acima) |

## O que o artigo não deve afirmar

- Que as comunidades **predizem** evasão. Elas não predizem nada: são
  descrição estrutural, e a relação com o desfecho é verificada depois.
- Que uma disciplina de alta intermediação é "difícil". Ela é
  estruturalmente central; se também é difícil, isso é a pergunta da
  C-06, não a premissa.
- Que os resultados generalizam para outras instituições. O OULAD é uma
  universidade aberta britânica, com perfil de aluno e de currículo
  particulares.
