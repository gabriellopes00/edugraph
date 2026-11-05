# Estudo para a apresentação ao orientador (novembro/2026)

Visão geral do que o sistema faz, para entender antes de mostrar. O foco é
o **Laboratório ao vivo**, a parte interativa. Os números foram medidos em
04/11/2026 com os valores padrão da tela (45 alunos, semente 12, mistura
de 20%).

## 1. O sistema em uma frase

Pega dados de alunos e disciplinas, transforma num **grafo** (pontos
ligados por linhas), encontra **grupos de alunos parecidos** e diz quem
é importante na rede — usando só Teoria dos Grafos, sem inteligência
artificial nem aprendizado de máquina (exigência do orientador, conferida
por teste automático).

Para subir tudo: `python scripts/iniciar.py`. Ele instala, testa e abre
http://127.0.0.1:8000/ no navegador.

## 2. As palavras que vão aparecer na tela

| Palavra | O que é, sem jargão |
|---|---|
| **Grafo bipartido** | Dois tipos de ponto: alunos de um lado, disciplinas do outro. Uma linha liga o aluno à disciplina que ele cursou. Aluno nunca se liga direto a aluno. |
| **Projeção** | Tira as disciplinas do desenho e liga **aluno com aluno** quando os dois cursaram a mesma disciplina. Quanto mais disciplinas em comum, mais grossa a linha (o **peso**). |
| **Ponderação** | A regra do peso. *Simples*: conta as disciplinas em comum. *Alocação de recursos*: disciplina que todo mundo cursa vale pouco, disciplina rara vale muito — porque dividir uma disciplina rara diz mais sobre duas pessoas. |
| **Comunidade (grupo)** | Um conjunto de alunos muito ligados entre si e pouco ligados ao resto. É o que os algoritmos procuram. |
| **Modularidade (Q)** | A **nota** de uma divisão em grupos. Mede quanto das ligações fica *dentro* dos grupos, descontando o que ficaria lá por puro acaso. **Q perto de 0**: a divisão não é melhor que sortear. **Acima de 0,3**: grupos bem definidos. O máximo teórico é 1. |
| **Ponte** | Uma ligação entre dois grupos, por onde passa muito "caminho" de um lado para o outro. O nome técnico do quanto ela é usada é *intermediação*. |
| **Centralidade** | Quão importante é um ponto na rede: quantas ligações tem (*grau*), quanto serve de ponte (*intermediação*) ou quanto está ligado a outros importantes (*autovetor*). Na tela, muda o tamanho das bolinhas. |

## 3. Laboratório ao vivo

A aba que abre primeiro. Monta uma rede pequena **na hora**, roda o
algoritmo de verdade e anima o que ele fez. Nada roda sozinho: escolha os
controles e aperte ▶. Mudar um controle depois espera o próximo ▶.

### Os controles

**1 · Turma**
- **Fonte dos dados**: a turma de Computação fictícia (padrão) ou uma
  amostra de um dos datasets em disco (seção 4).
- **Número de alunos**: de 24 a 75. Mais alunos, mais lento o
  Girvan–Newman (75 alunos: ~3,6 s).
- **Mistura entre áreas** (só na turma fictícia): a chance de um aluno
  cursar também uma disciplina de fora da sua área. 0% = áreas perfeitas;
  100% = todo mundo cursa algo de fora.
- **Sortear nova turma**: troca a semente, e sai outra turma com as mesmas
  regras.

**2 · Rede**
- **O que projetar**: ligar *alunos* (padrão) ou *disciplinas* entre si.
- **Ponderação**: simples ou alocação de recursos (seção 2).
- **Ligação mínima**: apaga as linhas mais fracas. Nos dados reais, a
  rede vem quase toda ligada (todo mundo com todo mundo), e o botão
  *Manter só as 30% mais fortes* aparece para deixá-la legível.

**Algoritmo**: Louvain ou Girvan–Newman.

