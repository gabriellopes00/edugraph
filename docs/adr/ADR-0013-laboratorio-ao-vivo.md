# ADR-0013: Laboratório ao vivo e leitura dos resultados em linguagem de gente

**Status:** aceita (substitui em parte a ADR-0004)
**Data:** 2026-10-30
**Decidido por:** Pedro, Gabriel, Lucas
**Frente:** [T]

## Contexto

Na revisão de entrega (30/10/2026), o que o professor veria ao subir a
interface era um grafo já calculado, com comunidades chamadas
"Comunidade 0, 1, 2" e nenhuma forma de ver **como** o grafo nasce. A
ADR-0004 tornou a API somente leitura porque o Girvan-Newman não termina
em tempo de HTTP **sobre a base real**; mas isso vale para o OULAD, não
para uma turma de 45 alunos.

Números medidos na mesma revisão:

| Rede | Louvain | Girvan-Newman |
|---|---:|---:|
| turma gerada, 45 alunos, 337 ligações | 3 ms | 0,5 s |
| turma gerada, 60 alunos, 704 ligações | 4 ms | 2,8 s |
| OULAD real, amostra de 40 alunos | 5 ms | 4,1 s |

Dois fatos pesaram além do tempo:

1. Amostras pequenas do OULAD real **não formam grupos visíveis**: com 40
   alunos a projeção é quase completa e o Louvain acha Q ≈ 0. Uma demo
   só com dado real mostraria um grafo sem estrutura.
2. A biblioteca `python-louvain` devolve só a hierarquia pronta; em redes
   pequenas são dois níveis (cada nó sozinho e o resultado). Não há o que
   animar.

E uma decisão do grupo, tomada na mesma data: o `CLAUDE.md` e os
contratos foram montados para a fase de arquitetura; hoje os três
integrantes podem mexer em qualquer parte do sistema.

## Decisão

O projeto ganha um **laboratório ao vivo**: `POST /lab/run` monta, na
hora, uma rede pequena (turma de Computação gerada com o gerador da
A-01, ou amostra de um dataset em disco), roda Louvain **ou**
Girvan-Newman de verdade e devolve o passo a passo; a interface anima as
quatro etapas (matrículas, projeção, algoritmo, resultado). Junto vêm
quatro mudanças:

1. **Leitura dos resultados** (`/insight`, `/outcomes`): nome das
   comunidades, papel de cada nó e frases-resumo, por regra.
2. **Pacote `edugraph.lab`**, fora das quatro frentes, que compõe as
   frentes pelo registro. A API importa `lab`, não as frentes.
3. **Cache de uma projeção** na API.
4. **Sinais por aluno** (`edugraph.lab.signals`): *risco de evasão* e
   *possíveis talentos*, em `insight.signals`. São contas de estatística
   descritiva sobre medidas de rede, **sem rótulo e sem modelo treinado**:
   o risco é a média ponderada de três sinais de afastamento medidos
   contra a turma em desvios-padrão (z) — carga (nº de disciplinas),
   intensidade (nota ou atividade de cada matrícula frente à média da
   disciplina) e vínculo com o próprio grupo (o *z* de Guimerà e
   Amaral) —, com pesos 0,35/0,35/0,30 e cortes legíveis (≥ 0,25 em
   atenção; ≥ 0,50 alto) **fixados antes de olhar o desfecho**. Os
   talentos são quem tem intensidade ≥ 1 desvio acima da turma, se
   destaca numa disciplina (z ≥ 1,5) ou liga grupos sem perder
   desempenho, sem estar em risco. O resultado é descrito na tela como
   *indicador estrutural, não previsão*. A **conferência** contra o
   `outcomes.csv` (taxa de reprovação/desistência por faixa e AUC) é feita
   depois, em `community/evaluate.py` (`outcomes_by_group`, `rank_auc`),
   e só aparece na revelação do desfecho (ADR-0008).

O cálculo pesado (OULAD inteiro, Girvan-Newman da coorte) continua só
pela CLI. O laboratório tem limites: 75 alunos, 4.000 ligações, 1.500
ligações no Girvan-Newman, 60 s.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter a API somente leitura e animar um vídeo gravado | Não é "ao vivo": a banca pode pedir outra turma, outro algoritmo, e a resposta é o que ela quer ver |
| Animar o resultado final fingindo os passos | Seria encenação. A tela mostra o que o algoritmo fez de fato |
| Rodar os algoritmos em JavaScript no navegador | Duplicaria os algoritmos; o artigo defende os de Python, comparados com o NetworkX |
| Streaming por WebSocket, quadro a quadro | Complexidade sem ganho: o cálculo leva menos de 3 s e a resposta inteira já traz o rastro |
| Usar `python-louvain` e mostrar só dois níveis | Sem movimento para animar; a demonstração perderia a parte mais clara do método |
| Papéis com os limiares originais de Guimerà e Amaral (z ≥ 2,5, P fixo) | Projeção densa: 1.585 dos 1.870 alunos do AVA viravam "ponte" |
| Treinar um classificador para nomear comunidades | Proibido (regra 1). Os nomes saem de contagem de disciplinas |