### As quatro etapas da animação

1. **Matrículas** — o grafo bipartido. Alunos de um lado, disciplinas do
   outro, linhas surgindo. Na turma padrão: 43 alunos, 8 disciplinas, 93
   matrículas (só conta a matrícula com nota média ≥ 50).
2. **Projeção** — as disciplinas somem e os alunos se ligam entre si: 337
   ligações. Aqui o grupo já começa a existir: quem é da mesma área divide
   mais disciplinas, então as **linhas grossas ficam dentro das áreas**, e
   as linhas entre áreas vêm dos alunos que cursam algo de fora.
3. **Algoritmo** — o passo a passo, com o Q mudando ao vivo e um gráfico
   da evolução do Q.
4. **Resultado** — os grupos com nome, os papéis, os perfis dos alunos e
   as revelações.

As setas ← → andam quadro a quadro; espaço toca e pausa; **F** põe em
tela cheia.

### Como o Louvain se comporta

Pense numa festa em que cada pessoa começa sozinha numa mesa.

1. Um a um, cada aluno olha as mesas dos vizinhos e **muda para a mesa
   onde a nota Q mais sobe** — em geral, onde estão os colegas com quem ele
   tem mais disciplinas em comum. Se nenhuma mudança melhora, ele fica.
2. Repete até **ninguém mais querer mudar**.
3. Depois, cada mesa vira um "super-aluno" e o processo recomeça num nível
   acima (em redes pequenas como a da tela, um nível basta).

É um método **de baixo para cima**: junta. Na tela, os pontos trocam de
cor e o Q só sobe. Na turma padrão: 41 movimentos, Q de 0 a **0,53**, três
grupos, **1 milésimo de segundo**. E acerta a área de 100% dos alunos.

### Como o Girvan–Newman se comporta

O caminho inverso: começa com a rede inteira junta e **vai cortando**.

1. Calcula qual ligação é a **ponte mais usada** entre todos os pares de
   alunos e a apaga (fica vermelha na tela).
2. **Recalcula as pontes** — o desenho mudou — e apaga a próxima.
3. Quando a rede se parte em pedaços, cada pedaço vira um grupo. Ele anota
   o Q de cada corte e, no fim, **fica com o corte de maior Q**.

É um método **de cima para baixo**: separa. Na tela, as ligações somem e
o gráfico do Q sobe até um pico e depois cai (cortar demais só piora). Na
turma padrão: apaga as 337 ligações, chega aos mesmos três grupos com Q =
**0,49** e acerta 93% dos alunos, mas leva **0,6 s — umas 550 vezes mais
que o Louvain**. Recalcular as pontes a cada corte é o que o torna lento;
no OULAD inteiro ele não termina, e por isso tem limite de tempo.

**Quando ele se perde:** a ponte é escolhida pelo número de caminhos, sem
olhar o peso da linha. Com muita mistura entre áreas, ele corta ligações
de dentro dos grupos e fragmenta:

| Turma padrão, mudando a mistura | Louvain | Girvan–Newman |
|---|---|---|
| 20% (padrão) | Q 0,53 · 3 grupos · acerta 100% | Q 0,49 · 3 grupos · acerta 93% |
| 50% | Q 0,45 · 3 grupos · acerta 90% | Q 0,34 · 7 grupos |
| 100% | Q 0,19 · 3 grupos · acerta 86% | Q 0,02 · 28 grupos |

### O que aparece no resultado

- **Os grupos, com nome.** O nome vem das disciplinas que mais aparecem
  no grupo em comparação com a turma ("Algoritmos · Estruturas de Dados").
  É contagem, não IA.
- **Papel de cada aluno**: *referência* (muito ligado dentro do próprio
  grupo), *conector* (muito ligado no grupo e também fora dele), *ponte*
  (pouco central no grupo, mas ligado a outros grupos) e *periférico*
  (poucas ligações). Dá para filtrar no grafo.
- **Perfis dos alunos**: *quem merece atenção* (risco de evasão) e
  *possíveis talentos*, cada um com o porquê. São indicadores tirados do
  grafo (poucas disciplinas, desempenho abaixo da turma, pouco vínculo com
  o grupo), com pesos fixos — não é previsão nem modelo treinado.
- **Revelar o que o grafo nunca viu**: as *áreas que o gerador plantou*
  (a resposta certa, para medir o acerto) e o *desfecho dos alunos*
  (aprovado, reprovado…). Os dois ficam guardados fora do grafo e só são
  cruzados com os grupos no fim.
- **Conferência**: o Louvain da tela foi escrito pelo grupo para mostrar
  cada movimento; a tela compara com a biblioteca oficial (na turma
  padrão, mesma partição e mesmo Q).
- **Mesma turma, os dois algoritmos**: depois de rodar os dois, uma tabela
  compara Q, grupos e tempo.

### Experimentos que valem mostrar

- Turma padrão com **Louvain**, depois **Girvan–Newman**: mesmos grupos,
  tempos muito diferentes (a tabela de comparação aparece sozinha).
- **Mistura** em 0% (Q 0,65, grupos perfeitos) e em 50% ou mais: os grupos
  ficam difíceis de achar, e o Girvan–Newman se perde antes.
- **Sortear nova turma**: o resultado se repete com outra turma.
- **Projetar disciplinas**: as 8 disciplinas se agrupam nas 3 áreas (Q
  0,45 no Louvain).
- **Dado real** (`oulad_vle_bbb_2013j`): ver a seção 4. A rede vem quase
  completa e o Q fica perto de 0 — é o resultado honesto, não um defeito.

## 4. Os datasets que dá para escolher

A lista do laboratório mostra a turma fictícia e todo dataset que estiver
em disco. Os do OULAD só aparecem se `data/processed/` existir (o ZIP de
resultados; ver `docs/entrega.md`, seção 9). Em todos, o laboratório
sorteia uma **amostra** do tamanho pedido. Medido com 45 alunos e Louvain:

| Dataset | Como foi montado | O que acontece no laboratório |
|---|---|---|
| **Turma de Computação** (fictícia, padrão) | Gerada na hora. Três áreas plantadas — Desenvolvimento de Software (Algoritmos, Estruturas de Dados, Programação Web), Infraestrutura e Redes (Redes, Sistemas Operacionais, Segurança) e Dados (Banco de Dados, Modelagem). Cada aluno cursa 2 ou 3 disciplinas da sua área e, com a chance da "mistura", uma de fora. Notas sorteadas; alguns alunos "em risco" recebem notas menores. Nomes e desfechos são inventados. | Grupos nítidos (Q 0,53). É a única fonte com **as áreas plantadas para revelar**. |
| `synthetic_v1` | O mesmo gerador, com 7 disciplinas de nome genérico (AAA a GGG) em três áreas ("exatas", "sistemas", "humanas"), 35% de mistura e nota ≥ 60. 98 alunos. É o dataset de teste do projeto. | Três grupos claros (Q 0,50), nomeados pelos códigos ("EEE · DDD"). |
| `synthetic_v2` | O `synthetic_v1` com 70% dos alunos reduzidos a **uma só matrícula**, imitando o OULAD, onde a maioria cursa um módulo. | Mais grupos, alguns de uma disciplina só (Q 0,46, 4 grupos): menos informação por aluno. |
| `tiny_v1` | 6 alunos e 3 disciplinas, desenhado à mão para os testes conferirem o resultado no papel. | Tem só 6 alunos, qualquer que seja o tamanho pedido: bom para ver o passo a passo devagar. |
| `oulad_module_presentation` | OULAD real inteiro: 22.425 alunos ligados à oferta de disciplina que cursaram (módulo + semestre, ex.: "BBB_2013J"), com nota ≥ 40. | A maioria dos alunos tem uma matrícula só, então cada oferta vira um grupo isolado: **Q 0,78 e 13 grupos que não querem dizer nada**. Um Q alto pode enganar — no trabalho, ele é comparado com redes embaralhadas e fica igual a elas. |
| `oulad_bbb_2013j` | Uma turma real (módulo BBB, semestre 2013J, 1.706 alunos), ligando o aluno a cada uma das **11 avaliações** em que tirou ≥ 40. | Quase todo mundo faz as mesmas avaliações: rede completa e Q ≈ 0,03. Grupos "Muitas disciplinas" e "Poucas disciplinas". |
| `oulad_vle_bbb_2013j` | A mesma turma, mas ligando o aluno aos **recursos do ambiente virtual** (AVA) que acessou, com o número de cliques como peso: 1.870 alunos × 320 recursos. É o dataset do trabalho que mostra grupos de verdade. | Na amostra, Q ≈ 0,02 ("Mais engajados" × "Menos engajados"); com *Manter só as 30% mais fortes*, Q 0,10. Os grupos aparecem melhor na turma inteira, no Explorar resultados. |