## Consequências

**Boas.** A banca vê o grafo nascer e escolhe turma, tamanho, mistura entre
áreas, algoritmo e corte de ligações. O resultado vem em português
("Algoritmos · Estruturas de Dados", "Pouco engajados") e com a revelação
a posteriori: as áreas que o gerador plantou e o desfecho dos alunos,
que o grafo nunca viu. A API do AVA caiu de ~10 s para 0 s a partir do
segundo pedido pelo mesmo grafo.

**Ruins.**

- A API deixa de ser somente leitura: há um `POST` que consome CPU. O
  limite de tamanho e de tempo protege o servidor, mas não é
  autenticação; o uso continua sendo interno.
- O Louvain da tela **não é o mesmo código** do algoritmo registrado.
  Para não ser promessa vazia, um teste exige que o Q fique a menos de
  0,02 do `python-louvain` e que recupere as áreas plantadas sem ruído, e
  a tela mostra os dois Q lado a lado. Nos casos medidos, Q idêntico em
  5 de 6 e partição idêntica em 5 de 6; no outro, o Q da implementação
  própria foi maior (0,3784 contra 0,3766).
- O Girvan-Newman é o mesmo cálculo do registrado (mesmo gerador, mesma
  regra de desempate); um teste confere a partição.
- Os papéis dos nós usam limiares **adaptados** (z ≥ 1; P comparado com o
  do próprio grupo, com margem de 0,05), não os do artigo original. São
  uma leitura descritiva, não um resultado a reportar sem a ressalva.
- O cache guarda uma projeção só: no AVA, ~1 GB. Trocar de projeção
  grande paga a leitura de novo (~5 s).

**O que muda no código.** Novos: `src/edugraph/lab/`,
`src/edugraph/api/lab_routes.py`, `src/edugraph/api/projection_cache.py`,
`frontend/src/lab/`, `LabView`, `LabCanvas`, `LabPaineis`, `QChart`,
`cascas.ts`, `tests/lab/`, `tests/api/test_projection_cache.py`,
`frontend/tests/frames.test.mjs`. Alterados: `api/app.py` (rota nova e
CORS com POST), `api/routes.py` (cache), `GraphView`, `CommunityLegend`,
`NodePanel`, `App`. Os testes de contrato (`tests/contract/`) **não
mudaram** e passam: `lab` não é uma das quatro frentes, e quem lê o
desfecho continua sendo `community/evaluate.py`. Os sinais acrescentam
`lab/signals.py`, `components/Sinais.tsx` e `tests/lab/test_signals.py`.
O tour de boas-vindas acrescenta `frontend/src/tour/` e `lab/pedido.ts`
(o laboratório deixou de montar a rede sozinho: só ao apertar ▶);
`evaluate.py` ganhou `outcomes_by_group` e `rank_auc`.

**O que os sinais mostraram nos dados** (conferência a posteriori,
31/10/2026): no AVA do OULAD inteiro (1.870 alunos), 46% dos de risco
alto desistiram e outros 46% reprovaram, contra 11% e 19% dos sem sinais
(AUC 0,79); na coorte por avaliação (1.706 alunos) o AUC é 0,91. Na
turma fictícia o desfecho vem do gerador, que sorteia alunos "em risco"
com notas menores e mais abandono: o AUC fica entre 0,5 e 0,8 conforme a
turma, e a tela diz isso. O limite é que a carga e a intensidade
carregam a maior parte do sinal; o vínculo com o grupo depende do
algoritmo de comunidades.

## Impacto no artigo

- **Capítulo 3:** a classificação de papéis (Guimerà; Amaral, 2005) e a
  adaptação dos limiares entram como parágrafo de justificativa, com o
  número que a motivou (1.585 de 1.870).
- **Capítulo 3 / discussão:** os sinais de risco e talento respondem à
  pergunta "o que a rede diz que um gestor possa usar?" sem classificador:
  o grafo nunca viu o desfecho e, ainda assim, separa quem desiste.
  Pergunta de banca provável: *"isso é aprendizado de máquina?"* — não:
  não há treino, ajuste a rótulos nem parâmetro estimado; os pesos e
  cortes são convenções fixas, e o desfecho só entra na conferência.
- **Figura 9:** passa a incluir as quatro etapas do laboratório.
- **Limitação:** o Louvain da animação é uma implementação própria,
  conferida contra a biblioteca; as tabelas continuam vindo do algoritmo
  registrado.