## 5. Explorar resultados (a outra aba)

Mostra os resultados **já calculados** sobre os datasets inteiros, em vez
de montar na hora. Escolhe-se o dataset, a projeção e a partição (o
resultado de um algoritmo), e a tela desenha o grafo colorido pelos
grupos, com a nota Q, o número de grupos, a legenda e o tamanho dos pontos
pela centralidade. Clicar num ponto mostra os vizinhos e as três medidas
de importância. Tem menos animação e mais números: é onde está o
resultado do trabalho.

O exemplo mais forte é o `oulad_vle_bbb_2013j` inteiro, partição
`louvain__student_resource_allocation`: quatro grupos por nível de
engajamento, Q = 0,08 (baixo, mas cinco vezes o de uma rede embaralhada).
Em *Revelar o desfecho*, o grupo «Pouco engajados» (941 alunos) tem **69%
de reprovados e desistentes**, contra 7% em «Engajamento moderado» — e o
grafo nunca viu a nota final. Dos 197 alunos marcados com risco alto, 94%
reprovaram ou desistiram (na turma toda, 43%).

## 6. Perguntas para o professor

Anotar as respostas em
[`observacoes/para-todos.md`](../../observacoes/para-todos.md) (T-OBS-05).

1. **Precisamos entregar o OULAD, ou o dataset fictício basta?** O OULAD
   bruto tem 450 MB e leva ~14 min para recalcular (a parte com
   Girvan–Newman, mais de 2 h). A licença (CC BY 4.0) permite
   redistribuir; o problema é o tamanho. Nossa proposta: o repositório
   com os fictícios e um **ZIP de 32 MB com os resultados do OULAD já
   calculados**, instalado com `python scripts/iniciar.py --oulad <zip>`.
2. **Uma versão online só com os dados fictícios ajuda?** É possível
   (análise em `docs/entrega.md`, seção 9), como atalho para ver, sem
   substituir o repositório.
3. **O "risco de evasão" cabe na regra "sem aprendizado de máquina"?** É
   conta descritiva com pesos fixos, sem treino, mas o nome soa como
   previsão. Manter, renomear ou deixar como trabalho futuro?

## 7. Se algo der errado

- **A página mostra só um texto (JSON)**: falta compilar a interface, o
  que exige Node 20+. O `iniciar.py` compila sozinho quando o Node existe.
- **Erro ao clonar no Windows (`Filename too long`)**: clonar numa pasta
  curta, como `C:\tcc`.
- **Porta ocupada**: `python scripts/iniciar.py --porta 8001`.
- **A primeira rodada demora**: o primeiro ▶ e a primeira abertura do
  AVA no explorador carregam as bibliotecas e o arquivo grande (~10 s);
  depois, é instantâneo. Vale fazer os dois antes de apresentar.
